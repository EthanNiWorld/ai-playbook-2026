"""
kimi-k3.1-pro 原生 Responses 协议 / Anthropic Messages 协议接入实测
====================================================================
目标：确认百炼托管的 kimi-k3.1-pro 能否走两条"非 Chat Completions"协议面：
  A. OpenAI 兼容 Responses API：POST {host}/compatible-mode/v1/responses
  B. Anthropic 兼容 Messages：POST {host}/apps/anthropic/v1/messages
     （认证支持 x-api-key 或 Authorization: Bearer，需 anthropic-version 头）
  C. 对照组：原生 Chat Completions，确认模型在该节点已授权
  D. B 的流式形态（stream=true）事件序列
节点：国际站新加坡 / 国际站北京（.env 中 *_TEST 密钥与 _URL 成对读取）
运行：python3 test_kimi_k31_protocol_support.py
"""

import json
import os
import time
from pathlib import Path

import httpx

# ---- 加载 .env ----
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

MODEL = os.getenv("TEST_MODEL", "kimi-k3.1-pro")
PROMPT = "用一句话解释什么是向量检索。"

NODES = [
    ("INTL-SG", os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST"),
     "https://llm-ablnum2bgfvl34hs.ap-southeast-1.maas.aliyuncs.com"),
    ("INTL-BJ", os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST"),
     "https://llm-kvw0aiysjfv4g6fh.cn-beijing.maas.aliyuncs.com"),
]

client = httpx.Client(timeout=180)


def req(method, url, headers, payload, stream=False, retries=3):
    for attempt in range(retries):
        try:
            r = client.request(method, url, headers=headers, json=payload)
        except Exception as e:
            return None, f"异常 {e}"
        if r.status_code == 429:
            wait = 8 * (attempt + 1)
            print(f"      429 限流，{wait}s 后重试 ({attempt + 1}/{retries})")
            time.sleep(wait)
            continue
        return r, ""
    return None, "重试耗尽（429）"


def show(label, r, note=""):
    if r is None:
        print(f"  [{label}] {note}")
        return
    print(f"  [{label}] HTTP {r.status_code}")
    ct = r.headers.get("content-type", "")
    if "json" not in ct:
        print(f"      body: {r.text[:200]}")
        return
    try:
        d = r.json()
    except Exception:
        print(f"      body: {r.text[:200]}")
        return
    if r.status_code != 200:
        err = d.get("error", d)
        if isinstance(err, dict):
            print(f"      type={err.get('type')} code={err.get('code')} msg={str(err.get('message'))[:220]}")
        else:
            print(f"      msg={str(err)[:220]}")
        return
    print(f"      {note}")
    print(f"      keys={list(d)[:10]}")
    return d


for label, key, host in NODES:
    if not key:
        print(f"\n=== {label} 缺少密钥，跳过 ===")
        continue
    print(f"\n=== {label} ({host.split('//')[1].split('.')[0]}) model={MODEL} ===")
    auth = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # C. 对照组 chat/completions
    r, err = req("POST", f"{host}/compatible-mode/v1/chat/completions", auth, {
        "model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 64, "stream": False})
    d = show("C. chat/completions", r, err)
    if d and d.get("choices"):
        msg = d["choices"][0]["message"]
        txt = (msg.get("content") or "")[:60].replace("\n", " ")
        print(f"      content='{txt}' reasoning={(msg.get('reasoning_content') or '')[:30]!r}")

    # A. Responses API
    r, err = req("POST", f"{host}/compatible-mode/v1/responses", auth, {
        "model": MODEL, "input": PROMPT, "max_output_tokens": 1024})
    d = show("A. Responses (/compatible-mode/v1/responses)", r, err)
    if d:
        print(f"      status={d.get('status')} usage={json.dumps(d.get('usage', {}), ensure_ascii=False)}")
        outs = d.get("output") or []
        for o in outs[:3]:
            ctype = o.get("type")
            txt = ""
            if ctype == "message":
                txt = "".join(c.get("text", "") for c in (o.get("content") or []))[:60]
            print(f"      output item type={ctype} {txt!r}")

    # B. Anthropic Messages（非流式）
    anth = {"x-api-key": key, "Authorization": f"Bearer {key}",
            "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    r, err = req("POST", f"{host}/apps/anthropic/v1/messages", anth, {
        "model": MODEL, "max_tokens": 256,
        "messages": [{"role": "user", "content": PROMPT}]})
    d = show("B. Anthropic Messages (/apps/anthropic/v1/messages)", r, err)
    if d:
        blocks = d.get("content") or []
        print(f"      model={d.get('model')} stop_reason={d.get('stop_reason')} "
              f"usage={json.dumps(d.get('usage', {}), ensure_ascii=False)}")
        for b in blocks[:3]:
            snippet = (b.get("text") or b.get("thinking") or "")[:50].replace("\n", " ")
            print(f"      block type={b.get('type')} {snippet!r}")

    # D. Anthropic Messages 流式
    r, err = req("POST", f"{host}/apps/anthropic/v1/messages", anth, {
        "model": MODEL, "max_tokens": 128, "stream": True,
        "messages": [{"role": "user", "content": PROMPT}]})
    if r is None:
        print(f"  [D. Anthropic stream] {err}")
    elif r.status_code != 200:
        try:
            print(f"  [D. Anthropic stream] HTTP {r.status_code} {json.dumps(r.json(), ensure_ascii=False)[:200]}")
        except Exception:
            print(f"  [D. Anthropic stream] HTTP {r.status_code} {r.text[:200]}")
    else:
        events = []
        for line in r.text.splitlines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
        print(f"  [D. Anthropic stream] HTTP 200 event 序列前 12: {events[:12]}")

    # E. Anthropic thinking 可关闭（售前常问）
    r, err = req("POST", f"{host}/apps/anthropic/v1/messages", anth, {
        "model": MODEL, "max_tokens": 512, "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": PROMPT}]})
    d = show("E. Anthropic thinking=disabled", r, err)
    if d:
        types = [b.get("type") for b in (d.get("content") or [])]
        print(f"      content block types={types} stop_reason={d.get('stop_reason')}")

    # E2. 对照：Chat Completions 面 enable_thinking=false 是否同样无效
    r, err = req("POST", f"{host}/compatible-mode/v1/chat/completions", auth, {
        "model": MODEL, "max_tokens": 512, "enable_thinking": False,
        "messages": [{"role": "user", "content": PROMPT}]})
    d = show("E2. chat/completions enable_thinking=false", r, err)
    if d and d.get("choices"):
        m = d["choices"][0]["message"]
        rc = m.get("reasoning_content") or ""
        print(f"      reasoning_len={len(rc)} content_len={len(m.get('content') or '')}")

    # F. Responses 流式 SSE 事件序列
    r, err = req("POST", f"{host}/compatible-mode/v1/responses", auth, {
        "model": MODEL, "input": PROMPT, "max_output_tokens": 256, "stream": True})
    if r is None:
        print(f"  [F. Responses stream] {err}")
    elif r.status_code != 200:
        try:
            print(f"  [F. Responses stream] HTTP {r.status_code} {json.dumps(r.json(), ensure_ascii=False)[:200]}")
        except Exception:
            print(f"  [F. Responses stream] HTTP {r.status_code} {r.text[:200]}")
    else:
        ev = [l.split(":", 1)[1].strip() for l in r.text.splitlines() if l.startswith("event:")]
        uniq = list(dict.fromkeys(ev))
        print(f"  [F. Responses stream] HTTP 200 事件类型（去重保序）: {uniq[:14]}")
