use open_message_format::models::CreateEmbeddingRequest;
use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::configuration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingRequest {
    pub create_embedding_request: CreateEmbeddingRequest,
    pub prompt_target: configuration::PromptTarget,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MessageType {
    EmbeddingRequest(EmbeddingRequest),
    CreateVectorStorePoints(CreateVectorStorePoints),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalloutData {
    pub message: MessageType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorPoint {
    pub id: String,
    pub payload: HashMap<String, String>,
    pub vector: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateVectorStorePoints {
    pub points: Vec<VectorPoint>,
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
