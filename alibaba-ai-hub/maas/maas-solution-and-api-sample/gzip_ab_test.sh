#!/bin/bash
# gzip 请求体支持性 A/B 验证：同一 payload 分别以明文 / gzip+Content-Encoding 发送
# 判定：gzip 侧返回 200 且内容正常 => 该端点支持解压；400/415 => 不支持
# 覆盖矩阵：公共 compatible-mode / workspace compatible-mode / DashScope 原生 API
# 用法：bash gzip_ab_test.sh （从仓库根目录 .env 读取 Key，不回显）
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../../../.env"
# .env 含 shell 不兼容变量名，不能整体 source，只提取所需变量
getenv() { grep "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }

KEY_SGP="$(getenv DASHSCOPE_API_KEY_SGP)"
KEY_WS="$(getenv DASHSCOPE_API_KEY_INTL_SG_TEST)"
URL_WS="$(getenv DASHSCOPE_API_KEY_INTL_SG_TEST_URL)"
TMP="$(mktemp -d)"

python3 - "$TMP" <<'EOF'
import json, sys
t = sys.argv[1]
msgs = [{"role": "user", "content": "只回复OK"}]
# OpenAI 兼容格式
p = {"model": "deepseek-v4.1-flash", "messages": msgs, "max_tokens": 8}
open(t + '/openai.json', 'w').write(json.dumps(p, ensure_ascii=False))
# DashScope 原生格式
n = {"model": "deepseek-v4.1-flash", "input": {"messages": msgs},
     "parameters": {"max_tokens": 8, "result_format": "message"}}
open(t + '/native.json', 'w').write(json.dumps(n, ensure_ascii=False))
EOF
gzip -c "$TMP/openai.json" > "$TMP/openai.gz"
gzip -c "$TMP/native.json" > "$TMP/native.gz"

run_case() { # $1=名称 $2=URL $3=KEY $4=body文件 $5=是否gzip(0/1)
  local enc=()
  [ "$5" = "1" ] && enc=(-H 'Content-Encoding: gzip')
  printf '%-38s' "$1"
  curl -s -o "$TMP/resp.out" -w 'status:%{http_code} ttfb:%{time_starttransfer}s up:%{size_upload}B ' \
    "$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' \
    "${enc[@]}" --data-binary @"$4"
  head -c 160 "$TMP/resp.out"; echo
}

PUB="https://dashscope-intl.aliyuncs.com"
echo "== 1. 公共 compatible-mode =="
run_case "A 明文" "$PUB/compatible-mode/v1/chat/completions" "$KEY_SGP" "$TMP/openai.json" 0
run_case "B gzip" "$PUB/compatible-mode/v1/chat/completions" "$KEY_SGP" "$TMP/openai.gz" 1

if [ -n "$KEY_WS" ] && [ -n "$URL_WS" ]; then
  echo "== 2. workspace compatible-mode =="
  run_case "C 明文" "$URL_WS/chat/completions" "$KEY_WS" "$TMP/openai.json" 0
  run_case "D gzip" "$URL_WS/chat/completions" "$KEY_WS" "$TMP/openai.gz" 1
fi

echo "== 3. DashScope 原生 API =="
NATIVE="$PUB/api/v1/services/aigc/text-generation/generation"
run_case "E 明文" "$NATIVE" "$KEY_SGP" "$TMP/native.json" 0
run_case "F gzip" "$NATIVE" "$KEY_SGP" "$TMP/native.gz" 1