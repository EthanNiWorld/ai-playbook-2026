"""
USD/CNY 实时汇率 —— 带 TTL 缓存与多源回退

为什么自己取而不交给模型：模型记忆里的汇率必然过期且无法自察。后台踩记录
（id=225~230）里用户直接问「查询下实时汇率」，旧版本只能回"我无法查询"，
把活推回给用户，随后整段折扣换算是靠用户手动报的汇率算的。

数据源（2026-11-06 境内网络实测）：
  1. 新浪财经 hq.sinajs.cn/list=USDCNY   实时报价，无需 key（须带 Referer）
  2. 新浪外汇 fx_susdcny                 同源备用代码，字段布局一致
  3. exchangerate-api v4                 日频兜底（境外，个别网络会被网关拦）
全部走 HTTPS + 6 秒超时；任一源成功即返回，取值做区间校验防解析错位。
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime

import httpx

log = logging.getLogger("fx")

RATE_TTL_S = 300  # 5 分钟：日内换算够用，又不至于把早上的价当实时
_SINA_UA = "Mozilla/5.0 (compatible; alibaba-presale-agent/1.0)"
_TIMEOUT_S = 6.0
# 合理区间，挡掉解析错位（例如把时间/成交量当汇率）
_RATE_MIN, _RATE_MAX = 3.0, 12.0

_cache: dict = {"data": None, "at": 0.0}
_lock = asyncio.Lock()

# 汇率意图：只认明确的换汇/汇率表达，避免"美元计价"这类顺带提法触发抓取
_FX_RE = re.compile(
    r"汇率|牌价|换汇|兑人民币|人民币兑|美元兑|美金兑|USD\s*/\s*CNY|CNY\s*/\s*USD"
    r"|折合人民币|换算成人民币|换成人民币|实时汇率",
    re.IGNORECASE,
)
# 币种共现：美元 + (人民币 | 折算类动词) 也要取汇率（实测问法里常一个字不提"汇率"）
_USD_RE = re.compile(r"美元|美金|USD", re.IGNORECASE)
_CNY_RE = re.compile(r"人民币|RMB|CNY", re.IGNORECASE)
_CONVERT_HINT_RE = re.compile(r"几折|折扣|相当于|换算|折合|等于多少|比值|几倍")
# 纯查询（只要一个数字）：「查询下实时汇率」「美元兑人民币多少」
_PURE_RATE_RE = re.compile(
    r"^(?:请|帮我|麻烦)?\s*(?:查询|查|看看|报)?\s*一?下?\s*(?:实时|今天|最新)?\s*"
    r"(?:的)?\s*(?:美元|美金|USD)?\s*(?:对|兑|换|汇率|牌价|汇率是多少|汇率多少)[^0-9]{0,8}$",
    re.IGNORECASE,
)
# 用户自己报的汇率（"实时汇率是6.6704"）——测算时以用户为准
_USER_RATE_RE = re.compile(r"(?:汇率|rate)\s*(?:是|为|=|:|：)?\s*(\d(?:\.\d{1,4})?)", re.IGNORECASE)


def is_fx_question(question: str) -> bool:
    """是否需要实时汇率。

    除了显式提到“汇率”，还得盖住实际踩过的问法：
    「北京的 1.65 美金相当于 12RMB*0.45 的几折？」——一个字没提汇率，
    但同时出现美元与人民币，实际必须先把币种统一才能算，否则模型只能死推。
    """
    if not question:
        return False
    if _FX_RE.search(question):
        return True
    if not _USD_RE.search(question):
        return False
    return bool(_CNY_RE.search(question) or _CONVERT_HINT_RE.search(question))


def is_pure_rate_query(question: str) -> bool:
    """只问汇率数值、没有别的计算诉求 —— 可绕过 LLM 直接回。"""
    if not question or not is_fx_question(question):
        return False
    q = question.strip().rstrip("。？！?.! ")
    if len(q) > 20:
        return False
    # 出现金额/折扣/换算动词，说明用户要算东西，交给模型
    if re.search(r"\d|几折|折扣|相当于|等于|乘|除以", q):
        return False
    return bool(_PURE_RATE_RE.search(q) or re.search(r"汇率|牌价", q))


def user_given_rate(question: str) -> float | None:
    """用户自报汇率优先（他们可能在按某个成交价核算）。"""
    m = _USER_RATE_RE.search(question or "")
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return v if _RATE_MIN <= v <= _RATE_MAX else None


def parse_sina(text: str) -> float | None:
    """解析 hq.sinajs.cn 的 USDCNY / fx_susdcny 报价，取买卖中间价。"""
    m = re.search(r'"([^"]*)"', text or "")
    if not m:
        return None
    parts = m.group(1).split(",")
    if len(parts) < 3:
        return None
    try:
        bid, ask = float(parts[1]), float(parts[2])
    except ValueError:
        return None
    mid = (bid + ask) / 2
    return mid if _RATE_MIN <= mid <= _RATE_MAX else None


def parse_exchangerate_api(data: dict) -> float | None:
    try:
        v = float(data["rates"]["CNY"])
    except (KeyError, TypeError, ValueError):
        return None
    return v if _RATE_MIN <= v <= _RATE_MAX else None


async def _from_sina(client: httpx.AsyncClient, code: str) -> float | None:
    r = await client.get(
        "https://hq.sinajs.cn/list=" + code,
        headers={"Referer": "https://finance.sina.com.cn", "User-Agent": _SINA_UA},
    )
    r.raise_for_status()
    return parse_sina(r.text)


async def _from_exchangerate_api(client: httpx.AsyncClient) -> float | None:
    r = await client.get("https://api.exchangerate-api.com/v4/latest/USD")
    r.raise_for_status()
    return parse_exchangerate_api(r.json())


async def usd_cny(force: bool = False) -> dict | None:
    """返回 {rate, source, url, at, stale}；全部源失败时返回 None（绝不猜）。"""
    now = time.time()
    if not force and _cache["data"] and now - _cache["at"] < RATE_TTL_S:
        return {**_cache["data"], "stale": False}
    async with _lock:
        if not force and _cache["data"] and time.time() - _cache["at"] < RATE_TTL_S:
            return {**_cache["data"], "stale": False}
        sources = (
            ("新浪财经 USD/CNY 实时", "https://hq.sinajs.cn/list=USDCNY", "USDCNY"),
            ("新浪财经 USD/CNY 实时", "https://hq.sinajs.cn/list=fx_susdcny", "fx_susdcny"),
        )
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S, follow_redirects=True) as client:
                for label, url, code in sources:
                    try:
                        rate = await _from_sina(client, code)
                        if rate:
                            return _remember(rate, label, url)
                    except Exception as e:
                        log.warning("汇率源失败 %s: %s", code, e)
                try:
                    rate = await _from_exchangerate_api(client)
                    if rate:
                        return _remember(
                            rate, "exchangerate-api（日频兜底）",
                            "https://api.exchangerate-api.com/v4/latest/USD",
                        )
                except Exception as e:
                    log.warning("汇率兜底源失败: %s", e)
        except Exception:
            log.exception("汇率抓取异常")
    # 本轮全失败：退回上次成功值（若在 1 小时内），并标 stale
    if _cache["data"] and time.time() - _cache["at"] < 3600:
        return {**_cache["data"], "stale": True}
    return None


def _remember(rate: float, source: str, url: str) -> dict:
    data = {
        "rate": round(rate, 4),
        "source": source,
        "url": url,
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    _cache["data"] = data
    _cache["at"] = time.time()
    log.info("汇率已更新: 1 USD = %.4f CNY（%s）", rate, source)
    return {**data, "stale": False}


def evidence_md(info: dict) -> str:
    """给 LLM 的汇率证据块：只给一个数、一个来源、一个时间，防止模型自由发挥。"""
    tail = "（缓存值，实时源本次不可用）" if info.get("stale") else ""
    return (
        f"1 USD = {info['rate']} CNY\n"
        f"来源：{info['source']}（抓取于 {info['at']}）{tail}\n"
        f"换算规则：金额(USD) × {info['rate']} = 金额(CNY)；反向则除以该汇率。\n"
        "本块的汇率是本次唯一可信来源：不要使用记忆里的汇率，也不要回答“无法查询实时汇率”。"
    )


def direct_answer(info: dict) -> str:
    """纯查汇率的直接回答（不调 LLM，秒回）。"""
    tail = "（缓存值，实时源暂不可用）" if info.get("stale") else ""
    return (
        f"当前 **1 USD ≈ {info['rate']} CNY**{tail}\n\n"
        f"来源：{info['source']} · 抓取时间 {info['at'][:16].replace('T', ' ')}\n\n"
        "要换算具体金额的话，把数字和币种发我就行（比如「1.65 美元是多少人民币」「12 元打 4.5 折后折合美元多少」）。"
    )


def no_source_answer() -> str:
    return (
        "这次没能取到实时汇率（数据源暂时不可用）。\n\n"
        "你可以直接把汇率发我（例如「实时汇率 6.67」），我按你给的数算；"
        "或以中国银行、外汇交易平台的报价为准。"
    )
