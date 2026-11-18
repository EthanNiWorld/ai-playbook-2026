"""端到端 ECS 服务器询价验证（需服务已启动：run.py --port 8000）
场景：入口 chip 问法 → 跨地域裸金属追问 → 缺地域反问（新会话）
运行: .venv/bin/python tests/e2e/test_ecs_price.py
"""
import json

import httpx

BASE = "http://127.0.0.1:8000"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  OK  " if cond else "  FAIL ") + name + ("" if cond else f"   {detail}"))
    PASS, FAIL = PASS + (1 if cond else 0), FAIL + (0 if cond else 1)


def ask(q, history, session):
    r = httpx.post(
        f"{BASE}/api/chat",
        json={"question": q, "history": history, "session_id": session},
        timeout=180,
    )
    parts, done, statuses, sources = [], {}, [], []
    for line in r.text.splitlines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if ev["type"] == "delta":
                parts.append(ev["text"])
            elif ev["type"] == "status":
                statuses.append(ev.get("message", ""))
            elif ev["type"] == "sources":
                sources = ev.get("sources", [])
            elif ev["type"] == "done":
                done = ev
            elif ev["type"] == "error":
                done["error"] = ev["message"]
    answer = "".join(parts)
    history = history + [
        {"role": "user", "content": q},
        {"role": "assistant", "content": answer[:2000]},
    ]
    return answer, done, statuses, history, sources


print("=" * 60)
print("ECS 服务器询价端到端")
print("=" * 60)

h = []
a1, d1, s1, h, src1 = ask("乌兰察布 ecs.g9i.large 服务器包月多少钱？", h, "e2e-ecs-price")
print(f"\n[1] chip 问法 price_status={d1.get('price_status')} audit={d1.get('price_audit')}")
check("[1] 未被缺型号反问劫持", "你想问哪个模型" not in a1, a1[:120])
check("[1] 调用了 get_ecs_price", any("ECS" in s for s in s1), str(s1))
check("[1] 包月价 $32.29 逐字来自证据（两位小数）", "$32.29" in a1, a1[:300])
check("[1] official + audit ok", d1.get("price_status") == "official"
      and d1.get("price_audit") == "ok", str(d1))
check("[1] 附计算器链接", "pricing-calculator" in a1, a1[-300:])
check("[1] 不附百炼模型定价页", "model-pricing" not in a1, a1[-300:])
check("[1] 无无关知识库引用", not any(s.get("kind") == "knowledge" for s in src1), str(src1))

a2, d2, s2, h, src2 = ask("那香港的 ebmg9ae.48xlarge 呢？", h, "e2e-ecs-price")
print(f"\n[2] 跨地域裸金属追问 price_status={d2.get('price_status')} audit={d2.get('price_audit')}")
check("[2] 追问触发询价", any("ECS" in s for s in s2), str(s2))
check("[2] 香港裸金属包月 $6,627.60", "$6,627.60" in a2, a2[:300])
check("[2] official + audit ok", d2.get("price_status") == "official"
      and d2.get("price_audit") == "ok", str(d2))
check("[2] 追问也无知识库引用", not any(s.get("kind") == "knowledge" for s in src2), str(src2))

a3, d3, s3, _, _ = ask("ecs.g9i.large 多少钱", [], "e2e-ecs-price-clarify")
print(f"\n[3] 缺地域反问 price_status={d3.get('price_status')}")
check("[3] 反问地域而非报价", "地域" in a3 and "$32" not in a3 and "$6" not in a3, a3[:200])
check("[3] 未擅自询价", not any("ECS" in s for s in s3), str(s3))

a4, d4, s4, h, _ = ask("把刚才两个报价生成一个可转发的链接，方便我发给客户", h, "e2e-ecs-price")
print(f"\n[4] ECS 报价分享链接")
import re as _re
urls = _re.findall(r"https?://[^\s)\u3002\uff0c]+", a4)
share_urls = [u for u in urls if "pricing-calculator" not in u and "model-pricing" not in u]
check("[4] 不再拒答‘只支持百炼模型’", "只支持百炼" not in a4 and "暂时生成不了" not in a4, a4[:200])
check("[4] 回答含分享链接", bool(share_urls), a4[:300])
if share_urls:
    resp = httpx.get(share_urls[0], timeout=30, follow_redirects=True)
    check("[4] 链接可访问且为 HTML 卡片", resp.status_code == 200
          and "text/html" in resp.headers.get("content-type", "")
          and "ECS" in resp.text, str(resp.status_code))
    check("[4] 卡片含两台规格与总计", "ecs.g9i.large" in resp.text
          and "ecs.ebmg9ae.48xlarge" in resp.text and "总计" in resp.text, resp.text[:200])
    print("SHARE_URL:", share_urls[0])

print("-" * 60)
print(f"结果: {PASS} 通过 / {FAIL} 失败")
raise SystemExit(1 if FAIL else 0)