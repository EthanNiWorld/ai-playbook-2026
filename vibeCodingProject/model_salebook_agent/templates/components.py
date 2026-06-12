"""
HTML 组件渲染器 — 将结构化 JSON 渲染为完整 HTML Salebook
设计系统复用 qwen3.7-max-salebook.html 的 CSS 变量
"""

from datetime import datetime


def render_salebook_html(data: dict) -> str:
    """将 salebook JSON 渲染为完整 HTML"""
    hero = data.get("hero", {})
    positioning = data.get("positioning", "")
    vs_prev = data.get("vs_previous", {})
    vs_comp = data.get("vs_competitors", {})
    arch = data.get("architecture_advantages", [])
    scenarios = data.get("scenarios", [])
    pricing = data.get("pricing", {})
    talking = data.get("talking_points", [])
    cta = data.get("cta", {})

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{hero.get('model_name', 'Model')} Sales Book</title>
{_css()}
</head>
<body>
{_render_hero(hero)}
<div class="divider"></div>
{_render_positioning(positioning)}
{_render_vs_previous(vs_prev)}
<div class="divider"></div>
{_render_vs_competitors(vs_comp)}
<div class="divider"></div>
{_render_architecture(arch)}
{_render_scenarios(scenarios)}
<div class="divider"></div>
{_render_pricing(pricing)}
<div class="divider"></div>
{_render_talking_points(talking)}
{_render_cta(cta)}
{_render_footer(hero.get('model_name', ''))}
</body>
</html>"""


def _css() -> str:
    return """<style>
:root{--primary:#FF6A00;--bg-dark:#0F1419;--bg-card:#1A1F2E;--text:#E8EAED;--text-muted:#9AA0A6;--green:#34A853;--red:#EA4335;--gold:#FFD700;--gradient:linear-gradient(135deg,#FF6A00 0%,#EE0979 100%)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;background:var(--bg-dark);color:var(--text);line-height:1.6}
.section{max-width:1100px;margin:0 auto;padding:50px 24px}
.section-title{font-size:26px;font-weight:700;margin-bottom:8px}
.section-sub{color:var(--text-muted);margin-bottom:28px;font-size:14px}
.hero{padding:70px 40px 50px;text-align:center;background:linear-gradient(180deg,#1a0a2e 0%,#0F1419 100%)}
.hero h1{font-size:48px;font-weight:800;background:var(--gradient);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:12px}
.hero .tagline{font-size:20px;color:var(--text-muted);margin-bottom:30px}
.hero-stats{display:flex;justify-content:center;gap:36px;flex-wrap:wrap}
.hero-stat .num{font-size:36px;font-weight:800;background:var(--gradient);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-stat .label{font-size:12px;color:var(--text-muted);margin-top:4px}
.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
.card{background:var(--bg-card);border-radius:16px;padding:24px;border:1px solid rgba(255,255,255,0.06)}
.card h3{font-size:17px;font-weight:700;margin-bottom:8px}
.card p{font-size:13px;color:var(--text-muted);line-height:1.7}
.card .metric{display:inline-block;background:rgba(255,106,0,0.12);color:var(--primary);padding:3px 10px;border-radius:6px;font-size:12px;font-weight:600;margin-top:8px}
.bench-table{width:100%;border-collapse:separate;border-spacing:0;border-radius:12px;overflow:hidden;font-size:14px}
.bench-table thead th{background:var(--bg-card);padding:12px 16px;text-align:left;font-weight:600;border-bottom:2px solid rgba(255,106,0,0.3)}
.bench-table tbody td{padding:10px 16px;border-bottom:1px solid rgba(255,255,255,0.04)}
.bench-table tbody tr{background:var(--bg-card)}
.win{color:var(--green);font-weight:700}.lose{color:var(--text-muted)}.tie{color:var(--gold)}
.faq-item{background:var(--bg-card);border-radius:14px;padding:22px 26px;margin-bottom:14px;border:1px solid rgba(255,255,255,0.06)}
.faq-item h3{font-size:15px;font-weight:700;margin-bottom:8px;color:var(--primary)}
.faq-item p{font-size:13px;color:var(--text-muted);line-height:1.8}
.price-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.price-card{background:var(--bg-card);border-radius:14px;padding:22px;text-align:center;border:1px solid rgba(255,255,255,0.06)}
.price-card .model-name{font-size:15px;font-weight:700;margin-bottom:10px}
.price-card .price{font-size:28px;font-weight:800}
.price-card .detail{font-size:12px;color:var(--text-muted);margin-top:6px}
.price-card.highlight{border-color:var(--primary);box-shadow:0 0 20px rgba(255,106,0,0.1)}
.cta{text-align:center;padding:50px 24px 70px;background:linear-gradient(0deg,#1a0a2e 0%,var(--bg-dark) 100%)}
.cta h2{font-size:28px;font-weight:800;margin-bottom:10px}
.cta p{color:var(--text-muted);margin-bottom:24px}
.cta-btn{display:inline-block;background:var(--gradient);color:#fff;padding:12px 36px;border-radius:28px;font-size:15px;font-weight:700;text-decoration:none}
.divider{height:1px;background:linear-gradient(90deg,transparent,rgba(255,106,0,0.2),transparent);max-width:800px;margin:0 auto}
.footer{text-align:center;padding:24px;font-size:11px;color:var(--text-muted);border-top:1px solid rgba(255,255,255,0.04)}
.callout{background:linear-gradient(135deg,rgba(255,106,0,0.08),rgba(238,9,121,0.06));border-left:4px solid var(--primary);border-radius:0 12px 12px 0;padding:18px 22px;margin:20px 0;font-size:14px}
@media(max-width:768px){.hero h1{font-size:32px}.hero-stats{gap:20px}.section{padding:36px 16px}}
</style>"""


def _render_hero(hero: dict) -> str:
    stats_html = ""
    for s in hero.get("stats", []):
        stats_html += f'<div class="hero-stat"><div class="num">{s["value"]}</div><div class="label">{s["label"]}</div></div>\n'
    return f"""<section class="hero">
<h1>{hero.get('model_name', 'Model')}</h1>
<p class="tagline">{hero.get('tagline', '')}</p>
<div class="hero-stats">{stats_html}</div>
</section>"""


def _render_positioning(text: str) -> str:
    if not text:
        return ""
    return f"""<section class="section">
<h2 class="section-title">模型定位</h2>
<div class="callout">{text}</div>
</section>"""


def _render_vs_previous(data: dict) -> str:
    points = data.get("points", [])
    if not points:
        return ""
    cards = ""
    for p in points:
        metric = f'<span class="metric">{p.get("metric", "")}</span>' if p.get("metric") else ""
        cards += f'<div class="card"><h3>{p["title"]}</h3><p>{p.get("description", "")}</p>{metric}</div>\n'
    return f"""<section class="section">
<h2 class="section-title">{data.get('title', 'vs 上一代')}</h2>
<div class="card-grid">{cards}</div>
</section>"""


def _render_vs_competitors(data: dict) -> str:
    rows = data.get("rows", [])
    if not rows:
        return ""
    tbody = ""
    for r in rows:
        verdict_class = r.get("verdict", "tie")
        tbody += f'<tr><td>{r["dimension"]}</td><td class="{verdict_class}">{r.get("ours", "—")}</td><td>{r.get("theirs", "—")}</td></tr>\n'
    return f"""<section class="section">
<h2 class="section-title">{data.get('title', 'vs 竞品')}</h2>
<p class="section-sub">vs {data.get('competitor_name', '竞品')}</p>
<table class="bench-table">
<thead><tr><th>维度</th><th>我方</th><th>竞品</th></tr></thead>
<tbody>{tbody}</tbody>
</table>
</section>"""


def _render_architecture(items: list) -> str:
    if not items:
        return ""
    cards = ""
    for item in items:
        cards += f'<div class="card"><h3>{item["title"]}</h3><p>{item.get("description", "")}</p></div>\n'
    return f"""<section class="section">
<h2 class="section-title">架构优势</h2>
<div class="card-grid">{cards}</div>
</section>"""


def _render_scenarios(items: list) -> str:
    if not items:
        return ""
    cards = ""
    for s in items:
        cards += f'<div class="card"><h3>{s["name"]}</h3><p>{s.get("description", "")}</p><p style="color:var(--green);margin-top:8px;font-size:13px">→ {s.get("why_us", "")}</p></div>\n'
    return f"""<section class="section">
<h2 class="section-title">推荐切入场景</h2>
<div class="card-grid">{cards}</div>
</section>"""


def _render_pricing(data: dict) -> str:
    our = data.get("our_model", {})
    comps = data.get("competitors", [])
    if not our:
        return ""
    cards = f'<div class="price-card highlight"><div class="model-name">{our.get("name", "")}</div><div class="price">{our.get("output_price", "—")}</div><div class="detail">输入: {our.get("input_price", "—")} / 输出: {our.get("output_price", "—")} per 1M tokens</div></div>\n'
    for c in comps:
        cards += f'<div class="price-card"><div class="model-name">{c.get("name", "")}</div><div class="price">{c.get("output_price", "—")}</div><div class="detail">输入: {c.get("input_price", "—")} / 输出: {c.get("output_price", "—")} per 1M tokens</div></div>\n'
    highlight = f'<div class="callout" style="margin-top:20px">{data.get("savings_highlight", "")}</div>' if data.get("savings_highlight") else ""
    return f"""<section class="section">
<h2 class="section-title">定价对比</h2>
<div class="price-grid">{cards}</div>
{highlight}
</section>"""


def _render_talking_points(items: list) -> str:
    if not items:
        return ""
    faqs = ""
    for tp in items:
        faqs += f'<div class="faq-item"><h3>{tp.get("question", "")}</h3><p>{tp.get("answer", "")}</p></div>\n'
    return f"""<section class="section">
<h2 class="section-title">话术建议 / FAQ</h2>
{faqs}
</section>"""


def _render_cta(data: dict) -> str:
    if not data:
        return ""
    return f"""<section class="cta">
<h2>{data.get('title', '立即接入')}</h2>
<p>百炼平台一键开通 · OpenAI 协议兼容 · 新用户赠 100 万 Tokens</p>
<a href="{data.get('primary_link', '#')}" class="cta-btn" target="_blank">{data.get('primary_text', '了解更多')}</a>
</section>"""


def _render_footer(model_name: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""<div class="footer">
<p>© 2026 Alibaba Cloud · 百炼平台 · 仅供内部销售参考</p>
<p style="margin-top:4px">Model Salebook Agent 自动生成 · {model_name} · {today}</p>
<p style="margin-top:4px">⚠️ 部分数据来自联网搜索，建议以实际业务验证为准</p>
</div>"""
