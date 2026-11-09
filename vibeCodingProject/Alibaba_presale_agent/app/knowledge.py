"""
知识库层 — GitHub sparse-checkout 同步 + 本地/克隆模式自适应 + BM25 检索
====================================================================
知识来源（仅两个目录）：
  - alibaba-ai-hub/            阿里云百炼/模型/Agent 产品知识
  - knowledge/ai-general-notes/ AI 通识

来源解析顺序：
  1. 环境变量 LOCAL_KNOWLEDGE_PATH 指定的仓库根（须含 alibaba-ai-hub/）
  2. 从项目根向上自动探测（本地开发 = ai-knowledge-base 仓库根，零拷贝直读）
  3. 都没有 → git sparse clone 到 data/kb/（服务器部署形态）
"""

import json
import logging
import math
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

from .config import KB_SYNC_INTERVAL_HOURS, PROJECT_ROOT, SPARSE_DIRS, get_data_dir, get_repo_url

log = logging.getLogger("kb")

# ──────────────────────────── 知识同步 ────────────────────────────


def _dir_looks_like_repo_root(p: Path) -> bool:
    return (p / "alibaba-ai-hub").is_dir() and (p / "knowledge" / "ai-general-notes").is_dir()


def resolve_source_root() -> tuple[str, Path]:
    """返回 (mode, root)：mode = local（直读已有仓库）| clone（需维护 data/kb 克隆）"""
    import os

    env_path = os.getenv("LOCAL_KNOWLEDGE_PATH")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if _dir_looks_like_repo_root(p):
            return "local", p
        log.warning("LOCAL_KNOWLEDGE_PATH 配置无效（缺少 alibaba-ai-hub/ 或 knowledge/ai-general-notes/）: %s", env_path)
    # 从项目根向上探测（本地开发时命中 ai-knowledge-base 仓库根）
    for p in [PROJECT_ROOT, *PROJECT_ROOT.parents]:
        if _dir_looks_like_repo_root(p):
            return "local", p
    return "clone", get_data_dir() / "kb"


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _kb_meta_path() -> Path:
    return get_data_dir() / "kb_meta.json"


def _touch_sync_meta() -> None:
    _kb_meta_path().write_text(
        json.dumps({"last_sync": time.time()}), encoding="utf-8"
    )


def _kb_stale() -> bool:
    meta = _kb_meta_path()
    if not meta.exists():
        return True
    try:
        return time.time() - json.loads(meta.read_text()).get("last_sync", 0) > KB_SYNC_INTERVAL_HOURS * 3600
    except Exception:
        return True


def ensure_knowledge(force: bool = False) -> Path:
    """确保知识目录就绪，返回仓库根路径。

    local  模式：直读已有仓库（force 时尝试 git pull --ff-only 同步）
    clone 模式：首次 sparse clone；过期或 force 时 git pull
    任何 git 失败都只降级告警，不阻塞问答（用现有内容）。
    """
    mode, root = resolve_source_root()

    if mode == "local":
        if force and (root / ".git").exists():
            r = _run_git(["pull", "--ff-only"], cwd=root)
            if r.returncode != 0:
                log.warning("本地知识库 git pull 失败（不影响使用）: %s", r.stderr.strip()[:200])
        return root

    # clone 模式
    if not (root / ".git").exists():
        log.info("首次克隆知识库: %s（sparse: %s）", get_repo_url(), ", ".join(SPARSE_DIRS))
        root.parent.mkdir(parents=True, exist_ok=True)
        r = _run_git(["clone", "--filter=blob:none", "--sparse", get_repo_url(), str(root)])
        if r.returncode != 0:
            raise RuntimeError(f"知识库克隆失败: {r.stderr.strip()[:500]}")
        _run_git(["sparse-checkout", "set", *SPARSE_DIRS], cwd=root)
        _touch_sync_meta()
    elif force or _kb_stale():
        log.info("知识库过期/强制同步，git pull 中...")
        # 先重申 sparse 范围（幂等）：已有克隆不会自动继承新 SPARSE_DIRS，
        # 不重跑 set 的话扩目录（如新增 knowledge/ 厂商文档）永远不生效。
        _run_git(["sparse-checkout", "set", *SPARSE_DIRS], cwd=root)
        r = _run_git(["pull", "--ff-only"], cwd=root)
        if r.returncode == 0:
            _touch_sync_meta()
        else:
            log.warning("知识库 git pull 失败（沿用现有内容）: %s", r.stderr.strip()[:200])
    return root


# ──────────────────────────── BM25 检索 ────────────────────────────

_LATIN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)*")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")

# markdown 分块参数：太小→噪声多，太大→上下文稀释
_MIN_CHUNK = 350
_MAX_CHUNK = 1200


def tokenize(text: str) -> list[str]:
    """拉丁词 + 中文一元/二元 bigram（兼顾中英混排检索）"""
    t = text.lower()
    tokens = _LATIN_RE.findall(t)
    # 版本化模型名补纯字母前缀："qwen3.8" → 额外 "qwen"，让文件名 qwen.md 可命中
    for tok in tokens[:]:
        m = re.match(r"^([a-z]+)[\d.]+$", tok)
        if m:
            tokens.append(m.group(1))
    for run in _CJK_RE.findall(t):
        tokens.extend(run)
        tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def _split_chunks(text: str, relpath: str) -> list[dict]:
    """按 markdown 标题 + 长度分块，每块携带标题与来源路径"""
    chunks: list[dict] = []
    heading = ""
    buf: list[str] = []
    buf_len = 0

    def emit():
        nonlocal buf, buf_len
        body = "\n".join(buf).strip()
        buf, buf_len = [], 0
        if len(body) < 60:
            return
        first_line = body.splitlines()[0][:80]
        chunks.append({"text": body, "title": heading or first_line, "relpath": relpath})

    for line in text.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            if buf_len >= _MIN_CHUNK:
                emit()
            heading = m.group(2).strip()
        buf.append(line)
        buf_len += len(line) + 1
        if buf_len >= _MAX_CHUNK:
            emit()
    emit()
    return chunks


class KnowledgeIndex:
    """内存 BM25 索引（文档量 ~百级，无需向量库/外部服务）"""

    def __init__(self):
        self.chunks: list[dict] = []
        self._postings: dict[str, list[tuple[int, int]]] = {}
        self._idf: dict[str, float] = {}
        self._doc_len: list[int] = []
        self._avgdl: float = 0.0
        self._k1 = 1.5
        self._b = 0.75

    @property
    def size(self) -> int:
        return len(self.chunks)

    def rebuild(self, root: Path) -> int:
        """扫描 SPARSE_DIRS 下全部 .md，重建索引，返回片段数"""
        self._postings.clear()
        self._idf.clear()
        self.chunks = []
        self._doc_len = []

        for rel in SPARSE_DIRS:
            base = root / rel
            if not base.is_dir():
                log.warning("知识目录不存在: %s", base)
                continue
            for f in sorted(base.rglob("*.md")):
                if f.name.startswith("_"):  # _template.md 等模板
                    continue
                if any(part.startswith("__") for part in f.parts):  # __pycache__ 等
                    continue
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception as e:
                    log.warning("读取失败 %s: %s", f, e)
                    continue
                relpath = f.relative_to(root).as_posix()
                self.chunks.extend(_split_chunks(text, relpath))

        n = len(self.chunks)
        for i, ch in enumerate(self.chunks):
            # 正文+标题一次；来源路径额外 3 次（文件名承载模型名信号，加权提升召回精度）
            toks = tokenize(ch["text"] + " " + ch["title"]) + tokenize(ch["relpath"]) * 3
            self._doc_len.append(len(toks))
            for tok, tf in Counter(toks).items():
                self._postings.setdefault(tok, []).append((i, tf))
        self._avgdl = (sum(self._doc_len) / n) if n else 1.0
        for tok, postings in self._postings.items():
            self._idf[tok] = math.log(1 + (n - len(postings) + 0.5) / (len(postings) + 0.5))
        log.info("BM25 索引重建完成: %d 个片段（来自 %d 个 token 项）", n, len(self._postings))
        return n

    def search(self, query: str, top_k: int = 6) -> list[dict]:
        """返回按相关度排序的片段 [{text, title, relpath, score}]"""
        if not self.chunks:
            return []
        scores: dict[int, float] = {}
        for tok in set(tokenize(query)):
            postings = self._postings.get(tok)
            if not postings:
                continue
            idf = self._idf.get(tok, 0.0)
            for idx, tf in postings:
                dl = self._doc_len[idx]
                denom = tf + self._k1 * (1 - self._b + self._b * dl / self._avgdl)
                scores[idx] = scores.get(idx, 0.0) + idf * tf * (self._k1 + 1) / denom
        # 文件名主词 boost：查询含模型系列名（如 qwen3.8-max → 主词 qwen）时，
        # stem 恰为该主词的文档（maas/qwen.md）是权威文档；sales-tools 等文档虽密集
        # 提及模型名，但应排在权威文档之后，故对权威文档加权
        prefixes = {
            m.group(1)
            for tok in _LATIN_RE.findall(query.lower())
            if (m := re.match(r"^([a-z]+)", tok)) and len(m.group(1)) >= 3
        }
        if prefixes:
            for idx in scores:
                stem = Path(self.chunks[idx]["relpath"]).stem.lower()
                if stem in prefixes:
                    # 权威文档块原分低（长文档模型名分散在多块），需强拉回；
                    # 竞品/工具文档密集提及模型名但不应排在权威文档前
                    scores[idx] *= 3
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        return [{**self.chunks[i], "score": round(s, 3)} for i, s in ranked if s > 0]


# 模块级单例（服务启动时构建，/api/admin/kb/sync 时重建）
_index = KnowledgeIndex()


def get_index() -> KnowledgeIndex:
    return _index


def search_with_models(
    question: str,
    models: list[str] | None,
    top_k: int = 6,
    per_model: int = 2,
    max_total: int = 9,
) -> list[dict]:
    """整题检索 + 按题中型号补充检索。

    对比/选型题的整题 BM25 容易被单一品牌的权威文档占满（qwen.md 享受文件名
    boost×3，deepseek 的 chunk 挤不进 top-k，2026-11-10 实测 top8 全是 qwen.md）。
    对题中出现的每个型号，若其家族文档未出现在整题结果里，则单独按型号补检
    per_model 条，去重后合并，上限 max_total。
    """
    chunks = _index.search(question, top_k=top_k)
    if not models:
        return chunks
    seen = {(c["relpath"], c["title"]) for c in chunks}
    # 家族主词取型号开头纯字母段：qwen3.8-max → qwen（qwen/wan 无连字符，
    # 若用 split("-") 会得到 "qwen3"，导致已覆盖的家族被重复补检）
    families = {}
    for m in models:
        if len(m) < 5:
            continue
        fm = re.match(r"[a-z]+", m.lower())
        if fm:
            families.setdefault(fm.group(0), m)
    for fam, model in families.items():
        covered = any(
            fam in Path(c["relpath"]).stem.lower() or f"/{fam}" in c["relpath"].lower()
            for c in chunks
        )
        if covered:
            continue
        for c in _index.search(f"{model} 规格 上下文 能力", top_k=per_model):
            key = (c["relpath"], c["title"])
            if key in seen:
                continue
            seen.add(key)
            chunks.append(c)
    return chunks[:max_total]


def build_default_index() -> int:
    """启动时调用：确保知识就绪并构建索引"""
    root = ensure_knowledge()
    return _index.rebuild(root)


def sync_and_rebuild() -> int:
    """手动同步（git 拉最新）+ 重建索引，返回片段数"""
    root = ensure_knowledge(force=True)
    return _index.rebuild(root)


def sync_if_remote_changed() -> int | None:
    """检查远端是否有新提交，有才 pull 并重建索引（供定时任务调用）。

    返回重建后的片段数；无新提交 / 非 git 仓库 / git 或网络失败均返回 None，绝不抛错。
    """
    _, root = resolve_source_root()
    if not (root / ".git").exists():
        log.info("知识目录非 git 仓库（%s），自动同步跳过", root)
        return None
    r = _run_git(["fetch", "-q", "origin"], cwd=root)
    if r.returncode != 0:
        log.warning("git fetch 失败，跳过本轮自动同步: %s", r.stderr.strip()[:200])
        return None
    local = _run_git(["rev-parse", "HEAD"], cwd=root).stdout.strip()
    remote = _run_git(["rev-parse", "FETCH_HEAD"], cwd=root).stdout.strip()
    if not local or not remote:
        log.warning("无法读取 HEAD/FETCH_HEAD，跳过本轮自动同步")
        return None
    if local == remote:
        log.info("知识库远端无新提交（HEAD %s）", local[:8])
        return None
    log.info("知识库远端有新提交（%s → %s），执行 git pull...", local[:8], remote[:8])
    r = _run_git(["pull", "--ff-only"], cwd=root)
    if r.returncode != 0:
        log.warning("git pull 失败（沿用现有内容）: %s", r.stderr.strip()[:200])
        return None
    _touch_sync_meta()
    return _index.rebuild(root)
