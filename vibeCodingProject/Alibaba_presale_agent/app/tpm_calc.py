"""
TPM/成本互算 — 确定性测算层（数值不进模型）
===========================================
口径（用户 2026-11-10 指定，基于官方动态限流文档）：
- 适用「模型与限流档位」章节的 auto TPM 模型，默认顶格 2000 万 TPM / 20000 RPM
- input : output = 30 : 1，缓存命中率 85%，利用率跑满 70%
- 价格取自模型详情页 Singapore 分表（USD / 百万 tokens），
  忙闲分时模型（DeepSeek 系）按 24h 加权（忙时 14h + 闲时 10h）
- 正算：TPM → 日成本；反算：日预算 → 所需 TPM

架构定位：与 fx.py 同类的确定性计算模块，由 tools.py 注册为
estimate_tpm_cost 工具供 LLM 调用；价格从 price_verifier 的官方证据
链取数（详情页 Singapore 结构化计费项），保证与报价口径同源。
"""

import re

from . import price_verifier

# 默认测算参数（口径见模块 docstring；工具调用可覆盖）
DEFAULT_TPM = 20_000_000        # 动态限流顶格档（等级3）
DEFAULT_RPM = 20_000
DEFAULT_IN_OUT = 30             # input:output = 30:1
DEFAULT_HIT = 0.85
DEFAULT_UTIL = 0.70
_FX_FALLBACK = 6.67             # 汇率兜底（正常链路由调用方传入实时汇率）
_MINS_PER_DAY = 1440
# 忙闲加权：忙时 08:00-22:00（14h）/ 闲时 22:00-08:00（10h）
_BUSY_W, _IDLE_W = 14 / 24, 10 / 24

# 已知 auto TPM 档位模型（动态限流；来自限流文档「模型与限流档位」）
AUTO_TPM_MODELS = [
    "qwen3.8-max", "qwen3.8-max-0902", "qwen3.8-flash", "qwen3.8-omni-flash",
    "qwen3.8-2.4t-a95b", "qwen3.8-27b", "deepseek-v4.1-flash",
    "deepseek-v4-pro-0813", "kimi-k3", "kimi-k3.1-pro", "glm-5.3", "glm-5.3-prime",
]


def _usd(v: str) -> float | None:
    m = re.search(r"\$?([\d]+(?:\.\d+)?)", v or "")
    return float(m.group(1)) if m else None


async def get_sg_prices(model: str) -> dict | None:
    """模型 → Singapore 结构化价格 {input, cache, output, busy(bool), 分时价}。

    数据源复用 price_verifier 的详情页抓取与 _parse_model_pricing（与报价
    证据链同源）；未命中详情页返回 None（不猜价）。
    """
    import asyncio

    models = price_verifier.extract_model_names(model)
    if not models:
        t = (model or "").strip().lower()
        models = [t] if t else []
    m = models[0]
    for slug in price_verifier._slug_candidates(m):
        url = f"https://www.alibabacloud.com/help/en/model-studio/{slug}"
        try:
            html = await price_verifier._cached_fetch(f"model_{slug}", url)
        except Exception:
            html = ""
        if not html:
            continue
        pricing = price_verifier._parse_model_pricing(price_verifier._strip_tags(html))
        sg = (pricing or {}).get("Singapore") or {}
        if not sg:
            continue
        # 无 qualifier（qwen/kimi/glm 形态）
        if "input" in sg and "input" in sg and "output" in sg:
            p_in, p_out = _usd(sg["input"]), _usd(sg["output"])
            p_cache = _usd(sg.get("input(implicit cache)", "") or "")
            if p_in and p_out:
                return {
                    "model": m, "busy": False,
                    "input": p_in, "cache": p_cache, "output": p_out,
                    "url": url,
                }
        # 忙闲分时（DeepSeek 形态）：取加权混合价
        if "input|busy hours" in sg and "output|busy hours" in sg:
            b_in, b_out = _usd(sg["input|busy hours"]), _usd(sg["output|busy hours"])
            i_in, i_out = _usd(sg["input|idle hours"]), _usd(sg["output|idle hours"])
            b_c = _usd(sg.get("input(implicit cache)|busy hours", "") or "")
            i_c = _usd(sg.get("input(implicit cache)|idle hours", "") or "")
            if b_in and b_out and i_in and i_out:
                return {
                    "model": m, "busy": True,
                    "input": b_in * _BUSY_W + i_in * _IDLE_W,
                    "cache": (b_c * _BUSY_W + i_c * _IDLE_W) if (b_c and i_c) else None,
                    "output": b_out * _BUSY_W + i_out * _IDLE_W,
                    "busy_input": b_in, "idle_input": i_in,
                    "busy_output": b_out, "idle_output": i_out,
                    "url": url,
                }
    return None


def _mixed_price(p: dict, in_out: int, hit: float) -> float | None:
    """混合单价（USD / 百万总 tokens）。"""
    p_in, p_out = p["input"], p["output"]
    p_cache = p["cache"] if p.get("cache") else p_in  # 无缓存价时保守按未命中算
    f_in, f_out = in_out / (in_out + 1), 1 / (in_out + 1)
    return f_in * (hit * p_cache + (1 - hit) * p_in) + f_out * p_out


def compute(
    p: dict,
    tpm: int | None = None,
    daily_cost_usd: float | None = None,
    in_out: int = DEFAULT_IN_OUT,
    hit: float = DEFAULT_HIT,
    util: float = DEFAULT_UTIL,
    fx: float = _FX_FALLBACK,
) -> dict:
    """正算（给 tpm）或反算（给 daily_cost_usd），两者给一个即可。"""
    mix = _mixed_price(p, in_out, hit)
    if mix is None:
        return {"error": "价格数据不完整"}
    if tpm:
        day_m = tpm * util * _MINS_PER_DAY / 1e6
        cost = day_m * mix
        return {
            "direction": "cost",
            "tpm": tpm,
            "daily_tokens_m": round(day_m, 1),
            "daily_input_m": round(day_m * in_out / (in_out + 1), 1),
            "daily_output_m": round(day_m / (in_out + 1), 1),
            "daily_cost_usd": round(cost, 2),
            "daily_cost_cny": round(cost * fx, 0),
            "monthly_cost_usd": round(cost * 30, 1),
            "mixed_price": round(mix, 4),
        }
    if daily_cost_usd:
        day_m = daily_cost_usd / mix
        tpm_need = day_m * 1e6 / (util * _MINS_PER_DAY)
        return {
            "direction": "tpm",
            "daily_budget_usd": daily_cost_usd,
            "daily_tokens_m": round(day_m, 1),
            "tpm_needed": round(tpm_need),
            "tpm_needed_wan": round(tpm_need / 1e4, 1),  # 万 TPM
            "rpm_needed": round(tpm_need * util / (day_m * 1e3 / 1) / 1e3) if day_m else 0,
            "mixed_price": round(mix, 4),
        }
    return {"error": "tpm 与 daily_cost_usd 至少给一个"}


async def estimate(
    model: str,
    tpm: int | None = None,
    daily_cost_usd: float | None = None,
    in_out: int | None = None,
    hit: float | None = None,
    util: float | None = None,
    fx: float | None = None,
) -> dict:
    """工具入口：模型名 + (tpm 或 daily_cost_usd) → 测算结果（含公式与口径说明）。"""
    p = await get_sg_prices(model)
    if not p:
        return {
            "error": f"未取到 {model} 的 Singapore 官方定价（详情页未命中），"
            "无法测算。请确认模型名，或以官方定价页为准。"
        }
    in_out = in_out or DEFAULT_IN_OUT
    hit = hit if hit is not None else DEFAULT_HIT
    util = util if util is not None else DEFAULT_UTIL
    fx = fx or _FX_FALLBACK
    if tpm is None and daily_cost_usd is None:
        tpm = DEFAULT_TPM  # 都没给：按顶格档正算
    r = compute(p, tpm=tpm, daily_cost_usd=daily_cost_usd, in_out=in_out, hit=hit, util=util, fx=fx)
    if "error" in r:
        return r
    r.update(
        model=p["model"],
        prices={
            "input": p["input"],
            "cache": p.get("cache"),
            "output": p["output"],
            "busy_split": p.get("busy", False),
        },
        params={"in_out": in_out, "hit": hit, "util": util, "fx": fx},
        source_url=p["url"],
    )
    return r


def format_md(r: dict) -> str:
    """测算结果 → markdown 证据块（回填给 role:tool 消息）。"""
    if "error" in r:
        return f"测算失败：{r['error']}"
    p = r["prices"]
    prm = r["params"]
    lines = [
        f"### {r['model']} · TPM/成本测算（Singapore 官方价 · 确定性计算）",
        "",
        f"价格（USD / 百万 tokens，来源：{r['source_url']}）：",
        f"- Input ${p['input']} / Cache Input ${p.get('cache')} / Output ${p['output']}"
        + ("（忙闲 14h/10h 加权混合价）" if p.get("busy_split") else ""),
        f"- 测算参数：input:output = {prm['in_out']}:1、缓存命中率 {prm['hit']:.0%}、"
        f"利用率 {prm['util']:.0%}、汇率 {prm['fx']}",
        f"- 混合单价：${r['mixed_price']}/百万总 tokens",
        "",
    ]
    if r["direction"] == "cost":
        lines += [
            f"**正算：{r['tpm']/1e4:.0f} 万 TPM → 日成本**",
            "",
            f"- 日吞吐：{r['daily_tokens_m']:,.0f}M tokens"
            f"（input {r['daily_input_m']:,.0f}M / output {r['daily_output_m']:,.0f}M）",
            f"- **日成本：${r['daily_cost_usd']:,.0f} ≈ ¥{r['daily_cost_cny']:,.0f}**",
            f"- 月成本（×30）：${r['monthly_cost_usd']:,.0f}",
            "",
        ]
    else:
        lines += [
            f"**反算：日预算 ${r['daily_budget_usd']:,.0f} → 所需 TPM**",
            "",
            f"- 日吞吐：{r['daily_tokens_m']:,.0f}M tokens",
            f"- **所需 TPM：{r['tpm_needed_wan']:,.0f} 万**（利用率 {prm['util']:.0%} 前提下）",
            "",
        ]
    lines += [
        "口径说明：适用于动态限流（auto TPM）模型的容量/预算测算；",
        "默认档 2000 万 TPM / 20000 RPM（百炼月消费等级3顶格，等级1起步 250~500 万，",
        "实际额度以模型详情页限流显示为准）；命中 85% 依赖固定前缀（system prompt +",
        "检索分块稳定），实际以账单核对为准。",
    ]
    return "\n".join(lines)
