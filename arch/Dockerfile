# build filter using rust toolchain
FROM rust:1.80.0 as builder
RUN rustup -v target add wasm32-wasi
WORKDIR /arch
COPY crates .

RUN cd prompt_gateway && cargo build --release --target wasm32-wasi
RUN cd llm_gateway && cargo build --release --target wasm32-wasi

# copy built filter into envoy image
FROM envoyproxy/envoy:v1.31-latest as envoy

#Build config generator, so that we have a single build image for both Rust and Python
FROM python:3-slim as arch
COPY --from=builder /arch/target/wasm32-wasi/release/prompt_gateway.wasm /etc/envoy/proxy-wasm-plugins/prompt_gateway.wasm
COPY --from=builder /arch/target/wasm32-wasi/release/llm_gateway.wasm /etc/envoy/proxy-wasm-plugins/llm_gateway.wasm
COPY --from=envoy /usr/local/bin/envoy /usr/local/bin/envoy
WORKDIR /config
COPY arch/requirements.txt .
RUN pip install -r requirements.txt
COPY arch/tools/cli/config_generator.py .
COPY arch/envoy.template.yaml .
COPY arch/arch_config_schema.yaml .

CMD ["sh", "-c", "python config_generator.py && envoy -c /etc/envoy/envoy.yaml --component-log-level wasm:debug"]
