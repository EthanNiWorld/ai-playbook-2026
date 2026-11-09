"""端到端：价格表格追问锚定 + 跨云竞品比价（需服务已启动）

背景（2026-11-09 线上两条点踩，id=64 / id=66）：
1. 上一轮给了 deepseek-v4.1-flash 价格表，用户追问「China (Beijing) · US是什么意思？」，
   系统把 US 当成术语长篇解释却不给该节点价格 → 答非所问。修复：表格追问也触发
   价格校验，并在 prompt 里注入"先解释字段、再按双节点口径给价格"的锚定。
2. 用户问「缓存 cache input 价格是不是和腾讯云一样了」，旧链路只抓阿里云官方页，
   竞品价格从未进证据池 → 系统绕圈。修复：识别竞品后额外检索第三方报价，作为
   「竞品价格（第三方信源）」证据块，且不参与阿里云报价、不算价格审计 mismatch。

运行: .venv/bin/python tests/e2e/test_price_followup_competitor.py
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


def ask(question, history=None, session="e2e-followup-competitor", timeout=240):
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"question": question, "history": history or [], "session_id": session},
        timeout=timeout,
    )
    parts, done, sources = [], {}, []
    for line in r.text.splitlines():
        if not line.startswith("data: "):
            continue
        try:
            ev = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if ev["type"] == "delta":
            parts.append(ev["text"])
        elif ev["type"] == "done":
            done = ev
        elif ev["type"] == "sources":
            sources = ev.get("sources", [])
    return "".join(parts), done, sources


PRICE_TABLE = (
    "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) |\n"
    "|---|---|---|---|\n"
    "| Singapore · idle hours | $0.15 | $0.015 | $0.6 |\n"
    "| China (Beijing) · idle hours | $0.141 | $0.014 | $0.565 |"
)


def main():
    print("=" * 56)
    print("e2e: 价格表格追问锚定 + 跨云竞品比价")
    print("=" * 56)

    # ── 场景 1：表格追问（踩点 id=64）──
    print("[1] 表格追问：China (Beijing) · US 是什么意思")
    history = [
        {"role": "user", "content": "deepseek-v4.1-flash 新加坡价格"},
        {"role": "assistant", "content": PRICE_TABLE},
    ]
    answer, done, _ = ask("China (Beijing) · US是什么意思？", history)
    low = answer.lower()
    check("先解释币种含义（US/USD = 美元）", "usd" in low or "美元" in answer, answer[:200])
    check("给出该节点价格（北京 $0.141）", "0.141" in answer, answer[:200])
    check("双节点口径（同时含 Singapore）", "singapore" in low, answer[:200])
    check("不是停留在术语解释（含价格表格）", "|" in answer and "$" in answer, answer[:200])
    check("未整体拒答", "暂未能联网核实" not in answer, answer[:200])
    check("price_status=official", done.get("price_status") == "official", str(done))
    check("价格审计通过", done.get("price_audit") in ("ok", ""), str(done))

    # ── 场景 2：跨云竞品比价（踩点 id=66）──
    print("[2] 跨云比价：缓存 cache input 与腾讯云对比")
    answer2, done2, sources2 = ask("看看缓存cache input 价格是不是和腾讯云一样了", history)
    low2 = answer2.lower()
    check("阿里云缓存价给出（$0.015 / $0.014）",
          "0.015" in answer2 or "0.014" in answer2, answer2[:200])
    check("触及竞品（腾讯云）", "腾讯云" in answer2 or "tencent" in low2, answer2[:200])
    check(
        "竞品价采用美金（USD）口径，与阿里云可直接对比",
        "$" in answer2 and ("usd" in low2 or "美元" in answer2),
        answer2[:400],
    )
    check(
        "竞品来源指向国际站官方定价页",
        any("tencentcloud.com" in (s.get("url") or "") for s in sources2)
        or any("tencentcloud.com" in answer2 for _ in [0]),
        str([s.get("url") for s in sources2])[:300],
    )
    check("竞品不作阿里云报价依据（标注第三方/官网为准）",
          "第三方" in answer2 or "官网为准" in answer2 or "未检索到" in answer2, answer2[:300])
    check("未因竞品缺证据而整体拒答", "暂未能联网核实" not in answer2, answer2[:200])
    check("price_status=official", done2.get("price_status") == "official", str(done2))
    check("竞品价不触发审计 mismatch", not str(done2.get("price_audit", "")).startswith("mismatch"),
          str(done2))
    web_sources = [s for s in sources2 if s.get("kind") == "web"]
    print(f"    （本次竞品检索到 {len(web_sources)} 条第三方来源，网络抖动时可能为 0）")

    print("-" * 56)
    print(f"结果: {PASS} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
