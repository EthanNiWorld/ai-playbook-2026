#!/usr/bin/env python3
"""
用同一段周星驰音频，分别为 qwen-audio-3.0-tts-plus 和 cosyvoice-v3.5-plus 克隆音色，
然后用相同文本、相同风格指令做直接对比合成。
"""
import os
import sys
import json
import time
import requests
import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

# ===== 配置 =====
WORKSPACE_ID = "llm-kvw0aiysjfv4g6fh"
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY_CN")
if not dashscope.api_key:
    print("❌ 请设置 DASHSCOPE_API_KEY_CN 环境变量")
    sys.exit(1)

dashscope.base_websocket_api_url = f"wss://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
dashscope.base_http_api_url = f"https://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1"

BASE_URL = f"https://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1"
HEADERS = {
    "Authorization": f"Bearer {dashscope.api_key}",
    "Content-Type": "application/json",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "tts_compare")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 周星驰音频文件
AUDIO_FILE = os.path.join(os.path.dirname(__file__), "zhouxingchi.mp3")

# CosyVoice 已有克隆音色
COSYVOICE_VOICE_ID = "cosyvoice-v3.5-plus-zhouxingch-63a523bc3f07457a82456e5636255416"

# 测试文本
TEST_TEXTS = [
    "大家好，欢迎使用语音合成服务。今天天气真不错，适合出门散步。",
    "在人工智能快速发展的今天，大模型正在改变我们生活和工作的方式。语音合成技术作为人机交互的重要桥梁，已经在智能客服、有声读物、语音助手等场景中得到广泛应用。",
    "The quick brown fox jumps over the lazy dog. This is a test of English speech synthesis quality and naturalness.",
]

STYLE_INSTRUCTION = "温暖亲切，语速自然舒缓，带有微笑感"


def upload_to_oss(local_path: str) -> str:
    """上传到 OSS 获取公网 URL"""
    import oss2
    import uuid

    ak_id = os.getenv("oss_AccessKey_ID", "")
    ak_secret = os.getenv("oss_AccessKey_key", "")
    endpoint = os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
    bucket_name = os.getenv("OSS_BUCKET_NAME", "")
    prefix = os.getenv("OSS_UPLOAD_PREFIX", "cosyvoice-demo/")

    if not all([ak_id, ak_secret, bucket_name]):
        raise ValueError("OSS 配置不完整")

    auth = oss2.Auth(ak_id, ak_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    ext = os.path.splitext(local_path)[1] or ".mp3"
    oss_key = f"{prefix}voice-clone-{uuid.uuid4().hex[:12]}{ext}"
    bucket.put_object_from_file(oss_key, local_path)
    signed_url = bucket.sign_url('GET', oss_key, 3600)
    return signed_url


def clone_voice(target_model, audio_url, prefix):
    """为指定模型克隆音色"""
    service = VoiceEnrollmentService()
    voice_id = service.create_voice(
        target_model=target_model,
        prefix=prefix,
        url=audio_url,
    )
    rid = service.get_last_request_id()
    print(f"  ✅ 克隆请求已提交 | Request ID: {rid} | Voice ID: {voice_id}")

    # 轮询等待
    for attempt in range(1, 21):
        time.sleep(5)
        try:
            info = service.query_voice(voice_id=voice_id)
            status = info.get("status")
            if status == "OK":
                print(f"  ✅ 音色已就绪（第 {attempt} 次查询）")
                return voice_id
            elif status == "UNDEPLOYED":
                print(f"  ❌ 音色审核未通过 (UNDEPLOYED)")
                return None
            print(f"  ⏳ 状态: {status}，继续等待...")
        except Exception as e:
            print(f"  ⚠️ 查询异常: {e}")

    print(f"  ⏰ 轮询超时")
    return None


def synthesize_one(model, voice, text, instruction="", label=""):
    """合成一次"""
    synth_kwargs = {"model": model, "voice": voice}
    if instruction and instruction.strip():
        synth_kwargs["instruction"] = instruction.strip()

    t0 = time.time()
    synthesizer = SpeechSynthesizer(**synth_kwargs)
    audio_data = synthesizer.call(text)
    wall_time = time.time() - t0

    if not audio_data:
        return {"label": label, "error": "合成失败：返回空音频"}

    rid = synthesizer.get_last_request_id()
    delay = synthesizer.get_first_package_delay()

    out_path = os.path.join(OUTPUT_DIR, f"{label}.mp3")
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
    }


def main():
    results = []

    print("=" * 70)
    print("  同音色对比: qwen-audio-3.0-tts-plus vs cosyvoice-v3.5-plus")
    print("  音色来源: 同一段周星驰音频克隆")
    print("=" * 70)

    # ===== Step 1: 上传音频 =====
    print(f"\n📤 上传音频到 OSS: {AUDIO_FILE}")
    audio_url = upload_to_oss(AUDIO_FILE)
    print(f"  ✅ 上传成功")

    # ===== Step 2: 为 qwen-audio-3.0-tts-plus 克隆音色 =====
    print(f"\n🎤 为 qwen-audio-3.0-tts-plus 克隆音色...")
    qwen_voice_id = clone_voice("qwen-audio-3.0-tts-plus", audio_url, "zxqclone")

    if not qwen_voice_id:
        print("❌ qwen-audio-3.0-tts-plus 音色克隆失败，终止测试")
        sys.exit(1)

    print(f"\n  qwen-audio-3.0-tts-plus 音色: {qwen_voice_id}")
    print(f"  cosyvoice-v3.5-plus 音色:    {COSYVOICE_VOICE_ID}")

    # ===== Step 3: 对比合成 =====
    for i, text in enumerate(TEST_TEXTS):
        text_short = text[:30] + "..." if len(text) > 30 else text
        print(f"\n{'─' * 70}")
        print(f"📝 测试文本 {i + 1}: {text_short}")
        print(f"{'─' * 70}")

        # 无风格指令
        print(f"\n  [无风格指令]")
        for model, voice, name in [
            ("qwen-audio-3.0-tts-plus", qwen_voice_id, "qwen"),
            ("cosyvoice-v3.5-plus", COSYVOICE_VOICE_ID, "cosy"),
        ]:
            label = f"clone_{name}_text{i + 1}_noinst"
            print(f"    🔄 {name} 合成中...")
            try:
                r = synthesize_one(model, voice, text, "", label)
                r["model_name"] = name
                r["text_index"] = i + 1
                r["has_instruction"] = False
                results.append(r)
                if "error" in r:
                    print(f"    ❌ {r['error']}")
                else:
                    print(f"    ✅ 首包: {r['first_packet_delay_ms']}ms | "
                          f"耗时: {r['wall_time_s']}s | "
                          f"大小: {r['file_size_bytes']}B")
            except Exception as e:
                print(f"    ❌ 异常: {e}")

        # 有风格指令
        print(f"\n  [风格指令: {STYLE_INSTRUCTION}]")
        for model, voice, name in [
            ("qwen-audio-3.0-tts-plus", qwen_voice_id, "qwen"),
            ("cosyvoice-v3.5-plus", COSYVOICE_VOICE_ID, "cosy"),
        ]:
            label = f"clone_{name}_text{i + 1}_inst"
            print(f"    🔄 {name} 合成中...")
            try:
                r = synthesize_one(model, voice, text, STYLE_INSTRUCTION, label)
                r["model_name"] = name
                r["text_index"] = i + 1
                r["has_instruction"] = True
                results.append(r)
                if "error" in r:
                    print(f"    ❌ {r['error']}")
                else:
                    print(f"    ✅ 首包: {r['first_packet_delay_ms']}ms | "
                          f"耗时: {r['wall_time_s']}s | "
                          f"大小: {r['file_size_bytes']}B")
            except Exception as e:
                print(f"    ❌ 异常: {e}")

    # ===== 汇总 =====
    print("\n" + "=" * 70)
    print("  📊 同音色对比结果汇总")
    print("=" * 70)

    for i, text in enumerate(TEST_TEXTS):
        text_short = text[:30] + "..." if len(text) > 30 else text
        print(f"\n📝 文本 {i + 1}: {text_short}")
        print(f"{'model':<12} {'inst':>4} {'delay(ms)':>10} {'wall(s)':>8} {'size(B)':>8}")
        print("-" * 50)
        for r in results:
            if r.get("text_index") != i + 1:
                continue
            if "error" in r:
                print(f"  {r.get('model_name','?'):<12} ❌ {r['error']}")
                continue
            inst = "Y" if r.get("has_instruction") else "N"
            print(f"  {r['model_name']:<12} {inst:>4} {r['first_packet_delay_ms']:>10} "
                  f"{r['wall_time_s']:>8} {r['file_size_bytes']:>8}")

    # 保存结果
    json_path = os.path.join(OUTPUT_DIR, "clone_comparison_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "qwen_voice_id": qwen_voice_id,
            "cosyvoice_voice_id": COSYVOICE_VOICE_ID,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n📁 详细结果: {json_path}")
    print(f"📁 音频目录: {OUTPUT_DIR}")
    print("\n💡 重点试听对比:")
    print("  - clone_qwen_text1_noinst.mp3  vs  clone_cosy_text1_noinst.mp3")
    print("  - clone_qwen_text2_inst.mp3    vs  clone_cosy_text2_inst.mp3")
    print("  - clone_qwen_text3_noinst.mp3  vs  clone_cosy_text3_noinst.mp3")


if __name__ == "__main__":
    main()
