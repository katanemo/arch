use std::time::Duration;

use proxy_wasm::traits::Context;

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

    fn http_call(&mut self, call_args: CallArgs, call_context: Self::CallContext) {
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

    fn add_call_context(&mut self, id: u32, call_context: Self::CallContext);
}
