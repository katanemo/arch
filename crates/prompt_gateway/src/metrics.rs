use common::stats::Gauge;

#[derive(Copy, Clone, Debug)]
pub struct Metrics {
    pub active_http_calls: Gauge,
}

impl Metrics {
    pub fn new() -> Metrics {
        Metrics {
            active_http_calls: Gauge::new(String::from("active_http_calls")),
        }
    }
}
