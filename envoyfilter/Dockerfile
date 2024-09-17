# build filter using rust toolchain
FROM rust:1.80.0 as builder
RUN rustup -v target add wasm32-wasi
WORKDIR /envoyfilter
COPY envoyfilter/src /envoyfilter/src
COPY envoyfilter/Cargo.toml /envoyfilter/
COPY envoyfilter/Cargo.lock /envoyfilter/
COPY open-message-format /open-message-format
COPY public_types /public_types

RUN cargo build --release --target wasm32-wasi

# copy built filter into envoy image
FROM envoyproxy/envoy:v1.30-latest
COPY --from=builder /envoyfilter/target/wasm32-wasi/release/intelligent_prompt_gateway.wasm /etc/envoy/proxy-wasm-plugins/intelligent_prompt_gateway.wasm
COPY envoyfilter/envoy.yaml /etc/envoy.yaml
# CMD ["envoy", "-c", "/etc/envoy/envoy.yaml"]
# CMD ["envoy", "-c", "/etc/envoy/envoy.yaml", "--log-level", "debug"]
CMD ["envoy", "-c", "/etc/envoy/envoy.yaml", "--component-log-level", "wasm:debug"]
