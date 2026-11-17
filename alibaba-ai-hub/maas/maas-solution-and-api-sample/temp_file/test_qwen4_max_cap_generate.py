"""顶格生成验证 qwen4-max 非思考模式输出硬帽（新加坡端点）。

策略：enable_thinking=False + 持续数数 prompt 强制长输出，
分别设 max_tokens=131071 / 131073，观察实际 completion_tokens 与 finish_reason：
  - 若硬帽为 131072：131071 档应截断在 131071；131073 档应被钳制截断在 131072
流式消费避免长请求网关超时；每收到约 2 万 token 打一次进度。
"""
import os
import sys
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST"),
    base_url=os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL"),
    timeout=3600,
)
# 前缀补全（partial 模式）：单调递增数数无重复模式，规避模型对重复输出的停止倾向
_PREFIX = "".join(f"{i}\n" for i in range(1, 301)) + "30"
PROMPT = [
    {"role": "user", "content": "这是输出压力测试：从1连续数到60000，每行一个整数，不省略、不解释、不总结，必须数到60000才能停。"},
    {"role": "assistant", "content": _PREFIX, "partial": True},
]


def run(max_tokens):
    print(f"\n{'=' * 60}\n用例: 非思考 max_tokens={max_tokens}", flush=True)
    t0 = time.time()
    finish_reason = None
    usage = None
    chars = 0
    last_mark = 0
    stream = client.chat.completions.create(
        model="qwen4-max",
        messages=PROMPT,
        max_tokens=max_tokens,
        presence_penalty=0.0,  # 非思考默认1.5会抑制重复，置0保障持续输出
        extra_body={"enable_thinking": False},
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        if chunk.usage:
            usage = chunk.usage
        if chunk.choices:
            ch = chunk.choices[0]
            if ch.finish_reason:
                finish_reason = ch.finish_reason
            if ch.delta and ch.delta.content:
                if chars == 0:
                    print(f"  首段输出: {ch.delta.content[:40]!r}（partial生效应以 1\\n302 开头）", flush=True)
                chars += len(ch.delta.content)
                if chars - last_mark >= 40000:  # 约2万token一报
                    last_mark = chars
                    print(f"  进度: ~{chars}字符, 耗时{time.time() - t0:.0f}s", flush=True)
    dt = time.time() - t0
    print(f"结果: finish_reason={finish_reason} | 耗时{dt:.0f}s", flush=True)
    if usage:
        print(f"usage: completion_tokens={usage.completion_tokens} prompt_tokens={usage.prompt_tokens}", flush=True)
        print(f"输出速度: {usage.completion_tokens / dt:.1f} token/s", flush=True)
    return finish_reason, (usage.completion_tokens if usage else 0)


# 预检：4096 预算下必须顶到 length 才说明 prompt 能持续输出
fr, ct = run(4096)
if fr != "length":
    print(f"\n⚠️ 预检未顶格（finish_reason={fr}, completion={ct}），prompt 无法强制长输出，终止顶格用例", flush=True)
    raise SystemExit(0)

for mt in [131071, 131073]:
    try:
        run(mt)
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {str(e)[:300]}", flush=True)

print("\n全部用例完成", flush=True)