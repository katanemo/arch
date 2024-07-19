use common_types::EmbeddingRequest;
use log::info;
use log::warn;
use serde_json::to_string;
use std::collections::HashMap;
use std::time::Duration;

use proxy_wasm::traits::*;
use proxy_wasm::types::*;

mod common_types;
mod configuration;
mod consts;
mod llm_backend;
mod stats;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(FilterContext {
          callouts: HashMap::new(),
          config: None,
          metrics: WasmMetrics {},
        })
    });
}}

struct StreamContext {
    context_id: u32,
    config: configuration::Configuration,
    metrics: WasmMetrics,
    host_header: Option<String>,
}

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for StreamContext {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        // Save the host header to be used by filter logic later on.
        self.host_header = self.get_http_request_header(":host");

        // Remove the Content-Length header because further body manipulations in the gateway logic will invalidate it.
        // Server's generally throw away requests whose body length do not match the Content-Length header.
        // However, a missing Content-Length header is not grounds for bad requests given that intermediary hops could
        // manipulate the body in benign ways e.g., compression.
        self.set_http_request_header("content-length", None);

        match self.get_http_request_header(":path") {
            // The gateway can start gathering information necessary for routing. For now change the path to an
            // OpenAI API path.
            Some(path) if path == "/llmrouting" => {
                self.set_http_request_header(":path", Some("/v1/chat/completions"));
            }
            // Otherwise let the filter continue.
            _ => (),
        }

        Action::Continue
    }

    fn on_http_request_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        // Let the client send the gateway all the data before sending to the LLM_provider.
        // TODO: consider a streaming API.
        if !end_of_stream {
            return Action::Pause;
        }

        // Let the filter continue if the request is not meant for OpenAi
        match &self.host_header {
            Some(host) if host != "api.openai.com" => return Action::Continue,
            _ => {}
        }

        if let Some(body_bytes) = self.get_http_request_body(0, body_size) {
            let mut deserialized: llm_backend::ChatCompletions =
                match serde_json::from_slice(&body_bytes) {
                    Ok(deserialized) => deserialized,
                    Err(msg) => panic!("Failed to deserialize: {}", msg),
                };

            warn!("deserialized body = {:?}", deserialized);

            // This is the big moment here: the user did not set the model in their request.
            // The gateway is setting the model for them.
            deserialized.model = String::from("gpt-3.5-turbo");
            let json_string = serde_json::to_string(&deserialized).unwrap();

            warn!("serialized json = {}", json_string);

            self.set_http_request_body(0, body_size, &json_string.into_bytes())
        }

        Action::Continue
    }
}

impl Context for StreamContext {}

#[derive(Copy, Clone)]
struct WasmMetrics {
    // Fill with metrics as needed
}

struct FilterContext {
    metrics: WasmMetrics,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: HashMap<u32, common_types::CalloutData>,
    config: Option<configuration::Configuration>,
}

impl Context for FilterContext {
    fn on_http_call_response(
        &mut self,
        token_id: u32,
        _num_headers: usize,
        body_size: usize,
        _num_trailers: usize,
    ) {
        info!("on_http_call_response: token_id = {}", token_id);

        let callout_data = self.callouts.remove(&token_id).expect("invalid token_id");

        match callout_data.message {
            common_types::MessageType::EmbeddingRequest(common_types::EmbeddingRequest {
                create_embedding_request,
                prompt_target,
            }) => {
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

                        let mut payload: HashMap<String, String> = HashMap::new();
                        payload.insert(
                            "prompt-target".to_string(),
                            to_string(&prompt_target).unwrap(),
                        );
                        payload.insert(
                            "few-shot-example".to_string(),
                            create_embedding_request.input.clone(),
                        );

                        let id = md5::compute(create_embedding_request.input);

                        let create_vector_store_points = common_types::CreateVectorStorePoints {
                            points: vec![common_types::VectorPoint {
                                id: format!("{:x}", id),
                                payload,
                                vector: embedding_response.data[0].embedding.clone(),
                            }],
                        };
                        let json_data = to_string(&create_vector_store_points).unwrap(); // Handle potential errors
                        info!(
                            "create_vector_store_points: points length: {}",
                            embedding_response.data[0].embedding.len()
                        );
                        let token_id = match self.dispatch_http_call(
                            "qdrant",
                            vec![
                                (":method", "PUT"),
                                (":path", "/collections/prompt_vector_store/points"),
                                (":authority", "qdrant"),
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
                            message: common_types::MessageType::CreateVectorStorePoints(
                                create_vector_store_points,
                            ),
                        };
                        if self.callouts.insert(token_id, callout_message).is_some() {
                            panic!("duplicate token_id")
                        }
                    }
                }
            }
            common_types::MessageType::CreateVectorStorePoints(_) => {
                info!("response received for CreateVectorStorePoints");
                if let Some(body) = self.get_http_call_response_body(0, body_size) {
                    if !body.is_empty() {
                        info!("response body: {:?}", String::from_utf8(body).unwrap());
                    }
                }
            }
        }
    }
}

// RootContext allows the Rust code to reach into the Envoy Config
impl RootContext for FilterContext {
    fn on_configure(&mut self, _: usize) -> bool {
        if let Some(config_bytes) = self.get_plugin_configuration() {
            self.config = serde_yaml::from_slice(&config_bytes).unwrap();
            info!("on_configure: plugin configuration loaded");
        }
        true
    }

    fn create_http_context(&self, context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(StreamContext {
            context_id,
            config: self.config.clone()?,
            metrics: self.metrics,
            host_header: None,
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
                    model: String::from(consts::DEFAULT_EMBEDDING_MODEL),
                };

                // TODO: Handle potential errors
                let json_data = to_string(&embeddings_input).unwrap();

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
                let embedding_request = EmbeddingRequest {
                    create_embedding_request: embeddings_input,
                    prompt_target: prompt_target.clone(),
                };
                let callout_message = common_types::CalloutData {
                    message: common_types::MessageType::EmbeddingRequest(embedding_request),
                };
                if self.callouts.insert(token_id, callout_message).is_some() {
                    panic!("duplicate token_id")
                }
            }
        }
        self.set_tick_period(Duration::from_secs(0));
    }
}
