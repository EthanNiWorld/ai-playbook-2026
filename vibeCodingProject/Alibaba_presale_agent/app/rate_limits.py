"""
官方限流查询 — 视频生成 / 生图模型的 RPM、RPS 与并发数
=====================================================
数据源（用户指定）：
  https://docs.bailian.console.aliyun.com/zh/model-studio/rate-limit

备用官方页：
  https://www.alibabacloud.com/help/zh/model-studio/rate-limit

不变量：
  - RPM/RPS/并发数只能来自官方限流页的结构化抽取，每次问答实时抓取，
    不做持久化缓存、不写死任何限流数值；
  - 视频/生图按「任务下发速率 + 同时处理任务数」限流，不等同于 LLM 的
    RPM/TPM，不能把两套口径混用；
  - 页面抓取失败时明确返回失败，由 LLM 引导用户打开官方页。
"""

import bisect
import html
import logging
import re
from datetime import datetime

import httpx

from .price_verifier import extract_model_names

log = logging.getLogger("rate_limits")

RATE_LIMIT_PAGE_URL = "https://docs.bailian.console.aliyun.com/zh/model-studio/rate-limit"
RATE_LIMIT_FALLBACK_URL = "https://www.alibabacloud.com/help/zh/model-studio/rate-limit"

_CATEGORY_LABEL = {"video": "视频生成", "image": "图像生成"}

# 用户未指定型号时按官方页实时顺序最多展示几个型号，避免把整张表（上百行）灌给模型。
# 这里只限制条数，不写死任何型号或限流数值。
_MAX_MODELS_PER_QUERY = 6

_MODEL_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_./-]{1,80}$")
_TABLE_RE = re.compile(r"<table\b[^>]*>([\s\S]*?)</table>", re.IGNORECASE)
_ROW_RE = re.compile(r"<tr\b[^>]*>([\s\S]*?)</tr>", re.IGNORECASE)
_CELL_RE = re.compile(r"<(th|td)\b[^>]*>([\s\S]*?)</\1>", re.IGNORECASE)
_PANEL_RE = re.compile(r'id="panel-([^"]+)"', re.IGNORECASE)
_HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>([\s\S]*?)</h\1>", re.IGNORECASE)

_REGION_ALIASES = {
    "华北2-北京": "华北2（北京）",
    "美国-弗吉尼亚": "美国（弗吉尼亚）",
    "德国-法兰克福": "德国（法兰克福）",
    "日本-东京": "日本（东京）",
}
_SCOPE_RE = re.compile(
    r"^(国际|全球|中国|美国|日本|德国|新加坡|华北|华东|华南|欧洲|亚太|中东|澳洲|印度|英国|法国)"
)


def _clean_text(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\u200b", "")
    return re.sub(r"\s+", " ", text).strip()


def _region_label(panel_id: str) -> str:
    raw = html.unescape(panel_id or "").replace("\u200b", "").strip()
    if raw.startswith("panel-"):
        raw = raw[len("panel-"):]
    if not raw:
        return ""
    if raw in _REGION_ALIASES:
        return _REGION_ALIASES[raw]
    if "-" in raw:
        return raw.replace("-", "（", 1) + "）"
    return raw


def _nearest(items: list[tuple[int, str]], pos: int) -> str:
    """返回 pos 之前最近的一项；没有则空串。"""
    if not items:
        return ""
    idx = bisect.bisect_right([p for p, _ in items], pos) - 1
    return items[idx][1] if idx >= 0 else ""


def _is_region_heading(text: str) -> bool:
    return bool(
        re.search(
            r"北京|新加坡|弗吉尼亚|法兰克福|东京|中国香港|美国|德国|日本",
            text,
        )
    ) and not re.search(r"生成|系列|模型|文本|语音|图像", text)


def _section_before(headings: list[tuple[int, str]], pos: int) -> str:
    for p, text in reversed(headings):
        if p >= pos:
            continue
        if _is_region_heading(text):
            continue
        return text
    return ""


def _looks_scope(value: str) -> bool:
    return bool(value and _SCOPE_RE.search(value) and len(value) <= 12)


def _parse_table(
    block: str,
    region: str,
    section: str,
) -> list[dict]:
    header_labels: list[str] = []
    data_rows: list[list[str]] = []

    for tr in _ROW_RE.findall(block):
        cells = _CELL_RE.findall(tr)
        if not cells:
            continue
        texts = [_clean_text(content) for _, content in cells]
        if all(tag.lower() == "th" for tag, _ in cells):
            header_labels = [t for t in texts if t]
        else:
            data_rows.append(texts)

    labels = [
        h for h in header_labels
        if h and "模型名称" not in h and "部署范围" not in h
    ]
    rows: list[dict] = []
    for texts in data_rows:
        if len(texts) < 2:
            continue
        model = texts[0].strip()
        if not _MODEL_ID_RE.match(model):
            continue
        values = [t for t in texts[1:]]
        scope = ""
        if len(values) == len(labels) + 1:
            scope = values.pop(0)
        elif len(values) > len(labels) and _looks_scope(values[0]):
            scope = values.pop(0)
        if not values:
            continue

        if len(labels) == len(values):
            pairs = list(zip(labels, values))
        elif len(labels) > len(values):
            pairs = list(zip(labels[-len(values):], values))
        else:
            # 表头行数少于数据列（极少见）：保留上限值，指标名兜底。
            pairs = [
                (labels[i] if i < len(labels) else f"限流条件{i + 1}", v)
                for i, v in enumerate(values)
            ]

        metrics = [
            {"name": name, "value": value}
            for name, value in pairs
            if value and value not in {"—", "-"}
        ]
        if not metrics:
            continue
        rows.append(
            {
                "model": model,
                "region": region,
                "scope": scope,
                "section": section,
                "metrics": metrics,
            }
        )
    return rows


def parse_rate_limit_html(html_text: str) -> list[dict]:
    """把官方限流页 HTML 解析为结构化行（纯函数，便于离线测试）。"""
    if not html_text:
        return []

    panels = [(m.start(), _region_label(m.group(1))) for m in _PANEL_RE.finditer(html_text)]
    headings: list[tuple[int, str]] = []
    for m in _HEADING_RE.finditer(html_text):
        text = _clean_text(m.group(2))
        if text:
            headings.append((m.start(), text))

    rows: list[dict] = []
    for m in _TABLE_RE.finditer(html_text):
        region = _nearest(panels, m.start())
        section = _section_before(headings, m.start())
        rows.extend(_parse_table(m.group(1), region, section))

    deduped: list[dict] = []
    seen: set[tuple] = set()
    for row in rows:
        key = (
            row["model"],
            row["region"],
            row["scope"],
            row["section"],
            tuple((x["name"], x["value"]) for x in row["metrics"]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _norm_model(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").lower()).replace("_", "-")


def _candidate_models(raw: str) -> list[str]:
    """把用户/模型给的口语型号映射为官方限流页里的 Model ID。"""
    raw = (raw or "").strip()
    if not raw:
        return []
    candidates: list[str] = []

    def add(v: str) -> None:
        v = _norm_model(v)
        if v and v not in candidates:
            candidates.append(v)

    for name in extract_model_names(raw) or []:
        add(name)
    add(raw)

    low = raw.lower().replace("_", "-")
    # wan 视频线：wan3.0 prime / wan3.0 video prime / 裸 wan3.0
    m = re.search(r"wan\s*([\d.]+)\s*([a-z0-9 .-]*)", low)
    if m:
        ver, rest = m.group(1), m.group(2)
        tokens = re.findall(r"[a-z0-9]+", rest)
        if "prime" in tokens:
            add(f"wan{ver}-video-prime")
        if "video" in tokens:
            add(f"wan{ver}-video")
        if "image" in tokens:
            add(f"wan{ver}-image")
        for token in ("t2v", "i2v", "r2v", "s2v", "kf2v", "t2i", "i2i", "vace"):
            if token in tokens:
                add(f"wan{ver}-{token}")
        if not tokens:
            add(f"wan{ver}")
            add(f"wan{ver}-video")
    # happyhorse 1.1 t2v → happyhorse-1.1-t2v
    m = re.search(r"happyhorse\s*([\d.]+)?\s*([a-z0-9 -]*)", low)
    if m:
        ver, rest = m.group(1), m.group(2)
        tokens = re.findall(r"[a-z0-9]+", rest)
        base = f"happyhorse-{ver}" if ver else "happyhorse"
        if tokens:
            add(base + "-" + "-".join(tokens))
        else:
            add(base)
    return candidates


def _category_of(row: dict) -> str:
    model = row["model"].lower()
    section = row["section"] or ""
    if (
        "image" in model
        or re.search(r"(?:^|-)(?:t2i|i2i|imageedit)(?:-|$)", model)
        or "图像" in section
    ):
        return "image"
    if (
        "video" in model
        or "happyhorse" in model
        or re.search(r"(?:^|-)(?:t2v|i2v|r2v|s2v|kf2v|vace)(?:-|$)", model)
        or "视频" in section
    ):
        return "video"
    return ""


def _region_hit(region: str, hint: str) -> bool:
    if not hint:
        return True
    h = hint.lower()
    r = (region or "").lower()
    aliases = {
        "新加坡": ("新加坡", "singapore"),
        "北京": ("北京", "beijing"),
        "美国": ("美国", "弗吉尼亚", "virginia"),
        "德国": ("德国", "法兰克福", "frankfurt"),
        "日本": ("日本", "东京", "tokyo"),
        "香港": ("香港", "hong kong"),
    }
    for key, words in aliases.items():
        if key in h or any(w in h for w in words):
            return any(w in r for w in words)
    return h in r


def lookup_rate_limits(
    rows: list[dict],
    model: str = "",
    category: str = "",
    region: str = "",
) -> dict:
    """按型号/类别/地域筛选官方限流行（纯函数）。"""
    category = category if category in _CATEGORY_LABEL else ""
    model_hint = (model or "").strip()
    candidates = _candidate_models(model_hint)

    selected: list[dict] = []
    if candidates:
        bare_wan = re.fullmatch(r"wan[\d.]+", _norm_model(model_hint))
        if bare_wan:
            # 裸 wan3.0 是泛问：同时返回标准版与 Prime 等全部同版本型号。
            prefix = _norm_model(model_hint)
            selected = [r for r in rows if _norm_model(r["model"]).startswith(prefix)]
        else:
            exact = {
                c for c in candidates
                if any(_norm_model(r["model"]) == c for r in rows)
            }
            if exact:
                selected = [r for r in rows if _norm_model(r["model"]) in exact]
            else:
                selected = [
                    r for r in rows
                    if any(_norm_model(r["model"]).startswith(c) for c in candidates)
                ]

    if not selected and category:
        selected = [r for r in rows if _category_of(r) == category]

    if not selected and not model_hint and not category:
        return {"rows": [], "matched_models": [], "note": ""}

    if category:
        selected = [r for r in selected if _category_of(r) != "" and _category_of(r) == category] or selected

    region_note = ""
    if region and selected:
        filtered = [r for r in selected if _region_hit(r["region"], region)]
        if filtered:
            selected = filtered
        else:
            region_note = f"官方限流页未找到「{region}」的条目，以下为全部地域。"

    # 未指定型号的泛问：按官方页实时顺序取前 N 个型号，不维护任何"主推清单"。
    limit_note = ""
    if not model_hint and category and selected:
        kept: list[dict] = []
        seen_models: list[str] = []
        for row in selected:
            if row["model"] not in seen_models:
                if len(seen_models) >= _MAX_MODELS_PER_QUERY:
                    continue
                seen_models.append(row["model"])
            if row["model"] in seen_models:
                kept.append(row)
        if len({r["model"] for r in selected}) > len(seen_models):
            limit_note = (
                f"未指定型号，按官方限流页顺序展示前 {len(seen_models)} 个型号；"
                "完整清单请查看官方页。"
            )
        selected = kept

    matched_models: list[str] = []
    for row in selected:
        if row["model"] not in matched_models:
            matched_models.append(row["model"])

    note = region_note
    if limit_note:
        note = (note + " " + limit_note).strip()
    if not selected:
        if model_hint:
            note = f"官方限流页未找到 {model_hint} 的条目。"
        elif category:
            note = f"官方限流页未找到{_CATEGORY_LABEL[category]}条目。"
    return {"rows": selected, "matched_models": matched_models, "note": note}


def _cell(value: str) -> str:
    return (value or "").replace("|", "\\|").strip()


def format_evidence(result: dict, source_url: str, fetched_at: str) -> str:
    """结构化行 → 代码渲染的 Markdown 证据表。"""
    rows = result.get("rows", [])
    models = result.get("matched_models", [])
    if not rows:
        return result.get("note") or "官方限流页未检索到对应模型。"

    categories = {_category_of(r) for r in rows if _category_of(r)}
    category_label = (
        "视频 / 图像生成"
        if len(categories) > 1
        else _CATEGORY_LABEL.get(next(iter(categories), ""), "图像与视频生成")
    )

    groups: dict[tuple, dict] = {}
    for row in rows:
        for metric in row["metrics"]:
            key = (
                row["model"],
                row["scope"],
                metric["name"],
                metric["value"],
                row["section"],
            )
            if key not in groups:
                groups[key] = {"regions": []}
            if row["region"] and row["region"] not in groups[key]["regions"]:
                groups[key]["regions"].append(row["region"])

    lines = [
        f"#### 百炼官方限流 · {category_label}",
        f"官方来源：{source_url}",
        f"抓取时间：{fetched_at}",
        "",
        "| 模型 (Model ID) | Region | 服务范围 | 限流指标 | 上限 |",
        "|---|---|---|---|---|",
    ]
    for (model, scope, metric, value, _), info in groups.items():
        lines.append(
            f"| {_cell(model)} | {_cell(' / '.join(info['regions']))} | "
            f"{_cell(scope or '—')} | {_cell(metric)} | {_cell(value)} |"
        )

    lines.extend(
        [
            "",
            f"命中型号：{'、'.join(models)}。",
            "口径说明：RPS = 每秒请求数；并发数 = 同一时刻处理中的任务数。"
            "视频/生图按任务下发速率与并发数限流，不等同于 LLM 的 RPM/TPM。",
        ]
    )
    if result.get("note"):
        lines.append(result["note"])
    return "\n".join(lines)


async def _fetch_page(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text


async def _load_rows() -> tuple[list[dict], str, str, str]:
    """实时抓取官方页并解析。返回 (rows, source_url, fetched_at, warning)。"""
    errors: list[str] = []
    for url in (RATE_LIMIT_PAGE_URL, RATE_LIMIT_FALLBACK_URL):
        try:
            page = await _fetch_page(url)
            rows = parse_rate_limit_html(page)
            if not rows:
                errors.append(f"{url}: 页面未解析出限流表")
                continue
            fetched_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
            return rows, url, fetched_at, ""
        except Exception as e:
            errors.append(f"{url}: {type(e).__name__}: {e}")
            log.warning("官方限流页抓取失败 %s: %s", url, e)

    return [], "", "", "官方限流页抓取失败：" + "；".join(errors)


async def get_rate_limits(
    model: str = "",
    category: str = "",
    region: str = "",
) -> dict:
    """工具主入口：实时抓取 → 筛选 → 生成证据文本。"""
    rows, source_url, fetched_at, warning = await _load_rows()
    if not rows:
        return {
            "content": (
                f"{warning}。请勿猜测 RPM/并发数，向用户说明暂未能获取官方限流数据，"
                f"并引导打开官方限流页：{RATE_LIMIT_PAGE_URL}"
            ),
            "sources": [
                {"title": "百炼官方限流页（未能抓取）", "url": RATE_LIMIT_PAGE_URL, "kind": "official"}
            ],
            "error": warning,
        }

    result = lookup_rate_limits(rows, model=model, category=category, region=region)
    content = format_evidence(result, source_url, fetched_at)
    if warning:
        content += f"\n\n> {warning}"
    source_title = "百炼官方限流页（权威）"
    return {
        "content": content,
        "sources": [
            {"title": source_title, "url": source_url or RATE_LIMIT_PAGE_URL, "kind": "official"}
        ],
        "matched_models": result.get("matched_models", []),
    }
