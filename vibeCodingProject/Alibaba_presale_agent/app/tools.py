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
from datetime import datetime

from . import fx, price_verifier, rate_limits, share_card, tpm_calc
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
            "name": "get_model_rate_limit",
            "description": (
                "联网查询阿里云百炼官方限流页，获取视频生成/图像生成模型的 RPM、RPS 与最大并发数。"
                "只要用户问视频模型或生图模型的 RPM、RPS、并发数、限流、配额、"
                "同时能跑几个任务（如「wan3.0 并发多少」「qwen-image-3.0-pro 每分钟几次」），"
                "必须先调用本工具拿官方表格，严禁凭记忆或资料片段回答。"
                "价格问题仍用 verify_price；价格与限流同时问时可并行调用两个工具。"
                "用户没说具体型号时，用 category 指定 video 或 image；说了型号就填 model。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "型号，用户原话即可（如 wan3.0-video-prime、qwen-image-3.0-pro）；未指定可留空",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["video", "image"],
                        "description": "未指定具体型号时必填：video=视频生成，image=图像生成",
                    },
                    "region": {
                        "type": "string",
                        "description": "可选地域（如 新加坡、北京、美国）；用户未指定则不填",
                    },
                },
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
            "name": "get_current_time",
            "description": (
                "获取服务器当前日期时间（含星期与时区）。凡回答涉及『今天/现在/最新"
                "能不能查到、数据是不是最新、财报发布没发布』等时效判断，"
                "或需要给回答标注数据时点时，先调用本工具再下结论；"
                "禁止凭检索结果推断当前日期。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_tpm_cost",
            "description": (
                "测算 auto TPM 模型（动态限流）的日成本或所需 TPM（基于新加坡官方定价）。"
                "两类问法：①用户给预算问容量（“每天预算 X 美元/人民币需要多少 TPM”）→ "
                "传 daily_cost_usd（人民币先按汇率换算）；②用户给 TPM 问成本"
                "（“2000 万 TPM 一天多少钱”）→ 传 tpm（单位 tokens/min）。"
                "都不传时按默认顶格 2000 万 TPM 正算。适用于 qwen3.8 系列/"
                "deepseek-v4/kimi-k3/glm-5.3 等动态限流模型的容量规划。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "模型名，用户原话即可（如 qwen3.8-flash）",
                    },
                    "tpm": {
                        "type": "number",
                        "description": "正算：TPM 限额（tokens/min），如 20000000 = 2000万",
                    },
                    "daily_cost_usd": {
                        "type": "number",
                        "description": "反算：日预算（USD），与 tpm 二选一",
                    },
                    "daily_cost_cny": {
                        "type": "number",
                        "description": "反算：日预算（人民币，工具内自动按 6.67 折算）",
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
    "get_model_rate_limit": "📈 查询官方限流与并发...",
    "get_fx_rate": "💱 获取实时汇率...",
    "make_price_share_link": "🔗 生成价格分享卡片...",
    "get_current_time": "🕒 获取当前时间...",
    "estimate_tpm_cost": "📊 TPM/成本测算...",
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

    if name == "get_model_rate_limit":
        model = str(args.get("model", "") or "").strip()
        category = str(args.get("category", "") or "").strip().lower()
        region = str(args.get("region", "") or "").strip()
        if category not in ("", "video", "image"):
            category = ""
        if not model and not category:
            return {"content": "缺少 model 或 category 参数。请提供用户所问的型号，或指定 video/image 类别。"}
        try:
            return await rate_limits.get_rate_limits(
                model=model, category=category, region=region
            )
        except Exception as e:
            log.exception("get_model_rate_limit 执行失败")
            return {
                "content": (
                    f"官方限流查询失败（{e}）。请勿猜测 RPM/并发数，"
                    f"引导用户打开官方限流页：{rate_limits.RATE_LIMIT_PAGE_URL}"
                )
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

    if name == "get_current_time":
        now = datetime.now().astimezone()
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        content = (
            f"当前时间：{now.strftime('%Y-%m-%d %H:%M')} （星期{weekdays[now.weekday()]}，"
            f"时区 {now.tzname() or 'UTC' + now.strftime('%z')}）\n"
            "时效判断提示：财经/行情/财报类检索结果若未带日期戳，应结合当前日期"
            "声明『数据为检索时点的最新公开口径，具体时点以来源页为准』，不得断言为实时。"
        )
        return {"content": content}

    if name == "estimate_tpm_cost":
        model = str(args.get("model", "")).strip()
        if not model:
            return {"content": "缺少 model 参数。请提供用户所问的模型名。"}
        tpm = args.get("tpm")
        daily_usd = args.get("daily_cost_usd")
        daily_cny = args.get("daily_cost_cny")
        if daily_cny and not daily_usd:
            info = await fx.usd_cny()
            rate = info["rate"] if info else fx._RATE_FALLBACK if hasattr(fx, "_RATE_FALLBACK") else 6.67
            daily_usd = round(daily_cny / rate, 2)
        try:
            r = await tpm_calc.estimate(
                model,
                tpm=int(tpm) if tpm else None,
                daily_cost_usd=float(daily_usd) if daily_usd else None,
            )
        except Exception as e:
            log.exception("estimate_tpm_cost 执行失败")
            return {"content": f"测算失败（{e}）。请引导用户以官方定价页自行核算。"}
        if "error" in r:
            return {"content": r["error"]}
        src = {
            "title": f"{r['model']} 模型详情页（Singapore 定价 · 权威）",
            "url": r.get("source_url", price_verifier.PRICE_PAGE_URL),
            "kind": "official",
        }
        return {"content": tpm_calc.format_md(r), "sources": [src]}

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
