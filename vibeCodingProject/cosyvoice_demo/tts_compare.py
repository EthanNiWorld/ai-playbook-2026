#!/usr/bin/env python3
"""
qwen-audio-3.0-tts-plus vs cosyvoice-v3.5-plus 对比测试脚本

测试维度：
1. 相同文本、相同风格指令下两个模型的合成效果
2. 首包延迟、音频文件大小等性能指标
3. qwen-audio-3.0-tts-plus 系统音色 vs cosyvoice-v3.5-plus 自定义音色
"""
import os
import sys
import json
import time
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

# ===== 配置 =====
WORKSPACE_ID = "llm-kvw0aiysjfv4g6fh"
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY_CN")
if not dashscope.api_key:
    print("❌ 请设置 DASHSCOPE_API_KEY_CN 环境变量")
    sys.exit(1)

dashscope.base_websocket_api_url = f"wss://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "tts_compare")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== 测试文本 =====
TEST_TEXTS = [
    "大家好，欢迎使用语音合成服务。今天天气真不错，适合出门散步。",
    "在人工智能快速发展的今天，大模型正在改变我们生活和工作的方式。语音合成技术作为人机交互的重要桥梁，已经在智能客服、有声读物、语音助手等场景中得到广泛应用。",
    "The quick brown fox jumps over the lazy dog. This is a test of English speech synthesis quality and naturalness.",
]

# 风格指令
STYLE_INSTRUCTION = "温暖亲切，语速自然舒缓，带有微笑感"

# ===== qwen-audio-3.0-tts-plus 系统音色 =====
QWEN_VOICES = [
    {"voice": "longanlingxin", "desc": "龙安灵心（知心温暖音，25岁，中文/英文）"},
    {"voice": "longanlufeng", "desc": "龙安鲁风（明亮开朗音，25岁，中文/英文）"},
]

# ===== cosyvoice-v3.5-plus 自定义音色（从 voices.json 读取） =====
VOICES_FILE = os.path.join(os.path.dirname(__file__), "output", "voices.json")
COSYVOICE_VOICE_ID = None
if os.path.exists(VOICES_FILE):
    with open(VOICES_FILE, "r", encoding="utf-8") as f:
        voices = json.load(f)
    # 优先使用声音设计的音色
    for v in voices:
        if v.get("source") == "design":
            COSYVOICE_VOICE_ID = v["voice_id"]
            break
    if not COSYVOICE_VOICE_ID and voices:
        COSYVOICE_VOICE_ID = voices[0]["voice_id"]


def synthesize_one(model, voice, text, instruction="", label=""):
    """调用 TTS 合成一次，返回指标和文件路径"""
    synth_kwargs = {"model": model, "voice": voice}
    if instruction and instruction.strip():
        synth_kwargs["instruction"] = instruction.strip()

    t0 = time.time()
    synthesizer = SpeechSynthesizer(**synth_kwargs)
    audio_data = synthesizer.call(text)
    wall_time = time.time() - t0

    if not audio_data:
        return {
            "label": label,
            "model": model,
            "voice": voice,
            "error": "合成失败：返回空音频",
        }

    rid = synthesizer.get_last_request_id()
    delay = synthesizer.get_first_package_delay()

    # 保存音频
    safe_label = label.replace(" ", "_").replace("/", "_")
    out_path = os.path.join(OUTPUT_DIR, f"{safe_label}.mp3")
    with open(out_path, "wb") as f:
        f.write(audio_data)

    return {
        "label": label,
        "model": model,
        "voice": voice,
        "request_id": rid,
        "first_packet_delay_ms": round(delay, 2),
        "wall_time_s": round(wall_time, 2),
        "file_size_bytes": len(audio_data),
        "audio_file": out_path,
        "instruction": instruction or None,
    }


def main():
    results = []

    print("=" * 70)
    print("  qwen-audio-3.0-tts-plus  vs  cosyvoice-v3.5-plus  对比测试")
    print("=" * 70)

    for i, text in enumerate(TEST_TEXTS):
        text_short = text[:30] + "..." if len(text) > 30 else text
        print(f"\n{'─' * 70}")
        print(f"📝 测试文本 {i + 1}: {text_short}")
        print(f"{'─' * 70}")

        # --- 无风格指令 ---
        print(f"\n  [无风格指令]")

        # qwen-audio-3.0-tts-plus 各音色
        for v in QWEN_VOICES:
            label = f"qwen-audio-plus_{v['voice']}_text{i + 1}_noinst"
            print(f"    🔄 合成中: {v['desc']} ...")
            try:
                r = synthesize_one("qwen-audio-3.0-tts-plus", v["voice"], text, "", label)
                r["voice_desc"] = v["desc"]
                r["text_index"] = i + 1
                r["has_instruction"] = False
                results.append(r)
                if "error" in r:
                    print(f"    ❌ {r['error']}")
                else:
                    print(f"    ✅ 首包延迟: {r['first_packet_delay_ms']}ms | "
                          f"耗时: {r['wall_time_s']}s | "
                          f"大小: {r['file_size_bytes']} bytes")
            except Exception as e:
                print(f"    ❌ 异常: {e}")
                results.append({"label": label, "error": str(e)})

        # cosyvoice-v3.5-plus
        if COSYVOICE_VOICE_ID:
            label = f"cosyvoice-plus_custom_text{i + 1}_noinst"
            print(f"    🔄 合成中: cosyvoice-v3.5-plus (自定义音色) ...")
            try:
                r = synthesize_one("cosyvoice-v3.5-plus", COSYVOICE_VOICE_ID, text, "", label)
                r["voice_desc"] = "自定义音色（声音设计）"
                r["text_index"] = i + 1
                r["has_instruction"] = False
                results.append(r)
                if "error" in r:
                    print(f"    ❌ {r['error']}")
                else:
                    print(f"    ✅ 首包延迟: {r['first_packet_delay_ms']}ms | "
                          f"耗时: {r['wall_time_s']}s | "
                          f"大小: {r['file_size_bytes']} bytes")
            except Exception as e:
                print(f"    ❌ 异常: {e}")
                results.append({"label": label, "error": str(e)})

        # --- 有风格指令 ---
        print(f"\n  [风格指令: {STYLE_INSTRUCTION}]")

        # qwen-audio-3.0-tts-plus 第一个音色
        v = QWEN_VOICES[0]
        label = f"qwen-audio-plus_{v['voice']}_text{i + 1}_inst"
        print(f"    🔄 合成中: {v['desc']} (带指令) ...")
        try:
            r = synthesize_one("qwen-audio-3.0-tts-plus", v["voice"], text, STYLE_INSTRUCTION, label)
            r["voice_desc"] = v["desc"]
            r["text_index"] = i + 1
            r["has_instruction"] = True
            results.append(r)
            if "error" in r:
                print(f"    ❌ {r['error']}")
            else:
                print(f"    ✅ 首包延迟: {r['first_packet_delay_ms']}ms | "
                      f"耗时: {r['wall_time_s']}s | "
                      f"大小: {r['file_size_bytes']} bytes")
        except Exception as e:
            print(f"    ❌ 异常: {e}")
            results.append({"label": label, "error": str(e)})

        # cosyvoice-v3.5-plus
        if COSYVOICE_VOICE_ID:
            label = f"cosyvoice-plus_custom_text{i + 1}_inst"
            print(f"    🔄 合成中: cosyvoice-v3.5-plus (自定义音色, 带指令) ...")
            try:
                r = synthesize_one("cosyvoice-v3.5-plus", COSYVOICE_VOICE_ID, text, STYLE_INSTRUCTION, label)
                r["voice_desc"] = "自定义音色（声音设计）"
                r["text_index"] = i + 1
                r["has_instruction"] = True
                results.append(r)
                if "error" in r:
                    print(f"    ❌ {r['error']}")
                else:
                    print(f"    ✅ 首包延迟: {r['first_packet_delay_ms']}ms | "
                          f"耗时: {r['wall_time_s']}s | "
                          f"大小: {r['file_size_bytes']} bytes")
            except Exception as e:
                print(f"    ❌ 异常: {e}")
                results.append({"label": label, "error": str(e)})

    # ===== 汇总输出 =====
    print("\n" + "=" * 70)
    print("  📊 对比结果汇总")
    print("=" * 70)

    # 按文本分组打印
    for i, text in enumerate(TEST_TEXTS):
        text_short = text[:30] + "..." if len(text) > 30 else text
        print(f"\n📝 文本 {i + 1}: {text_short}")
        print(f"{'label':<45} {'model':<25} {'delay(ms)':>10} {'wall(s)':>8} {'size(B)':>8} inst")
        print("-" * 105)
        for r in results:
            if r.get("text_index") != i + 1:
                continue
            if "error" in r:
                print(f"  {r['label']:<43} ❌ {r['error']}")
                continue
            inst = "Y" if r.get("has_instruction") else "N"
            print(f"  {r['label']:<45} {r['model']:<25} {r['first_packet_delay_ms']:>10} "
                  f"{r['wall_time_s']:>8} {r['file_size_bytes']:>8}    {inst}")

    # 保存 JSON 结果
    json_path = os.path.join(OUTPUT_DIR, "comparison_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📁 详细结果已保存: {json_path}")
    print(f"📁 音频文件目录: {OUTPUT_DIR}")
    print("\n💡 请逐个试听 output/tts_compare/ 目录下的 mp3 文件，对比两个模型的音质、自然度和情感表现力。")


if __name__ == "__main__":
    main()
