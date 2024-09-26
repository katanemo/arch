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
        Function,
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
        #[serde(default = "ParameterType::string")]
        pub parameter_type: ParameterType,
        pub description: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub required: Option<bool>,
        #[serde(skip_serializing_if = "Option::is_none")]
        #[serde(rename = "enum")]
        pub enum_values: Option<Vec<String>>,
        #[serde(skip_serializing_if = "Option::is_none")]
        pub default: Option<String>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
    pub enum ParameterType {
        #[serde(rename = "int")]
        Int,
        #[serde(rename = "float")]
        Float,
        #[serde(rename = "bool")]
        Bool,
        #[serde(rename = "string")]
        String,
        #[serde(rename = "list")]
        List,
        #[serde(rename = "dict")]
        Dict,
    }

    impl From<String> for ParameterType {
        fn from(s: String) -> Self {
            match s.as_str() {
                "int" => ParameterType::Int,
                "float" => ParameterType::Float,
                "bool" => ParameterType::Bool,
                "string" => ParameterType::String,
                "list" => ParameterType::List,
                "dict" => ParameterType::Dict,
                _ => ParameterType::String,
            }
        }
    }

    impl ParameterType {
        pub fn string() -> ParameterType {
            ParameterType::String
        }
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

#[cfg(test)]
mod test {
    use crate::common_types::open_ai::Message;
    use pretty_assertions::{assert_eq, assert_ne};
    use std::collections::HashMap;

    const TOOL_SERIALIZED: &str = r#"{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "user",
      "content": "What city do you want to know the weather for?",
      "tool_calls": null
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "weather_forecast",
        "description": "function to retrieve weather forecast",
        "parameters": {
          "properties": {
            "city": {
              "type": "string",
              "description": "city for weather forecast",
              "required": true,
              "default": "test"
            }
          }
        }
      }
    }
  ],
  "stream": true,
  "stream_options": {
    "include_usage": true
  }
}"#;

    #[test]
    fn test_tool_type_request() {
        use super::open_ai::{
            ChatCompletionsRequest, FunctionDefinition, FunctionParameter, ParameterType, ToolType,
        };

        let mut properties = HashMap::new();
        properties.insert(
            "city".to_string(),
            FunctionParameter {
                parameter_type: ParameterType::String,
                description: "city for weather forecast".to_string(),
                required: Some(true),
                enum_values: None,
                default: Some("test".to_string()),
            },
        );

        let function_definition = FunctionDefinition {
            name: "weather_forecast".to_string(),
            description: "function to retrieve weather forecast".to_string(),
            parameters: super::open_ai::FunctionParameters { properties },
        };

        let chat_completions_request = ChatCompletionsRequest {
            model: "gpt-3.5-turbo".to_string(),
            messages: vec![Message {
                role: "user".to_string(),
                content: Some("What city do you want to know the weather for?".to_string()),
                model: None,
                tool_calls: None,
            }],
            tools: Some(vec![super::open_ai::ChatCompletionTool {
                tool_type: ToolType::Function,
                function: function_definition,
            }]),
            stream: true,
            stream_options: Some(super::open_ai::StreamOptions {
                include_usage: true,
            }),
        };

        let serialized = serde_json::to_string_pretty(&chat_completions_request).unwrap();
        println!("{}", serialized);
        assert_eq!(TOOL_SERIALIZED, serialized);
    }

    #[test]
    fn test_parameter_types() {
        use super::open_ai::{
            ChatCompletionsRequest, FunctionDefinition, FunctionParameter, ParameterType, ToolType,
        };

        const PARAMETER_SERIALZIED: &str = r#"{
  "city": {
    "type": "string",
    "description": "city for weather forecast",
    "required": true,
    "default": "test"
  }
}"#;

        let properties = HashMap::from([(
            "city".to_string(),
            FunctionParameter {
                parameter_type: ParameterType::String,
                description: "city for weather forecast".to_string(),
                required: Some(true),
                enum_values: None,
                default: Some("test".to_string()),
            },
        )]);

        let serialized = serde_json::to_string_pretty(&properties).unwrap();
        assert_eq!(PARAMETER_SERIALZIED, serialized);

        // ensure that if type is missing it is set to string
        const PARAMETER_SERIALZIED_MISSING_TYPE: &str = r#"
{
  "city": {
    "description": "city for weather forecast",
    "required": true
  }
}"#;

        let missing_type_deserialized: HashMap<String, FunctionParameter> =
            serde_json::from_str(PARAMETER_SERIALZIED_MISSING_TYPE).unwrap();
        println!("{:?}", missing_type_deserialized);
        assert_eq!(
            missing_type_deserialized
                .get("city")
                .unwrap()
                .parameter_type,
            ParameterType::String
        );
    }
}
