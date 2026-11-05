"""端到端追问链验证（需服务已启动：run.py --port 8000）
模拟真实测试流：基线价格问 → 追问「呢？」→ 追问「价格。」
运行: .venv/bin/python tests/e2e/test_followup.py
"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
session = "e2e-followup-test"
history: list = []

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


def ask(q):
    global history
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"question": q, "history": history, "session_id": session},
        timeout=180,
    )
    parts, done = [], {}
    for line in r.text.splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "delta":
                parts.append(ev["text"])
            elif ev["type"] == "done":
                done = ev
            elif ev["type"] == "error":
                done["error"] = ev["message"]
    answer = "".join(parts)
    history = history + [
        {"role": "user", "content": q},
        {"role": "assistant", "content": answer[:2000]},
    ]
    return answer, done


def header_of(answer):
    for line in answer.splitlines():
        if line.startswith("| Region"):
            return line
    return ""


print("=" * 60)
print("追问链端到端（deepseek → qwen3.8-flash → kimi → 价格。）")
print("=" * 60)

a1, d1 = ask("deepseek-v4.1-flash 的价格是多少？")
print(f"\n[1] deepseek price_status={d1.get('price_status')}")
check("[1] official", d1.get("price_status") == "official", str(d1))
check("[1] 忙闲分档 + Cache Input 填数", "$0.015" in a1 and "busy hours" in a1, a1[:200])

a2, d2 = ask("qwen3.8 flash呢？")
print(f"\n[2] qwen3.8 flash呢？ price_status={d2.get('price_status')}")
check("[2] 追问触发校验（此前静默跳过）", d2.get("price_status") == "official", str(d2))
check("[2] Cache Input/Write 有官方值（此前全 '—'）", "$0.016" in a2 and "$0.2" in a2, a2[:300])

a3, d3 = ask("kimi-k3.1-pro呢？")
print(f"\n[3] kimi-k3.1-pro呢？ price_status={d3.get('price_status')}")
check("[3] 追问触发校验（此前只给 benchmark）", d3.get("price_status") == "official", str(d3))
check("[3] Cache Input $0.184 拆列", "$0.184" in a3, a3[:300])
check("[3] Cache Input 归列（$2 输入 + $0.2 命中，不挪用）", "| $2 | $0.2 |" in a3, a3[:400])

a4, d4 = ask("价格。")
print(f"\n[4] 价格。 price_status={d4.get('price_status')}")
check("[4] 无模型名回退历史（kimi）", d4.get("price_status") == "official", str(d4))
check("[4] 回答的是 kimi 价格表", "$0.184" in a4, a4[:300])

h1, h3 = header_of(a1), header_of(a3)
print(f"\n排版一致性：\n  [1] {h1}\n  [3] {h3}")
check("两次回答表头逐字一致（含 Cache Input/Write 列）", h1 != "" and h1 == h3)

print("-" * 60)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)
