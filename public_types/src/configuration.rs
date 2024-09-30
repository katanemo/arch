use std::{collections::HashMap, time::Duration};

use duration_string::DurationString;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Overrides {
    pub prompt_target_intent_matching_threshold: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Configuration {
    pub version: String,
    pub listener: Listener,
    pub endpoints: HashMap<String, Endpoint>,
    pub llm_providers: Vec<LlmProvider>,
    pub overrides: Option<Overrides>,
    pub system_prompt: Option<String>,
    pub prompt_guards: Option<PromptGuards>,
    pub prompt_targets: Vec<PromptTarget>,
    pub error_target: Option<EndpointDetails>,
    pub rate_limits: Option<Vec<Ratelimit>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Listener {
    pub address: String,
    pub port: u16,
    pub message_format: MessageFormat,
    pub connect_timeout: Option<DurationString>,
}

impl Default for Listener {
    fn default() -> Self {
        Listener {
            address: "".to_string(),
            port: 0,
            message_format: MessageFormat::default(),
            connect_timeout: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MessageFormat {
    #[serde(rename = "huggingface")]
    Huggingface,
}

impl Default for MessageFormat {
    fn default() -> Self {
        MessageFormat::Huggingface
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PromptGuards {
    pub input_guards: Vec<PromptGuard>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GuardType {
    #[serde(rename = "jailbreak")]
    Jailbreak,
    #[serde(rename = "toxicity")]
    Toxicity,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptGuard {
    pub name: GuardType,
    pub on_exception: GuardOptions,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardOptions {
    pub forward_to_error_target: Option<bool>,
    pub error_handler: Option<String>,
    pub on_exception: Option<OnExceptionDetails>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OnExceptionDetails {
    pub forward_to_error_target: Option<bool>,
    pub error_handler: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RatelimitSelectorType {
    #[serde(rename = "http_header")]
    Header(Header),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Ratelimit {
    pub selector: RatelimitSelectorType,
    pub limit: Limit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Limit {
    pub tokens: u32,
    pub unit: TimeUnit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TimeUnit {
    #[serde(rename = "second")]
    Second,
    #[serde(rename = "minute")]
    Minute,
    #[serde(rename = "hour")]
    Hour,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Header {
    pub name: String,
    pub value: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
//TODO: use enum for model, but if there is a new model, we need to update the code
pub struct EmbeddingProviver {
    pub name: String,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
//TODO: use enum for model, but if there is a new model, we need to update the code
pub struct LlmProvider {
    pub name: String,
    //TODO: handle env var replacement
    pub access_key: Option<String>,
    pub model: String,
    pub default: Option<bool>,
    pub stream: Option<bool>,
    pub rate_limits: Option<Ratelimit>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Endpoint {
    pub endpoint: Option<String>,
    pub connect_timeout: Option<DurationString>,
    pub timeout: Option<DurationString>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Parameter {
    pub name: String,
    #[serde(rename = "type")]
    pub parameter_type: Option<String>,
    pub description: String,
    pub required: Option<bool>,
    #[serde(rename = "enum")]
    pub enum_values: Option<Vec<String>>,
    pub default: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PromptType {
    #[serde(rename = "function_resolver")]
    FunctionResolver,
    #[serde(rename = "default")]
    Default,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EndpointDetails {
  pub name: String,
  pub path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptTarget {
    pub name: String,
    #[serde(rename = "type")]
    pub prompt_type: PromptType,
    pub description: String,
    pub endpoint: Option<EndpointDetails>,
    pub parameters: Option<Vec<Parameter>>,
    pub system_prompt: Option<String>,
    pub auto_llm_dispatch_on_response: Option<bool>,
}

#[cfg(test)]
mod test {
    use std::fs;

    #[test]
    fn test_deserialize_configuration() {
        let ref_config =
            fs::read_to_string("../docs/source/_config/prompt-config-full-reference.yml")
                .expect("reference config file not found");
        let config: super::Configuration = serde_yaml::from_str(&ref_config).unwrap();
        assert_eq!(config.version, "0.1-beta");
        let open_ai_provider = config.llm_providers.iter().find(|p| p.name.to_lowercase() == "openai").unwrap();
        assert_eq!(open_ai_provider.name.to_lowercase(), "openai");
        assert_eq!(open_ai_provider.access_key, Some("$OPENAI_API_KEY".to_string()));
        assert_eq!(open_ai_provider.model, "gpt-4o");
        assert_eq!(open_ai_provider.default, Some(true));
        assert_eq!(open_ai_provider.stream, Some(true));
    }
}
