"""探针：验证 qwen3.8-max 图像输入 + enable_thinking + tools 三者流式共存
（截图问答能力的前置验证，无需服务在跑，直连 DashScope）

要验证的四点：
  1) 多模态 content（image_url data URL + text blocks）被该端点接受
  2) 流式下 reasoning_content 与图片共存（思考流可推前端）
  3) 模型能从截图中读出模型名并自主发起 verify_price 工具调用
  4) 回填工具结果后正常收尾作答（价格逐字来自证据）

素材：/tmp/apa_probe.png（Chrome headless 渲染的模拟定价页截图，内容
"qwen3.8-max Input $2.00 Output $6.00"）。素材不存在时先运行：
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless --screenshot=/tmp/apa_probe.png --window-size=680,380 \
    file:///tmp/apa_probe.html
运行: PYTHONPATH=. .venv/bin/python tests/e2e/test_vision_probe.py
"""
import asyncio
import base64
import json
import sys
from pathlib import Path

from openai import AsyncOpenAI

from app.config import get_llm_config

PASS, FAIL = 0, 0
IMG = Path("/tmp/apa_probe.png")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verify_price",
            "description": (
                "联网核实阿里云百炼模型的官方定价（双节点 USD）。"
                "凡涉及具体模型价格的问题必须先调用，严禁凭记忆或凭截图报价。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "模型名，用户原话即可"},
                },
                "required": ["model"],
            },
        },
    }
]

VERIFY_RESULT = (
    "### 官方定价页证据（权威 — 具体价格数字仅可引用此处）\n"
    "**qwen3.8-max · 官方定价页（每 1M tokens USD）**\n\n"
    "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |\n"
    "|---|---|---|---|---|---|\n"
    "| Singapore | $1.6 | $0.2 | $8 | $2 | — |\n"
    "| China (Beijing) | $0.8 | $0.1 | $4 | $1 | — |\n\n"
    "来源：https://www.alibabacloud.com/help/en/model-studio/model-pricing\n"
    "注：截图中的价格是示例数据，回答必须以上方官方证据为准。\n"
)


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


async def main() -> int:
    cfg = get_llm_config()
    if not cfg["api_key"]:
        print("未配置 DASHSCOPE_API_KEY，跳过")
        return 2
    if not IMG.exists():
        print(f"素材不存在: {IMG}（先按 docstring 生成）")
        return 2
    data_url = "data:image/png;base64," + base64.b64encode(IMG.read_bytes()).decode()

    client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    print("=" * 60)
    print(f"视觉探针：{cfg['model']} 图像 + enable_thinking + tools 流式共存")
    print("=" * 60)

    user_content = [
        {"type": "image_url", "image_url": {"url": data_url}},
        {"type": "text", "text": "截图里这个模型在阿里云百炼的价格是多少？"},
    ]
    messages = [
        {"role": "system", "content": "你是测试助手。涉及模型价格必须调用 verify_price 工具核实。"},
        {"role": "user", "content": user_content},
    ]

    stream = await client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        tools=TOOLS,
        stream=True,
        temperature=0.3,
        max_tokens=2048,
        extra_body={"enable_thinking": True},
    )
    tool_acc: dict[int, dict] = {}
    saw_think = False
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        if getattr(delta, "reasoning_content", None):
            saw_think = True
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

    check("[1] 多模态 content（data URL 图片 + text）被接受（无 400）", True)
    check("[2] 思考流与图像共存（reasoning_content 到达）", saw_think)
    calls = list(tool_acc.values())
    check("[3] 模型从截图读出型号并发起 verify_price", any(c["name"] == "verify_price" for c in calls),
          json.dumps(calls, ensure_ascii=False))
    args = {}
    for c in calls:
        if c["name"] == "verify_price":
            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"    verify_price args: {args}")
    check("[4] 工具参数 model 指向截图中的型号 qwen3.8-max",
          "qwen" in str(args.get("model", "")).lower(), str(args))

    if not calls:
        print("未收到 tool_calls，后续轮次跳过")
        print("-" * 60)
        print(f"结果: {PASS} 通过 / {FAIL} 失败")
        return 1 if FAIL else 0

    # 第二轮：回填工具结果 → 期望收尾作答且价格逐字来自证据（$8 而非截图的 $6）
    messages.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": calls[0]["id"] or "call_0",
                    "type": "function",
                    "function": {"name": calls[0]["name"], "arguments": calls[0]["arguments"] or "{}"},
                }
            ],
        }
    )
    messages.append(
        {"role": "tool", "tool_call_id": calls[0]["id"] or "call_0", "content": VERIFY_RESULT}
    )
    stream2 = await client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        stream=True,
        temperature=0.3,
        max_tokens=2048,
        extra_body={"enable_thinking": True},
    )
    parts: list[str] = []
    async for chunk in stream2:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        if delta.content:
            parts.append(delta.content)
    answer = "".join(parts)
    print(f"\n[第二轮] 正文 {len(answer)} 字")
    print(answer[:300])
    check("[5] 回填后正常收尾作答", bool(answer.strip()), answer[:200])
    check("[6] 价格逐字来自工具证据（Singapore 输出 $8），未抄截图示例价 $6",
          "$8" in answer and "| $6" not in answer, answer[:400])

    print("-" * 60)
    print(f"结果: {PASS} 通过 / {FAIL} 失败")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
