"""端到端口语模型名验证（需服务已启动：run.py --port 8000）
事故回归：'kimi k3.1 pro的价格' 曾因口语写法提取不到模型名，
回退挪用历史里的 deepseek 证据 → 前端显示"deepseek 详情页已核实"却拒答 kimi 价格。
覆盖：口语归一 / 家族词守卫（不挪用历史模型）/ 双节点价格表。
运行: .venv/bin/python tests/e2e/test_colloquial_model.py
"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
session = "e2e-colloquial-model-test"
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
print("口语模型名端到端（deepseek 污染历史 → 'kimi k3.1 pro' → 家族词守卫）")
print("=" * 60)

# [1] 铺垫历史污染：先问 deepseek（事故时历史里最近一次提及的模型）
a1, d1, s1 = ask("deepseek-v4.1-flash的价格是多少")
print(f"\n[1] deepseek price_status={d1.get('price_status')}")
check("[1] official", d1.get("price_status") == "official", str(d1))

# [2] 事故复现句：口语写法 + 历史里有 deepseek
a2, d2, s2 = ask("kimi k3.1 pro的价格呢？")
src_text = json.dumps(s2, ensure_ascii=False)
print(f"\n[2] 'kimi k3.1 pro的价格呢？' price_status={d2.get('price_status')}")
check("[2] official（口语名归一后联网核实）", d2.get("price_status") == "official", str(d2))
check("[2] sources 是 kimi-k3.1-pro 详情页", "kimi-k3.1-pro" in src_text, src_text[:300])
check("[2] sources 不再挪用 deepseek（事故表象）", "deepseek" not in src_text.lower(), src_text[:300])
check("[2] 回答含 Singapore 分表", "Singapore" in a2 and "$" in a2, a2[:300])
check("[2] 回答含 China (Beijing) 分表", "China (Beijing)" in a2, a2[:300])
check("[2] 不再输出拒答话术（事故表象）", "暂未能联网核实" not in a2, a2[:200])

# [3] 家族词守卫：提了 glm 却抽不出型号时，不得挪用历史 kimi 的证据
a3, d3, s3 = ask("glm 最新款多少钱")
src3 = json.dumps(s3, ensure_ascii=False)
print(f"\n[3] 'glm 最新款多少钱' price_status={d3.get('price_status')}")
check("[3] sources 不挪用历史模型（kimi）", "kimi" not in src3.lower(), src3[:300])
check("[3] 回答不报 kimi 价格（引导官方页）", "kimi-k3.1" not in a3, a3[:200])

print("-" * 60)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)
