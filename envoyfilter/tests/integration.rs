use proxy_wasm_test_framework::tester;
use proxy_wasm_test_framework::types::{
    Action, BufferType, LogLevel, MapType, MetricType, ReturnType,
};
use std::path::Path;

fn wasm_module() -> String {
    let wasm_file =
        Path::new("target/wasm32-unknown-unknown/release/intelligent_prompt_gateway.wasm");
    assert!(
        wasm_file.exists(),
        "Run `cargo build --release --target=wasm32-unknown-unknown` first"
    );
    wasm_file.to_str().unwrap().to_string()
}

#[test]
fn it_loads() {
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
        .expect_metric_creation(MetricType::Counter, "example_counter")
        .expect_metric_creation(MetricType::Gauge, "example_gauge")
        .expect_metric_creation(MetricType::Histogram, "example_histogram")
        .expect_metric_increment("example_counter", 10)
        .expect_metric_get("example_counter", 10)
        .expect_metric_record("example_gauge", 20)
        .expect_metric_record("example_histogram", 30)
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
    module.call_proxy_on_request_body(http_context, body_size, end_of_stream)

    // module
    //     .call_proxy_on_response_headers(http_context, 0, true)
    //     .expect_log(Some(LogLevel::Debug), Some("#2 on_http_response_headers"))
    //     .execute_and_expect(ReturnType::Action(Action::Continue))
    //     .unwrap();
}
