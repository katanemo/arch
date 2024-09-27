RUST_VERSION=1.80.0
docker run --rm -v rustup_cache:/usr/local/rustup/ rust:$RUST_VERSION rustup -v target add wasm32-wasi
docker run --rm -v $PWD/../open-message-format:/code/open-message-format -v ~/.cargo:/root/.cargo -v $(pwd):/code/arch -w /code/arch -v rustup_cache:/usr/local/rustup/ rust:$RUST_VERSION cargo build --release --target wasm32-wasi
