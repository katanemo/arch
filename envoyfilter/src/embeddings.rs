use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Embeddings {
    pub input: String,
    pub model: String,
}
