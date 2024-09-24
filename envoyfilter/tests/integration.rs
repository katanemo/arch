use http::StatusCode;
use proxy_wasm_test_framework::tester::{self, Tester};
use proxy_wasm_test_framework::types::{
    Action, BufferType, LogLevel, MapType, MetricType, ReturnType,
};
use public_types::common_types::{
    open_ai::{ChatCompletionsResponse, Choice, Message, Usage},
    BoltFCToolsCall, IntOrString, ToolCallDetail,
};
use public_types::embeddings::embedding::Object;
use public_types::embeddings::{
    create_embedding_response, CreateEmbeddingResponse, CreateEmbeddingResponseUsage, Embedding,
};
use public_types::{common_types::ZeroShotClassificationResponse, configuration::Configuration};
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

fn normal_flow(module: &mut Tester, filter_context: i32, http_context: i32) {
    module
        .call_proxy_on_context_create(http_context, filter_context)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Request Headers
    module
        .call_proxy_on_request_headers(http_context, 0, false)
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":host"))
        .returning(Some("api.openai.com"))
        .expect_remove_header_map_value(Some(MapType::HttpRequestHeaders), Some("content-length"))
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":path"))
        .returning(Some("/llmrouting"))
        .expect_replace_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some(":path"),
            Some("/v1/chat/completions"),
        )
        .expect_get_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("x-katanemo-ratelimit-selector"),
        )
        .returning(Some("selector-key"))
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some("selector-key"))
        .returning(Some("selector-value"))
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();

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
        .expect_metric_increment("active_http_calls", 1)
        .expect_log(Some(LogLevel::Debug), None)
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
        .expect_http_call(Some("bolt_fc_1b"), None, None, None, None)
        .returning(Some(3))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_metric_increment("active_http_calls", 1)
        .execute_and_expect(ReturnType::None)
        .unwrap();
}

fn default_config() -> Configuration {
    let config: &str = r#"
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

prompt_targets:
  - type: function_resolver
    name: weather_forecast
    description: This resolver provides weather forecast information.
    endpoint:
      cluster: weatherhost
      path: /weather
    parameters:
      - name: city
        required: true
        description: The city for which the weather forecast is requested.
      - name: days
        description: The number of days for which the weather forecast is requested.
      - name: units
        description: The units in which the weather forecast is requested.

  - type: function_resolver
    name: weather_forecast_2
    description: This resolver provides weather forecast information.
    endpoint:
      cluster: weatherhost
      path: /weather
    entities:
      - name: city

ratelimits:
  - provider: gpt-3.5-turbo
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
    let root_context = 1;

    module
        .call_proxy_on_context_create(root_context, 0)
        .expect_metric_creation(MetricType::Gauge, "active_http_calls")
        .expect_metric_creation(MetricType::Counter, "ratelimited_rq")
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    module
        .call_proxy_on_context_create(http_context, root_context)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Request Headers
    module
        .call_proxy_on_request_headers(http_context, 0, false)
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":host"))
        .returning(Some("api.openai.com"))
        .expect_remove_header_map_value(Some(MapType::HttpRequestHeaders), Some("content-length"))
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":path"))
        .returning(Some("/llmrouting"))
        .expect_replace_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some(":path"),
            Some("/v1/chat/completions"),
        )
        .expect_get_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("x-katanemo-ratelimit-selector"),
        )
        .returning(None)
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();

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
    let root_context = 1;

    module
        .call_proxy_on_context_create(root_context, 0)
        .expect_metric_creation(MetricType::Gauge, "active_http_calls")
        .expect_metric_creation(MetricType::Counter, "ratelimited_rq")
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    module
        .call_proxy_on_context_create(http_context, root_context)
        .expect_log(Some(LogLevel::Debug), None)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Request Headers
    module
        .call_proxy_on_request_headers(http_context, 0, false)
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":host"))
        .returning(Some("api.openai.com"))
        .expect_remove_header_map_value(Some(MapType::HttpRequestHeaders), Some("content-length"))
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":path"))
        .returning(Some("/llmrouting"))
        .expect_replace_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some(":path"),
            Some("/v1/chat/completions"),
        )
        .expect_get_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("x-katanemo-ratelimit-selector"),
        )
        .returning(None)
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();

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
        .expect_log(Some(LogLevel::Debug), None)
        .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
        .returning(Some(&config))
        .execute_and_expect(ReturnType::Bool(true))
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    normal_flow(&mut module, filter_context, http_context);

    let tool_call_detail = vec![ToolCallDetail {
        name: String::from("weather_forecast"),
        arguments: HashMap::from([(
            String::from("city"),
            IntOrString::Text(String::from("seattle")),
        )]),
    }];

    let boltfc_tools_call = BoltFCToolsCall {
        tool_calls: tool_call_detail,
    };

    let bolt_fc_resp = ChatCompletionsResponse {
        usage: Usage {
            completion_tokens: 0,
        },
        choices: vec![Choice {
            finish_reason: "test".to_string(),
            index: 0,
            message: Message {
                role: "system".to_string(),
                content: Some(serde_json::to_string(&boltfc_tools_call).unwrap()),
                model: None,
            },
        }],
        model: String::from("test"),
    };

    let bolt_fc_resp_str = serde_json::to_string(&bolt_fc_resp).unwrap();
    module
        .call_proxy_on_http_call_response(http_context, 3, 0, bolt_fc_resp_str.len() as i32, 0)
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&bolt_fc_resp_str))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_http_call(Some("weatherhost"), None, None, None, None)
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
        .expect_log(Some(LogLevel::Debug), None)
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
        .expect_log(Some(LogLevel::Debug), None)
        .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
        .returning(Some(&config_str))
        .execute_and_expect(ReturnType::Bool(true))
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    normal_flow(&mut module, filter_context, http_context);

    let tool_call_detail = vec![ToolCallDetail {
        name: String::from("weather_forecast"),
        arguments: HashMap::from([(
            String::from("city"),
            IntOrString::Text(String::from("seattle")),
        )]),
    }];

    let boltfc_tools_call = BoltFCToolsCall {
        tool_calls: tool_call_detail,
    };

    let bolt_fc_resp = ChatCompletionsResponse {
        usage: Usage {
            completion_tokens: 0,
        },
        choices: vec![Choice {
            finish_reason: "test".to_string(),
            index: 0,
            message: Message {
                role: "system".to_string(),
                content: Some(serde_json::to_string(&boltfc_tools_call).unwrap()),
                model: None,
            },
        }],
        model: String::from("test"),
    };

    let bolt_fc_resp_str = serde_json::to_string(&bolt_fc_resp).unwrap();
    module
        .call_proxy_on_http_call_response(http_context, 3, 0, bolt_fc_resp_str.len() as i32, 0)
        .expect_metric_increment("active_http_calls", -1)
        .expect_get_buffer_bytes(Some(BufferType::HttpCallResponseBody))
        .returning(Some(&bolt_fc_resp_str))
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_http_call(Some("weatherhost"), None, None, None, None)
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
        .expect_log(Some(LogLevel::Debug), None)
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
