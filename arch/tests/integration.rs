use http::StatusCode;
use proxy_wasm_test_framework::tester::{self, Tester};
use proxy_wasm_test_framework::types::{
    Action, BufferType, LogLevel, MapType, MetricType, ReturnType,
};
use public_types::common_types::open_ai::{ChatCompletionsResponse, Choice, Message, Usage};
use public_types::common_types::open_ai::{FunctionCallDetail, ToolCall, ToolType};
use public_types::embeddings::embedding::Object;
use public_types::embeddings::{
    create_embedding_response, CreateEmbeddingResponse, CreateEmbeddingResponseUsage, Embedding,
};
use public_types::{common_types::ZeroShotClassificationResponse, configuration::Configuration};
use serde_yaml::Value;
use serial_test::serial;
use std::collections::HashMap;
use std::path::Path;

fn wasm_module() -> String {
    let wasm_file = Path::new("target/wasm32-wasi/release/intelligent_prompt_gateway.wasm");
    assert!(
        wasm_file.exists(),
        "Run `cargo build --release --target=wasm32-wasi` first"
    );
    wasm_file.to_str().unwrap().to_string()
}

fn request_headers_expectations(module: &mut Tester, http_context: i32) {
    module
        .call_proxy_on_request_headers(http_context, 0, false)
        .expect_get_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("x-arch-llm-provider-hint"),
        )
        .returning(Some("default"))
        .expect_add_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("x-arch-llm-provider"),
            Some("open-ai-gpt-4"),
        )
        .expect_replace_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("Authorization"),
            Some("Bearer secret_key"),
        )
        .expect_remove_header_map_value(Some(MapType::HttpRequestHeaders), Some("content-length"))
        .expect_get_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("x-arch-ratelimit-selector"),
        )
        .returning(Some("selector-key"))
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some("selector-key"))
        .returning(Some("selector-value"))
        .expect_get_header_map_pairs(Some(MapType::HttpRequestHeaders))
        .returning(None)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();
}

fn normal_flow(module: &mut Tester, filter_context: i32, http_context: i32) {
    module
        .call_proxy_on_context_create(http_context, filter_context)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    request_headers_expectations(module, http_context);

    // Request Body
    let chat_completions_request_body = "\
{\
    \"messages\": [\
    {\
        \"role\": \"system\",\
        \"content\": \"You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.\"\
    },\
    {\
        \"role\": \"user\",\
        \"content\": \"Compose a poem that explains the concept of recursion in programming.\"\
    }\
    ],\
    \"model\": \"gpt-4\"\
}";

    module
        .call_proxy_on_request_body(
            http_context,
            chat_completions_request_body.len() as i32,
            true,
        )
        .expect_get_buffer_bytes(Some(BufferType::HttpRequestBody))
        .returning(Some(chat_completions_request_body))
        // The actual call is not important in this test, we just need to grab the token_id
        .expect_http_call(Some("model_server"), None, None, None, None)
        .returning(Some(1))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_metric_increment("active_http_calls", 1)
        .expect_log(Some(LogLevel::Info), None)
        .execute_and_expect(ReturnType::Action(Action::Pause))
        .unwrap();

    let embedding_response = CreateEmbeddingResponse {
        data: vec![Embedding {
            index: 0,
            embedding: vec![],
            object: Object::default(),
        }],
        model: String::from("test"),
        object: create_embedding_response::Object::default(),
        usage: Box::new(CreateEmbeddingResponseUsage::new(0, 0)),
    };
    let embeddings_response_buffer = serde_json::to_string(&embedding_response).unwrap();
    module
        .call_proxy_on_http_call_response(
            http_context,
            1,
            0,
            embeddings_response_buffer.len() as i32,
            0,
        )
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&embeddings_response_buffer))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_http_call(Some("model_server"), None, None, None, None)
        .returning(Some(2))
        .expect_metric_increment("active_http_calls", 1)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    let zero_shot_response = ZeroShotClassificationResponse {
        predicted_class: "weather_forecast".to_string(),
        predicted_class_score: 0.1,
        scores: HashMap::new(),
        model: "test-model".to_string(),
    };
    let zeroshot_intent_detection_buffer = serde_json::to_string(&zero_shot_response).unwrap();
    module
        .call_proxy_on_http_call_response(
            http_context,
            2,
            0,
            zeroshot_intent_detection_buffer.len() as i32,
            0,
        )
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&zeroshot_intent_detection_buffer))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Info), None)
        .expect_http_call(Some("arch_fc"), None, None, None, None)
        .returning(Some(3))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_metric_increment("active_http_calls", 1)
        .execute_and_expect(ReturnType::None)
        .unwrap();
}

fn default_config() -> Configuration {
    let config: &str = r#"
version: "0.1-beta"

listener:
  address: 0.0.0.0
  port: 10000
  message_format: huggingface
  connect_timeout: 0.005s

endpoints:
  api_server:
    endpoint: api_server:80
    connect_timeout: 0.005s

llm_providers:
  - name: open-ai-gpt-4
    provider: openai
    access_key: secret_key
    model: gpt-4
    default: true

overrides:
  # confidence threshold for prompt target intent matching
  prompt_target_intent_matching_threshold: 0.6

system_prompt: |
  You are a helpful assistant.

prompt_targets:

  - name: weather_forecast
    description: This function provides realtime weather forecast information for a given city.
    parameters:
      - name: city
        required: true
        description: The city for which the weather forecast is requested.
      - name: days
        description: The number of days for which the weather forecast is requested.
      - name: units
        description: The units in which the weather forecast is requested.
    endpoint:
      name: api_server
      path: /weather
    system_prompt: |
      You are a helpful weather forecaster. Use weater data that is provided to you. Please following following guidelines when responding to user queries:
      - Use farenheight for temperature
      - Use miles per hour for wind speed

  - name: insurance_claim_details
    type: function_resolver
    description: This function resolver provides insurance claim details for a given policy number.
    parameters:
      - name: policy_number
        required: true
        description: The policy number for which the insurance claim details are requested.
        type: string
      - name: include_expired
        description: whether to include expired insurance claims in the response.
        type: bool
        required: true
    endpoint:
      name: api_server
      path: /insurance_claim_details
    system_prompt: |
      You are a helpful insurance claim details provider. Use insurance claim data that is provided to you. Please following following guidelines when responding to user queries:
      - Use policy number to retrieve insurance claim details
ratelimits:
  - model: gpt-4
    selector:
      key: selector-key
      value: selector-value
    limit:
      tokens: 1
      unit: minute
"#;
    serde_yaml::from_str(config).unwrap()
}

#[test]
#[serial]
fn successful_request_to_open_ai_chat_completions() {
    let args = tester::MockSettings {
        wasm_path: wasm_module(),
        quiet: false,
        allow_unexpected: false,
    };
    let mut module = tester::mock(args).unwrap();

    module
        .call_start()
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Setup Filter
    let filter_context = 1;
    let config = serde_json::to_string(&default_config()).unwrap();

    module
        .call_proxy_on_context_create(filter_context, 0)
        .expect_metric_creation(MetricType::Gauge, "active_http_calls")
        .expect_metric_creation(MetricType::Counter, "ratelimited_rq")
        .execute_and_expect(ReturnType::None)
        .unwrap();

    module
        .call_proxy_on_configure(filter_context, config.len() as i32)
        .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
        .returning(Some(&config))
        .execute_and_expect(ReturnType::Bool(true))
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    module
        .call_proxy_on_context_create(http_context, filter_context)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    request_headers_expectations(&mut module, http_context);

    // Request Body
    let chat_completions_request_body = "\
    {\
        \"messages\": [\
        {\
            \"role\": \"system\",\
            \"content\": \"You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.\"\
        },\
        {\
            \"role\": \"user\",\
            \"content\": \"Compose a poem that explains the concept of recursion in programming.\"\
        }\
        ],\
        \"model\": \"gpt-4\"\
    }";

    module
        .call_proxy_on_request_body(
            http_context,
            chat_completions_request_body.len() as i32,
            true,
        )
        .expect_get_buffer_bytes(Some(BufferType::HttpRequestBody))
        .returning(Some(chat_completions_request_body))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Info), None)
        .expect_http_call(Some("model_server"), None, None, None, None)
        .returning(Some(4))
        .expect_metric_increment("active_http_calls", 1)
        .execute_and_expect(ReturnType::Action(Action::Pause))
        .unwrap();
}

#[test]
#[serial]
fn bad_request_to_open_ai_chat_completions() {
    let args = tester::MockSettings {
        wasm_path: wasm_module(),
        quiet: false,
        allow_unexpected: false,
    };
    let mut module = tester::mock(args).unwrap();

    module
        .call_start()
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Setup Filter
    let filter_context = 1;
    let config = serde_json::to_string(&default_config()).unwrap();

    module
        .call_proxy_on_context_create(filter_context, 0)
        .expect_metric_creation(MetricType::Gauge, "active_http_calls")
        .expect_metric_creation(MetricType::Counter, "ratelimited_rq")
        .execute_and_expect(ReturnType::None)
        .unwrap();

    module
        .call_proxy_on_configure(filter_context, config.len() as i32)
        .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
        .returning(Some(&config))
        .execute_and_expect(ReturnType::Bool(true))
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    module
        .call_proxy_on_context_create(http_context, filter_context)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    request_headers_expectations(&mut module, http_context);

    // Request Body
    let incomplete_chat_completions_request_body = "\
    {\
        \"messages\": [\
        {\
            \"role\": \"system\",\
        },\
        {\
            \"role\": \"user\",\
            \"content\": \"Compose a poem that explains the concept of recursion in programming.\"\
        }\
        ]\
    }";

    module
        .call_proxy_on_request_body(
            http_context,
            incomplete_chat_completions_request_body.len() as i32,
            true,
        )
        .expect_get_buffer_bytes(Some(BufferType::HttpRequestBody))
        .returning(Some(incomplete_chat_completions_request_body))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_send_local_response(
            Some(StatusCode::BAD_REQUEST.as_u16().into()),
            None,
            None,
            None,
        )
        .execute_and_expect(ReturnType::Action(Action::Pause))
        .unwrap();
}

#[test]
#[serial]
fn request_ratelimited() {
    let args = tester::MockSettings {
        wasm_path: wasm_module(),
        quiet: false,
        allow_unexpected: false,
    };
    let mut module = tester::mock(args).unwrap();

    module
        .call_start()
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Setup Filter
    let filter_context = 1;
    let config = serde_json::to_string(&default_config()).unwrap();

    module
        .call_proxy_on_context_create(filter_context, 0)
        .expect_metric_creation(MetricType::Gauge, "active_http_calls")
        .expect_metric_creation(MetricType::Counter, "ratelimited_rq")
        .execute_and_expect(ReturnType::None)
        .unwrap();
    module
        .call_proxy_on_configure(filter_context, config.len() as i32)
        .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
        .returning(Some(&config))
        .execute_and_expect(ReturnType::Bool(true))
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    normal_flow(&mut module, filter_context, http_context);

    let arch_fc_resp = ChatCompletionsResponse {
        usage: Usage {
            completion_tokens: 0,
        },
        choices: vec![Choice {
            finish_reason: "test".to_string(),
            index: 0,
            message: Message {
                role: "system".to_string(),
                content: None,
                tool_calls: Some(vec![ToolCall {
                    id: String::from("test"),
                    tool_type: ToolType::Function,
                    function: FunctionCallDetail {
                        name: String::from("weather_forecast"),
                        arguments: HashMap::from([(
                            String::from("city"),
                            Value::String(String::from("seattle")),
                        )]),
                    },
                }]),
                model: None,
            },
        }],
        model: String::from("test"),
    };

    let arch_fc_resp_str = serde_json::to_string(&arch_fc_resp).unwrap();
    module
        .call_proxy_on_http_call_response(http_context, 3, 0, arch_fc_resp_str.len() as i32, 0)
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&arch_fc_resp_str))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_http_call(Some("api_server"), None, None, None, None)
        .returning(Some(4))
        .expect_metric_increment("active_http_calls", 1)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    let body_text = String::from("test body");
    module
        .call_proxy_on_http_call_response(http_context, 4, 0, body_text.len() as i32, 0)
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&body_text))
        .expect_log(Some(LogLevel::Warn), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_send_local_response(
            Some(StatusCode::TOO_MANY_REQUESTS.as_u16().into()),
            None,
            None,
            None,
        )
        .expect_metric_increment("ratelimited_rq", 1)
        .expect_log(
            Some(LogLevel::Debug),
            Some("server error occurred: Exceeded Ratelimit: Not allowed"),
        )
        .execute_and_expect(ReturnType::None)
        .unwrap();
}

#[test]
#[serial]
fn request_not_ratelimited() {
    let args = tester::MockSettings {
        wasm_path: wasm_module(),
        quiet: false,
        allow_unexpected: false,
    };
    let mut module = tester::mock(args).unwrap();

    module
        .call_start()
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Setup Filter
    let filter_context = 1;

    let mut config = default_config();
    config.ratelimits.as_mut().unwrap()[0].limit.tokens += 1000;
    let config_str = serde_json::to_string(&config).unwrap();

    module
        .call_proxy_on_context_create(filter_context, 0)
        .expect_metric_creation(MetricType::Gauge, "active_http_calls")
        .expect_metric_creation(MetricType::Counter, "ratelimited_rq")
        .execute_and_expect(ReturnType::None)
        .unwrap();
    module
        .call_proxy_on_configure(filter_context, config_str.len() as i32)
        .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
        .returning(Some(&config_str))
        .execute_and_expect(ReturnType::Bool(true))
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    normal_flow(&mut module, filter_context, http_context);

    let arch_fc_resp = ChatCompletionsResponse {
        usage: Usage {
            completion_tokens: 0,
        },
        choices: vec![Choice {
            finish_reason: "test".to_string(),
            index: 0,
            message: Message {
                role: "system".to_string(),
                content: None,
                tool_calls: Some(vec![ToolCall {
                    id: String::from("test"),
                    tool_type: ToolType::Function,
                    function: FunctionCallDetail {
                        name: String::from("weather_forecast"),
                        arguments: HashMap::from([(
                            String::from("city"),
                            Value::String(String::from("seattle")),
                        )]),
                    },
                }]),
                model: None,
            },
        }],
        model: String::from("test"),
    };

    let arch_fc_resp_str = serde_json::to_string(&arch_fc_resp).unwrap();
    module
        .call_proxy_on_http_call_response(http_context, 3, 0, arch_fc_resp_str.len() as i32, 0)
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&arch_fc_resp_str))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_http_call(Some("api_server"), None, None, None, None)
        .returning(Some(4))
        .expect_metric_increment("active_http_calls", 1)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    let body_text = String::from("test body");
    module
        .call_proxy_on_http_call_response(http_context, 4, 0, body_text.len() as i32, 0)
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&body_text))
        .expect_log(Some(LogLevel::Warn), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_set_buffer_bytes(Some(BufferType::HttpRequestBody), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();
}
