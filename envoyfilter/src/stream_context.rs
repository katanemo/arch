use crate::consts::{
    DEFAULT_COLLECTION_NAME, DEFAULT_EMBEDDING_MODEL, DEFAULT_NER_MODEL, DEFAULT_NER_THRESHOLD,
    DEFAULT_PROMPT_TARGET_THRESHOLD, RATELIMIT_SELECTOR_HEADER_KEY, SYSTEM_ROLE, USER_ROLE,
};
use crate::ratelimit;
use crate::ratelimit::Header;
use crate::tokenizer;
use http::StatusCode;
use log::{debug, error, info, warn};
use open_message_format_embeddings::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use public_types::common_types::{
    open_ai::{ChatCompletions, Message},
    NERRequest, NERResponse, SearchPointsRequest, SearchPointsResponse,
};
use public_types::configuration::{Entity, PromptTarget};
use std::collections::HashMap;
use std::num::NonZero;
use std::time::Duration;

enum RequestType {
    GetEmbedding,
    SearchPoints,
    Ner,
    ContextResolver,
}

pub struct CallContext {
    request_type: RequestType,
    user_message: Option<String>,
    prompt_target: Option<PromptTarget>,
    request_body: ChatCompletions,
}

pub struct StreamContext {
    pub host_header: Option<String>,
    pub ratelimit_selector: Option<Header>,
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

    fn save_ratelimit_header(&mut self) {
        self.ratelimit_selector =
            if let Some(key) = self.get_http_request_header(RATELIMIT_SELECTOR_HEADER_KEY) {
                self.get_http_request_header(&key)
                    .map(|value| Header { key, value })
            } else {
                None
            };
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

        if search_results[0].score < DEFAULT_PROMPT_TARGET_THRESHOLD {
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

        // only extract entity names
        let entity_names: Vec<String> = match prompt_target.entities {
            // Clone is unavoidable here because we don't want to move the values out of the prompt target struct.
            Some(ref entities) => entities.iter().map(|entity| entity.name.clone()).collect(),
            None => vec![],
        };

        let ner_request = NERRequest {
            input: callout_context.user_message.take().unwrap(),
            labels: entity_names,
            model: DEFAULT_NER_MODEL.to_string(),
        };

        let json_data: String = match serde_json::to_string(&ner_request) {
            Ok(json_data) => json_data,
            Err(e) => {
                warn!("Error serializing ner_request: {:?}", e);
                self.resume_http_request();
                return;
            }
        };

        let token_id = match self.dispatch_http_call(
            "nerhost",
            vec![
                (":method", "POST"),
                (":path", "/ner"),
                (":authority", "nerhost"),
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
        callout_context.request_type = RequestType::Ner;
        callout_context.prompt_target = Some(prompt_target);
        if self.callouts.insert(token_id, callout_context).is_some() {
            panic!("duplicate token_id")
        }
    }

    fn ner_handler(&mut self, body: Vec<u8>, mut callout_context: CallContext) {
        let ner_response: NERResponse = match serde_json::from_slice(&body) {
            Ok(ner_response) => ner_response,
            Err(e) => {
                warn!("Error deserializing ner_response: {:?}", e);
                self.resume_http_request();
                return;
            }
        };
        info!("ner_response: {:?}", ner_response);

        let mut request_params: HashMap<String, String> = HashMap::new();
        for entity in ner_response.data.into_iter() {
            if entity.score < DEFAULT_NER_THRESHOLD {
                warn!(
                    "score of entity was too low entity name: {}, score: {}",
                    entity.label, entity.score
                );
                continue;
            }
            request_params.insert(entity.label, entity.text);
        }

        let prompt_target = callout_context.prompt_target.as_ref().unwrap();

        let empty_vec: Vec<Entity> = vec![];
        for entity in prompt_target.entities.as_ref().unwrap_or(&empty_vec) {
            if entity.required.unwrap_or(false) && !request_params.contains_key(&entity.name) {
                warn!(
                    "required entity missing or score of entity was too low: {}",
                    entity.name
                );
                self.resume_http_request();
                return;
            }
        }

        let req_param_bytes = match serde_json::to_string(&request_params) {
            Ok(req_param_str) => req_param_str.as_bytes().to_owned(),
            Err(e) => {
                warn!("Error serializing request_params: {:?}", e);
                self.resume_http_request();
                return;
            }
        };

        let endpoint = callout_context
            .prompt_target
            .as_ref()
            .unwrap()
            .endpoint
            .as_ref()
            .unwrap();

        let http_path = match &endpoint.path {
            Some(path) => path,
            None => "/",
        };

        let http_method = match &endpoint.method {
            Some(method) => method,
            None => http::Method::POST.as_str(),
        };

        let token_id = match self.dispatch_http_call(
            &endpoint.cluster,
            vec![
                (":method", http_method),
                (":path", http_path),
                (":authority", endpoint.cluster.as_str()),
                ("content-type", "application/json"),
                ("x-envoy-max-retries", "3"),
            ],
            Some(&req_param_bytes),
            vec![],
            Duration::from_secs(5),
        ) {
            Ok(token_id) => token_id,
            Err(e) => {
                panic!("Error dispatching HTTP call for context_resolver: {:?}", e);
            }
        };
        callout_context.request_type = RequestType::ContextResolver;
        if self.callouts.insert(token_id, callout_context).is_some() {
            panic!("duplicate token_id")
        }
    }

    fn context_resolver_handler(&mut self, body: Vec<u8>, callout_context: CallContext) {
        debug!("response received for context_resolver");
        let body_string = String::from_utf8(body);
        let prompt_target = callout_context.prompt_target.unwrap();
        let mut request_body = callout_context.request_body;
        match prompt_target.system_prompt {
            None => {}
            Some(system_prompt) => {
                let system_prompt_message: Message = Message {
                    role: SYSTEM_ROLE.to_string(),
                    content: Some(system_prompt),
                };
                request_body.messages.push(system_prompt_message);
            }
        }
        match body_string {
            Ok(body_string) => {
                info!("context_resolver response: {}", body_string);
                let context_resolver_response = Message {
                    role: USER_ROLE.to_string(),
                    content: Some(body_string),
                };
                request_body.messages.push(context_resolver_response);
            }
            Err(e) => {
                warn!("Error converting response to string: {:?}", e);
                self.resume_http_request();
                return;
            }
        }

        let json_string = match serde_json::to_string(&request_body) {
            Ok(json_string) => json_string,
            Err(e) => {
                warn!("Error serializing request_body: {:?}", e);
                self.resume_http_request();
                return;
            }
        };

        // Tokenize and Ratelimit.
        if let Some(selector) = self.ratelimit_selector.take() {
            if let Ok(token_count) = tokenizer::token_count(&request_body.model, &json_string) {
                match ratelimit::ratelimits(None).read().unwrap().check_limit(
                    request_body.model,
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
        let mut deserialized_body: ChatCompletions = match self.get_http_request_body(0, body_size)
        {
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
            .pop()
            .and_then(|last_message| last_message.content)
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
            RequestType::Ner => self.ner_handler(body, callout_context),
            RequestType::ContextResolver => self.context_resolver_handler(body, callout_context),
        }
    }
}
