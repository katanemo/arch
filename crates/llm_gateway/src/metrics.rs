use common::stats::{Counter, Gauge, Histogram};

#[derive(Copy, Clone, Debug)]
pub struct Metrics {
    pub active_http_calls: Gauge,
    pub ratelimited_rq: Counter,
    pub time_to_first_token: Histogram,
    pub time_per_output_token: Histogram,
    pub tokens_per_second: Histogram,
    pub request_latency: Histogram,
    pub output_sequence_length: Histogram,
    pub input_sequence_length: Histogram,
}

impl Metrics {
    pub fn new() -> Metrics {
        Metrics {
            active_http_calls: Gauge::new(String::from("active_http_calls")),
            ratelimited_rq: Counter::new(String::from("ratelimited_rq")),
            time_to_first_token: Histogram::new(String::from("time_to_first_token")),
            time_per_output_token: Histogram::new(String::from("time_per_output_token")),
            tokens_per_second: Histogram::new(String::from("tokens_per_second")),
            request_latency: Histogram::new(String::from("request_latency")),
            output_sequence_length: Histogram::new(String::from("output_sequence_length")),
            input_sequence_length: Histogram::new(String::from("input_sequence_length")),
        }
    }
}
