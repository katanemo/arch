use crate::configuration::PromptTarget;
use crate::consts::{
    DEFAULT_COLLECTION_NAME, DEFAULT_EMBEDDING_MODEL, DEFAULT_PROMPT_TARGET_THRESHOLD, SYSTEM_ROLE,
    USER_ROLE,
};
use crate::{
    common_types::{
        open_ai::{ChatCompletions, Message},
        FunctionCallingModelResponse, FunctionCallingToolsCallContent, SearchPointsRequest,
        SearchPointsResponse, ToolParameter, ToolParameters, ToolsDefinition,
    },
    consts::{BOLT_FC_CLUSTER, BOLT_FC_REQUEST_TIMEOUT_MS, GPT_35_TURBO},
};
use http::StatusCode;
use log::info;
use log::warn;
use log::{debug, error};
use open_message_format_embeddings::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use std::collections::HashMap;
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
    request_body: ChatCompletions,
}

pub struct StreamContext {
    pub host_header: Option<String>,
    pub callouts: HashMap<u32, CallContext>,
}

impl StreamContext {
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
                self.set_http_request_header(":path", Some("/v1/chat/completions"));
            }
            // Otherwise let the filter continue.
            _ => (),
        }
    }

    fn embeddings_handler(&mut self, body: Vec<u8>, mut callout_context: CallContext) {
        let embedding_response: CreateEmbeddingResponse = match serde_json::from_slice(&body) {
            Ok(embedding_response) => embedding_response,
            Err(e) => {
                warn!("Error deserializing embedding response: {:?}", e);
                self.resume_http_request();
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
                warn!("Error serializing search_points_request: {:?}", e);
                self.reset_http_request();
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
    }

    fn search_points_handler(&mut self, body: Vec<u8>, mut callout_context: CallContext) {
        let search_points_response: SearchPointsResponse = match serde_json::from_slice(&body) {
            Ok(search_points_response) => search_points_response,
            Err(e) => {
                warn!("Error deserializing search_points_response: {:?}", e);
                self.resume_http_request();
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
        let mut bolt_assistant = false;
        let messages = &callout_context.request_body.messages;
        if messages.len() >= 2 {
            let latest_assistant_message = &messages[messages.len() - 2];
            latest_assistant_message.model.as_ref().map(|model| {
                if model.starts_with("Bolt") {
                    info!("Bolt assistant message found");
                    bolt_assistant = true;
                }
            });
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
                warn!("Error deserializing prompt_target: {:?}", e);
                self.resume_http_request();
                return;
            }
        };
        info!("prompt_target name: {:?}", prompt_target.name);
        info!("prompt_target type: {:?}", prompt_target.prompt_type);

        match prompt_target.prompt_type {
            crate::configuration::PromptType::FunctionResolver => {
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

                let chat_completions = ChatCompletions {
                    model: GPT_35_TURBO.to_string(),
                    messages: callout_context.request_body.messages.clone(),
                    tools: Some(vec![tools_defintion]),
                };

                let msg_body = match serde_json::to_string(&chat_completions) {
                    Ok(msg_body) => {
                        debug!("msg_body: {}", msg_body);
                        msg_body
                    }
                    Err(e) => {
                        warn!("Error serializing request_params: {:?}", e);
                        self.resume_http_request();
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

                info!(
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
    }

    fn function_resolver_handler(&mut self, body: Vec<u8>, mut callout_context: CallContext) {
        info!("response received for function resolver");
        // let body_string = String::from_utf8(body);

        let body_str = String::from_utf8(body.clone()).unwrap();
        debug!("function_resolver response str: {:?}", body_str);

        let mut resp = serde_json::from_str::<FunctionCallingModelResponse>(&body_str).unwrap();
        resp.resolver_name = Some(callout_context.prompt_target.as_ref().unwrap().name.clone());

        let content: String = resp.message.content.as_ref().unwrap().clone();

        let _tool_call_details = serde_json::from_str::<FunctionCallingToolsCallContent>(&content);
        match _tool_call_details {
            Ok(_) => {}
            Err(e) => {
                info!("error deserializing tool_call_details: {:?}", e);
                info!("possibly some required parameters are missing, send back the response");
                let resp_str = serde_json::to_string(&resp).unwrap();
                self.send_http_response(
                    200,
                    vec![("Powered-By", "Katanemo")],
                    Some(resp_str.as_bytes()),
                );
                return;
            }
        }

        let tool_call_details = _tool_call_details.unwrap();

        info!("tool_call_details: {:?}", tool_call_details);
        let tool_name = &tool_call_details.tool_calls[0].name;
        let tool_params = &tool_call_details.tool_calls[0].arguments;
        info!("tool_name: {:?}", tool_name);
        info!("tool_params: {:?}", tool_params);
        let prompt_target = callout_context.prompt_target.as_ref().unwrap();
        info!("prompt_target: {:?}", prompt_target);

        let tool_params_json_str = serde_json::to_string(&tool_params).unwrap();

        let endpoint = prompt_target.endpoint.as_ref().unwrap();
        let token_id = match self.dispatch_http_call(
            &endpoint.cluster,
            vec![
                (":method", "POST"),
                (":path", &endpoint.path.as_ref().unwrap_or(&"/".to_string())),
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
    }

    fn function_call_response_handler(&self, body: Vec<u8>, callout_context: CallContext) {
        info!("response received for function call response");
        let body_str: String = String::from_utf8(body).unwrap();
        info!("function_call_response response str: {:?}", body_str);
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

        let request_message: ChatCompletions = ChatCompletions {
            model: GPT_35_TURBO.to_string(),
            messages,
            tools: None,
        };

        let json_string = match serde_json::to_string(&request_message) {
            Ok(json_string) => json_string,
            Err(e) => {
                warn!("Error serializing request_body: {:?}", e);
                self.resume_http_request();
                return;
            }
        };
        info!(
            "function_calling sending request to openai: msg {}",
            json_string
        );
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
        let deserialized_body: ChatCompletions = match self.get_http_request_body(0, body_size) {
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

        let user_message = match deserialized_body
            .messages
            .last()
            .and_then(|last_message| last_message.content.clone())
        {
            Some(content) => content,
            None => {
                info!("No messages in the request body");
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
        info!(
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

        Action::Pause
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

        let resp = self.get_http_call_response_body(0, body_size);

        if resp.is_none() {
            warn!("No response body");
            self.resume_http_request();
            return;
        }

        let body = match resp {
            Some(body) => body,
            None => {
                warn!("Empty response body");
                self.resume_http_request();
                return;
            }
        };

        match callout_context.request_type {
            RequestType::GetEmbedding => self.embeddings_handler(body, callout_context),
            RequestType::SearchPoints => self.search_points_handler(body, callout_context),
            RequestType::FunctionResolver => self.function_resolver_handler(body, callout_context),
            RequestType::FunctionCallResponse => {
                self.function_call_response_handler(body, callout_context)
            }
        }
    }
}
