use std::str::FromStr;

use common::errors::ServerError;
use common::stats::IncrementingMetric;
use http::StatusCode;
use log::{debug, warn};
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

        let body = self
            .get_http_call_response_body(0, body_size)
            .unwrap_or(vec![]);

        let http_status = self
            .get_http_call_response_header(":status")
            .unwrap_or(StatusCode::OK.as_str().to_string());
        debug!("http call response code: {}", http_status);
        if http_status != StatusCode::OK.as_str() {
            let server_error = ServerError::Upstream {
                host: callout_context.upstream_cluster.unwrap(),
                path: callout_context.upstream_cluster_path.unwrap(),
                status: http_status.clone(),
                body: String::from_utf8(body).unwrap(),
            };
            warn!("filter received non 2xx code: {:?}", server_error);
            return self.send_server_error(
                server_error,
                Some(StatusCode::from_str(http_status.as_str()).unwrap()),
            );
        }

        debug!("http call response handler type: {:?}", callout_context.response_handler_type);
        #[cfg_attr(any(), rustfmt::skip)]
        match callout_context.response_handler_type {
            ResponseHandlerType::ArchFC => self.arch_fc_response_handler(body, callout_context),
            ResponseHandlerType::FunctionCall => self.api_call_response_handler(body, callout_context),
            ResponseHandlerType::DefaultTarget =>self.default_target_handler(body, callout_context),
        }
    }
}
