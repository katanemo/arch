use std::{collections::HashMap, time::Duration};

use common::{
    common_types::{
        open_ai::{
            ArchState, ChatCompletionsRequest, ChatCompletionsResponse, Message, StreamOptions,
        },
        PromptGuardRequest, PromptGuardTask,
    },
    consts::{
        ARCH_FC_MODEL_NAME, ARCH_INTERNAL_CLUSTER_NAME, ARCH_STATE_HEADER,
        ARCH_UPSTREAM_HOST_HEADER, ASSISTANT_ROLE, CHAT_COMPLETIONS_PATH, GUARD_INTERNAL_HOST,
        REQUEST_ID_HEADER, TOOL_ROLE, USER_ROLE,
    },
    errors::ServerError,
    http::{CallArgs, Client},
};
use http::StatusCode;
use log::{debug, warn};
use proxy_wasm::{traits::HttpContext, types::Action};
use serde_json::Value;

use crate::stream_context::{ResponseHandlerType, StreamCallContext, StreamContext};

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

        self.request_body_size = body_size;

        debug!(
            "on_http_request_body S[{}] body_size={}",
            self.context_id, body_size
        );

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
        if deserialized_body.stream && deserialized_body.stream_options.is_none() {
            deserialized_body.stream_options = Some(StreamOptions {
                include_usage: true,
            });
        }

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

        let user_message_str = self.user_prompt.as_ref().unwrap().content.clone();

        let prompt_guard_jailbreak_task = self
            .prompt_guards
            .input_guards
            .contains_key(&common::configuration::GuardType::Jailbreak);

        self.chat_completions_request = Some(deserialized_body);

        if !prompt_guard_jailbreak_task {
            debug!("Missing input guard. Making inline call to retrieve embeddings");
            let callout_context = StreamCallContext {
                response_handler_type: ResponseHandlerType::ArchGuard,
                user_message: user_message_str.clone(),
                prompt_target_name: None,
                request_body: self.chat_completions_request.as_ref().unwrap().clone(),
                similarity_scores: None,
                upstream_cluster: None,
                upstream_cluster_path: None,
                tool_calls: None,
            };
            self.get_embeddings(callout_context);
            return Action::Pause;
        }

        let get_prompt_guards_request = PromptGuardRequest {
            input: self
                .user_prompt
                .as_ref()
                .unwrap()
                .content
                .as_ref()
                .unwrap()
                .clone(),
            task: PromptGuardTask::Jailbreak,
        };

        let json_data: String = match serde_json::to_string(&get_prompt_guards_request) {
            Ok(json_data) => json_data,
            Err(error) => {
                self.send_server_error(ServerError::Serialization(error), None);
                return Action::Pause;
            }
        };

        let mut headers = vec![
            (ARCH_UPSTREAM_HOST_HEADER, GUARD_INTERNAL_HOST),
            (":method", "POST"),
            (":path", "/guard"),
            (":authority", GUARD_INTERNAL_HOST),
            ("content-type", "application/json"),
            ("x-envoy-max-retries", "3"),
            ("x-envoy-upstream-rq-timeout-ms", "60000"),
        ];

        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
        }

        let call_args = CallArgs::new(
            ARCH_INTERNAL_CLUSTER_NAME,
            "/guard",
            headers,
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        let call_context = StreamCallContext {
            response_handler_type: ResponseHandlerType::ArchGuard,
            user_message: self.user_prompt.as_ref().unwrap().content.clone(),
            prompt_target_name: None,
            request_body: self.chat_completions_request.as_ref().unwrap().clone(),
            similarity_scores: None,
            upstream_cluster: None,
            upstream_cluster_path: None,
            tool_calls: None,
        };

        if let Err(e) = self.http_call(call_args, call_context) {
            self.send_server_error(ServerError::HttpDispatch(e), None);
        }

        Action::Pause
    }

    fn on_http_response_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        debug!(
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
            debug!("streaming response");
        } else {
            debug!("non streaming response");
            let chat_completions_response: ChatCompletionsResponse =
                match serde_json::from_slice(&body) {
                    Ok(de) => de,
                    Err(e) => {
                        debug!(
                            "invalid response: {}, {}",
                            String::from_utf8_lossy(&body),
                            e
                        );
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

            if let Some(tool_calls) = self.tool_calls.as_ref() {
                if !tool_calls.is_empty() {
                    if self.arch_state.is_none() {
                        self.arch_state = Some(Vec::new());
                    }

                    let mut data = serde_json::from_slice(&body).unwrap();
                    // use serde::Value to manipulate the json object and ensure that we don't lose any data
                    if let Value::Object(ref mut map) = data {
                        // serialize arch state and add to metadata
                        let metadata = map
                            .entry("metadata")
                            .or_insert(Value::Object(serde_json::Map::new()));
                        if metadata == &Value::Null {
                            *metadata = Value::Object(serde_json::Map::new());
                        }

                        // since arch gateway generates tool calls (using arch-fc) and calls upstream api to
                        // get response, we will send these back to developer so they can see the api response
                        // and tool call arch-fc generated
                        let fc_messages = vec![
                            Message {
                                role: ASSISTANT_ROLE.to_string(),
                                content: None,
                                model: Some(ARCH_FC_MODEL_NAME.to_string()),
                                tool_calls: self.tool_calls.clone(),
                                tool_call_id: None,
                            },
                            Message {
                                role: TOOL_ROLE.to_string(),
                                content: self.tool_call_response.clone(),
                                model: None,
                                tool_calls: None,
                                tool_call_id: Some(self.tool_calls.as_ref().unwrap()[0].id.clone()),
                            },
                        ];
                        let fc_messages_str = serde_json::to_string(&fc_messages).unwrap();
                        let arch_state = HashMap::from([("messages".to_string(), fc_messages_str)]);
                        let arch_state_str = serde_json::to_string(&arch_state).unwrap();
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

        Action::Continue
    }
}
