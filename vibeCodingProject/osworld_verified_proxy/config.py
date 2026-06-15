"""OSWorld-Verified 代理测试配置。

所有敏感信息（API Key）均从环境变量读取，不硬编码。
"""
import os

# DashScope / 百炼 OpenAI 兼容接口
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 默认测试模型
DEFAULT_MODELS = [
    "qwen3.7-plus",
    "qwen3.7-max-2026-06-08",
]

# 路径配置（均使用相对路径，确保可移植）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# 截图尺寸（1024x768 在 vision token 成本与可读性之间取得平衡）
SCREENSHOT_WIDTH = 1024
SCREENSHOT_HEIGHT = 768

# 模型调用参数
MAX_TOKENS = 1024
TEMPERATURE = 0.2
TOP_P = 0.95
