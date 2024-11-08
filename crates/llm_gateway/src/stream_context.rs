use crate::filter_context::WasmMetrics;
use common::common_types::open_ai::{
    ChatCompletionStreamResponseServerEvents, ChatCompletionsRequest, ChatCompletionsResponse,
    StreamOptions,
};
use common::configuration::LlmProvider;
use common::consts::{
    ARCH_PROVIDER_HINT_HEADER, ARCH_ROUTING_HEADER, CHAT_COMPLETIONS_PATH,
    RATELIMIT_SELECTOR_HEADER_KEY, REQUEST_ID_HEADER,
};
use common::errors::ServerError;
use common::llm_providers::LlmProviders;
use common::pii::obfuscate_auth_header;
use common::ratelimit::Header;
use common::{ratelimit, routing, tokenizer};
use http::StatusCode;
use log::{debug, trace, warn};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use std::num::NonZero;
use std::rc::Rc;

use common::stats::{IncrementingMetric, RecordingMetric};

use proxy_wasm::hostcalls::get_current_time;
use std::time::{Duration, SystemTime};

pub struct StreamContext {
    context_id: u32,
    metrics: Rc<WasmMetrics>,
    ratelimit_selector: Option<Header>,
    streaming_response: bool,
    response_tokens: usize,
    is_chat_completions_request: bool,
    llm_providers: Rc<LlmProviders>,
    llm_provider: Option<Rc<LlmProvider>>,
    request_id: Option<String>,
    start_time: Option<SystemTime>,
    ttft_recorded: bool,
    ttft_duration: Option<Duration>, // Store the duration directly
    first_token_processed: bool,
    last_token_time: Option<SystemTime>,
}

impl StreamContext {
    pub fn new(context_id: u32, metrics: Rc<WasmMetrics>, llm_providers: Rc<LlmProviders>) -> Self {
        StreamContext {
            context_id,
            metrics,
            ratelimit_selector: None,
            streaming_response: false,
            response_tokens: 0,
            is_chat_completions_request: false,
            llm_providers,
            llm_provider: None,
            request_id: None,
            start_time: None,
            ttft_recorded: false,
            ttft_duration: None,
            first_token_processed: false,
            last_token_time: None,
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
        // Tokenize and record token count.
        let token_count = tokenizer::token_count(model, json_string).unwrap_or(0);

        // Record the token count to metrics.
        self.metrics
            .input_sequence_length
            .record(token_count as u64);
        log::debug!("Recorded input token count: {}", token_count);

        // Check if rate limiting needs to be applied.
        if let Some(selector) = self.ratelimit_selector.take() {
            log::debug!("Rate limiting applied for model: {}", model);
            let result = ratelimit::ratelimits(None).read().unwrap().check_limit(
                model.to_owned(),
                selector,
                NonZero::new(token_count as u32).unwrap(),
            );

            match result {
                Ok(_) => log::debug!("Rate limit check passed for model: {}", model),
                Err(e) => {
                    log::debug!(
                        "Rate limit check failed for model: {} with error: {:?}",
                        model,
                        e
                    );
                    return Err(e);
                }
            }
        } else {
            log::debug!("No rate limit applied for model: {}", model);
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
            obfuscate_auth_header(&mut self.get_http_request_headers())
        );

        self.request_id = self.get_http_request_header(REQUEST_ID_HEADER);

        //start the timing for the request using get_current_time()
        match get_current_time() {
            Ok(current_time) => {
                self.start_time = Some(current_time);
                self.ttft_recorded = false;
                self.ttft_duration = None;
            }
            Err(e) => {
                warn!("Failed to get current time: {:?}", e);
                self.start_time = None;
            }
        }

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

        trace!(
            "arch => {:?}, body: {}",
            deserialized_body.model,
            chat_completion_request_str
        );

        if deserialized_body.stream {
            self.streaming_response = true;
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

        self.set_http_request_body(0, body_size, chat_completion_request_str.as_bytes());

        Action::Continue
    }

    fn on_http_response_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        debug!(
            "on_http_response_body [S={}] bytes={} end_stream={}",
            self.context_id, body_size, end_of_stream
        );

        if !self.is_chat_completions_request {
            debug!("non-chatcompletion request");
            return Action::Continue;
        }

        let body = if self.streaming_response {
            if end_of_stream && body_size == 0 {
                // All streaming responses end with bytes=0 and end_stream=true
                // Record the latency for the request
                if let Some(start_time) = self.start_time {
                    match get_current_time() {
                        Ok(current_time) => match current_time.duration_since(start_time) {
                            Ok(duration) => {
                                // Convert the duration to milliseconds
                                let duration_ms = duration.as_millis();
                                debug!("Total latency: {} milliseconds", duration_ms);
                                // Record the latency to the latency histogram
                                self.metrics.latency.record(duration_ms as u64);
                            }
                            Err(e) => {
                                warn!("SystemTime error: {:?}", e);
                            }
                        },
                        Err(e) => {
                            warn!("Failed to get current time: {:?}", e);
                        }
                    }
                }
                // Record the output sequence length
                self.metrics
                    .output_sequence_length
                    .record(self.response_tokens as u64);

                return Action::Continue;
            }
            let chunk_start = 0;
            let chunk_size = body_size;
            debug!(
                "streaming response reading, {}..{}",
                chunk_start, chunk_size
            );
            let streaming_chunk = match self.get_http_response_body(0, chunk_size) {
                Some(chunk) => chunk,
                None => {
                    warn!(
                        "response body empty, chunk_start: {}, chunk_size: {}",
                        chunk_start, chunk_size
                    );
                    return Action::Continue;
                }
            };

            if streaming_chunk.len() != chunk_size {
                warn!(
                    "chunk size mismatch: read: {} != requested: {}",
                    streaming_chunk.len(),
                    chunk_size
                );
            }
            streaming_chunk
        } else {
            debug!("non streaming response bytes read: 0:{}", body_size);
            match self.get_http_response_body(0, body_size) {
                Some(body) => body,
                None => {
                    warn!("non streaming response body empty");
                    return Action::Continue;
                }
            }
        };

        let body_utf8 = match String::from_utf8(body) {
            Ok(body_utf8) => body_utf8,
            Err(e) => {
                debug!("could not convert to utf8: {}", e);
                return Action::Continue;
            }
        };

        if self.streaming_response {
            let chat_completions_chunk_response_events =
                match ChatCompletionStreamResponseServerEvents::try_from(body_utf8.as_str()) {
                    Ok(response) => response,
                    Err(e) => {
                        debug!(
                            "invalid streaming response: body str: {}, {:?}",
                            body_utf8, e
                        );
                        return Action::Continue;
                    }
                };

            if chat_completions_chunk_response_events.events.is_empty() {
                debug!("empty streaming response");
                return Action::Continue;
            }

            let mut model = chat_completions_chunk_response_events
                .events
                .first()
                .unwrap()
                .model
                .clone();
            let tokens_str = chat_completions_chunk_response_events.to_string();
            //HACK: add support for tokenizing mistral and other models
            //filed issue https://github.com/katanemo/arch/issues/222
            if model.as_ref().unwrap().starts_with("mistral")
                || model.as_ref().unwrap().starts_with("ministral")
            {
                model = Some("gpt-4".to_string());
            }
            let token_count =
                match tokenizer::token_count(model.as_ref().unwrap().as_str(), tokens_str.as_str())
                {
                    Ok(token_count) => token_count,
                    Err(e) => {
                        debug!("could not get token count: {:?}", e);
                        return Action::Continue;
                    }
                };
            self.response_tokens += token_count;

            // Compute TTFT if not already recorded
            if !self.ttft_recorded {
                if let Some(start_time) = self.start_time {
                    match get_current_time() {
                        Ok(current_time) => match current_time.duration_since(start_time) {
                            Ok(duration) => {
                                let duration_ms = duration.as_millis();
                                debug!("Time to First Token (TTFT): {} milliseconds", duration_ms);
                                self.ttft_duration = Some(duration);
                                self.metrics.time_to_first_token.record(duration_ms as u64);
                            }
                            Err(e) => {
                                warn!("SystemTime error: {:?}", e);
                            }
                        },
                        Err(e) => {
                            warn!("Failed to get current time: {:?}", e);
                        }
                    }
                    self.ttft_recorded = true;
                } else {
                    warn!("Start time was not recorded");
                }
            }
            // Check if first token was not processed yet, and if there are tokens in the response.
            // If so, set the last_token_time to now and set first_token_processed to true
            if !self.first_token_processed && token_count > 0 {
                self.first_token_processed = true;
                // Set last_token_time to now
                match get_current_time() {
                    Ok(current_time) => {
                        self.last_token_time = Some(current_time);
                    }
                    Err(e) => {
                        warn!("Failed to get current time: {:?}", e);
                    }
                }
            } else if self.first_token_processed && token_count > 0 {
                if let Some(last_token_time) = self.last_token_time {
                    match get_current_time() {
                        Ok(current_time) => {
                            // record the time for the current output token and calculate the time per output token
                            match current_time.duration_since(last_token_time) {
                                Ok(duration) => {
                                    // Convert the duration to milliseconds
                                    let duration_ms = duration.as_millis();
                                    debug!(
                                        "Time for Current Output Token: {} milliseconds",
                                        duration_ms as u64 / token_count as u64
                                    );
                                    // Record TPOT metric for historgram
                                    self.metrics
                                        .time_per_output_token
                                        .record((duration_ms as u64) / (token_count as u64));
                                }
                                Err(e) => {
                                    warn!("SystemTime error: {:?}", e);
                                }
                            }
                            // Set last_token_time to now
                            self.last_token_time = Some(current_time);
                        }
                        Err(e) => {
                            warn!("Failed to get current time: {:?}", e);
                        }
                    }
                }
            }
        } else {
            debug!("non streaming response");
            let chat_completions_response: ChatCompletionsResponse =
                match serde_json::from_str(body_utf8.as_str()) {
                    Ok(de) => de,
                    Err(_e) => {
                        debug!("invalid response: {}", body_utf8);
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

            // // Compute TFT if not already recorded
            // if !self.ttft_recorded {
            //     if let Some(start_time) = self.start_time {
            //         match get_current_time() {
            //             Ok(current_time) => match current_time.duration_since(start_time) {
            //                 Ok(duration) => {
            //                     let duration_ms = duration.as_millis();
            //                     debug!("Time to First Token (TFT): {} milliseconds", duration_ms);
            //                     self.ttft_duration = Some(duration);
            //                     self.metrics.time_to_first_token.record(duration_ms as u64);
            //                 }
            //                 Err(e) => {
            //                     warn!("SystemTime error: {:?}", e);
            //                 }
            //             },
            //             Err(e) => {
            //                 warn!("Failed to get current time: {:?}", e);
            //             }
            //         }
            //         self.ttft_recorded = true;
            //     } else {
            //         warn!("Start time was not recorded");
            //     }
            // }
        }

        debug!(
            "recv [S={}] total_tokens={} end_stream={}",
            self.context_id, self.response_tokens, end_of_stream
        );

        Action::Continue
    }
}

impl Context for StreamContext {}
