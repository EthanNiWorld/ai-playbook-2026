"""环境与凭证配置：从仓库根目录 .env 读取（禁止硬编码密钥）。

北京节点（cn-beijing）使用 workspace 专属端点：
- OpenAI 兼容模式（qwen4-max 文本/多模态）：DASHSCOPE_API_KEY_CN_URL（.../compatible-mode/v1）
- DashScope 原生异步任务（图像/视频生成）：由 compatible-mode URL 推导出 .../api/v1

Key 与端点必须成对使用（sk-ws- 前缀 Key 打到非配套端点会 401/403）。
"""
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ENV_FILE = os.path.join(PROJECT_DIR, "..", "..", ".env")


def load_repo_env():
    """手动解析仓库根 .env（不依赖 python-dotenv），已设置的环境变量不覆盖。"""
    if not os.path.exists(REPO_ENV_FILE):
        return
    with open(REPO_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_repo_env()

# 北京节点 workspace Key（按量计费测试 Key）
API_KEY = os.getenv("DASHSCOPE_API_KEY_CN_TEST", "").strip()
# OpenAI 兼容端点（chat/completions）
OPENAI_BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_URL", "").strip()
# DashScope 原生 API 端点：.../compatible-mode/v1 -> .../api/v1
NATIVE_BASE_URL = (
    OPENAI_BASE_URL.replace("/compatible-mode/v1", "/api/v1")
    if OPENAI_BASE_URL
    else "https://dashscope.aliyuncs.com/api/v1"
)

# 主模型（可通过环境变量覆盖，便于探测不同候选）
LLM_MODEL = os.getenv("SDP_LLM_MODEL", "qwen4-max")
IMAGE_MODEL = os.getenv("SDP_IMAGE_MODEL", "qwen-image-3.0-pro")
# 限流降级链：3.0-pro → 3.0（同代非 pro，额度独立）→ 2.1 系 → wan 系（异步路径）
IMAGE_MODEL_FALLBACKS = ["qwen-image-3.0", "qwen-image-2.1-pro", "qwen-image-2.1-turbo", "wan2.7-image-pro"]
# 2026-11-20 起默认 prime（用户指定，画质增强档，480P 列表价 $0.068/s vs 标准 $0.05/s）
VIDEO_MODEL = os.getenv("SDP_VIDEO_MODEL", "wan3.0-video-prime")
VIDEO_MODEL_FALLBACKS = ["wan3.0-video", "wan2.7-i2v", "wan2.7-t2v"]
VIDEOEDIT_MODEL = os.getenv("SDP_VIDEOEDIT_MODEL", "wan2.7-videoedit")

OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")


def check_credentials() -> bool:
    if not API_KEY:
        print("❌ 未找到环境变量 DASHSCOPE_API_KEY_CN_TEST（北京节点 workspace Key）")
        return False
    if not OPENAI_BASE_URL:
        print("❌ 未找到环境变量 DASHSCOPE_API_KEY_CN_URL（配套 workspace 端点）")
        return False
    return True
