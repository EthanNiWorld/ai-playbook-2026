"""
视频中文配音转英文配音 Demo
===========================

功能
----
- 将视频中一个人的中文说话转换为英文配音
- 声音克隆：使用 CosyVoice 保留原说话人音色特征
- 交互形式：Gradio Web UI

用户输入
--------
1. 视频文件（MP4/MOV）
2. 纯人声 MP3（通过 vocalremover.org 提取，无背景音乐）
3. 阿里云百炼 API Key + 地域选择（默认国际站，可切国内站）

Pipeline
--------
1. 百炼临时上传 → 纯人声 MP3 获得 oss:// URL
2. fun-asr ASR → 带时间戳的中文句子列表
3. qwen-mt-plus 翻译 → 中文→英文（plus 档质量优于 flash）
4. CosyVoice 声音复刻 → 克隆原说话人音色（国际/国内站均支持）
5. CosyVoice v3-plus TTS → 英文语音合成 + 时长对齐（plus 档音质优于 flash）
6. ffmpeg 合成 → 替换视频音轨输出最终视频

配置
----
环境变量（可选，也可在 UI 中输入）:
  DASHSCOPE_API_KEY_INTL_AIGC - 国际站 API Key（默认）
  DASHSCOPE_API_KEY_CN_AIGC   - 国内站 API Key

运行
----
  python video_dubbing_zh2en.py

依赖
----
  pip install dashscope openai gradio requests
  系统需要安装 ffmpeg (brew install ffmpeg)

参考文档
--------
- 百炼临时上传: https://help.aliyun.com/zh/model-studio/get-temporary-file-url
- fun-asr SDK: https://help.aliyun.com/zh/model-studio/non-realtime-speech-recognition-user-guide
- CosyVoice 声音复刻: https://help.aliyun.com/zh/model-studio/voice-clone-design-python-sdk
- qwen-mt API: https://help.aliyun.com/zh/model-studio/machine-translation
"""

import os
import json
import time
import logging
import subprocess
import tempfile
import re
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Generator

import dashscope
from dashscope.audio.asr import Transcription
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer, AudioFormat
from openai import OpenAI
import gradio as gr
import requests
from http import HTTPStatus

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("video_dubbing")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
# 地域（百炼多地域接入点）
# - cn:   国内大陆站 (北京)
# - intl: 国际站（新加坡）
REGION_URLS = {
    "cn":   "https://dashscope.aliyuncs.com",
    "intl": "https://dashscope-intl.aliyuncs.com",
}
REGION_API_V1 = {k: f"{v}/api/v1" for k, v in REGION_URLS.items()}
REGION_COMPAT_URL = {k: f"{v}/compatible-mode/v1" for k, v in REGION_URLS.items()}

# 默认地域（用户要求）
DEFAULT_REGION = "intl"

DEFAULT_MT_MODEL = "qwen-mt-plus"
DEFAULT_TTS_MODEL = "cosyvoice-v3-plus"
DEFAULT_ASR_MODEL = "fun-asr"
MAX_VIDEO_DURATION_S = 300  # 5 分钟

# WebSocket 端点（与 base_http_api_url 不互通，必须显式指定）
REGION_WS_URL = {
    "cn":   "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
    "intl": "wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference",
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def sanitize_filename(filename: str) -> str:
    """
    将文件名转换为安全的 OSS 路径格式
    移除空格、方括号等特殊字符，只保留字母、数字、下划线、连字符和点
    """
    name, ext = os.path.splitext(filename)
    # 只保留安全字符
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    # 移除连续下划线
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')
    # 如果处理后为空，使用时间戳
    if not safe_name:
        safe_name = f"file_{int(time.time())}"
    return f"{safe_name}{ext}"


def oss_url_to_http(oss_url: str) -> str:
    """
    将 oss:// URL 转换为阿里云 OSS HTTP URL
    
    oss://dashscope-instant/xxx/xxx/file.mp3
    -> https://dashscope-instant.oss-cn-beijing.aliyuncs.com/xxx/xxx/file.mp3
    """
    if not oss_url.startswith("oss://"):
        return oss_url  # 已经是 HTTP URL
    
    # 解析 oss:// URL
    # 格式: oss://bucket-name/path/to/file
    oss_path = oss_url[6:]  # 移除 "oss://"
    parts = oss_path.split("/", 1)
    bucket = parts[0]
    object_path = parts[1] if len(parts) > 1 else ""
    
    # 构建 HTTP URL（使用北京地域的 OSS endpoint）
    http_url = f"https://{bucket}.oss-cn-beijing.aliyuncs.com/{object_path}"
    logger.info(f"OSS URL 转换: {oss_url} -> {http_url}")
    return http_url


def upload_to_dashscope(
    api_key: str,
    model_name: str,
    file_path: str,
    api_v1_url: str,
) -> str:
    """
    上传本地文件至百炼临时存储，返回 oss:// URL（有效期 48 小时）

    百炼文件上传与模型绑定：上传时指定的 model 必须与后续调用的模型一致。

    Args:
        api_key: DashScope API Key
        model_name: 绑定的模型名称（如 'fun-asr'、'cosyvoice-v3-plus'）
        file_path: 本地文件路径
        api_v1_url: 当前地域的 API v1 接入点

    Returns:
        oss:// 格式的临时 URL
    """
    logger.info(f"上传文件 {file_path} (绑定模型: {model_name}, endpoint: {api_v1_url})...")

    # 安全化文件名（移除空格、方括号等特殊字符）
    original_name = Path(file_path).name
    safe_name = sanitize_filename(original_name)
    
    # 如果文件名需要修改，创建临时副本
    upload_path = file_path
    if safe_name != original_name:
        temp_dir = tempfile.mkdtemp(prefix="upload_")
        upload_path = os.path.join(temp_dir, safe_name)
        shutil.copy2(file_path, upload_path)
        logger.info(f"文件名安全化: {original_name} -> {safe_name}")

    try:
        # Step 1: 获取上传凭证
        url = f"{api_v1_url}/uploads"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        params = {"action": "getPolicy", "model": model_name}

        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"获取上传凭证失败: {resp.status_code} {resp.text}")

        policy_data = resp.json()["data"]

        # Step 2: 上传文件到 OSS
        file_name = Path(upload_path).name
        key = f"{policy_data['upload_dir']}/{file_name}"

        with open(upload_path, "rb") as f:
            files = {
                "OSSAccessKeyId": (None, policy_data["oss_access_key_id"]),
                "Signature": (None, policy_data["signature"]),
                "policy": (None, policy_data["policy"]),
                "x-oss-object-acl": (None, policy_data["x_oss_object_acl"]),
                "x-oss-forbid-overwrite": (None, policy_data["x_oss_forbid_overwrite"]),
                "key": (None, key),
                "success_action_status": (None, "200"),
                "file": (file_name, f),
            }
            upload_resp = requests.post(policy_data["upload_host"], files=files)

        if upload_resp.status_code != 200:
            raise RuntimeError(f"文件上传 OSS 失败: {upload_resp.status_code} {upload_resp.text}")

        oss_url = f"oss://{key}"
        logger.info(f"上传成功: {oss_url}")
        return oss_url
    finally:
        # 清理临时文件
        if upload_path != file_path and os.path.exists(upload_path):
            shutil.rmtree(os.path.dirname(upload_path), ignore_errors=True)


def get_audio_duration(audio_path: str) -> float:
    """使用 ffprobe 获取音频时长（秒）"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def trim_audio(input_path: str, output_path: str, max_seconds: float = 15.0) -> str:
    """截取音频前 N 秒"""
    subprocess.run(
        [
            "ffmpeg", "-i", input_path,
            "-t", str(max_seconds),
            "-y", output_path,
        ],
        capture_output=True, check=True,
    )
    return output_path


# ---------------------------------------------------------------------------
# 核心 Pipeline
# ---------------------------------------------------------------------------
class VideoDubbingPipeline:
    """视频中文配音转英文配音 Pipeline"""

    def __init__(
        self,
        api_key: str,
        mt_model: str = DEFAULT_MT_MODEL,
        region: str = DEFAULT_REGION,
    ):
        if region not in REGION_URLS:
            raise ValueError(
                f"不支持的地域: {region}（仅支持 {list(REGION_URLS.keys())}）"
            )

        # API Key 预处理与校验
        api_key = (api_key or "").strip()
        if not api_key:
            raise ValueError("API Key 不能为空")
        try:
            api_key.encode("latin-1")
        except UnicodeEncodeError as e:
            raise ValueError(
                f"API Key 包含非 ASCII 字符（位置 {e.start}-{e.end}）。"
                "通常原因：复制时带入了中文标点/空格/换行。\n"
                "请在 API Key 输入框中重新粘贴，确保不包含中文标点、"
                "中英文空格或不可见字符。"
            ) from e
        if not api_key.startswith("sk-"):
            raise ValueError("API Key 格式不正确，应以 'sk-' 开头")

        self.api_key = api_key
        self.region = region
        self.mt_model = mt_model
        self.tts_model = DEFAULT_TTS_MODEL
        self.asr_model = DEFAULT_ASR_MODEL

        # 按地域选择接入点
        self.base_url = REGION_URLS[region]
        self.api_v1_url = REGION_API_V1[region]
        self.compat_url = REGION_COMPAT_URL[region]
        self.ws_url = REGION_WS_URL[region]

        # 配置 DashScope SDK
        dashscope.api_key = api_key
        dashscope.base_http_api_url = self.api_v1_url

        logger.info(
            f"Pipeline 初始化: region={region}, endpoint={self.base_url}, ws={self.ws_url}"
        )

    def run(
        self,
        video_path: str,
        vocal_mp3_path: str,
        progress_cb=None,
    ) -> Tuple[str, str, str]:
        """
        执行完整 Pipeline

        Args:
            video_path: 原始视频文件路径
            vocal_mp3_path: 纯人声 MP3 文件路径
            progress_cb: 进度回调函数 (step_msg: str) -> None

        Returns:
            (output_video_path, asr_text, translation_text)
        """
        work_dir = tempfile.mkdtemp(prefix="dubbing_")
        logger.info(f"工作目录: {work_dir}")

        def _progress(msg: str):
            logger.info(msg)
            if progress_cb:
                progress_cb(msg)

        # Step 1: 上传文件
        _progress("Step 1/6: 上传音频文件至百炼...")
        asr_url, voice_url, vocal_path = self._upload_files(vocal_mp3_path, work_dir)

        # Step 2: ASR 语音识别
        _progress("Step 2/6: 语音识别中（可能需要1-2分钟）...")
        sentences = self._run_asr(asr_url)
        asr_text = "\n".join(
            f"[{s['begin_time']/1000:.1f}s - {s['end_time']/1000:.1f}s] {s['text']}"
            for s in sentences
        )
        _progress(f"Step 2/6: 语音识别完成，共 {len(sentences)} 句")

        # Step 3: 翻译
        _progress("Step 3/6: 中译英翻译中...")
        sentences = self._translate(sentences)
        translation_text = "\n".join(
            f"{s['text']} → {s['text_en']}" for s in sentences
        )
        _progress("Step 3/6: 翻译完成")

        # Step 4: 声音复刻
        _progress("Step 4/6: 声音复刻中（可能需要30秒-2分钟）...")
        voice_id = self._clone_voice(voice_url, vocal_path)
        _progress(f"Step 4/6: 声音复刻完成，voice_id={voice_id}")

        # Step 5: 英文语音合成
        _progress("Step 5/6: 英文语音合成中...")
        sentences = self._synthesize(sentences, voice_id, work_dir)
        _progress("Step 5/6: 语音合成完成")

        # Step 6: 合成视频
        _progress("Step 6/6: 合成最终视频...")
        output_path = self._compose_video(video_path, sentences, work_dir)
        _progress("✅ 全部完成！")

        return output_path, asr_text, translation_text

    def _upload_files(self, vocal_mp3_path: str, work_dir: str) -> Tuple[str, str, str]:
        """
        Step 1: 上传纯人声 MP3 至百炼临时存储

        ASR 支持 oss:// URL（通过 X-DashScope-OssResourceResolve header）
        声音复刻需要 oss:// URL（通过 HTTP API + header）或 Base64

        Returns:
            (asr_oss_url, voice_oss_url, local_file_path)
        """
        # 为 ASR 上传（绑定 fun-asr），使用 oss:// URL
        asr_oss_url = upload_to_dashscope(
            self.api_key, self.asr_model, vocal_mp3_path, self.api_v1_url
        )

        # 为声音复刻上传（绑定 voice-enrollment），保留 oss:// URL
        voice_oss_url = upload_to_dashscope(
            self.api_key, "voice-enrollment", vocal_mp3_path, self.api_v1_url
        )

        return asr_oss_url, voice_oss_url, vocal_mp3_path

    def _run_asr(self, audio_url: str) -> List[Dict]:
        """
        Step 2: 调用 fun-asr 进行语音识别

        使用 HTTP API 直接调用，以支持 oss:// URL（需添加 X-DashScope-OssResourceResolve header）

        Returns:
            sentences 列表: [{text, begin_time, end_time}]
        """
        # 使用 HTTP API 直接调用，添加必要的 header
        submit_url = f"{self.api_v1_url}/services/audio/asr/transcription"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
            "X-DashScope-OssResourceResolve": "enable",  # 关键：解析 oss:// URL
        }
        payload = {
            "model": self.asr_model,
            "input": {
                "file_urls": [audio_url],
            },
            "parameters": {
                "language_hints": ["zh", "en"],
            },
        }

        logger.info(f"提交 ASR 任务: {audio_url}")
        submit_resp = requests.post(submit_url, headers=headers, json=payload)

        if submit_resp.status_code != 200:
            raise RuntimeError(
                f"ASR 任务提交失败: {submit_resp.status_code} {submit_resp.text}"
            )

        submit_data = submit_resp.json()
        task_id = submit_data.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"ASR 任务提交无 task_id: {submit_data}")

        logger.info(f"ASR 任务已提交: task_id={task_id}")

        # 等待任务完成（轮询）
        query_url = f"{self.api_v1_url}/tasks/{task_id}"
        max_wait = 180  # 最大等待 3 分钟
        waited = 0
        while waited < max_wait:
            time.sleep(3)
            waited += 3

            query_resp = requests.get(query_url, headers=headers)
            if query_resp.status_code != 200:
                logger.warning(f"查询 ASR 任务失败: {query_resp.status_code}")
                continue

            query_data = query_resp.json()
            task_status = query_data.get("output", {}).get("task_status", "")

            if task_status == "SUCCEEDED":
                logger.info("ASR 任务完成")
                break
            elif task_status == "FAILED":
                error_msg = query_data.get("output", {}).get("message", "未知错误")
                raise RuntimeError(f"ASR 任务失败: {error_msg}")

            logger.info(f"ASR 进行中... status={task_status}")

        if waited >= max_wait:
            raise RuntimeError("ASR 任务超时")

        # 解析结果
        results = query_data.get("output", {}).get("results", [])
        if not results:
            raise RuntimeError("ASR 未返回任何结果")

        # 检查 subtask_status
        first_result = results[0]
        subtask_status = first_result.get("subtask_status", "")
        if subtask_status == "FAILED":
            error_code = first_result.get("code", "未知")
            error_msg = first_result.get("message", "未知错误")
            raise RuntimeError(f"ASR 子任务失败: {error_code} - {error_msg}")

        transcription_url = first_result.get("transcription_url")
        if not transcription_url:
            raise RuntimeError(f"ASR 结果无 transcription_url: {first_result}")

        result_json = requests.get(transcription_url).json()

        # 解析句子及时间戳
        sentences = []
        transcripts = result_json.get("transcripts", [])
        for transcript in transcripts:
            for sentence in transcript.get("sentences", []):
                sentences.append({
                    "text": sentence["text"].strip(),
                    "begin_time": sentence["begin_time"],  # ms
                    "end_time": sentence["end_time"],      # ms
                })

        if not sentences:
            raise RuntimeError("ASR 识别结果为空，请检查音频文件")

        logger.info(f"ASR 识别完成: {len(sentences)} 句")
        return sentences

    def _translate(self, sentences: List[Dict]) -> List[Dict]:
        """
        Step 3: 使用 qwen-mt-plus 将中文翻译为英文（质量档）

        通过 OpenAI 兼容 API 调用，translation_options 通过 extra_body 传入
        """
        client = OpenAI(api_key=self.api_key, base_url=self.compat_url)

        for i, sent in enumerate(sentences):
            logger.info(f"翻译 [{i+1}/{len(sentences)}]: {sent['text'][:30]}...")
            try:
                completion = client.chat.completions.create(
                    model=self.mt_model,
                    messages=[{"role": "user", "content": sent["text"]}],
                    extra_body={
                        "translation_options": {
                            "source_lang": "Chinese",
                            "target_lang": "English",
                        }
                    },
                )
                sent["text_en"] = completion.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"翻译第 {i+1} 句失败: {e}")
                # 失败时使用原文（优雅降级）
                sent["text_en"] = sent["text"]

        logger.info("翻译完成")
        return sentences

    def _clone_voice(self, ref_audio_url: str, local_audio_path: str) -> str:
        """
        Step 4: 使用 CosyVoice 声音复刻

        使用 HTTP API 调用，传入 Base64 音频数据（因为 oss:// URL 不被支持）

        Args:
            ref_audio_url: 参考音频的 oss:// URL（备用）
            local_audio_path: 本地音频文件路径（用于读取 Base64）

        Returns:
            voice_id: 克隆音色 ID
        """
        # 读取音频文件并转为 Base64
        logger.info(f"读取音频文件: {local_audio_path}")
        with open(local_audio_path, "rb") as f:
            audio_data = f.read()
        
        # 检测 MIME 类型
        import mimetypes
        mime_type, _ = mimetypes.guess_type(local_audio_path)
        if not mime_type:
            mime_type = "audio/mpeg"  # 默认 MP3
        
        base64_data = audio_data.encode("base64") if hasattr(audio_data, 'encode') else audio_data
        # Python 3: 使用 base64 模块
        import base64
        base64_str = base64.b64encode(audio_data).decode("utf-8")
        
        data_url = f"data:{mime_type};base64,{base64_str}"
        logger.info(f"音频 Base64 编码完成，大小: {len(base64_str)} 字符")

        # 使用 HTTP API 调用声音复刻
        url = f"{self.api_v1_url}/services/audio/tts/customization"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": self.tts_model,
                "prefix": "dubdemo",
                "url": data_url,
                "language_hints": ["zh"],
            },
        }

        logger.info(f"提交声音复刻请求...")
        resp = requests.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(
                f"声音复刻失败: {resp.status_code} {resp.text}"
            )

        result = resp.json()
        voice_id = result.get("output", {}).get("voice_id")
        if not voice_id:
            raise RuntimeError(f"声音复刻无 voice_id: {result}")

        logger.info(f"声音复刻完成: voice_id={voice_id}")
        return voice_id

    @staticmethod
    def _escape_ssml(text: str) -> str:
        """
        转义 SSML/XML 特殊字符。

        阿里云百炼要求标签内文本的 & < > 必须转义。
        注意：不能把 " 替换为 &quot;，因为我们的用法是标签内的文本内容，
        不是属性值。
        """
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )

    def _build_ssml_long_text(self, sentences: List[Dict], break_ms: int = 300) -> str:
        """
        把多句英文拼成一段 SSML 长文本，句间插入 <break> 标记气口。

        优势（vs 旧版"每句独立 WS 合成"）：
        - 一次 WebSocket 调用 → 模型有完整上下文，韵律连贯
        - 显式 <break> → 句间停顿可预期，避免"PPT 翻页感"

        Args:
            sentences: 含 text_en 字段的句子列表
            break_ms: 句间停顿时长（毫秒），范围 [50, 10000]

        Returns:
            SSML 字符串，外层包 <speak>
        """
        parts = []
        for sent in sentences:
            text_en = (sent.get("text_en") or sent.get("text", "")).strip()
            if not text_en:
                continue
            text_en = self._escape_ssml(text_en)
            # 句末若无标点，补一个句号让模型自然停顿
            if not text_en.endswith((".", "!", "?", ":", ";")):
                text_en += "."
            parts.append(text_en)

        if not parts:
            return "<speak></speak>"

        inner = f'<break time="{break_ms}ms"/>'.join(parts)
        return f"<speak>{inner}</speak>"

    def _synthesize(
        self,
        sentences: List[Dict],
        voice_id: str,
        work_dir: str,
    ) -> List[Dict]:
        """
        Step 5: 合并多句为一段 SSML，一次性合成英文语音

        关键改动（路径 A 优化 vs 旧版"逐句合成"）：
        1. 多句合并为 1 段长文本（用 <break> 隔开），一次 WebSocket 调用
           → 模型拿到完整上下文，句间韵律连贯，解决"PPT 翻页感"
        2. 取消 atempo 硬拉
           → 旧版每句独立合成后用 atempo 强行变速对齐中文时长，会损伤
              韵律、让重音错位；新版只做整段微调（仅当英文明显长于视频时）
        3. ffmpeg loudnorm 响度归一
           → 多句合成后整体响度统一，避免拼接处音量跳
        4. 文本中可能出现的 XML 特殊字符（& < >）在拼 SSML 前先转义

        输出约定：句 0 携带整段音频路径（en_is_full_track=True），
                 其他句 en_audio_path=None。_compose_video 据此走整段模式。
        """
        if not sentences:
            return sentences

        # 1) 拼 SSML 长文本
        ssml_text = self._build_ssml_long_text(sentences)
        logger.info(
            f"Step 5: 合并 {len(sentences)} 句为一次合成，"
            f"SSML 长度 {len(ssml_text)} 字符"
        )
        logger.info(f"  SSML 预览: {ssml_text[:200]}...")

        # 2) 一次 WebSocket 合成（WAV 格式便于后续 ffmpeg 处理）
        try:
            synth = SpeechSynthesizer(
                model=self.tts_model,
                voice=voice_id,
                format=AudioFormat.WAV_22050HZ_MONO_16BIT,
                url=self.ws_url,
            )
            audio_data = synth.call(ssml_text)
        except Exception as e:
            logger.error(f"TTS 合并合成失败: {e}")
            for sent in sentences:
                sent["en_audio_path"] = None
            return sentences

        if not audio_data:
            logger.error("TTS 返回空音频")
            for sent in sentences:
                sent["en_audio_path"] = None
            return sentences

        # 3) 保存原始合成结果
        raw_audio_path = os.path.join(work_dir, "en_full_raw.wav")
        with open(raw_audio_path, "wb") as f:
            f.write(audio_data)
        raw_duration_s = get_audio_duration(raw_audio_path)
        logger.info(
            f"合并合成完成: {len(audio_data)} bytes, "
            f"时长 {raw_duration_s:.1f}s, "
            f"约 {raw_duration_s / max(len(sentences), 1):.1f}s/句"
        )

        # 4) 响度归一（EBU R128 标准，播客/影视常用目标）
        normalized_path = os.path.join(work_dir, "en_full_normalized.wav")
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-i", raw_audio_path,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", "22050", "-ac", "1",
                    "-y", normalized_path,
                ],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                logger.warning(
                    f"loudnorm 失败，使用原音频: {result.stderr[:200]}"
                )
                normalized_path = raw_audio_path
            else:
                logger.info("响度归一完成 (EBU R128 I=-16 LUFS)")
        except Exception as e:
            logger.warning(f"loudnorm 异常: {e}")
            normalized_path = raw_audio_path

        # 5) 整段音频填到句 0，标记"整段模式"（_compose_video 据此走新逻辑）
        sentences[0]["en_audio_path"] = normalized_path
        sentences[0]["en_is_full_track"] = True
        sentences[0]["en_full_duration_s"] = raw_duration_s
        for sent in sentences[1:]:
            sent["en_audio_path"] = None

        return sentences

    def _compose_video(
        self,
        video_path: str,
        sentences: List[Dict],
        work_dir: str,
    ) -> str:
        """
        Step 6: 使用 ffmpeg 合成最终视频

        新策略（路径 A 优化）：
        - 5 句已合并为一段连续音频，整段替换原视频音轨
        - 只在英文总长 > 视频总长 × 1.2 时才做整体 atempo 微调
          （v.s. 旧版每句独立硬拉，严重损伤韵律）
        - 视频比英文长没关系（会保留原视频结尾的静音/画面）

        向后兼容：如果某句 en_is_full_track=True，走新逻辑；
                 否则回落到旧的"逐句按时间戳拼接"逻辑。
        """
        output_path = os.path.join(work_dir, "output_dubbed.mp4")

        # 获取原视频时长
        video_duration = get_audio_duration(video_path)
        logger.info(f"视频时长: {video_duration:.1f}s")

        if len(sentences) == 0:
            raise RuntimeError("无可合成的句子")

        # 找主音轨（句 0 携带整段音频）
        full_sent = next((s for s in sentences if s.get("en_is_full_track")), None)

        if full_sent and full_sent.get("en_audio_path"):
            return self._compose_video_full_track(
                video_path, full_sent, video_duration, output_path,
            )

        # 回落：旧的逐句拼接模式（保留以兼容）
        return self._compose_video_legacy(
            video_path, sentences, video_duration, work_dir, output_path,
        )

    def _compose_video_full_track(
        self,
        video_path: str,
        full_sent: Dict,
        video_duration: float,
        output_path: str,
    ) -> str:
        """
        整段音轨模式（路径 A 新逻辑）：
        - 整段替换原视频音轨
        - 仅在英文明显长于视频时做整体 atempo 微调
        """
        en_audio_path = full_sent["en_audio_path"]
        en_duration = full_sent.get("en_full_duration_s", video_duration)

        logger.info(
            f"整段音轨模式: en={en_duration:.1f}s, video={video_duration:.1f}s, "
            f"比例={en_duration / max(video_duration, 0.01):.2f}"
        )

        final_audio = en_audio_path
        ratio = en_duration / max(video_duration, 0.01)

        # 策略分层（避免 atempo > 1.3x 损伤韵律）：
        # - ratio <= 1.0   ：英文比视频短，直接用
        # - ratio <= 1.3   ：温和 atempo（最多 1.3x，重音改变有限）
        # - ratio >  1.3   ：不加速（会严重损韵律），改为截断英文到视频时长
        #                     保留开头部分，保证视频始终有声音
        if ratio > 1.3:
            truncated_path = os.path.join(
                os.path.dirname(output_path), "en_full_truncated.wav"
            )
            subprocess.run(
                [
                    "ffmpeg", "-i", en_audio_path,
                    "-t", str(video_duration),
                    "-y", truncated_path,
                ],
                capture_output=True, check=True,
            )
            final_audio = truncated_path
            logger.warning(
                f"英文比视频长 {ratio:.2f}x（>1.3），不加速避免损伤韵律；"
                f"截断英文到 {video_duration:.1f}s（保留开头）"
            )
        elif ratio > 1.0:
            # 温和 atempo（最大 1.3x）
            filter_str = f"atempo={ratio:.4f}"
            adapted_path = os.path.join(
                os.path.dirname(output_path), "en_full_adapted.wav"
            )
            subprocess.run(
                [
                    "ffmpeg", "-i", en_audio_path,
                    "-filter:a", filter_str,
                    "-y", adapted_path,
                ],
                capture_output=True, check=True,
            )
            final_audio = adapted_path
            logger.info(
                f"英文比视频长 {ratio:.2%}，温和 atempo={ratio:.3f}（保持韵律）"
            )
        else:
            logger.info(
                f"英文 {en_duration:.1f}s 短于视频 {video_duration:.1f}s，"
                f"直接替换（视频尾部保留原静音）"
            )

        # ffmpeg 替换音轨（最简方式）
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", final_audio,
            "-map", "0:v:0",   # 视频流来自原视频
            "-map", "1:a:0",   # 音频流来自英文音轨
            "-c:v", "copy",    # 视频编码直接复制（不重压）
            "-c:a", "aac",     # 音频编码为 AAC
            "-shortest",       # 以最短流为准
            "-y", output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ffmpeg 错误: {result.stderr}")
            raise RuntimeError(f"ffmpeg 合成失败: {result.stderr[:500]}")

        logger.info(f"视频合成完成: {output_path}")
        return output_path

    def _compose_video_legacy(
        self,
        video_path: str,
        sentences: List[Dict],
        video_duration: float,
        work_dir: str,
        output_path: str,
    ) -> str:
        """
        旧版逐句拼接模式（保留兼容，未来可能删除）

        策略：
        1. 对每句英文音频添加 adelay 延迟到对应时间点
        2. 混合所有音频
        3. 替换原视频音轨
        """
        inputs = ["-i", video_path]  # input 0: 原视频
        filter_parts = []
        audio_inputs = []

        for i, sent in enumerate(sentences):
            audio_path = sent.get("en_audio_path")
            if not audio_path or not os.path.exists(audio_path):
                continue

            inputs.extend(["-i", audio_path])
            input_idx = i + 1  # 0 是视频

            # adelay: 延迟到 begin_time（毫秒）
            delay_ms = int(sent["begin_time"])
            filter_parts.append(
                f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},"
                f"apad=whole_dur={video_duration}[a{i}]"
            )
            audio_inputs.append(f"[a{i}]")

        if not audio_inputs:
            raise RuntimeError("无有效音频片段可合成")

        # 混合所有音频
        mix_str = "".join(audio_inputs)
        filter_parts.append(
            f"{mix_str}amix=inputs={len(audio_inputs)}:"
            f"duration=longest:normalize=0[aout]"
        )

        filter_complex = ";".join(filter_parts)

        # 最终 ffmpeg 命令
        cmd = [
            "ffmpeg",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v:0",     # 视频流来自原视频
            "-map", "[aout]",    # 音频流来自混合结果
            "-c:v", "copy",      # 视频编码直接复制
            "-c:a", "aac",       # 音频编码为 AAC
            "-shortest",
            "-y", output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ffmpeg 错误（完整）: {result.stderr}")
            raise RuntimeError(f"ffmpeg 合成失败: {result.stderr[:500]}")

        logger.info(f"视频合成完成（legacy 模式）: {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
def build_ui() -> gr.Blocks:
    """构建 Gradio Web UI"""

    with gr.Blocks(
        title="视频中文配音转英文配音",
    ) as demo:
        gr.Markdown(
            "# 🎬 视频中文配音转英文配音 Demo\n"
            "将视频中一个人的中文说话转换为英文配音，保留原说话人音色。\n\n"
            "**使用步骤**: 1️⃣ 去 [vocalremover.org](https://vocalremover.org) 提取纯人声MP3 → "
            "2️⃣ 上传视频和MP3 → 3️⃣ 点击转换\n\n"
            "> 💡 **CosyVoice v3-plus / qwen-mt-plus 在国际/国内站均可用**。"
            "若某能力调用失败，尝试切换地域或检查 API Key 权限。"
        )

        with gr.Row():
            region_input = gr.Radio(
                choices=[("🌏 国际站 (intl)", "intl"), ("🇨🇳 国内站 (cn)", "cn")],
                value=DEFAULT_REGION,
                label="百炼地域",
                scale=1,
            )
            api_key_input = gr.Textbox(
                label="阿里云百炼 API Key (AIGC)",
                type="password",
                placeholder=(
                    "国际站: sk-xxx (DASHSCOPE_API_KEY_INTL_AIGC)  /  "
                    "国内站: sk-xxx (DASHSCOPE_API_KEY_CN_AIGC)"
                ),
                value="",
                scale=2,
            )
            mt_model_input = gr.Dropdown(
                choices=["qwen-mt-plus", "qwen-mt-flash"],
                value="qwen-mt-plus",
                label="翻译模型（plus 档质量更优）",
                scale=1,
            )

        # 地域切换时自动从对应环境变量预填 API Key
        def _on_region_change(region):
            env_key = "DASHSCOPE_API_KEY_INTL_AIGC" if region == "intl" \
                else "DASHSCOPE_API_KEY_CN_AIGC"
            return gr.update(value=os.getenv(env_key, ""))

        region_input.change(
            fn=_on_region_change,
            inputs=[region_input],
            outputs=[api_key_input],
        )

        with gr.Row():
            video_input = gr.Video(label="上传视频文件 (MP4/MOV, ≤5分钟)")
            vocal_input = gr.Audio(
                label="上传纯人声 MP3 (从 vocalremover.org 提取)",
                type="filepath",
            )

        start_btn = gr.Button("🚀 开始转换", variant="primary", size="lg")

        # 进度展示
        progress_output = gr.Textbox(
            label="处理进度",
            interactive=False,
            lines=8,
        )

        # 中间结果
        with gr.Accordion("📝 中间结果（ASR + 翻译对照）", open=False):
            asr_output = gr.Textbox(
                label="ASR 语音识别结果",
                interactive=False,
                lines=6,
            )
            translation_output = gr.Textbox(
                label="中英翻译对照",
                interactive=False,
                lines=6,
            )

        # 输出
        video_output = gr.Video(label="🎉 英文配音视频")

        # --- 事件处理 ---

        def process_video(video_path, vocal_path, region, api_key, mt_model):
            """处理视频的主函数"""
            if not api_key:
                env_hint = (
                    "DASHSCOPE_API_KEY_INTL_AIGC" if region == "intl"
                    else "DASHSCOPE_API_KEY_CN_AIGC"
                )
                raise gr.Error(f"请输入 API Key（环境变量名: {env_hint}）")
            if not video_path:
                raise gr.Error("请上传视频文件")
            if not vocal_path:
                raise gr.Error("请上传纯人声 MP3 文件")

            progress_log = []

            def progress_cb(msg):
                progress_log.append(msg)

            pipeline = VideoDubbingPipeline(
                api_key=api_key,
                mt_model=mt_model,
                region=region,
            )

            try:
                output_video, asr_text, trans_text = pipeline.run(
                    video_path=video_path,
                    vocal_mp3_path=vocal_path,
                    progress_cb=progress_cb,
                )
                progress_log.append("✅ 处理完成！")
                return (
                    "\n".join(progress_log),
                    asr_text,
                    trans_text,
                    output_video,
                )
            except Exception as e:
                progress_log.append(f"❌ 错误: {str(e)}")
                logger.exception("Pipeline 执行失败")
                return (
                    "\n".join(progress_log),
                    "",
                    "",
                    None,
                )

        start_btn.click(
            fn=process_video,
            inputs=[video_input, vocal_input, region_input, api_key_input, mt_model_input],
            outputs=[progress_output, asr_output, translation_output, video_output],
        )

    return demo


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ui = build_ui()
    # Gradio 6.0: theme 参数需在 launch() 传入
    ui.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())
