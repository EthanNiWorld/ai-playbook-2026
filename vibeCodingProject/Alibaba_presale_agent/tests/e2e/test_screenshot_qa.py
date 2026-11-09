"""端到端：截图问答（需服务已启动：run.py --port 8000）

验证 v3 多模态链路（qwen3.8-max 视觉输入 + 工具循环）：
  [1] 截图问价：模型从截图中读出模型名 → 自主调 verify_price → 报官方价格
      （素材是伪造的"定价页截图"，写 $2/$6 示例价，官方实际输出价是 $6 但输入
      官方价是 $2……素材价与官方价部分重叠，断言只钉 official 证据与审计，
      不钉具体数字）；更关键的是回答必须来自官方证据而非照抄截图。
  [2] 历史重发截图：第二轮当前句无型号、靠历史图片 blocks（前端构造的
      多模态 content）推断型号并重调 verify_price —— 验证 _mm_history_content
      保留 image_url 块透传给模型。
  [3] 纯文本回归：无图时请求/回答与旧链路一致（images 空数组不影响）。

素材：tests/e2e/assets/apa_screenshot_sample.png（Chrome headless 渲染的
自造模拟定价页，无隐私内容）。
运行: .venv/bin/python tests/e2e/test_screenshot_qa.py
"""
import base64
import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
IMG = Path(__file__).parent / "assets" / "apa_screenshot_sample.png"
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


def data_url():
    return "data:image/png;base64," + base64.b64encode(IMG.read_bytes()).decode()


print("=" * 62)
print("截图问答端到端（多模态 + 工具循环）")
print("=" * 62)

if not IMG.exists():
    print(f"素材缺失: {IMG}")
    sys.exit(2)

img = data_url()

# [1] 截图问价：素材截图写着 qwen3.8-max（示例价 $2 / $6）
q = "截图里这个模型在阿里云百炼的价格是多少？"
a, d, s, st, ms = ask(q, "e2e-shot-1", images=[img])
print(f"\n[1] {q}  （{ms / 1000:.1f}s）")
check("[1] 模型从截图识别并调用 verify_price（stage=tool）", "tool" in st, str(st))
check("[1] official 证据", d.get("price_status") == "official", str(d))
check("[1] 回答含官方价格表（Singapore 双节点口径）", "Singapore" in a and "China (Beijing)" in a, a[:300])
check("[1] 审计通过（价格逐字来自官方证据）", d.get("price_audit") in ("ok", ""), str(d))
check("[1] 回答的是截图中的模型 qwen3.8-max", "qwen3.8-max" in a.lower(), a[:200])

# [2] 历史重发截图：当前句省略型号，图片随多模态历史 blocks 重发
mm_history = [
    {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": img}},
            {"type": "text", "text": q},
        ],
    },
    {"role": "assistant", "content": a[:2000]},
]
q2 = "新加坡节点的输出价格是多少？"
a2, d2, s2, st2, ms2 = ask(q2, "e2e-shot-2", history=mm_history)
print(f"\n[2] {q2}  （{ms2 / 1000:.1f}s）")
check("[2] 历史图片重发后模型仍能定位型号（重调 verify_price）",
      d2.get("price_status") == "official", f"{d2} {a2[:200]}")
check("[2] 回答含新加坡节点输出价（图片/历史推断成功）",
      ("Singapore" in a2 or "新加坡" in a2) and "$6" in a2, a2[:300])
check("[2] 审计通过", d2.get("price_audit") in ("ok", ""), str(d2))

# [3] 纯文本回归（images 空数组不影响旧链路）
a3, d3, s3, st3, ms3 = ask("qwen3.8-flash 的价格是多少", "e2e-shot-3")
check("[3] 纯文本回归 official", d3.get("price_status") == "official", str(d3))
check("[3] 纯文本审计通过", d3.get("price_audit") in ("ok", ""), str(d3))
check("[3] 回答含价格表", "Singapore" in a3, a3[:200])

print("-" * 62)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)
