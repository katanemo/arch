use proxy_wasm_test_framework::tester;
use proxy_wasm_test_framework::types::{
    Action, BufferType, LogLevel, MapType, MetricType, ReturnType,
};
use std::path::Path;

fn wasm_module() -> String {
    let wasm_file = Path::new("target/wasm32-wasi/release/intelligent_prompt_gateway.wasm");
    assert!(
        wasm_file.exists(),
        "Run `cargo build --release --target=wasm32-wasi` first"
    );
    wasm_file.to_str().unwrap().to_string()
}

#[test]
fn request_to_open_ai_chat_completions() {
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
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Setup HTTP Stream
    let http_context = 2;

    module
        .call_proxy_on_context_create(http_context, root_context)
        .execute_and_expect(ReturnType::None)
        .unwrap();

    // Request Headers
    module
        .call_proxy_on_request_headers(http_context, 0, false)
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":host"))
        .returning(Some("api.openai.com"))
        .expect_add_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some("content-length"),
            Some(""),
        )
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":path"))
        .returning(Some("/llmrouting"))
        .expect_add_header_map_value(
            Some(MapType::HttpRequestHeaders),
            Some(":path"),
            Some("/v1/chat/completions"),
        )
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
        ]\
    }";

    module
        .call_proxy_on_request_body(
            http_context,
            chat_completions_request_body.len() as i32,
            true,
        )
        .expect_get_buffer_bytes(Some(BufferType::HttpRequestBody))
        .returning(Some(chat_completions_request_body))
        // TODO: assert that the model field was added.
        .expect_set_buffer_bytes(Some(BufferType::HttpRequestBody), None)
        .expect_log(Some(LogLevel::Info), None)
        .execute_and_expect(ReturnType::Action(Action::Pause))
        .unwrap();
}
