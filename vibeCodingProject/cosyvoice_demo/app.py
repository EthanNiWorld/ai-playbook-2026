#!/usr/bin/env python3
"""
CosyVoice v3.5-plus Demo
声音复刻 | 声音设计 | 语音合成
"""
import os
import re
import json
import time
import base64
import tempfile
import uuid
from datetime import datetime
import requests
import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer
import gradio as gr
from dotenv import load_dotenv

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

# ===== 配置 =====
WORKSPACE_ID = "llm-kvw0aiysjfv4g6fh"

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY_CN")
if not dashscope.api_key:
    raise ValueError("请设置 DASHSCOPE_API_KEY_CN 环境变量")

dashscope.base_websocket_api_url = f"wss://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
dashscope.base_http_api_url = f"https://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1"

BASE_URL = f"https://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1"
TARGET_MODEL = "cosyvoice-v3.5-plus"
QWEN_AUDIO_ASR_MODEL = "qwen-audio-3.0-asr-flash-filetrans"
QWEN_AUDIO_ASR_FLASH_MODEL = "qwen-audio-3.0-asr-flash"
HEADERS = {
    "Authorization": f"Bearer {dashscope.api_key}",
    "Content-Type": "application/json",
}

# 音色持久化
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
VOICES_FILE = os.path.join(OUTPUT_DIR, "voices.json")
GENERATED_AUDIO_FILE = os.path.join(OUTPUT_DIR, "generated_audio.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
#  工具函数
# ============================================================

def _sanitize_prefix(prefix: str) -> str:
    """清理 prefix：仅保留英文字母和数字，截断至 10 字符，空则用默认值"""
    if not prefix:
        return "myvoice"
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', prefix)
    if not cleaned:
        return "myvoice"
    return cleaned[:10]


def save_voice(voice_id: str, source: str, prefix: str, extra: dict = None):
    """将创建的音色保存到 output/voices.json"""
    voices = load_voices()
    entry = {
        "voice_id": voice_id,
        "source": source,  # "clone" or "design"
        "prefix": prefix,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if extra:
        entry.update(extra)
    voices.append(entry)
    with open(VOICES_FILE, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False, indent=2)


def load_voices() -> list:
    """从 output/voices.json 加载已保存的音色列表"""
    if not os.path.exists(VOICES_FILE):
        return []
    try:
        with open(VOICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_voice_choices() -> list:
    """生成 Gradio Dropdown 的 choices 列表"""
    voices = load_voices()
    choices = []
    for v in voices:
        vid = v.get("voice_id", "")
        src = "🎤复刻" if v.get("source") == "clone" else "🎨设计"
        prefix = v.get("prefix", "")
        created = v.get("created_at", "")
        label = f"{src} | {prefix} | {vid[:40]}... | {created}"
        choices.append((label, vid))
    return choices


def get_audio_url_choices() -> list:
    """从 generated_audio.json 中读取已保存的合成音频，生成 ASR 下拉列表"""
    audios = load_generated_audio()
    choices = []
    for a in audios:
        url = a.get("audio_url", "")
        if url:
            voice_id = a.get("voice_id", "")
            text = a.get("text", "")[:30]
            created = a.get("created_at", "")
            label = f"🔊 {voice_id[:30]}... | {text}... | {created}"
            choices.append((label, url))
    return choices


def save_generated_audio(voice_id: str, text: str, audio_url: str):
    """将 TTS 合成音频信息保存到 output/generated_audio.json"""
    audios = load_generated_audio()
    entry = {
        "voice_id": voice_id,
        "text": text,
        "audio_url": audio_url,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    audios.append(entry)
    with open(GENERATED_AUDIO_FILE, "w", encoding="utf-8") as f:
        json.dump(audios, f, ensure_ascii=False, indent=2)


def load_generated_audio() -> list:
    """从 output/generated_audio.json 加载已保存的合成音频列表"""
    if not os.path.exists(GENERATED_AUDIO_FILE):
        return []
    try:
        with open(GENERATED_AUDIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def upload_to_oss(local_path: str) -> str:
    """将本地音频文件上传到 OSS，返回带签名的临时访问 URL（有效期 1 小时）"""
    import oss2

    ak_id = os.getenv("oss_AccessKey_ID", "")
    ak_secret = os.getenv("oss_AccessKey_key", "")
    endpoint = os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
    bucket_name = os.getenv("OSS_BUCKET_NAME", "")
    prefix = os.getenv("OSS_UPLOAD_PREFIX", "cosyvoice-demo/")

    if not all([ak_id, ak_secret, bucket_name]):
        raise ValueError("OSS 配置不完整，请检查 .env 中的 oss_AccessKey_ID / oss_AccessKey_key / OSS_BUCKET_NAME")

    auth = oss2.Auth(ak_id, ak_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    ext = os.path.splitext(local_path)[1] or ".wav"
    oss_key = f"{prefix}{uuid.uuid4().hex[:12]}{ext}"

    bucket.put_object_from_file(oss_key, local_path)

    # 生成签名 URL（有效期 3600 秒），适用于 private bucket
    signed_url = bucket.sign_url('GET', oss_key, 3600)
    return signed_url


# ============================================================
#  核心函数
# ============================================================

def clone_voice_url(audio_url, prefix):
    """声音复刻 —— 通过音频 URL 创建音色"""
    if not audio_url:
        return "❌ 请输入音频 URL", "", None
    prefix = _sanitize_prefix(prefix)
    status_msg = f"ℹ️ prefix 已规范化为: {prefix}\n" if prefix != (prefix or 'myvoice') else ""

    try:
        service = VoiceEnrollmentService()
        voice_id = service.create_voice(
            target_model=TARGET_MODEL,
            prefix=prefix,
            url=audio_url,
        )
        rid = service.get_last_request_id()
        status_msg = f"✅ 复刻请求已提交\nRequest ID: {rid}\nVoice ID: {voice_id}"

        # 轮询等待音色就绪
        for attempt in range(1, 16):
            time.sleep(5)
            try:
                info = service.query_voice(voice_id=voice_id)
                status = info.get("status")
                if status == "OK":
                    status_msg += f"\n✅ 音色已就绪（第 {attempt} 次查询）"
                    save_voice(voice_id, "clone", prefix, {"audio_url": audio_url})
                    return status_msg, voice_id, None
                elif status == "UNDEPLOYED":
                    status_msg += f"\n❌ 音色审核未通过 (UNDEPLOYED)"
                    return status_msg, voice_id, None
                status_msg += f"\n⏳ 状态: {status}，继续等待..."
            except Exception as e:
                status_msg += f"\n⚠️ 查询异常: {e}"

        status_msg += "\n⏰ 轮询超时，请稍后手动查询状态"
        return status_msg, voice_id, None

    except Exception as e:
        return f"❌ 错误: {e}", "", None


def clone_voice_file(audio_file, prefix):
    """声音复刻 —— 本地文件上传 OSS → 获取 URL → 创建音色"""
    if audio_file is None:
        return "❌ 请上传音频文件", "", None
    prefix = _sanitize_prefix(prefix)

    try:
        # Step 1: 上传到 OSS
        status_msg = "⬆️ 正在上传音频到 OSS...\n"
        oss_url = upload_to_oss(audio_file)
        status_msg += f"✅ 上传成功\n\n"

        # Step 2: 调复刻 API
        status_msg += "🔧 正在创建音色...\n"
        service = VoiceEnrollmentService()
        voice_id = service.create_voice(
            target_model=TARGET_MODEL,
            prefix=prefix,
            url=oss_url,
        )
        rid = service.get_last_request_id()
        status_msg += f"✅ 复刻请求已提交\nRequest ID: {rid}\nVoice ID: {voice_id}"

        # Step 3: 轮询等待音色就绪
        for attempt in range(1, 16):
            time.sleep(5)
            try:
                info = service.query_voice(voice_id=voice_id)
                status = info.get("status")
                if status == "OK":
                    status_msg += f"\n✅ 音色已就绪（第 {attempt} 次查询）"
                    save_voice(voice_id, "clone", prefix, {"audio_url": oss_url})
                    return status_msg, voice_id, None
                elif status == "UNDEPLOYED":
                    status_msg += f"\n❌ 音色审核未通过 (UNDEPLOYED)"
                    return status_msg, voice_id, None
                status_msg += f"\n⏳ 状态: {status}，继续等待..."
            except Exception as e:
                status_msg += f"\n⚠️ 查询异常: {e}"

        status_msg += "\n⏰ 轮询超时，请稍后在「音色管理」Tab 查询状态"
        return status_msg, voice_id, None

    except Exception as e:
        return f"❌ 错误: {e}", "", None


def optimize_voice_prompt(user_prompt, language):
    """用 qwen3.7-max 优化声音设计提示词（走标准 DashScope 端点）"""

    if not user_prompt or not user_prompt.strip():
        return "❌ 请先输入音色描述", user_prompt

    system_prompt = """你是一个专业的声音设计提示词优化专家。用户会给你一段关于音色的描述，你需要将其优化为适合 CosyVoice 声音设计 API 的 voice_prompt。

优化规则：
1. 保留用户的核心意图（音色特征、性别、年龄、情绪、场景）
2. 用专业、简洁的语言描述音色特征（如：音色、音调、语速、情绪、风格）
3. 避免过于抽象或主观的描述（如“好听”、“有魅力”），用具体特征替代
4. 控制在 200 字符以内
5. 只输出优化后的 prompt，不要输出任何解释或前缀

示例：
- 用户输入：“你是KTV一姐林志玲，温柔，娇媚，听到你的声音就想下单和你买酒水。”
- 优化输出：“温柔娇媚的成熟女性，音调柔美清澈，语速舒缓，带有亲和力和感染力，适合酒水推销场景”

- 用户输入：“沉稳的中年男性播音员”
- 优化输出：“沉稳浑厚的中年男性，音色低沉有力，语速适中均匀，具有专业播音员的权威感和亲和力”"""

    try:
        # 使用标准 DashScope 端点（非 workspace 专属域名）
        api_key = os.getenv("DASHSCOPE_API_KEY_CN", "")
        resp = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "qwen3.7-max",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请优化以下声音描述：\n{user_prompt}"},
                ],
            },
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            optimized = data["choices"][0]["message"]["content"].strip()
            return f"✅ 优化完成\n\n原始：{user_prompt}\n\n优化后：{optimized}", optimized
        else:
            return f"❌ 优化失败 ({resp.status_code}): {resp.text[:200]}", user_prompt

    except Exception as e:
        return f"❌ 错误: {e}", user_prompt


def design_voice(voice_prompt, preview_text, prefix, language):
    """声音设计 —— 通过文字描述创建音色"""
    if not voice_prompt:
        return "❌ 请输入音色描述", "", None
    if not preview_text:
        preview_text = "你好，这是一段测试语音。"
    prefix = _sanitize_prefix(prefix)

    try:
        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": TARGET_MODEL,
                "voice_prompt": voice_prompt,
                "preview_text": preview_text,
                "prefix": prefix,
                "language_hints": [language],
            },
            "parameters": {
                "sample_rate": 24000,
                "response_format": "wav",
            },
        }
        resp = requests.post(
            f"{BASE_URL}/services/audio/tts/customization",
            json=payload,
            headers=HEADERS,
            timeout=120,
        )

        if resp.status_code != 200:
            return f"❌ API 错误 ({resp.status_code}): {resp.text}", "", None

        data = resp.json()
        output = data.get("output", {})
        voice_id = output.get("voice_id", "")
        rid = data.get("request_id", "")

        status_msg = f"✅ 声音设计完成\nRequest ID: {rid}\nVoice ID: {voice_id}"

        # 保存预览音频
        preview_path = None
        preview_audio = output.get("preview_audio", {})
        if preview_audio.get("data"):
            audio_bytes = base64.b64decode(preview_audio["data"])
            fmt = preview_audio.get("response_format", "wav")
            preview_path = tempfile.mktemp(suffix=f".{fmt}")
            with open(preview_path, "wb") as f:
                f.write(audio_bytes)
            status_msg += f"\n🎵 预览音频已生成"

        save_voice(voice_id, "design", prefix, {"voice_prompt": voice_prompt})
        return status_msg, voice_id, preview_path

    except Exception as e:
        return f"❌ 错误: {e}", "", None


def synthesize(voice_id, text, style_instruction):
    """语音合成 —— 使用指定音色合成语音，支持风格指令"""
    if not voice_id:
        return "❌ 请输入 Voice ID", None, ""
    if not text:
        return "❌ 请输入合成文本", None, ""

    try:
        # 构建 SpeechSynthesizer 参数
        synth_kwargs = {"model": TARGET_MODEL, "voice": voice_id}

        # 风格指令通过 instruction 参数传入（非文本拼接）
        instruction_text = ""
        if style_instruction and style_instruction.strip():
            instruction_text = style_instruction.strip()
            # 去掉可能的方括号包裹
            if instruction_text.startswith("[") and instruction_text.endswith("]"):
                instruction_text = instruction_text[1:-1]
            synth_kwargs["instruction"] = instruction_text

        synthesizer = SpeechSynthesizer(**synth_kwargs)
        audio_data = synthesizer.call(text)

        if not audio_data:
            return "❌ 合成失败：返回空音频", None, ""

        rid = synthesizer.get_last_request_id()
        delay = synthesizer.get_first_package_delay()

        out_path = tempfile.mktemp(suffix=".mp3")
        with open(out_path, "wb") as f:
            f.write(audio_data)

        # 上传到 OSS 并保存记录
        audio_url = ""
        try:
            audio_url = upload_to_oss(out_path)
            save_generated_audio(voice_id, text, audio_url)
        except Exception as e:
            audio_url = f"上传 OSS 失败: {e}"

        status = f"✅ 合成成功\nRequest ID: {rid}\n首包延迟: {delay}ms\n文件大小: {len(audio_data)} bytes"
        if instruction_text:
            status += f"\n风格指令: {instruction_text}"
        if audio_url and not audio_url.startswith("上传"):
            status += f"\nOSS: {audio_url[:60]}..."

        # 原始 JSON（调试用）
        raw_info = {
            "request_id": rid,
            "model": TARGET_MODEL,
            "voice_id": voice_id,
            "instruction": instruction_text or None,
            "text": text,
            "first_package_delay_ms": round(delay, 2),
            "file_size_bytes": len(audio_data),
            "audio_url": audio_url if audio_url and not audio_url.startswith("上传") else None,
        }
        raw_json = json.dumps(raw_info, ensure_ascii=False, indent=2)

        return status, out_path, raw_json

    except Exception as e:
        return f"❌ 错误: {e}", None, ""


def list_voices(prefix_filter):
    """查询音色列表"""
    try:
        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "list_voice",
                "page_size": 50,
                "page_index": 0,
            },
        }
        if prefix_filter:
            payload["input"]["prefix"] = prefix_filter

        resp = requests.post(
            f"{BASE_URL}/services/audio/tts/customization",
            json=payload,
            headers=HEADERS,
            timeout=30,
        )
        if resp.status_code != 200:
            return f"❌ API 错误 ({resp.status_code}): {resp.text}"

        data = resp.json()
        voice_list = data.get("output", {}).get("voice_list", [])

        if not voice_list:
            return "暂无自定义音色"

        lines = [f"共 {len(voice_list)} 个音色：\n"]
        for v in voice_list:
            vid = v.get("voice_id", "?")
            status = v.get("status", "?")
            created = v.get("gmt_create", "?")
            prompt = v.get("voice_prompt", "")
            preview = v.get("preview_text", "")
            lines.append(f"📌 {vid}")
            lines.append(f"   状态: {status} | 创建: {created}")
            if prompt:
                lines.append(f"   描述: {prompt[:60]}...")
            if preview:
                lines.append(f"   预览文本: {preview[:60]}...")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 错误: {e}"


def query_voice_detail(voice_id):
    """查询单个音色详情"""
    if not voice_id:
        return "❌ 请输入 Voice ID"
    try:
        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "query_voice",
                "voice_id": voice_id,
            },
        }
        resp = requests.post(
            f"{BASE_URL}/services/audio/tts/customization",
            json=payload,
            headers=HEADERS,
            timeout=30,
        )
        if resp.status_code != 200:
            return f"❌ API 错误 ({resp.status_code}): {resp.text}"

        data = resp.json()
        o = data.get("output", {})
        lines = [
            f"Voice ID: {o.get('voice_id', '?')}",
            f"状态: {o.get('status', '?')}",
            f"目标模型: {o.get('target_model', '?')}",
            f"创建时间: {o.get('gmt_create', '?')}",
            f"修改时间: {o.get('gmt_modified', '?')}",
        ]
        if o.get("voice_prompt"):
            lines.append(f"音色描述: {o['voice_prompt']}")
        if o.get("preview_text"):
            lines.append(f"预览文本: {o['preview_text']}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 错误: {e}"


def delete_voice(voice_id):
    """删除音色"""
    if not voice_id:
        return "❌ 请输入要删除的 Voice ID"
    try:
        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "delete_voice",
                "voice_id": voice_id,
            },
        }
        resp = requests.post(
            f"{BASE_URL}/services/audio/tts/customization",
            json=payload,
            headers=HEADERS,
            timeout=30,
        )
        if resp.status_code != 200:
            return f"❌ API 错误 ({resp.status_code}): {resp.text}"
        return f"✅ 已删除音色: {voice_id}"
    except Exception as e:
        return f"❌ 错误: {e}"


def asr_transcribe(audio_file, audio_url, model, use_standard_endpoint=False):
    """ASR 语音识别：支持本地文件上传或 URL。

    use_standard_endpoint=True 时临时切换到标准 DashScope 端点
    （workspace 专属域名仅支持 TTS 类 API，不支持 qwen-audio 等通用模型）。
    """
    from http import HTTPStatus
    from dashscope.audio.asr import Transcription

    if not model:
        model = "fun-asr"

    file_urls = []
    oss_url = ""

    # 优先使用本地文件（上传到 OSS）
    if audio_file is not None:
        try:
            oss_url = upload_to_oss(audio_file)
            file_urls.append(oss_url)
        except Exception as e:
            return "", f"❌ 文件上传 OSS 失败: {e}", "", "", None

    # 或使用 URL
    if audio_url and audio_url.strip():
        url = audio_url.strip()
        file_urls.append(url)
        if not oss_url:
            oss_url = url

    if not file_urls:
        return "", "❌ 请上传音频文件或提供音频 URL", "", "", None

    # 音频预览：如果有本地文件用它，否则下载 URL 到临时文件
    preview_path = audio_file
    if not preview_path and file_urls:
        try:
            resp = requests.get(file_urls[0], timeout=30)
            ext = ".mp3"
            if ".wav" in file_urls[0].lower():
                ext = ".wav"
            elif ".m4a" in file_urls[0].lower():
                ext = ".m4a"
            preview_path = tempfile.mktemp(suffix=ext)
            with open(preview_path, "wb") as f:
                f.write(resp.content)
        except Exception:
            preview_path = None

    # qwen-audio 等通用模型需走标准 DashScope 端点，调用期间临时切换
    original_base_url = dashscope.base_http_api_url
    if use_standard_endpoint:
        dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    try:
        task_response = Transcription.async_call(
            model=model,
            file_urls=file_urls,
        )

        request_id = task_response.request_id or ""
        task_id = task_response.output.task_id if hasattr(task_response, 'output') else ""

        transcribe_response = Transcription.wait(task=task_id)

        if transcribe_response.status_code == HTTPStatus.OK:
            result = transcribe_response.output
            all_text = []
            raw_json = ""

            # fun-asr 返回 results 列表，每项有 transcription_url
            if hasattr(result, 'results') and result.results:
                for i, r in enumerate(result.results):
                    # r 可能是 dict 或带属性的对象
                    transcription_url = ''
                    if isinstance(r, dict):
                        transcription_url = r.get('transcription_url', '')
                    else:
                        transcription_url = getattr(r, 'transcription_url', '') or ''

                    if transcription_url:
                        try:
                            resp = requests.get(transcription_url, timeout=30)
                            data = resp.json()
                            raw_json = json.dumps(data, ensure_ascii=False, indent=2)

                            # 解析 transcription 结果
                            transcripts = data.get('transcripts', [])
                            for t in transcripts:
                                text = t.get('text', '')
                                if text:
                                    all_text.append(text)

                            # 如果没有 transcripts，尝试 sentences
                            if not transcripts:
                                sentences = data.get('sentences', [])
                                if sentences:
                                    text = ' '.join(s.get('text', '') for s in sentences)
                                    all_text.append(text)
                        except Exception as e:
                            all_text.append(f"下载转写结果失败: {e}")

            text_result = "\n".join(all_text) if all_text else "(未识别到文本)"
            rid_display = request_id or task_id or "未知"
            return rid_display, text_result, raw_json, oss_url, preview_path
        else:
            return "", f"❌ 识别失败: {transcribe_response.status_code}\n{transcribe_response.output}", "", "", None

    except Exception as e:
        return "", f"❌ 错误: {e}", "", "", None
    finally:
        dashscope.base_http_api_url = original_base_url


def qwen_audio_asr_transcribe(audio_file, audio_url):
    """Qwen-Audio ASR：固定使用 qwen-audio-3.0-asr-flash-filetrans，走标准 DashScope 端点"""
    return asr_transcribe(audio_file, audio_url, QWEN_AUDIO_ASR_MODEL, use_standard_endpoint=True)


def qwen_audio_flash_asr_transcribe(audio_file, audio_url):
    """Qwen-Audio-3.0-ASR-Flash：同步多模态 HTTP 接口（不支持 SDK），
    走 workspace 专属域名 multimodal-generation/generation，音频支持 URL 或 Base64 Data URI。
    """
    file_url = ""
    oss_url = ""

    # 优先使用本地文件（上传 OSS 获取 URL，避免 Base64 超体积限制）
    if audio_file is not None:
        try:
            oss_url = upload_to_oss(audio_file)
            file_url = oss_url
        except Exception as e:
            return "", f"❌ 文件上传 OSS 失败: {e}", "", "", None

    if audio_url and audio_url.strip():
        url = audio_url.strip()
        if not file_url:
            file_url = url
        if not oss_url:
            oss_url = url

    if not file_url:
        return "", "❌ 请上传音频文件或提供音频 URL", "", "", None

    # 音频预览：如果有本地文件用它，否则下载 URL 到临时文件
    preview_path = audio_file
    if not preview_path:
        try:
            resp = requests.get(file_url, timeout=30)
            ext = ".mp3"
            if ".wav" in file_url.lower():
                ext = ".wav"
            elif ".m4a" in file_url.lower():
                ext = ".m4a"
            preview_path = tempfile.mktemp(suffix=ext)
            with open(preview_path, "wb") as f:
                f.write(resp.content)
        except Exception:
            preview_path = None

    # 根据文件扩展名推断音频格式
    lower_url = file_url.split("?")[0].lower()
    fmt = "mp3"
    if lower_url.endswith(".wav"):
        fmt = "wav"
    elif lower_url.endswith(".m4a"):
        fmt = "m4a"
    elif lower_url.endswith(".opus"):
        fmt = "opus"

    try:
        payload = {
            "model": QWEN_AUDIO_ASR_FLASH_MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {"data": file_url},
                            }
                        ],
                    }
                ]
            },
            "parameters": {
                "format": fmt,
                "sample_rate": "16000",
            },
        }
        resp = requests.post(
            f"{BASE_URL}/services/aigc/multimodal-generation/generation",
            json=payload,
            headers={**HEADERS, "X-DashScope-SSE": "disable"},
            timeout=120,
        )

        if resp.status_code != 200:
            return "", f"❌ API 错误 ({resp.status_code}): {resp.text[:500]}", "", "", None

        data = resp.json()
        raw_json = json.dumps(data, ensure_ascii=False, indent=2)
        text = data.get("output", {}).get("text", "")
        rid = data.get("request_id", "") or "未知"

        return rid, text or "(未识别到文本)", raw_json, oss_url, preview_path

    except Exception as e:
        return "", f"❌ 错误: {e}", "", "", None


# ============================================================
#  Gradio 界面
# ============================================================

CSS = """
.main-title { text-align: center; margin-bottom: 0; }
.sub-title  { text-align: center; color: #888; margin-top: 0; }
.mono textarea, .mono input {
    font-family: 'SF Mono', 'Menlo', 'Consolas', 'Courier New', monospace !important;
    font-size: 13px !important;
}
/* Markdown 中英文/数字/单位用等宽字体 */
.prose code {
    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace !important;
    background: rgba(0,0,0,0.06);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.9em;
}
"""

with gr.Blocks(title="TTS (CosyVoice v3.5-plus) & ASR (fun-asr / Qwen-Audio) Demo", css=CSS, theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """
        # 🎙️ TTS (CosyVoice v3.5-plus) & ASR (fun-asr / Qwen-Audio) Demo
        ### 声音复刻 · 声音设计 · 语音合成 · 语音识别
        """,
    )

    # ===== Tab 1: 声音复刻 =====
    with gr.Tab("🎤 声音复刻 Voice Cloning"):
        gr.Markdown(
            """
            **上传 10~20 秒清晰人声音频，即可克隆音色。**
            支持格式：`WAV` / `MP3` / `M4A`，`≤ 10MB`，采样率 `≥ 16kHz`。
            """
        )
        with gr.Row():
            with gr.Column():
                clone_prefix = gr.Textbox(
                    label="音色名称前缀",
                    value="myvoice",
                    info="仅英文字母+数字，最长 10 字符（中文/下划线/横线会被自动过滤）",
                )
                clone_url = gr.Textbox(
                    label="方式 1：音频 URL（公网可访问）",
                    placeholder="https://example.com/sample.wav",
                )
                clone_file = gr.Audio(
                    label="方式 2：本地上传 / 录音",
                    type="filepath",
                    sources=["upload", "microphone"],
                )
                clone_btn_url = gr.Button("🔗 通过 URL 创建音色", variant="primary")
                clone_btn_file = gr.Button("📁 通过上传文件创建音色", variant="primary")

            with gr.Column():
                clone_status = gr.Textbox(label="状态", lines=10, interactive=False)
                clone_voice_id = gr.Textbox(label="生成的 Voice ID（用于下方合成）", elem_classes=["mono"])

        clone_btn_url.click(
            clone_voice_url,
            inputs=[clone_url, clone_prefix],
            outputs=[clone_status, clone_voice_id],
        )
        clone_btn_file.click(
            clone_voice_file,
            inputs=[clone_file, clone_prefix],
            outputs=[clone_status, clone_voice_id],
        )

    # ===== Tab 2: 声音设计 =====
    with gr.Tab("🎨 声音设计 Voice Design"):
        gr.Markdown(
            """
            **用文字描述你想要的音色特征，AI 自动生成。**
            无需音频样本，仅支持中文和英文描述，最大 `500` 字符。
            """
        )
        with gr.Row():
            with gr.Column():
                design_prompt = gr.Textbox(
                    label="音色描述",
                    placeholder="例如：你是KTV一姐林志玲，温柔，娇媚，听到你的声音就想下单和你买酒水。",
                    lines=3,
                    info="最大 500 字符，支持中英文。描述不专业？点下方「AI 优化」自动改写",
                )
                with gr.Row():
                    optimize_btn = gr.Button("🤖 AI 优化提示词", variant="secondary", size="sm")
                    design_btn = gr.Button("✨ 创建设计音色", variant="primary", size="sm")
                optimize_status = gr.Textbox(
                    label="优化结果（确认后点「创建」）",
                    lines=3,
                    interactive=False,
                )
                design_preview_text = gr.Textbox(
                    label="预览文本（合成试听用）",
                    value="你好，欢迎使用声音设计功能，这是一段测试语音。",
                    info="最大 200 字符",
                )
                with gr.Row():
                    design_prefix = gr.Textbox(
                        label="音色名称前缀",
                        value="designed",
                        info="仅英文字母+数字，最长 10 字符（中文/下划线/横线会被自动过滤）",
                    )
                    design_lang = gr.Dropdown(
                        label="语言",
                        choices=["zh", "en"],
                        value="zh",
                    )

            with gr.Column():
                design_status = gr.Textbox(label="状态", lines=8, interactive=False)
                design_voice_id = gr.Textbox(label="生成的 Voice ID（用于下方合成）", elem_classes=["mono"])
                design_preview_audio = gr.Audio(label="预览音频", type="filepath")

        # AI 优化提示词：输出到 optimize_status 和 design_prompt（优化后的值回填）
        optimize_btn.click(
            optimize_voice_prompt,
            inputs=[design_prompt, design_lang],
            outputs=[optimize_status, design_prompt],
        )

        design_btn.click(
            design_voice,
            inputs=[design_prompt, design_preview_text, design_prefix, design_lang],
            outputs=[design_status, design_voice_id, design_preview_audio],
        )

    # ===== Tab 3: 语音合成 =====
    with gr.Tab("🔊 语音合成 TTS") as tts_tab:
        gr.Markdown(
            """
            **选择已保存的音色或手动输入 Voice ID，合成语音。**
            音色创建成功后会自动保存到 `output/voices.json`，下次可直接选用。
            """
        )
        with gr.Row():
            with gr.Column():
                tts_voice_dropdown = gr.Dropdown(
                    label="已保存的音色",
                    choices=get_voice_choices(),
                    value=None,
                    interactive=True,
                    info="从本地保存的音色中选择，自动填充 Voice ID",
                )
                tts_voice_id = gr.Textbox(
                    label="Voice ID（也可手动输入）",
                    placeholder="例如：cosyvoice-v3.5-plus-vc-myvoice-xxxxx",
                    elem_classes=["mono"],
                )
                tts_style = gr.Dropdown(
                    label="风格指令（可选，不改原文）",
                    choices=[
                        ("温暖亲切，像跟朋友聊天", "温暖亲切，语速自然舒缓，带有微笑感"),
                        ("专业播音，沉稳有力", "沉稳有力，语速适中均匀，具有专业播音的权威感"),
                        ("活泼欢快，声音上扬", "活泼欢快，声音上扬，充满活力和感染力"),
                        ("轻柔细语，安静温柔", "轻柔细语，安静温柔，像睡前故事的感觉"),
                        ("自信大气，商务正式", "自信大气，语速适中，商务正式风格"),
                        ("自定义...", ""),
                    ],
                    value=None,
                    interactive=True,
                    allow_custom_value=True,
                    info="通过 instruction 参数控制语音风格，原文不会被修改",
                )
                tts_text = gr.Textbox(
                    label="合成文本",
                    placeholder="请输入要合成的文本内容...",
                    lines=5,
                )
                tts_btn = gr.Button("🔊 合成语音", variant="primary")

            with gr.Column():
                tts_status = gr.Textbox(label="状态", lines=5, interactive=False)
                tts_audio = gr.Audio(label="合成结果", type="filepath")
                with gr.Accordion("原始 JSON（调试用）", open=False):
                    tts_raw_json = gr.Textbox(
                        label="",
                        lines=10,
                        interactive=False,
                        elem_classes=["mono"],
                        show_label=False,
                    )

        # Dropdown 选择后自动填充 Voice ID
        tts_voice_dropdown.change(
            fn=lambda x: x,
            inputs=[tts_voice_dropdown],
            outputs=[tts_voice_id],
        )

        tts_btn.click(
            synthesize,
            inputs=[tts_voice_id, tts_text, tts_style],
            outputs=[tts_status, tts_audio, tts_raw_json],
        )

        # 切换到 TTS Tab 时自动刷新音色下拉列表
        tts_tab.select(
            fn=lambda: gr.update(choices=get_voice_choices()),
            outputs=[tts_voice_dropdown],
        )

    # ===== Tab 4: 音色管理 =====
    with gr.Tab("📋 音色管理"):
        gr.Markdown("查询、查看详情、删除自定义音色。")

        with gr.Row():
            with gr.Column():
                list_prefix = gr.Textbox(label="按前缀筛选（可选）")
                list_btn = gr.Button("📋 查询音色列表")
                list_result = gr.Textbox(label="音色列表", lines=15, interactive=False, elem_classes=["mono"])

            with gr.Column():
                query_vid = gr.Textbox(label="查询详情的 Voice ID", elem_classes=["mono"])
                query_btn = gr.Button("🔍 查询详情")
                query_result = gr.Textbox(label="音色详情", lines=8, interactive=False, elem_classes=["mono"])

                del_vid = gr.Textbox(label="删除的 Voice ID", elem_classes=["mono"])
                del_btn = gr.Button("🗑️ 删除音色", variant="stop")
                del_result = gr.Textbox(label="删除结果", interactive=False, elem_classes=["mono"])

        list_btn.click(list_voices, inputs=[list_prefix], outputs=[list_result])
        query_btn.click(query_voice_detail, inputs=[query_vid], outputs=[query_result])
        del_btn.click(delete_voice, inputs=[del_vid], outputs=[del_result])

    # ===== Tab 5: ASR 语音识别 =====
    with gr.Tab("🎧 ASR 语音识别") as asr_tab:
        gr.Markdown(
            """
            **上传音频或输入音频 URL，识别为文字。**
            支持格式：`WAV` / `MP3` / `M4A` 等，本地文件会自动上传到 `OSS`。
            """
        )
        with gr.Row():
            with gr.Column():
                asr_model = gr.Dropdown(
                    label="ASR 模型",
                    choices=["fun-asr"],
                    value="fun-asr",
                )
                asr_file = gr.Audio(
                    label="方式 1：上传音频文件 / 录音",
                    type="filepath",
                    sources=["upload", "microphone"],
                )
                asr_audio_select = gr.Dropdown(
                    label="方式 2：选择 TTS 合成音频 或 手动输入 URL",
                    choices=get_audio_url_choices(),
                    value=None,
                    interactive=True,
                    allow_custom_value=True,
                    info="可从已保存的 TTS 合成音频中选择，也可直接输入任意公网 URL",
                )
                asr_url = gr.Textbox(
                    label="音频 URL",
                    placeholder="选择后自动填充，或手动输入 https://...",
                    elem_classes=["mono"],
                )
                asr_btn = gr.Button("🎧 开始识别", variant="primary")

            with gr.Column():
                asr_audio_preview = gr.Audio(
                    label="音频预览",
                    type="filepath",
                )
                asr_request_id = gr.Textbox(
                    label="Request ID",
                    interactive=False,
                    elem_classes=["mono"],
                )
                asr_result = gr.Textbox(
                    label="识别结果",
                    lines=6,
                    interactive=False,
                )
                with gr.Accordion("原始 JSON（调试用）", open=False):
                    asr_raw_json = gr.Textbox(
                        label="",
                        lines=10,
                        interactive=False,
                        elem_classes=["mono"],
                        show_label=False,
                    )
                asr_oss_url = gr.Textbox(
                    label="OSS 地址",
                    interactive=False,
                    elem_classes=["mono"],
                )

        asr_btn.click(
            asr_transcribe,
            inputs=[asr_file, asr_url, asr_model],
            outputs=[asr_request_id, asr_result, asr_raw_json, asr_oss_url, asr_audio_preview],
        )

        # 下拉选择后自动填充 URL 输入框
        asr_audio_select.change(
            fn=lambda x: x if x else "",
            inputs=[asr_audio_select],
            outputs=[asr_url],
        )

        # 切换到 ASR Tab 时刷新音频下拉列表
        asr_tab.select(
            fn=lambda: gr.update(choices=get_audio_url_choices()),
            outputs=[asr_audio_select],
        )

    # ===== Tab 6: Qwen-Audio ASR（后台模型 qwen-audio-3.0-asr-flash-filetrans）=====
    with gr.Tab("🎙️ Qwen-Audio ASR") as qwen_asr_tab:
        gr.Markdown(
            f"""
            **上传音频或输入音频 URL，识别为文字。后台模型：`{QWEN_AUDIO_ASR_MODEL}`**
            支持格式：`WAV` / `MP3` / `M4A` 等，本地文件会自动上传到 `OSS`。
            """
        )
        with gr.Row():
            with gr.Column():
                qwen_asr_model = gr.Dropdown(
                    label="ASR 模型",
                    choices=[QWEN_AUDIO_ASR_MODEL],
                    value=QWEN_AUDIO_ASR_MODEL,
                )
                qwen_asr_file = gr.Audio(
                    label="方式 1：上传音频文件 / 录音",
                    type="filepath",
                    sources=["upload", "microphone"],
                )
                qwen_asr_audio_select = gr.Dropdown(
                    label="方式 2：选择 TTS 合成音频 或 手动输入 URL",
                    choices=get_audio_url_choices(),
                    value=None,
                    interactive=True,
                    allow_custom_value=True,
                    info="可从已保存的 TTS 合成音频中选择，也可直接输入任意公网 URL",
                )
                qwen_asr_url = gr.Textbox(
                    label="音频 URL",
                    placeholder="选择后自动填充，或手动输入 https://...",
                    elem_classes=["mono"],
                )
                qwen_asr_btn = gr.Button("🎙️ 开始识别", variant="primary")

            with gr.Column():
                qwen_asr_audio_preview = gr.Audio(
                    label="音频预览",
                    type="filepath",
                )
                qwen_asr_request_id = gr.Textbox(
                    label="Request ID",
                    interactive=False,
                    elem_classes=["mono"],
                )
                qwen_asr_result = gr.Textbox(
                    label="识别结果",
                    lines=6,
                    interactive=False,
                )
                with gr.Accordion("原始 JSON（调试用）", open=False):
                    qwen_asr_raw_json = gr.Textbox(
                        label="",
                        lines=10,
                        interactive=False,
                        elem_classes=["mono"],
                        show_label=False,
                    )
                qwen_asr_oss_url = gr.Textbox(
                    label="OSS 地址",
                    interactive=False,
                    elem_classes=["mono"],
                )

        qwen_asr_btn.click(
            qwen_audio_asr_transcribe,
            inputs=[qwen_asr_file, qwen_asr_url],
            outputs=[qwen_asr_request_id, qwen_asr_result, qwen_asr_raw_json, qwen_asr_oss_url, qwen_asr_audio_preview],
        )

        # 下拉选择后自动填充 URL 输入框
        qwen_asr_audio_select.change(
            fn=lambda x: x if x else "",
            inputs=[qwen_asr_audio_select],
            outputs=[qwen_asr_url],
        )

        # 切换到 Qwen-Audio ASR Tab 时刷新音频下拉列表
        qwen_asr_tab.select(
            fn=lambda: gr.update(choices=get_audio_url_choices()),
            outputs=[qwen_asr_audio_select],
        )

    # ===== Tab 7: Qwen-Audio ASR Flash（后台模型 qwen-audio-3.0-asr-flash，同步多模态接口）=====
    with gr.Tab("⚡ Qwen-Audio ASR Flash") as flash_asr_tab:
        gr.Markdown(
            f"""
            **上传音频或输入音频 URL，识别为文字。后台模型：`{QWEN_AUDIO_ASR_FLASH_MODEL}`**
            同步调用（非异步 filetrans），支持格式：`WAV` / `MP3` / `M4A` 等，本地文件会自动上传到 `OSS`。
            """
        )
        with gr.Row():
            with gr.Column():
                flash_asr_model = gr.Dropdown(
                    label="ASR 模型",
                    choices=[QWEN_AUDIO_ASR_FLASH_MODEL],
                    value=QWEN_AUDIO_ASR_FLASH_MODEL,
                )
                flash_asr_file = gr.Audio(
                    label="方式 1：上传音频文件 / 录音",
                    type="filepath",
                    sources=["upload", "microphone"],
                )
                flash_asr_audio_select = gr.Dropdown(
                    label="方式 2：选择 TTS 合成音频 或 手动输入 URL",
                    choices=get_audio_url_choices(),
                    value=None,
                    interactive=True,
                    allow_custom_value=True,
                    info="可从已保存的 TTS 合成音频中选择，也可直接输入任意公网 URL",
                )
                flash_asr_url = gr.Textbox(
                    label="音频 URL",
                    placeholder="选择后自动填充，或手动输入 https://...",
                    elem_classes=["mono"],
                )
                flash_asr_btn = gr.Button("⚡ 开始识别", variant="primary")

            with gr.Column():
                flash_asr_audio_preview = gr.Audio(
                    label="音频预览",
                    type="filepath",
                )
                flash_asr_request_id = gr.Textbox(
                    label="Request ID",
                    interactive=False,
                    elem_classes=["mono"],
                )
                flash_asr_result = gr.Textbox(
                    label="识别结果",
                    lines=6,
                    interactive=False,
                )
                with gr.Accordion("原始 JSON（调试用）", open=False):
                    flash_asr_raw_json = gr.Textbox(
                        label="",
                        lines=10,
                        interactive=False,
                        elem_classes=["mono"],
                        show_label=False,
                    )
                flash_asr_oss_url = gr.Textbox(
                    label="OSS 地址",
                    interactive=False,
                    elem_classes=["mono"],
                )

        flash_asr_btn.click(
            qwen_audio_flash_asr_transcribe,
            inputs=[flash_asr_file, flash_asr_url],
            outputs=[flash_asr_request_id, flash_asr_result, flash_asr_raw_json, flash_asr_oss_url, flash_asr_audio_preview],
        )

        # 下拉选择后自动填充 URL 输入框
        flash_asr_audio_select.change(
            fn=lambda x: x if x else "",
            inputs=[flash_asr_audio_select],
            outputs=[flash_asr_url],
        )

        # 切换到 Flash ASR Tab 时刷新音频下拉列表
        flash_asr_tab.select(
            fn=lambda: gr.update(choices=get_audio_url_choices()),
            outputs=[flash_asr_audio_select],
        )


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
