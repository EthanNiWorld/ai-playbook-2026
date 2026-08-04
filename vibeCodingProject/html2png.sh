#!/bin/bash
# html2png.sh - 将本地 HTML 文件转为 2x Retina 高清 PNG
# 用法: html2png.sh input.html output.png [width]
# 示例: html2png.sh ModelStudio-api-sales-guide-20260720.html out.png 920
#
# 镜像配置（国内网络默认走阿里云/npmmirror，加速安装）
# 海外网络可设环境变量回退默认源：
#   PIP_INDEX="" PW_HOST="" html2png.sh input.html output.png

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

# 镜像配置（国内网络默认走阿里云/npmmirror；海外设 PIP_INDEX="" PW_HOST="" 回退默认源）
PIP_INDEX="${PIP_INDEX:-https://mirrors.aliyun.com/pypi/simple/}"
PW_HOST="${PW_HOST:-https://registry.npmmirror.com/-/binary/playwright}"

# [1/3] 检查 venv
if [ ! -d "$VENV" ] || [ ! -f "$VENV/bin/python" ]; then
  echo "[1/3] 创建 venv（pip 镜像: ${PIP_INDEX:-默认源}）..."
  python3 -m venv "$VENV"
  if [ -n "$PIP_INDEX" ]; then
    "$VENV/bin/pip" install playwright --quiet -i "$PIP_INDEX"
  else
    "$VENV/bin/pip" install playwright --quiet
  fi
else
  echo "[1/3] venv 已存在"
fi

# [2/3] 检查 chromium（验证版本是否匹配当前 Playwright）
NEED_INSTALL=true
if [ -d "$CHROMIUM_DIR" ]; then
  # 通过实际启动验证已缓存版本是否与 Playwright 版本匹配
  if "$VENV/bin/python" -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    b.close()
" 2>/dev/null; then
    NEED_INSTALL=false
  fi
fi

if [ "$NEED_INSTALL" = true ]; then
  echo "[2/3] 下载 chromium（镜像: ${PW_HOST:-默认源}，首次需要 1-2 分钟）..."
  if [ -n "$PW_HOST" ]; then
    PLAYWRIGHT_DOWNLOAD_HOST="$PW_HOST" "$VENV/bin/python" -m playwright install chromium
  else
    "$VENV/bin/python" -m playwright install chromium
  fi
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
    # 屏蔽 Google Fonts 外部字体，避免网络不稳时 goto/screenshot 阻塞超时，回退系统字体
    context.route(lambda url: "fonts.googleapis.com" in url or "fonts.gstatic.com" in url,
                  lambda route: route.abort())
    page = context.new_page()
    page.goto('file://$INPUT_ABS')
    page.wait_for_load_state('networkidle')
    page.screenshot(path='$OUTPUT', full_page=True)
    browser.close()
EOF

echo "完成 ✅  -> $OUTPUT"
