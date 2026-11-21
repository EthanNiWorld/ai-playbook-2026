"""ASR 台词质检：用 qwen-audio-3.1-asr-flash 识别配音音频，与分镜台词逐场比对。

同步多模态 HTTP 接口（不支持 SDK）：POST /services/aigc/multimodal-generation/generation，
音频走 input_audio.data（base64 data URI），parameters 带 format/sample_rate，
3.1 代际响应文本在 output.text。

用法：
  质检全片配音    .venv/bin/python -u scripts/qa_dubbing.py <run目录>
  质检单条 TTS    .venv/bin/python -u scripts/qa_dubbing.py --audio <mp3路径>
"""
import argparse
import base64
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

ASR_MODEL = "qwen-audio-3.1-asr-flash"


def asr(audio_path):
    """单条音频 → 识别文本。"""
    with open(audio_path, "rb") as f:
        data_uri = "data:audio/mp4;base64," + base64.b64encode(f.read()).decode()
    fmt = os.path.splitext(audio_path)[1].lstrip(".").lower()
    fmt = {"mp3": "mp3", "m4a": "m4a", "wav": "wav"}.get(fmt, "mp3")
    r = requests.post(
        config.NATIVE_BASE_URL.rstrip("/") + "/services/aigc/multimodal-generation/generation",
        headers={"Authorization": f"Bearer {config.API_KEY}", "X-DashScope-SSE": "disable"},
        json={"model": ASR_MODEL,
              "input": {"messages": [{"role": "user", "content": [
                  {"type": "input_audio", "input_audio": {"data": data_uri}}]}]},
              "parameters": {"format": fmt, "sample_rate": "16000"}},
        timeout=120)
    if r.status_code != 200:
        return f"<ASR失败 HTTP {r.status_code}: {r.text[:100]}>"
    out = r.json().get("output", {})
    return out.get("text", "")


def similarity(a, b):
    """字符级相似度（去空白后 LCS 比例），粗粒度但足够判断“指令被朗读”类事故。"""
    a, b = "".join(a.split()), "".join(b.split())
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = [0] * (n + 1)
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], 0
        for j in range(1, n + 1):
            tmp = dp[j]
            dp[j] = prev + 1 if a[i - 1] == b[j - 1] else max(dp[j], dp[j - 1])
            prev = tmp
    return 2.0 * dp[n] / (m + n)


def check_run(run_dir):
    board = json.load(open(os.path.join(run_dir, "storyboard.json")))
    ck = json.load(open(os.path.join(run_dir, "checkpoint.json")))
    lipsync_sids = {t["scene_id"] for t in ck.get("video_tasks", []) if t.get("lipsync")}
    print(f"== 配音质检: {os.path.basename(run_dir)}「{board['title']}」==\n")
    issues = []
    for sc in board["scenes"]:
        sid, line = sc["id"], sc.get("dialogue", "")
        audio = os.path.join(run_dir, f"voice_{sid}.mp3")
        if sid in lipsync_sids:
            print(f"场景{sid}: 口型镜头（台词已烧进视频音轨，ASR 质检见成片整体校验）")
            print(f"  台词: {line}\n")
            continue
        if not line:
            print(f"场景{sid}: 无台词\n")
            continue
        if not os.path.isfile(audio):
            print(f"场景{sid}: ⚠️ 缺配音文件 {os.path.basename(audio)}\n")
            issues.append(f"场景{sid} 缺配音")
            continue
        text = asr(audio)
        sim = similarity(text, line)
        flag = "✅" if sim >= 0.85 else "❌"
        print(f"场景{sid} {flag} 相似度 {sim:.0%}")
        print(f"  分镜台词: {line}")
        print(f"  ASR 识别 : {text}\n")
        if sim < 0.85:
            issues.append(f"场景{sid} 相似度 {sim:.0%}（疑似指令被朗读/幻觉/漏读）")
    if issues:
        print("== ❌ 发现问题 ==")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    print("== ✅ 全部台词质检通过 ==")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?", help="run 目录（质检全片配音）")
    ap.add_argument("--audio", help="单条音频路径（仅识别显示，不比对）")
    args = ap.parse_args()
    if args.audio:
        print(asr(args.audio))
        return
    if not args.run_dir:
        ap.print_help()
        sys.exit(2)
    check_run(args.run_dir)


if __name__ == "__main__":
    main()