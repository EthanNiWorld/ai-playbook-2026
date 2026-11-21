"""单镜头重生成（口型镜头版）：给已有 run 重造指定场景的口型镜头。

用途：run_011 场景4 原为"总裁本人"的收尾独白，需改为"马老师抱拳祝贺"——
换人物动作、换台词（LLM 生成）、换声音（马老师克隆音色）。

流程：
① qwen4-max 按人设生成一句台词 + voice_mood（贴人设情绪）
② TTS 合成（指定克隆音色，走 instruction 通道）→ 公网 URL 驱动口型
③ wan2.7-i2v：首帧（run 内归档图）+ driving_audio + 动作 prompt → 720P/8s
④ 备份旧 scene_X_edited.mp4 → 替换 → 更新 storyboard dialogue/voice_mood
⑤ 提示后续重拼/质检命令（dub 幂等重跑 + _concat_final_cut + qa 脚本）

运行：.venv/bin/python -u scripts/rework_lipsync_scene.py <run目录> <场景号> <图路径> <voice_id> <动作prompt> [人设描述]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from bailian_client import BailianAsyncClient  # noqa: E402
from llm_client import Qwen4MaxClient  # noqa: E402
from make_dubbed_final import synth  # noqa: E402
from qa_dubbing import asr as asr_text, similarity  # noqa: E402

RUN = sys.argv[1]
SID = int(sys.argv[2])
IMG = sys.argv[3]
VOICE_ID = sys.argv[4]
ACTION = sys.argv[5]
SPEAKER = sys.argv[6] if len(sys.argv) > 6 else "主角"


def main():
    board_path = os.path.join(RUN, "storyboard.json")
    board = json.load(open(board_path))
    sc = next(s for s in board["scenes"] if s["id"] == SID)

    # ① LLM 生成台词（贴人设；保持台词简短，口型镜头 3-8s 内说完）
    llm = Qwen4MaxClient()
    q = (f"短剧《{board['title']}》中，{SPEAKER}面对镜头做一个约 5 秒的祝贺/表态镜头，"
         f"画面动作是：{ACTION}。剧情背景：{sc.get('desc', '')}。"
         "请输出严格 JSON（不要 markdown）："
         "{\"dialogue\": \"一句 12-20 字的中文台词\", "
         "\"voice_mood\": \"这句台词的说话方式（语气/情绪，贴合人物身份，20字内）\", "
         "\"video_prompt\": \"一段镜头运动与人物动作描述（中文，40字内，含口型与台词同步的要求）\"}")
    gen = llm._extract_json(llm.chat([{"role": "user", "content": q}],
                                     temperature=0.8, max_tokens=400))
    line, mood, vprompt = gen["dialogue"], gen["voice_mood"], gen["video_prompt"]
    print(f"① 台词: {line}")
    print(f"   情绪: {mood}")
    print(f"   运镜: {vprompt}")

    # ② TTS 合成（指定克隆音色 + instruction 情绪通道）
    voiced_local = os.path.join(RUN, f"voice_{SID}.mp3")
    audio_url = synth(line, mood, voiced_local, voice=VOICE_ID)
    text_back = asr_text(voiced_local)
    sim = similarity(text_back, line)
    print(f"② TTS 合成（克隆音色）→ ASR 回验相似度 {sim:.0%}")
    if sim < 0.85:
        print(f"   ❌ ASR 识别: {text_back}")
        sys.exit(1)

    # ③ wan2.7-i2v 口型生成：首帧 data URI + driving_audio
    gen_client = BailianAsyncClient()
    b64, mime = llm._encode_image(IMG)
    still_uri = f"data:{mime};base64,{b64}"
    task_id, model = gen_client.lipsync2video(
        f"{vprompt}；口型与台词音频逐字同步", still_uri, audio_url,
        ["wan2.7-i2v", "wan2.7-i2v-2026-06-12"], resolution="720P", duration=8)
    print(f"③ 口型任务已提交: {task_id}（{model}）")
    t0 = time.time()
    while time.time() - t0 < 900:
        info = gen_client.query_task(task_id)
        status = info.get("output", {}).get("task_status", "UNKNOWN")
        if status in ("SUCCEEDED", "SUCCESS"):
            break
        if status in ("FAILED", "CANCELED"):
            print(json.dumps(info.get("output", {}), ensure_ascii=False)[:300])
            sys.exit(1)
        time.sleep(15)
    else:
        print("⚠️ 轮询超时（task_id 已落日志，可续查）")
        sys.exit(2)
    url = info["output"]["video_url"]

    # ④ 备份旧片段并替换
    edited = os.path.join(RUN, f"scene_{SID}_edited.mp4")
    if os.path.isfile(edited):
        os.replace(edited, edited + f".bak{int(time.time())}")
    gen_client.download(url, edited)

    # 更新 storyboard（台词/情绪/首帧归档引用不变）
    sc["dialogue"], sc["voice_mood"] = line, mood
    json.dump(board, open(board_path, "w"), ensure_ascii=False, indent=2)
    # checkpoint 的 lipsync 标记保持（该场仍为口型场景）
    print(f"✅ 场景{SID} 已重生成: {os.path.basename(edited)}")
    print(f"后续: 删除 {RUN}/scene_{SID}_dub.mp4 后重跑 dub_final + _concat_final_cut，"
          f"再跑 scripts/qa_dubbing.py / qa_continuity.py 质检")


if __name__ == "__main__":
    main()