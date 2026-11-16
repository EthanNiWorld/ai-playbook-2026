"""
实测 qwen4-max 最大输出 token 边界与迁移注意点（国际站新加坡端点）。

官方文档口径（https://help.aliyun.com/zh/model-studio/qwen4-max）：
  - 最大输出（非思考模式）：131,072
  - 思考+回答总预算（思考模式）：262,144
  - max_tokens 与 max_completion_tokens 等价，均限制思考+回答总量
  - reasoning_effort: low/high(默认)/xhigh，medium 映射到 high

测试策略：越界参数探测（报错即返回，不产生生成费用）+ 小额截断实测。
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST"),
    base_url=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL"),
    timeout=120,
)
MODEL = "qwen4-max"
PROMPT = [{"role": "user", "content": "用一句话介绍长城。"}]


def probe(name, **kwargs):
    print("=" * 60)
    print(f"{name} | 参数: {kwargs}")
    try:
        resp = client.chat.completions.create(model=MODEL, messages=PROMPT, **kwargs)
        ch = resp.choices[0]
        u = resp.usage
        rt = getattr(u.completion_tokens_details, "reasoning_tokens", None)
        print(f"✅ 接受 | finish_reason={ch.finish_reason} | completion={u.completion_tokens} (reasoning={rt})")
        content = (ch.message.content or "")[:80]
        print(f"   content: {content!r}")
    except Exception as e:
        print(f"❌ 拒绝: {type(e).__name__}: {str(e)[:300]}")


# ── A. 非思考模式输出上限 ──
probe("A1 非思考 max_tokens=131072（文档上限，应接受）",
      max_tokens=131072, extra_body={"enable_thinking": False})
probe("A2 非思考 max_tokens=131073（越界+1）",
      max_tokens=131073, extra_body={"enable_thinking": False})
probe("A3 非思考 max_tokens=262144（思考档预算，应拒绝）",
      max_tokens=262144, extra_body={"enable_thinking": False})

# ── B. 思考模式输出上限 ──
probe("B1 思考 max_tokens=262144（文档上限，应接受）",
      max_tokens=262144, extra_body={"reasoning_effort": "low"})
probe("B2 思考 max_tokens=262145（越界+1）",
      max_tokens=262145, extra_body={"reasoning_effort": "low"})

# ── C. max_tokens 语义：思考+回答共享预算，小额截断实测 ──
probe("C1 思考开启 max_tokens=64（预期思考耗尽预算→length截断）",
      max_tokens=64, extra_body={"reasoning_effort": "low"})
probe("C2 非思考 max_tokens=64（对照：回答可完整输出）",
      max_tokens=64, extra_body={"enable_thinking": False})

# ── D. max_completion_tokens 等价性 ──
probe("D1 max_completion_tokens=262145（应与B2同样拒绝）",
      max_completion_tokens=262145, extra_body={"reasoning_effort": "low"})

# ── E. reasoning_effort 取值 ──
probe("E1 reasoning_effort=medium（文档称映射到high）",
      max_tokens=2048, extra_body={"reasoning_effort": "medium"})
probe("E2 reasoning_effort=xhigh",
      max_tokens=2048, extra_body={"reasoning_effort": "xhigh"})
probe("E3 reasoning_effort 与 thinking_budget 同设（preview文档称互斥）",
      max_tokens=2048, extra_body={"reasoning_effort": "low", "thinking_budget": 512})

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)