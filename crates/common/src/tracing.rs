use rand::RngCore;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct ResourceSpan {
    pub resource: Resource,
    #[serde(rename = "scopeSpans")]
    pub scope_spans: Vec<ScopeSpan>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Resource {
    pub attributes: Vec<Attribute>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ScopeSpan {
    scope: Scope,
    spans: Vec<Span>,
}

#[derive(Serialize, Deserialize, Debug)]
struct Scope {
    name: String,
    version: String,
    attributes: Vec<Attribute>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Span {
    #[serde(rename = "traceId")]
    pub trace_id: String,
    #[serde(rename = "spanId")]
    pub span_id: String,
    #[serde(rename = "parentSpanId")]
    pub parent_span_id: Option<String>, // Optional in case there’s no parent span
    pub name: String,
    #[serde(rename = "startTimeUnixNano")]
    pub start_time_unix_nano: String,
    #[serde(rename = "endTimeUnixNano")]
    pub end_time_unix_nano: String,
    pub kind: u32,
    pub attributes: Vec<Attribute>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Attribute {
    key: String,
    value: AttributeValue,
}

#[derive(Serialize, Deserialize, Debug)]
struct AttributeValue {
    #[serde(rename = "stringValue")]
    string_value: Option<String>, // Use Option to handle different value types
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TraceData {
    #[serde(rename = "resourceSpans")]
    resource_spans: Vec<ResourceSpan>,
}

impl TraceData {
    pub fn new() -> Self {
        TraceData {
            resource_spans: Vec::new(),
        }
    }

    pub fn add_span(&mut self, span: Span) {
        if self.resource_spans.is_empty() {
            let resource = Resource {
                attributes: vec![Attribute {
                    key: "service.name".to_string(),
                    value: AttributeValue {
                        string_value: Some("upstream-llm".to_string()),
                    },
                }],
            };
            let scope_span = ScopeSpan {
                scope: Scope {
                    name: "default".to_string(),
                    version: "1.0".to_string(),
                    attributes: Vec::new(),
                },
                spans: Vec::new(),
            };
            let resource_span = ResourceSpan {
                resource,
                scope_spans: vec![scope_span],
            };
            self.resource_spans.push(resource_span);
        }
        self.resource_spans[0].scope_spans[0].spans.push(span);
    }
}

pub fn get_random_span_id() -> String {
    let mut rng = rand::thread_rng();
    let mut random_bytes = [0u8; 8];
    rng.fill_bytes(&mut random_bytes);

    hex::encode(random_bytes)
}
