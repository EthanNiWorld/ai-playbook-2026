"""端到端产品定价验证（需服务已启动：run.py --port 8000）
事故回归：问 "Qoder 怎么计费" 时，价格校验链把 Qoder 当成"没识别出模型的价格题"，
注入百炼"未能核实，请引导 model-pricing"回落证据 → LLM 把百炼模型定价页链接
安到了 Qoder（席位/Credits 订阅制产品）头上。
覆盖：产品定价不触发百炼校验 / 产品+模型混问不串线 / 纯模型价格题回归。
运行: .venv/bin/python tests/e2e/test_product_pricing.py
"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


def ask(q, session):
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"question": q, "history": [], "session_id": session},
        timeout=180,
    )
    parts, done, sources, stages = [], {}, [], []
    for line in r.text.splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "delta":
                parts.append(ev["text"])
            elif ev["type"] == "done":
                done = ev
            elif ev["type"] == "sources":
                sources = ev["sources"]
            elif ev["type"] == "status":
                stages.append(ev.get("stage"))
    return "".join(parts), done, sources, stages


print("=" * 60)
print("产品定价端到端（Qoder 计费 / 混问 / 纯模型回归）")
print("=" * 60)

# [1] 事故复现句：Qoder 计费/定价（订阅制产品，非百炼模型）
# v3 工具循环：价格校验阶段由 status.stage=tool 标识（旧版为 verifying_price）
a1, d1, s1, st1 = ask("Qoder 是怎么计费的？", "e2e-qoder-1")
print(f"\n[1] 'Qoder 是怎么计费的？'")
check("[1] 不触发百炼价格校验（无 tool 阶段）", "tool" not in st1, str(st1))
check("[1] price_status 为空（非模型价格题）", d1.get("price_status") == "", str(d1))
check("[1] 回答不含百炼定价页链接（事故表象）", "model-studio/model-pricing" not in a1, a1[:300])
check("[1] 回答不含拒答话术", "暂未能联网核实" not in a1, a1[:200])
check("[1] 回答含席位/Credits 计费信息", ("席位" in a1 and "Credits" in a1) or "$40" in a1, a1[:400])

# [2] 口语变体：qoder 多少钱（v3：是否调工具是模型决策，验收只看回答正确）
a2, d2, s2, st2 = ask("qoder多少钱", "e2e-qoder-2")
print(f"\n[2] 'qoder多少钱'")
check("[2] 不含百炼定价页链接", "model-studio/model-pricing" not in a2, a2[:300])
check("[2] 不把 qoder 当百炼模型拒答", "暂未能联网核实" not in a2, a2[:200])
check("[2] 回答含订阅/席位计费信息", "席位" in a2 or "Credits" in a2 or "订阅" in a2, a2[:400])

# [3] 混问场景（产品+模型）：模型校验仍触发且证据不串线
a3, d3, s3, st3 = ask("qoder 和 kimi k3.1 pro 多少钱", "e2e-qoder-3")
print(f"\n[3] 'qoder 和 kimi k3.1 pro 多少钱'")
check("[3] 模型价格校验触发（工具循环）", "tool" in st3, str(st3))
check("[3] kimi 详情页来源就位", "kimi-k3.1-pro" in json.dumps(s3, ensure_ascii=False))
check("[3] kimi 价格表在回答中", "Singapore" in a3 and "$2" in a3, a3[:400])

# [4] 回归：纯模型价格题不受产品守卫影响
a4, d4, s4, st4 = ask("qwen3.8-max 的价格是多少", "e2e-qoder-4")
print(f"\n[4] 'qwen3.8-max 的价格是多少'（回归）")
check("[4] 校验触发且 official", d4.get("price_status") == "official", str(d4))
check("[4] 回答含 Singapore 价格表", "Singapore" in a4, a4[:300])

print("-" * 60)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)
