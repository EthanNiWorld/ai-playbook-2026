"""
LLM 客户端 — DashScope OpenAI 兼容协议，流式输出（正文 + 思考过程）
"""

import logging

from openai import AsyncOpenAI

from .config import get_llm_config

log = logging.getLogger("llm")

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        cfg = get_llm_config()
        _client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    return _client


async def stream_chat(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 4096,
    enable_thinking: bool = True,
):
    """流式生成，逐段 yield (kind, text)。

    kind = "think"（模型思考过程 reasoning_content）| "text"（正式回答正文）。
    思考过程只推给前端折叠展示、不落库；实测 qwen3.8-max 价格类问题思考
    约 200 tokens（约 +2~3s），不会吃光 max_tokens。DashScope 兼容层对
    不支持 thinking 的模型会忽略该参数，此时无 think 增量、正文不受影响。
    """
    cfg = get_llm_config()
    if not cfg["api_key"]:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用 LLM")
    client = _get_client()
    stream = await client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"enable_thinking": enable_thinking},
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            yield ("think", reasoning)
        if delta.content:
            yield ("text", delta.content)
