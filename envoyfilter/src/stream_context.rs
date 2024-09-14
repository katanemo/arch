use crate::consts::{
    BOLT_FC_CLUSTER, BOLT_FC_REQUEST_TIMEOUT_MS, DEFAULT_COLLECTION_NAME, DEFAULT_EMBEDDING_MODEL,
    DEFAULT_PROMPT_TARGET_THRESHOLD, GPT_35_TURBO, OPENAI_CHAT_COMPLETIONS_PATH,
    RATELIMIT_SELECTOR_HEADER_KEY, SYSTEM_ROLE, USER_ROLE,
};
use crate::filter_context::WasmMetrics;
use crate::ratelimit;
use crate::ratelimit::Header;
use crate::stats::IncrementingMetric;
use crate::tokenizer;
use http::StatusCode;
use log::{debug, error, info, warn};
use open_message_format_embeddings::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use public_types::common_types::open_ai::StreamOptions;
use public_types::common_types::{
    open_ai::{
        ChatCompletionChunkResponse, ChatCompletionsRequest, ChatCompletionsResponse, Message,
    },
    SearchPointsRequest, SearchPointsResponse,
};
use public_types::common_types::{
    BoltFCResponse, BoltFCToolsCall, ToolParameter, ToolParameters, ToolsDefinition,
};
use public_types::configuration::{PromptTarget, PromptType};
use std::collections::HashMap;
use std::num::NonZero;
use std::rc::Rc;
use std::time::Duration;

enum RequestType {
    GetEmbedding,
    SearchPoints,
    FunctionResolver,
    FunctionCallResponse,
}

pub struct CallContext {
    request_type: RequestType,
    user_message: Option<String>,
    prompt_target: Option<PromptTarget>,
    request_body: ChatCompletionsRequest,
}

pub struct StreamContext {
    pub context_id: u32,
    pub metrics: Rc<WasmMetrics>,
    callouts: HashMap<u32, CallContext>,
    host_header: Option<String>,
    ratelimit_selector: Option<Header>,
    streaming_response: bool,
    response_tokens: usize,
    chat_completions_request: bool,
}

impl StreamContext {
    pub fn new(context_id: u32, metrics: Rc<WasmMetrics>) -> Self {
        StreamContext {
            context_id,
            metrics,
            callouts: HashMap::new(),
            host_header: None,
            ratelimit_selector: None,
            streaming_response: false,
            response_tokens: 0,
            chat_completions_request: false,
        }
    }
    fn save_host_header(&mut self) {
        // Save the host header to be used by filter logic later on.
        self.host_header = self.get_http_request_header(":host");
    }

    fn delete_content_length_header(&mut self) {
        // Remove the Content-Length header because further body manipulations in the gateway logic will invalidate it.
        // Server's generally throw away requests whose body length do not match the Content-Length header.
        // However, a missing Content-Length header is not grounds for bad requests given that intermediary hops could
        // manipulate the body in benign ways e.g., compression.
        self.set_http_request_header("content-length", None);
        // self.set_http_request_header("authorization", None);
    }

    fn modify_path_header(&mut self) {
        match self.get_http_request_header(":path") {
            // The gateway can start gathering information necessary for routing. For now change the path to an
            // OpenAI API path.
            Some(path) if path == "/llmrouting" => {
                self.set_http_request_header(":path", Some(OPENAI_CHAT_COMPLETIONS_PATH));
                self.chat_completions_request = true;
            }
            // Otherwise let the filter continue.
            _ => (),
        }
    }

    fn save_ratelimit_header(&mut self) {
        self.ratelimit_selector = self
            .get_http_request_header(RATELIMIT_SELECTOR_HEADER_KEY)
            .and_then(|key| {
                self.get_http_request_header(&key)
                    .map(|value| Header { key, value })
            });
    }

    fn send_server_error(&mut self, error: String) {
        debug!("server error occurred: {}", error);
        self.send_http_response(
            StatusCode::INTERNAL_SERVER_ERROR.as_u16().into(),
            vec![],
            Some(error.as_bytes()),
        )
    }

    fn embeddings_handler(&mut self, body: Vec<u8>, mut callout_context: CallContext) {
        let embedding_response: CreateEmbeddingResponse = match serde_json::from_slice(&body) {
            Ok(embedding_response) => embedding_response,
            Err(e) => {
                self.send_server_error(format!("Error deserializing embedding response: {:?}", e));
                return;
            }
        };

        let search_points_request = SearchPointsRequest {
            vector: embedding_response.data[0].embedding.clone(),
            limit: 10,
            with_payload: true,
        };

        let json_data: String = match serde_json::to_string(&search_points_request) {
            Ok(json_data) => json_data,
            Err(e) => {
                self.send_server_error(format!("Error serializing search_points_request: {:?}", e));
                return;
            }
        };

        let path = format!("/collections/{}/points/search", DEFAULT_COLLECTION_NAME);

        let token_id = match self.dispatch_http_call(
            "qdrant",
            vec![
                (":method", "POST"),
                (":path", &path),
                (":authority", "qdrant"),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
            ],
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        ) {
            Ok(token_id) => token_id,
            Err(e) => {
                panic!("Error dispatching HTTP call for get-embeddings: {:?}", e);
            }
        };

        callout_context.request_type = RequestType::SearchPoints;
        if self.callouts.insert(token_id, callout_context).is_some() {
            panic!("duplicate token_id")
        }
        self.metrics.active_http_calls.increment(1);
    }

    fn search_points_handler(&mut self, body: Vec<u8>, mut callout_context: CallContext) {
        let search_points_response: SearchPointsResponse = match serde_json::from_slice(&body) {
            Ok(search_points_response) => search_points_response,
            Err(e) => {
                self.send_server_error(format!(
                    "Error deserializing search_points_response: {:?}",
                    e
                ));

                return;
            }
        };

        let search_results = &search_points_response.result;

        if search_results.is_empty() {
            info!("No prompt target matched");
            self.resume_http_request();
            return;
        }

        info!("similarity score: {}", search_results[0].score);
        // Check to see who responded to user message. This will help us identify if control should be passed to Bolt FC or not.
        // If the last message was from Bolt FC, then Bolt FC is handling the conversation (possibly for parameter collection).
        let mut bolt_assistant = false;
        let messages = &callout_context.request_body.messages;
        if messages.len() >= 2 {
            let latest_assistant_message = &messages[messages.len() - 2];
            if let Some(model) = latest_assistant_message.model.as_ref() {
                if model.starts_with("Bolt") {
                    info!("Bolt assistant message found");
                    bolt_assistant = true;
                }
            }
        } else {
            info!("no assistant message found, probably first interaction");
        }

        if search_results[0].score < DEFAULT_PROMPT_TARGET_THRESHOLD && !bolt_assistant {
            info!(
                "prompt target below threshold: {}",
                DEFAULT_PROMPT_TARGET_THRESHOLD
            );
            self.resume_http_request();
            return;
        }
        let prompt_target_str = search_results[0].payload.get("prompt-target").unwrap();
        let prompt_target: PromptTarget = match serde_json::from_slice(prompt_target_str.as_bytes())
        {
            Ok(prompt_target) => prompt_target,
            Err(e) => {
                self.send_server_error(format!("Error deserializing prompt_target: {:?}", e));
                return;
            }
        };
        info!(
            "prompt_target name: {:?}, type: {:?}",
            prompt_target.name, prompt_target.prompt_type
        );

        match prompt_target.prompt_type {
            PromptType::FunctionResolver => {
                // only extract entity names
                let properties: HashMap<String, ToolParameter> = match prompt_target.parameters {
                    // Clone is unavoidable here because we don't want to move the values out of the prompt target struct.
                    Some(ref entities) => {
                        let mut properties: HashMap<String, ToolParameter> = HashMap::new();
                        for entity in entities.iter() {
                            let param = ToolParameter {
                                parameter_type: entity.parameter_type.clone(),
                                description: entity.description.clone(),
                                required: entity.required,
                            };
                            properties.insert(entity.name.clone(), param);
                        }
                        properties
                    }
                    None => HashMap::new(),
                };
                let tools_parameters = ToolParameters {
                    parameters_type: "dict".to_string(),
                    properties,
                };

                let tools_defintion: ToolsDefinition = ToolsDefinition {
                    name: prompt_target.name.clone(),
                    description: prompt_target.description.clone().unwrap_or("".to_string()),
                    parameters: tools_parameters,
                };

                let chat_completions = ChatCompletionsRequest {
                    model: GPT_35_TURBO.to_string(),
                    messages: callout_context.request_body.messages.clone(),
                    tools: Some(vec![tools_defintion]),
                    stream: false,
                    stream_options: None,
                };

                let msg_body = match serde_json::to_string(&chat_completions) {
                    Ok(msg_body) => {
                        debug!("msg_body: {}", msg_body);
                        msg_body
                    }
                    Err(e) => {
                        self.send_server_error(format!(
                            "Error serializing request_params: {:?}",
                            e
                        ));
                        return;
                    }
                };

                let token_id = match self.dispatch_http_call(
                    BOLT_FC_CLUSTER,
                    vec![
                        (":method", "POST"),
                        (":path", "/v1/chat/completions"),
                        (":authority", BOLT_FC_CLUSTER),
                        ("content-type", "application/json"),
                        ("x-envoy-max-retries", "3"),
                        (
                            "x-envoy-upstream-rq-timeout-ms",
                            BOLT_FC_REQUEST_TIMEOUT_MS.to_string().as_str(),
                        ),
                    ],
                    Some(msg_body.as_bytes()),
                    vec![],
                    Duration::from_secs(5),
                ) {
                    Ok(token_id) => token_id,
                    Err(e) => {
                        panic!("Error dispatching HTTP call for function-call: {:?}", e);
                    }
                };

                debug!(
                    "dispatched call to function {} token_id={}",
                    BOLT_FC_CLUSTER, token_id
                );

                callout_context.request_type = RequestType::FunctionResolver;
                callout_context.prompt_target = Some(prompt_target);
                if self.callouts.insert(token_id, callout_context).is_some() {
                    panic!("duplicate token_id")
                }
            }
        }
        self.metrics.active_http_calls.increment(1);
    }

    fn function_resolver_handler(&mut self, body: Vec<u8>, mut callout_context: CallContext) {
        debug!("response received for function resolver");

        let body_str = String::from_utf8(body).unwrap();
        debug!("function_resolver response str: {:?}", body_str);

        let mut boltfc_response: BoltFCResponse = serde_json::from_str(&body_str).unwrap();

        let boltfc_response_str = boltfc_response.message.content.as_ref().unwrap();

        let tools_call_response: BoltFCToolsCall = match serde_json::from_str(boltfc_response_str) {
            Ok(fc_resp) => fc_resp,
            Err(e) => {
                // This means that Bolt FC did not have enough information to resolve the function call
                // Bolt FC probably responded with a message asking for more information.
                // Let's send the response back to the user to initalize lightweight dialog for parameter collection

                // add resolver name to the response so the client can send the response back to the correct resolver
                boltfc_response.resolver_name = Some(callout_context.prompt_target.unwrap().name);
                info!("some requred parameters are missing, sending response from Bolt FC back to user for parameter collection: {}", e);
                let bolt_fc_dialogue_message = serde_json::to_string(&boltfc_response).unwrap();
                self.send_http_response(
                    StatusCode::OK.as_u16().into(),
                    vec![("Powered-By", "Katanemo")],
                    Some(bolt_fc_dialogue_message.as_bytes()),
                );
                return;
            }
        };

        // verify required parameters are present
        callout_context
            .prompt_target
            .as_ref()
            .unwrap()
            .parameters
            .as_ref()
            .unwrap()
            .iter()
            .for_each(|param| match param.required {
                None => {}
                Some(required) => {
                    if required
                        && !tools_call_response.tool_calls[0]
                            .arguments
                            .contains_key(&param.name)
                    {
                        warn!("boltfc did not extract required parameter: {}", param.name);
                        return self.send_http_response(
                            StatusCode::BAD_REQUEST.as_u16().into(),
                            vec![],
                            Some("missing required parameter".as_bytes()),
                        );
                    }
                }
            });

        debug!("tool_call_details: {:?}", tools_call_response);
        let tool_name = &tools_call_response.tool_calls[0].name;
        let tool_params = &tools_call_response.tool_calls[0].arguments;
        debug!("tool_name: {:?}", tool_name);
        debug!("tool_params: {:?}", tool_params);
        let prompt_target = callout_context.prompt_target.as_ref().unwrap();
        debug!("prompt_target: {:?}", prompt_target);

        let tool_params_json_str = serde_json::to_string(&tool_params).unwrap();

        let endpoint = prompt_target.endpoint.as_ref().unwrap();
        let token_id = match self.dispatch_http_call(
            &endpoint.cluster,
            vec![
                (":method", "POST"),
                (":path", endpoint.path.as_ref().unwrap_or(&"/".to_string())),
                (":authority", endpoint.cluster.as_str()),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
            ],
            Some(tool_params_json_str.as_bytes()),
            vec![],
            Duration::from_secs(5),
        ) {
            Ok(token_id) => token_id,
            Err(e) => {
                panic!("Error dispatching HTTP call for function_resolver: {:?}", e);
            }
        };

        callout_context.request_type = RequestType::FunctionCallResponse;
        if self.callouts.insert(token_id, callout_context).is_some() {
            panic!("duplicate token_id")
        }
        self.metrics.active_http_calls.increment(1);
    }

    fn function_call_response_handler(&mut self, body: Vec<u8>, callout_context: CallContext) {
        debug!("response received for function call response");
        let body_str: String = String::from_utf8(body).unwrap();
        debug!("function_call_response response str: {:?}", body_str);
        let prompt_target = callout_context.prompt_target.as_ref().unwrap();

        let mut messages: Vec<Message> = callout_context.request_body.messages.clone();

        // add system prompt
        match prompt_target.system_prompt.as_ref() {
            None => {}
            Some(system_prompt) => {
                let system_prompt_message = Message {
                    role: SYSTEM_ROLE.to_string(),
                    content: Some(system_prompt.clone()),
                    model: None,
                };
                messages.push(system_prompt_message);
            }
        }

        // add data from function call response
        messages.push({
            Message {
                role: USER_ROLE.to_string(),
                content: Some(body_str),
                model: None,
            }
        });

        // add original user prompt
        messages.push({
            Message {
                role: USER_ROLE.to_string(),
                content: Some(callout_context.user_message.unwrap()),
                model: None,
            }
        });

        let chat_completions_request: ChatCompletionsRequest = ChatCompletionsRequest {
            model: GPT_35_TURBO.to_string(),
            messages,
            tools: None,
            stream: callout_context.request_body.stream,
            stream_options: callout_context.request_body.stream_options,
        };

        let json_string = match serde_json::to_string(&chat_completions_request) {
            Ok(json_string) => json_string,
            Err(e) => {
                self.send_server_error(format!("Error serializing request_body: {:?}", e));
                return;
            }
        };
        debug!(
            "function_calling sending request to openai: msg {}",
            json_string
        );

        // Tokenize and Ratelimit.
        if let Some(selector) = self.ratelimit_selector.take() {
            if let Ok(token_count) =
                tokenizer::token_count(&chat_completions_request.model, &json_string)
            {
                match ratelimit::ratelimits(None).read().unwrap().check_limit(
                    chat_completions_request.model,
                    selector,
                    NonZero::new(token_count as u32).unwrap(),
                ) {
                    Ok(_) => (),
                    Err(err) => {
                        self.send_http_response(
                            StatusCode::TOO_MANY_REQUESTS.as_u16().into(),
                            vec![],
                            Some(format!("Exceeded Ratelimit: {}", err).as_bytes()),
                        );
                        self.metrics.ratelimited_rq.increment(1);
                        return;
                    }
                }
            }
        }

        debug!("sending request to openai: msg {}", json_string);
        self.set_http_request_body(0, json_string.len(), &json_string.into_bytes());
        self.resume_http_request();
    }
}

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for StreamContext {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        self.save_host_header();
        self.delete_content_length_header();
        self.modify_path_header();
        self.save_ratelimit_header();

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
                    Err(msg) => {
                        self.send_http_response(
                            StatusCode::BAD_REQUEST.as_u16().into(),
                            vec![],
                            Some(format!("Failed to deserialize: {}", msg).as_bytes()),
                        );
                        return Action::Pause;
                    }
                },
                None => {
                    self.send_http_response(
                        StatusCode::INTERNAL_SERVER_ERROR.as_u16().into(),
                        vec![],
                        None,
                    );
                    error!(
                        "Failed to obtain body bytes even though body_size is {}",
                        body_size
                    );
                    return Action::Pause;
                }
            };

        self.streaming_response = deserialized_body.stream;
        if deserialized_body.stream && deserialized_body.stream_options.is_none() {
            deserialized_body.stream_options = Some(StreamOptions {
                include_usage: true,
            });
        }

        let user_message = match deserialized_body
            .messages
            .last()
            .and_then(|last_message| last_message.content.clone())
        {
            Some(content) => content,
            None => {
                warn!("No messages in the request body");
                return Action::Continue;
            }
        };

        let get_embeddings_input = CreateEmbeddingRequest {
            // Need to clone into input because user_message is used below.
            input: Box::new(CreateEmbeddingRequestInput::String(user_message.clone())),
            model: String::from(DEFAULT_EMBEDDING_MODEL),
            encoding_format: None,
            dimensions: None,
            user: None,
        };

        let json_data: String = match serde_json::to_string(&get_embeddings_input) {
            Ok(json_data) => json_data,
            Err(error) => {
                panic!("Error serializing embeddings input: {}", error);
            }
        };

        let token_id = match self.dispatch_http_call(
            "embeddingserver",
            vec![
                (":method", "POST"),
                (":path", "/embeddings"),
                (":authority", "embeddingserver"),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
                ("x-envoy-upstream-rq-timeout-ms", "60000"),
            ],
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        ) {
            Ok(token_id) => token_id,
            Err(e) => {
                panic!(
                    "Error dispatching embedding server HTTP call for get-embeddings: {:?}",
                    e
                );
            }
        };
        debug!(
            "dispatched HTTP call to embedding server token_id={}",
            token_id
        );

        let call_context = CallContext {
            request_type: RequestType::GetEmbedding,
            user_message: Some(user_message),
            prompt_target: None,
            request_body: deserialized_body,
        };
        if self.callouts.insert(token_id, call_context).is_some() {
            panic!(
                "duplicate token_id={} in embedding server requests",
                token_id
            )
        }
        self.metrics.active_http_calls.increment(1);

        Action::Pause
    }

    fn on_http_response_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        if !self.chat_completions_request {
            return Action::Continue;
        }

        debug!(
            "recv [S={}] bytes={} end_stream={}",
            self.context_id, body_size, end_of_stream
        );

        if !end_of_stream && !self.streaming_response {
            return Action::Pause;
        }

        let body = self
            .get_http_response_body(0, body_size)
            .expect("cant get response body");

        let body_str = String::from_utf8(body).expect("body is not utf-8");

        if self.streaming_response {
            debug!("streaming response");
            let chat_completions_data = match body_str.split_once("data: ") {
                Some((_, chat_completions_data)) => chat_completions_data,
                None => {
                    self.send_http_response(
                        StatusCode::INTERNAL_SERVER_ERROR.as_u16().into(),
                        vec![],
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
                            debug!("error in streaming response");
                            self.send_http_response(
                                StatusCode::INTERNAL_SERVER_ERROR.as_u16().into(),
                                vec![],
                                None,
                            );
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
                match serde_json::from_str(&body_str) {
                    Ok(de) => de,
                    Err(e) => {
                        debug!(
                            "error in non-streaming response: {}\n response was={}",
                            e, body_str
                        );
                        self.send_http_response(
                            StatusCode::INTERNAL_SERVER_ERROR.as_u16().into(),
                            vec![],
                            None,
                        );
                        return Action::Continue;
                    }
                };

            self.response_tokens += chat_completions_response.usage.completions_tokens;
        }

        debug!(
            "recv [S={}] total_tokens={} end_stream={}",
            self.context_id, self.response_tokens, end_of_stream
        );

        // TODO:: ratelimit based on response tokens.
        Action::Continue
    }
}

impl Context for StreamContext {
    fn on_http_call_response(
        &mut self,
        token_id: u32,
        _num_headers: usize,
        body_size: usize,
        _num_trailers: usize,
    ) {
        let callout_context = self.callouts.remove(&token_id).expect("invalid token_id");
        self.metrics.active_http_calls.increment(-1);

        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            match callout_context.request_type {
                RequestType::GetEmbedding => self.embeddings_handler(body, callout_context),
                RequestType::SearchPoints => self.search_points_handler(body, callout_context),
                RequestType::FunctionResolver => {
                    self.function_resolver_handler(body, callout_context)
                }
                RequestType::FunctionCallResponse => {
                    self.function_call_response_handler(body, callout_context)
                }
            }
        } else {
            warn!("No response body in inline HTTP request");
        }
    }
}
