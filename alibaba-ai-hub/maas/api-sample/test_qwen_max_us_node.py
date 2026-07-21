"""
测试 qwen3.7-max-2026-06-08 美国节点（International）调用情况
base_url = https://dashscope-us.aliyuncs.com/compatible-mode/v1
key = DASHSCOPE_API_KEY_US (来自 .env)

测试三个场景：
  1. 纯文本 + response_format=json_object
  2. 视觉输入 + response_format=json_object
  3. 视觉输入 + prompt 中要求 JSON（兜底方案）
"""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# 加载项目根目录 .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY_US"),
    base_url="https://dashscope-us.aliyuncs.com/compatible-mode/v1",
)

MODEL = "qwen3.7-max-2026-06-08"
IMAGE_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"

# ──────────────────────────────────────────────
# 测试1: 纯文本 + JSON Mode
# ──────────────────────────────────────────────
print("=" * 60)
print("测试1: 纯文本 + response_format=json_object")
print("=" * 60)
try:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "请从用户输入中抽取姓名和年龄，以JSON格式返回"},
            {"role": "user", "content": "大家好，我叫张三，今年28岁，在北京做AI开发"},
        ],
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content
    print(f"返回内容: {text}")
    parsed = json.loads(text)
    print(f"JSON解析成功: {parsed}")
except Exception as e:
    print(f"❌ 失败: {type(e).__name__}: {e}")

# ──────────────────────────────────────────────
# 测试2: 视觉输入 + JSON Mode
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("测试2: 视觉输入 + response_format=json_object")
print("=" * 60)
try:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "请分析图片内容，以JSON格式返回，包含以下字段：scene(场景描述)、subjects(主体列表)、mood(氛围情绪)",
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": IMAGE_URL}},
                    {"type": "text", "text": "请分析这张图片，以JSON格式返回"},
                ],
            },
        ],
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content
    print(f"返回内容: {text}")
    parsed = json.loads(text)
    print(f"JSON解析成功: {parsed}")
except Exception as e:
    print(f"❌ 失败: {type(e).__name__}: {e}")

# ──────────────────────────────────────────────
# 测试3: 视觉输入 + prompt 要求 JSON（不用 response_format）
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("测试3: 视觉输入 + prompt 要求 JSON（兜底方案）")
print("=" * 60)
try:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": IMAGE_URL}},
                    {
                        "type": "text",
                        "text": (
                            "请分析这张图片，严格按以下JSON格式返回，不要输出任何其他内容：\n"
                            '{"scene": "场景描述", "subjects": ["主体1", "主体2"], "mood": "氛围情绪"}'
                        ),
                    },
                ],
            },
        ],
    )
    text = resp.choices[0].message.content
    print(f"返回内容: {text}")
    # 尝试解析（可能被 ```json 包裹）
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(clean)
    print(f"JSON解析成功: {parsed}")
except json.JSONDecodeError as e:
    print(f"⚠️ 返回了内容但不是合法JSON: {e}")
    print(f"原始内容: {text}")
except Exception as e:
    print(f"❌ 失败: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
