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
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def synth(text, mood, out_path, voice=None):
    """非流式合成一句台词，返回音频公网签名 URL（可供 wan driving_audio 直用）。

    voice 传入克隆音色 ID（如 qwen-audio-3.1-tts-plus-xxx）可覆盖默认旗舰音色。
    情绪指令走 input.instruction 独立参数（官方指令控制通道，复刻/设计音色
    均支持）——不拼进 text：方括号标签体系只对系统音色生效，克隆音色会把
    [指令] 当普通文本朗读（run_010 实测事故，ASR 回验发现“俏皮重庆妹儿”
    被念了出来）。"""
    inp = {"text": text}
    if mood:
        inp["instruction"] = f"请用中文说，{mood}"
    payload = {
        "model": TTS_MODEL,
        "input": inp,
        "parameters": {"voice": voice or VOICE, "format": "mp3"},
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
            if out_path:
                with open(out_path, "wb") as f:
                    f.write(audio.content)
            return url
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
    """PIL 生成底部居中的透明底字幕图（商用短视频样式），供 ffmpeg overlay。

    参考抖音/剪映字幕风格：无底色块，画面通透——靠「柔和虚化阴影 + 描边」
    保证任意背景下的可读性：阴影用多层低透明度偏移叠加再高斯模糊，
    呈现从字周向外渐散的虚化效果（区别于硬边黑条）。"""
    font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 34)
    lines = wrap_text(dialogue)
    line_h = 52
    # 画布留出血：四周预留描边+阴影扩散空间
    bleed = 24
    widths = [font.getbbox(l)[2] for l in lines]
    text_w = max(widths)
    w = text_w + bleed * 2
    h = len(lines) * line_h + bleed * 2
    # 第一层：先在更大画布画纯黑文字（阴影层），再模糊成虚化投影
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    y = bleed
    for l in lines:
        bbox = font.getbbox(l)
        x = (w - bbox[2]) // 2
        sdraw.text((x, y), l, font=font, fill=(0, 0, 0, 255))
        y += line_h
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    # 阴影透明度压到约 55%：足够 readable，又不会形成“黑色块”观感
    shadow.putalpha(shadow.getchannel("A").point(lambda a: int(a * 0.55)))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.alpha_composite(shadow)
    draw = ImageDraw.Draw(img)
    # 第二层：描边（八向偏移，包覆更完整）
    y = bleed
    for l in lines:
        bbox = font.getbbox(l)
        x = (w - bbox[2]) // 2
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)):
            draw.text((x + dx, y + dy), l, font=font, fill=(0, 0, 0, 200))
        y += line_h
    # 第三层：白字主体（略带淡黄暖调，更贴近商用短剧字幕观感）
    y = bleed
    for l in lines:
        bbox = font.getbbox(l)
        x = (w - bbox[2]) // 2
        draw.text((x, y), l, font=font, fill=(255, 252, 244, 255))
        y += line_h
    img.save(out_png)
    return w, h


def compose_scene(scene_id, dialogue, voiced, lipsync=False):
    """单场景合成：配音垫入 + 字幕 overlay → scene_N_dub.mp4。

    lipsync=True：台词已由 driving_audio 烧进视频音轨（wan2.7-i2v 口型镜头），
    跳过二次 TTS 混入避免双声重叠，只烧字幕、保留原音轨。"""
    src = os.path.join(RUN, f"scene_{scene_id}_edited.mp4")
    out = os.path.join(RUN, f"scene_{scene_id}_dub.mp4")
    if lipsync:
        afilter = "[0:a]anull[aout]"
    else:
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
    # lipsync 场景不输入 voice 文件，字幕 PNG 索引相应前移
    sub_idx = 1 if lipsync else 2
    ov = ov.replace("[2:v]", f"[{sub_idx}:v]")
    inputs = ["-i", src]
    if not lipsync:
        inputs += ["-i", voiced]
    inputs += ["-i", sub_png]
    subprocess.run([
        "ffmpeg", "-y", *inputs,
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


def _pick_voice(voice, speaker=""):
    """voice 为 dict（多角色映射）时按 speaker 取对应克隆音色；
    无匹配/无 speaker 回退默认旗舰音色（返回 None）；str 直接透传。"""
    if isinstance(voice, dict):
        return voice.get((speaker or "").strip())
    return voice


def dub_final(run_dir, voice=None):
    """对指定 run 目录生成配音字幕版全片 final_dubbed.mp4（可被 pipeline 导入）。

    voice：str=单音色 ID；dict=多角色映射（角色名→voice_id，按分镜 scenes[].speaker
    路由，无匹配场景回退默认音色）；None=默认旗舰女声。

    幂等：voice_*.mp3 / bgm.mp3 / scene_*_dub.mp4 已存在则跳过对应合成，
    可反复重跑（例如仅替换 bgm.mp3 后重混）。依赖 PIL + ffmpeg（无 drawtext 也能跑）。"""
    global RUN
    RUN = run_dir
    board = json.load(open(os.path.join(RUN, "storyboard.json")))
    scenes = sorted(board["scenes"], key=lambda s: s["id"])
    # 口型场景识别：checkpoint 里 lipsync 标记的镜头所在场景，
    # 台词已在视频音轨里，只烧字幕不二次配音（避免双声重叠）
    lipsync_sids = set()
    ckpt_path = os.path.join(RUN, "checkpoint.json")
    if os.path.isfile(ckpt_path):
        try:
            ck = json.load(open(ckpt_path))
            lipsync_sids = {t["scene_id"] for t in ck.get("video_tasks", []) if t.get("lipsync")}
        except (json.JSONDecodeError, OSError, KeyError):
            pass
    dubbed = []
    for i, sc in enumerate(scenes):
        sid, line = sc["id"], sc.get("dialogue", "")
        if not line:
            continue
        is_lipsync = sid in lipsync_sids
        voiced = os.path.join(RUN, f"voice_{sid}.mp3")
        if not is_lipsync:
            if not os.path.isfile(voiced):
                # 情绪优先用分镜的 voice_mood（LLM 按人设/剧情生成）；
                # 缺失时兑底 MOOD_CYCLE（旧分镜兼容）；多角色时按 speaker 选音色
                mood = sc.get("voice_mood") or MOOD_CYCLE[i % len(MOOD_CYCLE)]
                this_voice = _pick_voice(voice, sc.get("speaker", ""))
                tag = "，克隆音色" if this_voice else ""
                print(f"场景{sid} TTS 合成（{sc.get('speaker') or '旁白'}）: {line[:24]}…（{mood[:14]}…{tag}）", flush=True)
                synth(line, mood, voiced, voice=this_voice)
            print(f"  voice_{sid}.mp3 ({dur(voiced):.1f}s)", flush=True)
        else:
            print(f"场景{sid} 口型镜头：台词已在视频音轨，跳过二次配音只烧字幕", flush=True)
        out = compose_scene(sid, line, voiced, lipsync=is_lipsync)
        dubbed.append(out)
        print(f"✅ 场景{sid} 配音字幕版完成 ({dur(out):.1f}s)", flush=True)

    lst = os.path.join(RUN, "concat_dub.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.basename(d)}'\n" for d in dubbed)
    # 转场拼接：硬切在剧情跳跃时（清晨公寓→傍晚湖边）很突兀，改为
    # 每段首尾 0.4s 淡入淡出 + 场景间 0.8s 交叉溶解（视频 xfade + 音频 acrossfade 同步），
    # 总时长 ≈ 片段和 - 2×转场重叠。xfade 要求同分辨率/帧率，dub 片段已统一。不用 concat demuxer。
    FADE = 0.8  # 交叉溶解时长
    # 统一画布：客户图库模式下各段视频比例随原图各异（4:3/16:9/竖版），
    # xfade 要求同分辨率——每段内接缩放到 3:4 画布并居中 pad，不裁切不变形
    CANVAS = "scale=1080:1440:force_original_aspect_ratio=decrease,"
    CANVAS += "pad=1080:1440:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"
    merged = os.path.join(RUN, "final_dubbed_nobgm.mp4")
    if len(dubbed) >= 2:
        fc_parts = []
        for idx, p in enumerate(dubbed):
            fc_parts.append(
                f"[{idx}:v]{CANVAS},fade=t=in:st=0:d=0.4,fade=t=out:st={dur(p) - 0.4:.2f}:d=0.4[v{idx}];"
                f"[{idx}:a]aresample=44100,afade=t=in:st=0:d=0.4,afade=t=out:st={dur(p) - 0.4:.2f}:d=0.4[a{idx}]")
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
