use prompt_filter_context::PromptGatewayFilterContext;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

mod prompt_filter_context;
mod prompt_stream_context;

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(PromptGatewayFilterContext::new())
    });
}}
