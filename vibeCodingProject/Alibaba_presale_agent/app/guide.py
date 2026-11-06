"""
售前指南定位 — 把知识库里的销售指南 HTML 直接挂到问答站

指南文件名带交付版本日期（如 ModelStudio-api-sales-guide-20261130.html），
每月更新会换日期、且新旧版本常会共存一段时间。因此这里不做硬编码路径，
而是 glob 同类文件后取「版本日期最新」的一个：文件名里的 YYYYMMDD 优先，
没有日期则退回文件 mtime。这样换名、加版本、留旧版都不会退化成旧稿。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from . import knowledge

log = logging.getLogger("guide")

# 知识库内的指南目录（相对仓库根，随每日自动同步更新）
GUIDE_DIR = Path("alibaba-ai-hub") / "maas" / "sales-tools"
# 由严到宽：先认标准名，退化时才认任意含 sales-guide 的 HTML
PATTERNS = ("ModelStudio-api-sales-guide-*.html", "*sales-guide*.html")
_VERSION_RE = re.compile(r"(\d{8})")


def _version_key(p: Path) -> tuple[int, float]:
    """排序键：文件名里的 YYYYMMDD 优先，缺日期的按 mtime 兜底。"""
    m = _VERSION_RE.search(p.stem)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        mtime = 0.0
    return (int(m.group(1)) if m else 0, mtime)


def guide_dir() -> Path:
    """指南所在目录（本地开发指向工作区仓库，线上指向卷内 kb 克隆）。"""
    _, root = knowledge.resolve_source_root()
    return Path(root) / GUIDE_DIR


def latest_guide() -> Path | None:
    """返回当前应展示的指南文件；知识库尚未就绪时返回 None。"""
    d = guide_dir()
    if not d.is_dir():
        return None
    for pattern in PATTERNS:
        found = {p: _version_key(p) for p in d.glob(pattern) if p.is_file()}
        if found:
            return max(found, key=found.get)
    return None
