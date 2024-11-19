use crate::stream_context::StreamContext;
use common::configuration::Configuration;
use common::consts::OTEL_COLLECTOR_HTTP;
use common::consts::OTEL_POST_PATH;
use common::http::CallArgs;
use common::http::Client;
use common::llm_providers::LlmProviders;
use common::ratelimit;
use common::stats::Counter;
use common::stats::Gauge;
use common::stats::Histogram;
use common::tracing::TraceData;
use log::debug;
use log::warn;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::collections::VecDeque;
use std::rc::Rc;
use std::time::Duration;

use std::sync::{Arc, Mutex};

#[derive(Copy, Clone, Debug)]
pub struct WasmMetrics {
    pub active_http_calls: Gauge,
    pub ratelimited_rq: Counter,
    pub time_to_first_token: Histogram,
    pub time_per_output_token: Histogram,
    pub tokens_per_second: Histogram,
    pub request_latency: Histogram,
    pub output_sequence_length: Histogram,
    pub input_sequence_length: Histogram,
}

impl WasmMetrics {
    fn new() -> WasmMetrics {
        WasmMetrics {
            active_http_calls: Gauge::new(String::from("active_http_calls")),
            ratelimited_rq: Counter::new(String::from("ratelimited_rq")),
            time_to_first_token: Histogram::new(String::from("time_to_first_token")),
            time_per_output_token: Histogram::new(String::from("time_per_output_token")),
            tokens_per_second: Histogram::new(String::from("tokens_per_second")),
            request_latency: Histogram::new(String::from("request_latency")),
            output_sequence_length: Histogram::new(String::from("output_sequence_length")),
            input_sequence_length: Histogram::new(String::from("input_sequence_length")),
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
    traces_queue: Arc<Mutex<VecDeque<TraceData>>>,
}

impl FilterContext {
    pub fn new() -> FilterContext {
        FilterContext {
            callouts: RefCell::new(HashMap::new()),
            metrics: Rc::new(WasmMetrics::new()),
            llm_providers: None,
            traces_queue: Arc::new(Mutex::new(VecDeque::new())),
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
            Arc::clone(&self.traces_queue),
        )))
    }

    fn get_type(&self) -> Option<ContextType> {
        Some(ContextType::HttpContext)
    }

    fn on_vm_start(&mut self, _vm_configuration_size: usize) -> bool {
        self.set_tick_period(Duration::from_secs(1));
        true
    }

    fn on_tick(&mut self) {
        let _ = self.traces_queue.try_lock().map(|mut traces_queue| {
            while let Some(trace) = traces_queue.pop_front() {
                debug!("trace received: {:?}", trace);

                let trace_str = serde_json::to_string(&trace).unwrap();
                debug!("trace: {}", trace_str);
                let call_args = CallArgs::new(
                    OTEL_COLLECTOR_HTTP,
                    OTEL_POST_PATH,
                    vec![
                        (":method", http::Method::POST.as_str()),
                        (":path", OTEL_POST_PATH),
                        (":authority", OTEL_COLLECTOR_HTTP),
                        ("content-type", "application/json"),
                    ],
                    Some(trace_str.as_bytes()),
                    vec![],
                    Duration::from_secs(60),
                );
                if let Err(error) = self.http_call(call_args, CallContext {}) {
                    warn!(
                        "failed to schedule http call to otel-collector: {:?}",
                        error
                    );
                }
            }
        });
    }
}

impl Context for FilterContext {
    fn on_http_call_response(
        &mut self,
        token_id: u32,
        _num_headers: usize,
        _body_size: usize,
        _num_trailers: usize,
    ) {
        debug!(
            "||| on_http_call_response called with token_id: {:?} |||",
            token_id
        );

        let _callout_data = self
            .callouts
            .borrow_mut()
            .remove(&token_id)
            .expect("invalid token_id");

        self.get_http_call_response_header(":status").map(|status| {
            debug!("trace response status: {:?}", status);
        });
    }
}
