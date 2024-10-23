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

        /*
        state transition

        graph LR

        on_http_request_body --> prompt received
        prompt received --> get embeddings & arch guard
        arch guard --> get embeddings
        get embeddings --> zeroshot intent

        ┌──────────────────────┐   ┌─────────────────┐   ┌────────────────┐   ┌─────────────────┐
        │                      │   │                 │   │                │   │                 │
        │ on_http_request_body ├──►│ prompt received ├──►│ get embeddings ├──►│ zeroshot intent │
        │                      │   │                 │   │                │   │                 │
        └──────────────────────┘   └────────┬────────┘   └────────────────┘   └─────────────────┘
                                          │                     ▲
                                          │                     │
                                          │                     │
                                          │            ┌────────┴───────┐
                                          │            │                │
                                          └───────────►│   arch guard   │
                                                       │                │
                                                       └────────────────┘


        continue from zeroshot intent

        graph LR

        zeroshot intent --> arch_fc
        zeroshot intent --> default prompt target
        arch_fc --> developer api call & hallucination check
        hallucination check --> parameter gathering & developer api call
        developer api call --> resume request to llm


        ┌─────────────────┐   ┌───────────────────────┐   ┌─────────────────────┐   ┌───────────────────────┐
        │                 │   │                       │   │                     │   │                       │
        │ zeroshot intent ├──►│        arch_fc        ├──►│  developer api call ├──►│ resume request to llm │
        │                 │   │                       │   │                     │   │                       │
        └────────┬────────┘   └───────────┬───────────┘   └─────────────────────┘   └───────────────────────┘
               │                        │                          ▲
               │                        └─────────────┐            │
               │                                      │            │
               │            ┌───────────────────────┐ │ ┌──────────┴──────────┐   ┌───────────────────────┐
               │            │                       │ │ │                     │   │                       │
               └───────────►│ default prompt target │ └▲│ hallucination check ├──►│  parameter gathering  │
                            │                       │   │                     │   │                       │
                            └───────────────────────┘   └─────────────────────┘   └───────────────────────┘


        using https://mermaid-ascii.art/
        */

        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            #[cfg_attr(any(), rustfmt::skip)]
            match callout_context.response_handler_type {
                ResponseHandlerType::ArchGuard => self.arch_guard_handler(body, callout_context),
                ResponseHandlerType::Embeddings => self.embeddings_handler(body, callout_context),
                ResponseHandlerType::ZeroShotIntent => self.zero_shot_intent_detection_resp_handler(body, callout_context),
                ResponseHandlerType::ArchFC => self.arch_fc_response_handler(body, callout_context),
                ResponseHandlerType::Hallucination => self.hallucination_classification_resp_handler(body, callout_context),
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
