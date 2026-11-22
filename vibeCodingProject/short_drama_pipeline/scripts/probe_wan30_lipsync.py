"""探测 wan3.0-video-prime 口型迁移路线：reference_image + reference_audio 组合参考。

背景：wan2.7-i2v 的 first_frame+driving_audio 是现有口型链路（121s/条，逐字口型）。
wan3.0 的 reference 系与 first_frame 互斥，音频只能走 reference_audio，故候选：
  B 路（本脚本）：reference_image（人物剧照）+ reference_audio（TTS 台词）单任务，
     提示词要求图1人物说出台词——验证是否出口型同步
对照基线：run_012 场景1 现有 wan2.7-i2v 口型片 scene_1_shot1_take0.mp4。

验证维度：
  1. 音轨 ASR 相似度（台词是否说进去了）
  2. 抽帧目视口型开合变化
  3. 时长/规格
用法：python3 scripts/probe_wan30_lipsync.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient
from llm_client import Qwen4MaxClient

LINE = "重庆的辣装进行李箱，下一站，马来西亚！"
PROMPT = (
    "图1中的年轻女士面对镜头说话：她直视镜头、微笑着说出台词，"
    "语音内容与音频1完全一致，口型与语音逐字同步，头部与肩膀自然微动，"
    "其余保持人物原有的发型、面容与服饰；竖构图，写实风格。"
)


def main():
    run_dir = os.path.join(config.OUTPUT_DIR, "run_012_20261121_225209")
    if not config.check_credentials():
        sys.exit(1)
    gen = BailianAsyncClient()

    # 素材：换人剧照 + TTS 台词（reference_audio 只吃公网 URL）
    img = os.path.join(run_dir, "lead_s1_shot1.png")
    b64, mime = Qwen4MaxClient()._encode_image(img)
    img_uri = f"data:{mime};base64,{b64}"
    sys.path.insert(0, os.path.join(config.PROJECT_DIR, "scripts"))
    from make_dubbed_final import synth
    audio_url = synth(LINE, "兴奋俏皮", os.path.join(run_dir, "probe_ls_voice.mp3"), voice=None)
    print("[素材] 剧照 data URI + TTS 公网 URL 就绪")

    body = {
        "_kind": "video",
        "model": "wan3.0-video-prime",
        "input": {"prompt": PROMPT, "media": [
            {"type": "reference_image", "url": img_uri},
            {"type": "reference_audio", "url": audio_url},
        ]},
        "parameters": {"resolution": "480P", "ratio": "adaptive", "duration": -1},
    }
    t0 = time.time()
    task_id, _ = gen._post_task(body, max_retry=2)
    print(f"[wan30-lipsync] ✅ 受理（task={task_id[:18]}…）轮询中…")
    while True:
        info = gen.query_task(task_id)
        st = info.get("output", {}).get("task_status")
        if st in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"):
            break
        if time.time() - t0 > 900:
            print("超过 900s 未完成")
            return 1
        time.sleep(15)
    dt = time.time() - t0
    url = info.get("output", {}).get("video_url")
    print(f"[wan30-lipsync] 终态 {st}（{dt:.0f}s）{(info.get('output', {}).get('message') or '')[:150]}")
    if st != "SUCCEEDED" or not url:
        return 1
    out = os.path.join(config.PROJECT_DIR, "org_file", "probe_wan30_lipsync.mp4")
    gen.download(url, out)
    print(f"[wan30-lipsync] 产物: {out}")

    # 验证 1：ASR 台词相似度
    sys.path.insert(0, os.path.join(config.PROJECT_DIR, "scripts"))
    from qa_dubbing import asr, similarity
    text = asr(out)
    sim = similarity(text, LINE)
    print(f"[ASR] {text}\n[ASR] 相似度 {sim:.0%}（wan2.7-i2v 基线通常 ≥85%）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
