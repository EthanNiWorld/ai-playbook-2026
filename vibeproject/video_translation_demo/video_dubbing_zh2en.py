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
3. 阿里云百炼大陆站 API Key

Pipeline
--------
1. 百炼临时上传 → 纯人声 MP3 获得 oss:// URL
2. fun-asr ASR → 带时间戳的中文句子列表
3. qwen-mt-flash 翻译 → 中文→英文
4. CosyVoice 声音复刻 → 克隆原说话人音色
5. CosyVoice TTS → 英文语音合成 + 时长对齐
6. ffmpeg 合成 → 替换视频音轨输出最终视频

配置
----
环境变量（可选，也可在 UI 中输入）:
  DASHSCOPE_API_KEY - 大陆站 API Key

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
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer
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
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_API_V1 = f"{DASHSCOPE_BASE_URL}/api/v1"
DASHSCOPE_COMPAT_URL = f"{DASHSCOPE_BASE_URL}/compatible-mode/v1"
DEFAULT_MT_MODEL = "qwen-mt-flash"
DEFAULT_TTS_MODEL = "cosyvoice-v3-flash"
DEFAULT_ASR_MODEL = "fun-asr"
MAX_VIDEO_DURATION_S = 300  # 5 分钟


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


def upload_to_dashscope(api_key: str, model_name: str, file_path: str) -> str:
    """
    上传本地文件至百炼临时存储，返回 oss:// URL（有效期 48 小时）

    百炼文件上传与模型绑定：上传时指定的 model 必须与后续调用的模型一致。

    Args:
        api_key: DashScope API Key
        model_name: 绑定的模型名称（如 'fun-asr'、'cosyvoice-v3-flash'）
        file_path: 本地文件路径

    Returns:
        oss:// 格式的临时 URL
    """
    logger.info(f"上传文件 {file_path} (绑定模型: {model_name})...")

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
        url = f"{DASHSCOPE_API_V1}/uploads"
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

    def __init__(self, api_key: str, mt_model: str = DEFAULT_MT_MODEL):
        self.api_key = api_key
        self.mt_model = mt_model
        self.tts_model = DEFAULT_TTS_MODEL
        self.asr_model = DEFAULT_ASR_MODEL

        # 配置 DashScope SDK
        dashscope.api_key = api_key
        dashscope.base_http_api_url = DASHSCOPE_API_V1

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
        asr_oss_url = upload_to_dashscope(self.api_key, self.asr_model, vocal_mp3_path)

        # 为声音复刻上传（绑定 voice-enrollment），保留 oss:// URL
        voice_oss_url = upload_to_dashscope(self.api_key, "voice-enrollment", vocal_mp3_path)

        return asr_oss_url, voice_oss_url, vocal_mp3_path

    def _run_asr(self, audio_url: str) -> List[Dict]:
        """
        Step 2: 调用 fun-asr 进行语音识别

        使用 HTTP API 直接调用，以支持 oss:// URL（需添加 X-DashScope-OssResourceResolve header）

        Returns:
            sentences 列表: [{text, begin_time, end_time}]
        """
        # 使用 HTTP API 直接调用，添加必要的 header
        submit_url = f"{DASHSCOPE_API_V1}/services/audio/asr/transcription"
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
        query_url = f"{DASHSCOPE_API_V1}/tasks/{task_id}"
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
        Step 3: 使用 qwen-mt-flash 将中文翻译为英文

        通过 OpenAI 兼容 API 调用，translation_options 通过 extra_body 传入
        """
        client = OpenAI(api_key=self.api_key, base_url=DASHSCOPE_COMPAT_URL)

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
        url = f"{DASHSCOPE_API_V1}/services/audio/tts/customization"
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

    def _synthesize(
        self,
        sentences: List[Dict],
        voice_id: str,
        work_dir: str,
    ) -> List[Dict]:
        """
        Step 5: 使用克隆音色合成英文语音 + 时长对齐

        使用 HTTP API 非流式合成（返回音频 URL），避免 WebSocket 连接问题

        对每句英文：
        1. 计算目标时长（原中文句子的时长）
        2. 调用 HTTP API 合成，下载返回的音频 URL
        3. 合成后用 ffmpeg atempo 微调时长对齐
        """
        tts_url = f"{DASHSCOPE_API_V1}/services/audio/tts/SpeechSynthesizer"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for i, sent in enumerate(sentences):
            logger.info(f"合成 [{i+1}/{len(sentences)}]: {sent['text_en'][:40]}...")

            # 计算目标时长（原中文句子时长）
            target_duration_s = (sent["end_time"] - sent["begin_time"]) / 1000.0

            # 根据英文文本长度估算 rate 参数
            # 基准：rate=1.0 时，平均每个英文字符约 0.08 秒（需根据实际调整）
            # 让 TTS 直接合成接近目标时长，减少 atempo 机械拉伸
            text_len = len(sent["text_en"])
            baseline_duration = text_len * 0.08  # 预估基准时长
            
            # 计算 rate：让合成时长匹配目标时长
            # rate = 基准时长 / 目标时长（clamp 到 API 支持范围 0.5~2.0）
            if target_duration_s > 0.5 and baseline_duration > 0.1:
                estimated_rate = baseline_duration / target_duration_s
                # clamp 到合理范围，避免极端值影响音质
                rate = max(0.6, min(1.5, estimated_rate))
            else:
                rate = 0.85  # 默认稍慢
            
            logger.info(f"目标时长: {target_duration_s:.1f}s, 文本长度: {text_len}, rate: {rate:.2f}")

            # 使用 HTTP API 合成（非流式，返回音频 URL）
            payload = {
                "model": self.tts_model,
                "input": {
                    "text": sent["text_en"],
                    "voice": voice_id,
                    "format": "mp3",
                    "language_hints": ["en"],
                    "rate": round(rate, 2),  # 动态语速
                    "instruction": "语速请保持自然流畅，语气从容。",
                },
            }

            resp = requests.post(tts_url, headers=headers, json=payload)

            if resp.status_code != 200:
                logger.warning(f"第 {i+1} 句 TTS 失败: {resp.status_code} {resp.text[:200]}")
                sent["en_audio_path"] = None
                continue

            result = resp.json()
            audio_url = result.get("output", {}).get("audio", {}).get("url")

            if not audio_url:
                logger.warning(f"第 {i+1} 句 TTS 无音频 URL: {result}")
                sent["en_audio_path"] = None
                continue

            # 下载音频文件
            logger.info(f"下载音频: {audio_url[:80]}...")
            audio_resp = requests.get(audio_url)
            if audio_resp.status_code != 200:
                logger.warning(f"第 {i+1} 句音频下载失败: {audio_resp.status_code}")
                sent["en_audio_path"] = None
                continue

            audio_data = audio_resp.content

            # 保存临时音频
            raw_audio_path = os.path.join(work_dir, f"en_raw_{i:04d}.mp3")
            with open(raw_audio_path, "wb") as f:
                f.write(audio_data)

            # 获取实际合成时长
            try:
                actual_duration_s = get_audio_duration(raw_audio_path)
            except Exception:
                actual_duration_s = target_duration_s  # 获取失败时跳过对齐

            # 时长对齐：使用 ffmpeg atempo 调整
            aligned_audio_path = os.path.join(work_dir, f"en_aligned_{i:04d}.mp3")

            if target_duration_s > 0.1 and actual_duration_s > 0.1:
                ratio = actual_duration_s / target_duration_s

                if 0.5 <= ratio <= 2.0:
                    # atempo 支持 0.5~2.0 范围
                    subprocess.run(
                        [
                            "ffmpeg", "-i", raw_audio_path,
                            "-filter:a", f"atempo={ratio:.4f}",
                            "-y", aligned_audio_path,
                        ],
                        capture_output=True, check=True,
                    )
                elif ratio > 2.0:
                    # 超出范围，链式 atempo
                    filters = []
                    remaining = ratio
                    while remaining > 2.0:
                        filters.append("atempo=2.0")
                        remaining /= 2.0
                    filters.append(f"atempo={remaining:.4f}")
                    filter_str = ",".join(filters)
                    subprocess.run(
                        [
                            "ffmpeg", "-i", raw_audio_path,
                            "-filter:a", filter_str,
                            "-y", aligned_audio_path,
                        ],
                        capture_output=True, check=True,
                    )
                else:
                    # ratio < 0.5，链式处理
                    filters = []
                    remaining = ratio
                    while remaining < 0.5:
                        filters.append("atempo=0.5")
                        remaining /= 0.5
                    filters.append(f"atempo={remaining:.4f}")
                    filter_str = ",".join(filters)
                    subprocess.run(
                        [
                            "ffmpeg", "-i", raw_audio_path,
                            "-filter:a", filter_str,
                            "-y", aligned_audio_path,
                        ],
                        capture_output=True, check=True,
                    )
            else:
                # 时长异常，直接使用原音频
                aligned_audio_path = raw_audio_path

            sent["en_audio_path"] = aligned_audio_path

        logger.info("语音合成完成")
        return sentences

    def _compose_video(
        self,
        video_path: str,
        sentences: List[Dict],
        work_dir: str,
    ) -> str:
        """
        Step 6: 使用 ffmpeg 合成最终视频

        策略：
        1. 获取原视频时长
        2. 生成静音底板（与视频等长）
        3. 对每句英文音频添加 adelay 延迟到对应时间点
        4. 混合所有音频
        5. 替换原视频音轨
        """
        output_path = os.path.join(work_dir, "output_dubbed.mp4")

        # 获取原视频时长
        video_duration = get_audio_duration(video_path)
        logger.info(f"视频时长: {video_duration:.1f}s")

        if len(sentences) == 0:
            raise RuntimeError("无可合成的句子")

        # 方案：使用 ffmpeg complex_filter 将所有音频片段按时间戳混合
        # 构建 ffmpeg 命令
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

        logger.info(f"ffmpeg 合成命令: {' '.join(cmd[:10])}...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"ffmpeg 错误: {result.stderr[:500]}")
            raise RuntimeError(f"ffmpeg 合成失败: {result.stderr[:200]}")

        logger.info(f"视频合成完成: {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
def build_ui() -> gr.Blocks:
    """构建 Gradio Web UI"""

    with gr.Blocks(
        title="视频中文配音转英文配音",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            "# 🎬 视频中文配音转英文配音 Demo\n"
            "将视频中一个人的中文说话转换为英文配音，保留原说话人音色。\n\n"
            "**使用步骤**: 1️⃣ 去 [vocalremover.org](https://vocalremover.org) 提取纯人声MP3 → "
            "2️⃣ 上传视频和MP3 → 3️⃣ 点击转换"
        )

        with gr.Row():
            api_key_input = gr.Textbox(
                label="阿里云百炼 API Key (AIGC)",
                type="password",
                placeholder="sk-xxx (需要CosyVoice权限)",
                value=os.getenv("DASHSCOPE_API_KEY_CN_AIGC", os.getenv("DASHSCOPE_API_KEY_CN", "")),
                scale=2,
            )
            mt_model_input = gr.Dropdown(
                choices=["qwen-mt-flash", "qwen-mt-plus"],
                value="qwen-mt-flash",
                label="翻译模型",
                scale=1,
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

        def process_video(video_path, vocal_path, api_key, mt_model):
            """处理视频的主函数"""
            if not api_key:
                raise gr.Error("请输入 API Key")
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
            inputs=[video_input, vocal_input, api_key_input, mt_model_input],
            outputs=[progress_output, asr_output, translation_output, video_output],
        )

    return demo


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860)
