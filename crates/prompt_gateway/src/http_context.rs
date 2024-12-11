use crate::stream_context::{ResponseHandlerType, StreamCallContext, StreamContext};
use common::{
    api::open_ai::{
        self, ArchState, ChatCompletionStreamResponse, ChatCompletionTool, ChatCompletionsRequest,
    },
    consts::{
        ARCH_FC_MODEL_NAME, ARCH_INTERNAL_CLUSTER_NAME, ARCH_STATE_HEADER,
        ARCH_UPSTREAM_HOST_HEADER, ASSISTANT_ROLE, CHAT_COMPLETIONS_PATH, HEALTHZ_PATH,
        MODEL_SERVER_NAME, REQUEST_ID_HEADER, TOOL_ROLE, TRACE_PARENT_HEADER, USER_ROLE,
    },
    errors::ServerError,
    http::{CallArgs, Client},
    pii::obfuscate_auth_header,
};
use http::StatusCode;
use log::{debug, trace, warn};
use proxy_wasm::{traits::HttpContext, types::Action};
use serde_json::Value;
use std::{
    collections::HashMap,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for StreamContext {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        // Remove the Content-Length header because further body manipulations in the gateway logic will invalidate it.
        // Server's generally throw away requests whose body length do not match the Content-Length header.
        // However, a missing Content-Length header is not grounds for bad requests given that intermediary hops could
        // manipulate the body in benign ways e.g., compression.
        self.set_http_request_header("content-length", None);

        let request_path = self.get_http_request_header(":path").unwrap_or_default();
        if request_path == HEALTHZ_PATH {
            self.send_http_response(200, vec![], None);
            return Action::Continue;
        }

        self.is_chat_completions_request = request_path == CHAT_COMPLETIONS_PATH;

        trace!(
            "on_http_request_headers S[{}] req_headers={:?}",
            self.context_id,
            obfuscate_auth_header(&mut self.get_http_request_headers())
        );

        self.request_id = self.get_http_request_header(REQUEST_ID_HEADER);
        self.traceparent = self.get_http_request_header(TRACE_PARENT_HEADER);
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

        self.request_body_size = body_size;

        trace!(
            "on_http_request_body S[{}] body_size={}",
            self.context_id,
            body_size
        );

        let body_bytes = match self.get_http_request_body(0, body_size) {
            Some(body_bytes) => body_bytes,
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

        debug!(
            "developer => archgw: {}",
            String::from_utf8_lossy(&body_bytes)
        );

        // Deserialize body into spec.
        // Currently OpenAI API.
        let deserialized_body: ChatCompletionsRequest = match serde_json::from_slice(&body_bytes) {
            Ok(deserialized) => deserialized,
            Err(e) => {
                self.send_server_error(
                    ServerError::Deserialization(e),
                    Some(StatusCode::BAD_REQUEST),
                );
                return Action::Pause;
            }
        };

        self.arch_state = match deserialized_body.metadata {
            Some(ref metadata) => {
                if metadata.contains_key(ARCH_STATE_HEADER) {
                    let arch_state_str = metadata[ARCH_STATE_HEADER].clone();
                    let arch_state: Vec<ArchState> = serde_json::from_str(&arch_state_str).unwrap();
                    Some(arch_state)
                } else {
                    None
                }
            }
            None => None,
        };

        self.streaming_response = deserialized_body.stream;

        let last_user_prompt = match deserialized_body
            .messages
            .iter()
            .filter(|msg| msg.role == USER_ROLE)
            .last()
        {
            Some(content) => content,
            None => {
                warn!("No messages in the request body");
                return Action::Continue;
            }
        };

        self.user_prompt = Some(last_user_prompt.clone());

        // convert prompt targets to ChatCompletionTool
        let tool_calls: Vec<ChatCompletionTool> = self
            .prompt_targets
            .iter()
            .map(|(_, pt)| pt.into())
            .collect();

        let arch_fc_chat_completion_request = ChatCompletionsRequest {
            messages: deserialized_body.messages.clone(),
            metadata: deserialized_body.metadata.clone(),
            stream: deserialized_body.stream,
            model: "--".to_string(),
            stream_options: deserialized_body.stream_options.clone(),
            tools: Some(tool_calls),
        };

        self.chat_completions_request = Some(deserialized_body);

        let json_data = match serde_json::to_string(&arch_fc_chat_completion_request) {
            Ok(json_data) => json_data,
            Err(error) => {
                self.send_server_error(ServerError::Serialization(error), None);
                return Action::Pause;
            }
        };

        debug!("archgw => archfc: {}", json_data);

        let mut headers = vec![
            (ARCH_UPSTREAM_HOST_HEADER, MODEL_SERVER_NAME),
            (":method", "POST"),
            (":path", "/function_calling"),
            ("content-type", "application/json"),
            (":authority", MODEL_SERVER_NAME),
        ];

        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
        }

        if self.traceparent.is_some() {
            headers.push((TRACE_PARENT_HEADER, self.traceparent.as_ref().unwrap()));
        }

        let call_args = CallArgs::new(
            ARCH_INTERNAL_CLUSTER_NAME,
            "/function_calling",
            headers,
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );

        let call_context = StreamCallContext {
            response_handler_type: ResponseHandlerType::ArchFC,
            user_message: self.user_prompt.as_ref().unwrap().content.clone(),
            prompt_target_name: None,
            request_body: self.chat_completions_request.as_ref().unwrap().clone(),
            similarity_scores: None,
            upstream_cluster: None,
            upstream_cluster_path: None,
        };

        if let Err(e) = self.http_call(call_args, call_context) {
            debug!("http_call failed: {:?}", e);
            self.send_server_error(ServerError::HttpDispatch(e), None);
        }

        Action::Pause
    }

    fn on_http_response_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        trace!(
            "on_http_response_headers recv [S={}] headers={:?}",
            self.context_id,
            self.get_http_response_headers()
        );
        // delete content-lenght header let envoy calculate it, because we modify the response body
        // that would result in a different content-length
        self.set_http_response_header("content-length", None);
        Action::Continue
    }

    fn on_http_response_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        trace!(
            "on_http_response_body: recv [S={}] bytes={} end_stream={}",
            self.context_id,
            body_size,
            end_of_stream
        );

        if !self.is_chat_completions_request {
            debug!("non-gpt request");
            return Action::Continue;
        }

        if self.time_to_first_token.is_none() {
            self.time_to_first_token = Some(
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
            );
        }

        if end_of_stream && body_size == 0 {
            return Action::Continue;
        }

        let body = if self.streaming_response {
            let streaming_chunk = match self.get_http_response_body(0, body_size) {
                Some(chunk) => chunk,
                None => {
                    warn!(
                        "response body empty, chunk_start: {}, chunk_size: {}",
                        0, body_size
                    );
                    return Action::Continue;
                }
            };

            if streaming_chunk.len() != body_size {
                warn!(
                    "chunk size mismatch: read: {} != requested: {}",
                    streaming_chunk.len(),
                    body_size
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
            trace!("streaming response");

            if self.tool_calls.is_some() && !self.tool_calls.as_ref().unwrap().is_empty() {
                let chunks = vec![
                    ChatCompletionStreamResponse::new(
                        None,
                        Some(ASSISTANT_ROLE.to_string()),
                        Some(ARCH_FC_MODEL_NAME.to_string()),
                        self.tool_calls.to_owned(),
                    ),
                    ChatCompletionStreamResponse::new(
                        self.tool_call_response.clone(),
                        Some(TOOL_ROLE.to_string()),
                        Some(ARCH_FC_MODEL_NAME.to_string()),
                        None,
                    ),
                ];

                let mut response_str = open_ai::to_server_events(chunks);
                // append the original response from the model to the stream
                response_str.push_str(&body_utf8);
                self.set_http_response_body(0, body_size, response_str.as_bytes());
                self.tool_calls = None;
            }
        } else if let Some(tool_calls) = self.tool_calls.as_ref() {
            if !tool_calls.is_empty() {
                if self.arch_state.is_none() {
                    self.arch_state = Some(Vec::new());
                }

                let mut data = match serde_json::from_str(&body_utf8) {
                    Ok(data) => data,
                    Err(e) => {
                        warn!("could not deserialize response: {}", e);
                        self.send_server_error(ServerError::Deserialization(e), None);
                        return Action::Pause;
                    }
                };
                // use serde::Value to manipulate the json object and ensure that we don't lose any data
                if let Value::Object(ref mut map) = data {
                    // serialize arch state and add to metadata
                    let metadata = map
                        .entry("metadata")
                        .or_insert(Value::Object(serde_json::Map::new()));
                    if metadata == &Value::Null {
                        *metadata = Value::Object(serde_json::Map::new());
                    }

                    let fc_messages = vec![
                        self.generate_toll_call_message(),
                        self.generate_api_response_message(),
                    ];
                    let fc_messages_str = serde_json::to_string(&fc_messages).unwrap();
                    let arch_state = HashMap::from([("messages".to_string(), fc_messages_str)]);
                    let arch_state_str = serde_json::to_string(&arch_state).unwrap();
                    metadata.as_object_mut().unwrap().insert(
                        ARCH_STATE_HEADER.to_string(),
                        serde_json::Value::String(arch_state_str),
                    );
                    let data_serialized = serde_json::to_string(&data).unwrap();
                    debug!("archgw <= developer: {}", data_serialized);
                    self.set_http_response_body(0, body_size, data_serialized.as_bytes());
                };
            }
        }

        trace!("recv [S={}] end_stream={}", self.context_id, end_of_stream);

        Action::Continue
    }
}
