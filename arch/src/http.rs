use crate::stats::{Gauge, IncrementingMetric};
use log::debug;
use proxy_wasm::{traits::Context, types::Status};
use std::{cell::RefCell, collections::HashMap, fmt::Debug, time::Duration};

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

#[derive(thiserror::Error, Debug)]
pub enum ClientError {
    #[error("Error dispatching HTTP call to `{upstream_name}`, error: {internal_status:?}")]
    DispatchError {
        upstream_name: String,
        internal_status: Status,
    },
}

pub trait Client: Context {
    type CallContext: Debug;

    fn http_call(
        &self,
        call_args: CallArgs,
        call_context: Self::CallContext,
    ) -> Result<(), ClientError> {
        debug!(
            "dispatching http call with args={:?} context={:?}",
            call_args, call_context
        );

        match self.dispatch_http_call(
            call_args.upstream,
            call_args.headers,
            call_args.body,
            call_args.trailers,
            call_args.timeout,
        ) {
            Ok(id) => {
                self.add_call_context(id, call_context);
                Ok(())
            }
            Err(status) => Err(ClientError::DispatchError {
                upstream_name: String::from(call_args.upstream),
                internal_status: status.clone(),
            }),
        }
    }

    fn add_call_context(&self, id: u32, call_context: Self::CallContext) {
        let callouts = self.callouts();
        if callouts.borrow_mut().insert(id, call_context).is_some() {
            panic!("Duplicate http call with id={}", id);
        }
        self.active_http_calls().increment(1);
    }

    fn callouts(&self) -> &RefCell<HashMap<u32, Self::CallContext>>;

    fn active_http_calls(&self) -> &Gauge;
}
