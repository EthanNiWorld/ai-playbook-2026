"""glm-5.3 tool_calls finish_reason 兼容性验证 — 阿里云国际站

背景（2026-09-24）：
  客户反馈：tool_choice 强制指定函数时，glm-5.3 响应中输出了 tool_calls
  信息，但 finish_reason 为 "stop"（OpenAI 标准应为 "tool_calls"）。
  影响：依赖 finish_reason 驱动的 Agent 工具循环会误判"模型已给出最终
  回答"而提前终止，工具不执行。

用例矩阵（判定问题归属）：
  C1: glm-5.3        非流式 + 强制 tool_choice → 完整 message + finish_reason
  C2: glm-5.3        流式   + 强制 tool_choice → 流末 chunk 的 finish_reason
  C3: 对照 glm-5.2   非流式 + 强制 tool_choice → 判断是否 glm-5.3 专属
  C4: 对照 qwen3.8-max(enable_thinking=false) 非流式 + 强制 tool_choice
      → 判断是否百炼部署通病

端点与凭证：新加坡 workspace（DASHSCOPE_API_KEY_INTL_SG_TEST + _URL）
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

API_KEY = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", "").strip()
BASE_URL = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "").strip()

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
MESSAGES = [{"role": "user", "content": "请处理上海相关的信息。"}]
FORCED = {"type": "function", "function": {"name": "get_weather"}}


def fmt_tool_calls(msg):
    tcs = getattr(msg, "tool_calls", None)
    if not tcs:
        return "（无 tool_calls 字段）"
    out = []
    for tc in tcs:
        out.append(f"{tc.function.name}({tc.function.arguments})")
    return ", ".join(out)


def case_nonstream(name, model, extra_body=None):
    """非流式：打印 finish_reason / tool_calls / content 概要"""
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=420)
    kwargs = dict(model=model, messages=MESSAGES, tools=TOOLS, tool_choice=FORCED)
    if extra_body:
        kwargs["extra_body"] = extra_body
    try:
        resp = client.chat.completions.create(**kwargs)
        ch = resp.choices[0]
        msg = ch.message
        content = (msg.content or "")[:80]
        reasoning_len = len(getattr(msg, "reasoning_content", "") or "")
        print(f"  finish_reason : {ch.finish_reason!r}")
        print(f"  tool_calls    : {fmt_tool_calls(msg)}")
        print(f"  content       : {content!r}")
        print(f"  reasoning 长度: {reasoning_len} 字")
        return ch.finish_reason, fmt_tool_calls(msg)
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:200]}")
        return None, None


def case_stream(name, model):
    """流式：收集 tool_calls 头与最终 finish_reason"""
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=420)
    try:
        stream = client.chat.completions.create(
            model=model, messages=MESSAGES, tools=TOOLS, tool_choice=FORCED, stream=True,
        )
        finish = None
        tc_names = []
        content_head = []
        for chunk in stream:
            if not chunk.choices:
                continue
            c = chunk.choices[0]
            if c.delta and c.delta.tool_calls:
                for tc in c.delta.tool_calls:
                    if tc.function and tc.function.name:
                        tc_names.append(tc.function.name)
            if c.delta and c.delta.content:
                if len("".join(content_head)) < 80:
                    content_head.append(c.delta.content)
            if c.finish_reason:
                finish = c.finish_reason
        print(f"  流中 tool_calls: {tc_names or '（无）'}")
        print(f"  最终 finish_reason: {finish!r}")
        print(f"  content 头部: {''.join(content_head)[:80]!r}")
        return finish, tc_names
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:200]}")
        return None, None


if __name__ == "__main__":
    if not API_KEY:
        print("❌ 未检测到 DASHSCOPE_API_KEY_INTL_SG_TEST（.env）")
        raise SystemExit(1)
    print(f"Base URL: {BASE_URL}")
    print(f"tool_choice = {FORCED}（强制 get_weather）")
    print("=" * 60)

    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        f1 = pool.submit(case_nonstream, "C1: glm-5.3 非流式", "glm-5.3")
        f2 = pool.submit(case_stream, "C2: glm-5.3 流式", "glm-5.3")
        f3 = pool.submit(case_nonstream, "C3: 对照 glm-5.2 非流式", "glm-5.2")
        f4 = pool.submit(case_nonstream, "C4: 对照 qwen3.8-max(关思考) 非流式",
                         "qwen3.8-max", {"enable_thinking": False})
        results["C1 glm-5.3 非流式"] = f1.result()
        results["C2 glm-5.3 流式"] = f2.result()
        results["C3 glm-5.2 非流式"] = f3.result()
        results["C4 qwen3.8-max 非流式"] = f4.result()

    print("\n" + "=" * 20 + "结论汇总" + "=" * 20)
    for k, (finish, tcs) in results.items():
        flag = "✅ 标准(tool_calls)" if finish == "tool_calls" else f"❌ 异常({finish!r})"
        print(f"  {k}: finish_reason={finish!r} → {flag}")
    print("\n判定：若仅 glm-5.3 异常而 glm-5.2/qwen 正常 → glm-5.3 百炼部署专属缺陷；")
    print("      若 glm 系列均异常 → 百炼 GLM 部署通病；若 qwen 也异常 → 百炼通病。")
