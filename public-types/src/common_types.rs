use crate::configuration::PromptTarget;
use open_message_format_embeddings::models::CreateEmbeddingRequest;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingRequest {
    pub create_embedding_request: CreateEmbeddingRequest,
    pub prompt_target: PromptTarget,
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
pub struct ToolParameter {
    #[serde(rename = "type")]
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parameter_type: Option<String>,
    pub description: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub required: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolParameters {
    #[serde(rename = "type")]
    pub parameters_type: String,
    pub properties: HashMap<String, ToolParameter>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolsDefinition {
    pub name: String,
    pub description: String,
    pub parameters: ToolParameters,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoltFCResponse {
    pub model: String,
    pub message: open_ai::Message,
    pub done_reason: String,
    pub done: bool,
    pub resolver_name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum IntOrString {
    Integer(i32),
    Text(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallDetail {
    pub name: String,
    pub arguments: HashMap<String, IntOrString>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoltFCToolsCall {
    pub tool_calls: Vec<ToolCallDetail>,
}

pub mod open_ai {
    use serde::{Deserialize, Serialize};

    use super::ToolsDefinition;

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ChatCompletions {
        #[serde(default)]
        pub model: String,
        pub messages: Vec<Message>,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub tools: Option<Vec<ToolsDefinition>>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Message {
        pub role: String,
        pub content: Option<String>,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub model: Option<String>,
    }
}
