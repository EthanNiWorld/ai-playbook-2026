"""端到端：工具循环下的汇率换算与确定性快路径（需服务已启动：run.py --port 8000）

v3 工具循环验收（2026-11-09）：
  1. 换算类问题（含"美元"字样）不得被缺型号反问快路径劫持——必须进工具循环
     由模型自主调 get_fx_rate 给算式（实测踩坑："1.65 美元是多少人民币"因
     PRICE_KEYWORDS_RE 含"美元"被误判价格题，反问型号答非所问）；
  2. 缺型号反问与纯汇率查询两条确定性快路径保持秒回。
运行: .venv/bin/python tests/e2e/test_toolloop_fx_clarify.py
"""
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail[:300]}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


def ask(q, session):
    t0 = time.time()
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"question": q, "history": [], "session_id": session},
        timeout=300,
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
    return "".join(parts), done, sources, stages, int((time.time() - t0) * 1000)


print("=" * 60)
print("工具循环：汇率换算 / 缺型号反问 / 纯汇率秒回")
print("=" * 60)

# [1] 换算题（曾踩坑：被缺型号反问劫持）
a, d, s, st, ms = ask("1.65 美元是多少人民币？", "e2e-v3-fx")
check("[1] 调用了 get_fx_rate（stage=tool）", "tool" in st, str(st))
check("[1] 未被缺型号反问劫持", d.get("price_status") != "clarify", str(d))
check("[1] 回答含算式", ("×" in a) or ("乘" in a) or ("*" in a), a[:300])
check("[1] 回答含人民币结果", ("¥" in a) or ("元" in a), a[:300])
print(f"    换算耗时 {ms}ms")

# [2] 缺型号反问（确定性快路径，秒回）
a, d, s, st, ms = ask("新加坡节点模型价格是多少", "e2e-v3-clarify")
check("[2] price_status=clarify", d.get("price_status") == "clarify", str(d))
check("[2] 回答是反问而非拒答", "哪个模型" in a or "型号" in a, a[:200])
check("[2] 秒回（< 2s，不调 LLM）", ms < 2000, f"{ms}ms")

# [3] 纯汇率查询（确定性快路径，秒回）
a, d, s, st, ms = ask("查询下实时汇率", "e2e-v3-rate")
check("[3] 秒回（< 5s，取数不调 LLM）", ms < 5000, f"{ms}ms")
check("[3] 回答含汇率数字", "USD" in a and "CNY" in a, a[:200])
check("[3] 来源含汇率源", any("汇率" in (x.get("title") or "") for x in s), str(s)[:200])

print("-" * 60)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)
