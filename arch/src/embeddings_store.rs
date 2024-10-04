use crate::http::Client;
use crate::{
    consts::{DEFAULT_EMBEDDING_MODEL, MODEL_SERVER_NAME},
    filter_context::FilterContext,
    http::CallArgs,
};
use proxy_wasm::traits::Context;
use public_types::{
    common_types::EmbeddingType,
    configuration::PromptTarget,
    embeddings::{CreateEmbeddingRequest, CreateEmbeddingRequestInput, CreateEmbeddingResponse},
};
use std::{collections::HashMap, iter::Filter, sync::OnceLock, time::Duration};

pub type EmbeddingTypeMap = HashMap<EmbeddingType, Vec<f64>>;
pub type EmbeddingsStore = HashMap<String, EmbeddingTypeMap>;

pub fn embeddings_store() -> &'static EmbeddingsStore {
    static EMBEDDINGS_STORE: OnceLock<EmbeddingsStore> = OnceLock::new();
    EMBEDDINGS_STORE.get_or_init(|| {
        let embeddings: HashMap<String, EmbeddingTypeMap> = HashMap::new();
        embeddings
    })
}

fn process_prompt_targets(filter_context: &mut FilterContext) {
    for values in filter_context.prompt_targets().iter() {
        let prompt_target = values.1;
        schedule_embeddings_call(filter_context, &prompt_target.name, EmbeddingType::Name);
        schedule_embeddings_call(
            filter_context,
            &prompt_target.description,
            EmbeddingType::Description,
        );
    }
}

fn schedule_embeddings_call(
    filter_context: &mut FilterContext,
    input: &str,
    embedding_type: EmbeddingType,
) {
    let embeddings_input = CreateEmbeddingRequest {
        input: Box::new(CreateEmbeddingRequestInput::String(String::from(input))),
        model: String::from(DEFAULT_EMBEDDING_MODEL),
        encoding_format: None,
        dimensions: None,
        user: None,
    };
    let json_data = serde_json::to_string(&embeddings_input).unwrap();

    let call_args = CallArgs::new(
        MODEL_SERVER_NAME,
        vec![
            (":method", "POST"),
            (":path", "/embeddings"),
            (":authority", MODEL_SERVER_NAME),
            ("content-type", "application/json"),
            ("x-envoy-upstream-rq-timeout-ms", "60000"),
        ],
        Some(json_data.as_bytes()),
        vec![],
        Duration::from_secs(60),
    );

    let call_context = crate::filter_context::FilterCallContext {
        prompt_target: String::from(input),
        embedding_type,
    };

    filter_context.http_call(call_args, call_context);
}

fn embedding_response_handler(
    filter_context: &mut FilterContext,
    body_size: usize,
    embedding_type: EmbeddingType,
    prompt_target_name: String,
) {
    let prompt_targets = filter_context.prompt_targets();
    let prompt_target = prompt_targets.get(&prompt_target_name).unwrap();
    if let Some(body) = filter_context.get_http_call_response_body(0, body_size) {
        if !body.is_empty() {
            let mut embedding_response: CreateEmbeddingResponse =
                match serde_json::from_slice(&body) {
                    Ok(response) => response,
                    Err(e) => {
                        panic!(
                            "Error deserializing embedding response. body: {:?}: {:?}",
                            String::from_utf8(body).unwrap(),
                            e
                        );
                    }
                };

            let embeddings = embedding_response.data.remove(0).embedding;
            log::info!(
                "Adding embeddings for prompt target name: {:?}, description: {:?}, embedding type: {:?}",
                prompt_target.name,
                prompt_target.description,
                embedding_type
            );

            // embeddings_store().insert(
            //     prompt_target.name.clone(),
            //     HashMap::from([(embedding_type, embeddings)]),
            // );
        }
    } else {
        panic!("No body in response");
    }
}
