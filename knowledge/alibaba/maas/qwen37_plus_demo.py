"""
Qwen3.7-Plus API 调用 Demo（百炼国际站）
- 支持 enable_thinking 深度思考模式
- 流式输出思考过程 + 最终回复
- API Key 通过环境变量 DASHSCOPE_INTL_API_KEY 配置
"""

from openai import OpenAI
import os
import time

# ============================================================
# 配置
# ============================================================
API_KEY = os.getenv("DASHSCOPE_INTL_API_KEY")  # 国际站 API Key
BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3.7-plus"

if not API_KEY:
    print("❌ 请设置环境变量: export DASHSCOPE_INTL_API_KEY=sk-xxx")
    exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ============================================================
# 调用
# ============================================================
messages = [{"role": "user", "content": "你是谁？请用一句话回答"}]
start = time.time()

completion = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    extra_body={"enable_thinking": True},
    stream=True,
)

# ============================================================
# 流式解析
# ============================================================
is_answering = False
thinking_text = ""
answer_text = ""
first_thinking_time = None
first_answer_time = None

print("=" * 20 + " 思考过程 " + "=" * 20)

for chunk in completion:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta

    # 思考阶段
    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
        if not is_answering:
            if first_thinking_time is None:
                first_thinking_time = time.time() - start
            print(delta.reasoning_content, end="", flush=True)
            thinking_text += delta.reasoning_content

    # 回复阶段
    if hasattr(delta, "content") and delta.content:
        if not is_answering:
            first_answer_time = time.time() - start
            print("\n" + "=" * 20 + " 完整回复 " + "=" * 20)
            is_answering = True
        print(delta.content, end="", flush=True)
        answer_text += delta.content

# ============================================================
# 统计
# ============================================================
total_time = time.time() - start
print("\n")
print("=" * 20 + " 测试统计 " + "=" * 20)
print(f"端点: {BASE_URL}")
print(f"模型: {MODEL}")
print(f"enable_thinking: True")
print(f"首 token 思考延迟: {first_thinking_time:.2f}s" if first_thinking_time else "首 token 思考延迟: N/A")
print(f"首 token 回复延迟: {first_answer_time:.2f}s" if first_answer_time else "首 token 回复延迟: N/A")
print(f"总耗时: {total_time:.2f}s")
print(f"思考内容长度: {len(thinking_text)} 字符")
print(f"回复内容长度: {len(answer_text)} 字符")
