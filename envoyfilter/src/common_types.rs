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
#[allow(clippy::large_enum_variant)]
pub enum CallContext {
    EmbeddingRequest(EmbeddingRequest),
    StoreVectorEmbeddings(StoreVectorEmbeddingsRequest),
    CreateVectorCollection(String),
}

// https://api.qdrant.tech/master/api-reference/search/points
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchPointsRequest {
    pub vector: Vec<f64>,
    pub limit: i32,
    pub with_payload: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchPointResult {
    pub id: String,
    pub version: i32,
    pub score: f64,
    pub payload: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchPointsResponse {
    pub result: Vec<SearchPointResult>,
    pub status: String,
    pub time: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NERRequest {
    pub input: String,
    pub labels: Vec<String>,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub text: String,
    pub label: String,
    pub score: f64,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NERResponse {
    pub data: Vec<Entity>,
    pub model: String,
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
        pub content: Option<String>,
    }
}
