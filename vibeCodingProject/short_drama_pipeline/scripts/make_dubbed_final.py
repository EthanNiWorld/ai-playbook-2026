"""短剧成片配音版合成：qwen-audio-3.1-tts-plus 配音 + 字幕烧录 + BGM 垫底。

输入：run_008_20261120_180542 的三段 scene_*_edited.mp4（各 8s）+ storyboard.json 台词
输出：final_dubbed.mp4 —— 每段台词配音（甜美女声，台词中途插入）+ 底部字幕 + 环境音 BGM

字幕实现：本机 homebrew ffmpeg 8.1 bottle 不含 drawtext/subtitles 滤镜，
改用 PIL 生成透明底字幕 PNG + overlay 烧录（基础滤镜，无编译依赖）；
字体用系统 Hiragino Sans GB（PingFang.ttc 在 PIL 不可直接打开）。

运行：.venv/bin/python -u scripts/make_dubbed_final.py
"""
import json
import os
import subprocess
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

if not config.check_credentials():
    sys.exit(1)

RUN = os.path.join(config.OUTPUT_DIR, "run_008_20261120_180542")
TTS_MODEL = "qwen-audio-3.1-tts-plus"
VOICE = "longanlingxin_v3.1"  # plus 旗舰女声
# 情绪指令按场景序号循环（任意场景数通用）
MOOD_CYCLE = [
    "用开心到跳起来的兴奋语气说，语速稍快，尾音上扬",
    "用温柔感慨的语气缓缓说，像在对朋友回忆，语速适中",
    "用地道俏皮的重庆妹儿语气点评，带着笑意，尾音拖长",
]
BGM_PROMPT = ("纯器乐轻音乐，无人声无歌词，轻快治愈的吉他与钢琴，"
               "夏日傍晚湖边的松弛氛围，节奏舒缓，适合作为短视频背景音乐")


def tts_endpoint():
    # workspace compatible-mode URL → 原生 API 根（与 bailian_client 同一推导）
    return config.NATIVE_BASE_URL.rstrip("/") + "/services/audio/tts/SpeechSynthesizer"


def synth(text, mood, out_path):
    """非流式合成一句台词。"""
    payload = {
        "model": TTS_MODEL,
        "input": {"text": f"[{mood}]{text}"},
        "parameters": {"voice": VOICE, "format": "mp3"},
    }
    last = None
    for attempt in range(3):
        try:
            r = requests.post(
                tts_endpoint(),
                headers={"Authorization": f"Bearer {config.API_KEY}"},
                json=payload, timeout=120)
            body = r.json()
            if r.status_code != 200:
                last = f"HTTP {r.status_code}: {body.get('message', '')[:150]}"
                time.sleep(2 ** attempt)
                continue
            url = body["output"]["audio"]["url"]
            audio = requests.get(url, timeout=60)
            audio.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(audio.content)
            return
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
    raise RuntimeError(f"TTS 合成失败: {last}")


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True)
    return float(r.stdout.strip())


def wrap_text(t, per_line=14):
    """中文台词按固定字数折行（字幕图生成用，返回行列表）。"""
    return [t[i:i + per_line] for i in range(0, len(t), per_line)]


def make_subtitle_png(dialogue, out_png, video_w, video_h):
    """PIL 生成底部居中的透明底字幕图（白字 + 半透明黑底条），供 ffmpeg overlay。"""
    font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 30)
    lines = wrap_text(dialogue)
    line_h = 46
    pad = 14
    # 逐行测量宽度取最大值
    widths = [font.getbbox(l)[2] for l in lines]
    w = max(widths) + pad * 2
    h = len(lines) * line_h + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=10, fill=(0, 0, 0, 115))
    y = pad
    for l in lines:
        bbox = font.getbbox(l)
        x = (w - bbox[2]) // 2
        # 描边：四向偏移画黑，再画白字
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((x + dx, y + dy), l, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), l, font=font, fill=(255, 255, 255, 255))
        y += line_h
    img.save(out_png)
    return w, h


def compose_scene(scene_id, dialogue, voiced):
    """单场景合成：配音垫入 + 字幕 overlay → scene_N_dub.mp4。"""
    src = os.path.join(RUN, f"scene_{scene_id}_edited.mp4")
    out = os.path.join(RUN, f"scene_{scene_id}_dub.mp4")
    d_total = dur(src)
    d_voice = dur(voiced)
    # 台词起点：片段中段（约 40% 处），给画面留呼吸感
    start = max(0.8, (d_total - d_voice) * 0.4)
    afilter = (
        f"[0:a]volume=0.3[bg];"
        f"[1:a]adelay={int(start * 1000)}|{int(start * 1000)}[vo];"
        f"[bg][vo]amix=inputs=2:duration=first:dropout_transition=0[aout]"
    )
    # 字幕：PIL 生成透明 PNG，overlay 底部居中（enable 全程显示）
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                           "-show_entries", "stream=width,height", "-of", "csv=p=0", src],
                          capture_output=True, text=True)
    vw, vh = map(int, probe.stdout.strip().split(","))
    sub_png = os.path.join(RUN, f"sub_{scene_id}.png")
    sw, sh = make_subtitle_png(dialogue, sub_png, vw, vh)
    ov = (f"[2:v]scale={min(sw, vw - 20)}:-1[s];"
          f"[0:v][s]overlay=(W-w)/2:H-h-24")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", src, "-i", voiced, "-i", sub_png,
        "-filter_complex", f"{afilter};{ov}[vout]",
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", out,
    ], capture_output=True, check=True)
    return out


def gen_bgm(out_path):
    """fun-music-v1 生成纯器乐 BGM（幂等：已存在则跳过）。"""
    if os.path.isfile(out_path):
        return
    payload = {
        "model": "fun-music-v1",
        "input": {"prompt": BGM_PROMPT},
        "parameters": {"format": "mp3"},
    }
    last = None
    for attempt in range(3):
        try:
            r = requests.post(
                config.NATIVE_BASE_URL.rstrip("/") + "/services/audio/music/generation",
                headers={"Authorization": f"Bearer {config.API_KEY}"},
                json=payload, timeout=300)
            body = r.json()
            if r.status_code != 200:
                last = f"HTTP {r.status_code}: {body.get('message', '')[:150]}"
                time.sleep(2 ** attempt)
                continue
            audio = requests.get(body["output"]["audio"]["url"], timeout=120)
            audio.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(audio.content)
            return
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
    print(f"  ⚠️ BGM 生成失败（{last}），跳过背景乐继续合成", flush=True)


def dub_final(run_dir):
    """对指定 run 目录生成配音字幕版全片 final_dubbed.mp4（可被 pipeline 导入）。

    幂等：voice_*.mp3 / bgm.mp3 / scene_*_dub.mp4 已存在则跳过对应合成，
    可反复重跑（例如仅替换 bgm.mp3 后重混）。依赖 PIL + ffmpeg（无 drawtext 也能跑）。"""
    global RUN
    RUN = run_dir
    board = json.load(open(os.path.join(RUN, "storyboard.json")))
    scenes = sorted(board["scenes"], key=lambda s: s["id"])
    dubbed = []
    for i, sc in enumerate(scenes):
        sid, line = sc["id"], sc.get("dialogue", "")
        if not line:
            continue
        voiced = os.path.join(RUN, f"voice_{sid}.mp3")
        if not os.path.isfile(voiced):
            print(f"场景{sid} TTS 合成: {line[:24]}…", flush=True)
            synth(line, MOOD_CYCLE[i % len(MOOD_CYCLE)], voiced)
        print(f"  voice_{sid}.mp3 ({dur(voiced):.1f}s)", flush=True)
        out = compose_scene(sid, line, voiced)
        dubbed.append(out)
        print(f"✅ 场景{sid} 配音字幕版完成 ({dur(out):.1f}s)", flush=True)

    lst = os.path.join(RUN, "concat_dub.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.basename(d)}'\n" for d in dubbed)
    # 转场拼接：硬切在剧情跳跃时（清晨公寓→傍晚湖边）很突兀，改为
    # 每段首尾 0.4s 淡入淡出 + 场景间 0.8s 交叉溶解（视频 xfade + 音频 acrossfade 同步），
    # 总时长 ≈ 片段和 - 2×转场重叠。xfade 要求同分辨率/帧率，dub 片段已统一。不用 concat demuxer。
    FADE = 0.8  # 交叉溶解时长
    merged = os.path.join(RUN, "final_dubbed_nobgm.mp4")
    if len(dubbed) >= 2:
        fc_parts = []
        for idx, p in enumerate(dubbed):
            fc_parts.append(
                f"[{idx}:v]fade=t=in:st=0:d=0.4,fade=t=out:st={dur(p) - 0.4:.2f}:d=0.4[v{idx}];"
                f"[{idx}:a]afade=t=in:st=0:d=0.4,afade=t=out:st={dur(p) - 0.4:.2f}:d=0.4[a{idx}]")
        # 链式 xfade/acrossfade：偏移 = 已拼时长 - FADE
        inputs = []
        for p in dubbed:
            inputs += ["-i", p]
        prev_v, prev_a = "v0", "a0"
        offset = dur(dubbed[0]) - FADE
        for i in range(1, len(dubbed)):
            out_v, out_a = (f"xv{i}", f"xa{i}") if i < len(dubbed) - 1 else ("xv", "xa")
            fc_parts.append(
                f"[{prev_v}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.2f}[{out_v}];"
                f"[{prev_a}][a{i}]acrossfade=d={FADE}[{out_a}]")
            prev_v, prev_a = out_v, out_a
            offset += dur(dubbed[i]) - FADE
        subprocess.run(
            ["ffmpeg", "-y", *inputs,
             "-filter_complex", ";".join(fc_parts),
             "-map", "[xv]", "-map", "[xa]",
             "-c:v", "libx264", "-preset", "fast", "-crf", "23",
             "-c:a", "aac", "-b:a", "160k", merged],
            capture_output=True, check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", merged], capture_output=True, check=True)
    print(f"  转场拼接完成（{len(dubbed)} 段，交叉溶解 {FADE}s）", flush=True)
    # BGM：自动生成（幂等）→ 循环垫底音量 0.18 + 淡入；无 BGM 时不阻断出片
    final = os.path.join(RUN, "final_dubbed.mp4")
    bgm = os.path.join(RUN, "bgm.mp3")
    gen_bgm(bgm)
    if os.path.isfile(bgm):
        subprocess.run([
            "ffmpeg", "-y", "-i", merged, "-stream_loop", "-1", "-i", bgm,
            "-filter_complex",
            "[1:a]volume=0.18,afade=t=in:d=1.5[b];[0:a][b]amix=inputs=2:duration=first:dropout_transition=0[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest", final,
        ], capture_output=True, check=True)
        print("已混入 fun-music 生成的 BGM", flush=True)
    else:
        os.replace(merged, final)
        print("（BGM 缺失，出无背景乐版本）", flush=True)
    print(f"✅ 配音字幕版全片: final_dubbed.mp4（{dur(final):.1f}s）", flush=True)
    return final


def main():
    run_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        config.OUTPUT_DIR, "run_008_20261120_180542")
    dub_final(run_dir)


if __name__ == "__main__":
    main()
