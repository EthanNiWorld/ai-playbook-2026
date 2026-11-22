"""端到端：带用量截图问单价 + 省略后缀型号裁决（需服务已启动：run.py --port 8000）

2026-11-22 事故回归（用户真实会话「kimi-k3.1，多少钱」+ 用量截图）：
  [1] 事故复现：带用量截图只问单价 —— 修复前 is_usage_cost_question 被
      「多少钱」歧义词误判成成本题，硬闸门把模型已写好的单价表替换成
      USAGE_COST_CLARIFY_TEXT（答非所问）；且 _resolve_official_ids 正向
      包含把 kimi-k3.1 截断裁决成 kimi-k3（目录只有 kimi-k3 / kimi-k3.1-pro）。
      修复后应走正常报价路径，报 kimi-k3.1-pro 官方单价。
  [2] 成本闸门回归保护：同一张用量截图问「看看多少钱」（型号名只在图里）
      仍须命中成本题，由 calculate_token_cost 代码渲染成品表，
      不允许自由文本成本（#198 手算放大 10 倍事故的闸门不能被本次修复关掉）。
  [3] 纯文本省略后缀：「kimi-k3.1 价格」无图也应裁决到 kimi-k3.1-pro。

素材：tests/e2e/assets/apa_usage_sample.png（Chrome headless 渲染的合成
用量表，自造数字，无隐私内容；源 HTML 同目录，重生成命令见其头部注释）。
运行: .venv/bin/python tests/e2e/test_screenshot_unit_price.py
"""
import base64
import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
IMG = Path(__file__).parent / "assets" / "apa_usage_sample.png"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail[:300]}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


def ask(question, session, history=None, images=None):
    t0 = time.time()
    r = httpx.post(
        f"{BASE}/api/chat",
        json={
            "question": question,
            "session_id": session,
            "history": history or [],
            "images": images or [],
        },
        timeout=300,
    )
    parts, done, stages = [], {}, []
    for line in r.text.splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "delta":
                parts.append(ev["text"])
            elif ev["type"] == "done":
                done = ev
            elif ev["type"] == "status":
                stages.append(ev.get("stage"))
    return "".join(parts), done, stages, int((time.time() - t0) * 1000)


def data_url():
    return "data:image/png;base64," + base64.b64encode(IMG.read_bytes()).decode()


print("=" * 62)
print("带用量截图问单价 + 省略后缀裁决 端到端（2026-11-22 事故回归）")
print("=" * 62)

if not IMG.exists():
    print(f"素材缺失: {IMG}")
    sys.exit(2)

img = data_url()

# [1] 事故复现：用量截图 + 「kimi-k3.1，多少钱」→ 应报 pro 单价，不落澄清话术
q = "kimi-k3.1，多少钱"
a, d, st, ms = ask(q, "e2e-usage-unitprice-1", images=[img])
print(f"\n[1] {q}（附用量截图）  （{ms / 1000:.1f}s）")
check("[1] official 证据", d.get("price_status") == "official", str(d))
check("[1] 不再落成本澄清话术", "我需要原始整数 token 用量" not in a, a[:300])
check("[1] 裁决到 kimi-k3.1-pro（不被截断成 kimi-k3）", "kimi-k3.1-pro" in a.lower(), a[:300])
check("[1] 回答含官方单价表", "Singapore" in a and "$" in a, a[:300])
check("[1] 审计通过", d.get("price_audit") in ("ok", ""), str(d))

# [2] 成本闸门回归保护：同图问「看看多少钱」（型号名只在图里）仍走确定性计算
q2 = "看看多少钱"
a2, d2, st2, ms2 = ask(q2, "e2e-usage-unitprice-2", images=[img])
print(f"\n[2] {q2}（附用量截图）  （{ms2 / 1000:.1f}s）")
check("[2] 仍命中成本题（代码渲染成品表前缀）",
      "按官方单价与原始整数 tokens 计算" in a2, a2[:300])
check("[2] official 证据", d2.get("price_status") == "official", str(d2))
check("[2] 审计通过", d2.get("price_audit") in ("ok", ""), str(d2))

# [3] 纯文本省略后缀：无图也应裁决到 pro
q3 = "kimi-k3.1 价格"
a3, d3, st3, ms3 = ask(q3, "e2e-usage-unitprice-3")
print(f"\n[3] {q3}  （{ms3 / 1000:.1f}s）")
check("[3] official 证据", d3.get("price_status") == "official", str(d3))
check("[3] 裁决到 kimi-k3.1-pro", "kimi-k3.1-pro" in a3.lower(), a3[:300])
check("[3] 审计通过", d3.get("price_audit") in ("ok", ""), str(d3))

print("-" * 62)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)