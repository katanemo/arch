use crate::consts::DEFAULT_EMBEDDING_MODEL;
use crate::ratelimit;
use crate::stats::{Gauge, RecordingMetric};
use crate::stream_context::StreamContext;
use log::info;
use md5::Digest;
use open_message_format_embeddings::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use public_types::common_types::{
    CallContext, EmbeddingRequest, StoreVectorEmbeddingsRequest, VectorPoint,
};
use public_types::configuration::{Configuration, PromptTarget};
use serde_json::to_string;
use std::collections::HashMap;
use std::time::Duration;

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

pub struct FilterContext {
    metrics: WasmMetrics,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: HashMap<u32, CallContext>,
    config: Option<Configuration>,
}

impl FilterContext {
    pub fn new() -> FilterContext {
        FilterContext {
            callouts: HashMap::new(),
            config: None,
            metrics: WasmMetrics::new(),
        }
    }

    fn process_prompt_targets(&mut self) {
        for prompt_target in &self.config.as_ref().unwrap().prompt_targets {
            for few_shot_example in &prompt_target.few_shot_examples {
                let embeddings_input = CreateEmbeddingRequest {
                    input: Box::new(CreateEmbeddingRequestInput::String(
                        few_shot_example.to_string(),
                    )),
                    model: String::from(DEFAULT_EMBEDDING_MODEL),
                    encoding_format: None,
                    dimensions: None,
                    user: None,
                };

                // TODO: Handle potential errors
                let json_data: String = to_string(&embeddings_input).unwrap();

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
                let embedding_request = EmbeddingRequest {
                    create_embedding_request: embeddings_input,
                    // Need to clone prompt target to leave config string intact.
                    prompt_target: prompt_target.clone(),
                };
                if self
                    .callouts
                    .insert(token_id, {
                        CallContext::EmbeddingRequest(embedding_request)
                    })
                    .is_some()
                {
                    panic!("duplicate token_id")
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
        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            if !body.is_empty() {
                let mut embedding_response: CreateEmbeddingResponse =
                    serde_json::from_slice(&body).unwrap();

                let mut payload: HashMap<String, String> = HashMap::new();
                payload.insert(
                    "prompt-target".to_string(),
                    to_string(&prompt_target).unwrap(),
                );
                let id: Option<Digest>;
                match *create_embedding_request.input {
                    CreateEmbeddingRequestInput::String(input) => {
                        id = Some(md5::compute(&input));
                        payload.insert("input".to_string(), input);
                    }
                    CreateEmbeddingRequestInput::Array(_) => todo!(),
                }

                let create_vector_store_points = StoreVectorEmbeddingsRequest {
                    points: vec![VectorPoint {
                        id: format!("{:x}", id.unwrap()),
                        payload,
                        vector: embedding_response.data.remove(0).embedding,
                    }],
                };
                let json_data = to_string(&create_vector_store_points).unwrap(); // Handle potential errors
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

                if self
                    .callouts
                    .insert(
                        token_id,
                        CallContext::StoreVectorEmbeddings(create_vector_store_points),
                    )
                    .is_some()
                {
                    panic!("duplicate token_id")
                }
                self.metrics
                    .active_http_calls
                    .record(self.callouts.len().try_into().unwrap());
            }
        }
    }

    fn create_vector_store_points_handler(&self, body_size: usize) {
        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            if !body.is_empty() {
                info!(
                    "response body: len {:?}",
                    String::from_utf8(body).unwrap().len()
                );
            }
        }
    }

    //TODO: run once per envoy instance, right now it runs once per worker
    fn init_vector_store(&mut self) {
        let token_id = match self.dispatch_http_call(
            "qdrant",
            vec![
                (":method", "PUT"),
                (":path", "/collections/prompt_vector_store"),
                (":authority", "qdrant"),
                ("content-type", "application/json"),
            ],
            Some(b"{ \"vectors\": { \"size\": 1024, \"distance\": \"Cosine\"}}"),
            vec![],
            Duration::from_secs(5),
        ) {
            Ok(token_id) => token_id,
            Err(e) => {
                panic!("Error dispatching HTTP call for init-vector-store: {:?}", e);
            }
        };
        if self
            .callouts
            .insert(
                token_id,
                CallContext::CreateVectorCollection("prompt_vector_store".to_string()),
            )
            .is_some()
        {
            panic!("duplicate token_id")
        }
        self.metrics
            .active_http_calls
            .record(self.callouts.len().try_into().unwrap());
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
        let callout_data = self.callouts.remove(&token_id).expect("invalid token_id");

        self.metrics
            .active_http_calls
            .record(self.callouts.len().try_into().unwrap());

        match callout_data {
            CallContext::EmbeddingRequest(EmbeddingRequest {
                create_embedding_request,
                prompt_target,
            }) => {
                self.embedding_request_handler(body_size, create_embedding_request, prompt_target)
            }
            CallContext::StoreVectorEmbeddings(_) => {
                self.create_vector_store_points_handler(body_size)
            }
            CallContext::CreateVectorCollection(_) => {
                let mut http_status_code = "Nil".to_string();
                self.get_http_call_response_headers()
                    .iter()
                    .for_each(|(k, v)| {
                        if k == ":status" {
                            http_status_code.clone_from(v);
                        }
                    });
                info!("CreateVectorCollection response: {}", http_status_code);
            }
        }
    }
}

// RootContext allows the Rust code to reach into the Envoy Config
impl RootContext for FilterContext {
    fn on_configure(&mut self, _: usize) -> bool {
        if let Some(config_bytes) = self.get_plugin_configuration() {
            self.config = serde_yaml::from_slice(&config_bytes).unwrap();

            if let Some(ratelimits_config) = self
                .config
                .as_mut()
                .and_then(|config| config.ratelimits.as_mut())
            {
                ratelimit::ratelimits(Some(std::mem::take(ratelimits_config)));
            }
        }
        true
    }

    fn create_http_context(&self, _context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(StreamContext {
            host_header: None,
            ratelimit_selector: None,
            callouts: HashMap::new(),
        }))
    }

    fn get_type(&self) -> Option<ContextType> {
        Some(ContextType::HttpContext)
    }

    fn on_vm_start(&mut self, _: usize) -> bool {
        self.set_tick_period(Duration::from_secs(1));
        true
    }

    fn on_tick(&mut self) {
        self.init_vector_store();
        self.process_prompt_targets();
        self.set_tick_period(Duration::from_secs(0));
    }
}
