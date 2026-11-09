"""
问答管线 — 检索 → 价格联网校验（条件触发）→ 流式生成 → 交付记录入库
"""

import asyncio
import logging
import time
from datetime import datetime

from . import fx, prompts, store
from .config import REPO_BROWSE_URL, get_llm_config
from .knowledge import get_index
from .llm import stream_chat
from .price_verifier import (
    audit_answer_prices,
    is_price_question,
    needs_model_clarify,
    verify_prices,
)

log = logging.getLogger("pipeline")

MAX_CHUNKS = 6          # 注入知识库片段数
CHUNK_CHARS = 1500       # 每个片段截断长度
MAX_HISTORY = 8          # 注入对话历史轮数（user+assistant 条数）

# 来源展示优先级：官方定价页 > 搜索旁证 > 知识库引用。
# 知识库仓库公开可核对，故 KB 引用也对客户展示（可点击 GitHub 链接自查）。
_KIND_ORDER = {"official": 0, "web": 1, "knowledge": 2}


def order_sources(sources: list[dict], limit: int = 10) -> list[dict]:
    """按可信度排序后截断，供前端展示（含知识库引用）。"""
    return sorted(sources, key=lambda s: _KIND_ORDER.get(s.get("kind"), 3))[:limit]


def _format_kb(chunks: list[dict]) -> str:
    """知识片段注入 prompt。不给模型文件路径（relpath），保持正文简洁；
    来源引用由系统以可点击的 GitHub 链接（sources 事件）统一展示给客户自查。"""
    if not chunks:
        return "（未检索到相关知识库片段）"
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"### 片段[{i}]（内部知识库资料）· {c['title']}\n{c['text'][:CHUNK_CHARS]}"
        )
    return "\n\n".join(parts)


async def stream_answer(
    question: str,
    history: list,
    session_id: str,
    client_ip: str = "",
    user_agent: str = "",
):
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
    price_audit = ""

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
    direct_text = ""
    price_q = is_price_question(question, history)
    if price_q and needs_model_clarify(question, history):
        # 问了价格却没说是哪个型号：反问一句，不猜型号、不联网、不报价。
        # 确定性分支（不调 LLM），既不会编数字，也不会先想一千多字再甩拒答话术。
        direct_text = prompts.MODEL_CLARIFY_TEXT
        price_status = "clarify"
    elif price_q:
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

    # ── 2.2 实时汇率（换算/折扣/成本测算类问题必须有当日汇率）──
    # 旧版本只能回「无法查询实时汇率」，用户只能自己报一个数（踩记录 id=225~230）。
    fx_info = None
    if not direct_text and fx.is_fx_question(question):
        given = fx.user_given_rate(question)
        if given:
            # 用户自报汇率优先：他可能在按某个成交价核算，拿实时价覆盖反而制造分歧
            fx_info = {
                "rate": given,
                "source": "用户提供",
                "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "stale": False,
            }
        else:
            yield {"type": "status", "stage": "verifying_fx", "message": "💱 获取实时汇率..."}
            fx_info = await fx.usd_cny()
            if fx_info:
                sources.append(
                    {
                        "title": f"实时汇率 1 USD = {fx_info['rate']} CNY · {fx_info['source']}",
                        "url": fx_info.get("page")
                        or "https://finance.sina.com.cn/money/forex/hq/USDCNY.shtml",
                        "kind": "web",
                    }
                )
                if fx.is_pure_rate_query(question):
                    # 只问汇率数字：直接回，不调 LLM（秒回且不会把 6.67 说成 7 点几）
                    direct_text = fx.direct_answer(fx_info)
            elif fx.is_pure_rate_query(question):
                direct_text = fx.no_source_answer()

    # 知识库仓库公开可核对：知识库引用也随来源展示给客户（可点击 GitHub 自查），
    # 与官方定价页/搜索来源一起按可信度排序。
    yield {"type": "sources", "sources": order_sources(sources)}

    parts: list[str] = []
    think_parts: list[str] = []
    cfg = get_llm_config()

    def persist(interrupted: bool) -> int:
        return store.insert_answer(
            session_id=session_id,
            question=question,
            answer="".join(parts),
            sources=sources,
            price_status=price_status,
            price_audit=price_audit,
            llm_model=cfg["model"],
            latency_ms=int((time.time() - t0) * 1000),
            thinking="".join(think_parts),
            client_ip=client_ip,
            user_agent=user_agent,
            interrupted=interrupted,
        )

    # ── 2.5 确定性直答（缺型号反问 / 纯汇率查询 / 汇率不可用）──
    if direct_text:
        stage_msg = "🤔 先确认是哪个模型..." if price_status == "clarify" else "💱 实时汇率已就绪..."
        yield {"type": "status", "stage": "direct", "message": stage_msg}
        parts.append(direct_text)
        yield {"type": "delta", "text": direct_text}
        answer_id = persist(False)
        yield {
            "type": "done",
            "answer_id": answer_id,
            "price_status": price_status,
            "price_audit": price_audit,
            "latency_ms": int((time.time() - t0) * 1000),
        }
        return

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
    if fx_info:
        user_content += f"## 实时汇率（USD/CNY，本次唯一可信汇率）\n{fx.evidence_md(fx_info)}\n\n"
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
    thinking = False

    try:
        async for kind, text in stream_chat(messages):
            if kind == "think":
                if not thinking:
                    thinking = True
                    yield {"type": "status", "stage": "thinking", "message": "🧠 模型思考中（过程实时显示）..."}
                think_parts.append(text)
                yield {"type": "think", "text": text}
            else:
                parts.append(text)
                yield {"type": "delta", "text": text}
    except (asyncio.CancelledError, GeneratorExit):
        # 客户点「停止」或直接关闭页面：uvicorn 取消任务，上游 LLM 流随之关闭（真省 token）。
        # 取消路径里不能再 await，只能同步写库；已生成部分仍入库存档并标记 interrupted，
        # 便于后台统计「哪些问题用户等不下去」。（无内容可存时直接跳过）
        if parts or think_parts:
            try:
                persist(True)
                log.info("用户中断，已保存部分回答：%d 字", len("".join(parts)))
            except Exception:
                log.exception("中断记录落库失败")
        raise
    except Exception as e:
        log.exception("LLM 流式生成失败")
        yield {"type": "error", "message": f"生成失败：{e}"}
        return

    # ── 5. 输出侧价格审计 + 交付记录入库 ──
    # 价格题：核对回答表格里的 $ 金额是否都来自官方证据，抄错/臆造则标记 mismatch。
    if price_q:
        official_md = price_ev.get("official_md", "") if price_ev else ""
        result = audit_answer_prices("".join(parts), official_md)
        if result["checked"]:
            price_audit = (
                "mismatch:" + "|".join(result["mismatched"])
                if result["mismatched"]
                else "ok"
            )
            if result["mismatched"]:
                log.warning(
                    "价格审计 mismatch：回答表格出现官方证据外的价格 %s",
                    result["mismatched"],
                )
    answer_id = persist(False)
    yield {
        "type": "done",
        "answer_id": answer_id,
        "price_status": price_status,
        "price_audit": price_audit,
        "latency_ms": int((time.time() - t0) * 1000),
    }
