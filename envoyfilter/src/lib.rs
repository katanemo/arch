mod configuration;

use log::info;
use std::time::Duration;

use proxy_wasm::traits::*;
use proxy_wasm::types::*;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(HttpHeaderRoot {
            config: None,
        })
    });
}}

struct HttpHeader {
    context_id: u32,
    config: configuration::Configuration,
}

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for HttpHeader {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        // Example of reading the HTTP headers on the incoming request
        for (name, value) in &self.get_http_request_headers() {
            info!("#{} -> {}: {}", self.context_id, name, value);
        }

        // Example logic of branching based on a request header.
        match self.get_http_request_header(":path") {
            // If the path header is present and the path is /inline
            Some(path) if path == "/inline" => {
                // Dispatch an HTTP call inline. This is the model that we will use for the LLM routing host.
                self.dispatch_http_call(
                    "httpbin",
                    vec![
                        (":method", "GET"),
                        (":path", "/bytes/1"),
                        (":authority", "httpbin.org"),
                    ],
                    None,
                    vec![],
                    Duration::from_secs(5),
                )
                .unwrap();
                // Pause the filter until the out of band HTTP response arrives.
                Action::Pause
            }

            // Otherwise let the HTTP request continue.
            _ => Action::Continue,
        }
    }

    fn on_http_response_headers(&mut self, _: usize, _: bool) -> Action {
        self.set_http_response_header("Powered-By", Some("Katanemo"));
        Action::Continue
    }
}

impl Context for HttpHeader {
    // Note that the event driven model continues here from the return of the on_http_request_headers above.
    fn on_http_call_response(&mut self, _: u32, _: usize, body_size: usize, _: usize) {
        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            if !body.is_empty() && body[0] % 2 == 0 {
                info!("Access granted.");
                // This call allows the filter to continue operating on the HTTP request sent by the user.
                // In Katanemo's use case the call would continue after the LLM host has responded with routing
                // decisions.
                self.resume_http_request();
                return;
            }
        }
        info!("Access forbidden.");
        // This is an example of short-circuiting the http request and sending back a response to the client.
        // i.e there was never an external HTTP request made. This could be used for example if the user prompt requires
        // more information before it can be sent out to a third party API.
        self.send_http_response(
            403,
            vec![("Powered-By", "Katanemo")],
            Some(b"Access forbidden.\n"),
        );
    }
}

struct HttpHeaderRoot {
    config: Option<configuration::Configuration>,
}

impl Context for HttpHeaderRoot {}

// RootContext allows the Rust code to reach into the Envoy Config
impl RootContext for HttpHeaderRoot {
    fn on_configure(&mut self, plugin_configuration_size: usize) -> bool {
        info!(
            "on_configure: plugin_configuration_size is {}",
            plugin_configuration_size
        );

        if let Some(config_bytes) = self.get_plugin_configuration() {
            let config_str = String::from_utf8(config_bytes).unwrap();
            info!("on_configure: plugin configuration is {:?}", config_str);
            self.config = serde_yaml::from_str(&config_str).unwrap();
            info!("on_configure: plugin configuration loaded");
            info!("on_configure: {:?}", self.config);
        }
        true
    }

    fn create_http_context(&self, context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(HttpHeader {
            context_id,
            config: self.config.clone()?,
        }))
    }

    fn get_type(&self) -> Option<ContextType> {
        Some(ContextType::HttpContext)
    }
}
