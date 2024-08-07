use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Configuration {
    pub default_prompt_endpoint: String,
    pub load_balancing: LoadBalancing,
    pub timeout_ms: u64,
    pub embedding_provider: EmbeddingProviver,
    pub llm_providers: Vec<LlmProvider>,
    pub system_prompt: Option<String>,
    pub prompt_targets: Vec<PromptTarget>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LoadBalancing {
    #[serde(rename = "round_robin")]
    RoundRobin,
    #[serde(rename = "random")]
    Random,
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
    pub api_key: Option<String>,
    pub model: String,
    pub default: Option<bool>,
    pub endpoint: Option<EnpointType>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum EnpointType {
    String(String),
    Struct(Endpoint),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Endpoint {
    pub cluster: String,
    pub path: Option<String>,
    pub method: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub name: String,
    pub required: Option<bool>,
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptTarget {
    #[serde(rename = "type")]
    pub prompt_type: String,
    pub name: String,
    pub few_shot_examples: Vec<String>,
    pub entities: Option<Vec<Entity>>,
    pub endpoint: Option<Endpoint>,
    pub system_prompt: Option<String>,
}

#[cfg(test)]
mod test {
    pub const CONFIGURATION: &str = r#"
default_prompt_endpoint: "127.0.0.1"
load_balancing: "round_robin"
timeout_ms: 5000

embedding_provider:
  name: "SentenceTransformer"
  model: "all-MiniLM-L6-v2"

llm_providers:

  - name: "open-ai-gpt-4"
    api_key: "$OPEN_AI_API_KEY"
    model: gpt-4

system_prompt: |
  You are a helpful weather forecaster. Please following following guidelines when responding to user queries:
  - Use farenheight for temperature
  - Use miles per hour for wind speed

prompt_targets:

  - type: context_resolver
    name: weather_forecast
    few_shot_examples:
      - what is the weather in New York?
    endpoint:
      cluster: weatherhost
      path: /weather
    entities:
      - name: location
        required: true
        description: "The location for which the weather is requested"

  - type: context_resolver
    name: weather_forecast_2
    few_shot_examples:
      - what is the weather in New York?
    endpoint:
      cluster: weatherhost
      path: /weather
    entities:
      - name: city
  "#;

    #[test]
    fn test_deserialize_configuration() {
        let _: super::Configuration = serde_yaml::from_str(CONFIGURATION).unwrap();
    }
}
