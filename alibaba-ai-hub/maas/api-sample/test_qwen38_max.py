"""
测试 qwen3.8-max 调用情况：
  1. 纯文本调用
  2. 视觉输入（VL 能力验证）
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

# 国际站新加坡节点（知识库定价主口径节点）
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST"),
    base_url=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL"),
)

CANDIDATE_MODELS = ["qwen3.8-max"]
IMAGE_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"

alive_model = None

# ── 测试1: 模型名探测 + 纯文本调用 ──
for model in CANDIDATE_MODELS:
    print("=" * 60)
    print(f"测试1: 纯文本调用 model={model}")
    print("=" * 60)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你是什么模型？请说明你的名称、参数规模和发布时间。用一句话回答。"},
            ],
            max_tokens=200,
        )
        text = resp.choices[0].message.content
        print(f"✅ 调用成功: {text}")
        alive_model = model
        break
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {e}")

if alive_model is None:
    print("\n所有候选模型名均调用失败，测试终止")
    raise SystemExit(0)

# ── 测试2: 视觉输入（VL 能力验证） ──
print("\n" + "=" * 60)
print(f"测试2: 视觉输入 model={alive_model}")
print("=" * 60)
try:
    resp = client.chat.completions.create(
        model=alive_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": IMAGE_URL}},
                    {"type": "text", "text": "请描述这张图片的内容，两句话以内。"},
                ],
            },
        ],
        max_tokens=200,
    )
    print(f"✅ VL 支持: {resp.choices[0].message.content}")
except Exception as e:
    print(f"❌ 视觉输入失败（可能不支持 VL）: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
