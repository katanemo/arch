use std::collections::HashMap;
use std::sync::OnceLock;

use filter_context::FilterContext;
use log::error;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

mod common_types;
mod configuration;
mod consts;
mod filter_context;
mod stats;
mod stream_context;

fn ratelimits() -> &'static HashMap<u32, u32> {
    static HASHMAP: OnceLock<HashMap<u32, u32>> = OnceLock::new();
    HASHMAP.get_or_init(|| HashMap::new())
}

proxy_wasm::main! {{
    proxy_wasm::set_log_level(LogLevel::Trace);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(FilterContext::new())
    });

    error!("Only one ratelimit! {:p}", ratelimits());
}}
