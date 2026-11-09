"""
工具层 — function calling 工具 schema 与执行器
============================================
v3 工具循环架构（2026-11-09）：意图路由（何时查价/查汇率/查竞品）从
pipeline 正则开关改为 LLM function calling 自主决策。本模块只做两件事：
  1. TOOLS：OpenAI 格式工具 schema（描述写给模型看，决定它何时调用）
  2. execute_tool：执行调用，产出回填给 role:tool 消息的文本

数值层不变量不动：价格/汇率数字仍只能来自 price_verifier / fx 的确定性
证据链（官方页抓取 + 结构化抽取 + 代码渲染表格），模型永远拿不到
"自己联网报价"的能力；输出侧 audit_answer_prices 审计在 pipeline 保留。
"""

import json
import logging

from . import fx, price_verifier, share_card
from .searcher import web_search

log = logging.getLogger("tools")

# 竞品厂商白名单（schema enum 约束；与 price_verifier 的官方页/英文名映射对齐）
COMPETITORS = [
    "腾讯云混元",
    "火山引擎豆包",
    "百度智能云文心",
    "AWS Bedrock",
    "OpenAI",
    "Anthropic Claude",
    "Google Gemini",
    "DeepSeek 官方",
]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verify_price",
            "description": (
                "联网核实阿里云百炼模型的官方定价（Singapore/China (Beijing) 双节点 USD）。"
                "凡是涉及任何具体模型的价格/计费/多少钱的问题（含追问、对比），必须先调用本工具"
                "取得证据再回答，严禁凭记忆报价。用户追问上一轮价格表里的字段或节点"
                "（如「China (Beijing) 那行多少」「cache input 是什么」）时，对同一型号重新调用。"
                "跨云比价时填写 competitor 参数。"
                "仅适用于百炼在售模型（qwen/wan/deepseek/kimi/glm/cosyvoice 等）；"
                "Qoder/QoderWake/QwenWork 等席位订阅制产品不在百炼定价页，不要对它们调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "模型名，用户原话即可（口语写法如 kimi k3.1 pro、wan3.0 video 也能归一）",
                    },
                    "competitor": {
                        "type": "string",
                        "enum": COMPETITORS,
                        "description": "跨云比价时填对方厂商；只问阿里云自家价格则不填",
                    },
                },
                "required": ["model"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fx_rate",
            "description": (
                "获取 USD/CNY 实时汇率。仅当需要美元/人民币换算、折算、折扣测算，"
                "且用户没有自报汇率时调用。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_price_share_link",
            "description": (
                "生成一份可转发给客户的价格分享卡片链接（HTML，含官方定价与 TPM/RPM 限流信息，"
                "24 小时内有效）。仅在用户明确要求“生成链接/发我一个链接/可转发的报价页”时调用；"
                "普通价格问答（用户没要链接）不要调用。"
                "model 填用户所问的模型名（原话即可）；同一轮已调过 verify_price 时仍需本工具重新核实，"
                "因为卡片内容必须由代码从官方页重新抽取，不经模型转手。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "模型名，用户原话即可（口语写法也能归一）",
                    },
                },
                "required": ["model"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "联网搜索时效性信息（如竞品最新定价、新发布产品）。"
                "仅当资料片段与 verify_price 证据都不够时使用。"
                "query 用简短英文更容易命中海外定价页。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索词，简短为佳（≤100 字符）"}
                },
                "required": ["query"],
            },
        },
    },
]

# 工具执行时的前端状态提示（pipeline 转成 status 事件）
_TOOL_STATUS = {
    "verify_price": "💰 联网核实官方定价...",
    "get_fx_rate": "💱 获取实时汇率...",
    "make_price_share_link": "🔗 生成价格分享卡片...",
    "search_web": "🔍 联网搜索...",
}


def status_of(name: str) -> str:
    return _TOOL_STATUS.get(name, "⚙️ 执行工具...")


async def execute_tool(name: str, arguments: str) -> dict:
    """执行一次工具调用。

    返回：
        {
          "content":        回填给 role:tool 消息的文本（证据原文/说明），
          "sources":        [{title, url, kind}]（管线收集进来源面板），
          "price_status":   仅 verify_price：official | web | none，
          "official_md":    仅 verify_price：官方证据（输出侧审计白名单），
          "competitor_md":  仅 verify_price：竞品证据（审计白名单），
        }
    """
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        log.warning("工具参数解析失败 %s: %r", name, arguments[:200])
        return {"content": "工具参数不是合法 JSON，请修正参数后重试。"}

    if name == "verify_price":
        model = str(args.get("model", "")).strip()
        if not model:
            return {"content": "缺少 model 参数。请提供用户所问的模型名。"}
        competitor = str(args.get("competitor", "") or "").strip()
        if competitor not in COMPETITORS:
            competitor = ""
        try:
            ev = await price_verifier.verify_price_for(model, competitor)
        except Exception as e:
            log.exception("verify_price 执行失败")
            return {"content": f"价格核实失败（{e}）。请说明暂未能联网核实，"
                    f"并引导用户访问官方定价页：{price_verifier.PRICE_PAGE_URL}"}
        return {
            "content": ev["evidence_md"] or "未核实到该模型的官方定价。",
            "sources": ev["sources"],
            "price_status": ev["status"],
            "official_md": ev["official_md"],
            "competitor_md": ev["competitor_md"],
        }

    if name == "make_price_share_link":
        model = str(args.get("model", "")).strip()
        if not model:
            return {"content": "缺少 model 参数。请提供用户所问的模型名。"}
        try:
            r = await share_card.make_share_link(model)
        except Exception as e:
            log.exception("make_price_share_link 执行失败")
            return {"content": f"分享卡片生成失败（{e}）。请向用户致歉并说明稍后再试。"}
        if r.get("error"):
            return {"content": f"分享卡片生成失败：{r['error']}。请向用户说明并提供官方定价页链接。"}
        models = "、".join(r.get("models", []))
        return {
            "content": (
                f"分享卡片已生成（模型：{models}，有效期至 {r['expires_at']}）\n"
                f"链接（必须原样完整输出给用户，不要截断/改写/重新拼接）：\n{r['url']}"
            )
        }

    if name == "get_fx_rate":
        info = await fx.usd_cny()
        if info:
            src = {
                "title": f"实时汇率 1 USD = {info['rate']} CNY · {info['source']}",
                "url": info.get("page")
                or "https://finance.sina.com.cn/money/forex/hq/USDCNY.shtml",
                "kind": "web",
            }
            return {"content": fx.evidence_md(info), "sources": [src]}
        return {"content": fx.no_source_answer()}

    if name == "search_web":
        query = str(args.get("query", "")).strip()[:200]
        if not query:
            return {"content": "缺少 query 参数。"}
        results = await web_search(query, max_results=5, thinking_budget=1024)
        if not results:
            return {"content": "搜索无结果。"}
        lines = [
            f"- [{r.get('title', '')}]({r.get('url', '')}): {(r.get('snippet') or '')[:300]}"
            for r in results
            if (r.get("snippet") or "").strip()
        ]
        return {
            "content": (
                "搜索结果（第三方信源，可能过期，不得作为阿里云官方报价依据）：\n"
                + "\n".join(lines)
            ),
            "sources": [
                {
                    "title": (r.get("title") or "搜索结果")[:60],
                    "url": r.get("url", ""),
                    "kind": "web",
                }
                for r in results
                if r.get("url")
            ],
        }

    return {"content": f"未知工具 {name}。"}
