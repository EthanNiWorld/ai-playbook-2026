"""
配置管理 — 环境变量、路径、默认值（所有路径动态推导，无硬编码绝对路径）
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # 未装 python-dotenv 时退化为仅读进程环境变量
    load_dotenv = None

# 项目根目录 = app/ 的上一级
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 项目本地 .env（可选；不存在则静默跳过）
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

# ── 知识来源（GitHub 仓库的两个目录）──
# 注：以下均用 `or 默认值` 而非 getenv 的第二个参数 —— Docker Compose 会把未设置的
# 变量透传为空字符串，此时 getenv 会返回 "" 而不是默认值。
REPO_URL = os.getenv("KNOWLEDGE_REPO_URL") or "https://github.com/EthanNiWorld/ai-playbook-2026.git"


def get_repo_url() -> str:
    """知识库仓库 URL（允许测试时替换）"""
    return REPO_URL

REPO_BROWSE_URL = REPO_URL.replace(".git", "").rstrip("/")
SPARSE_DIRS = ("alibaba-ai-hub", "knowledge/ai-general-notes")
# 克隆模式下距上次同步超过该小时数才自动 git pull（手动同步不受限）
KB_SYNC_INTERVAL_HOURS = float(os.getenv("KB_SYNC_INTERVAL_HOURS") or "24")

# ── 价格校验 ──
# 口径：阿里云国际站（新加坡节点）USD 列表价；alibabacloud.com 为静态页可直接抓取
PRICE_PAGE_URL = "https://www.alibabacloud.com/help/en/model-studio/model-pricing"
PRICE_PAGE_TTL_HOURS = float(os.getenv("PRICE_PAGE_TTL_HOURS", "6"))


def get_data_dir() -> Path:
    """运行时数据目录（知识库克隆、缓存、SQLite），Docker 中挂载为卷"""
    d = PROJECT_ROOT / "data"
    d.mkdir(exist_ok=True)
    return d


def get_cache_dir() -> Path:
    c = get_data_dir() / "cache"
    c.mkdir(exist_ok=True)
    return c


def get_db_path() -> Path:
    return get_data_dir() / "qa.db"


def get_llm_config() -> dict:
    """LLM 调用配置（DASHSCOPE_API_KEY 优先，兼容 _INTL 后缀变量名）"""
    return {
        "api_key": os.getenv("DASHSCOPE_API_KEY") or os.getenv("DASHSCOPE_API_KEY_INTL", ""),
        "base_url": os.getenv("DASHSCOPE_BASE_URL")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": os.getenv("QA_MODEL") or "qwen3.8-max",
    }


def get_tavily_api_key() -> str:
    """Tavily Key（空表示未配置，联网搜索降级为 DuckDuckGo）"""
    return os.getenv("TAVILY_API_KEY", "")


# ── 价格分享卡片（OSS 私有 Bucket + 24h 签名链接）──
# 变量名沿用工作区 .env 既有约定（与 cosyvoice_demo 共用同一对受限 RAM key）
OSS_SHARE_PREFIX = "presale-agent/price-cards/"


def get_oss_config() -> dict:
    """OSS 配置（key 为空表示未配置，分享卡片工具返回 error 由 LLM 说明）"""
    return {
        "key_id": os.getenv("oss_AccessKey_ID", ""),
        "key_secret": os.getenv("oss_AccessKey_key", ""),
        "bucket": os.getenv("OSS_BUCKET_NAME") or "Bucket_for_ai_project",
        "endpoint": os.getenv("OSS_ENDPOINT") or "https://oss-cn-beijing.aliyuncs.com",
        "prefix": OSS_SHARE_PREFIX,
    }


def get_admin_token() -> str:
    """后台保护令牌（空表示不启用鉴权，仅建议内网/测试环境留空）"""
    return os.getenv("ADMIN_TOKEN", "")
