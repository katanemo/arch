use common::errors::ServerError;
use common::stats::IncrementingMetric;
use proxy_wasm::traits::Context;

use crate::stream_context::{ResponseHandlerType, StreamContext};

impl Context for StreamContext {
    fn on_http_call_response(
        &mut self,
        token_id: u32,
        _num_headers: usize,
        body_size: usize,
        _num_trailers: usize,
    ) {
        let callout_context = self
            .callouts
            .get_mut()
            .remove(&token_id)
            .expect("invalid token_id");
        self.metrics.active_http_calls.increment(-1);

        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            #[cfg_attr(any(), rustfmt::skip)]
            match callout_context.response_handler_type {
                ResponseHandlerType::ArchFC => self.arch_fc_response_handler(body, callout_context),
                ResponseHandlerType::FunctionCall => self.api_call_response_handler(body, callout_context),
                ResponseHandlerType::DefaultTarget =>self.default_target_handler(body, callout_context),
            }
        } else {
            self.send_server_error(
                ServerError::LogicError(String::from("No response body in inline HTTP request")),
                None,
            );
        }
    }
}
