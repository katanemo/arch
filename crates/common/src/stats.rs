use log::error;
use proxy_wasm::hostcalls;
use proxy_wasm::types::*;

pub trait Metric {
    fn id(&self) -> u32;
    fn value(&self) -> Result<u64, String> {
        match hostcalls::get_metric(self.id()) {
            Ok(value) => Ok(value),
            Err(Status::NotFound) => Err(format!("metric not found: {}", self.id())),
            Err(err) => Err(format!("unexpected status: {:?}", err)),
        }
    }
}

pub trait IncrementingMetric: Metric {
    fn increment(&self, offset: i64) {
        match hostcalls::increment_metric(self.id(), offset) {
            Ok(_) => (),
            Err(err) => error!("error incrementing metric: {:?}", err),
        }
    }
}

pub trait RecordingMetric: Metric {
    fn record(&self, value: u64) {
        match hostcalls::record_metric(self.id(), value) {
            Ok(_) => (),
            Err(err) => error!("error recording metric: {:?}", err),
        }
    }
}

#[derive(Copy, Clone, Debug)]
pub struct Counter {
    id: u32,
}

impl Counter {
    pub fn new(name: String) -> Counter {
        let returned_id = hostcalls::define_metric(MetricType::Counter, &name)
            .expect("failed to define counter '{}', name");
        Counter { id: returned_id }
    }
}

impl Metric for Counter {
    fn id(&self) -> u32 {
        self.id
    }
}

impl IncrementingMetric for Counter {}

#[derive(Copy, Clone, Debug)]
pub struct Gauge {
    id: u32,
}

impl Gauge {
    pub fn new(name: String) -> Gauge {
        let returned_id = hostcalls::define_metric(MetricType::Gauge, &name)
            .expect("failed to define gauge '{}', name");
        Gauge { id: returned_id }
    }
}

impl Metric for Gauge {
    fn id(&self) -> u32 {
        self.id
    }
}

/// For state of the world updates
impl RecordingMetric for Gauge {}
/// For offset deltas
impl IncrementingMetric for Gauge {}

#[derive(Copy, Clone, Debug)]
pub struct Histogram {
    id: u32,
}

impl Histogram {
    pub fn new(name: String) -> Histogram {
        let returned_id = hostcalls::define_metric(MetricType::Histogram, &name)
            .expect("failed to define histogram '{}', name");
        Histogram { id: returned_id }
    }
}

impl Metric for Histogram {
    fn id(&self) -> u32 {
        self.id
    }
}

impl RecordingMetric for Histogram {}
