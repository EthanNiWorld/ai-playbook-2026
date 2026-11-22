"""探测 wan3.0-video-prime 的视频编辑 + 语音带入能力（官方 wan3 视频生成指南）。

文档口径（docs.modelstudio wan3-video-generation-guide）：
- wan3.0 系是 All-in-One：视频编辑 = input.media type=reference_video + 提示词含
  编辑意图（"编辑视频/替换/去掉"）；ratio 建议 adaptive、duration 建议 -1
  （自动保持原视频宽高比与时长）
- 语音带入 = type=reference_audio（≤5段、总时长≤15s、单文件≤15MB），
  可与 reference_video 组合
- 素材指代：第1个 reference_video 对应"视频1"，第1个 reference_audio 对应"音频1"

探测项：
  A. 视频编辑：reference_video（现场生成的 8s 素材）+ 编辑意图提示词
  B. voice 带入：reference_video + reference_audio（TTS 台词）+ 说出台词提示词
对比基线：wan2.7-videoedit（type=video 老格式）单条编辑任务耗时

用法：python3 scripts/probe_wan30_edit.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient
from llm_client import Qwen4MaxClient

EDIT_PROMPT = ("编辑视频1：把背景替换为雨夜霓虹街头，人物与动作保持不变，"
               "画面内所有文字与原视频逐字一致；保持原视频宽高比与时长。")
VOICE_PROMPT = ("编辑视频1：让视频中的女士说出台词，语音内容与音频1完全一致，"
                "口型与音频同步，其余画面与动作保持原样。")
VOICE_LINE = "重庆的辣装进行李箱，下一站，马来西亚！"


def gen_material_video(gen, run_dir):
    """现场生成 8s 素材视频（prime 480P，首帧用换人剧照），返回产物 URL。"""
    first_frame = None
    for cand in ("lead_s1_shot1.png", "custom_01.png"):
        p = os.path.join(run_dir, cand)
        if os.path.isfile(p):
            first_frame = p
            break
    ff_uri = None
    if first_frame:
        b64, mime = Qwen4MaxClient()._encode_image(first_frame)
        ff_uri = f"data:{mime};base64,{b64}"
    task_id, model = gen.image2video(
        "女主角微笑着向镜头挥手，动作轻微", ff_uri,
        ["wan3.0-video-prime", "wan3.0-video"], resolution="480P", duration=8)
    print(f"[素材] 生成中（{model} task={task_id[:18]}…）…")
    t0 = time.time()
    while True:
        info = gen.query_task(task_id)
        st = info.get("output", {}).get("task_status")
        if st in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"):
            break
        if time.time() - t0 > 420:
            raise TimeoutError("素材视频生成超时")
        time.sleep(15)
    url = info.get("output", {}).get("video_url")
    if st != "SUCCEEDED" or not url:
        raise RuntimeError(f"素材视频生成失败: {st} {info.get('output', {}).get('message', '')[:120]}")
    print(f"[素材] 就绪（{time.time() - t0:.0f}s）")
    return url


def gen_tts_audio(run_dir):
    """TTS 合成一句台词，返回公网签名 URL（driving_audio 同款通道）。"""
    sys.path.insert(0, os.path.join(config.PROJECT_DIR, "scripts"))
    from make_dubbed_final import synth
    local = os.path.join(run_dir, "probe_voice.mp3")
    url = synth(VOICE_LINE, "兴奋俏皮", local, voice=None)
    print(f"[音频] TTS 就绪: {local}")
    return url


def run_edit_task(gen, label, model, media, prompt):
    """提交视频编辑/语音任务并轮询到终态，返回 (耗时s, 状态, url)。"""
    body = {
        "_kind": "video",
        "model": model,
        "input": {"prompt": prompt, "media": media},
        "parameters": {"resolution": "480P", "duration": -1, "ratio": "adaptive"},
    }
    t0 = time.time()
    try:
        task_id, _ = gen._post_task(body, max_retry=2)
    except Exception as e:
        print(f"[{label}] ❌ 提交被拒: {str(e)[:200]}")
        return None
    print(f"[{label}] ✅ 受理（task={task_id[:18]}…）轮询中…")
    while True:
        info = gen.query_task(task_id)
        st = info.get("output", {}).get("task_status")
        if st in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"):
            break
        if time.time() - t0 > 900:
            print(f"[{label}] ⏱️ 超过 900s 未完成（wan2.7-videoedit 同类任务约 8-10 分钟）")
            return ("timeout", task_id)
        time.sleep(20)
    dt = time.time() - t0
    url = info.get("output", {}).get("video_url")
    msg = info.get("output", {}).get("message", "") or info.get("message", "")
    print(f"[{label}] 终态 {st}（{dt:.0f}s）{str(msg)[:150]}")
    if st == "SUCCEEDED" and url:
        out = os.path.join(config.PROJECT_DIR, "org_file", f"probe_{label}.mp4")
        gen.download(url, out)
        print(f"[{label}] 产物已下载: {out}")
    return (st, dt, url)


def main():
    run_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        config.OUTPUT_DIR, "run_012_20261121_225209")
    if not config.check_credentials():
        sys.exit(1)
    gen = BailianAsyncClient()

    # 素材：新视频 + TTS 音频（reference_video/audio 都只吃公网 URL）
    video_url = gen_material_video(gen, run_dir)
    audio_url = gen_tts_audio(run_dir)

    # A. 视频编辑（wan3.0-video-prime，type=reference_video + 编辑意图）
    run_edit_task(gen, "edit_wan30prime", "wan3.0-video-prime",
                  [{"type": "reference_video", "url": video_url}], EDIT_PROMPT)

    # B. voice 带入（reference_video + reference_audio 组合）
    run_edit_task(gen, "voice_wan30prime", "wan3.0-video-prime",
                  [{"type": "reference_video", "url": video_url},
                   {"type": "reference_audio", "url": audio_url}], VOICE_PROMPT)

    print("\n探测完成。产物在 org_file/probe_*.mp4，可抽帧人工比对。")


if __name__ == "__main__":
    main()
