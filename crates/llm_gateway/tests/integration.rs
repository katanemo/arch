use http::StatusCode;
use proxy_wasm_test_framework::tester::{self, Tester};
use proxy_wasm_test_framework::types::{
    Action, BufferType, LogLevel, MapType, MetricType, ReturnType,
};
use serial_test::serial;
use std::path::Path;

fn wasm_module() -> String {
    let wasm_file = Path::new("../target/wasm32-wasi/release/llm_gateway.wasm");
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
        .expect_log(Some(LogLevel::Debug), None)
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
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":path"))
        .returning(Some("/v1/chat/completions"))
        .expect_get_header_map_pairs(Some(MapType::HttpRequestHeaders))
        .returning(None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some("x-request-id"))
        .returning(None)
        .expect_get_current_time_nanos()
        .returning(Some(0))
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
}

fn setup_filter(module: &mut Tester, config: &str) -> i32 {
    let filter_context = 1;

    module
        .call_proxy_on_context_create(filter_context, 0)
        .expect_metric_creation(MetricType::Gauge, "active_http_calls")
        .expect_metric_creation(MetricType::Counter, "ratelimited_rq")
        .expect_metric_creation(MetricType::Histogram, "time_to_first_token")
        .expect_metric_creation(MetricType::Histogram, "time_per_output_token")
        .expect_metric_creation(MetricType::Histogram, "latency")
        .expect_metric_creation(MetricType::Histogram, "output_sequence_length")
        .expect_metric_creation(MetricType::Histogram, "input_sequence_length")
        .execute_and_expect(ReturnType::None)
        .unwrap();

    module
        .call_proxy_on_configure(filter_context, config.len() as i32)
        .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
        .returning(Some(config))
        .execute_and_expect(ReturnType::Bool(true))
        .unwrap();

    filter_context
}

fn default_config() -> &'static str {
    r#"
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
  - name: open-ai-gpt-4o
    provider: openai
    access_key: secret_key
    model: gpt-4o

overrides:
  # confidence threshold for prompt target intent matching
  prompt_target_intent_matching_threshold: 0.6

system_prompt: |
  You are a helpful assistant.

prompt_guards:
  input_guards:
    jailbreak:
      on_exception:
        message: "Looks like you're curious about my abilities, but I can only provide assistance within my programmed parameters."

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

ratelimits:
  - model: gpt-4
    selector:
      key: selector-key
      value: selector-value
    limit:
      tokens: 100
      unit: minute
"#
}

#[test]
#[serial]
fn llm_gateway_successful_request_to_open_ai_chat_completions() {
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
    let filter_context = setup_filter(&mut module, default_config());

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
            \"content\": \"Compose a poem.\"\
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
        .expect_log(Some(LogLevel::Trace), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_set_buffer_bytes(Some(BufferType::HttpRequestBody), None)
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();
}

#[test]
#[serial]
fn llm_gateway_bad_request_to_open_ai_chat_completions() {
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
    let filter_context = setup_filter(&mut module, default_config());

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
fn llm_gateway_request_ratelimited() {
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
    let filter_context = setup_filter(&mut module, default_config());

    // Setup HTTP Stream
    let http_context = 2;

    normal_flow(&mut module, filter_context, http_context);

    // Request Body
    let chat_completions_request_body = "\
{\
    \"messages\": [\
    {\
        \"role\": \"system\",\
        \"content\": \"You are a helpful poetic assistant!, skilled in explaining complex programming concepts with creative flair. Be sure to be concise and to the point.\"\
    },\
    {\
        \"role\": \"user\",\
        \"content\": \"Compose a poem that explains the concept of recursion in programming. Compose a poem that explains the concept of recursion in programming. Compose a poem that explains the concept of recursion in programming. And also summarize it how a 4th graded would understand it.\"\
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
        .expect_log(Some(LogLevel::Trace), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        // .expect_metric_increment("active_http_calls", 1)
        .expect_send_local_response(
            Some(StatusCode::TOO_MANY_REQUESTS.as_u16().into()),
            None,
            None,
            None,
        )
        .expect_metric_increment("ratelimited_rq", 1)
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();
}

#[test]
#[serial]
fn llm_gateway_request_not_ratelimited() {
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
    let filter_context = setup_filter(&mut module, default_config());

    // Setup HTTP Stream
    let http_context = 2;

    normal_flow(&mut module, filter_context, http_context);

    // give shorter body to avoid rate limiting
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
        .expect_log(Some(LogLevel::Trace), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_log(Some(LogLevel::Debug), None)
        .expect_set_buffer_bytes(Some(BufferType::HttpRequestBody), None)
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();
}
