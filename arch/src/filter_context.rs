use crate::consts::{DEFAULT_EMBEDDING_MODEL, MODEL_SERVER_NAME};
use crate::http::{CallArgs, CallContext, Client};
use crate::llm_providers::LlmProviders;
use crate::ratelimit;
use crate::stats::{Counter, Gauge, RecordingMetric};
use crate::stream_context::StreamContext;
use log::debug;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use public_types::common_types::EmbeddingType;
use public_types::configuration::{Configuration, Overrides, PromptGuards, PromptTarget};
use public_types::embeddings::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
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
pub struct FilterCallContext {
    pub prompt_target: String,
    pub embedding_type: EmbeddingType,
}

#[derive(Debug)]
pub struct FilterContext {
    metrics: Rc<WasmMetrics>,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: HashMap<u32, FilterCallContext>,
    overrides: Rc<Option<Overrides>>,
    prompt_targets: Rc<HashMap<String, PromptTarget>>,
    prompt_guards: Rc<PromptGuards>,
    llm_providers: Option<Rc<LlmProviders>>,
}

impl FilterContext {
    pub fn new() -> FilterContext {
        FilterContext {
            callouts: HashMap::new(),
            metrics: Rc::new(WasmMetrics::new()),
            prompt_targets: Rc::new(HashMap::new()),
            overrides: Rc::new(None),
            prompt_guards: Rc::new(PromptGuards::default()),
            llm_providers: None,
        }
    }

    pub fn prompt_targets(&self) -> Rc<HashMap<String, PromptTarget>> {
        Rc::clone(&self.prompt_targets)
    }
}

impl Client for FilterContext {
    type CallContext = FilterCallContext;

    fn add_call_context(&mut self, id: u32, call_context: Self::CallContext) {
        if let Some(_) = self.callouts.insert(id, call_context) {
            panic!("Duplicate http call with id={}", id);
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
        debug!(
            "filter_context: on_http_call_response called with token_id: {:?}",
            token_id
        );
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
        let config_bytes = self
            .get_plugin_configuration()
            .expect("Arch config cannot be empty");

        let config: Configuration = match serde_yaml::from_slice(&config_bytes) {
            Ok(config) => config,
            Err(err) => panic!("Invalid arch config \"{:?}\"", err),
        };

        self.overrides = Rc::new(config.overrides);

        let mut prompt_targets = HashMap::new();
        for pt in config.prompt_targets {
            prompt_targets.insert(pt.name.clone(), pt.clone());
        }
        self.prompt_targets = Rc::new(prompt_targets);

        ratelimit::ratelimits(config.ratelimits);

        if let Some(prompt_guards) = config.prompt_guards {
            self.prompt_guards = Rc::new(prompt_guards)
        }

        match config.llm_providers.try_into() {
            Ok(llm_providers) => self.llm_providers = Some(Rc::new(llm_providers)),
            Err(err) => panic!("{err}"),
        }

        true
    }

    fn create_http_context(&self, context_id: u32) -> Option<Box<dyn HttpContext>> {
        debug!(
            "||| create_http_context called with context_id: {:?} |||",
            context_id
        );
        Some(Box::new(StreamContext::new(
            context_id,
            Rc::clone(&self.metrics),
            Rc::clone(&self.prompt_targets),
            Rc::clone(&self.prompt_guards),
            Rc::clone(&self.overrides),
            Rc::clone(
                self.llm_providers
                    .as_ref()
                    .expect("LLM Providers must exist when Streams are being created"),
            ),
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
