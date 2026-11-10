"""
问答管线 v3 — 检索 → 确定性快路径 → LLM 工具循环 → 流式生成 → 交付记录入库
================================================================
v3（2026-11-09）：意图路由（何时查价/查汇率/查竞品）从正则开关改为 LLM
function calling 自主决策。旧版每个路由开关都是手写正则，漏一种问法
不会报错、只会静默降级成模型凭记忆拼答案——正是泛化差与幻觉的根源。
不变量：
  - 数值层：价格/汇率数字仍只能来自工具证据（verify_price / get_fx_rate
    内部是确定性抓取 + 结构化抽取 + 代码渲染），输出侧 audit_answer_prices
    审计保留；
  - 确定性快路径：缺型号反问、纯汇率秒回保留在循环之前（出错成本趋零，
    收益是秒回且零幻觉）；
  - SSE 事件 schema 不变（status/sources/delta/think/done/error），
    server 与前端零改动；sources 事件可多次下发，前端覆盖渲染。
"""

import asyncio
import logging
import re
import time

from . import fx, prompts, store, tools
from .config import REPO_BROWSE_URL, get_llm_config
from .knowledge import get_index, search_with_models
from .llm import stream_chat
from .price_verifier import (
    _STOCK_CONTEXT_RE,
    audit_answer_prices,
    extract_model_names,
    is_price_question,
    needs_model_clarify,
)

log = logging.getLogger("pipeline")

# 领域关键词：命中任一即认为问题在业务范围内，需要检索资料。
# 背景（2026-11-10 实测）：爱情/股票等出界问题 BM25 仍会靠高频单字（"我说的是，伊
# 斯坦布尔有爱情么" → 我/的/爱/斯/坦/尔）召出 5~6 条无关片段并展示为参考来源；
# 而出界题与业务题的分数区间重叠（51 vs 45~103），分数阈值无法区分，只能域门控。
_DOMAIN_HINT_RE = re.compile(
    r"百炼|模型|智能体|agent|大模型|llm|api|token|上下文|推理|训练|微调|部署|"
    r"选型|benchmark|多模态|语音|tts|asr|视频|图像|生图|缓存|限流|并发|吞吐|"
    r"gpu|ecs|服务器|裸金属|网关|编排|框架|rag|embedding|工作流|计费|收费|"
    r"价格|多少钱|额度|配额|开源|权重|幻觉|私有|合规|备案|鉴权|密钥|阿里云|阿里|"
    r"混元|文心|豆包|hunyuan|kimi|glm|dashscope",
    re.IGNORECASE,
)


def is_domain_question(question: str, history: list | None = None) -> bool:
    """问题是否在百炼/阿里云 AI 业务范围内（决定是否检索资料）。

    股票/投资语境优先级高于领域关键词：句中无型号名但命中股票语境
    （股价/投资/PE 等）时不检索本地资料库、直接交给工具循环联网检索
    （“腾讯和阿里的股价对比”里的“阿里”是公司而非阿里云，本地 AI 资料
    帮不上忙，用户 2026-11-10 指示）；句中含型号名则仍按业务题检索
    （“qwen3.8-max 值得投资吗”是 AI 话题）。
    """

    if extract_model_names(question):
        return True
    if _STOCK_CONTEXT_RE.search(question or ""):
        return False

    def _hit(text: str) -> bool:
        return bool(
            text
            and (
                extract_model_names(text)
                or is_price_question(text)
                or fx.is_fx_question(text)
                or _DOMAIN_HINT_RE.search(text)
            )
        )

    if _hit(question):
        return True
    # 省略式追问（"它支持视觉吗"）本身无领域词，但历史里问过业务问题
    for h in (history or [])[-6:]:
        if h.get("role") == "user" and _hit(str(h.get("content", ""))[:300]):
            return True
    return False

MAX_CHUNKS = 6          # 注入知识库片段数
CHUNK_CHARS = 1500       # 每个片段截断长度
MAX_HISTORY = 8          # 注入对话历史轮数（user+assistant 条数）
MAX_TOOL_ROUNDS = 3      # 工具循环轮数上限（前 N-1 轮可调工具，最后一轮强制收尾）

# 来源展示优先级：官方定价页 > 搜索旁证 > 知识库引用。
# 知识库仓库公开可核对，故 KB 引用也对客户展示（可点击 GitHub 链接自查）。
_KIND_ORDER = {"official": 0, "web": 1, "knowledge": 2}


# 展示上限：参考来源区最多显示 3 条（官方 > 搜索 > 知识片段按可信度取前 3）。
# 截断只发生在推送给前端的列表，落库仍是全量（后台可追溯全部来源）。
_DISPLAY_SOURCE_LIMIT = 3


def order_sources(sources: list[dict], limit: int = _DISPLAY_SOURCE_LIMIT) -> list[dict]:
    """按可信度排序后截断，供前端展示（含知识引用）。"""
    return sorted(sources, key=lambda s: _KIND_ORDER.get(s.get("kind"), 3))[:limit]


def _format_kb(chunks: list[dict]) -> str:
    """知识片段注入 prompt。不给模型文件路径（relpath），保持正文简洁；
    来源引用由系统以可点击的 GitHub 链接（sources 事件）统一展示给客户自查。"""
    if not chunks:
        return "（未检索到相关资料片段）"
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"### 片段[{i}]（已整理的内部资料）· {c['title']}\n{c['text'][:CHUNK_CHARS]}"
        )
    return "\n\n".join(parts)


def _mm_user_content(text: str, images: list[str]) -> str | list[dict]:
    """把「文本 + 截图」组装成多模态 content blocks；无图时退回纯字符串
    （与历史消息的 str content 兼容，DashScope 两种写法均接受）。"""
    if not images:
        return text
    blocks: list[dict] = [
        {"type": "image_url", "image_url": {"url": img}} for img in images
    ]
    blocks.append({"type": "text", "text": text})
    return blocks


def _mm_history_content(content: object, max_chars: int = 4000) -> str | list:
    """历史消息 content 透传前的体量控制：str 照旧截断；list（含图片 blocks）
    保留图片块 + 文本块（历史重发截图，多轮追问“图里第二行”可见）；
    丢弃图片块会让追问失明，故不允许。文本块仍受 max_chars 约束。"""
    if not isinstance(content, list):
        return str(content)[:max_chars]
    out: list = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "image_url":
            out.append(item)
    text_total = 0
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            t = str(item.get("text", ""))
            if text_total >= max_chars:
                break
            out.append({"type": "text", "text": t[: max_chars - text_total]})
            text_total += len(t)
    return out if out else str(content)[:max_chars]


def _history_has_images(history: list) -> bool:
    """历史里是否有携带截图的 user 轮（多模态 blocks）：
    追问轮的快路径判定必须感知图片 —— 模型名可能写在截图里，文本正则看不到。"""
    for h in (history or [])[-MAX_HISTORY:]:
        if h.get("role") == "user" and isinstance(h.get("content"), list):
            if any(
                isinstance(it, dict) and it.get("type") == "image_url"
                for it in h["content"]
            ):
                return True
    return False


async def stream_answer(
    question: str,
    history: list,
    session_id: str,
    client_ip: str = "",
    user_agent: str = "",
    images: list[str] | None = None,
):
    """async generator，产出 SSE 事件 dict（server 层负责序列化）。

    images：可选截图/图片 data URL 列表（最多 4 张，server 层已校验格式与体量），
    与问题一起组装为多模态 content 发给 qwen3.8-max；随历史在后续轮重发
    （多轮追问“图里第二行多少钱”始终可见）。探针：tests/e2e/test_vision_probe.py。

    事件类型：
      status   {stage: retrieving|answering|thinking|tool|direct|verifying_fx, message}
      sources  {sources: [{title, url, kind}]}        — 可多次下发，前端覆盖渲染
      delta    {text}                        — 流式回答增量
      think    {text}                        — 思考过程增量（折叠展示）
      done     {answer_id, price_status, price_audit, latency_ms}
      error    {message}
    """
    t0 = time.time()
    images = list(images or [])
    # 纯图无文本时给占位问题，保证检索与快路径判定不炸
    question = (question or "").strip() or "[图片] 这张截图/图片是什么？请结合图片回答。"
    sources: list[dict] = []
    seen_urls: set[str] = set()
    price_status = ""
    price_audit = ""
    official_md = ""
    competitor_md = ""
    price_checked = False  # 是否调过 verify_price（决定输出侧审计）

    def add_source(s: dict) -> None:
        if s.get("url") and s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            sources.append(s)

    # ── 1. 本地知识检索（仅业务范围内问题：出界题（爱情/股票/寒暄）不注入
    # 无关片段，参考来源区也因此不再展示凭单字噪声匹配出来的假链接）──
    yield {"type": "status", "stage": "retrieving", "message": "🔍 检索资料..."}
    chunks = []
    if is_domain_question(question, history):
        chunks = search_with_models(
            question, extract_model_names(question), top_k=MAX_CHUNKS
        )
    for c in chunks:
        add_source(
            {
                "title": f"{c['relpath']} · {c['title']}"[:90],
                "url": f"{REPO_BROWSE_URL}/blob/main/{c['relpath']}",
                "kind": "knowledge",
            }
        )

    # ── 2. 确定性快路径（不经 LLM，秒回且零幻觉）──
    # 带截图（本轮或历史任一 user 轮）时跳过全部快路径：型号/数字可能写在图片里，
    # 文本正则看不到，反问或直答都会答非所问；交工具循环让模型看图自主决策
    # （模型发现真缺型号时会自己反问）。
    direct_text = ""
    if not images and not _history_has_images(history):
        # 汇率意图先判：换算类问题含“美元/美元价格词”时会误命中价格意图，
        # 若不先排除会把它劫持进缺型号反问（“1.65 美元是多少人民币”实测踩坑）。
        fx_q = fx.is_fx_question(question)
        # 2a. 纯汇率查询：只要一个数字，直接回（不调 LLM，秒回且不会抄错数）。
        if fx_q and fx.is_pure_rate_query(question):
            yield {"type": "status", "stage": "verifying_fx", "message": "💱 获取实时汇率..."}
            fx_info = await fx.usd_cny()
            if fx_info:
                direct_text = fx.direct_answer(fx_info)
                add_source(
                    {
                        "title": f"实时汇率 1 USD = {fx_info['rate']} CNY · {fx_info['source']}",
                        "url": fx_info.get("page")
                        or "https://finance.sina.com.cn/money/forex/hq/USDCNY.shtml",
                        "kind": "web",
                    }
                )
            else:
                direct_text = fx.no_source_answer()
        # 2b. 缺型号反问：价格意图明确但没说型号（快路径窄场景，见 is_price_question
        #     docstring）。确定性分支：不猜型号、不联网、不报价。换算类（fx_q）排除在外。
        elif (
            not fx_q
            and is_price_question(question, history)
            and needs_model_clarify(question, history)
        ):
            direct_text = prompts.MODEL_CLARIFY_TEXT
            price_status = "clarify"

    yield {"type": "sources", "sources": order_sources(sources)}

    parts: list[str] = []
    think_parts: list[str] = []
    cfg = get_llm_config()

    def persist(interrupted: bool) -> int:
        return store.insert_answer(
            session_id=session_id,
            question=("[图片] " * 0 + question) if not images else question + f"（附 {len(images)} 张截图）",
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

    # ── 3. LLM 工具循环：模型自主决定查价/查汇率/搜索 ──
    messages: list[dict] = [{"role": "system", "content": prompts.ANSWER_SYSTEM_PROMPT}]
    for h in history[-MAX_HISTORY:]:
        role = h.get("role")
        content = _mm_history_content(h.get("content", ""))
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append(
        {
            "role": "user",
            "content": _mm_user_content(
                "## 资料片段（按相关度排序）\n"
                + _format_kb(chunks)
                + f"\n\n## 用户问题\n{question}",
                images,
            ),
        }
    )

    yield {"type": "status", "stage": "answering", "message": "✍️ 生成回答..."}

    async def tool_loop():
        """工具循环主体。前 MAX_TOOL_ROUNDS-1 轮带工具；最后一轮强制收尾作答。
        循环由 tool_calls 非空驱动（不信 finish_reason）：某轮未产出工具调用
        即视为模型已作答完毕，正常收尾。所有轮的 text 都正常流式输出——
        模型在带工具轮也可能不调工具直接作答（能力题知识库够答时），丢弃
        会丢整段回答；探针已验证 qwen3.8-max 工具轮前无正文泄漏。"""
        nonlocal price_status, official_md, competitor_md, price_checked
        for rnd in range(MAX_TOOL_ROUNDS):
            use_tools = rnd < MAX_TOOL_ROUNDS - 1
            thinking = False
            tool_calls: list[dict] = []
            async for kind, text in stream_chat(
                messages, tools=tools.TOOLS if use_tools else None
            ):
                if kind == "think":
                    if not thinking:
                        thinking = True
                        yield {
                            "type": "status",
                            "stage": "thinking",
                            "message": "🧠 模型思考中（过程实时显示）...",
                        }
                    think_parts.append(text)
                    yield {"type": "think", "text": text}
                elif kind == "tool_calls":
                    tool_calls = text
                else:  # text：工具轮与收尾轮同样流式输出（见 docstring）
                    parts.append(text)
                    yield {"type": "delta", "text": text}
            if not tool_calls:
                return
            # 回填 assistant 工具调用消息 + 执行结果，进入下一轮
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": c["id"] or f"call_{i}",
                            "type": "function",
                            "function": {
                                "name": c["name"],
                                "arguments": c["arguments"] or "{}",
                            },
                        }
                        for i, c in enumerate(tool_calls)
                    ],
                }
            )
            for i, c in enumerate(tool_calls):
                yield {"type": "status", "stage": "tool", "message": tools.status_of(c["name"])}
                try:
                    result = await tools.execute_tool(c["name"], c["arguments"])
                except Exception as e:
                    log.exception("工具执行失败 %s", c["name"])
                    result = {"content": f"工具执行失败：{e}"}
                if "price_status" in result:
                    price_status = result["price_status"]
                    # 多模型问题会连调多次 verify_price（如 4 个型号各一次）：
                    # 证据必须累加，若用赋值覆盖，白名单只剩最后一次的证据，
                    # 其余型号的官方价会被审计误判 mismatch（id 72 实测事故）。
                    if result.get("official_md"):
                        official_md = (
                            official_md + "\n\n" + result["official_md"]
                            if official_md
                            else result["official_md"]
                        )
                    if result.get("competitor_md"):
                        competitor_md = (
                            competitor_md + "\n\n" + result["competitor_md"]
                            if competitor_md
                            else result["competitor_md"]
                        )
                    price_checked = True
                for s in result.get("sources", []):
                    add_source(s)
                yield {"type": "sources", "sources": order_sources(sources)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": c["id"] or f"call_{i}",
                        "content": result.get("content", ""),
                    }
                )
            yield {"type": "status", "stage": "answering", "message": "✍️ 整理证据，生成回答..."}

    try:
        async for ev in tool_loop():
            yield ev
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

    # ── 4. 输出侧价格审计 + 交付记录入库 ──
    # 调过 verify_price 才审计：核对回答表格里的 $ 金额是否都来自官方证据，
    # 抄错/臆造则标记 mismatch（前端「已联网核实」徽章只看 official，不能为抄错背书）。
    if price_checked:
        result = audit_answer_prices(
            "".join(parts), official_md, competitor_md, question
        )
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
