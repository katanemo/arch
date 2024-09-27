# build filter using rust toolchain
FROM rust:1.80.0 as builder
RUN rustup -v target add wasm32-wasi
WORKDIR /arch
COPY arch/src /arch/src
COPY arch/Cargo.toml /arch/
COPY arch/Cargo.lock /arch/
COPY public_types /public_types

RUN cargo build --release --target wasm32-wasi

# copy built filter into envoy image
FROM envoyproxy/envoy:v1.30-latest
COPY --from=builder /arch/target/wasm32-wasi/release/intelligent_prompt_gateway.wasm /etc/envoy/proxy-wasm-plugins/intelligent_prompt_gateway.wasm
# CMD ["envoy", "-c", "/etc/envoy/envoy.yaml"]
# CMD ["envoy", "-c", "/etc/envoy/envoy.yaml", "--log-level", "debug"]
CMD ["envoy", "-c", "/etc/envoy/envoy.yaml", "--component-log-level", "wasm:debug"]
