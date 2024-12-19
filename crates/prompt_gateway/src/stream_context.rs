use crate::metrics::Metrics;
use common::api::open_ai::{
    to_server_events, ArchState, ChatCompletionStreamResponse, ChatCompletionsRequest,
    ChatCompletionsResponse, Message, ModelServerResponse, ToolCall,
};
use common::configuration::{Overrides, PromptTarget, Tracing};
use common::consts::{
    ARCH_FC_MODEL_NAME, ARCH_FC_REQUEST_TIMEOUT_MS, ARCH_INTERNAL_CLUSTER_NAME,
    ARCH_UPSTREAM_HOST_HEADER, ASSISTANT_ROLE, MESSAGES_KEY, REQUEST_ID_HEADER, SYSTEM_ROLE,
    TOOL_ROLE, TRACE_PARENT_HEADER, USER_ROLE,
};
use common::errors::ServerError;
use common::http::{CallArgs, Client};
use common::stats::Gauge;
use derivative::Derivative;
use http::StatusCode;
use log::{debug, warn};
use proxy_wasm::traits::*;
use serde_yaml::Value;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;
use std::str::FromStr;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
pub enum ResponseHandlerType {
    ArchFC,
    FunctionCall,
    DefaultTarget,
}

#[derive(Clone, Derivative)]
#[derivative(Debug)]
pub struct StreamCallContext {
    pub response_handler_type: ResponseHandlerType,
    pub user_message: Option<String>,
    pub prompt_target_name: Option<String>,
    #[derivative(Debug = "ignore")]
    pub request_body: ChatCompletionsRequest,
    pub similarity_scores: Option<Vec<(String, f64)>>,
    pub upstream_cluster: Option<String>,
    pub upstream_cluster_path: Option<String>,
}

pub struct StreamContext {
    system_prompt: Rc<Option<String>>,
    pub prompt_targets: Rc<HashMap<String, PromptTarget>>,
    _overrides: Rc<Option<Overrides>>,
    pub metrics: Rc<Metrics>,
    pub callouts: RefCell<HashMap<u32, StreamCallContext>>,
    pub context_id: u32,
    pub tool_calls: Option<Vec<ToolCall>>,
    pub tool_call_response: Option<String>,
    pub arch_state: Option<Vec<ArchState>>,
    pub request_body_size: usize,
    pub user_prompt: Option<Message>,
    pub streaming_response: bool,
    pub is_chat_completions_request: bool,
    pub chat_completions_request: Option<ChatCompletionsRequest>,
    pub request_id: Option<String>,
    pub start_upstream_llm_request_time: u128,
    pub time_to_first_token: Option<u128>,
    pub traceparent: Option<String>,
    pub _tracing: Rc<Option<Tracing>>,
}

impl StreamContext {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        context_id: u32,
        metrics: Rc<Metrics>,
        system_prompt: Rc<Option<String>>,
        prompt_targets: Rc<HashMap<String, PromptTarget>>,
        overrides: Rc<Option<Overrides>>,
        tracing: Rc<Option<Tracing>>,
    ) -> Self {
        StreamContext {
            context_id,
            metrics,
            system_prompt,
            prompt_targets,
            callouts: RefCell::new(HashMap::new()),
            chat_completions_request: None,
            tool_calls: None,
            tool_call_response: None,
            arch_state: None,
            request_body_size: 0,
            streaming_response: false,
            user_prompt: None,
            is_chat_completions_request: false,
            _overrides: overrides,
            request_id: None,
            traceparent: None,
            _tracing: tracing,
            start_upstream_llm_request_time: 0,
            time_to_first_token: None,
        }
    }

    pub fn send_server_error(&self, error: ServerError, override_status_code: Option<StatusCode>) {
        self.send_http_response(
            override_status_code
                .unwrap_or(StatusCode::INTERNAL_SERVER_ERROR)
                .as_u16()
                .into(),
            vec![],
            Some(format!("{error}").as_bytes()),
        );
    }

    fn _trace_arch_internal(&self) -> bool {
        match self._tracing.as_ref() {
            Some(tracing) => match tracing.trace_arch_internal.as_ref() {
                Some(trace_arch_internal) => *trace_arch_internal,
                None => false,
            },
            None => false,
        }
    }

    pub fn arch_fc_response_handler(
        &mut self,
        body: Vec<u8>,
        mut callout_context: StreamCallContext,
    ) {
        let body_str = String::from_utf8(body).unwrap();
        debug!("archgw <= archfc response: {}", body_str);

        let model_server_response: ModelServerResponse = match serde_json::from_str(&body_str) {
            Ok(arch_fc_response) => arch_fc_response,
            Err(e) => {
                warn!(
                    "error deserializing archfc response: {}, body: {}",
                    e, body_str
                );
                return self.send_server_error(ServerError::Deserialization(e), None);
            }
        };

        let arch_fc_response = match model_server_response {
            ModelServerResponse::ChatCompletionsResponse(response) => response,
            ModelServerResponse::ModelServerErrorResponse(response) => {
                debug!("archgw <= archfc error response: {}", response.result);
                if response.result == "No intent matched" {
                    if let Some(default_prompt_target) = self
                        .prompt_targets
                        .values()
                        .find(|pt| pt.default.unwrap_or(false))
                    {
                        debug!("default prompt target found, forwarding request to default prompt target");
                        let endpoint = default_prompt_target.endpoint.clone().unwrap();
                        let upstream_path: String = endpoint.path.unwrap_or(String::from("/"));

                        let upstream_endpoint = endpoint.name;
                        let mut params = HashMap::new();
                        params.insert(
                            MESSAGES_KEY.to_string(),
                            callout_context.request_body.messages.clone(),
                        );
                        let arch_messages_json = serde_json::to_string(&params).unwrap();
                        let timeout_str = ARCH_FC_REQUEST_TIMEOUT_MS.to_string();

                        let mut headers = vec![
                            (":method", "POST"),
                            (ARCH_UPSTREAM_HOST_HEADER, &upstream_endpoint),
                            (":path", &upstream_path),
                            (":authority", &upstream_endpoint),
                            ("content-type", "application/json"),
                            ("x-envoy-max-retries", "3"),
                            ("x-envoy-upstream-rq-timeout-ms", timeout_str.as_str()),
                        ];

                        if self.request_id.is_some() {
                            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
                        }

                        // if self.trace_arch_internal() && self.traceparent.is_some() {
                        //     headers.push((TRACE_PARENT_HEADER, self.traceparent.as_ref().unwrap()));
                        // }

                        let call_args = CallArgs::new(
                            ARCH_INTERNAL_CLUSTER_NAME,
                            &upstream_path,
                            headers,
                            Some(arch_messages_json.as_bytes()),
                            vec![],
                            Duration::from_secs(5),
                        );
                        callout_context.response_handler_type = ResponseHandlerType::DefaultTarget;
                        callout_context.prompt_target_name =
                            Some(default_prompt_target.name.clone());

                        if let Err(e) = self.http_call(call_args, callout_context) {
                            warn!("error dispatching default prompt target request: {}", e);
                            return self.send_server_error(
                                ServerError::HttpDispatch(e),
                                Some(StatusCode::BAD_REQUEST),
                            );
                        }
                        return;
                    }
                }
                return self.send_server_error(
                    ServerError::LogicError(response.result),
                    Some(StatusCode::BAD_REQUEST),
                );
            }
        };

        arch_fc_response.choices[0]
            .message
            .tool_calls
            .clone_into(&mut self.tool_calls);

        if self.tool_calls.as_ref().unwrap().len() > 1 {
            warn!(
                "multiple tool calls not supported yet, tool_calls count found: {}",
                self.tool_calls.as_ref().unwrap().len()
            );
        }

        if self.tool_calls.is_none() || self.tool_calls.as_ref().unwrap().is_empty() {
            // This means that Arch FC did not have enough information to resolve the function call
            // Arch FC probably responded with a message asking for more information.
            // Let's send the response back to the user to initialize lightweight dialog for parameter collection

            //TODO: add resolver name to the response so the client can send the response back to the correct resolver

            let direct_response_str = if self.streaming_response {
                let chunks = vec![
                    ChatCompletionStreamResponse::new(
                        None,
                        Some(ASSISTANT_ROLE.to_string()),
                        Some(ARCH_FC_MODEL_NAME.to_owned()),
                        None,
                    ),
                    ChatCompletionStreamResponse::new(
                        Some(
                            arch_fc_response.choices[0]
                                .message
                                .content
                                .as_ref()
                                .unwrap()
                                .clone(),
                        ),
                        None,
                        Some(ARCH_FC_MODEL_NAME.to_owned()),
                        None,
                    ),
                ];

                to_server_events(chunks)
            } else {
                body_str
            };

            self.tool_calls = None;
            return self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![],
                Some(direct_response_str.as_bytes()),
            );
        }

        self.schedule_api_call_request(callout_context);
    }

    fn schedule_api_call_request(&mut self, mut callout_context: StreamCallContext) {
        let tools_call_name = self.tool_calls.as_ref().unwrap()[0].function.name.clone();

        let prompt_target = self.prompt_targets.get(&tools_call_name).unwrap().clone();

        let mut tool_params = self.tool_calls.as_ref().unwrap()[0]
            .function
            .arguments
            .clone();
        tool_params.insert(
            String::from(MESSAGES_KEY),
            serde_yaml::to_value(&callout_context.request_body.messages).unwrap(),
        );

        let tool_params_json_str = serde_json::to_string(&tool_params).unwrap();

        let endpoint = prompt_target.endpoint.unwrap();
        let path: String = endpoint.path.unwrap_or(String::from("/"));

        // only add params that are of string, number and bool type
        let url_params = tool_params
            .iter()
            .filter(|(_, value)| value.is_number() || value.is_string() || value.is_bool())
            .map(|(key, value)| match value {
                Value::Number(n) => (key.clone(), n.to_string()),
                Value::String(s) => (key.clone(), s.clone()),
                Value::Bool(b) => (key.clone(), b.to_string()),
                Value::Null => todo!(),
                Value::Sequence(_) => todo!(),
                Value::Mapping(_) => todo!(),
                Value::Tagged(_) => todo!(),
            })
            .collect::<HashMap<String, String>>();

        let path = match common::path::replace_params_in_path(&path, &url_params) {
            Ok(path) => path,
            Err(e) => {
                return self.send_server_error(
                    ServerError::BadRequest {
                        why: format!("error replacing params in path: {}", e),
                    },
                    Some(StatusCode::BAD_REQUEST),
                );
            }
        };

        let http_method = endpoint.method.unwrap_or_default().to_string();
        let mut headers = vec![
            (ARCH_UPSTREAM_HOST_HEADER, endpoint.name.as_str()),
            (":method", &http_method),
            (":path", &path),
            (":authority", endpoint.name.as_str()),
            ("content-type", "application/json"),
            ("x-envoy-max-retries", "3"),
        ];

        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
        }

        if self.traceparent.is_some() {
            headers.push((TRACE_PARENT_HEADER, self.traceparent.as_ref().unwrap()));
        }

        let call_args = CallArgs::new(
            ARCH_INTERNAL_CLUSTER_NAME,
            &path,
            headers,
            Some(tool_params_json_str.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );

        debug!(
            "archgw => api call, endpoint: {}{}, body: {}",
            endpoint.name.as_str(),
            path,
            tool_params_json_str
        );

        callout_context.upstream_cluster = Some(endpoint.name.to_owned());
        callout_context.upstream_cluster_path = Some(path.to_owned());
        callout_context.response_handler_type = ResponseHandlerType::FunctionCall;

        if let Err(e) = self.http_call(call_args, callout_context) {
            self.send_server_error(ServerError::HttpDispatch(e), Some(StatusCode::BAD_REQUEST));
        }
    }

    pub fn api_call_response_handler(&mut self, body: Vec<u8>, callout_context: StreamCallContext) {
        let http_status = self
            .get_http_call_response_header(":status")
            .unwrap_or(StatusCode::OK.as_str().to_string());
          debug!("api_call_response_handler: http_status: {}", http_status);
          if http_status != StatusCode::OK.as_str() {
            warn!(
                "api server responded with non 2xx status code: {}",
                http_status
            );
            return self.send_server_error(
                ServerError::Upstream {
                    host: callout_context.upstream_cluster.unwrap(),
                    path: callout_context.upstream_cluster_path.unwrap(),
                    status: http_status.clone(),
                    body: String::from_utf8(body).unwrap(),
                },
                Some(StatusCode::from_str(http_status.as_str()).unwrap()),
            );
        }
        self.tool_call_response = Some(String::from_utf8(body).unwrap());
        debug!(
            "archgw <= api call response: {}",
            self.tool_call_response.as_ref().unwrap()
        );

        let mut messages = self.filter_out_arch_messages(&callout_context);

        let user_message = match messages.pop() {
            Some(user_message) => user_message,
            None => {
                return self.send_server_error(
                    ServerError::NoMessagesFound {
                        why: "no user messages found".to_string(),
                    },
                    None,
                );
            }
        };

        let final_prompt = format!(
            "{}\ncontext: {}",
            user_message.content.unwrap(),
            self.tool_call_response.as_ref().unwrap()
        );

        // add original user prompt
        messages.push({
            Message {
                role: USER_ROLE.to_string(),
                content: Some(final_prompt),
                model: None,
                tool_calls: None,
                tool_call_id: None,
            }
        });

        let chat_completions_request: ChatCompletionsRequest = ChatCompletionsRequest {
            model: callout_context.request_body.model,
            messages,
            tools: None,
            stream: callout_context.request_body.stream,
            stream_options: callout_context.request_body.stream_options,
            metadata: None,
        };

        let llm_request_str = match serde_json::to_string(&chat_completions_request) {
            Ok(json_string) => json_string,
            Err(e) => {
                return self.send_server_error(ServerError::Serialization(e), None);
            }
        };
        debug!("archgw => llm request: {}", llm_request_str);

        self.start_upstream_llm_request_time = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();

        self.set_http_request_body(0, self.request_body_size, &llm_request_str.into_bytes());
        self.resume_http_request();
    }

    fn filter_out_arch_messages(&mut self, callout_context: &StreamCallContext) -> Vec<Message> {
        let mut messages: Vec<Message> = Vec::new();
        // add system prompt

        let system_prompt = match callout_context.prompt_target_name.as_ref() {
            None => self.system_prompt.as_ref().clone(),
            Some(prompt_target_name) => {
                let prompt_system_prompt = self
                    .prompt_targets
                    .get(prompt_target_name)
                    .unwrap()
                    .clone()
                    .system_prompt;
                match prompt_system_prompt {
                    None => self.system_prompt.as_ref().clone(),
                    Some(system_prompt) => Some(system_prompt),
                }
            }
        };
        if system_prompt.is_some() {
            let system_prompt_message = Message {
                role: SYSTEM_ROLE.to_string(),
                content: system_prompt,
                model: None,
                tool_calls: None,
                tool_call_id: None,
            };
            messages.push(system_prompt_message);
        }

        // don't send tools message and api response to chat gpt
        for m in callout_context.request_body.messages.iter() {
            // don't send api response and tool calls to upstream LLMs
            if m.role == TOOL_ROLE
                || m.content.is_none()
                || (m.tool_calls.is_some() && !m.tool_calls.as_ref().unwrap().is_empty())
            {
                continue;
            }
            messages.push(m.clone());
        }

        messages
    }

    pub fn generate_toll_call_message(&mut self) -> Message {
        Message {
            role: ASSISTANT_ROLE.to_string(),
            content: None,
            model: Some(ARCH_FC_MODEL_NAME.to_string()),
            tool_calls: self.tool_calls.clone(),
            tool_call_id: None,
        }
    }

    pub fn generate_api_response_message(&mut self) -> Message {
        Message {
            role: TOOL_ROLE.to_string(),
            content: self.tool_call_response.clone(),
            model: None,
            tool_calls: None,
            tool_call_id: Some(self.tool_calls.as_ref().unwrap()[0].id.clone()),
        }
    }

    pub fn default_target_handler(&self, body: Vec<u8>, mut callout_context: StreamCallContext) {
        let prompt_target = self
            .prompt_targets
            .get(callout_context.prompt_target_name.as_ref().unwrap())
            .unwrap()
            .clone();

        // check if the default target should be dispatched to the LLM provider
        if !prompt_target
            .auto_llm_dispatch_on_response
            .unwrap_or_default()
        {
            let default_target_response_str = if self.streaming_response {
                let chat_completion_response =
                    match serde_json::from_slice::<ChatCompletionsResponse>(&body) {
                        Ok(chat_completion_response) => chat_completion_response,
                        Err(e) => {
                            warn!(
                                "error deserializing default target response: {}, body str: {}",
                                e,
                                String::from_utf8(body).unwrap()
                            );
                            return self.send_server_error(ServerError::Deserialization(e), None);
                        }
                    };

                let chunks = vec![
                    ChatCompletionStreamResponse::new(
                        None,
                        Some(ASSISTANT_ROLE.to_string()),
                        Some(chat_completion_response.model.clone()),
                        None,
                    ),
                    ChatCompletionStreamResponse::new(
                        chat_completion_response.choices[0].message.content.clone(),
                        None,
                        Some(chat_completion_response.model.clone()),
                        None,
                    ),
                ];

                to_server_events(chunks)
            } else {
                String::from_utf8(body).unwrap()
            };

            self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![],
                Some(default_target_response_str.as_bytes()),
            );
            return;
        }

        let chat_completions_resp: ChatCompletionsResponse = match serde_json::from_slice(&body) {
            Ok(chat_completions_resp) => chat_completions_resp,
            Err(e) => {
                warn!(
                    "error deserializing default target response: {}, body str: {}",
                    e,
                    String::from_utf8(body).unwrap()
                );
                return self.send_server_error(ServerError::Deserialization(e), None);
            }
        };

        let mut messages = Vec::new();
        // add system prompt
        match prompt_target.system_prompt.as_ref() {
            None => {}
            Some(system_prompt) => {
                let system_prompt_message = Message {
                    role: SYSTEM_ROLE.to_string(),
                    content: Some(system_prompt.clone()),
                    model: None,
                    tool_calls: None,
                    tool_call_id: None,
                };
                messages.push(system_prompt_message);
            }
        }

        messages.append(&mut callout_context.request_body.messages);

        let api_resp = chat_completions_resp.choices[0]
            .message
            .content
            .as_ref()
            .unwrap();

        let user_message = messages.pop().unwrap();
        let message = format!("{}\ncontext: {}", user_message.content.unwrap(), api_resp);
        messages.push(Message {
            role: USER_ROLE.to_string(),
            content: Some(message),
            model: None,
            tool_calls: None,
            tool_call_id: None,
        });

        let chat_completion_request = ChatCompletionsRequest {
            model: self
                .chat_completions_request
                .as_ref()
                .unwrap()
                .model
                .clone(),
            messages,
            tools: None,
            stream: callout_context.request_body.stream,
            stream_options: callout_context.request_body.stream_options,
            metadata: None,
        };

        let json_resp = serde_json::to_string(&chat_completion_request).unwrap();
        debug!("archgw => (default target) llm request: {}", json_resp);
        self.set_http_request_body(0, self.request_body_size, json_resp.as_bytes());
        self.resume_http_request();
    }
}

impl Client for StreamContext {
    type CallContext = StreamCallContext;

    fn callouts(&self) -> &RefCell<HashMap<u32, Self::CallContext>> {
        &self.callouts
    }

    fn active_http_calls(&self) -> &Gauge {
        &self.metrics.active_http_calls
    }
}
