use common_types::{CallContext, EmbeddingRequest};
use configuration::PromptTarget;
use http::StatusCode;
use log::error;
use log::info;
use md5::Digest;
use open_message_format::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use serde_json;
use stats::{Gauge, RecordingMetric};
use std::collections::HashMap;
use std::time::Duration;

mod common_types;
mod configuration;
mod consts;
mod stats;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(FilterContext::new())
    });
}}

struct StreamContext {
    host_header: Option<String>,
}

impl StreamContext {
    fn save_host_header(&mut self) {
        // Save the host header to be used by filter logic later on.
        self.host_header = self.get_http_request_header(":host");
    }

    fn delete_content_length_header(&mut self) {
        // Remove the Content-Length header because further body manipulations in the gateway logic will invalidate it.
        // Server's generally throw away requests whose body length do not match the Content-Length header.
        // However, a missing Content-Length header is not grounds for bad requests given that intermediary hops could
        // manipulate the body in benign ways e.g., compression.
        self.set_http_request_header("content-length", None);
    }

    fn modify_path_header(&mut self) {
        match self.get_http_request_header(":path") {
            // The gateway can start gathering information necessary for routing. For now change the path to an
            // OpenAI API path.
            Some(path) if path == "/llmrouting" => {
                self.set_http_request_header(":path", Some("/v1/chat/completions"));
            }
            // Otherwise let the filter continue.
            _ => (),
        }
    }
}

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for StreamContext {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        self.save_host_header();
        self.delete_content_length_header();
        self.modify_path_header();

        Action::Continue
    }

    fn on_http_request_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        // Let the client send the gateway all the data before sending to the LLM_provider.
        // TODO: consider a streaming API.
        if !end_of_stream {
            return Action::Pause;
        }

        if body_size == 0 {
            return Action::Continue;
        }

        // Deserialize body into spec.
        // Currently OpenAI API.
        let mut deserialized_body: common_types::open_ai::ChatCompletions =
            match self.get_http_request_body(0, body_size) {
                Some(body_bytes) => match serde_json::from_slice(&body_bytes) {
                    Ok(deserialized) => deserialized,
                    Err(msg) => {
                        self.send_http_response(
                            StatusCode::BAD_REQUEST.as_u16().into(),
                            vec![],
                            Some(format!("Failed to deserialize: {}", msg).as_bytes()),
                        );
                        return Action::Pause;
                    }
                },
                None => {
                    self.send_http_response(
                        StatusCode::INTERNAL_SERVER_ERROR.as_u16().into(),
                        vec![],
                        None,
                    );
                    error!(
                        "Failed to obtain body bytes even though body_size is {}",
                        body_size
                    );
                    return Action::Pause;
                }
            };

        // Modify JSON payload
        deserialized_body.model = String::from("gpt-3.5-turbo");

        match serde_json::to_string(&deserialized_body) {
            Ok(json_string) => {
                self.set_http_request_body(0, body_size, &json_string.into_bytes());
                Action::Continue
            }
            Err(error) => {
                self.send_http_response(
                    StatusCode::INTERNAL_SERVER_ERROR.as_u16().into(),
                    vec![],
                    None,
                );
                error!("Failed to serialize body: {}", error);
                Action::Pause
            }
        }
    }
}

impl Context for StreamContext {}

#[derive(Copy, Clone)]
struct WasmMetrics {
    active_http_calls: Gauge,
}

impl WasmMetrics {
    fn new() -> WasmMetrics {
        WasmMetrics {
            active_http_calls: Gauge::new(String::from("active_http_calls")),
        }
    }
}

struct FilterContext {
    metrics: WasmMetrics,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: HashMap<u32, common_types::CallContext>,
    config: Option<configuration::Configuration>,
}

impl FilterContext {
    fn new() -> FilterContext {
        FilterContext {
            callouts: HashMap::new(),
            config: None,
            metrics: WasmMetrics::new(),
        }
    }

    fn process_prompt_targets(&mut self) {
        for prompt_target in &self
            .config
            .as_ref()
            .expect("Gateway configuration cannot be non-existent")
            .prompt_config
            .prompt_targets
        {
            for few_shot_example in &prompt_target.few_shot_examples {
                info!("few_shot_example: {:?}", few_shot_example);

                let embeddings_input = CreateEmbeddingRequest {
                    input: CreateEmbeddingRequestInput::String(few_shot_example.to_string()),
                    model: String::from(consts::DEFAULT_EMBEDDING_MODEL),
                    encoding_format: None,
                    dimensions: None,
                    user: None,
                };

                let json_data: String = match serde_json::to_string(&embeddings_input) {
                    Ok(json_data) => json_data,
                    Err(error) => {
                        panic!("Error serializing embeddings input: {}", error);
                    }
                };

                let token_id = match self.dispatch_http_call(
                    "embeddingserver",
                    vec![
                        (":method", "POST"),
                        (":path", "/embeddings"),
                        (":authority", "embeddingserver"),
                        ("content-type", "application/json"),
                        ("x-envoy-max-retries", "3"),
                    ],
                    Some(json_data.as_bytes()),
                    vec![],
                    Duration::from_secs(5),
                ) {
                    Ok(token_id) => token_id,
                    Err(e) => {
                        panic!("Error dispatching embedding server HTTP call: {:?}", e);
                    }
                };
                info!("on_tick: dispatched HTTP call with token_id = {}", token_id);
                let embedding_request = EmbeddingRequest {
                    create_embedding_request: embeddings_input,
                    prompt_target: prompt_target.clone(),
                };
                if self
                    .callouts
                    .insert(token_id, {
                        CallContext::EmbeddingRequest(embedding_request)
                    })
                    .is_some()
                {
                    panic!(
                        "duplicate token_id={} in embedding server requests",
                        token_id
                    )
                }
                self.metrics
                    .active_http_calls
                    .record(self.callouts.len().try_into().unwrap());
            }
        }
    }

    fn embedding_request_handler(
        &mut self,
        body_size: usize,
        create_embedding_request: CreateEmbeddingRequest,
        prompt_target: PromptTarget,
    ) {
        info!("response received for CreateEmbeddingRequest");
        let body = match self.get_http_call_response_body(0, body_size) {
            Some(body) => body,
            None => {
                return;
            }
        };

        if body.is_empty() {
            return;
        }

        let (json_data, create_vector_store_points) =
            match build_qdrant_data(&body, &create_embedding_request, &prompt_target) {
                Ok(tuple) => tuple,
                Err(error) => {
                    panic!(
                        "Error building qdrant data from embedding response {}",
                        error
                    );
                }
            };

        let token_id = match self.dispatch_http_call(
            "qdrant",
            vec![
                (":method", "PUT"),
                (":path", "/collections/prompt_vector_store/points"),
                (":authority", "qdrant"),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
            ],
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        ) {
            Ok(token_id) => token_id,
            Err(e) => {
                panic!("Error dispatching qdrant HTTP call: {:?}", e);
            }
        };
        info!("on_tick: dispatched HTTP call with token_id = {}", token_id);

        if self
            .callouts
            .insert(
                token_id,
                CallContext::StoreVectorEmbeddings(create_vector_store_points),
            )
            .is_some()
        {
            panic!("duplicate token_id={} in qdrant requests", token_id)
        }

        self.metrics
            .active_http_calls
            .record(self.callouts.len().try_into().unwrap());
    }

    // TODO: @adilhafeez implement.
    fn create_vector_store_points_handler(&self, body_size: usize) {
        info!("response received for CreateVectorStorePoints");
        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            if !body.is_empty() {
                info!("response body: {:?}", String::from_utf8(body).unwrap());
            }
        }
    }
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

        self.metrics
            .active_http_calls
            .record(self.callouts.len().try_into().unwrap());
        match callout_data {
            common_types::CallContext::EmbeddingRequest(common_types::EmbeddingRequest {
                create_embedding_request,
                prompt_target,
            }) => {
                self.embedding_request_handler(body_size, create_embedding_request, prompt_target)
            }
            common_types::CallContext::StoreVectorEmbeddings(_) => {
                self.create_vector_store_points_handler(body_size)
            }
        }
    }
}

// RootContext allows the Rust code to reach into the Envoy Config
impl RootContext for FilterContext {
    fn on_configure(&mut self, _: usize) -> bool {
        if let Some(config_bytes) = self.get_plugin_configuration() {
            self.config = match serde_yaml::from_slice(&config_bytes) {
                Ok(config) => config,
                Err(error) => {
                    panic!("Failed to deserialize plugin configuration: {}", error);
                }
            };
            info!("on_configure: plugin configuration loaded");
        }
        true
    }

    fn create_http_context(&self, _context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(StreamContext { host_header: None }))
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
        self.process_prompt_targets();
        self.set_tick_period(Duration::from_secs(0));
    }
}

fn build_qdrant_data(
    embedding_data: &Vec<u8>,
    create_embedding_request: &CreateEmbeddingRequest,
    prompt_target: &PromptTarget,
) -> Result<(String, common_types::StoreVectorEmbeddingsRequest), serde_json::Error> {
    let embedding_response: CreateEmbeddingResponse = match serde_json::from_slice(embedding_data) {
        Ok(embedding_response) => embedding_response,
        Err(error) => {
            panic!("Failed to deserialize embedding response: {}", error);
        }
    };
    info!(
        "embedding_response model: {}, vector len: {}",
        embedding_response.model,
        embedding_response.data[0].embedding.len()
    );

    let mut payload: HashMap<String, String> = HashMap::new();
    payload.insert(
        "prompt-target".to_string(),
        serde_json::to_string(&prompt_target)?,
    );

    let id: Option<Digest>;
    match create_embedding_request.input {
        CreateEmbeddingRequestInput::String(ref input) => {
            id = Some(md5::compute(&input));
            payload.insert("input".to_string(), input.clone());
        }
        CreateEmbeddingRequestInput::Array(_) => todo!(),
    }

    let create_vector_store_points = common_types::StoreVectorEmbeddingsRequest {
        points: vec![common_types::VectorPoint {
            id: format!("{:x}", id.unwrap()),
            payload,
            vector: embedding_response.data[0].embedding.clone(),
        }],
    };
    let json_data = serde_json::to_string(&create_vector_store_points)?;
    info!(
        "create_vector_store_points: points length: {}",
        embedding_response.data[0].embedding.len()
    );

    Ok((json_data, create_vector_store_points))
}
