"""
价格分享卡片 — 官方价格证据 → HTML 卡片 → OSS 私有 Bucket → 24h 签名链接
======================================================================
仅当用户/客户明确要求生成"可转发的价格链接"时，由 LLM 调用
make_price_share_link 工具（见 tools.py）触发；普通价格问答不生成，
避免每次报价都往 OSS 写对象。

数值层不变量：卡片内容直接取自 verify_price_for 的官方证据
（price_verifier 代码渲染的 markdown 表格），不经 LLM 转手，
杜绝链接里的数字被抄错。

LLM（token 计费）模型卡片附默认限流备注：3000 万 TPM / 20000 万 RPM
（额度未在定价页公开，按售前默认口径；视频/生图/音频模型不附）。
OSS 未配置或上传失败时返回 error，LLM 向用户说明即可，不影响问答主链路。
"""

import asyncio
import html
import logging
import re
import uuid
from datetime import datetime, timedelta

from .config import get_oss_config

log = logging.getLogger("share_card")

# 链接有效期：24 小时（产品要求）
LINK_TTL_SECONDS = 24 * 3600

# 分享域名（CNAME 模式）：配置后签名链接改走 <域名>/，规避 OSS 默认
# 域名对 text/html 的平台级强制下载（x-oss-force-download）；空则退回默认域名。
# 绑定步骤：DNS CNAME share→bucket + TXT _dnsauth.share 归属验证，OSS PutBucketCname。
# HTTPS 需为域名托管证书（OSS 控制台域名管理页可绑免费 DV 证书）；证书就绪前可配
# OSS_SHARE_SCHEME=http 先以明文预览，就绪后切回 https。

# LLM（token 计费）模型的默认限流备注。判定依据：官方证据含"每 1M tokens"
# 计费表（视频/生图走"按秒/按张计费"表，不附限流）。
DEFAULT_RATE_LIMIT_NOTE = "限流（LLM 默认额度）：3,000 万 TPM / 20,000 万 RPM（更高额度可提工单调整）"

_CARD_CSS = """
body{margin:0;padding:24px;background:#f7f6f4;color:#0d0d0d;
font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif}
.card{max-width:860px;margin:0 auto;background:#fff;border-radius:12px;
padding:32px 36px;box-shadow:0 2px 16px rgba(0,0,0,.06)}
.brand{color:#ff6a00;font-size:13px;font-weight:600;letter-spacing:.5px}
h1{font-size:22px;margin:8px 0 4px}
.meta{color:#888;font-size:13px;margin-bottom:20px}
h3{font-size:15px;margin:22px 0 8px}
p{font-size:14px;line-height:1.7;margin:8px 0}
table{border-collapse:collapse;width:100%;margin:10px 0 6px;font-size:13.5px}
th,td{border:1px solid #e8e6e2;padding:7px 10px;text-align:left;vertical-align:top}
th{background:#faf6f0;font-weight:600}
td code,code{background:#f4f2ef;padding:1px 5px;border-radius:4px;font-size:12.5px}
.rate{margin-top:16px;padding:10px 14px;background:#faf6f0;border-radius:8px;
font-size:13.5px;line-height:1.6}
.foot{margin-top:26px;padding-top:14px;border-top:1px solid #eee;color:#999;
font-size:12.5px;line-height:1.8}
a{color:#ff6a00;word-break:break-all}
"""


def _md_inline(s: str) -> str:
    """行内 markdown → HTML：转义优先，再处理 **加粗**、`代码`、裸 URL。"""
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"(https?://[^\s<>]+)", r'<a href="\1">\1</a>', s)
    return s


def _is_sep_row(cells: list[str]) -> bool:
    """|---|---| 分隔行判定"""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c != "") and any(c for c in cells)


def md_to_html(md: str) -> str:
    """证据 markdown（标题/段落/表格/加粗/代码/链接）→ 卡片 HTML 片段。

    只需覆盖 price_verifier 产出的结构：#### 标题、**加粗**标题、表格、
    普通说明行；不追求通用 markdown。
    """
    out: list[str] = []
    table: list[list[str]] = []

    def flush_table() -> None:
        nonlocal table
        if not table:
            return
        rows = [r for r in table if not _is_sep_row(r)]
        if rows:
            t = ["<table>", "<tr>" + "".join(f"<th>{_md_inline(c)}</th>" for c in rows[0]) + "</tr>"]
            for r in rows[1:]:
                t.append("<tr>" + "".join(f"<td>{_md_inline(c)}</td>" for c in r) + "</tr>")
            t.append("</table>")
            out.append("\n".join(t))
        table = []

    for line in md.splitlines():
        t = line.strip()
        if t.startswith("|"):
            cells = [c.strip() for c in t.strip("|").split("|")]
            table.append(cells)
            continue
        flush_table()
        if not t:
            continue
        if t.startswith("####"):
            out.append(f"<h3>{_md_inline(t.lstrip('#').strip())}</h3>")
        else:
            out.append(f"<p>{_md_inline(t)}</p>")
    flush_table()
    return "\n".join(out)


def render_price_card(models: list[str], official_md: str, checked_at: str) -> str:
    """官方证据 markdown → 自包含 HTML 卡片（无外部资源，可离线打开）。

    LLM（token 计费）模型附默认 TPM/RPM 限流备注；卡片底部标注链接有效期。
    """
    # 证据里"来源链接（回答时直接引用此 URL…）"是写给 LLM 的指令，
    # 出现在卡片里不合适，替换为中性表述
    md = re.sub(r"来源链接（[^）]*）：", "来源：", official_md)
    body = md_to_html(md)
    is_llm = "每 1M tokens" in official_md
    rate_html = f'<div class="rate">{DEFAULT_RATE_LIMIT_NOTE}</div>' if is_llm else ""
    title = "、".join(models) + " 报价"
    expires = (
        datetime.fromisoformat(checked_at) + timedelta(seconds=LINK_TTL_SECONDS)
    ).strftime("%Y-%m-%d %H:%M") if checked_at else ""
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><style>{_CARD_CSS}</style></head><body>
<div class="card">
<div class="brand">阿里云百炼 Model Studio · 模型报价卡片</div>
<h1>{html.escape(title)}</h1>
<div class="meta">价格口径：官方定价页（国际站 USD） · 核实时间 {html.escape(checked_at)}</div>
{body}
{rate_html}
<div class="foot">价格为核实时点的官方列表价，如有调整以官方定价页为准。<br>
本卡片由「阿里小可爱」生成 · 链接 24 小时内有效{f"（至 {expires}）" if expires else ""}，过期后请重新生成。</div>
</div>
</body></html>"""


def oss_configured(cfg: dict) -> bool:
    return bool(cfg["key_id"] and cfg["key_secret"])


async def make_share_link(model: str) -> dict:
    """核实价格 → 渲染卡片 → 上传 OSS → 签发 24h 访问链接。

    返回 {"url", "expires_at", "models"} 或 {"error": 原因}。
    上传/签名走 asyncio.to_thread，避免阻塞事件循环。
    """
    cfg = get_oss_config()
    if not oss_configured(cfg):
        return {"error": "分享卡片功能未配置（缺少 oss_AccessKey_ID / oss_AccessKey_key 环境变量）"}

    from . import price_verifier  # 延迟导入：tools 已同时导入两者，避免潜在循环

    ev = await price_verifier.verify_price_for(model, "")
    official_md = ev.get("official_md") or ""
    if not official_md:
        return {"error": f"未核实到 {model} 的官方定价（状态 {ev.get('status', 'none')}），无法生成卡片"}
    models = ev.get("models") or [model]
    card_html = render_price_card(models, official_md, ev.get("checked_at", ""))

    slug = re.sub(r"[^a-z0-9.-]+", "-", models[0].lower()).strip("-") or "model"
    key = f"{cfg['prefix']}{slug}-{datetime.now():%Y%m%d%H%M}-{uuid.uuid4().hex[:6]}.html"
    try:
        url, expires_at = await asyncio.to_thread(_put_and_sign, cfg, key, card_html)
    except Exception as e:
        log.warning("分享卡片上传失败: %s", e)
        return {"error": f"卡片上传 OSS 失败：{e}"}
    log.info("价格分享卡片已生成: %s（模型 %s）", key, ",".join(models))
    return {"url": url, "expires_at": expires_at, "models": models}


def _put_and_sign(cfg: dict, key: str, card_html: str) -> tuple[str, str]:
    """同步上传 + 签名（在线程池中执行）。

    预览修复（2026-11-09）：OSS 默认域名对 text/html 有平台级强制下载策略
    （x-oss-force-download: true，错误码 0048-00000001，实测签名参数与对象
    元数据均无法覆盖）。唯一解法是走自定义域名：DNS 侧 CNAME share→bucket
    + TXT verify 归属验证，OSS 侧 PutBucketCname 绑定后，签名走
    cname=True（host 变成 https://share.day1cloud.cn，响应不再带
    attachment，浏览器直接预览）。OSS_SHARE_CNAME 配置了才启用，未配置
    时退回默认域名（预览受限，会强制下载，属已知行为）。
    """
    import os

    import oss2

    endpoint = cfg["endpoint"]
    share_domain = os.getenv("OSS_SHARE_CNAME", "").strip()
    # 签名 URL 协议：HTTPS 证书未就绪时可配 http（预览能力不受影响，仅明文传输）
    scheme = (os.getenv("OSS_SHARE_SCHEME") or "https").strip().lower()
    if scheme not in ("http", "https"):
        scheme = "https"
    cname_mode = bool(share_domain)
    if cname_mode:
        # 签名时 endpoint 用 <scheme>://<自定义域名>，cname=True 告知 SDK
        # 该域名是 Bucket 的 CNAME，不拼接 bucket 前缀
        endpoint = scheme + "://" + share_domain
    bucket = oss2.Bucket(
        oss2.Auth(cfg["key_id"], cfg["key_secret"]),
        endpoint,
        cfg["bucket"],
        is_cname=cname_mode,
    )
    # 上传始终走 OSS 原生 endpoint（is_cname 模式下 put 会打到自定义域名，
    # 也能用，但走原生 endpoint 更稳）；签名再按 cname 模式切域名
    if cname_mode:
        put_bucket = oss2.Bucket(
            oss2.Auth(cfg["key_id"], cfg["key_secret"]), cfg["endpoint"], cfg["bucket"]
        )
    else:
        put_bucket = bucket
    put_bucket.put_object(
        key, card_html, headers={"Content-Type": "text/html; charset=utf-8"}
    )
    url = bucket.sign_url("GET", key, LINK_TTL_SECONDS, slash_safe=True)
    expires_at = (datetime.now() + timedelta(seconds=LINK_TTL_SECONDS)).strftime("%Y-%m-%d %H:%M")
    return url, expires_at
