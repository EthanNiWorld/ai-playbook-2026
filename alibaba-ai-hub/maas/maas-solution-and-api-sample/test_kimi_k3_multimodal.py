"""测试 kimi 系列多模态能力（图片/视频输入）— MaaS 专属端点

背景：Kimi 官方口径为原生多模态（文本 + 图像 + 视频），但 Moonshot 官方 API
约束视觉输入仅支持 base64 / ms:// 文件 ID，不支持公网 URL。本脚本实测阿里云
MaaS 专属端点（cn-beijing workspace 网关）上各 kimi 模型的实际表现。
被测模型由环境变量 TEST_MODEL 控制，默认 kimi-k3.1-pro（可切 kimi-k3 / kimi-k2.6 对比）：

  Case 0: 文本连通性（排除 404 / product_not_activated）
  Case 1: 图片 base64（本地截图 → data URL）
  Case 2: 图片公网 URL（百炼官方示例图 dog_and_girl.jpeg）
  Case 3: 视频 base64（本地 mp4 前 6 秒 → data URL）
  Case 4: 视频公网 URL（百炼官方示例视频 1.mp4，字符串格式）
  Case 4b: 视频公网 URL（官方嵌套格式 {"video_url": {"url": ...}} + fps=2）
  Case 5: 对照组 — 同端点 qwen3.8-max 测视频（排除端点链路问题）
  Case 6: 对照组 — kimi-k2.6 测视频（含 fps=2，官方嵌套格式）

实测结论 A — kimi-k3.1-pro（2026-11-05，北京 workspace 端点）：
  图片 base64 ✅ | 图片 URL ✅ | 视频 base64 ❌ | 视频 URL ❌ | 视频嵌套+fps ❌
  视频一律报 400 "Video inputs are not supported by this model"；
  对照组 qwen3.8-max / kimi-k2.6 视频均正常 → 系百炼 kimi-k3.1-pro 部署层
  限制（与 k3 一致），非端点链路问题。
  注：K3.1 Pro 官方多模态口径为“文本 + 图片 + 视频”（kimi.com 博客），
  但百炼 MaaS 端点上视频未开放，售前口径以实测为准。

实测结论 B — kimi-k3（2026-08-24，三个 MaaS 端点交叉验证：
北京 workspace×2 + 新加坡节点，结论一致）：
  kimi-k3：图片 base64 ✅ | 图片 URL ✅ | 视频 base64 ❌ | 视频 URL ❌
  视频报同一 400 错误，字符串格式与官方嵌套格式（含 fps）均被拒；
  **同端点 kimi-k2.6 / kimi-k2.7-code 视频输入均正常**（嵌套格式含 fps
  均通过，k2.6 字符串格式也可）→ 视频不支持系 k3 系列专属限制；
  客户需 kimi + 视频理解时引导用 kimi-k2.6 / kimi-k2.7-code。
  归因（2026-09-07 调研）：K3 开源权重官方口径 Modality 仅 Text + Image，
  视频不存在于模型本身；Moonshot 官方托管 API 例外支持视频（ms:// file-id）。
  另：文档称图片仅支持 URL 不支持 base64，实测 k3 / k3.1-pro base64 均可用。

限流说明：该端点并发配额较紧，密集连跑易触发 429 Throttling.ResourceExhausted，
脚本已内置 429 自动重试（3 次，退避 8/16/24s）。

端点与凭证：DASHSCOPE_API_KEY_CN_TEST + DASHSCOPE_API_KEY_CN_URL（.env，sk-ws- 前缀）
模型 ID：kimi-k3.1-pro / kimi-k3（MaaS 专属端点上无 kimi/ 前缀；标准百炼端点为 kimi/kimi-k3）
参考文档: https://help.aliyun.com/zh/model-studio/vision
"""
from openai import OpenAI
import base64
import os
import time

# 加载 .env 文件（.env 已被 .gitignore 忽略，密钥不会进 Git）
# 采用直接覆盖策略，让 .env 的最新值生效（避免 shell 中旧值干扰）
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()  # 覆盖，让 .env 优先

API_KEY = os.getenv("DASHSCOPE_API_KEY_CN_TEST", "").strip()
BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_URL", "").strip() or \
    "https://llm-7ufq8xadyf99jlbp.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
MODEL = os.getenv("TEST_MODEL", "kimi-k3.1-pro").strip()  # MaaS 专属端点上的模型 ID（无 kimi/ 前缀）

REPO_ROOT = os.path.dirname(env_path)
IMG_LOCAL = os.path.join(REPO_ROOT, "alibaba-ai-hub/ai-coding/images/ask-mode.png")
VIDEO_LOCAL = "/tmp/kimi_test_clip.mp4"  # 矿山安全 demo 前 6 秒（ffmpeg 预截取）
if not os.path.exists(VIDEO_LOCAL):
    VIDEO_LOCAL = os.path.join(REPO_ROOT, "alibaba-ai-hub/ai-industry-solutions/mining-safety-ai-demo-20260716.mp4")
IMG_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
VIDEO_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241115/cqqkru/1.mp4"


def b64_data_url(path, mime):
    """本地文件 → base64 data URL"""
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def run_case(name, content, model=MODEL):
    """执行单个多模态用例，流式收集思考与回复（429 限流自动重试）"""
    print(f"\n{'=' * 20} {name} {'=' * 20}")
    t0 = time.time()
    for attempt in range(3):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                stream=True,
            )
            reasoning_len, reply = 0, []
            for chunk in completion:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        reasoning_len += len(delta.reasoning_content)
                    if hasattr(delta, "content") and delta.content:
                        reply.append(delta.content)
            text = "".join(reply)
            ms = (time.time() - t0) * 1000
            if text.strip():
                print(f"✅ PASS（{ms:.0f}ms，思考 {reasoning_len} 字）")
                show = text if len(text) <= 600 else text[:600] + " …[截断]"
                print(f"回复：{show}")
            else:
                print(f"⚠️ 无正文输出（{ms:.0f}ms，思考 {reasoning_len} 字）— 可能被思考 token 耗尽")
            return True
        except Exception as e:
            if "429" in str(e) or "Throttling" in str(e):
                wait = 8 * (attempt + 1)
                print(f"⏳ 429 限流，{wait}s 后重试（第 {attempt + 1}/3 次）")
                time.sleep(wait)
                continue
            ms = (time.time() - t0) * 1000
            print(f"❌ FAIL（{ms:.0f}ms）：{type(e).__name__}")
            print(f"   {e}")
            return False
    print("❌ FAIL：429 限流重试 3 次仍失败")
    return False


print(f"Base URL: {BASE_URL}")
print(f"Model:    {MODEL}")
print(f"API Key:  {(API_KEY[:8] + '...' + API_KEY[-4:]) if len(API_KEY) > 12 else '(未设置)'}")
print(f"图片素材: {IMG_LOCAL}（{os.path.getsize(IMG_LOCAL) // 1024}KB）")
print(f"视频素材: {VIDEO_LOCAL}（{os.path.getsize(VIDEO_LOCAL) // 1024}KB）")
print("=" * 60)

if not API_KEY:
    print("\n❌ 未检测到环境变量 DASHSCOPE_API_KEY_CN_TEST（.env）")
    raise SystemExit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=300)

results = {}

# Case 0: 文本连通性（确认模型 ID 在该端点可用，排除 404/product_not_activated）
results["文本连通"] = run_case(
    "Case 0: 文本连通性",
    [{"type": "text", "text": "回复两个字：收到"}],
)

# Case 1: 图片 base64
results["图片 base64"] = run_case(
    "Case 1: 图片 base64",
    [
        {"type": "text", "text": "用两三句话描述这张截图里的主要界面元素。"},
        {"type": "image_url", "image_url": {"url": b64_data_url(IMG_LOCAL, "image/png")}},
    ],
)

# Case 2: 图片公网 URL
results["图片 URL"] = run_case(
    "Case 2: 图片公网 URL",
    [
        {"type": "text", "text": "用两三句话描述这张图片的内容。"},
        {"type": "image_url", "image_url": {"url": IMG_URL}},
    ],
)

# Case 3: 视频 base64
results["视频 base64"] = run_case(
    "Case 3: 视频 base64",
    [
        {"type": "text", "text": "用两三句话描述这段视频里出现的场景和内容。"},
        {"type": "video_url", "video_url": b64_data_url(VIDEO_LOCAL, "video/mp4")},
    ],
)

# Case 4: 视频公网 URL
results["视频 URL"] = run_case(
    "Case 4: 视频公网 URL",
    [
        {"type": "text", "text": "用两三句话描述这段视频里出现的场景和内容。"},
        {"type": "video_url", "video_url": VIDEO_URL},
    ],
)

# Case 4b: 视频公网 URL（官方嵌套格式 + fps），kimi 系列推荐的视频写法
results["视频 URL(嵌套+fps)"] = run_case(
    "Case 4b: 视频公网 URL（嵌套格式+fps）",
    [
        {"type": "video_url", "video_url": {"url": VIDEO_URL}, "fps": 2},
        {"type": "text", "text": "用两三句话描述这段视频里出现的场景和内容。"},
    ],
)

# Case 5: 对照组 — 同端点多模态 Qwen 模型测视频，若通过则说明
# 端点视频链路正常，kimi-k3 视频失败系模型部署限制
results["对照 qwen3.8-max 视频"] = run_case(
    "Case 5: 对照 qwen3.8-max 视频 URL",
    [
        {"type": "video_url", "video_url": VIDEO_URL},
        {"type": "text", "text": "用一句话描述这段视频的内容。"},
    ],
    model="qwen3.8-max",
)

# Case 6: 对照组 — kimi-k2.6 官方嵌套格式（含 fps），实测视频正常，
# 证明视频不支持系 kimi-k3 专属限制而非 kimi 系列整体问题
results["对照 kimi-k2.6 视频"] = run_case(
    "Case 6: 对照 kimi-k2.6 视频 URL（嵌套格式+fps）",
    [
        {"type": "video_url", "video_url": {"url": VIDEO_URL}, "fps": 2},
        {"type": "text", "text": "用一句话描述这段视频的内容。"},
    ],
    model="kimi-k2.6",
)

print("\n" + "=" * 20 + "结论汇总" + "=" * 20)
for k, v in results.items():
    print(f"  {k}: {'✅ 支持' if v else '❌ 不支持/失败'}")
