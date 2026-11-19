"""端到端 qwen4 .0 别名 + 实时在售目录候选验证（需服务已启动：run.py --port 8000）
事故回归（2026-11-16）：qwen4-max 已上架（SG $1.5/$4.5），用户口语问「qwen4.0-max价格」，
旧逻辑 slug 拼出 qwen4-0-max 空壳页、主表也失配 → LLM 凭旧 Prompt 清单断言"尚未上架"
并改报 qwen3.8-max，徽章还显示"已联网核实"。
覆盖：.0 别名归一 / 官方 ID 剥 Cache price 尾注 / 目录候选→LLM 重核闭环 / 不断言尚未上架。
运行: .venv/bin/python tests/e2e/test_qwen4_alias.py
"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
session = "e2e-qwen4-alias-test"
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
    parts, done, sources = [], {}, []
    for line in r.text.splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "delta":
                parts.append(ev["text"])
            elif ev["type"] == "done":
                done = ev
            elif ev["type"] == "sources":
                sources = ev["sources"]
            elif ev["type"] == "error":
                done["error"] = ev["message"]
    answer = "".join(parts)
    history = history + [
        {"role": "user", "content": q},
        {"role": "assistant", "content": answer[:2000]},
    ]
    return answer, done, sources


print("=" * 60)
print("qwen4 .0 别名 + 在售目录候选端到端（事故句复现 → 候选重核闭环）")
print("=" * 60)

# [1] 事故复现句：口语 .0 写法（归一化后应直接命中 qwen4-max）
a1, d1, s1 = ask("qwen4.0-max价格")
print(f"\n[1] 'qwen4.0-max价格' price_status={d1.get('price_status')}")
check("[1] official（.0 别名归一后联网核实）", d1.get("price_status") == "official", str(d1))
check("[1] 回答报 qwen4-max 而非改报旧旗舰", "qwen4-max" in a1, a1[:300])
check("[1] Singapore 价 $1.5/$4.5", "$1.5" in a1 and "$4.5" in a1, a1[:300])
check("[1] 默认仅 Singapore 表", "Singapore" in a1 and "China (Beijing)" not in a1, a1[:300])
check("[1] 不断言尚未上架（事故表象）", "尚未上架" not in a1 and "未上架" not in a1, a1[:300])
check("[1] 官方 ID 不带 Cache price 尾注", "Cache price" not in a1, a1[:300])
check("[1] Cache Input 列取到 $0.075（不得为 —）",
      "| Singapore · International | $1.5 | $0.075 | $4.5 |" in a1, a1[:500])
check("[1] 缓存写价 5m 档入表（$1.875）", "$1.875" in a1, a1[:400])

# [2] 官方 ID 直问（回归：正常路径不受影响）
a2, d2, s2 = ask("qwen4-max 新加坡 多少钱")
print(f"\n[2] 'qwen4-max 新加坡 多少钱' price_status={d2.get('price_status')}")
check("[2] official", d2.get("price_status") == "official", str(d2))
check("[2] $1.5/$4.5", "$1.5" in a2 and "$4.5" in a2, a2[:300])

# [3] 目录候选→LLM 重核闭环：裸版本号 qwen4.0 归一化覆盖不到，
#     应由在售目录候选召回 qwen4-max，LLM 用官方 ID 重核后报价
a3, d3, s3 = ask("qwen4.0 价格")
print(f"\n[3] 'qwen4.0 价格' price_status={d3.get('price_status')}")
check("[3] official（候选重核闭环）", d3.get("price_status") == "official", str(d3))
check("[3] 回答落到 qwen4-max", "qwen4-max" in a3, a3[:300])
check("[3] 不输出拒答话术", "暂未能联网核实" not in a3, a3[:200])

# [4] 追问事故复现：「怎么没拿到缓存输入价格」——修复后应重核并给出读价，
#     不得断言"该模型无缓存计费项"
a4, d4, s4 = ask("怎么没拿到缓存输入价格 (Cache Input)")
print(f"\n[4] 缓存追问 price_status={d4.get('price_status')}")
check("[4] official", d4.get("price_status") == "official", str(d4))
check("[4] 给出缓存读价 $0.075", "$0.075" in a4, a4[:300])
check("[4] 不断言无缓存计费项（事故表象）", "没有单列缓存" not in a4 and "未公布单独的缓存" not in a4, a4[:300])

# [5] 显式北京节点：同一缓存子表按地域挂接，不带 Singapore，不写“—”
a5, d5, s5 = ask("那北京节点呢？缓存读写分别是多少？")
print(f"\n[5] 北京缓存追问 price_status={d5.get('price_status')}")
check("[5] official", d5.get("price_status") == "official", str(d5))
check("[5] 仅输出 Beijing", "China (Beijing)" in a5 and "Singapore" not in a5, a5[:400])
check("[5] 北京 Cache Input 列取到 $0.071（不得为 —）",
      "| China (Beijing) · Global | $1.413 | $0.071 | $4.24 |" in a5, a5[:500])
check("[5] 北京缓存写价两档 $1.767/$2.827", "$1.767" in a5 and "$2.827" in a5, a5[:400])

print("-" * 60)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)