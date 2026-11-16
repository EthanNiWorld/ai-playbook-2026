"""补充探测：qwen4-max max_tokens 超大值的真实拒绝边界（新加坡端点）。"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST"),
    base_url=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL"),
    timeout=120,
)
PROMPT = [{"role": "user", "content": "用一句话介绍长城。"}]

CASES = [
    ("非思考 max_tokens=1000000", {"max_tokens": 1000000, "extra_body": {"enable_thinking": False}}),
    ("思考 max_tokens=1000000", {"max_tokens": 1000000, "extra_body": {"reasoning_effort": "low"}}),
    ("思考 max_tokens=131073", {"max_tokens": 131073, "extra_body": {"reasoning_effort": "low"}}),
    ("思考 max_tokens=393216(preview档)", {"max_tokens": 393216, "extra_body": {"reasoning_effort": "low"}}),
]
for name, kw in CASES:
    print("=" * 60)
    print(name)
    try:
        resp = client.chat.completions.create(model="qwen4-max", messages=PROMPT, **kw)
        ch = resp.choices[0]
        print(f"✅ 接受 | finish_reason={ch.finish_reason} | completion={resp.usage.completion_tokens}")
    except Exception as e:
        print(f"❌ 拒绝: {type(e).__name__}: {str(e)[:300]}")

# ── F. 多轮 preserve_thinking：历史 assistant 无 reasoning_content ──
HISTORY = [
    {"role": "user", "content": "用一句话介绍长城。"},
    {"role": "assistant", "content": "长城是中国古代的军事防御工程。"},
    {"role": "user", "content": "它有多长？一句话回答。"},
]
for name, extra in [
    ("F1 默认preserve_thinking，历史无reasoning_content", {"reasoning_effort": "low"}),
    ("F2 显式preserve_thinking=False", {"reasoning_effort": "low", "preserve_thinking": False}),
]:
    print("=" * 60)
    print(name)
    try:
        resp = client.chat.completions.create(model="qwen4-max", messages=HISTORY, max_tokens=2048, extra_body=extra)
        ch = resp.choices[0]
        print(f"✅ 接受 | finish_reason={ch.finish_reason} | content={ch.message.content[:60]!r}")
    except Exception as e:
        print(f"❌ 拒绝: {type(e).__name__}: {str(e)[:300]}")

# ── G. 紧预算+xhigh：思考是否被 max_tokens 压制 ──
print("=" * 60)
print("G1 xhigh + max_tokens=200 + 复杂问题")
try:
    resp = client.chat.completions.create(
        model="qwen4-max",
        messages=[{"role": "user", "content": "一个房间里有3个人，走了2人，又来了5人，现在几人？"}],
        max_tokens=200,
        extra_body={"reasoning_effort": "xhigh"},
    )
    ch = resp.choices[0]
    u = resp.usage
    print(f"✅ finish_reason={ch.finish_reason} | completion={u.completion_tokens} reasoning={u.completion_tokens_details.reasoning_tokens}")
    print(f"   content={ch.message.content[:60]!r}")
except Exception as e:
    print(f"❌ {type(e).__name__}: {str(e)[:300]}")