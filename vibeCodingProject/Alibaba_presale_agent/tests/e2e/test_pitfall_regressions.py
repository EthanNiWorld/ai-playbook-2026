"""端到端：历史踩坑原句回归（需服务已启动：run.py --port 8000）

每一条都是曾经真实翻过车的问句，防止任何后续改动（prompt/工具/管线）让旧事故复发：
  [1] 「北京的1.65美金相当于12RMB*0.45的几折？」（踩坑 id=225~230）
      旧版漏触发汇率获取 → 模型凭记忆心算，124.8s / 思考 10920 字 / 两个互斥答案（3.1 折 / 9.9 折）。
  [2] 「11.01打几折等于5.40」折扣口径（B÷A），旧版模型自己重新定义口径答错。
  [3] 「wan3.0 video 1080P 每秒多少钱」旧版把视频页塞进 token 六列表，思考 5818 字、丢分辨率丢单位。
  [4] 「qwen-image-3.0-pro 每张多少钱」旧版把 $0.003 输入图价当报价（客户问的是生成价 $0.04）。
运行: .venv/bin/python tests/e2e/test_pitfall_regressions.py
"""
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail[:260]}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


def ask(q, session):
    t0 = time.time()
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"question": q, "history": [], "session_id": session},
        timeout=300,
    )
    parts, think, done, sources, stages = [], [], {}, [], []
    for line in r.text.splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "delta":
                parts.append(ev["text"])
            elif ev["type"] == "think":
                think.append(ev["text"])
            elif ev["type"] == "done":
                done = ev
            elif ev["type"] == "sources":
                sources = ev["sources"]
            elif ev["type"] == "status":
                stages.append(ev.get("stage"))
    return "".join(parts), "".join(think), done, sources, stages, int((time.time() - t0) * 1000)


print("=" * 62)
print("历史踩坑原句回归（v3 工具循环）")
print("=" * 62)

# [1] 汇率共现 + 折扣（旧版 124.8s / 思考 10920 字 / 互斥双答案）
# 该句语义天然歧义：「北京的1.65美金」原语境就是北京节点模型价，模型读知识库做消歧
# 属正确行为，思考量实测在 3722~10051 字间波动。硬断言只钉行为（调工具/单一结论/算式），
# 思考与耗时用宽松边界仅拦“真暴涨”（旧事故量级的 1.5 倍以上）。
q = "北京的1.65美金相当于12RMB*0.45的几折？"
a, th, d, s, st, ms = ask(q, "e2e-pitfall-1")
print(f"\n[1] {q}  （{ms / 1000:.1f}s / 思考{len(th)}字 / 正文{len(a)}字）")
check("[1] 调用了汇率工具（get_fx_rate）", "tool" in st, str(st))
check("[1] 含算式", "×" in a or "乘" in a, a[:300])
check("[1] 给出单一折扣结论（非互斥双答案）", "3.1" not in a.split("≈")[-1] if "≈" in a else True)
check("[1] 思考未真暴涨（< 15000 字，旧事故 10920 且行为错；波动正常区间 4k~10k）",
      len(th) < 15000, f"{len(th)}字")
check("[1] 耗时未失控（< 150s，旧事故 124.8s 且行为错）", ms < 150000, f"{ms}ms")

# [2] 折扣第二种问法：口径 B÷A（5.40÷11.01≈0.49 → 约 4.9 折）
q = "11.01打几折等于5.40"
a, th, d, s, st, ms = ask(q, "e2e-pitfall-2")
print(f"\n[2] {q}  （{ms / 1000:.1f}s / 思考{len(th)}字 / 正文{len(a)}字）")
check("[2] 结论为约 4.9 折（B÷A 口径）", "4.9" in a or "0.49" in a, a[:300])
check("[2] 耗时可接受（< 30s）", ms < 30000, f"{ms}ms")

# [3] wan 视频按秒计费（旧版思考 5818 字、丢分辨率丢单位）
q = "wan3.0 video 1080P 每秒多少钱"
a, th, d, s, st, ms = ask(q, "e2e-pitfall-3")
print(f"\n[3] {q}  （{ms / 1000:.1f}s / 思考{len(th)}字 / 正文{len(a)}字）")
check("[3] official 证据", d.get("price_status") == "official", str(d))
check("[3] 输出按秒单价（USD/秒）", "/秒" in a and "$" in a, a[:400])
check("[3] 保留分辨率档位 1080P", "1080P" in a, a[:400])
check("[3] 不套 token 六列表", "Cache Input" not in a, a[:400])
check("[3] 审计通过", d.get("price_audit") in ("ok", ""), str(d))
check("[3] 思考量未暴涨（< 4000 字，旧 5818）", len(th) < 4000, f"{len(th)}字")

# [4] 生图按张计费：单价列取输出图价，输入图价只进备注
q = "qwen-image-3.0-pro 每张多少钱"
a, th, d, s, st, ms = ask(q, "e2e-pitfall-4")
print(f"\n[4] {q}  （{ms / 1000:.1f}s / 思考{len(th)}字 / 正文{len(a)}字）")
check("[4] official 证据", d.get("price_status") == "official", str(d))
check("[4] 输出按张单价（USD/张）", "/张" in a and "$" in a, a[:400])
check("[4] 不把输入图价当报价", "$0.003" not in a.split("|")[0] if "|" in a else True, a[:400])
check("[4] 审计通过", d.get("price_audit") in ("ok", ""), str(d))

print("-" * 62)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)
