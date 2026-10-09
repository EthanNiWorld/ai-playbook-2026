"""glm-5.3 finish_reason 补充定性用例 — auto 模式 + 北京 workspace

承接 test_glm53_finish_reason.py 的发现：强制 tool_choice 下 glm-5.3 /
glm-5.2 / qwen3.8-max 的 finish_reason 均为 'stop'（标准应为 'tool_calls'），
且强制指定 get_weather 时模型实际调了两个工具（强制语义未严格执行）。

本脚本补两个定性用例：
  C5: glm-5.3 + tool_choice='auto'（自然提问）→ auto 下模型自主调用工具时
      finish_reason 是否正常为 'tool_calls'（缩小问题范围：仅强制模式异常
      还是通病）
  C6: glm-5.3 + 强制 tool_choice → 国际站北京 workspace（确认另一网关同病）

端点与凭证：DASHSCOPE_API_KEY_INTL_SG_TEST / DASHSCOPE_API_KEY_INTL_BJ_TEST（.env）
"""
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
import os

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

KEY_SG = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", "").strip()
URL_SG = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "").strip()
KEY_BJ = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST", "").strip()
URL_BJ = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST_URL", "").strip()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "查询指定城市的当前时间",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
    },
]


def run(name, base_url, key, model, messages, tool_choice):
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    client = OpenAI(api_key=key, base_url=base_url, timeout=420)
    kwargs = dict(model=model, messages=messages, tools=TOOLS)
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    try:
        resp = client.chat.completions.create(**kwargs)
        ch = resp.choices[0]
        msg = ch.message
        tcs = [f"{tc.function.name}({tc.function.arguments})" for tc in (msg.tool_calls or [])]
        print(f"  finish_reason: {ch.finish_reason!r}")
        print(f"  tool_calls   : {', '.join(tcs) if tcs else '（无）'}")
        print(f"  content      : {(msg.content or '')[:80]!r}")
        return ch.finish_reason, tcs
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:200]}")
        return None, None


if __name__ == "__main__":
    results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        f5 = pool.submit(
            run, "C5: glm-5.3 auto 模式（新加坡 workspace）", URL_SG, KEY_SG,
            "glm-5.3", [{"role": "user", "content": "请查询上海的天气和时间。"}], "auto",
        )
        f6 = pool.submit(
            run, "C6: glm-5.3 强制 tool_choice（国际站北京 workspace）", URL_BJ, KEY_BJ,
            "glm-5.3", [{"role": "user", "content": "请处理上海相关的信息。"}],
            {"type": "function", "function": {"name": "get_weather"}},
        )
        f7 = pool.submit(
            run, "C7: glm-5.3 tool_choice='required'（新加坡 workspace，workaround 探路）", URL_SG, KEY_SG,
            "glm-5.3", [{"role": "user", "content": "请处理上海相关的信息。"}], "required",
        )
        results["C5 glm-5.3 auto(SG-ws)"] = f5.result()
        results["C6 glm-5.3 强制(BJ-ws)"] = f6.result()
        results["C7 glm-5.3 required(SG-ws)"] = f7.result()

    print("\n" + "=" * 20 + "结论汇总" + "=" * 20)
    for k, (finish, tcs) in results.items():
        flag = "✅ 标准(tool_calls)" if finish == "tool_calls" else f"❌ 异常({finish!r})"
        print(f"  {k}: finish_reason={finish!r}, tool_calls={tcs} → {flag}")
