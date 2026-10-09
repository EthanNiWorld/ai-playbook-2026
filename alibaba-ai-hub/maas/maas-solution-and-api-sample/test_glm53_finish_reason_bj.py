"""glm-5.3 finish_reason 客户原始 payload 复现 — 国际站北京 workspace

背景（2026-09-24）：
  客户用如下 payload 调北京站点 glm-5.3，响应 message 中含两个 tool_calls，
  但 finish_reason="stop"（OpenAI 标准应为 "tool_calls"）。客户反馈应修复。

本脚本 1:1 复刻客户 payload（非流式），在北京 workspace 连跑 3 次确认是否
稳定复现，并附 auto 模式对照（用于定位：仅强制模式异常还是通病）。

端点与凭证：DASHSCOPE_API_KEY_INTL_BJ_TEST / _URL（.env）
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST", "").strip()
BASE_URL = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST_URL", "").strip()

# ---- 客户原始 payload（1:1 复刻） ----
CUSTOMER_PAYLOAD = {
    "model": "glm-5.3",
    "messages": [{"role": "user", "content": "请处理上海相关的信息。"}],
    "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询指定城市的当前天气",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                    "additionalProperties": False,
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
                    "additionalProperties": False,
                },
            },
        },
    ],
}


def run_once(tag, payload):
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=420)
    try:
        resp = client.chat.completions.create(**payload)
        ch = resp.choices[0]
        msg = ch.message
        tcs = [f"{tc.function.name}({tc.function.arguments})" for tc in (msg.tool_calls or [])]
        print(f"\n----- {tag} -----")
        print(f"  finish_reason : {ch.finish_reason!r}")
        print(f"  tool_calls    : {', '.join(tcs) if tcs else '（无）'}")
        print(f"  content       : {(msg.content or '')[:60]!r}")
        return ch.finish_reason, tcs
    except Exception as e:
        print(f"\n----- {tag} -----\n  ❌ {type(e).__name__}: {str(e)[:200]}")
        return None, None


if __name__ == "__main__":
    if not API_KEY or not BASE_URL:
        print("❌ 未检测到 DASHSCOPE_API_KEY_INTL_BJ_TEST / _URL（.env）")
        raise SystemExit(1)
    print(f"Base URL: {BASE_URL}")
    print(f"Payload : {json.dumps(CUSTOMER_PAYLOAD, ensure_ascii=False)[:120]}...")

    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        # 客户 payload 连跑 3 次，确认是否稳定复现
        futs = {
            pool.submit(run_once, f"复现 #{i}（客户原 payload，强制 get_weather）", CUSTOMER_PAYLOAD):
                f"复现#{i}" for i in (1, 2, 3)
        }
        # 对照：auto / required 模式同工具同提问
        auto_payload = dict(CUSTOMER_PAYLOAD, tool_choice="auto")
        futs[pool.submit(run_once, "对照（tool_choice='auto'）", auto_payload)] = "对照auto"
        req_payload = dict(CUSTOMER_PAYLOAD, tool_choice="required")
        futs[pool.submit(run_once, "对照（tool_choice='required'）", req_payload)] = "对照required"
        # glm-5.2 对照：同 payload 三种 tool_choice（判断是否 GLM 系列通病）
        for tc_name, tc in [("强制", CUSTOMER_PAYLOAD["tool_choice"]), ("auto", "auto"), ("required", "required")]:
            p52 = dict(CUSTOMER_PAYLOAD, model="glm-5.2", tool_choice=tc)
            futs[pool.submit(run_once, f"glm-5.2 对照（tool_choice={tc_name}）", p52)] = f"glm5.2-{tc_name}"
        for f, name in futs.items():
            results[name] = f.result()

    print("\n" + "=" * 20 + "结论汇总" + "=" * 20)
    for k, (finish, tcs) in results.items():
        n = len(tcs or [])
        flag = "✅ 标准(tool_calls)" if finish == "tool_calls" else f"❌ 异常({finish!r})"
        print(f"  {k}: finish_reason={finish!r}, tool_calls 数={n} → {flag}")
    print("\n判定：含 tool_calls 但 finish_reason='stop' → 服务端 finish_reason 映射缺陷；")
    print("      若 auto 模式正常 → 仅强制 tool_choice 路径异常；若 auto 也异常 → 通病。")
