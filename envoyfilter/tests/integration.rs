use proxy_wasm_test_framework::tester;
use proxy_wasm_test_framework::types::{Action, BufferType, LogLevel, MapType, ReturnType};
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

    let root_context = 1;
    // let cfg = r#"{
    //     "failureMode": "deny",
    //     "rateLimitPolicies": []
    // }"#;

    module
        .call_proxy_on_context_create(root_context, 0)
        .expect_log(Some(LogLevel::Info), Some("#1 set_root_context"))
        .execute_and_expect(ReturnType::None)
        .unwrap();
    // module
    //     .call_proxy_on_configure(root_context, 0)
    //     .expect_log(Some(LogLevel::Info), Some("#1 on_configure"))
    //     .expect_get_buffer_bytes(Some(BufferType::PluginConfiguration))
    //     .returning(Some(cfg.as_bytes()))
    //     .expect_log(Some(LogLevel::Info), None)
    //     .execute_and_expect(ReturnType::Bool(true))
    //     .unwrap();

    let http_context = 2;
    module
        .call_proxy_on_context_create(http_context, root_context)
        .expect_log(Some(LogLevel::Debug), Some("#2 create_http_context"))
        .execute_and_expect(ReturnType::None)
        .unwrap();

    module
        .call_proxy_on_request_headers(http_context, 0, true)
        .expect_log(Some(LogLevel::Debug), Some("#2 on_http_request_headers"))
        .expect_get_header_map_value(Some(MapType::HttpRequestHeaders), Some(":authority"))
        .returning(Some("cars.toystore.com"))
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();

    module
        .call_proxy_on_response_headers(http_context, 0, true)
        .expect_log(Some(LogLevel::Debug), Some("#2 on_http_response_headers"))
        .execute_and_expect(ReturnType::Action(Action::Continue))
        .unwrap();
}
