#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER="$root/zig-cc-aarch64"
export ZIG_GLOBAL_CACHE_DIR="${ZIG_GLOBAL_CACHE_DIR:-$root/.zig-cache}"
cargo build --locked --manifest-path "$root/mon0-probe/Cargo.toml" --release --target aarch64-unknown-linux-gnu
