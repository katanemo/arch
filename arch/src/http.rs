use crate::stats::{Gauge, IncrementingMetric};
use proxy_wasm::traits::Context;
use std::{cell::RefCell, collections::HashMap, time::Duration};

#[derive(Debug)]
pub struct CallArgs<'a> {
    upstream: &'a str,
    headers: Vec<(&'a str, &'a str)>,
    body: Option<&'a [u8]>,
    trailers: Vec<(&'a str, &'a str)>,
    timeout: Duration,
}

impl<'a> CallArgs<'a> {
    pub fn new(
        upstream: &'a str,
        headers: Vec<(&'a str, &'a str)>,
        body: Option<&'a [u8]>,
        trailers: Vec<(&'a str, &'a str)>,
        timeout: Duration,
    ) -> Self {
        CallArgs {
            upstream,
            headers,
            body,
            trailers,
            timeout,
        }
    }
}

pub trait Client: Context {
    type CallContext;

    fn http_call(&self, call_args: CallArgs, call_context: Self::CallContext) {
        let id = self
            .dispatch_http_call(
                call_args.upstream,
                call_args.headers,
                call_args.body,
                call_args.trailers,
                call_args.timeout,
            )
            .inspect_err(|err| {
                panic!(
                    "Error dispatching HTTP call to `{}`, error: {:?}",
                    call_args.upstream, err
                );
            })
            .unwrap();

        self.add_call_context(id, call_context);
    }

    fn add_call_context(&self, id: u32, call_context: Self::CallContext) {
        let callouts = self.callouts();
        if let Some(_) = callouts.borrow_mut().insert(id, call_context) {
            panic!("Duplicate http call with id={}", id);
        }
        self.active_http_calls().increment(1);
    }

    fn callouts(&self) -> &RefCell<HashMap<u32, Self::CallContext>>;

    fn active_http_calls(&self) -> &Gauge;
}
