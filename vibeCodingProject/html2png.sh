#!/bin/bash
# html2png.sh - 将本地 HTML 文件转为 2x Retina 高清 PNG
# 用法: html2png.sh input.html output.png [width]
# 示例: html2png.sh ModelStudio-api-sales-guide-20260629.html out.png 920

set -e

INPUT="$1"
OUTPUT="$2"
WIDTH="${3:-920}"

if [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
  echo "用法: $0 <input.html> <output.png> [width=920]"
  exit 1
fi

VENV="/tmp/pw_venv"
CHROMIUM_DIR="$HOME/Library/Caches/ms-playwright"

# [1/3] 检查 venv
if [ ! -d "$VENV" ] || [ ! -f "$VENV/bin/python" ]; then
  echo "[1/3] 创建 venv ..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install playwright --quiet
else
  echo "[1/3] venv 已存在"
fi

# [2/3] 检查 chromium 缓存
NEED_INSTALL=true
if [ -d "$CHROMIUM_DIR" ]; then
  for dir in "$CHROMIUM_DIR"/chromium_headless_shell-*; do
    [ -d "$dir" ] || continue
    if [ -f "$dir/chrome-headless-shell-mac-arm64/chrome-headless-shell" ] || [ -f "$dir/chrome-headless-shell-mac-x64/chrome-headless-shell" ]; then
      NEED_INSTALL=false
      break
    fi
  done
fi

if [ "$NEED_INSTALL" = true ]; then
  echo "[2/3] 下载 chromium（首次需要 1-2 分钟）..."
  "$VENV/bin/python" -m playwright install chromium
else
  echo "[2/3] chromium 已就绪"
fi

# [3/3] 生成 PNG
echo "[3/3] 生成 2x Retina PNG (宽 ${WIDTH}px) ..."
INPUT_ABS=$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")
"$VENV/bin/python" <<EOF
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        viewport={'width': $WIDTH, 'height': 1800},
        device_scale_factor=2
    )
    page = context.new_page()
    page.goto('file://$INPUT_ABS')
    page.wait_for_load_state('networkidle')
    page.screenshot(path='$OUTPUT', full_page=True)
    browser.close()
EOF

echo "完成 ✅  -> $OUTPUT"
