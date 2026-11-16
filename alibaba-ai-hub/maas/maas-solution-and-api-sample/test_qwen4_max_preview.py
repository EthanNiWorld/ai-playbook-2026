"""
测试 Qwen4-Max 在百炼的上架与可调用情况（正式版 qwen4-max + 预览版 qwen4-max-preview）。

实测结论（2026-11-16）：正式版 qwen4-max 在 CN / 国际站新加坡 / 国际站北京三端点均调通；
预览版仅 Token Plan 可调用，按量密钥 403。详见同目录 results_20261116.md。

官方文档：
  - 正式版 https://help.aliyun.com/zh/model-studio/qwen4-max
  - 预览版 https://help.aliyun.com/zh/model-studio/qwen4-max-preview
    （预览期 2026-11-11 ~ 11-25，仅 Token Plan，专用 Base URL token-plan.cn-beijing.maas.aliyuncs.com）
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

ENDPOINTS = [
    ("CN 常规端点", os.getenv("DASHSCOPE_API_KEY_CN_TEST"), os.getenv("DASHSCOPE_API_KEY_CN_URL")),
    ("国际站新加坡", os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST"), os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL")),
    ("国际站北京", os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST"), os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST_URL")),
    ("Token Plan 专用端点", os.getenv("DASHSCOPE_API_KEY_CN_TEST"), "https://token-plan.cn-beijing.maas.aliyuncs.com/v1"),
]

CANDIDATE_MODELS = ["qwen4-max", "qwen4-max-preview", "qwen4.0-max"]

for ep_name, api_key, base_url in ENDPOINTS:
    if not api_key or not base_url:
        print(f"⚠️ 跳过 {ep_name}：缺少密钥或 URL 配置")
        continue
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60)
    for model in CANDIDATE_MODELS:
        print("=" * 60)
        print(f"端点: {ep_name} | model={model}")
        print("=" * 60)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "你是什么模型？一句话回答。"}],
                max_tokens=2048,  # 思考+回答共享预算，预留充足
                extra_body={"reasoning_effort": "low"},
            )
            msg = resp.choices[0].message
            print(f"✅ 调用成功: {msg.content}")
            print(f"   usage: {resp.usage}")
        except Exception as e:
            print(f"❌ 失败: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)