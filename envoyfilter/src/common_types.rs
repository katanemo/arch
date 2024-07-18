use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::configuration;

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
  pub id : String,
  pub payload: HashMap<String, String>,
  pub vector: Vec<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateVectorStorePoints {
  pub points : Vec<VectorPoint>,
}
