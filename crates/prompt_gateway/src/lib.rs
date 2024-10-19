use filter_context::FilterContext;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

mod filter_context;
mod stream_context;
mod hallucination;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(FilterContext::new())
    });
}}
