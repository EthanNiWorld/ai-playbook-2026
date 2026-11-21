"""口型同步镜头端到端实测（l5）：wan2.7-i2v + first_frame + driving_audio。

复用 run_009 场景2镜头3（近景）剧照 URL + voice_2.mp3 台词：
重新 TTS 拿公网签名 URL（uploads 两步上传的 oss:// 已实测被拒，driving_audio
仅接受公网 HTTP(S)）→ lipsync2video 提交 → 轮询 → 下载 lipsync_probe.mp4。

运行：.venv/bin/python -u scripts/test_lipsync_e2e.py [run目录]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from bailian_client import BailianAsyncClient  # noqa: E402
from make_dubbed_final import synth, MOOD_CYCLE  # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    config.OUTPUT_DIR, "run_009_20261120_210920")


def main():
    ckpt = json.load(open(os.path.join(RUN, "checkpoint.json")))
    still_url = next(i["url"] for i in ckpt["images"]["stills"]
                     if i["local"] == "scene_2_shot3_still.png")
    print(f"首帧: {still_url[:80]}…")
    gen = BailianAsyncClient()
    line = json.load(open(os.path.join(RUN, "storyboard.json")))["scenes"][1]["dialogue"]
    audio_url = synth(line, MOOD_CYCLE[1], os.path.join(RUN, "voice_2.mp3"))
    print(f"音轨: {audio_url[:100]}…")

    prompt = ("固定近景浅景深，男子面对镜头轻声说话，口型与台词音频逐字同步，"
              "说完后抬眼望向远方，嘴角慢慢浮现释然微笑，晚风吹动发丝")
    task_id, model = gen.lipsync2video(
        prompt, still_url, audio_url,
        ["wan2.7-i2v", "wan2.7-i2v-2026-06-12"],
        resolution="720P", duration=8)
    print(f"✅ 已提交: {task_id}（{model}）")

    t0 = time.time()
    while time.time() - t0 < 1500:
        info = gen.query_task(task_id)
        status = info.get("output", {}).get("task_status", "UNKNOWN")
        print(f"  [{time.time() - t0:.0f}s] {status}", flush=True)
        if status in ("SUCCEEDED", "SUCCESS"):
            url = info["output"]["video_url"]
            out = os.path.join(RUN, "lipsync_probe.mp4")
            gen.download(url, out)
            print(f"✅ 口型镜头成片: {out}")
            return
        if status in ("FAILED", "UNKNOWN"):
            print(json.dumps(info, ensure_ascii=False)[:600])
            sys.exit(1)
        time.sleep(15)
    print("⚠️ 轮询超时（任务仍在服务端，可凭 task_id 续查）")
    sys.exit(2)


if __name__ == "__main__":
    main()