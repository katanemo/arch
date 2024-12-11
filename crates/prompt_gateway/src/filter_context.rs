use crate::metrics::Metrics;
use crate::stream_context::StreamContext;
use common::configuration::{Configuration, Overrides, PromptGuards, PromptTarget, Tracing};
use common::http::Client;
use common::stats::Gauge;
use log::debug;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

#[derive(Debug)]
pub struct FilterCallContext {}

#[derive(Debug)]
pub struct FilterContext {
    metrics: Rc<Metrics>,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: RefCell<HashMap<u32, FilterCallContext>>,
    overrides: Rc<Option<Overrides>>,
    system_prompt: Rc<Option<String>>,
    prompt_targets: Rc<HashMap<String, PromptTarget>>,
    prompt_guards: Rc<PromptGuards>,
    tracing: Rc<Option<Tracing>>,
}

impl FilterContext {
    pub fn new() -> FilterContext {
        FilterContext {
            callouts: RefCell::new(HashMap::new()),
            metrics: Rc::new(Metrics::new()),
            system_prompt: Rc::new(None),
            prompt_targets: Rc::new(HashMap::new()),
            overrides: Rc::new(None),
            prompt_guards: Rc::new(PromptGuards::default()),
            tracing: Rc::new(None),
        }
    }
}

impl Client for FilterContext {
    type CallContext = FilterCallContext;

    fn callouts(&self) -> &RefCell<HashMap<u32, Self::CallContext>> {
        &self.callouts
    }

    fn active_http_calls(&self) -> &Gauge {
        &self.metrics.active_http_calls
    }
}

impl Context for FilterContext {}

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
        for pt in config.prompt_targets.unwrap_or_default() {
            prompt_targets.insert(pt.name.clone(), pt.clone());
        }
        self.system_prompt = Rc::new(config.system_prompt);
        self.prompt_targets = Rc::new(prompt_targets);

        if let Some(prompt_guards) = config.prompt_guards {
            self.prompt_guards = Rc::new(prompt_guards)
        }

        self.tracing = Rc::new(config.tracing);

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
            Rc::clone(&self.system_prompt),
            Rc::clone(&self.prompt_targets),
            Rc::clone(&self.overrides),
            Rc::clone(&self.tracing),
        )))
    }

    fn get_type(&self) -> Option<ContextType> {
        Some(ContextType::HttpContext)
    }

    fn on_vm_start(&mut self, _: usize) -> bool {
        true
    }
}
