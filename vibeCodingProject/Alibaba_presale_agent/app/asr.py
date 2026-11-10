"""
ASR 语音识别 — qwen-audio-3.1-asr-flash（同步多模态 HTTP）
===========================================================
探针实测（2026-11-10，workspace ap-southeast-1 端点）：
qwen-audio-3.1-asr-flash 与 qwen-audio-3.0-asr-flash 均 200，
16kHz mono WAV Base64 Data URI 输入，output.text 返回转写文本；
3.1 的标点质量更好（问句正确带？）。

调用协议（知识库 alibaba-ai-hub/maas/qwen-audio-asr.md）：
- flash 系列只支持同步多模态 HTTP，不支持 SDK 与异步 filetrans；
- POST {base}/api/v1/services/aigc/multimodal-generation/generation
  （base 由 DASHSCOPE_BASE_URL 的 compatible-mode/v1 换 api/v1 推导）；
- 音频经 input.messages[].content[].input_audio.data 传
  data:audio/wav;base64,...，parameters 带 format 与 sample_rate；
- ≤5 分钟 / ≤10MB（前端限制 60s，天然满足）。
"""

import logging

import httpx

from .config import get_llm_config

log = logging.getLogger("asr")

# 3.1 为主（用户指定），3.0 兜底（规格/地域万一未覆盖时降级）
ASR_MODELS = ["qwen-audio-3.1-asr-flash", "qwen-audio-3.0-asr-flash"]
_TIMEOUT_S = 60.0


def _generation_endpoint() -> str:
    """LLM 的 compatible-mode/v1 base_url → 多模态 generation 端点。

    两种形态都推导得到 .../api/v1/services/aigc/multimodal-generation/generation：
    workspace 专属域名（https://llm-xxx.<region>.maas.aliyuncs.com/compatible-mode/v1）
    与标准域名（https://dashscope.aliyuncs.com/compatible-mode/v1）。
    """
    base = get_llm_config()["base_url"].rstrip("/")
    if base.endswith("/compatible-mode/v1"):
        base = base[: -len("/compatible-mode/v1")]
    elif base.endswith("/compatible-mode"):
        base = base[: -len("/compatible-mode")]
    return base.rstrip("/") + "/api/v1/services/aigc/multimodal-generation/generation"


def build_payload(model: str, audio_b64: str, context: str = "") -> dict:
    """构造 multimodal-generation 请求体（供离线单测断言）。

    context 为上一段已识别文本（实时分段识别时传入，≤400 字符）：
    qwen-audio ASR 支持「上下文增强」——携带历史文本消息提升跨段
    连续性（实测协议被接受，含音频的 user 消息必须置末）。
    """
    messages = []
    if context and context.strip():
        messages.append(
            {"role": "assistant", "content": [{"text": context.strip()[:400]}]}
        )
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "input_audio": {
                        "data": f"data:audio/wav;base64,{audio_b64}",
                        "format": "wav",
                    }
                }
            ],
        }
    )
    return {
        "model": model,
        "input": {"messages": messages},
        "parameters": {"format": "wav", "sample_rate": 16000},
    }


async def transcribe(audio_b64: str, context: str = "") -> dict:
    """WAV（16kHz mono）Base64 → 文本。

    context：实时分段识别时传上一段已识别文本（上下文增强，≤400 字符）。
    返回 {"text": str, "model": str} 或 {"error": str}（错误信息可直接展示给前端）。
    """
    cfg = get_llm_config()
    if not cfg["api_key"]:
        return {"error": "未配置 API Key，无法识别语音"}
    if not audio_b64:
        return {"error": "音频为空"}
    # 容忍 dataURL 前缀
    if "," in audio_b64 and audio_b64.strip().startswith("data:"):
        audio_b64 = audio_b64.split(",", 1)[1]
    endpoint = _generation_endpoint()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
        "X-DashScope-SSE": "disable",
    }
    last_err = ""
    for model in ASR_MODELS:
        payload = build_payload(model, audio_b64, context)
        try:
            r = await _post(endpoint, headers, payload)
        except Exception as e:
            last_err = str(e)[:200]
            log.warning("ASR 请求失败 %s: %s", model, last_err)
            continue
        if r.status_code == 200:
            text = (r.json().get("output") or {}).get("text") or ""
            return {"text": text.strip(), "model": model}
        # 400 + ASR_RESPONSE_HAVE_NO_WORDS：音频里没有可识别的词（静音/噪声），
        # 不是链路故障——返回空文本让前端提示"没有识别到内容"而非"识别失败"
        # （线上实测：正弦波探针即此错误，注意错误码在 message 字段而非 code 字段）。
        try:
            _j = r.json()
            _msg = (_j.get("code") or "") + " " + (_j.get("message") or "")
        except Exception:
            _msg = ""
        if r.status_code == 400 and "NO_WORDS" in _msg:
            return {"text": "", "model": model}
        body = r.text[:200]
        last_err = f"HTTP {r.status_code}: {body}"
        log.warning("ASR %s 失败: %s", model, last_err)
    return {"error": f"语音识别失败（{last_err}），请重试或改用键盘输入"}


async def _post(endpoint: str, headers: dict, payload: dict):
    async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
        return await client.post(endpoint, headers=headers, json=payload)
