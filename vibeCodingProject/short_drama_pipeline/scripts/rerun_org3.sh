#!/bin/zsh
# 按 wan3.0 新版本链路重跑 run_011（霸道总裁回乡盖新房），参数与 run_011 对齐：
# 图库模式 4 张客户图 + 于总/马老师双克隆音色路由，全自动（无 --manual）。
cd "$(dirname "$0")/.."
R11=output/run_011_20261121_125023
exec .venv/bin/python run_demo.py \
  --theme "霸道总裁回乡盖新房" \
  --custom-images "$R11/custom_01.jpg" "$R11/custom_02.jpg" "$R11/custom_03.jpg" "$R11/custom_04.png" \
  --voice-map '{"于总": "qwen-audio-3.1-tts-plus-testwan-e04e5295c1984305a82f4b8cda88c677", "马老师": "qwen-audio-3.1-tts-plus-malaoshi-12a0d668a8f54b36939be4635d60cf82"}'