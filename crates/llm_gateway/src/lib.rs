use llm_filter_context::LlmGatewayFilterContext;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

mod llm_filter_context;
mod llm_stream_context;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(LlmGatewayFilterContext::new())
    });
}}
