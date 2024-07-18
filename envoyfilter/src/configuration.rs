use serde::{Deserialize, Serialize};

//TODO: possibly use protbuf to enforce schema

//FIX: it is unnecessary to place yaml config inside katanemo-prompt-config
//GH Issue: https://github.com/katanemo/intelligent-prompt-gateway/issues/7

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct Configuration {
    #[serde(rename = "katanemo-prompt-config")]
    pub prompt_config: PromptConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]

pub enum LoadBalancing {
    #[serde(rename = "round-robin")]
    RoundRobin,
    #[serde(rename = "random")]
    Random,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct PromptConfig {
    pub default_prompt_endpoint: String,
    pub load_balancing: LoadBalancing,
    pub timeout_ms: u64,
    pub embedding_provider: EmbeddingProviver,
    pub llm_providers: Vec<LlmProvider>,
    pub system_prompt: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
//TODO: use enum for model, but if there is a new model, we need to update the code
pub struct EmbeddingProviver {
    pub name: String,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
//TODO: use enum for model, but if there is a new model, we need to update the code
pub struct LlmProvider {
    pub name: String,
    pub api_key: String,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct PromptTarget {
    #[serde(rename = "type")]
    pub prompt_type: String,
    pub name: String,
    pub few_shot_examples: Vec<String>,
    pub endpoint: String,
}

#[cfg(test)]
mod test {
    pub const CONFIGURATION: &str = r#"
katanemo-prompt-config:
  default-prompt-endpoint: "127.0.0.1"
  load-balancing: "round-robin"
  timeout-ms: 5000

  embedding-provider:
    name: "SentenceTransformer"
    model: "all-MiniLM-L6-v2"

  llm-providers:

    - name: "open-ai-gpt-4"
      api-key: "$OPEN_AI_API_KEY"
      model: gpt-4

  system-prompt: |
    You are a helpful weather forecaster. Please following following guidelines when responding to user queries:
    - Use farenheight for temperature
    - Use miles per hour for wind speed

  prompt-targets:

    - type: context-resolver
      name: weather-forecast
      few-shot-examples:
        - what is the weather in New York?
      endpoint: "POST:$WEATHER_FORECAST_API_ENDPOINT"
      cache-response: true
      cache-response-settings:
        - cache-ttl-secs: 3600 # cache expiry in seconds
        - cache-max-size: 1000 # in number of items
        - cache-eviction-strategy: LRU

  "#;

    #[test]
    fn test_deserialize_configuration() {
        let _: super::Configuration = serde_yaml::from_str(CONFIGURATION).unwrap();
    }
}
