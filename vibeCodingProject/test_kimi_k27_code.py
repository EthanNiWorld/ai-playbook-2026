"""测试 kimi-k2.7-code 模型可用性"""
from openai import OpenAI
import os
import time

# 手动加载 .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.getenv("DASHSCOPE_API_KEY_CN_kimi")
BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_url_2.7", "").strip()

print(f"API Key: {API_KEY[:20]}...")
print(f"Base URL: {BASE_URL}")
print(f"Model: kimi-k2.7-code")
print("=" * 60)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

messages = [{"role": "user", "content": "你是谁"}]

try:
    t0 = time.time()
    completion = client.chat.completions.create(
        model="kimi-k2.7-code",
        messages=messages,
        stream=True
    )
    is_answering = False
    first_chunk_ms = None
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
    total_ms = (time.time() - t0) * 1000
    print(f"\n\n✅ 测试通过：kimi-k2.7-code 模型调用成功")
    print(f"   首chunk延迟: {first_chunk_ms:.0f}ms | 总耗时: {total_ms:.0f}ms")
except Exception as e:
    err_ms = (time.time() - t0) * 1000
    print(f"\n❌ 测试失败（{err_ms:.0f}ms）：{type(e).__name__}: {e}")
