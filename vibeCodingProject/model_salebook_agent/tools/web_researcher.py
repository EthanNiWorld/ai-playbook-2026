"""
联网研究工具 — 当本地知识库缺少数据时搜索权威来源
支持 DuckDuckGo（免费）自动可用
"""

import httpx
from datetime import datetime
from typing import Optional


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    搜索网页，返回结果列表。
    优先使用 DuckDuckGo（免费，无需 API Key）。

    返回: [{title, url, snippet}]
    """
    try:
        return _search_duckduckgo(query, max_results)
    except Exception as e:
        print(f"⚠️ 搜索失败: {e}")
        return []


def fetch_page_content(url: str, max_chars: int = 5000) -> str:
    """抓取网页正文前 N 个字符"""
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        # 简单提取：去除 HTML 标签
        import re
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        return f"[抓取失败: {e}]"


def research_model(model_name: str, aspect: str = "benchmark pricing") -> list[dict]:
    """
    针对特定模型进行联网研究。

    Args:
        model_name: 模型名称（如 "GPT-5.5", "Claude Opus 4.8"）
        aspect: 搜索维度（如 "benchmark pricing", "vs Qwen"）

    Returns:
        [{source, content, date}]
    """
    queries = [
        f"{model_name} {aspect} 2026",
        f"{model_name} benchmark comparison latest",
    ]

    results = []
    today = datetime.now().strftime("%Y-%m-%d")

    for q in queries:
        search_results = search_web(q, max_results=3)
        for item in search_results:
            results.append({
                "source": item.get("url", ""),
                "title": item.get("title", ""),
                "content": item.get("snippet", ""),
                "date": today,
            })

    return results


def research_enterprise(enterprise_name: str, max_snippets: int = 9) -> str:
    """查企业画像素材。

    返回拼接后的 markdown 片段，供 LLM 推断营收/业务形态/决策驱动/AI 潜力。
    DDG 免费使用，总耗时 3-5s。失败返回空字符串。
    """
    if not enterprise_name:
        return ""
    queries = [
        f"{enterprise_name} 2024 营收 业务",
        f"{enterprise_name} 创始人 CEO 决策人",
        f"{enterprise_name} 数字化转型 AI 应用",
    ]
    snippets: list[str] = []
    for q in queries:
        try:
            for r in search_web(q, max_results=3):
                title = r.get("title", "").strip()
                body = r.get("snippet", "").strip()
                url = r.get("url", "")
                if not body:
                    continue
                snippets.append(f"- **{title}**: {body}（来源: {url}）")
        except Exception as e:
            print(f"⚠️ 企业搜索子查询失败 [{q}]: {e}")
    # 去重（同一 url 可能出现多次）并限量
    seen = set()
    deduped = []
    for s in snippets:
        if s in seen:
            continue
        seen.add(s)
        deduped.append(s)
        if len(deduped) >= max_snippets:
            break
    return "\n".join(deduped)


def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo 搜索（免费方案）"""
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in results
    ]
