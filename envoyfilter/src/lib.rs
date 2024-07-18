mod common_types;
mod configuration;

use log::info;
use serde_json::to_string;
use stats::IncrementingMetric;
use stats::Metric;
use stats::RecordingMetric;
use std::cell::RefCell;
use std::collections::HashMap;
use std::time::Duration;

use proxy_wasm::traits::*;
use proxy_wasm::types::*;

mod stats;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(HttpHeaderRoot {
          callouts: RefCell::new(HashMap::new()),
          config: None,
          metrics: WasmMetrics {
                counter: stats::Counter::new(String::from("wasm_counter")),
                gauge: stats::Gauge::new(String::from("wasm_gauge")),
                histogram: stats::Histogram::new(String::from("wasm_histogram")),
            },
        })
    });
}}

struct HttpHeader {
    context_id: u32,
    config: configuration::Configuration,
    metrics: WasmMetrics,
}

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for HttpHeader {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        // Read config
        info!("config: {:?}", self.config.prompt_config.system_prompt);
        // Metrics
        self.metrics.counter.increment(10);
        info!("counter -> {}", self.metrics.counter.value());
        self.metrics.gauge.record(20);
        info!("gauge -> {}", self.metrics.gauge.value());
        self.metrics.histogram.record(30);
        info!("histogram -> {}", self.metrics.histogram.value());

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
        info!("on_http_call_response: body_size = {}", body_size);
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

#[derive(Copy, Clone)]
struct WasmMetrics {
    counter: stats::Counter,
    gauge: stats::Gauge,
    histogram: stats::Histogram,
}

struct HttpHeaderRoot {
    metrics: WasmMetrics,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: RefCell<HashMap<u32, common_types::CalloutData>>,
    config: Option<configuration::Configuration>,
}

impl Context for HttpHeaderRoot {
    fn on_http_call_response(
        &mut self,
        token_id: u32,
        _num_headers: usize,
        body_size: usize,
        _num_trailers: usize,
    ) {
        info!("on_http_call_response: token_id = {}", token_id);

        let callout_data = self
            .callouts
            .borrow_mut()
            .remove(&token_id)
            .expect("invalid token_id");

        info!(
            "on_http_call_response: callout message = {:?}",
            callout_data.message
        );

        match callout_data.message {
            common_types::MessageType::CreateEmbeddingRequest(
                common_types::CreateEmbeddingRequest { .. },
            ) => {
                info!("response received for CreateEmbeddingRequest");
                if let Some(body) = self.get_http_call_response_body(0, body_size) {
                    if !body.is_empty() {
                        let embedding_response: common_types::CreateEmbeddingResponse =
                            serde_json::from_slice(&body).unwrap();
                        info!(
                            "embedding_response model: {}, vector len: {}",
                            embedding_response.model,
                            embedding_response.data[0].embedding.len()
                        );
                        //TODO: store embedding_response in qdrant
                    }
                }
            }
        }
    }
}

// RootContext allows the Rust code to reach into the Envoy Config
impl RootContext for HttpHeaderRoot {
    fn on_configure(&mut self, _: usize) -> bool {
        if let Some(config_bytes) = self.get_plugin_configuration() {
            self.config = serde_yaml::from_slice(&config_bytes).unwrap();
            info!("on_configure: plugin configuration loaded");
        }
        true
    }

    fn create_http_context(&self, context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(HttpHeader {
            context_id,
            config: self.config.clone()?,
            metrics: self.metrics,
        }))
    }

    fn get_type(&self) -> Option<ContextType> {
        Some(ContextType::HttpContext)
    }

    fn on_vm_start(&mut self, _: usize) -> bool {
        info!("on_vm_start: setting up tick timeout");
        self.set_tick_period(Duration::from_secs(1));
        true
    }

    fn on_tick(&mut self) {
        info!("on_tick: starting to process prompt targets");
        for prompt_target in &self.config.as_ref().unwrap().prompt_config.prompt_targets {
            for few_shot_example in &prompt_target.few_shot_examples {
                info!("few_shot_example: {:?}", few_shot_example);
                let embeddings_input = common_types::CreateEmbeddingRequest {
                    input: few_shot_example.to_string(),
                    //FIXME: load model from config
                    model: String::from("BAAI/bge-large-en-v1.5"),
                };

                // TODO: Handle potential errors
                let json_data = to_string(&embeddings_input).unwrap();

                info!("json_data: {:?}", json_data);

                let token_id = match self.dispatch_http_call(
                    "embeddingserver",
                    vec![
                        (":method", "POST"),
                        (":path", "/embeddings"),
                        (":authority", "embeddingserver"),
                        ("content-type", "application/json"),
                    ],
                    Some(json_data.as_bytes()),
                    vec![],
                    Duration::from_secs(5),
                ) {
                    Ok(token_id) => token_id,
                    Err(e) => {
                        panic!("Error dispatching HTTP call: {:?}", e);
                    }
                };
                info!("on_tick: dispatched HTTP call with token_id = {}", token_id);
                let callout_message = common_types::CalloutData {
                    message: common_types::MessageType::CreateEmbeddingRequest(embeddings_input),
                };
                if self
                    .callouts
                    .borrow_mut()
                    .insert(token_id, callout_message)
                    .is_some()
                {
                    panic!("duplicate token_id")
                }
            }
        }
        //TODO: ideally we only need to reload the prompt targets when the configuration changes
        self.set_tick_period(Duration::from_secs(3600));
    }
}
