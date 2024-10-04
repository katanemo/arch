use filter_context::FilterContext;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

mod consts;
mod filter_context;
mod llm_providers;
mod ratelimit;
mod routing;
mod stats;
mod stream_context;
mod tokenizer;
mod utils;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(FilterContext::new())
    });
}}
