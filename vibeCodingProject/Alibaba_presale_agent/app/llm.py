"""
LLM 客户端 — DashScope OpenAI 兼容协议，流式输出（正文 + 思考 + 工具调用）
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
    tools: list[dict] | None = None,
    temperature: float = 0.3,
    # 实测该端点 max_tokens 只约束正文不约束思考；近 7 天正文峰值 2306 字≈4000 token
    # 已贴近 4096 上限，长回答尾部存在静默截断风险（pipeline 不读 finish_reason
    # 无法感知），放宽到 8192。max_tokens 是上限非目标，短回答零成本。
    max_tokens: int = 8192,
    enable_thinking: bool = True,
):
    """流式生成，逐段 yield (kind, text)。

    kind = "think"（模型思考过程 reasoning_content）| "text"（正式回答正文）
         | "tool_calls"（工具调用请求，流末一次性产出）。

    思考过程只推给前端折叠展示；实测 qwen3.8-max 价格类问题思考约 200
    tokens（约 +2~3s），不会吃光 max_tokens。DashScope 兼容层对不支持
    thinking 的模型会忽略该参数，此时无 think 增量、正文不受影响。

    tool_calls 增量按 index 拼装为 [{id, name, arguments}]（探针
    tests/e2e/test_toolcall_probe.py 已验证 qwen3.8-max 下 enable_thinking
    与 tools 共存、回填 role:tool 消息可正常收尾作答）。是否进入工具
    循环由调用方以 tool_calls 非空判断——不信任 finish_reason（GLM 系列
    强制 tool_choice 下 finish_reason 返回 stop 的既有教训）。
    """
    cfg = get_llm_config()
    if not cfg["api_key"]:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用 LLM")
    client = _get_client()
    kwargs: dict = dict(
        model=cfg["model"],
        messages=messages,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"enable_thinking": enable_thinking},
    )
    if tools:
        kwargs["tools"] = tools
    stream = await client.chat.completions.create(**kwargs)
    tool_acc: dict[int, dict] = {}
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
        tcs = getattr(delta, "tool_calls", None)
        if tcs:
            for tc in tcs:
                acc = tool_acc.setdefault(
                    tc.index or 0, {"id": "", "name": "", "arguments": ""}
                )
                if tc.id:
                    acc["id"] += tc.id
                fn = tc.function
                if fn:
                    if fn.name:
                        acc["name"] += fn.name
                    if fn.arguments:
                        acc["arguments"] += fn.arguments
    if tool_acc:
        yield ("tool_calls", [tool_acc[i] for i in sorted(tool_acc)])
