"""端到端 参数量后缀型号（开源线）目录优先裁决验证（需服务已启动：run.py --port 8000）
事故回归（2026-11-17）：qwen3.8-27b / qwen3.8-2.4t-a95b 的 -27b / -2.4t-a95b
后缀不在 MODEL_NAME_RE 档位白名单里，被削成 qwen3.8 → 详情页 slug 拼成 qwen3-8
空壳页 → 主表家族前缀"假命中"四行合并表（缓存列全 "—"）→ 按用量拆分计价的
问题只能答"缓存输入单价官方未单列 / 暂未能联网核实"。而两个型号的详情页
（qwen3-8-27b / qwen3-8-2-4t-a95b）实际存在且缓存价齐全。
修复：ID 裁决前移到实时在售行目录（_resolve_official_ids），正则降级为口语
归一兜底；详情页补 Explicit Cache Hit → explicit cache read 别名。
覆盖：全串/口语写法裁决 / 详情页双节点缓存价 / 用量拆分计价不再拒答。
运行: .venv/bin/python tests/e2e/test_param_suffix_models.py
"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
session = "e2e-param-suffix-test"
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
print("参数量后缀型号目录优先裁决端到端（27b / a95b 事故复现）")
print("=" * 60)

# [1] 事故型号一：qwen3.8-27b（详情页 SG $0.5/$3，隐式命中 $0.1）
a1, d1, s1 = ask("qwen3.8-27b 价格")
print(f"\n[1] 'qwen3.8-27b 价格' price_status={d1.get('price_status')}")
check("[1] official（目录裁决后详情页命中）", d1.get("price_status") == "official", str(d1))
check("[1] 输入/输出价正确（$0.5 / $3）", "$0.5" in a1 and "$3" in a1, a1[:300])
check("[1] 缓存命中价不再缺失（$0.1）", "$0.1" in a1, a1[:300])
check("[1] 官方 ID 全串（不被削成 qwen3.8）", "qwen3.8-27b" in a1, a1[:300])
check("[1] 不再说未能核实", "未能核实" not in a1, a1[:300])

# [2] 事故型号二：qwen3.8-2.4t-a95b（详情页 SG $2/$6，命中 $0.25，读取 $0.17）
a2, d2, s2 = ask("qwen3.8-2.4t-a95b 价格")
print(f"\n[2] 'qwen3.8-2.4t-a95b 价格' price_status={d2.get('price_status')}")
check("[2] official", d2.get("price_status") == "official", str(d2))
check("[2] 输入/输出价正确（$2 / $6）", "$2" in a2 and "$6" in a2, a2[:300])
check("[2] 缓存命中价 $0.25", "$0.25" in a2, a2[:300])
check("[2] Explicit Cache Hit 别名生效（读取 $0.17）", "$0.17" in a2, a2[:300])
check("[2] 官方 ID 全串", "qwen3.8-2.4t-a95b" in a2, a2[:300])

# [3] 口语空格写法：目录归一 key 去分隔符后仍应精确裁决
a3, d3, s3 = ask("qwen3.8 27b 多少钱")
print(f"\n[3] 'qwen3.8 27b 多少钱' price_status={d3.get('price_status')}")
check("[3] official", d3.get("price_status") == "official", str(d3))
check("[3] 口语写法裁决到 qwen3.8-27b", "qwen3.8-27b" in a3 and "$0.5" in a3, a3[:300])

# [4] 事故原场景：按用量拆分计价（缓存部分此前因单价缺失被拒答）
a4, d4, s4 = ask(
    "qwen3.8-27b 按新加坡节点算：输入 1 亿 tokens，其中 5000 万命中隐式缓存，"
    "输出 1000 万 tokens，总成本多少美元？"
)
print(f"\n[4] 用量拆分计价 price_status={d4.get('price_status')}")
check("[4] official", d4.get("price_status") == "official", str(d4))
check("[4] 不再以缓存单价缺失拒答", "未能核实" not in a4 and "未单列" not in a4, a4[:400])
# SG 口径：0.5 亿×$0.5 + 0.5 亿×$0.1 + 0.1 亿×$3 = $25+$5+$30 = $60
check("[4] 拆分计价结果正确（$60）", "$60" in a4, a4[:600])

print("\n" + "-" * 60)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)