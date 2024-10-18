use crate::filter_context::WasmMetrics;
use common::common_types::open_ai::{
    ArchState, ChatCompletionChunkResponse, ChatCompletionsRequest, ChatCompletionsResponse,
    Message, ToolCall, ToolCallState,
};
use common::configuration::LlmProvider;
use common::consts::{
    ARCH_PROVIDER_HINT_HEADER, ARCH_ROUTING_HEADER, ARCH_STATE_HEADER, CHAT_COMPLETIONS_PATH,
    RATELIMIT_SELECTOR_HEADER_KEY, REQUEST_ID_HEADER, USER_ROLE,
};
use common::errors::ServerError;
use common::llm_providers::LlmProviders;
use common::ratelimit::Header;
use common::{ratelimit, routing, tokenizer};
use http::StatusCode;
use log::debug;
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::num::NonZero;
use std::rc::Rc;

use common::stats::IncrementingMetric;

pub struct StreamContext {
    context_id: u32,
    metrics: Rc<WasmMetrics>,
    tool_calls: Option<Vec<ToolCall>>,
    tool_call_response: Option<String>,
    arch_state: Option<Vec<ArchState>>,
    ratelimit_selector: Option<Header>,
    streaming_response: bool,
    user_prompt: Option<Message>,
    response_tokens: usize,
    is_chat_completions_request: bool,
    chat_completions_request: Option<ChatCompletionsRequest>,
    llm_providers: Rc<LlmProviders>,
    llm_provider: Option<Rc<LlmProvider>>,
    request_id: Option<String>,
}

impl StreamContext {
    pub fn new(context_id: u32, metrics: Rc<WasmMetrics>, llm_providers: Rc<LlmProviders>) -> Self {
        StreamContext {
            context_id,
            metrics,
            chat_completions_request: None,
            tool_calls: None,
            tool_call_response: None,
            arch_state: None,
            ratelimit_selector: None,
            streaming_response: false,
            user_prompt: None,
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

        if !end_of_stream {
            return Action::Pause;
        }

        let body = self
            .get_http_response_body(0, body_size)
            .expect("cant get response body");

        if self.streaming_response {
            let body_str = String::from_utf8(body).expect("body is not utf-8");
            debug!("streaming response");
            let chat_completions_data = match body_str.split_once("data: ") {
                Some((_, chat_completions_data)) => chat_completions_data,
                None => {
                    self.send_server_error(
                        ServerError::LogicError(String::from("parsing error in streaming data")),
                        None,
                    );
                    return Action::Pause;
                }
            };

            let chat_completions_chunk_response: ChatCompletionChunkResponse =
                match serde_json::from_str(chat_completions_data) {
                    Ok(de) => de,
                    Err(_) => {
                        if chat_completions_data != "[NONE]" {
                            self.send_server_error(
                                ServerError::LogicError(String::from(
                                    "error in streaming response",
                                )),
                                None,
                            );
                            return Action::Continue;
                        }
                        return Action::Continue;
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
                    Err(e) => {
                        debug!("invalid response: {}", String::from_utf8_lossy(&body));
                        self.send_server_error(ServerError::Deserialization(e), None);
                        return Action::Pause;
                    }
                };

            if chat_completions_response.usage.is_some() {
                self.response_tokens += chat_completions_response
                    .usage
                    .as_ref()
                    .unwrap()
                    .completion_tokens;
            }

            if let Some(tool_calls) = self.tool_calls.as_ref() {
                if !tool_calls.is_empty() {
                    if self.arch_state.is_none() {
                        self.arch_state = Some(Vec::new());
                    }

                    // compute sha hash from message history
                    let mut hasher = Sha256::new();
                    let prompts: Vec<String> = self
                        .chat_completions_request
                        .as_ref()
                        .unwrap()
                        .messages
                        .iter()
                        .filter(|msg| msg.role == USER_ROLE)
                        .map(|msg| msg.content.clone().unwrap())
                        .collect();
                    let prompts_merged = prompts.join("#.#");
                    hasher.update(prompts_merged.clone());
                    let hash_key = hasher.finalize();
                    // conver hash to hex string
                    let hash_key_str = format!("{:x}", hash_key);
                    debug!("hash key: {}, prompts: {}", hash_key_str, prompts_merged);

                    // create new tool call state
                    let tool_call_state = ToolCallState {
                        key: hash_key_str,
                        message: self.user_prompt.clone(),
                        tool_call: tool_calls[0].function.clone(),
                        tool_response: self.tool_call_response.clone().unwrap(),
                    };

                    // push tool call state to arch state
                    self.arch_state
                        .as_mut()
                        .unwrap()
                        .push(ArchState::ToolCall(vec![tool_call_state]));

                    let mut data: Value = serde_json::from_slice(&body).unwrap();
                    // use serde::Value to manipulate the json object and ensure that we don't lose any data
                    if let Value::Object(ref mut map) = data {
                        // serialize arch state and add to metadata
                        let arch_state_str = serde_json::to_string(&self.arch_state).unwrap();
                        debug!("arch_state: {}", arch_state_str);
                        let metadata = map
                            .entry("metadata")
                            .or_insert(Value::Object(serde_json::Map::new()));
                        metadata.as_object_mut().unwrap().insert(
                            ARCH_STATE_HEADER.to_string(),
                            serde_json::Value::String(arch_state_str),
                        );

                        let data_serialized = serde_json::to_string(&data).unwrap();
                        debug!("arch => user: {}", data_serialized);
                        self.set_http_response_body(0, body_size, data_serialized.as_bytes());
                    };
                }
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
