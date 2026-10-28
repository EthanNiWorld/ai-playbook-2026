#!/usr/bin/env bash
set -Eeuo pipefail

SWEEP_HOST="${SWEEP_HOST:-127.0.0.1}"
SWEEP_PORT="${SWEEP_PORT:-8000}"
BASE_URL="http://${SWEEP_HOST}:${SWEEP_PORT}"

for endpoint in reset_prefix_cache reset_mm_cache reset_encoder_cache; do
    curl -fsS -X POST "${BASE_URL}/${endpoint}" >/dev/null
done
