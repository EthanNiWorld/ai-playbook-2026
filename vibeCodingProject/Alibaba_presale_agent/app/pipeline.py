"""
问答管线 — 检索 → 价格联网校验（条件触发）→ 流式生成 → 交付记录入库
"""

import logging
import time

from . import prompts, store
from .config import REPO_BROWSE_URL, get_llm_config
from .knowledge import get_index
from .llm import stream_chat
from .price_verifier import is_price_question, verify_prices

log = logging.getLogger("pipeline")

MAX_CHUNKS = 6          # 注入知识库片段数
CHUNK_CHARS = 1500       # 每个片段截断长度
MAX_HISTORY = 8          # 注入对话历史轮数（user+assistant 条数）


def _format_kb(chunks: list[dict]) -> str:
    """知识片段注入 prompt。不暴露文件路径（relpath）：模型看不到路径就不会在回答里复述，
    GitHub 文件引用仅随 sources 落库供后台追溯。"""
    if not chunks:
        return "（未检索到相关知识库片段）"
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"### 片段[{i}]（内部知识库资料）· {c['title']}\n{c['text'][:CHUNK_CHARS]}"
        )
    return "\n\n".join(parts)


async def stream_answer(question: str, history: list, session_id: str):
    """async generator，产出 SSE 事件 dict（server 层负责序列化）。

    事件类型：
      status   {stage: retrieving|verifying_price|answering, message}
      sources  {sources: [{title, url, kind}]}
      delta    {text}                        — 流式回答增量
      done     {answer_id, price_status, latency_ms}
      error    {message}
    """
    t0 = time.time()
    sources: list[dict] = []
    seen_urls: set[str] = set()
    price_status = ""

    # ── 1. 本地知识检索 ──
    yield {"type": "status", "stage": "retrieving", "message": "🔍 检索知识库..."}
    chunks = get_index().search(question, top_k=MAX_CHUNKS)
    for c in chunks:
        url = f"{REPO_BROWSE_URL}/blob/main/{c['relpath']}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append(
            {
                "title": f"{c['relpath']} · {c['title']}"[:90],
                "url": url,
                "kind": "knowledge",
            }
        )

    # ── 2. 价格联网校验（问题涉及价格才触发；追问场景靠历史回退识别）──
    price_ev = None
    if is_price_question(question, history):
        yield {"type": "status", "stage": "verifying_price", "message": "💰 联网核实官方定价..."}
        try:
            price_ev = await verify_prices(question, history)
            price_status = price_ev["status"]
            for s in price_ev["sources"]:
                if s["url"] and s["url"] not in seen_urls:
                    seen_urls.add(s["url"])
                    sources.append(s)
            yield {
                "type": "status",
                "stage": "price_verified",
                "message": f"✅ 价格证据已就绪（{price_status}，{int((time.time() - t0) * 1000)}ms）",
            }
        except Exception as e:
            log.exception("价格校验失败")
            price_status = "error"

    # 前端 sources 事件：知识库文件引用（GitHub 路径）仅落库供后台分析，不展示给客户；
    # 只推官方定价页/搜索来源
    visible_sources = [s for s in sources if s["kind"] != "knowledge"]
    yield {"type": "sources", "sources": visible_sources[:8]}

    # ── 3. 组装 prompt ──
    user_content = (
        "## 知识库片段（按相关度排序）\n" + _format_kb(chunks) + "\n\n"
    )
    if price_ev and price_ev.get("evidence_md"):
        user_content += (
            f"## 联网价格证据（实时核实 · 核实时间 {price_ev['checked_at']} · 状态 {price_status}）\n"
            f"{price_ev['evidence_md']}\n\n"
        )
    elif price_status:
        user_content += (
            "## 联网价格证据\n"
            "（本次未能联网核实到价格证据。若被问及具体价格，请明确说明暂无法核实，"
            f"并引导用户访问官方定价页：{prompts.OFFICIAL_PRICING_URL}）\n\n"
        )
    user_content += f"## 用户问题\n{question}"

    messages = [{"role": "system", "content": prompts.ANSWER_SYSTEM_PROMPT}]
    for h in history[-MAX_HISTORY:]:
        role = h.get("role")
        content = str(h.get("content", ""))[:4000]
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_content})

    # ── 4. 流式生成（思考过程实时推送，等待期可见进展）──
    yield {"type": "status", "stage": "answering", "message": "✍️ 生成回答..."}
    parts: list[str] = []
    thinking = False
    cfg = get_llm_config()
    try:
        async for kind, text in stream_chat(messages):
            if kind == "think":
                if not thinking:
                    thinking = True
                    yield {"type": "status", "stage": "thinking", "message": "🧠 模型思考中（过程实时显示）..."}
                yield {"type": "think", "text": text}
            else:
                parts.append(text)
                yield {"type": "delta", "text": text}
    except Exception as e:
        log.exception("LLM 流式生成失败")
        yield {"type": "error", "message": f"生成失败：{e}"}
        return

    # ── 5. 交付记录入库（供后台分析与迭代）──
    answer = "".join(parts)
    latency_ms = int((time.time() - t0) * 1000)
    answer_id = store.insert_answer(
        session_id=session_id,
        question=question,
        answer=answer,
        sources=sources,
        price_status=price_status,
        llm_model=cfg["model"],
        latency_ms=latency_ms,
    )
    yield {
        "type": "done",
        "answer_id": answer_id,
        "price_status": price_status,
        "latency_ms": latency_ms,
    }
