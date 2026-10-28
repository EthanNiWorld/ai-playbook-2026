#!/usr/bin/env bash
set -Eeuo pipefail

VLLM_BIN="${VLLM_BIN:-/root/.conda/envs/qwen3.8/bin/vllm}"
SWEEP_PORT="${SWEEP_PORT:-8000}"
SWEEP_SERVER_LOG="${SWEEP_SERVER_LOG:-/data/benchmark-results/native-sweep/server-${SWEEP_PORT}.log}"

mkdir -p "$(dirname "$SWEEP_SERVER_LOG")"
exec "$VLLM_BIN" "$@" >"$SWEEP_SERVER_LOG" 2>&1
