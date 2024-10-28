use crate::filter_context::{EmbeddingsStore, WasmMetrics};
use crate::hallucination::extract_messages_for_hallucination;
use acap::cos;
use common::common_types::open_ai::{
    ArchState, ChatCompletionStreamResponse, ChatCompletionTool, ChatCompletionsRequest,
    ChatCompletionsResponse, FunctionDefinition, FunctionParameter, FunctionParameters, Message,
    ParameterType, ToolCall, ToolType,
};
use common::common_types::{
    EmbeddingType, HallucinationClassificationRequest, HallucinationClassificationResponse,
    PromptGuardResponse, ZeroShotClassificationRequest, ZeroShotClassificationResponse,
};
use common::configuration::{Overrides, PromptGuards, PromptTarget};
use common::consts::{
    ARCH_FC_INTERNAL_HOST, ARCH_FC_MODEL_NAME, ARCH_FC_REQUEST_TIMEOUT_MS,
    ARCH_INTERNAL_CLUSTER_NAME, ARCH_MODEL_PREFIX, ARCH_STATE_HEADER, ARCH_UPSTREAM_HOST_HEADER,
    ASSISTANT_ROLE, DEFAULT_EMBEDDING_MODEL, DEFAULT_HALLUCINATED_THRESHOLD, DEFAULT_INTENT_MODEL,
    DEFAULT_PROMPT_TARGET_THRESHOLD, EMBEDDINGS_INTERNAL_HOST, HALLUCINATION_INTERNAL_HOST,
    HALLUCINATION_TEMPLATE, MESSAGES_KEY, REQUEST_ID_HEADER, SYSTEM_ROLE, TOOL_ROLE, USER_ROLE,
    ZEROSHOT_INTERNAL_HOST,
};
use common::embeddings::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use common::errors::ServerError;
use common::http::{CallArgs, Client};
use common::stats::Gauge;
use derivative::Derivative;
use http::StatusCode;
use log::{debug, info, trace, warn};
use proxy_wasm::traits::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;
use std::str::FromStr;
use std::time::Duration;

#[derive(Debug, Clone)]
pub enum ResponseHandlerType {
    Embeddings,
    ArchFC,
    FunctionCall,
    ZeroShotIntent,
    Hallucination,
    ArchGuard,
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
    prompt_targets: Rc<HashMap<String, PromptTarget>>,
    pub embeddings_store: Option<Rc<EmbeddingsStore>>,
    overrides: Rc<Option<Overrides>>,
    pub metrics: Rc<WasmMetrics>,
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
    pub prompt_guards: Rc<PromptGuards>,
    pub request_id: Option<String>,
}

impl StreamContext {
    pub fn new(
        context_id: u32,
        metrics: Rc<WasmMetrics>,
        system_prompt: Rc<Option<String>>,
        prompt_targets: Rc<HashMap<String, PromptTarget>>,
        prompt_guards: Rc<PromptGuards>,
        overrides: Rc<Option<Overrides>>,
        embeddings_store: Option<Rc<EmbeddingsStore>>,
    ) -> Self {
        StreamContext {
            context_id,
            metrics,
            system_prompt,
            prompt_targets,
            embeddings_store,
            callouts: RefCell::new(HashMap::new()),
            chat_completions_request: None,
            tool_calls: None,
            tool_call_response: None,
            arch_state: None,
            request_body_size: 0,
            streaming_response: false,
            user_prompt: None,
            is_chat_completions_request: false,
            prompt_guards,
            overrides,
            request_id: None,
        }
    }
    fn embeddings_store(&self) -> &EmbeddingsStore {
        self.embeddings_store
            .as_ref()
            .expect("embeddings store is not set")
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

    pub fn get_embeddings(&mut self, callout_context: StreamCallContext) {
        let user_message = callout_context.user_message.unwrap();
        let get_embeddings_input = CreateEmbeddingRequest {
            // Need to clone into input because user_message is used below.
            input: Box::new(CreateEmbeddingRequestInput::String(user_message.clone())),
            model: String::from(DEFAULT_EMBEDDING_MODEL),
            encoding_format: None,
            dimensions: None,
            user: None,
        };

        let embeddings_request_str: String = match serde_json::to_string(&get_embeddings_input) {
            Ok(json_data) => json_data,
            Err(error) => {
                warn!("error serializing get embeddings request: {}", error);
                return self.send_server_error(ServerError::Deserialization(error), None);
            }
        };

        let mut headers = vec![
            (ARCH_UPSTREAM_HOST_HEADER, EMBEDDINGS_INTERNAL_HOST),
            (":method", "POST"),
            (":path", "/embeddings"),
            (":authority", EMBEDDINGS_INTERNAL_HOST),
            ("content-type", "application/json"),
            ("x-envoy-max-retries", "3"),
            ("x-envoy-upstream-rq-timeout-ms", "60000"),
        ];
        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
        }
        let call_args = CallArgs::new(
            ARCH_INTERNAL_CLUSTER_NAME,
            "/embeddings",
            headers,
            Some(embeddings_request_str.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        let call_context = StreamCallContext {
            response_handler_type: ResponseHandlerType::Embeddings,
            user_message: Some(user_message),
            prompt_target_name: None,
            request_body: callout_context.request_body,
            similarity_scores: None,
            upstream_cluster: None,
            upstream_cluster_path: None,
        };

        debug!(
            "archgw => get embeddings request: {}",
            embeddings_request_str
        );
        if let Err(e) = self.http_call(call_args, call_context) {
            warn!("error dispatching get embeddings request: {}", e);
            self.send_server_error(ServerError::HttpDispatch(e), None);
        }
    }

    pub fn embeddings_handler(&mut self, body: Vec<u8>, mut callout_context: StreamCallContext) {
        let embedding_response: CreateEmbeddingResponse = match serde_json::from_slice(&body) {
            Ok(embedding_response) => embedding_response,
            Err(e) => {
                warn!("error deserializing embedding response: {}", e);
                return self.send_server_error(ServerError::Deserialization(e), None);
            }
        };

        let prompt_embeddings_vector = &embedding_response.data[0].embedding;

        trace!(
            "embedding model: {}, vector length: {:?}",
            embedding_response.model,
            prompt_embeddings_vector.len()
        );

        let prompt_target_names = self
            .prompt_targets
            .iter()
            // exclude default target
            .filter(|(_, prompt_target)| !prompt_target.default.unwrap_or(false))
            .map(|(name, _)| name.clone())
            .collect();

        let similarity_scores: Vec<(String, f64)> = self
            .prompt_targets
            .iter()
            // exclude default prompt target
            .filter(|(_, prompt_target)| !prompt_target.default.unwrap_or(false))
            .map(|(prompt_name, _)| {
                let pte = match self.embeddings_store().get(prompt_name) {
                    Some(embeddings) => embeddings,
                    None => {
                        warn!(
                            "embeddings not found for prompt target name: {}",
                            prompt_name
                        );
                        return (prompt_name.clone(), f64::NAN);
                    }
                };

                let description_embeddings = match pte.get(&EmbeddingType::Description) {
                    Some(embeddings) => embeddings,
                    None => {
                        warn!(
                            "description embeddings not found for prompt target name: {}",
                            prompt_name
                        );
                        return (prompt_name.clone(), f64::NAN);
                    }
                };
                let similarity_score_description =
                    cos::cosine_similarity(&prompt_embeddings_vector, &description_embeddings);
                (prompt_name.clone(), similarity_score_description)
            })
            .collect();

        debug!(
            "similarity scores based on description embeddings match: {:?}",
            similarity_scores
        );

        callout_context.similarity_scores = Some(similarity_scores);

        let zero_shot_classification_request = ZeroShotClassificationRequest {
            // Need to clone into input because user_message is used below.
            input: callout_context.user_message.as_ref().unwrap().clone(),
            model: String::from(DEFAULT_INTENT_MODEL),
            labels: prompt_target_names,
        };

        let json_data: String = match serde_json::to_string(&zero_shot_classification_request) {
            Ok(json_data) => json_data,
            Err(error) => {
                debug!(
                    "error serializing zero shot classification request: {}",
                    error
                );
                return self.send_server_error(ServerError::Serialization(error), None);
            }
        };

        let mut headers = vec![
            (ARCH_UPSTREAM_HOST_HEADER, ZEROSHOT_INTERNAL_HOST),
            (":method", "POST"),
            (":path", "/zeroshot"),
            (":authority", ZEROSHOT_INTERNAL_HOST),
            ("content-type", "application/json"),
            ("x-envoy-max-retries", "3"),
            ("x-envoy-upstream-rq-timeout-ms", "60000"),
        ];

        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
        }

        let call_args = CallArgs::new(
            ARCH_INTERNAL_CLUSTER_NAME,
            "/zeroshot",
            headers,
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        callout_context.response_handler_type = ResponseHandlerType::ZeroShotIntent;

        if let Err(e) = self.http_call(call_args, callout_context) {
            warn!("error dispatching zero shot classification request: {}", e);
            self.send_server_error(ServerError::HttpDispatch(e), None);
        }
    }

    pub fn hallucination_classification_resp_handler(
        &mut self,
        body: Vec<u8>,
        callout_context: StreamCallContext,
    ) {
        let body_str = String::from_utf8(body).expect("could not convert body to string");
        debug!("archgw <= hallucination response: {}", body_str);
        let hallucination_response: HallucinationClassificationResponse =
            match serde_json::from_str(body_str.as_str()) {
                Ok(hallucination_response) => hallucination_response,
                Err(e) => {
                    warn!(
                        "error deserializing hallucination response: {}, body: {}",
                        e,
                        body_str.as_str()
                    );
                    return self.send_server_error(ServerError::Deserialization(e), None);
                }
            };
        let mut keys_with_low_score: Vec<String> = Vec::new();
        for (key, value) in &hallucination_response.params_scores {
            if *value < DEFAULT_HALLUCINATED_THRESHOLD {
                debug!(
                    "hallucination detected: score for {} : {} is less than threshold {}",
                    key, value, DEFAULT_HALLUCINATED_THRESHOLD
                );
                keys_with_low_score.push(key.clone().to_string());
            }
        }

        if !keys_with_low_score.is_empty() {
            let response =
                HALLUCINATION_TEMPLATE.to_string() + &keys_with_low_score.join(", ") + " ?";

            let response_str = if self.streaming_response {
                let chunks = [
                    ChatCompletionStreamResponse::new(
                        None,
                        Some(ASSISTANT_ROLE.to_string()),
                        Some(ARCH_FC_MODEL_NAME.to_owned()),
                    ),
                    ChatCompletionStreamResponse::new(
                        Some(response),
                        None,
                        Some(ARCH_FC_MODEL_NAME.to_owned()),
                    ),
                ];

                let mut response_str = String::new();
                for chunk in chunks.iter() {
                    response_str.push_str("data: ");
                    response_str.push_str(&serde_json::to_string(&chunk).unwrap());
                    response_str.push_str("\n\n");
                }
                response_str
            } else {
                let chat_completion_response = ChatCompletionsResponse::new(response);
                serde_json::to_string(&chat_completion_response).unwrap()
            };
            debug!("hallucination response: {:?}", response_str);
            // make sure on_http_response_body does not attach tool calls and tool response to the response
            self.tool_calls = None;
            self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![("Powered-By", "Katanemo")],
                Some(response_str.as_bytes()),
            );
        } else {
            // not a hallucination, resume the flow
            self.schedule_api_call_request(callout_context);
        }
    }

    pub fn zero_shot_intent_detection_resp_handler(
        &mut self,
        body: Vec<u8>,
        mut callout_context: StreamCallContext,
    ) {
        let zeroshot_intent_response: ZeroShotClassificationResponse =
            match serde_json::from_slice(&body) {
                Ok(zeroshot_response) => zeroshot_response,
                Err(e) => {
                    warn!(
                        "error deserializing zero shot classification response: {}",
                        e
                    );
                    return self.send_server_error(ServerError::Deserialization(e), None);
                }
            };

        trace!(
            "zeroshot intent response: {}",
            serde_json::to_string(&zeroshot_intent_response).unwrap()
        );

        let desc_emb_similarity_map: HashMap<String, f64> = callout_context
            .similarity_scores
            .clone()
            .unwrap()
            .into_iter()
            .collect();

        let pred_class_desc_emb_similarity = desc_emb_similarity_map
            .get(&zeroshot_intent_response.predicted_class)
            .unwrap();

        let prompt_target_similarity_score = zeroshot_intent_response.predicted_class_score * 0.7
            + pred_class_desc_emb_similarity * 0.3;

        debug!(
            "similarity score: {:.3}, intent score: {:.3}, description embedding score: {:.3}, prompt: {}",
            prompt_target_similarity_score,
            zeroshot_intent_response.predicted_class_score,
            pred_class_desc_emb_similarity,
            callout_context.user_message.as_ref().unwrap()
        );

        let prompt_target_name = zeroshot_intent_response.predicted_class.clone();

        // Check to see who responded to user message. This will help us identify if control should be passed to Arch FC or not.
        // If the last message was from Arch FC, then Arch FC is handling the conversation (possibly for parameter collection).
        let mut arch_assistant = false;
        let messages = &callout_context.request_body.messages;
        if messages.len() >= 2 {
            let latest_assistant_message = &messages[messages.len() - 2];
            if let Some(model) = latest_assistant_message.model.as_ref() {
                if model.contains(ARCH_MODEL_PREFIX) {
                    arch_assistant = true;
                }
            }
        } else {
            debug!("no assistant message found, probably first interaction");
        }

        // get prompt target similarity thresold from overrides
        let prompt_target_intent_matching_threshold = match self.overrides.as_ref() {
            Some(overrides) => match overrides.prompt_target_intent_matching_threshold {
                Some(threshold) => threshold,
                None => DEFAULT_PROMPT_TARGET_THRESHOLD,
            },
            None => DEFAULT_PROMPT_TARGET_THRESHOLD,
        };

        // check to ensure that the prompt target similarity score is above the threshold
        if prompt_target_similarity_score < prompt_target_intent_matching_threshold
            || arch_assistant
        {
            debug!("intent score is low or arch assistant is handling the conversation");
            // if arch fc responded to the user message, then we don't need to check the similarity score
            // it may be that arch fc is handling the conversation for parameter collection
            if arch_assistant {
                info!("arch fc is engaged in parameter collection");
            } else {
                if let Some(default_prompt_target) = self
                    .prompt_targets
                    .values()
                    .find(|pt| pt.default.unwrap_or(false))
                {
                    debug!(
                        "default prompt target found, forwarding request to default prompt target"
                    );
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

                    let call_args = CallArgs::new(
                        ARCH_INTERNAL_CLUSTER_NAME,
                        &upstream_path,
                        headers,
                        Some(arch_messages_json.as_bytes()),
                        vec![],
                        Duration::from_secs(5),
                    );
                    callout_context.response_handler_type = ResponseHandlerType::DefaultTarget;
                    callout_context.prompt_target_name = Some(default_prompt_target.name.clone());

                    if let Err(e) = self.http_call(call_args, callout_context) {
                        warn!("error dispatching default prompt target request: {}", e);
                        return self.send_server_error(
                            ServerError::HttpDispatch(e),
                            Some(StatusCode::BAD_REQUEST),
                        );
                    }
                }

                self.resume_http_request();
                return;
            }
        }

        let prompt_target = self
            .prompt_targets
            .get(&prompt_target_name)
            .expect("prompt target not found")
            .clone();

        let mut chat_completion_tools: Vec<ChatCompletionTool> = Vec::new();
        for pt in self.prompt_targets.values() {
            if pt.default.unwrap_or_default() {
                continue;
            }
            // only extract entity names
            let properties: HashMap<String, FunctionParameter> = match pt.parameters {
                // Clone is unavoidable here because we don't want to move the values out of the prompt target struct.
                Some(ref entities) => {
                    let mut properties: HashMap<String, FunctionParameter> = HashMap::new();
                    for entity in entities.iter() {
                        let param = FunctionParameter {
                            parameter_type: ParameterType::from(
                                entity.parameter_type.clone().unwrap_or("str".to_string()),
                            ),
                            description: entity.description.clone(),
                            required: entity.required,
                            enum_values: entity.enum_values.clone(),
                            default: entity.default.clone(),
                        };
                        properties.insert(entity.name.clone(), param);
                    }
                    properties
                }
                None => HashMap::new(),
            };
            let tools_parameters = FunctionParameters { properties };

            chat_completion_tools.push({
                ChatCompletionTool {
                    tool_type: ToolType::Function,
                    function: FunctionDefinition {
                        name: pt.name.clone(),
                        description: pt.description.clone(),
                        parameters: tools_parameters,
                    },
                }
            });
        }

        // archfc handler needs state so it can expand tool calls
        let mut metadata = HashMap::new();
        metadata.insert(
            ARCH_STATE_HEADER.to_string(),
            serde_json::to_string(&self.arch_state).unwrap(),
        );

        let chat_completions = ChatCompletionsRequest {
            model: self
                .chat_completions_request
                .as_ref()
                .unwrap()
                .model
                .clone(),
            messages: callout_context.request_body.messages.clone(),
            tools: Some(chat_completion_tools),
            stream: false,
            stream_options: None,
            metadata: Some(metadata),
        };

        let msg_body = match serde_json::to_string(&chat_completions) {
            Ok(msg_body) => msg_body,
            Err(e) => {
                warn!("error serializing arch_fc request body: {}", e);
                return self.send_server_error(ServerError::Serialization(e), None);
            }
        };

        let timeout_str = ARCH_FC_REQUEST_TIMEOUT_MS.to_string();

        let mut headers = vec![
            (":method", "POST"),
            (ARCH_UPSTREAM_HOST_HEADER, ARCH_FC_INTERNAL_HOST),
            (":path", "/v1/chat/completions"),
            (":authority", ARCH_FC_INTERNAL_HOST),
            ("content-type", "application/json"),
            ("x-envoy-max-retries", "3"),
            ("x-envoy-upstream-rq-timeout-ms", timeout_str.as_str()),
        ];

        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
        }

        let call_args = CallArgs::new(
            ARCH_INTERNAL_CLUSTER_NAME,
            "/v1/chat/completions",
            headers,
            Some(msg_body.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        callout_context.response_handler_type = ResponseHandlerType::ArchFC;
        callout_context.prompt_target_name = Some(prompt_target.name);

        debug!("archgw => archfc request: {}", msg_body);
        if let Err(e) = self.http_call(call_args, callout_context) {
            debug!("error dispatching arch_fc request: {}", e);
            self.send_server_error(ServerError::HttpDispatch(e), Some(StatusCode::BAD_REQUEST));
        }
    }

    pub fn arch_fc_response_handler(
        &mut self,
        body: Vec<u8>,
        mut callout_context: StreamCallContext,
    ) {
        let body_str = String::from_utf8(body).unwrap();
        debug!("archgw <= archfc response: {}", body_str);

        let arch_fc_response: ChatCompletionsResponse = match serde_json::from_str(&body_str) {
            Ok(arch_fc_response) => arch_fc_response,
            Err(e) => {
                warn!("error deserializing archfc response: {}", e);
                return self.send_server_error(ServerError::Deserialization(e), None);
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
            // Let's send the response back to the user to initalize lightweight dialog for parameter collection

            //TODO: add resolver name to the response so the client can send the response back to the correct resolver

            let direct_response_str = if self.streaming_response {
                let chunks = [
                    ChatCompletionStreamResponse::new(
                        None,
                        Some(ASSISTANT_ROLE.to_string()),
                        Some(ARCH_FC_MODEL_NAME.to_owned()),
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
                    ),
                ];

                let mut response_str = String::new();
                for chunk in chunks.iter() {
                    response_str.push_str("data: ");
                    response_str.push_str(&serde_json::to_string(&chunk).unwrap());
                    response_str.push_str("\n\n");
                }
                response_str
            } else {
                body_str
            };

            if self.streaming_response {}

            self.tool_calls = None;
            return self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![("Powered-By", "Katanemo")],
                Some(direct_response_str.as_bytes()),
            );
        }

        // TODO CO:  pass nli check
        let tools_call_name = self.tool_calls.as_ref().unwrap()[0].function.name.clone();
        let prompt_target = self
            .prompt_targets
            .get(&tools_call_name)
            .expect("prompt target not found for tool call")
            .clone();

        debug!(
            "prompt_target_name: {}, tool_name(s): {:?}",
            prompt_target.name,
            self.tool_calls
                .as_ref()
                .unwrap()
                .iter()
                .map(|tc| tc.function.name.clone())
                .collect::<Vec<String>>(),
        );

        // If hallucination, pass chat template to check parameters
        //HACK: for now we only support one tool call, we will support multiple tool calls in the future

        let mut tool_params = self.tool_calls.as_ref().unwrap()[0]
            .function
            .arguments
            .clone();
        let tool_params_json_str = serde_json::to_string(&tool_params).unwrap();
        debug!(
            "tool_params (without messages history): {}",
            tool_params_json_str
        );
        tool_params.insert(
            String::from(MESSAGES_KEY),
            serde_yaml::to_value(&callout_context.request_body.messages).unwrap(),
        );
        let tool_params_json_str = serde_json::to_string(&tool_params).unwrap();

        use serde_json::Value;
        let v: Value = serde_json::from_str(&tool_params_json_str).unwrap();
        let tool_params_dict: HashMap<String, String> = match v.as_object() {
            Some(obj) => obj
                .iter()
                .map(|(key, value)| {
                    // Convert each value to a string, regardless of its type
                    (key.clone(), value.to_string())
                })
                .collect(),
            None => HashMap::new(), // Return an empty HashMap if v is not an object
        };

        let all_user_messages =
            extract_messages_for_hallucination(&callout_context.request_body.messages);
        let user_messages_str = all_user_messages.join(", ");
        debug!("user messages: {}", user_messages_str);

        let hallucination_classification_request = HallucinationClassificationRequest {
            prompt: user_messages_str,
            model: String::from(DEFAULT_INTENT_MODEL),
            parameters: tool_params_dict,
        };

        let hallucination_request_str: String =
            match serde_json::to_string(&hallucination_classification_request) {
                Ok(json_data) => json_data,
                Err(error) => {
                    debug!(
                        "error serializing hallucination classification request: {}",
                        error
                    );
                    return self.send_server_error(ServerError::Serialization(error), None);
                }
            };

        let mut headers = vec![
            (ARCH_UPSTREAM_HOST_HEADER, HALLUCINATION_INTERNAL_HOST),
            (":method", "POST"),
            (":path", "/hallucination"),
            (":authority", HALLUCINATION_INTERNAL_HOST),
            ("content-type", "application/json"),
            ("x-envoy-max-retries", "3"),
            ("x-envoy-upstream-rq-timeout-ms", "60000"),
        ];

        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
        }

        let call_args = CallArgs::new(
            ARCH_INTERNAL_CLUSTER_NAME,
            "/hallucination",
            headers,
            Some(hallucination_request_str.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        callout_context.response_handler_type = ResponseHandlerType::Hallucination;

        debug!(
            "archgw => hallucination request: {}",
            hallucination_request_str
        );
        if let Err(e) = self.http_call(call_args, callout_context) {
            self.send_server_error(ServerError::HttpDispatch(e), None);
        }
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

        let mut headers = vec![
            (ARCH_UPSTREAM_HOST_HEADER, endpoint.name.as_str()),
            (":method", "POST"),
            (":path", &path),
            (":authority", endpoint.name.as_str()),
            ("content-type", "application/json"),
            ("x-envoy-max-retries", "3"),
        ];

        if self.request_id.is_some() {
            headers.push((REQUEST_ID_HEADER, self.request_id.as_ref().unwrap()));
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
            "archgw => api call, endpoint: {}/{}, body: {}",
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
            .expect("http status code not found");
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
        let prompt_target_name = callout_context.prompt_target_name.unwrap();
        let prompt_target = self
            .prompt_targets
            .get(&prompt_target_name)
            .unwrap()
            .clone();

        let mut messages: Vec<Message> = Vec::new();

        // add system prompt
        let system_prompt = match prompt_target.system_prompt.as_ref() {
            None => self.system_prompt.as_ref().clone(),
            Some(system_prompt) => Some(system_prompt.clone()),
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
            if m.role == TOOL_ROLE || m.content.is_none() {
                continue;
            }
            messages.push(m.clone());
        }

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

        self.set_http_request_body(0, self.request_body_size, &llm_request_str.into_bytes());
        self.resume_http_request();
    }

    pub fn arch_guard_handler(&mut self, body: Vec<u8>, callout_context: StreamCallContext) {
        let prompt_guard_resp: PromptGuardResponse = serde_json::from_slice(&body).unwrap();
        debug!(
            "archgw <= archguard response: {:?}",
            serde_json::to_string(&prompt_guard_resp)
        );

        if prompt_guard_resp.jailbreak_verdict.unwrap_or_default() {
            //TODO: handle other scenarios like forward to error target
            let msg = self
                .prompt_guards
                .jailbreak_on_exception_message()
                .unwrap_or("refrain from discussing jailbreaking.");
            warn!("jailbreak detected: {}", msg);
            return self.send_server_error(
                ServerError::Jailbreak(String::from(msg)),
                Some(StatusCode::BAD_REQUEST),
            );
        }

        self.get_embeddings(callout_context);
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
                    serde_json::from_slice::<ChatCompletionsResponse>(&body).unwrap();

                let chunks = [
                    ChatCompletionStreamResponse::new(
                        None,
                        Some(ASSISTANT_ROLE.to_string()),
                        Some(chat_completion_response.model.clone()),
                    ),
                    ChatCompletionStreamResponse::new(
                        chat_completion_response.choices[0].message.content.clone(),
                        None,
                        Some(chat_completion_response.model.clone()),
                    ),
                ];

                let mut response_str = String::new();
                for chunk in chunks.iter() {
                    response_str.push_str("data: ");
                    response_str.push_str(&serde_json::to_string(&chunk).unwrap());
                    response_str.push_str("\n\n");
                }
                response_str
            } else {
                String::from_utf8(body).unwrap()
            };

            self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![("Powered-By", "Katanemo")],
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
