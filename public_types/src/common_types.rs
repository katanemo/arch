use crate::configuration::PromptTarget;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingRequest {
    pub prompt_target: PromptTarget,
}

#[derive(Debug, Clone, Hash, PartialEq, Eq)]
pub enum EmbeddingType {
    Name,
    Description,
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
pub struct SearchPointResult {
    pub id: String,
    pub version: i32,
    pub score: f64,
    pub payload: HashMap<String, String>,
}

pub mod open_ai {
    use std::collections::HashMap;

    use serde::{Deserialize, Serialize};
    use serde_yaml::Value;

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ChatCompletionsRequest {
        #[serde(default)]
        pub model: String,
        pub messages: Vec<Message>,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub tools: Option<Vec<ChatCompletionTool>>,
        #[serde(default)]
        pub stream: bool,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub stream_options: Option<StreamOptions>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub enum ToolType {
        #[serde(rename = "function")]
        Function
    }
      #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ChatCompletionTool {
        #[serde(rename = "type")]
        pub tool_type: ToolType,
        pub function: FunctionDefinition,
    }

      #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct FunctionDefinition {
        pub name: String,
        pub description: String,
        pub parameters: FunctionParameters,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct FunctionParameters {
        pub properties: HashMap<String, FunctionParameter>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct FunctionParameter {
        #[serde(rename = "type")]
        #[serde(skip_serializing_if = "Option::is_none")]
        pub parameter_type: Option<String>,
        pub description: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub required: Option<bool>,
        #[serde(skip_serializing_if = "Option::is_none")]
        #[serde(rename = "enum")]
        pub enum_values: Option<Vec<String>>,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub default: Option<String>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct StreamOptions {
        pub include_usage: bool,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Message {
        pub role: String,
        pub content: Option<String>,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub model: Option<String>,
        pub tool_calls: Option<Vec<ToolCall>>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Choice {
        pub finish_reason: String,
        pub index: usize,
        pub message: Message,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ToolCall {
        pub id: String,
        #[serde(rename = "type")]
        pub tool_type: ToolType,
        pub function: FunctionCallDetail,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct FunctionCallDetail {
        pub name: String,
        pub arguments: HashMap<String, Value>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ChatCompletionsResponse {
        pub usage: Usage,
        pub choices: Vec<Choice>,
        pub model: String,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Usage {
        pub completion_tokens: usize,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ChatCompletionChunkResponse {
        pub model: String,
        pub choices: Vec<ChunkChoice>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ChunkChoice {
        pub delta: Delta,
        // TODO: could this be an enum?
        pub finish_reason: Option<String>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Delta {
        pub content: Option<String>,
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZeroShotClassificationRequest {
    pub input: String,
    pub labels: Vec<String>,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZeroShotClassificationResponse {
    pub predicted_class: String,
    pub predicted_class_score: f64,
    pub scores: HashMap<String, f64>,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PromptGuardTask {
    #[serde(rename = "jailbreak")]
    Jailbreak,
    #[serde(rename = "toxicity")]
    Toxicity,
    #[serde(rename = "both")]
    Both,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptGuardRequest {
    pub input: String,
    pub task: PromptGuardTask,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptGuardResponse {
    pub toxic_prob: Option<f64>,
    pub jailbreak_prob: Option<f64>,
    pub toxic_verdict: Option<bool>,
    pub jailbreak_verdict: Option<bool>,
}
