"""
Qwen3.7-Plus 多模态理解 Demo（百炼国际站 — DashScope 原生 SDK）
- 使用 MultiModalConversation API 进行图文理解
- API Key 通过环境变量 DASHSCOPE_INTL_API_KEY 配置
"""

import os
import dashscope

# ============================================================
# 配置
# ============================================================
API_KEY = os.getenv("DASHSCOPE_INTL_API_KEY")  # 国际站 API Key

if not API_KEY:
    print("❌ 请设置环境变量: export DASHSCOPE_INTL_API_KEY=sk-xxx")
    exit(1)

# 国际站 base_http_api_url（注意与 OpenAI 兼容模式的端点不同）
dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"

# ============================================================
# 调用（多模态：图片 + 文本）
# ============================================================
messages = [
    {
        "role": "user",
        "content": [
            {"image": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"},
            {"text": "图中描绘的是什么景象?"},
        ],
    }
]

response = dashscope.MultiModalConversation.call(
    api_key=API_KEY,
    model="qwen3.7-plus",
    messages=messages,
)

# ============================================================
# 输出
# ============================================================
if response.status_code == 200:
    print("✅ 调用成功")
    print()
    print(response.output.choices[0].message.content[0]["text"])
else:
    print(f"❌ 调用失败: {response.status_code} {response.code}")
    print(f"   {response.message}")
