# -*- coding: utf-8 -*-
"""
kimi-k3.1-pro 阻塞性验收失败项实证脚本（对应 vendor-report-kimi-k3.1-pro-2026-11-12.html）

复测 4 条阻塞失败，用原始 HTTP 抓完整响应 JSON（含 SDK 会丢弃的厂商扩展字段）：
  F1/F2 缓存：cache_write_tokens 字段是否返回？重复长前缀 cached_tokens 是否 >0（缓存真生效）？
  F3 参数边界：prompt_cache_options.ttl 大写 '1H' 是否被拒(400)还是接受(200)？
  F4 流式：stream=true 不开 include_usage vs 开 include_usage，末块 choices 形态与 usage 位置。

密钥从仓库根 .env 安全解析（不在 shell 层 source，不回显）。端点默认北京 workspace 专属网关，
与报告 Aliyun(hk) 同属阿里云 compatible-mode 协议层。可用 TEST_BASE_URL/TEST_API_KEY 覆盖。
"""
import os
import json
import time
import httpx

# ---- 安全加载 .env（仅 KEY=VALUE 行，覆盖式）----
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
_env = os.path.join(_root, ".env")
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("TEST_API_KEY") or os.getenv("DASHSCOPE_API_KEY_CN_TEST", "")
BASE_URL = (os.getenv("TEST_BASE_URL") or os.getenv("DASHSCOPE_API_KEY_CN_URL", "")
            or "https://llm-7ufq8xadyf99jlbp.cn-beijing.maas.aliyuncs.com/compatible-mode/v1").rstrip("/")
MODEL = os.getenv("TEST_MODEL", "kimi-k3.1-pro")
URL = BASE_URL + "/chat/completions"
HDR = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}

# 固定长前缀（>1000 token），两轮字节级一致以触发缓存
_PARA = ("The sea has always been a mirror in which people see both their smallness and their ambition. "
         "Long before charts and compasses, sailors read the water the way farmers read the sky, gathering "
         "meaning from the color of a wave, the temperature of a current, the flight of a distant bird. ")
PREFIX = "Reading edition: cacheProbe2026\n\n" + (_PARA * 28)


def _post(payload, tries=4):
    for i in range(tries):
        r = httpx.post(URL, headers=HDR, json=payload, timeout=120)
        if r.status_code == 429:
            time.sleep(5 * (i + 1))
            continue
        return r
    return r


def _usage(r):
    try:
        return r.json().get("usage", {})
    except Exception:
        return {"_raw": r.text[:300]}


def test_cache():
    print("\n========== F1/F2 缓存：字段存在性 + 是否真生效 ==========")
    base = {"model": MODEL, "max_completion_tokens": 64, "reasoning_effort": "low",
            "messages": [{"role": "system", "content": PREFIX},
                         {"role": "user", "content": "用一句话概括你的角色。"}]}
    r1 = _post(base)
    u1 = _usage(r1)
    print(f"[轮1 首次写入] status={r1.status_code}")
    print("  usage =", json.dumps(u1, ensure_ascii=False))
    print("  prompt_tokens_details =", json.dumps(u1.get("prompt_tokens_details", {}), ensure_ascii=False))
    print("  >> cache_write_tokens 字段存在?", "cache_write_tokens" in u1.get("prompt_tokens_details", {}))
    time.sleep(6)
    r2 = _post(base)  # 同前缀重放
    u2 = _usage(r2)
    print(f"[轮2 同前缀重放] status={r2.status_code}")
    print("  usage =", json.dumps(u2, ensure_ascii=False))
    ct = u2.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    print(f"  >> cached_tokens={ct}  → 缓存{'生效(命中>0)' if ct and ct > 0 else '未命中(=0)'}")
    time.sleep(4)
    r2b = _post(base)  # 再重放一次
    ct2 = _usage(r2b).get("prompt_tokens_details", {}).get("cached_tokens", 0)
    print(f"[轮2b 再次重放] cached_tokens={ct2}")
    # 显式 implicit+5m
    r3 = _post({**base, "prompt_cache_options": {"mode": "implicit", "ttl": "5m"}})
    print(f"[轮3 显式 implicit+5m] status={r3.status_code} usage={json.dumps(_usage(r3), ensure_ascii=False)}")


def test_ttl_case():
    print("\n========== F3 参数边界：ttl 大小写 ==========")
    base = {"model": MODEL, "max_completion_tokens": 32, "reasoning_effort": "low",
            "messages": [{"role": "system", "content": PREFIX},
                         {"role": "user", "content": "hi"}]}
    for ttl in ["1H", "1h", "5m", "30m"]:
        r = _post({**base, "prompt_cache_options": {"mode": "implicit", "ttl": ttl}})
        print(f"  ttl={ttl!r:8} → status={r.status_code}  {'(接受)' if r.status_code == 200 else '(拒绝)'}")
        if r.status_code != 200:
            print("     err =", r.text[:200])
        time.sleep(2)


def _stream_last(payload, label):
    chunks = []
    status = None
    for attempt in range(5):
        chunks = []
        with httpx.stream("POST", URL, headers=HDR, json=payload, timeout=120) as r:
            status = r.status_code
            if status == 429:
                time.sleep(8 * (attempt + 1))
                continue
            for line in r.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    chunks.append("[DONE]")
                    continue
                try:
                    chunks.append(json.loads(data))
                except Exception:
                    pass
        break
    print(f"\n  [{label}] status={status} 共{len(chunks)}块")
    for c in chunks[-3:]:
        if c == "[DONE]":
            print("    末块: [DONE]")
        else:
            ch = c.get("choices")
            print(f"    choices={json.dumps(ch, ensure_ascii=False)[:160]} | 顶层usage={json.dumps(c.get('usage'), ensure_ascii=False)}")
    # 找最后一个非[DONE]数据块
    data_chunks = [c for c in chunks if c != "[DONE]"]
    if data_chunks:
        last = data_chunks[-1]
        print(f"    >> 最后数据块 choices 是否为空数组[]? {last.get('choices') == []}")
        print(f"    >> 最后数据块 顶层usage 是否非空? {bool(last.get('usage'))}")


def test_stream():
    print("\n========== F4 流式：include_usage 开关对比 ==========")
    base = {"model": MODEL, "max_completion_tokens": 64, "reasoning_effort": "low",
            "messages": [{"role": "user", "content": "hello"}], "stream": True}
    _stream_last(base, "stream=true 不带 include_usage（报告原样）")
    time.sleep(2)
    _stream_last({**base, "stream_options": {"include_usage": True}}, "stream=true + include_usage=true")


if __name__ == "__main__":
    print(f"端点: {BASE_URL}\n模型: {MODEL}")
    test_cache()
    test_ttl_case()
    test_stream()
    print("\n========== 完成 ==========")