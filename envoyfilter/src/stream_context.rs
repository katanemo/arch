use log::info;
use open_message_format::models::{
    CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse,
};
use serde_json::to_string;
use std::collections::HashMap;
use std::time::Duration;

use proxy_wasm::traits::*;
use proxy_wasm::types::*;

use crate::common_types;

use crate::consts;

pub struct StreamContext {
    pub host_header: Option<String>,
    pub callouts: HashMap<u32, HashMap<String, String>>,
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
                Some(body_bytes) => {
                    let body_string = String::from_utf8(body_bytes).unwrap();
                    info!("body_string: {}", body_string);
                    serde_json::from_str(&body_string).unwrap()
                }
                None => panic!(
                    "Failed to obtain body bytes even though body_size is {}",
                    body_size
                ),
            };

        // 1. find latest message with user role
        // 2. compute its embeddings
        // 3. use cosine similarity to find the most similar prompt target
        // 4. use the prompt target to generate a response

        let user_message = deserialized_body
            .messages
            .last()
            .unwrap()
            .content
            .clone()
            .unwrap();
        info!("user input: {}", user_message);

        let get_embeddings_input = CreateEmbeddingRequest {
            input: Box::new(CreateEmbeddingRequestInput::String(user_message)),
            model: String::from(consts::DEFAULT_EMBEDDING_MODEL),
            encoding_format: None,
            dimensions: None,
            user: None,
        };

        // TODO: Handle potential errors
        let json_data: String = to_string(&get_embeddings_input).unwrap();

        let token_id = match self.dispatch_http_call(
            "embeddingserver",
            vec![
                (":method", "POST"),
                (":path", "/embeddings"),
                (":authority", "embeddingserver"),
                ("content-type", "application/json"),
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
        // let embedding_request = EmbeddingRequest {
        //     create_embedding_request: embeddings_input,
        //     prompt_target: user_message,
        // };
        let mut payload: HashMap<String, String> = HashMap::new();
        payload.insert("request-type".to_string(), "get-embedding".to_string());
        if self.callouts.insert(token_id, payload).is_some() {
            panic!("duplicate token_id")
        }

        // Modify JSON payload
        // deserialized_body.model = String::from("gpt-3.5-turbo");
        // let json_string = serde_json::to_string(&deserialized_body).unwrap();

        // self.set_http_request_body(0, body_size, &json_string.into_bytes());

        Action::Pause
    }

    fn on_http_response_body(&mut self, _body_size: usize, _end_of_stream: bool) -> Action {
        Action::Continue
    }
}

impl Context for StreamContext {
    fn on_http_call_response(
        &mut self,
        token_id: u32,
        _num_headers: usize,
        _body_size: usize,
        _num_trailers: usize,
    ) {
        info!("on_http_call_response: token_id = {}", token_id);

        let callout_data: HashMap<String, String> =
            self.callouts.remove(&token_id).expect("invalid token_id");

        match callout_data.get("request-type").unwrap().as_str() {
            "get-embedding" => {
                info!("response received for get-embedding");
                if let Some(body) = self.get_http_call_response_body(0, _body_size) {
                    if !body.is_empty() {
                        let embedding_response: CreateEmbeddingResponse =
                            serde_json::from_slice(&body).unwrap();
                        info!(
                            "embedding_response model: {}, vector len: {}",
                            embedding_response.model,
                            embedding_response.data[0].embedding.len()
                        );
                        // create request to perform similarity search in qdrant
                        // let create_vector_store_points = CreateVectorStorePoints {
                    }
                }

                self.resume_http_request();
            }
            _ => {
                info!("response received for unknown request type");
            }
        }
    }
}
