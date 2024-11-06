use crate::stream_context::StreamContext;
use common::configuration::Configuration;
use common::http::Client;
use common::llm_providers::LlmProviders;
use common::ratelimit;
use common::stats::Counter;
use common::stats::Gauge;
use common::stats::Histogram;
use log::debug;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

#[derive(Copy, Clone, Debug)]
pub struct WasmMetrics {
    pub active_http_calls: Gauge,
    pub ratelimited_rq: Counter,
    pub time_to_first_token: Histogram,
}

impl WasmMetrics {
    fn new() -> WasmMetrics {
        WasmMetrics {
            active_http_calls: Gauge::new(String::from("active_http_calls")),
            ratelimited_rq: Counter::new(String::from("ratelimited_rq")),
            time_to_first_token: Histogram::new(String::from("time_to_first_token")),
        }
    }
}

#[derive(Debug)]
pub struct CallContext {}

#[derive(Debug)]
pub struct FilterContext {
    metrics: Rc<WasmMetrics>,
    // callouts stores token_id to request mapping that we use during #on_http_call_response to match the response to the request.
    callouts: RefCell<HashMap<u32, CallContext>>,
    llm_providers: Option<Rc<LlmProviders>>,
}

impl FilterContext {
    pub fn new() -> FilterContext {
        FilterContext {
            callouts: RefCell::new(HashMap::new()),
            metrics: Rc::new(WasmMetrics::new()),
            llm_providers: None,
        }
    }
}

impl Client for FilterContext {
    type CallContext = CallContext;

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

        ratelimit::ratelimits(Some(config.ratelimits.unwrap_or_default()));

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
}
