"""
价格联网校验 — 官方定价页结构化抽取（权威）+ 搜索引擎旁证
================================================
口径：阿里云国际站（新加坡节点）USD 列表价。
alibabacloud.com 为静态渲染页，可直接 httpx 抓取（区别于 JS 渲染站点）。

核心原则（与 LLM 解耦）：本模块产出的「证据块」是回答中唯一合法的
价格数字来源；LLM 严禁凭记忆报价，证据缺失时必须拒答并引导官方页。

v2 结构化抽取：按 <table> 行 + region 标题解析，每行携带地域归属。
（v1 纯文本窗口提取的教训：定价页按 Singapore/Beijing/Frankfurt 等 6 个
region 分表，窗口提取会混淆地域归属；且 DeepSeek 的缓存折扣是 Model ID
单元格里的 "context caching discount" 标记而非独立 Cached input 列，
文本化后语义全丢。）
"""

import asyncio
import bisect
import json
import logging
import re
import time
from datetime import datetime

import httpx

from .config import PRICE_PAGE_TTL_HOURS, PRICE_PAGE_URL, get_cache_dir
from .searcher import web_search

log = logging.getLogger("price")

# 模型名识别（价格校验的检索目标）
MODEL_NAME_RE = re.compile(
    r"(qwen[\d.]*-(?:max|plus|flash|turbo)(?:-preview)?"
    r"|qwen[\d.]+"
    r"|wan[\d.]+"
    r"|happyhorse[\d.]*"
    r"|deepseek-v[\d.]+(?:-pro|-flash)?"
    r"|claude-(?:opus|sonnet|haiku)-?[\d.]*"
    r"|gpt-[\d.]+(?:-mini|-nano)?"
    r"|gemini-[\d.]+"
    r"|kimi-k[\d.]+(?:-pro|-thinking)?"
    r"|glm-[\d.]+"
    r"|doubao-[\w-]+"
    r"|minimax-[\w-]+"
    r"|cosyvoice[\w-]*"
    r"|funasr|fun-music|qwen-audio[\w-]*)",
    re.IGNORECASE,
)

# 触发价格校验的问题特征
PRICE_KEYWORDS_RE = re.compile(
    r"价格|定价|多少钱|多钱|计费|收费|费率|费用|成本|单价|免费额度|额度|优惠|折扣|一亿|百万"
    r"|pricing|price|cost|quota|discount|usd|美元|\$",
    re.IGNORECASE,
)

# 口语中会出现的模型家族词。当前句提到家族词却抽不出具体型号时（如
# "kimi 最新款价格"），禁止回退挪用历史里的其他模型——否则会拿着
# deepseek 的证据去回答 kimi 的问题，前端还显示"已联网核实"误导客户。
# 边界用 (?<![a-z])…(?![a-z]) 而非 \b：汉字在 Python 正则中也算 \w，
# "那kimi呢"/"kimi的" 在 \b 下不命中，追问场景会漏拦截。
_FAMILY_HINT_RE = re.compile(
    r"(?<![a-z])(qwen|wan|deepseek|glm|kimi|claude|gpt|gemini|doubao|minimax"
    r"|cosyvoice|funasr|fun-music|happyhorse)(?![a-z])",
    re.IGNORECASE,
)

# 定价页分表的地域标题（口径优先级：Singapore > China (Beijing) > 其他）
_REGIONS = (
    "Singapore",
    "China (Beijing)",
)
_REGION_RE = re.compile("|".join(re.escape(r) for r in _REGIONS))

# 首格像模型 ID 的行才入库（排除表头/说明行）
_ROW_MODEL_RE = re.compile(r"^[a-z][a-z0-9._-]{2,40}", re.IGNORECASE)
_ROW_SKIP_KW = ("model", "note", "region", "deployment", "scope", "quota", "item")


def is_price_question(question: str, history: list | None = None) -> bool:
    """价格问题识别；单句含价格关键词直接命中。

    追问兜底：短句含模型名（如 "qwen3.8 flash呢？"）且历史中出现价格话题时
    也触发校验——否则追问会静默跳过联网核实，LLM 只能凭知识库拼表。
    """
    if question and PRICE_KEYWORDS_RE.search(question):
        return True
    if history and question and len(question) <= 30 and extract_model_names(question):
        for h in history[-8:]:
            if h.get("role") == "user" and PRICE_KEYWORDS_RE.search(
                str(h.get("content", ""))[:200]
            ):
                return True
    return False


def _models_with_history(question: str, history: list | None) -> list[str]:
    """提取模型名；当前句没有时，从历史 user 消息倒序找最近的模型名。

    覆盖追问场景："kimi-k3.1-pro呢？"（当前句直接提取）、
    "价格。"（无模型名，回退到历史最近一次提及的模型）。
    但当前句含家族词（如 "kimi 最新款"）却抽不出具体型号时不得回退——
    挪用历史模型的证据会答非所问（见 "kimi k3.1 pro" 撞上历史 deepseek 的教训）。
    """
    models = extract_model_names(question)
    if not models and history:
        if question and _FAMILY_HINT_RE.search(question):
            return models
        for h in reversed(history[-8:]):
            if h.get("role") == "user":
                found = extract_model_names(str(h.get("content", ""))[:600])
                if found:
                    return found
    return models


def extract_model_names(question: str) -> list[str]:
    """从问题中提取去重后的模型名（小写），并把口语写法归一为官方 model ID：
    'qwen3.8 max' → 'qwen3.8-max'、'kimi k3.1 pro' → 'kimi-k3.1-pro'、
    'deepseek v4.1 flash' → 'deepseek-v4.1-flash'。
    """
    q = question
    # ① 家族名与版本号之间的口语空格先归并（注意家族差异：
    #    kimi/deepseek/glm 官方 ID 带连字符，qwen/wan 不带）。
    #    边界用 (?<![a-z]) 而非 \b：汉字也算 \w，"和deepseek v4.1" 在 \b 下不命中
    q = re.sub(r"(?<![a-z])(kimi|deepseek|glm)[\s-]+([a-z]?[\d.]+)", r"\1-\2", q, flags=re.IGNORECASE)
    q = re.sub(r"(?<![a-z])(qwen|wan)\s+([a-z]?[\d.]+)", r"\1\2", q, flags=re.IGNORECASE)
    # ② 版本号与档位后缀之间的空格归并为连字符（保留 ① 拼出的 k/v 前缀）。
    #    后缀边界用 (?![a-z]) 而非 \b：CJK 汉字在 Python 正则中也算 \w，
    #    "pro的价格" 在 "pro" 后没有 \b，会漏归一（"kimi-k3.1 pro的价格" 实测踩坑）
    q = re.sub(
        r"(?<![a-z])(qwen|wan|kimi|deepseek|glm)(-?[a-z]?[\d.]+)\s+(max|plus|flash|pro|turbo|thinking)(?![a-z])",
        r"\1\2-\3",
        q,
        flags=re.IGNORECASE,
    )
    return sorted({m.group(0).lower() for m in MODEL_NAME_RE.finditer(q)})


# ──────────────────── 抓取与缓存 ────────────────────


async def _fetch_raw(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text
    except Exception as e:
        log.warning("抓取 %s 失败: %s", url, e)
        return ""


def _strip_tags(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


async def _get_pricing_html() -> str:
    """官方定价页原始 HTML，TTL 内读缓存；抓取失败时降级用过期缓存"""
    return await _cached_fetch("pricing_page", PRICE_PAGE_URL)


async def _cached_fetch(key: str, url: str) -> str:
    """通用抓取缓存：{key}.html + {key}.json 元数据，TTL 同定价页；失败降级过期缓存"""
    cache_dir = get_cache_dir()
    page_file = cache_dir / f"{key}.html"
    meta_file = cache_dir / f"{key}.json"
    now = time.time()
    if page_file.exists() and meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if now - meta.get("fetched_at", 0) < PRICE_PAGE_TTL_HOURS * 3600:
                return page_file.read_text(encoding="utf-8")
        except Exception:
            pass
    html = await _fetch_raw(url)
    if html:
        page_file.write_text(html, encoding="utf-8")
        meta_file.write_text(
            json.dumps({"fetched_at": now, "url": url}), encoding="utf-8"
        )
        return html
    if page_file.exists():
        log.warning("%s 本次抓取失败，沿用过期缓存", key)
        return page_file.read_text(encoding="utf-8")
    return ""


# ────────────── 模型详情页（含缓存/细项价格，优先于主定价页） ──────────────

# 详情页 Billing Item 行（长项优先；可选括号修饰词支持忙/闲时段写法，如 "Input (Idle hours) 0.141"）
_BILLING_ITEM_RE = re.compile(
    r"(Explicit Cache Creation|Explicit Cache Read|Input\(Implicit Cache[^)]*\)|"
    r"Input\(Batch File\)|Input\(Batch Chat\)|Output\(Batch File\)|Output\(Batch Chat\)"
    r"|Input|Output)\s*(\([^)]*\))?\s+\$?([\d.]+)",
    re.IGNORECASE,
)


def _parse_model_pricing(text: str) -> dict:
    """从模型详情页纯文本中提取 Pricing 节的 Singapore / Beijing 计费项。

    返回 {region: {billing_item_lower: "$price"}}，region 为 Singapore / China (Beijing)。
    """
    out: dict = {}
    pi = text.find("original pricing")
    if pi < 0:
        pi = text.lower().find("pricing")
    if pi < 0:
        return out
    # 窗口：Pricing 节起点 → 之后的 Rate Limits 节（详情页该节标题固定）
    ri = text.find("Rate Limits", pi)
    window = text[pi : ri if ri > 0 else pi + 20000]
    for region in ("Singapore", "China (Beijing)"):
        rpos = window.find(region)
        if rpos < 0:
            continue
        # 切到下一个 region 标题或窗口尾
        nexts = [window.find(r2, rpos + len(region)) for r2 in _REGIONS if r2 != region]
        end = min([n for n in nexts if n > 0], default=len(window))
        seg = window[rpos + len(region) : end]
        items: dict = {}
        for m in _BILLING_ITEM_RE.finditer(seg):
            base = m.group(1).lower()
            qual = (m.group(2) or "").strip("() ").strip()  # 如 "Idle hours"
            # 归一化：Input(Implicit Cache, Busy hours) → base=input(implicit cache), qual=busy hours
            m_ic = re.match(r"input\(implicit cache\s*,?\s*([^)]*)\)$", base)
            if m_ic:
                extra = m_ic.group(1).strip(" ,")
                base = "input(implicit cache)"
                qual = (extra + ", " + qual).strip(" ,") if qual and extra else (extra or qual)
            # kimi 详情页写法 "Input (cache hit) 0.184" → 缓存命中价，归入 Cache Input 列
            if base == "input" and "cache hit" in qual.lower():
                base, qual = "input(implicit cache)", ""
            key = base + (f"|{qual.lower()}" if qual else "")
            if key not in items:  # 同名取首个（区域段内不会重复）
                items[key] = "$" + m.group(3)
        if items:
            out[region] = items
    return out


# ────────────── 标准价格表渲染（代码生成，杜绝 LLM 排版漂移） ──────────────
# 列序为产品约定：Region | Input | Cache Input | Output | Cache Write | 备注
_TABLE_HEADER = (
    "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) "
    "| 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |"
)
_TABLE_SEP = "|---|---|---|---|---|---|"


def _render_price_table(title: str, rows: list[tuple]) -> str:
    """rows 元素: (region_label, input, cache_input, output, cache_write, note)"""
    lines = [f"**{title}**", "", _TABLE_HEADER, _TABLE_SEP]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows]
    return "\n".join(lines)


def _detail_evidence(model_id: str, page_url: str, pricing: dict) -> list[str]:
    """模型详情页 → 标准价格表（代码渲染）。

    按 qualifier（idle/busy hours）拆行；显式缓存读取与 Batch 档价进备注列；
    详情页未提供的计费项（如 DeepSeek 系无 Explicit Cache Creation）填 “—”。
    """
    rows: list[tuple] = []
    for region, items in pricing.items():
        # 按时段 qualifier 分组：input|idle hours 与 output|idle hours 同行
        groups: dict[str, dict] = {}
        order: list[str] = []
        for key, price in items.items():
            base, _, qual = key.partition("|")
            if qual not in groups:
                groups[qual] = {}
                order.append(qual)
            groups[qual][base] = price
        for qual in order:
            g = groups[qual]
            notes = []
            if g.get("explicit cache read"):
                notes.append(f"显式缓存读取 {g['explicit cache read']}")
            # 口径：Batch 折扣/批次价一律忽略，不进备注
            rows.append(
                (
                    f"{region} · {qual}" if qual else region,
                    g.get("input", "—"),
                    g.get("input(implicit cache)", "—"),
                    g.get("output", "—"),
                    g.get("explicit cache creation", "—"),
                    "；".join(notes) or "—",
                )
            )
    return [
        _render_price_table(
            f"{model_id} · 模型详情页定价（每 1M tokens USD · 权威）", rows
        )
    ]


# ──────────────────── 结构化解析 ────────────────────


def _cells(tr_html: str) -> list[str]:
    cells = []
    for td in re.finditer(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", tr_html):
        txt = re.sub(r"&nbsp;?", " ", td.group(1))
        txt = re.sub(r"<[^>]+>", " ", txt)
        cells.append(re.sub(r"\s+", " ", txt).strip())
    return cells


def _parse_pricing_rows(html: str) -> list[dict]:
    """把定价页全部 <table> 解析为行记录。

    每行 {region, model_id, cells, header}：
      region  = 行所属地域（由该表之前最近的 region 标题决定，bisect 定位）
      header  = 该表表头（用于证据中说明列含义）
    """
    # 提取页首官方缓存计费规则（explicit cache / implicit cache 说明段），
    # 供无独立命中价的模型附注引用
    text = _strip_tags(html)
    m = re.search(r"cache\s*creation|Cache-hit input tokens", text, re.I)
    _CACHE_RULE_POS["page"] = text
    _CACHE_RULE_POS["rule"] = m.start() - 120 if m else None
    # 预扫描全部地域标题位置
    heads = []
    for h in re.finditer(r"<h[1-4][^>]*>([\s\S]*?)</h[1-4]>", html):
        m = _REGION_RE.search(_strip_tags(h.group(1)))
        if m:
            heads.append((h.start(), m.group(0)))
    positions = [p for p, _ in heads]

    rows: list[dict] = []
    for tbl in re.finditer(r"<table[\s\S]*?</table>", html):
        idx = bisect.bisect_right(positions, tbl.start()) - 1
        region = heads[idx][1] if idx >= 0 else ""
        trs = list(re.finditer(r"<tr[\s\S]*?</tr>", tbl.group(0)))
        if not trs:
            continue
        # 首行若含 "model" 视为表头
        first_cells = _cells(trs[0].group(0))
        header = (
            " ｜ ".join(c for c in first_cells if c)[:220]
            if any("model" in c.lower() for c in first_cells)
            else ""
        )
        for tr in trs:
            cells = _cells(tr.group(0))
            if not cells:
                continue
            first = cells[0]
            lowered = first.lower()
            if (
                not _ROW_MODEL_RE.match(first)
                or any(k in lowered for k in _ROW_SKIP_KW)
                or not first.replace("context caching discount", "").strip()
            ):
                continue  # 表头/说明行
            rows.append(
                {
                    "region": region,
                    "model_id": first,
                    "cells": cells,
                    "header": header,
                    "header_cells": first_cells,  # 表头单元格序列（代码渲染表格的列映射依据）
                }
            )
    log.info("定价页结构化解析: %d 行（含地域归属）", len(rows))
    return rows


# 命中缓存但无独立命中价时，附官方页首的显式/隐式缓存计费规则（解析时填充）
_CACHE_RULE_POS: dict = {}


def _col_roles(header_cells: list[str]) -> dict:
    """表头单元格 → 列角色索引（主定价页表头存在多种变体：有无 scope 列、free quota 列等）"""
    roles: dict = {}
    for i, c in enumerate(header_cells):
        cl = c.lower()
        if "deployment scope" in cl or cl.strip() in ("scope", "region"):
            roles.setdefault("scope", i)
        elif "input price" in cl:
            roles.setdefault("input", i)
        elif "output price" in cl:
            roles.setdefault("output", i)
        elif "cached input" in cl or "cache hit" in cl:
            roles.setdefault("cache_input", i)
        elif "cache creation" in cl or "cache write" in cl:
            roles.setdefault("cache_write", i)
    return roles


def _first_price(cell: str) -> str:
    m = re.search(r"\$[\d.]+", cell)
    return m.group(0) if m else ""


def _model_evidence(rows: list[dict], token: str) -> list[str]:
    """某模型 → 标准价格表（代码渲染；Singapore 主口径 + China (Beijing) 第二参考，均给）。

    按表头列映射取数，杜绝 LLM 渲染时的跨 scope 挪用（此前 US scope 的 $2
    曾被当成 Singapore·International 价）。busy/idle 双价同格的行拆为两行，
    同 region 同 scope 同价的重复行合并。
    """
    hits = [r for r in rows if token in r["model_id"].lower()]
    if not hits:
        return []
    sg = [r for r in hits if r["region"] == "Singapore"]
    bj = [r for r in hits if r["region"] == "China (Beijing)"]
    selected = sg + bj or hits[:4]

    table_rows: list[tuple] = []
    all_rows: list[tuple[tuple, bool]] = []  # (六元组行, 是否带 scope 标注)
    seen: set = set()
    has_cc = False
    for r in selected[:8]:
        cells = r["cells"]
        first = cells[0].lower()
        # 口径：Batch 折扣/批次价一律忽略——带折扣标记的行整行剔除（避免把折扣后价格当常规价）
        if re.search(r"\d+%\s*batch|batch inference discount", first):
            continue
        cc = "context caching discount" in first
        has_cc = has_cc or cc
        roles = _col_roles(r.get("header_cells") or [])

        def _cell(role: str) -> str:
            i = roles.get(role)
            return cells[i] if i is not None and i < len(cells) else ""

        scope = _cell("scope").strip()
        input_cell, output_cell = _cell("input"), _cell("output")
        cache_w_cell = _cell("cache_write")

        # kimi 系：Cached input 数值内嵌在输入价单元格
        cache_in = ""
        mi = re.search(r"Cached input:\s*\$([\d.]+)", input_cell, re.I)
        if mi:
            cache_in = f"${mi.group(1)}"
        if not cache_in and roles.get("cache_input") is not None:
            cache_in = _first_price(_cell("cache_input"))
        cache_w = _first_price(cache_w_cell) if cache_w_cell else ""

        notes = []

        # busy/idle 双价在同一格（DeepSeek 系）→ 拆两行
        busy_i = re.search(r"Busy hours:\s*\$([\d.]+)", input_cell, re.I)
        idle_i = re.search(r"Idle hours:\s*\$([\d.]+)", input_cell, re.I)
        variants: list[tuple[str, str, str]] = []
        if busy_i and idle_i:
            busy_o = re.search(r"Busy hours:\s*\$([\d.]+)", output_cell, re.I)
            idle_o = re.search(r"Idle hours:\s*\$([\d.]+)", output_cell, re.I)
            variants = [
                ("busy hours", f"${busy_i.group(1)}", f"${busy_o.group(1)}" if busy_o else ""),
                ("idle hours", f"${idle_i.group(1)}", f"${idle_o.group(1)}" if idle_o else ""),
            ]
        else:
            variants = [("", _first_price(input_cell), _first_price(output_cell))]

        for qual, ip, op in variants:
            if not ip and not op:
                continue
            label = f"{r['region']} · {scope}" if scope else r["region"]
            if qual:
                label = f"{label} · {qual}" if label else qual
            key = (label, ip, op, cache_in, cache_w)
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(
                (
                    (
                        label,
                        ip or "—",
                        cache_in or "—",
                        op or "—",
                        cache_w or "—",
                        "；".join(notes) or "—",
                    ),
                    bool(scope),
                )
            )

    # 同 region 同价且同备注的无 scope 行若已被带 scope 行覆盖 → 丢弃；
    # 备注不同（如 batch 折扣档）则保留，避免吞掉分档信息
    scoped_prices = {
        (r[0].split(" · ")[0], r[1], r[2], r[3], r[4], r[5]) for r, sc in all_rows if sc
    }
    table_rows = [
        r
        for r, sc in all_rows
        if sc
        or (r[0].split(" · ")[0], r[1], r[2], r[3], r[4], r[5]) not in scoped_prices
    ]

    if not table_rows:
        return []
    block = _render_price_table(
        f"{token} · 官方定价页（每 1M tokens USD）", table_rows
    )
    # 支持缓存折扣但主表未给命中单价（DeepSeek/Qwen 系常态）→ 附官方规则，防 LLM 臆造
    if has_cc and not any(r[2] != "—" for r in table_rows):
        i = _CACHE_RULE_POS.get("rule")
        if i:
            rule = re.sub(r"\s+", " ", _CACHE_RULE_POS["page"])[i : i + 500]
            m1 = (
                re.search(r"[^.;]*cache[^.;]*%[^.;]*[.;]", rule, re.I)
                or re.search(r"[^.;]*cache[^.;]*[.;]", rule, re.I)
            )
            snippet = m1.group(0).strip() if m1 else rule[:180].strip()
            block += (
                "\n\n注：该模型 intl 主表未单列缓存命中/显式创建单价"
                f"（仅 context caching discount 标记）。官方规则节选：{snippet} "
                "具体单价以官方页为准，禁止估算。"
            )
    return [block]


def _find_windows(page_text: str, token: str, width: int = 300, max_windows: int = 2) -> list[str]:
    """（兜底用）在纯文本中定位模型 token 附近的上下文窗口"""
    windows: list[str] = []
    last_end = -1
    for m in re.finditer(re.escape(token), page_text, re.IGNORECASE):
        if m.start() <= last_end:
            continue
        s = max(0, m.start() - width // 3)
        e = min(len(page_text), m.end() + width)
        windows.append(page_text[s:e].strip())
        last_end = e
        if len(windows) >= max_windows:
            break
    return windows


# ──────────────────── 校验主入口 ────────────────────


async def verify_prices(question: str, history: list | None = None) -> dict:
    """对问题（含追问回退历史）中的模型名做「官方定价页结构化抽取 + 搜索旁证」两级校验。

    返回:
        {
          "status":     "official" | "web" | "none",
          "models":     [识别出的模型名],
          "evidence_md": 证据块 markdown（拼入 LLM prompt），
          "sources":    [{title, url, kind}]（展示给前端），
          "checked_at": 核实时间 ISO
        }
    """
    models = _models_with_history(question, history)
    # 兜底：问到价但没识别出具体模型名，且提到 qwen/百炼 → 用泛化 token
    if not models and re.search(r"qwen|百炼|bailian|model\s*studio", question, re.I):
        models = ["qwen"]

    checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
    sources: list[dict] = []
    official_blocks: list[str] = []
    web_blocks: list[str] = []
    need_main_page_models: list[str] = []  # 详情页未命中、回退主定价页的模型

    # 〇级证据：模型详情页（含缓存/显式缓存/批量等细项价，优先）
    for m in models:
        if m == "qwen":  # 泛化 token，无详情页
            need_main_page_models.append(m)
            continue
        slug = re.sub(r"\.", "-", m)
        url = f"https://www.alibabacloud.com/help/en/model-studio/{slug}"
        try:
            html = await _cached_fetch(f"model_{slug}", url)
        except Exception as e:
            log.warning("模型详情页抓取失败 %s: %s", url, e)
            html = ""
        if html:
            pricing = _parse_model_pricing(_strip_tags(html))
            if pricing:
                official_blocks.append(
                    f"#### {m} · 模型详情页定价（权威，优先于主定价页）"
                )
                official_blocks.extend(_detail_evidence(m, url, pricing))
                sources.append(
                    {
                        "title": f"{m} 模型详情页（含缓存价 · 权威）",
                        "url": url,
                        "kind": "official",
                    }
                )
                continue
        need_main_page_models.append(m)

    # 一级证据：官方定价页主表（详情页未命中时）
    html = await _get_pricing_html()
    if html and need_main_page_models:
        rows = _parse_pricing_rows(html)
        for m in need_main_page_models:
            official_blocks.extend(_model_evidence(rows, m))
        text = _strip_tags(html)
        if not any("模型详情页定价" in b for b in official_blocks):
            # 详情页全未命中时才回退 v1 文本窗口
            if not official_blocks:
                for m in need_main_page_models:
                    for w in _find_windows(text, m):
                        official_blocks.append(f"- 【{m}】…{w}…")
        # 命中忙/闲分时价格时，附带官方的忙时时间段定义（不然回答有价无时段）
        if any("busy" in b.lower() for b in official_blocks):
            i = text.lower().find("busy hours are")
            if i >= 0:
                official_blocks.append(
                    "- 【忙/闲时段官方定义】" + text[max(0, i - 60) : i + 260].strip()
                )
        if official_blocks and need_main_page_models:
            sources.append(
                {
                    "title": "Model Studio 官方定价页（国际站 · 权威）",
                    "url": PRICE_PAGE_URL,
                    "kind": "official",
                }
            )

    # 二级证据：搜索旁证。官方证据已就绪时跳过（官方页更权威，且 web_search 单次 12-14s，
    # 跳过可把价格题核实耗时从 ~25s 降到秒级）；仅官方证据缺失时用作兜底
    web_results = []
    if not official_blocks:
        queries = [f"{m} alibabacloud model studio pricing" for m in models]
        if not queries:
            queries = ["阿里云百炼 模型 定价 pricing"]
        web_results = await asyncio.gather(
            *[web_search(q, max_results=3) for q in queries[:3]]
        )
    for results in web_results:
        for r in results:
            snippet = (r.get("snippet") or "").strip()
            if not snippet:
                continue
            web_blocks.append(
                f"- [{r.get('title', '')}]({r.get('url', '')}): {snippet[:300]}"
            )
            sources.append(
                {
                    "title": (r.get("title") or "搜索结果")[:60],
                    "url": r.get("url", ""),
                    "kind": "web",
                }
            )

    # 去重 sources
    seen: set[str] = set()
    deduped: list[dict] = []
    for s in sources:
        if s["url"] and s["url"] not in seen:
            seen.add(s["url"])
            deduped.append(s)
    sources = deduped

    status = "official" if official_blocks else ("web" if web_blocks else "none")

    evidence_md = ""
    if official_blocks:
        evidence_md += (
            "### 官方定价页证据（权威 — 具体价格数字仅可引用此处）\n"
            "以下价格表格为系统代码渲染的成品：必须逐字原样输出，"
            "不得改写列名/行序/“—”占位，不得增删行列或自行重组表格。\n"
            + "\n".join(official_blocks)
            + "\n\n"
        )
    if web_blocks:
        evidence_md += (
            "### 搜索旁证（仅供交叉参考与时效提示，不得作为报价依据）\n"
            + "\n".join(web_blocks[:8])
            + "\n"
        )

    return {
        "status": status,
        "models": models,
        "evidence_md": evidence_md,
        "sources": sources,
        "checked_at": checked_at,
    }
