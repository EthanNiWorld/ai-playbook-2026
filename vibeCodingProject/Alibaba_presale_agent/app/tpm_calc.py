"""
TPM/成本互算与账单 token 成本 — 确定性测算层（数值不进模型）
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
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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


# ── 账单 token 成本：原始整数 + Decimal 确定性计算 ──
_MILLION = Decimal(1_000_000)
_CENT = Decimal("0.01")


def _usage_int(value, label: str) -> int:
    """只接受原始非负整数；禁止模型先换算成 M/B 后再传入。"""
    text = str(value if value is not None else "").strip().replace(",", "")
    if not re.fullmatch(r"\d+", text):
        raise ValueError(f"{label} 必须是原始非负整数 token 数")
    return int(text)


def _usage_decimal(value, label: str, required: bool = True) -> Decimal | None:
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(f"缺少 {label}")
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{label} 不是合法数字") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{label} 必须是非负有限数字")
    return number


def _cent(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def usage_cost_md(items: list[dict], region: str = "Singapore", fx_rate=None) -> str:
    """按原始 token 整数计算账单，返回可直接交付的 Markdown 成品表。

    每个费用分量先四舍五入到美分，小计为三个已舍入分量之和，总计为各模型
    小计之和，保证客户看到的表格在分、合计两个层级都严格可加。
    """
    if not isinstance(items, list) or not items:
        raise ValueError("items 至少需要一条模型用量")
    if len(items) > 12:
        raise ValueError("单次最多测算 12 个模型")
    rate = _usage_decimal(fx_rate, "fx_rate", required=False)
    if rate is not None and rate <= 0:
        raise ValueError("fx_rate 必须大于 0")

    rows: list[dict] = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条用量不是对象")
        model = re.sub(r"[|\r\n]", "", str(item.get("model", "")).strip())[:80]
        if not model:
            raise ValueError(f"第 {index} 条缺少 model")
        input_tokens = _usage_int(item.get("input_tokens"), f"{model}.input_tokens")
        cached_tokens = _usage_int(
            item.get("cached_input_tokens", 0), f"{model}.cached_input_tokens"
        )
        output_tokens = _usage_int(item.get("output_tokens", 0), f"{model}.output_tokens")
        if cached_tokens > input_tokens:
            raise ValueError(f"{model} 的缓存 token 不能大于输入总 token")
        input_price = _usage_decimal(
            item.get("input_price_per_million"), f"{model}.input_price_per_million"
        )
        cache_price = _usage_decimal(
            item.get("cache_input_price_per_million"),
            f"{model}.cache_input_price_per_million",
            required=cached_tokens > 0,
        )
        output_price = _usage_decimal(
            item.get("output_price_per_million"),
            f"{model}.output_price_per_million",
            required=output_tokens > 0,
        )
        uncached_tokens = input_tokens - cached_tokens
        uncached_cost = _cent(Decimal(uncached_tokens) / _MILLION * input_price)
        cached_cost = _cent(
            Decimal(cached_tokens) / _MILLION * (cache_price or Decimal(0))
        )
        output_cost = _cent(
            Decimal(output_tokens) / _MILLION * (output_price or Decimal(0))
        )
        rows.append({
            "model": model,
            "uncached_tokens": uncached_tokens,
            "cached_tokens": cached_tokens,
            "output_tokens": output_tokens,
            "uncached_cost": uncached_cost,
            "cached_cost": cached_cost,
            "output_cost": output_cost,
            "subtotal": uncached_cost + cached_cost + output_cost,
        })

    lines = [
        f"### Token 成本测算（{region} · 确定性计算）",
        "",
        "| 模型 | 非缓存输入 tokens | 缓存输入 tokens | 输出 tokens | 非缓存输入费用 (USD) | 缓存输入费用 (USD) | 输出费用 (USD) | 小计 (USD) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {row['uncached_tokens']:,} | {row['cached_tokens']:,} "
            f"| {row['output_tokens']:,} | ${row['uncached_cost']:,.2f} "
            f"| ${row['cached_cost']:,.2f} | ${row['output_cost']:,.2f} | ${row['subtotal']:,.2f} |"
        )
    total = sum((row["subtotal"] for row in rows), Decimal(0))
    total_uncached = sum(row["uncached_tokens"] for row in rows)
    total_cached = sum(row["cached_tokens"] for row in rows)
    total_output = sum(row["output_tokens"] for row in rows)
    total_uncached_cost = sum((row["uncached_cost"] for row in rows), Decimal(0))
    total_cached_cost = sum((row["cached_cost"] for row in rows), Decimal(0))
    total_output_cost = sum((row["output_cost"] for row in rows), Decimal(0))
    lines.append(
        f"| **合计** | {total_uncached:,} | {total_cached:,} | {total_output:,} "
        f"| ${total_uncached_cost:,.2f} | ${total_cached_cost:,.2f} "
        f"| ${total_output_cost:,.2f} | **${total:,.2f}** |"
    )
    lines += [
        "",
        f"**{len(rows)} 个模型合计：${total:,.2f}**",
        "",
        "口径：缓存 tokens 已包含在输入总 tokens 内；非缓存输入 = 输入总量 − 缓存量。"
        "所有费用均由原始整数 tokens ÷ 1,000,000 × 对应 USD 单价计算，未经过 M/B 手工换算。",
    ]
    if rate is not None:
        lines.append(f"按汇率 1 USD = {rate} CNY：合计约 **¥{_cent(total * rate):,.2f}**。")
    lines.append("以上表格为代码计算成品，表头、数据行与合计必须逐字输出，不得自行重算或改写。")
    return "\n".join(lines)
