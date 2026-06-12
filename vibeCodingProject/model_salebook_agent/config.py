"""
配置管理 — 环境变量读取、路径管理、默认值
"""

import os
from pathlib import Path


# 可选底层 LLM （SA/BD 可在 main/web 启动时选择）
MODEL_OPTIONS = [
    "qwen3.7-max",       # 默认：能力天花板
    "qwen3.7-plus",      # 性价比
    "deepseek-v4-pro",   # 备选
]
DEFAULT_MODEL = "qwen3.7-max"

# 运行时模型覆盖（优先级高于环境变量 SALEBOOK_MODEL）
_RUNTIME_MODEL_OVERRIDE: str | None = None


def set_runtime_model(model_id: str) -> None:
    """运行时覆盖底层 LLM，供 main.py / web.py 选择使用"""
    global _RUNTIME_MODEL_OVERRIDE
    if model_id and model_id in MODEL_OPTIONS:
        _RUNTIME_MODEL_OVERRIDE = model_id


def get_project_root() -> Path:
    """返回 model_salebook_agent 项目根目录"""
    return Path(__file__).parent


def get_knowledge_base_path() -> Path:
    """返回 knowledge/ 目录绝对路径"""
    env_path = os.getenv("KNOWLEDGE_BASE_PATH")
    if env_path:
        return Path(env_path)
    # 默认：向上推导到 ai-knowledge-base 仓库根目录
    return get_project_root().parent.parent / "knowledge"


def get_notes_path() -> Path:
    """返回 notes/ 目录绝对路径"""
    return get_knowledge_base_path().parent / "notes"


def get_output_path() -> Path:
    """返回 output/ 目录"""
    out = get_project_root() / "output"
    out.mkdir(exist_ok=True)
    return out


def get_log_path() -> Path:
    """返回 output/log/ 目录（会话对话日志，供审计/反补知识库）"""
    log = get_output_path() / "log"
    log.mkdir(exist_ok=True)
    return log


def get_llm_config() -> dict:
    """返回 LLM 调用配置

    模型优先级：运行时覆盖 > SALEBOOK_MODEL 环境变量 > DEFAULT_MODEL
    """
    model = (
        _RUNTIME_MODEL_OVERRIDE
        or os.getenv("SALEBOOK_MODEL")
        or DEFAULT_MODEL
    )
    return {
        "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
        "base_url": os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        "model": model,
    }


def get_tavily_api_key() -> str:
    """返回 Tavily API Key（空字符串表示未配置，降级为 DuckDuckGo）"""
    return os.getenv("TAVILY_API_KEY", "")
