use proxy_wasm::hostcalls;
use proxy_wasm::types::*;

#[allow(unused)]
pub trait Metric {
    fn id(&self) -> u32;
    fn value(&self) -> u64 {
        match hostcalls::get_metric(self.id()) {
            Ok(value) => value,
            Err(Status::NotFound) => panic!("metric not found: {}", self.id()),
            Err(err) => panic!("unexpected status: {:?}", err),
        }
    }
}

#[allow(unused)]
pub trait IncrementingMetric: Metric {
    fn increment(&self, offset: i64) {
        match hostcalls::increment_metric(self.id(), offset) {
            Ok(data) => data,
            Err(Status::NotFound) => panic!("metric not found: {}", self.id()),
            Err(err) => panic!("unexpected status: {:?}", err),
        }
    }
}

pub trait RecordingMetric: Metric {
    fn record(&self, value: u64) {
        match hostcalls::record_metric(self.id(), value) {
            Ok(data) => data,
            Err(Status::NotFound) => panic!("metric not found: {}", self.id()),
            Err(err) => panic!("unexpected status: {:?}", err),
        }
    }
}

#[derive(Copy, Clone)]
pub struct Counter {
    id: u32,
}

#[allow(unused)]
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

#[derive(Copy, Clone)]
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

impl RecordingMetric for Gauge {}

#[derive(Copy, Clone)]
pub struct Histogram {
    id: u32,
}

#[allow(unused)]
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
