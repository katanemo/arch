use crate::consts::{DEFAULT_EMBEDDING_MODEL, MODEL_SERVER_NAME};
use crate::ratelimit;
use crate::stats::{Counter, Gauge, RecordingMetric};
use crate::stream_context::StreamContext;
use log::debug;
use open_message_format_embeddings::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use public_types::common_types::EmbeddingType;
use public_types::configuration::{Configuration, Overrides, PromptTarget};
use serde_json::to_string;
use std::collections::HashMap;
use std::rc::Rc;
use std::sync::{OnceLock, RwLock};
use std::time::Duration;

#[derive(Copy, Clone, Debug)]
pub struct WasmMetrics {
    pub active_http_calls: Gauge,
    pub ratelimited_rq: Counter,
}

impl WasmMetrics {
    fn new() -> WasmMetrics {
        WasmMetrics {
            active_http_calls: Gauge::new(String::from("active_http_calls")),
            ratelimited_rq: Counter::new(String::from("ratelimited_rq")),
        }
    }
}

#[derive(Debug)]
struct CallContext {
    prompt_target: String,
    embedding_type: EmbeddingType,
}

pub type EmbeddingTypeMap = HashMap<EmbeddingType, Vec<f64>>;

#[derive(Debug)]
pub struct FilterContext {
    metrics: Rc<WasmMetrics>,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: HashMap<u32, CallContext>,
    config: Option<Configuration>,
    overrides: Rc<Option<Overrides>>,
    prompt_targets: Rc<RwLock<HashMap<String, PromptTarget>>>,
}

pub fn embeddings_store() -> &'static RwLock<HashMap<String, EmbeddingTypeMap>> {
    static EMBEDDINGS: OnceLock<RwLock<HashMap<String, EmbeddingTypeMap>>> = OnceLock::new();
    EMBEDDINGS.get_or_init(|| {
        let embeddings: HashMap<String, EmbeddingTypeMap> = HashMap::new();
        RwLock::new(embeddings)
    })
}

impl FilterContext {
    pub fn new() -> FilterContext {
        FilterContext {
            callouts: HashMap::new(),
            config: None,
            metrics: Rc::new(WasmMetrics::new()),
            prompt_targets: Rc::new(RwLock::new(HashMap::new())),
            overrides: Rc::new(None),
        }
    }

    fn process_prompt_targets(&mut self) {
        let prompt_targets = match self.prompt_targets.read() {
            Ok(prompt_targets) => prompt_targets,
            Err(e) => {
                panic!("Error reading prompt targets: {:?}", e);
            }
        };
        for values in prompt_targets.iter() {
            let prompt_target = &values.1;

            // schedule embeddings call for prompt target name
            let token_id = self.schedule_embeddings_call(prompt_target.name.clone());
            if self
                .callouts
                .insert(token_id, {
                    CallContext {
                        prompt_target: prompt_target.name.clone(),
                        embedding_type: EmbeddingType::Name,
                    }
                })
                .is_some()
            {
                panic!("duplicate token_id")
            }

            // schedule embeddings call for prompt target description
            let token_id = self.schedule_embeddings_call(prompt_target.description.clone());
            if self
                .callouts
                .insert(token_id, {
                    CallContext {
                        prompt_target: prompt_target.name.clone(),
                        embedding_type: EmbeddingType::Description,
                    }
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

    fn schedule_embeddings_call(&self, input: String) -> u32 {
        let embeddings_input = CreateEmbeddingRequest {
            input: Box::new(CreateEmbeddingRequestInput::String(input)),
            model: String::from(DEFAULT_EMBEDDING_MODEL),
            encoding_format: None,
            dimensions: None,
            user: None,
        };

        let json_data = to_string(&embeddings_input).unwrap();
        let token_id = match self.dispatch_http_call(
            MODEL_SERVER_NAME,
            vec![
                (":method", "POST"),
                (":path", "/embeddings"),
                (":authority", MODEL_SERVER_NAME),
                ("content-type", "application/json"),
                ("x-envoy-upstream-rq-timeout-ms", "60000"),
            ],
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(60),
        ) {
            Ok(token_id) => token_id,
            Err(e) => {
                panic!("Error dispatching HTTP call: {:?}", e);
            }
        };
        token_id
    }

    fn embedding_response_handler(
        &mut self,
        body_size: usize,
        embedding_type: EmbeddingType,
        prompt_target_name: String,
    ) {
        let prompt_targets = self.prompt_targets.read().unwrap();
        let prompt_target = prompt_targets.get(&prompt_target_name).unwrap();
        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            if !body.is_empty() {
                let mut embedding_response: CreateEmbeddingResponse =
                    match serde_json::from_slice(&body) {
                        Ok(response) => response,
                        Err(e) => {
                            panic!(
                                "Error deserializing embedding response. body: {:?}: {:?}",
                                String::from_utf8(body).unwrap(),
                                e
                            );
                        }
                    };

                let embeddings = embedding_response.data.remove(0).embedding;
                log::info!(
                    "Adding embeddings for prompt target name: {:?}, description: {:?}, embedding type: {:?}",
                    prompt_target.name,
                    prompt_target.description,
                    embedding_type
                );

                embeddings_store().write().unwrap().insert(
                    prompt_target.name.clone(),
                    HashMap::from([(embedding_type, embeddings)]),
                );
            }
        } else {
            panic!("No body in response");
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
        debug!("on_http_call_response called with token_id: {:?}", token_id);
        let callout_data = self.callouts.remove(&token_id).expect("invalid token_id");

        self.metrics
            .active_http_calls
            .record(self.callouts.len().try_into().unwrap());

        self.embedding_response_handler(
            body_size,
            callout_data.embedding_type,
            callout_data.prompt_target,
        )
    }
}

// RootContext allows the Rust code to reach into the Envoy Config
impl RootContext for FilterContext {
    fn on_configure(&mut self, _: usize) -> bool {
        if let Some(config_bytes) = self.get_plugin_configuration() {
            self.config = serde_yaml::from_slice(&config_bytes).unwrap();

            if let Some(overrides_config) = self
                .config
                .as_mut()
                .and_then(|config| config.overrides.as_mut())
            {
                self.overrides = Rc::new(Some(std::mem::take(overrides_config)));
            }

            for pt in self.config.clone().unwrap().prompt_targets {
                self.prompt_targets
                    .write()
                    .unwrap()
                    .insert(pt.name.clone(), pt.clone());
            }

            debug!("set configuration object");

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

    fn create_http_context(&self, context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(StreamContext::new(
            context_id,
            Rc::clone(&self.metrics),
            Rc::clone(&self.prompt_targets),
            Rc::clone(&self.overrides),
        )))
    }

    fn get_type(&self) -> Option<ContextType> {
        Some(ContextType::HttpContext)
    }

    fn on_vm_start(&mut self, _: usize) -> bool {
        self.set_tick_period(Duration::from_secs(1));
        true
    }

    fn on_tick(&mut self) {
        self.process_prompt_targets();
        self.set_tick_period(Duration::from_secs(0));
    }
}
