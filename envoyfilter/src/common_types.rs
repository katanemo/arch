use open_message_format::models::CreateEmbeddingRequest;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::configuration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingRequest {
    pub create_embedding_request: CreateEmbeddingRequest,
    pub prompt_target: configuration::PromptTarget,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorPoint {
    pub id: String,
    pub payload: HashMap<String, String>,
    pub vector: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoreVectorEmbeddingsRequest {
    pub points: Vec<VectorPoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CallContext {
    EmbeddingRequest(EmbeddingRequest),
    StoreVectorEmbeddings(StoreVectorEmbeddingsRequest),
}

pub mod open_ai {
    use serde::{Deserialize, Serialize};

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ChatCompletions {
        #[serde(default)]
        pub model: String,
        pub messages: Vec<Message>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Message {
        pub role: String,
        pub content: String,
    }
}
