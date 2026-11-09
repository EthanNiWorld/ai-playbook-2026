"""
联网搜索 — 百炼 Web Search（enable_search）优先，Tavily/DDG 兜底
================================================================
优先级（2026-11-05 实测北京/新加坡 Key 均可用 enable_search）：
  1. 百炼 Web Search：复用 DashScope Key，延迟稳定，无额外配置
  2. Tavily：配了 API Key 时的高质量备选
  3. ddgs (DuckDuckGo)：免费兜底（多引擎易超时，仅最后防线）
"""

import asyncio
import logging
import os
import re

import httpx

from .config import get_llm_config, get_tavily_api_key

log = logging.getLogger("search")

# 搜索是价格校验的旁证；百炼 Web Search（enable_search）内部含搜索+生成两段，
# 实测 14s 左右，预算放宽到 25s（价格类问题才触发，可接受）
SEARCH_TIMEOUT_S = 25

# Web Search 结果中的引用 URL 提取
_URL_RE = re.compile(r"https?://[^\s\)\]\"'<>，。；]+")


async def web_search(
    query: str, max_results: int = 5, thinking_budget: int | None = None
) -> list[dict]:
    """搜索网页，返回 [{title, url, snippet}]；任何失败/超时都降级为空列表

    thinking_budget：给 enable_search 内部的思考设上限。实测不加时，竞品类
    query（如“腾讯云混元 价格”）会因模型长考而超 25s/60s；设 1024 后降到 7~9s
    且仍能拿到关键数字。竞品比价等“只要摘要与链接”的场景必须传它。
    """
    try:
        return await asyncio.wait_for(
            _web_search_impl(query, max_results, thinking_budget), timeout=SEARCH_TIMEOUT_S
        )
    except asyncio.TimeoutError:
        log.warning("搜索超时（%ss），降级为空结果: %s", SEARCH_TIMEOUT_S, query[:60])
        return []


async def _web_search_impl(
    query: str, max_results: int, thinking_budget: int | None = None
) -> list[dict]:
    # 1. 百炼 Web Search（enable_search）
    try:
        results = await _search_bailian(query, max_results, thinking_budget)
        if results:
            return results
    except Exception as e:
        log.warning("百炼 Web Search 失败，降级 Tavily/DDG: %s", str(e)[:150])
    # 2. Tavily
    tavily = get_tavily_api_key()
    if tavily:
        try:
            return await _search_tavily(tavily, query, max_results)
        except Exception as e:
            log.warning("Tavily 搜索失败，降级 DuckDuckGo: %s", e)
    # 3. ddgs 兜底
    return await asyncio.to_thread(_search_ddg, query, max_results)


async def _search_bailian(
    query: str, max_results: int, thinking_budget: int | None = None
) -> list[dict]:
    """百炼 Web Search：enable_search（走 DashScope 兼容协议，复用 QA_MODEL 同一模型）

    与回答模型统一（qwen3.8-max 实测 enable_search 可用，延迟约 12s），
    好处：一个 QA_MODEL 变量控制全局，换模型只改一处。
    返回 [{title, url, snippet}]。回答正文提炼为 snippet，引用 URL 从正文提取。

    踩坑：不限制思考预算时，模型会对“腾讯云混元价格”这类开放问题长考至
    60s 仍未返回（单次 25s 超时直接降级为空）；传 thinking_budget=1024 后
    7~9s 即返回且信息量不降。
    """
    from openai import AsyncOpenAI

    cfg = get_llm_config()
    if not cfg["api_key"]:
        return []
    client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    extra: dict = {"enable_search": True}
    if thinking_budget:
        extra["thinking_budget"] = int(thinking_budget)
    resp = await client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {
                "role": "user",
                "content": (
                    f"联网搜索以下问题，回答控制在 150 字内，并单独列出参考链接：\n{query}"
                ),
            }
        ],
        extra_body=extra,
        max_tokens=800,
    )
    msg = resp.choices[0].message
    content = (msg.content or "").strip()
    if not content:
        return []
    # 从正文中提取引用 URL 作为结果来源
    urls = _URL_RE.findall(content)[:max_results]
    results = [
        {
            "title": f"百炼 Web Search：{query[:40]}",
            "url": u.rstrip(".,;)"),
            "snippet": content[:300],
        }
        for u in urls
    ]
    # 无显式 URL 时仍保留一段摘要（可作时效旁证，无来源链接）
    if not results:
        results = [
            {
                "title": f"百炼 Web Search：{query[:40]}",
                "url": "",
                "snippet": content[:300],
            }
        ]
    return results


async def _search_tavily(api_key: str, query: str, max_results: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
        )
        r.raise_for_status()
        data = r.json()
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
        }
        for item in data.get("results", [])
    ]


def _search_ddg(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo 搜索：优先新版 ddgs 包，回退旧包名"""
    try:
        from ddgs import DDGS  # 新包名（duckduckgo_search 已改名）
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            log.warning("未安装搜索库（ddgs / duckduckgo-search），跳过联网搜索")
            return []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", r.get("url", "")),
                "snippet": r.get("body", ""),
            }
            for r in results
        ]
    except Exception as e:
        log.warning("DuckDuckGo 搜索失败: %s", e)
        return []
