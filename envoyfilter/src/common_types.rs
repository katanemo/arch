use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateEmbeddingRequest {
    pub input: String,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateEmbeddingResponse {
    pub object: String,
    pub model: String,
    pub data: Vec<Embedding>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Embedding {
    pub object: String,
    pub index: i32,
    pub embedding: Vec<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MessageType {
    EmbeddingRequest(CreateEmbeddingRequest),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalloutData {
    pub message: MessageType,
}
