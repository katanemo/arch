use http::StatusCode;
use log::error;
use log::info;
use log::warn;
use open_message_format::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use serde_json::to_string;
use std::collections::HashMap;
use std::time::Duration;

use proxy_wasm::traits::*;
use proxy_wasm::types::*;

use crate::common_types;

use crate::common_types::open_ai::Message;
use crate::common_types::SearchPointsResponse;
use crate::configuration::EntityDetail;
use crate::configuration::EntityType;
use crate::configuration::PromptTarget;
use crate::consts;
use crate::consts::DEFAULT_COLLECTION_NAME;
use crate::consts::DEFAULT_NER_MODEL;
use crate::consts::DEFAULT_NER_THRESHOLD;
use crate::consts::DEFAULT_PROMPT_TARGET_THRESHOLD;

enum RequestType {
    GetEmbedding,
    SearchPoints,
    Ner,
    ContextResolver,
}

pub struct CallContext {
    request_type: RequestType,
    user_message: String,
    prompt_target: Option<PromptTarget>,
    request_body: common_types::open_ai::ChatCompletions,
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

    fn on_http_response_body(&mut self, _body_size: usize, end_of_stream: bool) -> Action {
        if end_of_stream {
            info!("on_http_response_body");
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
        let deserialized_body: common_types::open_ai::ChatCompletions =
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

        let last_message = match deserialized_body.messages.last() {
            Some(message) => message,
            None => {
                info!("No messages in the request body");
                return Action::Continue;
            }
        };

        let user_message: String = match last_message.content.clone() {
            Some(content) => content,
            None => {
                info!("last_message content is None");
                return Action::Continue;
            }
        };

        let get_embeddings_input = CreateEmbeddingRequest {
            input: Box::new(CreateEmbeddingRequestInput::String(user_message.clone())),
            model: String::from(consts::DEFAULT_EMBEDDING_MODEL),
            encoding_format: None,
            dimensions: None,
            user: None,
        };

        let json_data: String = match to_string(&get_embeddings_input) {
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
            user_message,
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
        let mut callout_context = self.callouts.remove(&token_id).expect("invalid token_id");

        let resp = self.get_http_call_response_body(0, body_size);

        if resp.is_none() {
            warn!("No response body");
            self.resume_http_request();
            return;
        }

        let body = resp.unwrap();
        if body.is_empty() {
            warn!("Empty response body");
            self.resume_http_request();
            return;
        }

        match callout_context.request_type {
            RequestType::GetEmbedding => {
                let embedding_response: CreateEmbeddingResponse =
                    serde_json::from_slice(&body).unwrap();

                let search_points_request = common_types::SearchPointsRequest {
                    vector: embedding_response.data[0].embedding.clone(),
                    limit: 10,
                    with_payload: true,
                };

                let json_data: String = match to_string(&search_points_request) {
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
            RequestType::SearchPoints => {
                let search_points_response: SearchPointsResponse =
                    serde_json::from_slice(&body).unwrap();

                let search_results = &search_points_response.result;

                if search_results.is_empty() {
                    info!("No prompt target matched");
                    self.resume_http_request();
                    return;
                }

                search_results[0].payload.get("prompt-target").unwrap();
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
                let prompt_target: PromptTarget =
                    serde_json::from_slice(prompt_target_str.as_bytes()).unwrap();
                info!("prompt_target name: {:?}", prompt_target.name);

                // only extract entity names
                let entity_names = get_entity_details(&prompt_target)
                    .iter()
                    .map(|entity| entity.name.clone())
                    .collect();
                let user_message = callout_context.user_message.clone();
                let ner_request = common_types::NERRequest {
                    input: user_message,
                    labels: entity_names,
                    model: DEFAULT_NER_MODEL.to_string(),
                };

                let json_data: String = to_string(&ner_request).unwrap();

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
            RequestType::Ner => {
                let ner_response: common_types::NERResponse =
                    serde_json::from_slice(&body).unwrap();
                info!("ner_response: {:?}", ner_response);

                let mut request_params: HashMap<String, String> = HashMap::new();
                for entity in ner_response.data.iter() {
                    if entity.score < DEFAULT_NER_THRESHOLD {
                        warn!(
                            "score of entity was too low entity name: {}, score: {}",
                            entity.label, entity.score
                        );
                        continue;
                    }
                    request_params.insert(entity.label.clone(), entity.text.clone());
                }

                let prompt_target = callout_context.prompt_target.as_ref().unwrap();
                let entity_details = get_entity_details(prompt_target);
                for entity in entity_details {
                    if entity.required.unwrap_or(false)
                        && !request_params.contains_key(&entity.name)
                    {
                        warn!(
                            "required entity missing or score of entity was too low: {}",
                            entity.name
                        );
                        self.resume_http_request();
                        return;
                    }
                }

                let req_param_str = to_string(&request_params).unwrap();

                let endpoint = callout_context
                    .prompt_target
                    .as_ref()
                    .unwrap()
                    .endpoint
                    .as_ref()
                    .unwrap();

                let http_path = match &endpoint.path {
                    Some(path) => path.clone(),
                    None => "/".to_string(),
                };

                let http_method = match &endpoint.method {
                    Some(method) => method.clone(),
                    None => "POST".to_string(),
                };

                let token_id = match self.dispatch_http_call(
                    &endpoint.cluster.clone(),
                    vec![
                        (":method", http_method.as_str()),
                        (":path", http_path.as_str()),
                        (":authority", endpoint.cluster.as_str()),
                        ("content-type", "application/json"),
                        ("x-envoy-max-retries", "3"),
                    ],
                    Some(req_param_str.as_bytes()),
                    vec![],
                    Duration::from_secs(5),
                ) {
                    Ok(token_id) => token_id,
                    Err(e) => {
                        panic!("Error dispatching HTTP call for context-resolver: {:?}", e);
                    }
                };
                callout_context.request_type = RequestType::ContextResolver;
                if self.callouts.insert(token_id, callout_context).is_some() {
                    panic!("duplicate token_id")
                }
            }
            RequestType::ContextResolver => {
                info!("response received for context-resolver");
                let body_string = String::from_utf8(body).unwrap();
                let prompt_target = callout_context.prompt_target.unwrap();

                info!("context-resolver response: {}", body_string);
                let system_prompt = Message {
                    role: "system".to_string(),
                    content: Some(prompt_target.system_prompt.unwrap().clone()),
                };
                let weather_system_response = Message {
                    role: "user".to_string(),
                    content: Some(body_string.clone()),
                };

                let mut request_body = callout_context.request_body;
                request_body.messages.push(system_prompt);
                request_body.messages.push(weather_system_response);
                let json_string = serde_json::to_string(&request_body).unwrap();
                info!("sending request to openai: msg len: {}", json_string.len());
                self.set_http_request_body(0, json_string.len(), &json_string.into_bytes());
                self.resume_http_request();
            }
        }
    }
}

fn get_entity_details(prompt_target: &PromptTarget) -> Vec<EntityDetail> {
    match prompt_target.entities.as_ref() {
        Some(EntityType::Vec(entity_names)) => {
            let mut entity_details: Vec<EntityDetail> = Vec::new();
            for entity_name in entity_names {
                entity_details.push(EntityDetail {
                    name: entity_name.clone(),
                    required: Some(true),
                    description: None,
                });
            }
            entity_details
        }
        Some(EntityType::Struct(entity_details)) => entity_details.clone(),
        None => Vec::new(),
    }
}
