# Envoy filter code for gateway

## Building

```sh
$ cargo build --target wasm32-wasi --release
```

## Using in Envoy

This example can be run with [`docker compose`](https://docs.docker.com/compose/install/)
and has a matching Envoy configuration.

```sh
$ docker compose up
```

## Examples

### Direct response.

Send HTTP request to `localhost:10000/hello`:

```sh
$ curl localhost:10000/hello
```

Expected response:

```console
HTTP/1.1 200 OK
content-length: 40
content-type: text/plain
custom-header: katanemo filter
date: Wed, 10 Jul 2024 16:59:43 GMT
server: envoy
```

### Inline call.

Send HTTP request to `localhost:10000/inline`:

```sh
$ curl localhost:10000/hello
{
  "headers": {
    "Accept": "*/*",
    "Host": "localhost",
    "User-Agent": "curl/7.81.0",
    "X-Amzn-Trace-Id": "Root=1-637c4767-6e31776a0b407a0219b5b570",
    "X-Envoy-Expected-Rq-Timeout-Ms": "15000"
  }
}
```

Expected Envoy logs:

```console
[...] wasm log http_auth_random: Access granted.
```
