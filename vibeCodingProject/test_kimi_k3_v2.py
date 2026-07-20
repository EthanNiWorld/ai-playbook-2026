"""测试 kimi-k3 模型可用性（阿里云百炼）

Kimi K3 于 2026-07-17 正式发布（2.8 万亿参数，100 万上下文，原生视觉）。
阿里云百炼已于近期上架，关键约束：
  1) 模型 ID：kimi/kimi-k3（带 kimi/ 前缀，不是 kimi-k3）
  2) 仅支持华北2（北京）地域的 API Key
  3) 需在百炼控制台搜索 Kimi → 立即开通该模型
  4) 仅支持思考模式，reasoning_effort 仅可为 'max'
  5) temperature 固定 1.0、top_p 固定 0.95

参考文档: https://help.aliyun.com/zh/model-studio/kimi-api-by-moonshot-ai
参考脚本: test_kimi_k27_code.py
"""
from openai import OpenAI
import os
import time

# 加载 .env 文件（.env 已被 .gitignore 忽略，密钥不会进 Git）
# 采用直接覆盖策略，让 .env 的最新值生效（避免 shell 中旧值干扰）
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()  # 覆盖，让 .env 优先

# 从环境变量读取百炼密钥（.gitignore 已忽略 .env，密钥不得硬编码）
API_KEY = os.getenv("DASHSCOPE_API_KEY_CN", "").strip()
# 优先使用北京地域专属网关 Host（DASHSCOPE_API_KEY_CN_Host）
# 否则 fallback 到通用 dashscope.aliyuncs.com 端点
BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_Host", "").strip() or "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "kimi/kimi-k3"  # 百炼上的模型 ID 带 kimi/ 前缀

print(f"Base URL: {BASE_URL}")
print(f"Model:    {MODEL}")
print(f"API Key:  {(API_KEY[:8] + '...' + API_KEY[-4:]) if len(API_KEY) > 12 else '(未设置)'}")
print("=" * 60)

if not API_KEY:
    print("\n❌ 未检测到环境变量 DASHSCOPE_API_KEY_CN")
    print("   请先 export DASHSCOPE_API_KEY_CN=你的百炼密钥")
    raise SystemExit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

messages = [{"role": "user", "content": "你是谁？用一句话回答"}]

try:
    t0 = time.time()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=True,
        extra_body={"reasoning_effort": "max"},  # kimi-k3 仅支持 max
    )
    is_answering = False
    first_chunk_ms = None
    full_reply = []
    print("\n" + "=" * 20 + "思考过程" + "=" * 20)
    for chunk in completion:
        if first_chunk_ms is None:
            first_chunk_ms = (time.time() - t0) * 1000
        if chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                if not is_answering:
                    print(delta.reasoning_content, end="", flush=True)
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    print("\n" + "=" * 20 + "完整回复" + "=" * 20)
                    is_answering = True
                print(delta.content, end="", flush=True)
                full_reply.append(delta.content)
    total_ms = (time.time() - t0) * 1000
    print(f"\n\n✅ 测试通过：{MODEL} 在阿里云百炼调用成功")
    print(f"   首 chunk 延迟: {first_chunk_ms:.0f}ms | 总耗时: {total_ms:.0f}ms")
except Exception as e:
    err_ms = (time.time() - t0) * 1000
    print(f"\n❌ 测试失败（{err_ms:.0f}ms）：{type(e).__name__}: {e}")
    print("\n💡 常见原因：")
    print("   1) 403 model_access_denied → 当前账号未在百炼控制台开通 Kimi 模型")
    print("      解决：百炼控制台 → 搜索 Kimi → 找到 kimi-k3 卡片 → 立即开通")
    print("   2) 403 model_access_denied → 使用的 API Key 非华北2（北京）地域")
    print("      解决：使用华北2（北京）地域获取的 API Key")
    print("   3) 404 model_not_found → 模型 ID 写错（应为 kimi/kimi-k3，带前缀）")
    print("\n   如百炼暂不可用，可用 Kimi 官方 API：")
    print("   - Base URL: https://api.moonshot.cn/v1")
    print("   - Model:    kimi-k3 (无前缀)")
    print("   - 需要 MOONSHOT_API_KEY 环境变量")
