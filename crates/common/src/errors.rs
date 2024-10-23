use proxy_wasm::types::Status;
use serde_json::error;

use crate::{common_types::open_ai::ChatCompletionChunkResponseError, ratelimit};

#[derive(thiserror::Error, Debug)]
pub enum ClientError {
    #[error("Error dispatching HTTP call to `{upstream_name}/{path}`, error: {internal_status:?}")]
    DispatchError {
        upstream_name: String,
        path: String,
        internal_status: Status,
    },
}

#[derive(thiserror::Error, Debug)]
pub enum ServerError {
    #[error(transparent)]
    HttpDispatch(ClientError),
    #[error(transparent)]
    Deserialization(serde_json::Error),
    #[error(transparent)]
    Serialization(serde_json::Error),
    #[error("{0}")]
    LogicError(String),
    #[error("upstream error response authority={authority}, path={path}, status={status}")]
    Upstream {
        authority: String,
        path: String,
        status: String,
    },
    #[error("jailbreak detected: {0}")]
    Jailbreak(String),
    #[error("{why}")]
    NoMessagesFound { why: String },
    #[error(transparent)]
    ExceededRatelimit(ratelimit::Error),
    #[error("{why}")]
    BadRequest { why: String },
    #[error("error in streaming response")]
    Streaming(#[from] ChatCompletionChunkResponseError),
}
