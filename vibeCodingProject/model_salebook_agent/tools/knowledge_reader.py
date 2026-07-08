"""
本地知识库读取工具
- 支持按模型名模糊匹配 knowledge/ 中的文档
- 支持加载销售策略和竞品分析
"""

from pathlib import Path
from typing import Optional

from config import get_knowledge_base_path, get_notes_path, get_alibaba_hub_path


def load_model_knowledge(model_name: str) -> str:
    """
    根据模型名加载对应知识文档全文。
    搜索逻辑：
    1. alibaba-ai-hub/maas/ 下按关键词匹配
    2. 其他厂商目录按关键词匹配
    返回文档全文或空字符串
    """
    kb = get_knowledge_base_path()
    model_lower = model_name.lower()

    # 关键词提取：如 "Qwen3.7-Max" → ["qwen", "3.7", "max"]
    # "Wan2.7" → ["wan", "2.7"]
    keywords = _extract_keywords(model_lower)

    # 搜索优先级：alibaba-ai-hub/maas > 阿里云全栈 > knowledge 其他目录
    hub = get_alibaba_hub_path()
    search_dirs = [
        hub / "maas",
        hub,
        kb,
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for md_file in search_dir.rglob("*.md"):
            filename_lower = md_file.stem.lower()
            # 检查文件名是否匹配模型关键词
            if _matches_keywords(filename_lower, keywords):
                return md_file.read_text(encoding="utf-8")

    return ""


def load_sales_strategy() -> str:
    """加载销售策略框架文档"""
    notes = get_notes_path()
    sales_file = notes / "maas_sales_advice_ethan_2026.md"
    if sales_file.exists():
        return sales_file.read_text(encoding="utf-8")
    return ""


def load_competitive_analysis(model_name: str) -> str:
    """加载与模型相关的竞品分析文档"""
    comp_dir = get_alibaba_hub_path() / "competitive-analysis"
    if not comp_dir.exists():
        return ""

    model_lower = model_name.lower()
    keywords = _extract_keywords(model_lower)
    results = []

    for md_file in comp_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        content = md_file.read_text(encoding="utf-8")
        # 检查文件名或内容中是否包含模型相关关键词
        if any(kw in md_file.stem.lower() or kw in content.lower()[:500]
               for kw in keywords if len(kw) > 2):
            results.append(content)

    return "\n\n---\n\n".join(results)


def list_available_models() -> list[str]:
    """列出本地知识库中有文档的模型/产品"""
    maas_dir = get_alibaba_hub_path() / "maas"
    models = []
    if maas_dir.exists():
        for f in maas_dir.iterdir():
            if f.suffix == ".md" and not f.name.startswith("_"):
                models.append(f.stem)
    return models


def _extract_keywords(model_name: str) -> list[str]:
    """从模型名中提取搜索关键词"""
    import re
    # 移除常见分隔符，按段拆分
    parts = re.split(r"[-_.\s]+", model_name)
    # 合并：保留完整名（如 "qwen"）和版本片段
    keywords = [p for p in parts if p]
    # 也加入整体名的主要部分（如 "qwen3" from "qwen3.7-max"）
    main_name = re.match(r"([a-z]+)", model_name)
    if main_name:
        keywords.append(main_name.group(1))
    return list(set(keywords))


def _matches_keywords(filename: str, keywords: list[str]) -> bool:
    """检查文件名是否匹配关键词"""
    # 主模型名（第一个纯字母关键词）必须匹配
    alpha_keywords = [k for k in keywords if k.isalpha() and len(k) > 2]
    if alpha_keywords:
        if not any(k in filename for k in alpha_keywords):
            return False
    return True
