use crate::filter_context::WasmMetrics;
use common::common_types::open_ai::{
    ChatCompletionChunkResponse, ChatCompletionsRequest, ChatCompletionsResponse, StreamOptions,
};
use common::configuration::LlmProvider;
use common::consts::{
    ARCH_PROVIDER_HINT_HEADER, ARCH_ROUTING_HEADER, CHAT_COMPLETIONS_PATH,
    RATELIMIT_SELECTOR_HEADER_KEY, REQUEST_ID_HEADER,
};
use common::errors::ServerError;
use common::llm_providers::LlmProviders;
use common::ratelimit::Header;
use common::{ratelimit, routing, tokenizer};
use http::StatusCode;
use log::debug;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use std::num::NonZero;
use std::rc::Rc;

use common::stats::IncrementingMetric;

pub struct StreamContext {
    context_id: u32,
    metrics: Rc<WasmMetrics>,
    ratelimit_selector: Option<Header>,
    streaming_response: Option<StreamingResponse>,
    response_tokens: usize,
    is_chat_completions_request: bool,
    llm_providers: Rc<LlmProviders>,
    llm_provider: Option<Rc<LlmProvider>>,
    request_id: Option<String>,
}

struct StreamingResponse {
    bytes_read: usize,
}

impl StreamingResponse {
    fn new() -> Self {
        StreamingResponse { bytes_read: 0 }
    }
}

impl StreamContext {
    pub fn new(context_id: u32, metrics: Rc<WasmMetrics>, llm_providers: Rc<LlmProviders>) -> Self {
        StreamContext {
            context_id,
            metrics,
            ratelimit_selector: None,
            streaming_response: None,
            response_tokens: 0,
            is_chat_completions_request: false,
            llm_providers,
            llm_provider: None,
            request_id: None,
        }
    }
    fn llm_provider(&self) -> &LlmProvider {
        self.llm_provider
            .as_ref()
            .expect("the provider should be set when asked for it")
    }

    fn select_llm_provider(&mut self) {
        let provider_hint = self
            .get_http_request_header(ARCH_PROVIDER_HINT_HEADER)
            .map(|provider_name| provider_name.into());

        debug!("llm provider hint: {:?}", provider_hint);
        self.llm_provider = Some(routing::get_llm_provider(
            &self.llm_providers,
            provider_hint,
        ));
        debug!("selected llm: {}", self.llm_provider.as_ref().unwrap().name);
    }

    fn modify_auth_headers(&mut self) -> Result<(), ServerError> {
        let llm_provider_api_key_value =
            self.llm_provider()
                .access_key
                .as_ref()
                .ok_or(ServerError::BadRequest {
                    why: format!(
                        "No access key configured for selected LLM Provider \"{}\"",
                        self.llm_provider()
                    ),
                })?;

        let authorization_header_value = format!("Bearer {}", llm_provider_api_key_value);

        self.set_http_request_header("Authorization", Some(&authorization_header_value));

        Ok(())
    }

    fn delete_content_length_header(&mut self) {
        // Remove the Content-Length header because further body manipulations in the gateway logic will invalidate it.
        // Server's generally throw away requests whose body length do not match the Content-Length header.
        // However, a missing Content-Length header is not grounds for bad requests given that intermediary hops could
        // manipulate the body in benign ways e.g., compression.
        self.set_http_request_header("content-length", None);
    }

    fn save_ratelimit_header(&mut self) {
        self.ratelimit_selector = self
            .get_http_request_header(RATELIMIT_SELECTOR_HEADER_KEY)
            .and_then(|key| {
                self.get_http_request_header(&key)
                    .map(|value| Header { key, value })
            });
    }

    fn send_server_error(&self, error: ServerError, override_status_code: Option<StatusCode>) {
        debug!("server error occurred: {}", error);
        self.send_http_response(
            override_status_code
                .unwrap_or(StatusCode::INTERNAL_SERVER_ERROR)
                .as_u16()
                .into(),
            vec![],
            Some(format!("{error}").as_bytes()),
        );
    }

    fn enforce_ratelimits(
        &mut self,
        model: &str,
        json_string: &str,
    ) -> Result<(), ratelimit::Error> {
        if let Some(selector) = self.ratelimit_selector.take() {
            // Tokenize and Ratelimit.
            if let Ok(token_count) = tokenizer::token_count(model, json_string) {
                ratelimit::ratelimits(None).read().unwrap().check_limit(
                    model.to_owned(),
                    selector,
                    NonZero::new(token_count as u32).unwrap(),
                )?;
            }
        }
        Ok(())
    }
}

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for StreamContext {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        self.select_llm_provider();
        self.add_http_request_header(ARCH_ROUTING_HEADER, &self.llm_provider().name);

        if let Err(error) = self.modify_auth_headers() {
            self.send_server_error(error, Some(StatusCode::BAD_REQUEST));
        }
        self.delete_content_length_header();
        self.save_ratelimit_header();

        self.is_chat_completions_request =
            self.get_http_request_header(":path").unwrap_or_default() == CHAT_COMPLETIONS_PATH;

        debug!(
            "on_http_request_headers S[{}] req_headers={:?}",
            self.context_id,
            self.get_http_request_headers()
        );

        self.request_id = self.get_http_request_header(REQUEST_ID_HEADER);

        Action::Continue
    }

    fn on_http_request_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        // Let the client send the gateway all the data before sending to the LLM_provider.
        // TODO: consider a streaming API.
        if !end_of_stream {
            return Action::Pause;
        }

        if body_size == 0 {
            return Action::Continue;
        }

        // Deserialize body into spec.
        // Currently OpenAI API.
        let mut deserialized_body: ChatCompletionsRequest =
            match self.get_http_request_body(0, body_size) {
                Some(body_bytes) => match serde_json::from_slice(&body_bytes) {
                    Ok(deserialized) => deserialized,
                    Err(e) => {
                        self.send_server_error(
                            ServerError::Deserialization(e),
                            Some(StatusCode::BAD_REQUEST),
                        );
                        return Action::Pause;
                    }
                },
                None => {
                    self.send_server_error(
                        ServerError::LogicError(format!(
                            "Failed to obtain body bytes even though body_size is {}",
                            body_size
                        )),
                        None,
                    );
                    return Action::Pause;
                }
            };

        // remove metadata from the request body
        deserialized_body.metadata = None;
        // delete model key from message array
        for message in deserialized_body.messages.iter_mut() {
            message.model = None;
        }

        // override model name from the llm provider
        deserialized_body
            .model
            .clone_from(&self.llm_provider.as_ref().unwrap().model);
        let chat_completion_request_str = serde_json::to_string(&deserialized_body).unwrap();

        if deserialized_body.stream {
            self.streaming_response = Some(StreamingResponse::new());
        }
        if deserialized_body.stream && deserialized_body.stream_options.is_none() {
            deserialized_body.stream_options = Some(StreamOptions {
                include_usage: true,
            });
        }

        // enforce ratelimits on ingress
        if let Err(e) =
            self.enforce_ratelimits(&deserialized_body.model, &chat_completion_request_str)
        {
            self.send_server_error(
                ServerError::ExceededRatelimit(e),
                Some(StatusCode::TOO_MANY_REQUESTS),
            );
            self.metrics.ratelimited_rq.increment(1);
            return Action::Continue;
        }

        debug!(
            "arch => {:?}, body: {}",
            deserialized_body.model, chat_completion_request_str
        );
        self.set_http_request_body(0, body_size, chat_completion_request_str.as_bytes());

        Action::Continue
    }

    fn on_http_response_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        debug!(
            "recv [S={}] bytes={} end_stream={}",
            self.context_id, body_size, end_of_stream
        );

        if !self.is_chat_completions_request {
            if let Some(body_str) = self
                .get_http_response_body(0, body_size)
                .and_then(|bytes| String::from_utf8(bytes).ok())
            {
                debug!("recv [S={}] body_str={}", self.context_id, body_str);
            }
            return Action::Continue;
        }

        if !end_of_stream && self.streaming_response.is_none() {
            return Action::Pause;
        }

        let body = match self.streaming_response.take() {
            Some(mut streaming_response) => {
                let streaming_chunk = self
                    .get_http_response_body(streaming_response.bytes_read, body_size)
                    .expect("cant get response body");
                streaming_response.bytes_read += body_size;
                // n.b: this funky take and replace of the streaming_response struct is done to appease the borrow
                // checker which wouldn't let us take a mut ref of streaming_response, and then a ref for
                // `get_http_response_body`
                self.streaming_response = Some(streaming_response);
                streaming_chunk
            }
            None => self
                .get_http_response_body(0, body_size)
                .expect("cant get response body"),
        };

        if self.streaming_response.is_some() {
            let body_str = String::from_utf8(body).expect("body is not utf-8");
            debug!("streaming response");

            let chat_completions_chunk_response =
                match ChatCompletionChunkResponse::try_from(body_str.as_str()) {
                    Ok(response) => response,
                    Err(e) => {
                        self.send_server_error(e.into(), None);
                        return Action::Pause;
                    }
                };

            if let Some(content) = chat_completions_chunk_response
                .choices
                .first()
                .unwrap()
                .delta
                .content
                .as_ref()
            {
                let model = &chat_completions_chunk_response.model;
                let token_count = tokenizer::token_count(model, content).unwrap_or(0);
                self.response_tokens += token_count;
            }
        } else {
            debug!("non streaming response");
            let chat_completions_response: ChatCompletionsResponse =
                match serde_json::from_slice(&body) {
                    Ok(de) => de,
                    Err(_e) => {
                        debug!("invalid response: {}", String::from_utf8_lossy(&body));
                        return Action::Continue;
                    }
                };

            if chat_completions_response.usage.is_some() {
                self.response_tokens += chat_completions_response
                    .usage
                    .as_ref()
                    .unwrap()
                    .completion_tokens;
            }
        }

        debug!(
            "recv [S={}] total_tokens={} end_stream={}",
            self.context_id, self.response_tokens, end_of_stream
        );

        // TODO:: ratelimit based on response tokens.
        Action::Continue
    }
}

impl Context for StreamContext {}
