#!/bin/zsh
# Web SSE 冒烟：通过 /api/run 触发一次 1 场景流水线，事件流落盘供验证
set -e
cd "$(dirname "$0")/.."
printf '%s' '{"theme":"都市逆袭短剧","scenes":1}' > output/_run_body.json
curl -sN -X POST http://127.0.0.1:7861/api/run \
  -H 'Content-Type: application/json' \
  --data @output/_run_body.json > output/ui_run_sse.log 2>&1
echo "SSE_DONE"
