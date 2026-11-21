"""声音复刻实测：real_testwan.m4a → qwen-audio-3.1-tts-plus 克隆音色 → 合成验证。

官方协议（voice-cloning-user-guide）：
① POST /services/audio/tts/customization {model: voice-enrollment,
   input: {action: create_voice, target_model, prefix, audio: <URL|Base64 Data URI>}}
② 轮询 query_voice 直到 status=OK
③ 用返回的 voice_id 走普通 SpeechSynthesizer 合成（同 target_model）
创建免费，合成按目标模型计费。prefix 仅字母数字 ≤10 字符。

运行：.venv/bin/python -u scripts/test_voice_clone.py [音频路径]
"""
import base64
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

TARGET_MODEL = "qwen-audio-3.1-tts-plus"
# prefix 仅字母数字 ≤10 字符；可被环境变量覆盖（多角色多音色场景各自命名）
PREFIX = os.environ.get("VOICE_PREFIX", "testwan")
PROBE_TEXT = os.environ.get("VOICE_PROBE_TEXT", "这房子，从第一块砖起，就是我说了算。")


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "org_file", "real_testwan.m4a")
    base = config.NATIVE_BASE_URL.rstrip("/")
    headers = {"Authorization": f"Bearer {config.API_KEY}"}

    with open(audio_path, "rb") as f:
        data_uri = "data:audio/mp4;base64," + base64.b64encode(f.read()).decode()
    print(f"样本: {os.path.basename(audio_path)} ({os.path.getsize(audio_path) / 1024:.0f} KB)")

    # ① 创建音色
    r = requests.post(f"{base}/services/audio/tts/customization", headers=headers,
                      json={"model": "voice-enrollment",
                            "input": {"action": "create_voice",
                                      "target_model": TARGET_MODEL,
                                      "prefix": PREFIX,
                                      "audio": data_uri}}, timeout=60)
    print(f"① create_voice HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:400])
        sys.exit(1)
    voice_id = r.json()["output"]["voice_id"]
    print(f"   voice_id: {voice_id}")

    # ② 轮询就绪
    for i in range(60):
        q = requests.post(f"{base}/services/audio/tts/customization", headers=headers,
                          json={"model": "voice-enrollment",
                                "input": {"action": "query_voice", "voice_id": voice_id}},
                          timeout=60)
        status = q.json().get("output", {}).get("status", "UNKNOWN")
        if i % 5 == 0:
            print(f"   [{i}s] status={status}")
        if status == "OK":
            break
        if status not in ("DEPLOYING", "PENDING"):
            print(q.text[:400])
            sys.exit(1)
        time.sleep(1)
    else:
        print("⚠️ 音色部署超时（voice_id 已保存，可稍后重查）")
        print(f"VOICE_ID={voice_id}")
        sys.exit(2)
    print(f"② 音色部署完成: {voice_id}")

    # ③ 克隆音色合成一句验证
    s = requests.post(f"{base}/services/audio/tts/SpeechSynthesizer", headers=headers,
                      json={"model": TARGET_MODEL,
                            "input": {"text": PROBE_TEXT,
                                      "voice": voice_id, "format": "mp3"}}, timeout=120)
    print(f"③ 合成 HTTP {s.status_code}")
    if s.status_code != 200:
        print(s.text[:400])
        sys.exit(1)
    url = s.json()["output"]["audio"]["url"]
    out = os.path.join(os.path.dirname(audio_path), "clone_probe.mp3")
    audio = requests.get(url, timeout=60)
    audio.raise_for_status()
    with open(out, "wb") as f:
        f.write(audio.content)
    print(f"✅ 克隆音色合成验证通过: {out}（{len(audio.content) / 1024:.0f} KB）")
    print(f"VOICE_ID={voice_id}")


if __name__ == "__main__":
    main()