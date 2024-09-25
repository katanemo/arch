use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Overrides {
    pub prompt_target_intent_matching_threshold: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Configuration {
    pub default_prompt_endpoint: String,
    pub load_balancing: LoadBalancing,
    pub timeout_ms: u64,
    pub overrides: Option<Overrides>,
    pub llm_providers: Vec<LlmProvider>,
    pub prompt_guards: Option<PromptGuards>,
    pub system_prompt: Option<String>,
    pub prompt_targets: Vec<PromptTarget>,
    pub ratelimits: Option<Vec<Ratelimit>>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PromptGuards {
    pub input_guards: InputGuards,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct InputGuards {
    pub jailbreak: Option<GuardOptions>,
    pub toxicity: Option<GuardOptions>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GuardOptions {
    pub on_exception_message: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Ratelimit {
    pub provider: String,
    pub selector: Header,
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
    pub key: String,
    pub value: Option<String>,
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
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptTarget {
    #[serde(rename = "type")]
    pub prompt_type: PromptType,
    pub name: String,
    pub description: String,
    pub parameters: Option<Vec<Parameter>>,
    pub endpoint: Option<Endpoint>,
    pub system_prompt: Option<String>,
}

#[cfg(test)]
mod test {
    pub const CONFIGURATION: &str = r#"
default_prompt_endpoint: "127.0.0.1"
load_balancing: "round_robin"
timeout_ms: 5000

llm_providers:
  - name: "open-ai-gpt-4"
    api_key: "$OPEN_AI_API_KEY"
    model: gpt-4

system_prompt: |
  You are a helpful weather forecaster. Please following following guidelines when responding to user queries:
  - Use farenheight for temperature
  - Use miles per hour for wind speed

prompt_guards:
  input_guard:
    - name: jailbreak
      on_exception_message: Looks like you are curious about my abilities…
    - name: toxic
      on_exception_message: Looks like you are curious about my abilities…

prompt_targets:

  - type: function_resolver
    name: weather_forecast
    description: Get the weather forecast for a location
    endpoint:
      cluster: weatherhost
      path: /weather
    parameters:
      - name: location
        required: true
        description: "The location for which the weather is requested"

  - type: function_resolver
    name: weather_forecast_2
    description: Get the weather forecast for a location
    few_shot_examples:
      - what is the weather in New York?
    endpoint:
      cluster: weatherhost
      path: /weather
    parameters:
      - name: city
        description: "The location for which the weather is requested"

ratelimits:
  - provider: open-ai-gpt-4
    selector:
      key: x-katanemo-openai-limit-id
    limit:
      tokens: 100
      unit: minute
  "#;

    #[test]
    fn test_deserialize_configuration() {
        let c: super::Configuration = serde_yaml::from_str(CONFIGURATION).unwrap();
        assert_eq!(c.prompt_guards.unwrap().input_guard.len(), 2);
    }
}
