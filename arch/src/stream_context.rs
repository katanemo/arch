use crate::consts::{
    ARCH_FC_MODEL_NAME, ARCH_FC_REQUEST_TIMEOUT_MS, ARCH_MESSAGES_KEY, ARCH_PROVIDER_HINT_HEADER,
    ARCH_ROUTING_HEADER, ARCH_STATE_HEADER, ARC_FC_CLUSTER, CHAT_COMPLETIONS_PATH,
    DEFAULT_EMBEDDING_MODEL, DEFAULT_HALLUCINATED_THRESHOLD, DEFAULT_INTENT_MODEL,
    DEFAULT_PROMPT_TARGET_THRESHOLD, GPT_35_TURBO, MODEL_SERVER_NAME,
    RATELIMIT_SELECTOR_HEADER_KEY, SYSTEM_ROLE, USER_ROLE,
};
use crate::filter_context::{EmbeddingsStore, WasmMetrics};
use crate::http::{CallArgs, Client, ClientError};
use crate::llm_providers::LlmProviders;
use crate::ratelimit::Header;
use crate::stats::IncrementingMetric;
use crate::{ratelimit, routing, tokenizer};
use acap::cos;
use http::StatusCode;
use log::{debug, info, warn};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use public_types::common_types::open_ai::{
    ArchState, ChatCompletionChunkResponse, ChatCompletionTool, ChatCompletionsRequest,
    ChatCompletionsResponse, Choice, FunctionDefinition, FunctionParameter, FunctionParameters,
    Message, ParameterType, StreamOptions, ToolCall, ToolCallState, ToolType,
};
use public_types::common_types::{
    EmbeddingType, HallucinationClassificationRequest, HallucinationClassificationResponse,
    PromptGuardRequest, PromptGuardResponse, PromptGuardTask, ZeroShotClassificationRequest,
    ZeroShotClassificationResponse,
};
use public_types::configuration::LlmProvider;
use public_types::configuration::{Overrides, PromptGuards, PromptTarget};
use public_types::embeddings::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::cell::RefCell;
use std::collections::HashMap;
use std::num::NonZero;
use std::rc::Rc;
use std::time::Duration;

#[derive(Debug, Clone)]
enum ResponseHandlerType {
    GetEmbeddings,
    FunctionResolver,
    FunctionCall,
    ZeroShotIntent,
    HallucinationDetect,
    ArchGuard,
    DefaultTarget,
}

#[derive(Debug, Clone)]
pub struct StreamCallContext {
    response_handler_type: ResponseHandlerType,
    user_message: Option<String>,
    prompt_target_name: Option<String>,
    request_body: ChatCompletionsRequest,
    tool_calls: Option<Vec<ToolCall>>,
    similarity_scores: Option<Vec<(String, f64)>>,
    upstream_cluster: Option<String>,
    upstream_cluster_path: Option<String>,
}

#[derive(thiserror::Error, Debug)]
pub enum ServerError {
    #[error(transparent)]
    HttpDispatch(ClientError),
    #[error(transparent)]
    Deserialization(serde_json::Error),
    #[error(transparent)]
    Serialization(serde_json::Error),
    #[error("{0}")]
    LogicError(String),
    #[error("upstream error response authority={authority}, path={path}, status={status}")]
    Upstream {
        authority: String,
        path: String,
        status: String,
    },
    #[error(transparent)]
    ExceededRatelimit(ratelimit::Error),
    #[error("jailbreak detected: {0}")]
    Jailbreak(String),
    #[error("{why}")]
    BadRequest { why: String },
}

pub struct StreamContext {
    context_id: u32,
    metrics: Rc<WasmMetrics>,
    prompt_targets: Rc<HashMap<String, PromptTarget>>,
    embeddings_store: Rc<EmbeddingsStore>,
    overrides: Rc<Option<Overrides>>,
    callouts: RefCell<HashMap<u32, StreamCallContext>>,
    tool_calls: Option<Vec<ToolCall>>,
    tool_call_response: Option<String>,
    arch_state: Option<Vec<ArchState>>,
    request_body_size: usize,
    ratelimit_selector: Option<Header>,
    streaming_response: bool,
    user_prompt: Option<Message>,
    response_tokens: usize,
    is_chat_completions_request: bool,
    chat_completions_request: Option<ChatCompletionsRequest>,
    prompt_guards: Rc<PromptGuards>,
    llm_providers: Rc<LlmProviders>,
    llm_provider: Option<Rc<LlmProvider>>,
}

impl StreamContext {
    pub fn new(
        context_id: u32,
        metrics: Rc<WasmMetrics>,
        prompt_targets: Rc<HashMap<String, PromptTarget>>,
        prompt_guards: Rc<PromptGuards>,
        overrides: Rc<Option<Overrides>>,
        llm_providers: Rc<LlmProviders>,
        embeddings_store: Rc<EmbeddingsStore>,
    ) -> Self {
        StreamContext {
            context_id,
            metrics,
            prompt_targets,
            embeddings_store,
            callouts: RefCell::new(HashMap::new()),
            chat_completions_request: None,
            tool_calls: None,
            tool_call_response: None,
            arch_state: None,
            request_body_size: 0,
            ratelimit_selector: None,
            streaming_response: false,
            user_prompt: None,
            response_tokens: 0,
            is_chat_completions_request: false,
            llm_providers,
            llm_provider: None,
            prompt_guards,
            overrides,
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

        self.llm_provider = Some(routing::get_llm_provider(
            &self.llm_providers,
            provider_hint,
        ));
    }

    fn add_routing_header(&mut self) {
        self.add_http_request_header(ARCH_ROUTING_HEADER, &self.llm_provider().name);
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

    fn embeddings_handler(&mut self, body: Vec<u8>, mut callout_context: StreamCallContext) {
        let embedding_response: CreateEmbeddingResponse = match serde_json::from_slice(&body) {
            Ok(embedding_response) => embedding_response,
            Err(e) => {
                return self.send_server_error(ServerError::Deserialization(e), None);
            }
        };

        let prompt_embeddings_vector = &embedding_response.data[0].embedding;

        debug!(
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
                let pte = match self.embeddings_store.get(prompt_name) {
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
                return self.send_server_error(ServerError::Serialization(error), None);
            }
        };

        let call_args = CallArgs::new(
            MODEL_SERVER_NAME,
            "/zeroshot",
            vec![
                (":method", "POST"),
                (":path", "/zeroshot"),
                (":authority", MODEL_SERVER_NAME),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
                ("x-envoy-upstream-rq-timeout-ms", "60000"),
            ],
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        callout_context.response_handler_type = ResponseHandlerType::ZeroShotIntent;

        if let Err(e) = self.http_call(call_args, callout_context) {
            self.send_server_error(ServerError::HttpDispatch(e), None);
        }
    }

    // compute the hallucination score, print handler
    // resume the flow
    // pr for zershot vs hallucination
    fn hallucination_classification_resp_handler(
        &mut self,
        body: Vec<u8>,
        callout_context: StreamCallContext,
    ) {
        let hallucination_response: HallucinationClassificationResponse =
            match serde_json::from_slice(&body) {
                Ok(hallucination_response) => hallucination_response,
                Err(e) => {
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
                "It seems I’m missing some information. Could you provide the following details: "
                    .to_string()
                    + &keys_with_low_score.join(", ")
                    + " ?";
            let message = Message {
                role: SYSTEM_ROLE.to_string(),
                content: Some(response),
                model: Some(ARCH_FC_MODEL_NAME.to_string()),
                tool_calls: None,
            };

            let chat_completion_response = ChatCompletionsResponse {
                choices: vec![Choice {
                    message,
                    index: 0,
                    finish_reason: "done".to_string(),
                }],
                usage: None,
                model: ARCH_FC_MODEL_NAME.to_string(),
                metadata: None,
            };

            debug!("hallucination response: {:?}", chat_completion_response);
            self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![("Powered-By", "Katanemo")],
                Some(
                    serde_json::to_string(&chat_completion_response)
                        .unwrap()
                        .as_bytes(),
                ),
            );
        } else {
            // not a hallucination, resume the flow
            self.schedule_api_call_request(callout_context);
        }
    }

    fn zero_shot_intent_detection_resp_handler(
        &mut self,
        body: Vec<u8>,
        mut callout_context: StreamCallContext,
    ) {
        let zeroshot_intent_response: ZeroShotClassificationResponse =
            match serde_json::from_slice(&body) {
                Ok(zeroshot_response) => zeroshot_response,
                Err(e) => {
                    return self.send_server_error(ServerError::Deserialization(e), None);
                }
            };

        debug!("zeroshot intent response: {:?}", zeroshot_intent_response);

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
                if model.contains("Arch") {
                    arch_assistant = true;
                }
            }
        } else {
            info!("no assistant message found, probably first interaction");
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
                info!("arch assistant is handling the conversation");
            } else {
                debug!("checking for default prompt target");
                if let Some(default_prompt_target) = self
                    .prompt_targets
                    .values()
                    .find(|pt| pt.default.unwrap_or(false))
                {
                    debug!("default prompt target found");
                    let endpoint = default_prompt_target.endpoint.clone().unwrap();
                    let upstream_path: String = endpoint.path.unwrap_or(String::from("/"));

                    let upstream_endpoint = endpoint.name;
                    let mut params = HashMap::new();
                    params.insert(
                        ARCH_MESSAGES_KEY.to_string(),
                        callout_context.request_body.messages.clone(),
                    );
                    let arch_messages_json = serde_json::to_string(&params).unwrap();
                    debug!("no prompt target found with similarity score above threshold, using default prompt target");

                    let timeout_str = ARCH_FC_REQUEST_TIMEOUT_MS.to_string();
                    let call_args = CallArgs::new(
                        &upstream_endpoint,
                        &upstream_path,
                        vec![
                            (":method", "POST"),
                            (":path", &upstream_path),
                            (":authority", &upstream_endpoint),
                            ("content-type", "application/json"),
                            ("x-envoy-max-retries", "3"),
                            ("x-envoy-upstream-rq-timeout-ms", timeout_str.as_str()),
                        ],
                        Some(arch_messages_json.as_bytes()),
                        vec![],
                        Duration::from_secs(5),
                    );
                    callout_context.response_handler_type = ResponseHandlerType::DefaultTarget;
                    callout_context.prompt_target_name = Some(default_prompt_target.name.clone());

                    if let Err(e) = self.http_call(call_args, callout_context) {
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

        let prompt_target = match self.prompt_targets.get(&prompt_target_name) {
            Some(prompt_target) => prompt_target.clone(),
            None => {
                return self.send_server_error(
                    ServerError::LogicError(format!(
                        "Prompt target not found: {prompt_target_name}"
                    )),
                    None,
                );
            }
        };

        info!("prompt_target name: {:?}", prompt_target_name);
        let mut chat_completion_tools: Vec<ChatCompletionTool> = Vec::new();
        for pt in self.prompt_targets.values() {
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
            model: GPT_35_TURBO.to_string(),
            messages: callout_context.request_body.messages.clone(),
            tools: Some(chat_completion_tools),
            stream: false,
            stream_options: None,
            metadata: Some(metadata),
        };

        let msg_body = match serde_json::to_string(&chat_completions) {
            Ok(msg_body) => {
                debug!("arch_fc request body content: {}", msg_body);
                msg_body
            }
            Err(e) => {
                return self.send_server_error(ServerError::Serialization(e), None);
            }
        };

        let timeout_str = ARCH_FC_REQUEST_TIMEOUT_MS.to_string();
        let call_args = CallArgs::new(
            ARC_FC_CLUSTER,
            "/v1/chat/completions",
            vec![
                (":method", "POST"),
                (":path", "/v1/chat/completions"),
                (":authority", ARC_FC_CLUSTER),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
                ("x-envoy-upstream-rq-timeout-ms", timeout_str.as_str()),
            ],
            Some(msg_body.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        callout_context.response_handler_type = ResponseHandlerType::FunctionResolver;
        callout_context.prompt_target_name = Some(prompt_target.name);

        if let Err(e) = self.http_call(call_args, callout_context) {
            self.send_server_error(ServerError::HttpDispatch(e), Some(StatusCode::BAD_REQUEST));
        }
    }

    fn function_resolver_handler(&mut self, body: Vec<u8>, mut callout_context: StreamCallContext) {
        let body_str = String::from_utf8(body).unwrap();
        debug!("arch <= app response body: {}", body_str);

        let arch_fc_response: ChatCompletionsResponse = match serde_json::from_str(&body_str) {
            Ok(arch_fc_response) => arch_fc_response,
            Err(e) => {
                return self.send_server_error(ServerError::Deserialization(e), None);
            }
        };

        let model_resp = &arch_fc_response.choices[0];

        if model_resp.message.tool_calls.is_none()
            || model_resp.message.tool_calls.as_ref().unwrap().is_empty()
        {
            // This means that Arch FC did not have enough information to resolve the function call
            // Arch FC probably responded with a message asking for more information.
            // Let's send the response back to the user to initalize lightweight dialog for parameter collection

            //TODO: add resolver name to the response so the client can send the response back to the correct resolver

            return self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![("Powered-By", "Katanemo")],
                Some(body_str.as_bytes()),
            );
        }

        let tool_calls = model_resp.message.tool_calls.as_ref().unwrap();

        // TODO CO:  pass nli check
        // If hallucination, pass chat template to check parameters

        // extract all tool names
        let tool_names: Vec<String> = tool_calls
            .iter()
            .map(|tool_call| tool_call.function.name.clone())
            .collect();

        debug!(
            "call context similarity score: {:?}",
            callout_context.similarity_scores
        );
        //HACK: for now we only support one tool call, we will support multiple tool calls in the future
        let mut tool_params = tool_calls[0].function.arguments.clone();
        tool_params.insert(
            String::from(ARCH_MESSAGES_KEY),
            serde_yaml::to_value(&callout_context.request_body.messages).unwrap(),
        );

        let tools_call_name = tool_calls[0].function.name.clone();
        let tool_params_json_str = serde_json::to_string(&tool_params).unwrap();
        let prompt_target = self.prompt_targets.get(&tools_call_name).unwrap().clone();
        callout_context.tool_calls = Some(tool_calls.clone());

        debug!(
            "prompt_target_name: {}, tool_name(s): {:?}",
            prompt_target.name, tool_names
        );
        debug!("tool_params: {}", tool_params_json_str);

        if model_resp.message.tool_calls.is_some()
            && !model_resp.message.tool_calls.as_ref().unwrap().is_empty()
        {
            use serde_json::Value;
            let v: Value = serde_json::from_str(&tool_params_json_str).unwrap();
            let tool_params_dict: HashMap<String, String> = match v.as_object() {
                Some(obj) => obj
                    .iter()
                    .filter_map(|(key, value)| {
                        value
                            .as_str()
                            .map(|str_value| (key.clone(), str_value.to_string()))
                    })
                    .collect(),
                None => HashMap::new(), // Return an empty HashMap if v is not an object
            };

            let hallucination_classification_request = HallucinationClassificationRequest {
                prompt: callout_context.user_message.as_ref().unwrap().clone(),
                model: String::from(DEFAULT_INTENT_MODEL),
                parameters: tool_params_dict,
            };

            let json_data: String =
                match serde_json::to_string(&hallucination_classification_request) {
                    Ok(json_data) => json_data,
                    Err(error) => {
                        return self.send_server_error(ServerError::Serialization(error), None);
                    }
                };
            let call_args = CallArgs::new(
                MODEL_SERVER_NAME,
                "/hallucination",
                vec![
                    (":method", "POST"),
                    (":path", "/hallucination"),
                    (":authority", MODEL_SERVER_NAME),
                    ("content-type", "application/json"),
                    ("x-envoy-max-retries", "3"),
                    ("x-envoy-upstream-rq-timeout-ms", "60000"),
                ],
                Some(json_data.as_bytes()),
                vec![],
                Duration::from_secs(5),
            );
            callout_context.response_handler_type = ResponseHandlerType::HallucinationDetect;

            if let Err(e) = self.http_call(call_args, callout_context.clone()) {
                self.send_server_error(ServerError::HttpDispatch(e), None);
            }
            let callout_context_clone = callout_context.clone();
            self.metrics.active_http_calls.increment(1);
            let token_id = 1;
            if self
                .callouts
                .borrow_mut()
                .insert(
                    token_id,
                    StreamCallContext {
                        response_handler_type: ResponseHandlerType::HallucinationDetect,
                        user_message: callout_context_clone.user_message.clone(),
                        prompt_target_name: callout_context_clone.prompt_target_name.clone(),
                        request_body: callout_context_clone.request_body.clone(),
                        similarity_scores: callout_context_clone.similarity_scores.clone(),
                        upstream_cluster: callout_context_clone.upstream_cluster.clone(),
                        upstream_cluster_path: callout_context_clone.upstream_cluster_path.clone(),
                        tool_calls: callout_context_clone.tool_calls.clone(),
                    },
                )
                .is_some()
            {
                panic!("duplicate token_id")
            }
        } else {
            self.schedule_api_call_request(callout_context);
        }
    }

    fn schedule_api_call_request(&mut self, mut callout_context: StreamCallContext) {
        let tools_call_name = callout_context.tool_calls.as_ref().unwrap()[0]
            .function
            .name
            .clone();

        let prompt_target = self.prompt_targets.get(&tools_call_name).unwrap().clone();

        //HACK: for now we only support one tool call, we will support multiple tool calls in the future
        let mut tool_params = callout_context.tool_calls.as_ref().unwrap()[0]
            .function
            .arguments
            .clone();
        tool_params.insert(
            String::from(ARCH_MESSAGES_KEY),
            serde_yaml::to_value(&callout_context.request_body.messages).unwrap(),
        );

        let tool_params_json_str = serde_json::to_string(&tool_params).unwrap();

        let endpoint = prompt_target.endpoint.unwrap();
        let path: String = endpoint.path.unwrap_or(String::from("/"));
        let call_args = CallArgs::new(
            &endpoint.name,
            &path,
            vec![
                (":method", "POST"),
                (":path", &path),
                (":authority", endpoint.name.as_str()),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
            ],
            Some(tool_params_json_str.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        callout_context.upstream_cluster = Some(endpoint.name.clone());
        callout_context.upstream_cluster_path = Some(path.clone());
        callout_context.response_handler_type = ResponseHandlerType::FunctionCall;

        if let Err(e) = self.http_call(call_args, callout_context) {
            self.send_server_error(ServerError::HttpDispatch(e), Some(StatusCode::BAD_REQUEST));
        }
    }

    fn function_call_response_handler(
        &mut self,
        body: Vec<u8>,
        callout_context: StreamCallContext,
    ) {
        if let Some(http_status) = self.get_http_call_response_header(":status") {
            if http_status != StatusCode::OK.as_str() {
                return self.send_server_error(
                    ServerError::Upstream {
                        authority: callout_context.upstream_cluster.unwrap(),
                        path: callout_context.upstream_cluster_path.unwrap(),
                        status: http_status,
                    },
                    None,
                );
            }
        } else {
            warn!("http status code not found in api response");
        }
        let body_str: String = String::from_utf8(body).unwrap();
        self.tool_call_response = Some(body_str.clone());
        debug!("arch <= app response body: {}", body_str);
        let prompt_target_name = callout_context.prompt_target_name.unwrap();
        let prompt_target = self
            .prompt_targets
            .get(&prompt_target_name)
            .unwrap()
            .clone();

        let mut messages: Vec<Message> = callout_context.request_body.messages.clone();

        // add system prompt
        match prompt_target.system_prompt.as_ref() {
            None => {}
            Some(system_prompt) => {
                let system_prompt_message = Message {
                    role: SYSTEM_ROLE.to_string(),
                    content: Some(system_prompt.clone()),
                    model: None,
                    tool_calls: None,
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
                tool_calls: None,
            }
        });

        // add original user prompt
        messages.push({
            Message {
                role: USER_ROLE.to_string(),
                content: Some(callout_context.user_message.unwrap()),
                model: None,
                tool_calls: None,
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

        let json_string = match serde_json::to_string(&chat_completions_request) {
            Ok(json_string) => json_string,
            Err(e) => {
                return self.send_server_error(ServerError::Serialization(e), None);
            }
        };
        debug!("arch => openai request body: {}", json_string);

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
                        self.send_server_error(
                            ServerError::ExceededRatelimit(err),
                            Some(StatusCode::TOO_MANY_REQUESTS),
                        );
                        self.metrics.ratelimited_rq.increment(1);
                        return;
                    }
                }
            }
        }

        self.set_http_request_body(0, self.request_body_size, &json_string.into_bytes());
        self.resume_http_request();
    }

    fn arch_guard_handler(&mut self, body: Vec<u8>, callout_context: StreamCallContext) {
        debug!("response received for arch guard");
        let prompt_guard_resp: PromptGuardResponse = serde_json::from_slice(&body).unwrap();
        debug!("prompt_guard_resp: {:?}", prompt_guard_resp);

        if prompt_guard_resp.jailbreak_verdict.unwrap_or_default() {
            //TODO: handle other scenarios like forward to error target
            let msg = self
                .prompt_guards
                .jailbreak_on_exception_message()
                .unwrap_or("refrain from discussing jailbreaking.");
            return self.send_server_error(
                ServerError::Jailbreak(String::from(msg)),
                Some(StatusCode::BAD_REQUEST),
            );
        }

        self.get_embeddings(callout_context);
    }

    fn get_embeddings(&mut self, callout_context: StreamCallContext) {
        let user_message = callout_context.user_message.unwrap();
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
                return self.send_server_error(ServerError::Deserialization(error), None);
            }
        };

        let call_args = CallArgs::new(
            MODEL_SERVER_NAME,
            "/embeddings",
            vec![
                (":method", "POST"),
                (":path", "/embeddings"),
                (":authority", MODEL_SERVER_NAME),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
                ("x-envoy-upstream-rq-timeout-ms", "60000"),
            ],
            Some(json_data.as_bytes()),
            vec![],
            Duration::from_secs(5),
        );
        let call_context = StreamCallContext {
            response_handler_type: ResponseHandlerType::GetEmbeddings,
            user_message: Some(user_message),
            prompt_target_name: None,
            request_body: callout_context.request_body,
            similarity_scores: None,
            upstream_cluster: None,
            upstream_cluster_path: None,
            tool_calls: None,
        };

        if let Err(e) = self.http_call(call_args, call_context) {
            self.send_server_error(ServerError::HttpDispatch(e), None);
        }
    }

    fn default_target_handler(&self, body: Vec<u8>, callout_context: StreamCallContext) {
        let prompt_target = self
            .prompt_targets
            .get(callout_context.prompt_target_name.as_ref().unwrap())
            .unwrap()
            .clone();
        debug!(
            "response received for default target: {}",
            prompt_target.name
        );
        // check if the default target should be dispatched to the LLM provider
        if !prompt_target.auto_llm_dispatch_on_response.unwrap_or(false) {
            let default_target_response_str = String::from_utf8(body).unwrap();
            debug!(
                "sending response back to developer: {}",
                default_target_response_str
            );
            self.send_http_response(
                StatusCode::OK.as_u16().into(),
                vec![("Powered-By", "Katanemo")],
                Some(default_target_response_str.as_bytes()),
            );
            // self.resume_http_request();
            return;
        }
        debug!("default_target: sending api response to default llm");
        let chat_completions_resp: ChatCompletionsResponse = match serde_json::from_slice(&body) {
            Ok(chat_completions_resp) => chat_completions_resp,
            Err(e) => {
                return self.send_server_error(ServerError::Deserialization(e), None);
            }
        };
        let api_resp = chat_completions_resp.choices[0]
            .message
            .content
            .as_ref()
            .unwrap();
        let mut messages = callout_context.request_body.messages;

        // add system prompt
        match prompt_target.system_prompt.as_ref() {
            None => {}
            Some(system_prompt) => {
                let system_prompt_message = Message {
                    role: SYSTEM_ROLE.to_string(),
                    content: Some(system_prompt.clone()),
                    model: None,
                    tool_calls: None,
                };
                messages.push(system_prompt_message);
            }
        }

        messages.push(Message {
            role: USER_ROLE.to_string(),
            content: Some(api_resp.clone()),
            model: None,
            tool_calls: None,
        });
        let chat_completion_request = ChatCompletionsRequest {
            model: GPT_35_TURBO.to_string(),
            messages,
            tools: None,
            stream: callout_context.request_body.stream,
            stream_options: callout_context.request_body.stream_options,
            metadata: None,
        };
        let json_resp = serde_json::to_string(&chat_completion_request).unwrap();
        debug!("sending response back to default llm: {}", json_resp);
        self.set_http_request_body(0, self.request_body_size, json_resp.as_bytes());
        self.resume_http_request();
    }
}

// HttpContext is the trait that allows the Rust code to interact with HTTP objects.
impl HttpContext for StreamContext {
    // Envoy's HTTP model is event driven. The WASM ABI has given implementors events to hook onto
    // the lifecycle of the http request and response.
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        self.select_llm_provider();
        self.add_routing_header();
        if let Err(error) = self.modify_auth_headers() {
            self.send_server_error(error, Some(StatusCode::BAD_REQUEST));
        }
        self.delete_content_length_header();
        self.save_ratelimit_header();

        self.is_chat_completions_request =
            self.get_http_request_header(":path").unwrap_or_default() == CHAT_COMPLETIONS_PATH;

        debug!(
            "S[{}] req_headers={:?}",
            self.context_id,
            self.get_http_request_headers()
        );

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

        self.is_chat_completions_request = true;
        // Set the model based on the chosen LLM Provider
        deserialized_body.model = String::from(&self.llm_provider().model);

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
            .contains_key(&public_types::configuration::GuardType::Jailbreak);

        self.chat_completions_request = Some(deserialized_body);

        if !prompt_guard_jailbreak_task {
            debug!("Missing input guard. Making inline call to retrieve");
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

        let call_args = CallArgs::new(
            MODEL_SERVER_NAME,
            "/guard",
            vec![
                (":method", "POST"),
                (":path", "/guard"),
                (":authority", MODEL_SERVER_NAME),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
                ("x-envoy-upstream-rq-timeout-ms", "60000"),
            ],
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

        if let Some(body) = self.get_http_call_response_body(0, body_size) {
            match callout_context.response_handler_type {
                ResponseHandlerType::GetEmbeddings => {
                    self.embeddings_handler(body, callout_context)
                }
                ResponseHandlerType::ZeroShotIntent => {
                    self.zero_shot_intent_detection_resp_handler(body, callout_context)
                }
                ResponseHandlerType::HallucinationDetect => {
                    self.hallucination_classification_resp_handler(body, callout_context)
                }
                ResponseHandlerType::FunctionResolver => {
                    self.function_resolver_handler(body, callout_context)
                }
                ResponseHandlerType::FunctionCall => {
                    self.function_call_response_handler(body, callout_context)
                }
                ResponseHandlerType::ArchGuard => self.arch_guard_handler(body, callout_context),
                ResponseHandlerType::DefaultTarget => {
                    self.default_target_handler(body, callout_context)
                }
            }
        } else {
            self.send_server_error(
                ServerError::LogicError(String::from("No response body in inline HTTP request")),
                None,
            );
        }
    }
}

impl Client for StreamContext {
    type CallContext = StreamCallContext;

    fn callouts(&self) -> &RefCell<HashMap<u32, Self::CallContext>> {
        &self.callouts
    }

    fn active_http_calls(&self) -> &crate::stats::Gauge {
        &self.metrics.active_http_calls
    }
}
