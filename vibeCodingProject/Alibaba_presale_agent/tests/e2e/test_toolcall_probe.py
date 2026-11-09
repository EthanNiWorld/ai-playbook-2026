"""探针：验证 DashScope 兼容层流式 function calling 行为（改造管线前的先决验证）

背景：app/pipeline.py 要从「正则路由」改为「模型自主调工具」的工具循环，
必须先实测 qwen3.8-max + enable_thinking + tools 三者共存的流式行为：
  1) 流式 delta.tool_calls 按 index 增量到达（id/name/arguments 分片拼装）
  2) 思考(reasoning_content)与 tool_calls 是否同流共存
  3) 第二轮回填 assistant(tool_calls) + role:tool 消息是否被接受并产出正文
     （kimi-k3 在百炼端点对消息结构有严格校验，qwen3.8-max 需单独验证）
  4) 循环必须由 message.tool_calls 非空驱动，不信任 finish_reason
     （GLM 系列强制 tool_choice 下 finish_reason 返回 stop 的既有教训）

运行: .venv/bin/python tests/e2e/test_toolcall_probe.py
（无需服务在跑；直接调 DashScope，需 DASHSCOPE_API_KEY）
"""
import asyncio
import json
import sys

from openai import AsyncOpenAI

from app.config import get_llm_config

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verify_price",
            "description": "联网核实阿里云百炼模型的官方定价（新加坡/北京双节点 USD）。涉及任何具体模型的价格/计费/多少钱问题时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "模型名或口语写法，如 qwen3.8-max、kimi k3.1 pro、wan3.0 video",
                    },
                },
                "required": ["model"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fx_rate",
            "description": "获取 USD/CNY 实时汇率。仅当用户要求美元人民币换算/折算/比价金额时调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

VERIFY_PRICE_RESULT = (
    "### 官方定价页证据（权威 — 具体价格数字仅可引用此处）\n"
    "**qwen3.8-max · 官方定价页（每 1M tokens USD）**\n\n"
    "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) |"
    " 显式缓存创建 (Cache Write) | 备注 |\n"
    "|---|---|---|---|---|---|\n"
    "| Singapore | $2 | $0.2 | $10 | $2.5 | — |\n"
    "| China (Beijing) | $1.65 | $0.165 | $8 | $2 | — |\n\n"
    "来源：https://www.alibabacloud.com/help/en/model-studio/model-pricing\n"
)


async def main() -> int:
    cfg = get_llm_config()
    if not cfg["api_key"]:
        print("未配置 DASHSCOPE_API_KEY，跳过探针")
        return 2
    client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

    print("=" * 60)
    print(f"探针：{cfg['model']} 流式 tool_calls（enable_thinking=True）")
    print("=" * 60)

    messages = [
        {
            "role": "system",
            "content": "你是测试助手。用户问模型价格时必须调用 verify_price 工具核实，不得凭记忆报价。",
        },
        {"role": "user", "content": "qwen3.8-max 新加坡多少钱？"},
    ]

    # ── 第一轮：期望模型发起 tool call ──
    stream = await client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        tools=TOOLS,
        stream=True,
        temperature=0.3,
        max_tokens=2048,
        extra_body={"enable_thinking": True},
    )

    tool_acc: dict[int, dict] = {}  # index → {id, name, arguments}
    saw_think = False
    saw_text_before_tools = False
    finish_reason = None
    chunk_count = 0
    async for chunk in stream:
        chunk_count += 1
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        finish_reason = finish_reason or choice.finish_reason
        delta = choice.delta
        if delta is None:
            continue
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            saw_think = True
        if delta.content:
            # 工具轮出现正文是异常信号（DashScope 部分模型会先吐一句再调工具，记录之）
            if not tool_acc:
                saw_text_before_tools = True
        tcs = getattr(delta, "tool_calls", None)
        if tcs:
            for tc in tcs:
                acc = tool_acc.setdefault(tc.index or 0, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    acc["id"] += tc.id
                if tc.function and tc.function.name:
                    acc["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    acc["arguments"] += tc.function.arguments

    print(f"\nfinish_reason={finish_reason}（不作为循环依据，仅记录）")
    check("[1] 流式 tool_calls 增量到达并按 index 拼装", bool(tool_acc), f"chunks={chunk_count}")
    calls = list(tool_acc.values())
    check("[2] tool call 名称合法", any(c["name"] == "verify_price" for c in calls),
          json.dumps(calls, ensure_ascii=False))
    args_ok = False
    for c in calls:
        if c["name"] == "verify_price":
            try:
                args = json.loads(c["arguments"] or "{}")
                args_ok = "model" in args and "qwen" in str(args.get("model", "")).lower()
                print(f"    verify_price args: {args}")
            except json.JSONDecodeError as e:
                args_ok = False
                print(f"    arguments 解析失败: {e}: {c['arguments']!r}")
    check("[3] verify_price 参数含 model 且指向所问型号", args_ok)
    check("[4] 思考流与 tool_calls 共存", saw_think, "未见 reasoning_content")
    print(f"    工具轮前出现正文: {saw_text_before_tools}（True 则管线需丢弃该段正文）")

    if not calls:
        print("未收到 tool_calls，后续轮次跳过")
        print("-" * 60)
        print(f"结果: {PASS} 通过 / {FAIL} 失败")
        return 1 if FAIL else 0

    # ── 第二轮：回填工具结果，期望产出正文 ──
    messages.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": c["id"] or f"call_{i}",
                    "type": "function",
                    "function": {"name": c["name"], "arguments": c["arguments"] or "{}"},
                }
                for i, c in enumerate(calls)
            ],
        }
    )
    for i, c in enumerate(calls):
        content = (
            VERIFY_PRICE_RESULT if c["name"] == "verify_price"
            else "1 USD = 6.6700 CNY（探针假数据）"
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": c["id"] or f"call_{i}",
                "content": content,
            }
        )

    stream2 = await client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        tools=TOOLS,  # 仍带工具：观察模型是否会再发起调用（正常应收尾作答）
        stream=True,
        temperature=0.3,
        max_tokens=2048,
        extra_body={"enable_thinking": True},
    )
    parts: list[str] = []
    think_parts: list[str] = []
    second_round_calls: dict[int, dict] = {}
    async for chunk in stream2:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            think_parts.append(reasoning)
        if delta.content:
            parts.append(delta.content)
        tcs = getattr(delta, "tool_calls", None)
        if tcs:
            for tc in tcs:
                acc = second_round_calls.setdefault(tc.index or 0, {"id": "", "name": "", "arguments": ""})
                if tc.function and tc.function.name:
                    acc["name"] += tc.function.name

    answer = "".join(parts)
    print(f"\n[第二轮] 正文 {len(answer)} 字 / 思考 {len(''.join(think_parts))} 字")
    check("[5] 回填 tool 消息被接受（无 400）", True if answer or think_parts else False,
          f"answer[:200]={answer[:200]}")
    check("[6] 第二轮产出正文而非再次调工具", bool(answer.strip()) and not second_round_calls,
          f"again_calls={list(second_round_calls.values())}")
    has_price = "$2" in answer and "$10" in answer
    check("[7] 正文引用了工具证据里的价格", has_price, answer[:300])

    print("-" * 60)
    print(f"结果: {PASS} 通过 / {FAIL} 失败")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
