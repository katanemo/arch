use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Configuration {
    #[serde(rename = "katanemo-prompt-config")]
    prompt_config: PromptConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptConfig {
    #[serde(rename = "default-prompt-endpoint")]
    default_prompt_endpoint: String,

    #[serde(rename = "load-balancing")]
    load_balancing: String,

    #[serde(rename = "timeout-ms")]
    timeout_ms: u64,

    #[serde(rename = "embedding-provider")]
    embedding_provider: EmbeddingProviver,

    #[serde(rename = "llm-providers")]
    llm_providers: Vec<LlmProvider>,

    #[serde(rename = "system-prompt")]
    system_prompt: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct EmbeddingProviver {
    provider: String,
    #[serde(rename = "model-name")]
    model_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct LlmProvider {
    provider: String,
    #[serde(rename = "api-key")]
    api_key: String,
    //TODO: change it to model-name
    #[serde(rename = "model-version")]
    model_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PromptTarget {
    #[serde(rename = "type")]
    prompt_type: String,

    name: String,

    #[serde(rename = "few-shot-examples")]
    few_shot_examples: Vec<String>,

    endpoint: String,
}

#[cfg(test)]
mod test {
    pub const CONFIGURATION: &str = r#"
    katanemo-prompt-config:
      default-prompt-endpoint: "127.0.0.1"
      load-balancing: "prompt-robin"
      timeout-ms: 5000

      embedding-provider:
        provider: "SentenceTransformer"
        model-name: "all-MiniLM-L6-v2"

      llm-providers:

        - provider: "open-ai-gpt-4"
          api-key: "$OPEN_AI_API_KEY"
          model-version: gpt-4

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
