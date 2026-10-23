#!/usr/bin/env python3
"""
qwen-audio-3.1-tts-flash / plus / next 新加坡节点（国际站）对比测试

测试目标：
1. 验证三个模型在新加坡节点（ap-southeast-1）的可用性与计费口径
2. 同一段带情绪/动作提示的台词，在三种提示写法下的表现差异
   - raw       : 原文，保留中文括号提示（如「（狂笑）」「（停顿，深吸一口气）」「（哭腔）」）
   - tags      : 改写为官方英文方括号标签（[laughing] [gasp] [crying]）
   - delivery  : raw 去括号后 + instruction / text_prompt 描述表演方式
3. 流式首包延迟（SSE，X-DashScope-SSE: enable）：flash / plus 各跑一次，
   记录首个事件与首个非空音频块到达时刻，用于验证「实时交互」定位
   （非流式只测得到端到端，会低估 flash 的实时优势）
4. 采集端到端耗时、音频大小、时长等基础指标

API 说明：
- flash / plus：Qwen-Audio-TTS HTTP API（input.text + input.voice，支持 instruction）
- next       ：Audio generation API（input.text_prompt，无 voice 参数，可按 references 传参考音频）
- 两者共用同一端点：POST https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer

用法：
    python3 test_qwen_audio_31_tts_sgp.py
    python3 test_qwen_audio_31_tts_sgp.py --model qwen-audio-3.1-tts-next   # 只跑指定模型
    python3 test_qwen_audio_31_tts_sgp.py --no-stream                       # 跳过流式首包测试
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../.."))
ENV_PATH = os.path.join(REPO_ROOT, ".env")

# ===== 台词（用户指定原文，保留中文括号表演提示）=====
ORIGINAL_TEXT = (
    "（狂笑）哈哈哈哈！曾经有一份真诚的爱情放在我面前，我没有珍惜，等我失去的时候我才后悔莫及，"
    "人世间最痛苦的事莫过于此。（停顿，深吸一口气，转为深情/哭腔）如果上天能够给我一个再来一次的机会，"
    "我会对那个女孩子说三个字：我爱你。如果非要在这份爱上加个期限，我希望是……一万年。"
)

# ===== 三种提示写法 =====
# 1) raw：原样提交，观察模型能否自行理解中文括号内的表演提示
TEXT_RAW = ORIGINAL_TEXT

# 2) tags：按官方「Emotion and nonverbal tags」文档改写为英文方括号标签
TEXT_TAGS = (
    "[laughing]哈哈哈哈！曾经有一份真诚的爱情放在我面前，我没有珍惜，等我失去的时候我才后悔莫及，"
    "人世间最痛苦的事莫过于此。[gasp][crying]如果上天能够给我一个再来一次的机会，"
    "我会对那个女孩子说三个字：我爱你。如果非要在这份爱上加个期限，我希望是……一万年。"
)

# 3) delivery：去掉括号提示的纯台词，表演方式改由 instruction / text_prompt 描述
TEXT_CLEAN = re.sub(r"[（(][^）)]*[）)]", "", ORIGINAL_TEXT)

INSTRUCTION_DELIVERY = (
    "开头先用一阵狂笑开场，笑中带苦；到「人世间最痛苦的事莫过于此」后停顿，深吸一口气，"
    "转为深情而带哭腔的告白，结尾「一万年」语速放慢、情绪拉满。"
)

# next 模型没有 voice / instruction 参数，表演方式需写进 text_prompt
NEXT_PROMPT_PREFIX = (
    "一位年轻女性独白，情绪层次分明：开头先狂笑（带苦涩），随后停顿、深吸一口气，"
    "转为深情且带哭腔的告白，结尾「一万年」放慢语速、情绪饱满。台词如下："
)
NEXT_PROMPT_RAW = NEXT_PROMPT_PREFIX + ORIGINAL_TEXT
NEXT_PROMPT_TAGS = (
    "一位年轻女性独白，按标签切换情绪：[laughing]开头狂笑；[gasp][crying]转为哭腔深情告白。台词如下：" + TEXT_TAGS
)
NEXT_PROMPT_CLEAN = NEXT_PROMPT_PREFIX + TEXT_CLEAN

# ===== 模型与音色配置 =====
# 音色必须与模型严格匹配（跨模型混用会报 InvalidParameter）
TTS_MODELS = [
    {
        "model": "qwen-audio-3.1-tts-flash",
        "voices": [
            {"voice": "longanhuan_v3.1", "desc": "龙安欢_v3.1（女声，多语种/方言音色组）"},
            {"voice": "xunanchuan_v3.1", "desc": "徐南川_v3.1（男声，多语种/方言音色组）"},
        ],
    },
    {
        "model": "qwen-audio-3.1-tts-plus",
        "voices": [
            {"voice": "longanlingxin_v3.1", "desc": "龙安灵心_v3.1（女声，plus 旗舰音色）"},
            {"voice": "xunanchuan_v3.1", "desc": "徐南川_v3.1（男声，plus 旗舰音色）"},
        ],
    },
]

NEXT_MODEL = "qwen-audio-3.1-tts-next"

FORMAT = "mp3"
SAMPLE_RATE = 24000


def load_env(path):
    """轻量 .env 解析（避免额外依赖 python-dotenv）"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def resolve_singapore_endpoint():
    """从 .env 的工作空间域名推导新加坡端点，避免硬编码 WorkspaceId"""
    workspace_id = os.getenv("SG_WORKSPACE_ID")
    if not workspace_id:
        for env_name in ("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "DASHSCOPE_API_KEY_SGP_URL"):
            url = os.getenv(env_name, "")
            m = re.match(r"https?://([a-zA-Z0-9-]+)\.ap-southeast-1\.maas\.aliyuncs\.com", url)
            if m:
                workspace_id = m.group(1)
                break
    if not workspace_id:
        print("❌ 未找到新加坡 WorkspaceId：请在 .env 配置 DASHSCOPE_API_KEY_INTL_SG_TEST_URL 或 SG_WORKSPACE_ID")
        sys.exit(1)
    return f"https://{workspace_id}.ap-southeast-1.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"


def resolve_api_key():
    for env_name in ("DASHSCOPE_API_KEY_SGP", "DASHSCOPE_API_KEY_INTL_SG_TEST"):
        value = os.getenv(env_name)
        if value:
            return value, env_name
    print("❌ 未找到新加坡 API Key：请在 .env 配置 DASHSCOPE_API_KEY_SGP")
    sys.exit(1)


def probe_duration(path):
    """读取音频时长（优先 afinfo，其次 ffprobe），失败返回 None"""
    try:
        out = subprocess.run(["afinfo", path], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"estimated duration:\s*([\d.]+)\s*sec", out)
        if m:
            return round(float(m.group(1)), 2)
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=10,
        ).stdout
        if out.strip():
            return round(float(out.strip()), 2)
    except Exception:
        pass
    return None


def call_tts(endpoint, api_key, payload, out_path):
    """提交一次合成请求并下载音频，返回指标字典"""
    record = {
        "model": payload["model"],
        "mode": "http",
        "request": payload,
        "http_status": None,
        "request_id": None,
        "usage": None,
        "latency_s": None,
        "download_s": None,
        "file_size_bytes": None,
        "audio_duration_s": None,
        "audio_file": None,
        "error": None,
    }
    t0 = time.time()
    try:
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=300,
        )
        record["http_status"] = resp.status_code
        body = resp.json()
        record["request_id"] = body.get("request_id")
        record["usage"] = body.get("usage")
        if resp.status_code != 200:
            record["error"] = body.get("message") or body.get("code") or resp.text[:300]
            record["latency_s"] = round(time.time() - t0, 2)
            return record

        audio_url = body["output"]["audio"]["url"]
        record["latency_s"] = round(time.time() - t0, 2)
        record["reported_duration_s"] = body["output"]["audio"].get("duration")

        t1 = time.time()
        audio_resp = requests.get(audio_url, timeout=120)
        audio_resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(audio_resp.content)
        record["download_s"] = round(time.time() - t1, 2)
        record["file_size_bytes"] = len(audio_resp.content)
        record["audio_file"] = out_path
        record["audio_duration_s"] = probe_duration(out_path) or record.get("reported_duration_s")
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        record["latency_s"] = round(time.time() - t0, 2)
    return record


def call_tts_stream(endpoint, api_key, payload, out_path):
    """SSE 流式合成（X-DashScope-SSE: enable）

    记录首个事件、首个非空音频块（即真正可播放的首包）与完成时间，
    用于验证 flash 的「实时交互」定位；非流式只测得到端到端，会低估实时优势。
    """
    record = {
        "model": payload["model"],
        "mode": "sse",
        "request": payload,
        "http_status": None,
        "request_id": None,
        "usage": None,
        "ttfb_event_s": None,
        "ttfb_audio_s": None,
        "latency_s": None,
        "chunks": 0,
        "downloaded_full": False,
        "file_size_bytes": None,
        "audio_duration_s": None,
        "audio_file": None,
        "error": None,
    }
    t0 = time.time()
    audio_chunks = []
    try:
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-SSE": "enable",
            },
            json=payload,
            stream=True,
            timeout=300,
        )
        record["http_status"] = resp.status_code
        if resp.status_code != 200:
            record["error"] = resp.text[:300]
            record["latency_s"] = round(time.time() - t0, 3)
            return record

        buf = []
        final_url = None
        for raw in resp.iter_lines(decode_unicode=False):
            if raw is None:
                continue
            line = raw.decode("utf-8", "ignore")
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                # 一个 SSE 事件可能带多行 data:，先缓存，遇空行再合并解析
                buf.append(line[5:].strip())
                continue
            if line.strip() or not buf:
                continue
            obj = json.loads("\n".join(buf))
            buf = []
            if record["ttfb_event_s"] is None:
                record["ttfb_event_s"] = round(time.time() - t0, 3)
            record["request_id"] = record["request_id"] or obj.get("request_id")
            out = obj.get("output") or {}
            data = (out.get("audio") or {}).get("data") or ""
            if data:
                audio_chunks.append(base64.b64decode(data))
                record["chunks"] += 1
                if record["ttfb_audio_s"] is None:
                    record["ttfb_audio_s"] = round(time.time() - t0, 3)
            if out.get("finish_reason") == "stop":
                final_url = (out.get("audio") or {}).get("url")
                record["usage"] = obj.get("usage")
                record["latency_s"] = round(time.time() - t0, 3)
                break

        if record["latency_s"] is None:
            record["latency_s"] = round(time.time() - t0, 3)

        # 优先取最终完整文件（避免分片拼接的容器头问题），失败则用已收分片
        audio_bytes = b"".join(audio_chunks)
        if final_url:
            try:
                full = requests.get(final_url, timeout=120)
                full.raise_for_status()
                audio_bytes = full.content
                record["downloaded_full"] = True
            except Exception:
                pass
        if not audio_bytes:
            record["error"] = "流式未返回音频数据"
            return record
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        record["file_size_bytes"] = len(audio_bytes)
        record["audio_file"] = out_path
        record["audio_duration_s"] = probe_duration(out_path)
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        record["latency_s"] = round(time.time() - t0, 3)
    return record


def build_variants():
    """TTS（flash / plus）：同台词三种写法"""
    return [
        {"variant": "raw", "text": TEXT_RAW, "instruction": None,
         "note": "原文提交，保留中文括号表演提示"},
        {"variant": "tags", "text": TEXT_TAGS, "instruction": None,
         "note": "中文括号改写为官方英文标签 [laughing]/[gasp]/[crying]"},
        {"variant": "delivery", "text": TEXT_CLEAN, "instruction": INSTRUCTION_DELIVERY,
         "note": "纯台词 + instruction 描述表演层次"},
    ]


def build_next_variants():
    """next：表演提示写在 text_prompt 里"""
    return [
        {"variant": "raw", "prompt": NEXT_PROMPT_RAW,
         "note": "描述 + 原文（保留中文括号提示）"},
        {"variant": "tags", "prompt": NEXT_PROMPT_TAGS,
         "note": "描述 + 英文方括号标签"},
        {"variant": "delivery", "prompt": NEXT_PROMPT_CLEAN,
         "note": "描述中写明表演层次 + 纯台词"},
    ]


def print_record(tag, r):
    if r["error"]:
        print(f"    ❌ {tag} | HTTP {r['http_status']} | {r['error'][:160]}")
        return
    print(f"    ✅ {tag} | 请求 {r['latency_s']}s | 下载 {r['download_s']}s | "
          f"{r['file_size_bytes']} bytes | 时长 {r['audio_duration_s']}s | "
          f"request_id={r['request_id']}")


def model_stats(results):
    """按模型聚合延迟 / 时长，并标出异常（实际时长显著超过接口上报时长）"""
    stats = {}
    for r in results:
        if r["error"] or r.get("mode") == "sse":
            continue
        s = stats.setdefault(r["model"], {"latency": [], "duration": [], "anomaly": []})
        s["latency"].append(r["latency_s"])
        if r["audio_duration_s"]:
            s["duration"].append(r["audio_duration_s"])
        reported = r.get("reported_duration_s")
        actual = r["audio_duration_s"]
        if reported and actual and actual > reported * 1.3:
            s["anomaly"].append(f"{r['variant']}（上报 {reported}s / 实际 {actual}s）")
    return stats


def write_markdown(results, md_path, out_dir, endpoint, key_env, started_at):
    lines = [
        "# Qwen-Audio-3.1-TTS 三模型新加坡节点实测报告",
        "",
        f"- 测试时间：{started_at}",
        f"- 地域/端点：新加坡（ap-southeast-1）`{endpoint}`",
        f"- 凭证环境变量：`{key_env}`",
        f"- 输出格式：{FORMAT} / {SAMPLE_RATE}Hz",
        "",
        "## 测试台词",
        "",
        f"> {ORIGINAL_TEXT}",
        "",
        "## 三种提示写法",
        "",
        "| 写法 | 说明 |",
        "|------|------|",
        "| raw | 原文提交，保留中文括号表演提示「（狂笑）」「（停顿，深吸一口气，转为深情/哭腔）」 |",
        "| tags | 改写为官方英文方括号标签 `[laughing]` `[gasp]` `[crying]` |",
        "| delivery | 去掉括号的纯台词 + `instruction`（flash/plus）/ prompt 描述（next） |",
        "",
        "## 实测结果",
        "",
        "| 模型 | 变体 | 音色 | 状态 | 请求耗时(s) | 文件大小(KB) | 音频时长(s) | 计费用量 | 音频文件 |",
        "|------|------|------|------|------------:|-------------:|------------:|----------|----------|",
    ]
    for r in results:
        if r.get("mode") == "sse":
            continue
        usage = r.get("usage") or {}
        if usage.get("total_tokens") is not None:
            usage_str = f"{usage['total_tokens']} tokens"
        elif usage.get("characters") is not None:
            usage_str = f"{usage['characters']} 字符"
        elif usage.get("duration") is not None:
            usage_str = f"{usage['duration']} 秒"
        else:
            usage_str = "-"
        status = "✅ 200" if not r["error"] else f"❌ {r['http_status'] or 'ERR'}"
        size = f"{r['file_size_bytes'] / 1024:.1f}" if r["file_size_bytes"] else "-"
        audio_name = os.path.basename(r["audio_file"]) if r["audio_file"] else "-"
        lines.append(
            f"| `{r['model']}` | {r['variant']} | {r.get('voice') or '—（无 voice 参数）'} | {status} | "
            f"{r['latency_s'] if r['latency_s'] is not None else '-'} | {size} | "
            f"{r['audio_duration_s'] or '-'} | {usage_str} | {audio_name} |"
        )

    lines += ["", "## 指标观察", ""]
    for model, s in model_stats(results).items():
        lat = s["latency"]
        dur = s["duration"]
        lines.append(
            f"- `{model}`：请求耗时 {min(lat)}~{max(lat)}s（均值 {sum(lat) / len(lat):.2f}s）；"
            f"音频时长 {min(dur) if dur else '-'}~{max(dur) if dur else '-'}s"
            + (f"；时长异常：{'、'.join(s['anomaly'])}" if s["anomaly"] else "")
        )

    streams = [r for r in results if r.get("mode") == "sse"]
    if streams:
        lines += [
            "",
            "## 流式首包延迟（SSE）",
            "",
            "> 与非流式 `raw` 同音色、同台词对比；首包 = 首个非空 `output.audio.data` 到达时刻（含网络往返）。非流式端到端 = 请求耗时 + 下载耗时。",
            "",
            "| 模型 | 音色 | 首个事件(s) | 首个音频块(s) | 完成(s) | 音频块数 | 非流式端到端(s) | 首包提速 |",
            "|------|------|------------:|--------------:|--------:|---------:|----------------:|---------:|",
        ]
        for r in streams:
            base = next(
                (x for x in results
                 if x.get("mode") != "sse" and x["model"] == r["model"] and not x["error"]
                 and x.get("variant") == "raw" and x.get("voice") == r.get("voice")),
                None,
            )
            e2e = None
            if base:
                e2e = round((base.get("latency_s") or 0) + (base.get("download_s") or 0), 2)
            speed = f"{e2e / r['ttfb_audio_s']:.1f}x" if e2e and r.get("ttfb_audio_s") else "-"
            status = "✅" if not r["error"] else "❌"
            lines.append(
                f"| `{r['model']}` | {r.get('voice') or '-'} | {r.get('ttfb_event_s') or '-'} | "
                f"{r.get('ttfb_audio_s') or '-'} | {r.get('latency_s') or '-'} | {r.get('chunks') or '-'} | "
                f"{e2e or '-'} | {status} {speed} |"
            )

    failed = [r for r in results if r["error"]]
    if failed:
        lines += ["", "## 失败明细", ""]
        for r in failed:
            lines.append(f"- `{r['model']}` / {r['variant']}：HTTP {r['http_status']} — {r['error']}")

    lines += [
        "",
        f"> 音频文件位于 `{os.path.relpath(out_dir, SCRIPT_DIR)}/`（运行时产物，已加入 .gitignore，不入库），明细见同目录 `results.json`。",
        "> flash / plus 按输入+输出 tokens 计费（usage 中同时返回 characters）；next 按音频时长对应的 tokens 计费。",
        "",
        "## 试听建议",
        "",
        "1. 先对比 `flash` 与 `plus` 同音色同写法的文件，判断音质与情感细腻度差异；",
        "2. 再对比同一模型的 `raw` / `tags` / `delivery`，判断哪种写法最能让模型「演出」狂笑、吸气与哭腔；",
        "3. `next` 是 AudioGen 模型，输出为一段完整音频表演（可含环境音/音效），与纯 TTS 的 flash/plus 不属同一任务范式，横向对比时以「表演完整度」为主要观感维度。",
        "",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="只跑指定模型（默认全部）")
    parser.add_argument("--no-stream", action="store_true", help="跳过 SSE 流式首包延迟测试")
    args = parser.parse_args()

    load_env(ENV_PATH)
    endpoint = resolve_singapore_endpoint()
    api_key, key_env = resolve_api_key()

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_dir = os.path.join(SCRIPT_DIR, "output", f"tts_qwen_audio_31_sgp_{datetime.now():%Y%m%d_%H%M%S}")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(
        SCRIPT_DIR, f"test_qwen_audio_31_tts_sgp_results_{datetime.now():%Y%m%d}.md"
    )

    print("=" * 78)
    print("  Qwen-Audio-3.1-TTS 新加坡节点实测：flash / plus / next")
    print("=" * 78)
    print(f"  端点: {endpoint}")
    print(f"  凭证: {key_env}")
    print(f"  产物: {out_dir}")

    results = []

    # -------- flash / plus：HTTP TTS API --------
    for cfg in TTS_MODELS:
        model = cfg["model"]
        if args.model and args.model != model:
            continue
        print(f"\n{'─' * 78}\n🎙  {model}")
        for v in cfg["voices"]:
            for variant in build_variants():
                payload = {
                    "model": model,
                    "input": {
                        "text": variant["text"],
                        "voice": v["voice"],
                        "format": FORMAT,
                        "sample_rate": SAMPLE_RATE,
                    },
                }
                if variant["instruction"]:
                    payload["input"]["instruction"] = variant["instruction"]

                short = model
                out_path = os.path.join(out_dir, f"{short}_{v['voice']}_{variant['variant']}.mp3")
                print(f"  🔄 {v['desc']} / {variant['variant']} ({variant['note']})")
                r = call_tts(endpoint, api_key, payload, out_path)
                r.update({"variant": variant["variant"], "variant_note": variant["note"],
                          "voice": v["voice"], "voice_desc": v["desc"]})
                results.append(r)
                print_record(f"{v['voice']}/{variant['variant']}", r)

    # -------- next：Audio generation API --------
    if not args.model or args.model == NEXT_MODEL:
        print(f"\n{'─' * 78}\n🎬  {NEXT_MODEL}（AudioGen：text_prompt）")
        for variant in build_next_variants():
            payload = {
                "model": NEXT_MODEL,
                "input": {
                    "text_prompt": variant["prompt"],
                    "format": FORMAT,
                    "sample_rate": SAMPLE_RATE,
                    "channels": 1,
                },
            }
            out_path = os.path.join(out_dir, f"{NEXT_MODEL}_{variant['variant']}.mp3")
            print(f"  🔄 {variant['variant']} ({variant['note']})，最长耗时约 120s，请稍候……")
            r = call_tts(endpoint, api_key, payload, out_path)
            r.update({"variant": variant["variant"], "variant_note": variant["note"],
                      "voice": None, "voice_desc": "—（无 voice 参数）"})
            results.append(r)
            print_record(f"next/{variant['variant']}", r)

    # -------- 流式首包延迟（SSE）：验证 flash / plus 的实时性定位 --------
    if not args.no_stream:
        print(f"\n{'─' * 78}\n⚡ 流式首包延迟（X-DashScope-SSE: enable）")
        for cfg in TTS_MODELS:
            model = cfg["model"]
            if args.model and args.model != model:
                continue
            v = cfg["voices"][0]
            payload = {
                "model": model,
                "input": {
                    "text": TEXT_RAW,
                    "voice": v["voice"],
                    "format": FORMAT,
                    "sample_rate": SAMPLE_RATE,
                },
            }
            out_path = os.path.join(out_dir, f"{model}_{v['voice']}_stream.mp3")
            print(f"  🔄 {model} / {v['voice']} / 流式（与非流式 raw 同参数）")
            r = call_tts_stream(endpoint, api_key, payload, out_path)
            r.update({"variant": "stream", "voice": v["voice"], "voice_desc": v["desc"],
                      "variant_note": "SSE 流式，与非流式 raw 同参数"})
            results.append(r)
            if r["error"]:
                print(f"    ❌ 首个事件 {r['ttfb_event_s']}s | {r['error'][:160]}")
            else:
                print(f"    ✅ 首个事件 {r['ttfb_event_s']}s | 首个音频块 {r['ttfb_audio_s']}s | "
                      f"完成 {r['latency_s']}s | {r['chunks']} 块 | {r['file_size_bytes']} bytes")

    # -------- 汇总 --------
    print("\n" + "=" * 78)
    print("  📊 汇总")
    print("=" * 78)
    print(f"  {'模型':<26}{'变体':<10}{'音色':<18}{'耗时':>7}{'大小KB':>8}{'时长s':>7}  状态")
    print("  " + "-" * 84)
    for r in results:
        if r.get("mode") == "sse":
            continue
        status = "OK" if not r["error"] else "FAIL"
        size = f"{r['file_size_bytes'] / 1024:.1f}" if r["file_size_bytes"] else "-"
        print(f"  {r['model']:<26}{r['variant']:<10}{(r.get('voice') or 'next'):<18}"
              f"{str(r['latency_s']):>7}{size:>8}{str(r['audio_duration_s'] or '-'):>7}  {status}")

    streams = [r for r in results if r.get("mode") == "sse"]
    if streams:
        print(f"\n  {'流式模型':<26}{'首个事件s':>10}{'首个音频块s':>12}{'完成s':>8}{'块数':>6}  状态")
        print("  " + "-" * 74)
        for r in streams:
            status = "OK" if not r["error"] else "FAIL"
            print(f"  {r['model']:<26}{str(r['ttfb_event_s']):>10}{str(r['ttfb_audio_s']):>12}"
                  f"{str(r['latency_s']):>8}{str(r['chunks']):>6}  {status}")

    json_path = os.path.join(out_dir, "results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    md_path = write_markdown(results, report_path, out_dir, endpoint, key_env, started_at)

    ok = sum(1 for r in results if not r["error"])
    print(f"\n  ✅ 成功 {ok}/{len(results)}")
    print(f"  📁 音频目录: {out_dir}")
    print(f"  📄 明细 JSON: {json_path}")
    print(f"  📄 测试报告: {md_path}")


if __name__ == "__main__":
    main()
