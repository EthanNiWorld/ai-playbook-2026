"""yundun-key（AI DeepSign 网关）kimi-k3 TPM / 缓存命中率 / P50 TTFT 压测

背景：AI DeepSign 网关（api-aideepsign.cn-hangzhou.aliyuncs.com）以 Anthropic
Messages 协议（/v1/messages）代理 kimi-k3，响应带 C2PA 内容签名（_manifest）。
本脚本实测该网关的三项性能/容量指标：

  Phase 1 (ttft)  — 流式请求采样 TTFT（首个 content_block_delta 事件），
                    early-exit 拿到首 token 即断开，输出 P50/P95
  Phase 2 (cache) — 固定长前缀（~2K tokens）连续重复请求，观察 usage 中
                    cache_creation_input_tokens / cache_read_input_tokens
                    → 隐式前缀缓存命中情况与命中率
  Phase 3 (tpm)   — 阶梯并发爬坡（1→2→4→8→16→32），每阶固定窗口统计
                    成功请求的 (input+output) tokens/min；触发限流（HTTP 429
                    或自定义 code）即停，输出限流错误样例
                    注意：TPM 需要爬坡，服务端配额窗口是滚动统计的

实测结论（2026-09-11）见脚本末尾 Changelog 注释。

端点与凭证（.env）：yundun-key（sk-ds. JWT）、yundun-url
协议要点：x-api-key 头 + anthropic-version: 2023-06-01；thinking 映射为
Anthropic thinking block（signature 为空）；usage 为标准 Anthropic 结构
（input_tokens / output_tokens / cache_creation_input_tokens / cache_read_input_tokens）

运行：
  python3 test_yundun_k3_tpm_ttft.py                  # 全部三阶段
  python3 test_yundun_k3_tpm_ttft.py --phase ttft     # 仅 TTFT
  python3 test_yundun_k3_tpm_ttft.py --phase cache    # 仅缓存
  python3 test_yundun_k3_tpm_ttft.py --phase tpm --ramp 1,2,4,8,16,32 --step-duration 60
"""
import os
import time
import json
import uuid
import argparse
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ---------------------------------------------------------------------------
# 配置加载（复用项目惯例：直接解析仓库根 .env 并覆盖环境变量）
# ---------------------------------------------------------------------------
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "..", ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("yundun-key", "").strip()
BASE_URL = os.getenv("yundun-url", "").strip() or \
    "https://api-aideepsign.cn-hangzhou.aliyuncs.com/v1/messages"
MODEL = "kimi-k3"
TIMEOUT = 180

HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}

# 缓存测试用长前缀（中文段落重复，~3000 字符 ≈ 2K+ tokens，>256 触发隐式缓存）
_CACHE_PREFIX_TEXT = (
    "以下是一段用于压测上下文缓存的技术背景资料，请记住其中的关键信息。\n" * 8
    + "分布式推理系统的核心指标包括：TTFT（首 token 延迟）反映排队与预填充开销；"
      "TPOT（每 token 输出时间）反映解码吞吐；TPM/RPM 是平台配额口径，通常按"
      "滚动窗口统计；上下文缓存通过复用相同前缀的 KV 状态降低预填充成本，命中"
      "部分按折扣计费；限流触发时平台返回 429 并附带配额恢复时间提示。\n"
) * 18  # ~3000+ 字符


def _pad_unique(text: str, target_chars: int) -> str:
    """在文本后填充唯一内容到目标长度（避免隐式缓存命中，保证压测真实消耗）"""
    pad = f"\n[uniq-{uuid.uuid4().hex}] 数据样本编号："
    while len(text) + len(pad) < target_chars:
        pad += str(uuid.uuid4().int % 10_000_000) + "，"
    return text + pad


def make_payload(user_text, max_tokens=128, stream=False, system=None):
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_text}],
    }
    if system:
        body["system"] = system
    if stream:
        body["stream"] = True
    return body


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(f"HTTP {status} [{code}] {message}")


def is_rate_limited(status, code=""):
    return status == 429 or "hrottl" in (code or "").lower() \
        or "hrottle" in (code or "").lower() or "rate" in (code or "").lower()


def chat_once(payload):
    """非流式调用，返回响应 JSON；限流抛 ApiError(status=429)"""
    r = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=TIMEOUT)
    try:
        data = r.json()
    except ValueError:
        raise ApiError(r.status_code, "BadJSON", r.text[:300])
    if r.status_code != 200 or ("error" in data and "content" not in data):
        code = data.get("code") or (data.get("error") or {}).get("type", "")
        msg = data.get("message") or (data.get("error") or {}).get("message", "")
        raise ApiError(r.status_code, code, msg)
    return data


def usage_of(data):
    u = data.get("usage") or {}
    return {
        "input": u.get("input_tokens", 0),
        "output": u.get("output_tokens", 0),
        "cache_create": u.get("cache_creation_input_tokens", 0),
        "cache_read": u.get("cache_read_input_tokens", 0),
    }


def chat_ttft(user_text, max_tokens=512):
    """流式请求，返回 (ttft_ms, thinking 首段预览)；首个 delta 后 early-exit"""
    t0 = time.time()
    r = requests.post(BASE_URL, headers=HEADERS,
                      json=make_payload(user_text, max_tokens, stream=True),
                      timeout=TIMEOUT, stream=True)
    if r.status_code != 200:
        try:
            d = r.json()
            raise ApiError(r.status_code, d.get("code", ""), d.get("message", ""))
        except ValueError:
            raise ApiError(r.status_code, "BadJSON", r.text[:300])
    ttft, preview = None, ""
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        chunk = raw[5:].strip()
        if not chunk:
            continue
        try:
            evt = json.loads(chunk)
        except ValueError:
            continue
        if evt.get("type") == "content_block_delta":
            ttft = (time.time() - t0) * 1000
            preview = (evt.get("delta") or {}).get("thinking") \
                or (evt.get("delta") or {}).get("text") or ""
            break  # early-exit：拿到首 token 即断开，省 token
    r.close()
    if ttft is None:
        raise ApiError(200, "NoDelta", "流式响应中未出现 content_block_delta")
    return ttft, preview


# ---------------------------------------------------------------------------
# Phase 1: TTFT
# ---------------------------------------------------------------------------
def phase_ttft(samples):
    print(f"\n{'=' * 20} Phase 1: TTFT（{samples} 次流式采样，early-exit）{'=' * 20}")
    ttfts = []
    for i in range(samples):
        try:
            ms, preview = chat_ttft("1+1等于几？只回答数字。")
            ttfts.append(ms)
            print(f"  #{i + 1}: TTFT = {ms:8.0f} ms | 首 token: {preview[:24]!r}")
        except ApiError as e:
            print(f"  #{i + 1}: ❌ {e}")
        time.sleep(1)
    if ttfts:
        ttfts.sort()
        p50 = statistics.median(ttfts)
        p95 = ttfts[max(0, int(len(ttfts) * 0.95) - 1)]
        print(f"\n  ✅ TTFT P50 = {p50:.0f} ms | P95 = {p95:.0f} ms"
              f" | min = {min(ttfts):.0f} | max = {max(ttfts):.0f} | n = {len(ttfts)}")
        return p50
    return None


# ---------------------------------------------------------------------------
# Phase 2: 缓存命中率
# ---------------------------------------------------------------------------
def phase_cache(rounds):
    print(f"\n{'=' * 20} Phase 2: 缓存命中率（固定长前缀 × {rounds} 轮）{'=' * 20}")
    q = "基于上述资料回答：TTFT 反映什么开销？一句话。"
    hits = 0
    total_cost = 0
    for i in range(rounds):
        payload = make_payload(q, max_tokens=512, system=_CACHE_PREFIX_TEXT)
        try:
            u = usage_of(chat_once(payload))
        except ApiError as e:
            print(f"  轮次 {i + 1}: ❌ {e}")
            continue
        denom = u["input"] + u["cache_create"] + u["cache_read"]
        rate = (u["cache_read"] / denom * 100) if denom else 0
        hit = "🎯 命中" if u["cache_read"] > 0 else "✍️ 未命中"
        if u["cache_read"] > 0:
            hits += 1
        total_cost += denom
        print(f"  轮次 {i + 1}: input={u['input']} cache_creation={u['cache_create']}"
              f" cache_read={u['cache_read']} → {hit}（命中率 {rate:.1f}%）")
        time.sleep(2)
    print(f"\n  ✅ {rounds} 轮中 {hits} 轮命中缓存（命中轮次占比 {hits / max(1, rounds) * 100:.0f}%）")
    return hits


# ---------------------------------------------------------------------------
# Phase 3: TPM 阶梯爬坡
# ---------------------------------------------------------------------------
def phase_tpm(ramp, step_duration, prompt_chars, max_tokens):
    print(f"\n{'=' * 20} Phase 3: TPM 爬坡（并发 {ramp}，每阶 {step_duration}s）{'=' * 20}")
    print(f"  请求规格: prompt≈{prompt_chars} 字符（唯一化防缓存） + max_tokens={max_tokens}")
    limit_hit = None

    def worker(stop_at, stats, lock):
        while time.time() < stop_at:
            try:
                data = chat_once(make_payload(
                    _pad_unique("请简要总结以下内容的主要观点：\n", prompt_chars),
                    max_tokens=max_tokens))
                u = usage_of(data)
                with lock:
                    stats["ok"] += 1
                    stats["tokens"] += u["input"] + u["output"]
            except ApiError as e:
                with lock:
                    stats["errors"] += 1
                    stats["last_error"] = str(e)
                if is_rate_limited(e.status, e.code):
                    with lock:
                        stats["rate_limited"] += 1
                    return  # 触发限流，本 worker 退出
                time.sleep(0.5)
            except Exception:
                with lock:
                    stats["errors"] += 1
                time.sleep(0.5)

    for c in ramp:
        stats = {"ok": 0, "tokens": 0, "errors": 0, "rate_limited": 0,
                 "last_error": ""}
        lock = threading.Lock()
        stop_at = time.time() + step_duration
        threads = [threading.Thread(target=worker, args=(stop_at, stats, lock))
                   for _ in range(c)]
        t_start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - t_start
        tpm = stats["tokens"] / (elapsed / 60)
        line = (f"  并发 {c:3d} | {elapsed:5.1f}s | 成功 {stats['ok']:4d} 请求"
                f" | {stats['tokens']:8d} tokens | ≈{tpm:9.0f} TPM")
        if stats["rate_limited"]:
            line += f" | 🚨 限流 ×{stats['rate_limited']}（{stats['last_error'][:80]}）"
            print(line)
            limit_hit = {"concurrency": c, "tpm": tpm, "error": stats["last_error"]}
            break
        if stats["errors"]:
            line += f" | 其他错误 ×{stats['errors']}（{stats['last_error'][:60]}）"
        print(line)
        time.sleep(5)  # 阶间缓冲，让服务端滚动窗口推进

    print(f"\n  {'=' * 16} TPM 爬坡结论 {'=' * 16}")
    if limit_hit:
        print(f"  🚨 在并发 {limit_hit['concurrency']} 触发限流，"
              f"实测 TPM ≈ {limit_hit['tpm']:.0f}")
        print(f"  限流错误样例: {limit_hit['error'][:200]}")
    else:
        print(f"  ⚠️ 爬到并发 {ramp[-1]} 未触发限流"
              f"（最高观测 ≈{tpm:.0f} TPM），可加大 --ramp / --step-duration 继续")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all",
                    choices=["all", "ttft", "cache", "tpm"])
    ap.add_argument("--ttft-samples", type=int, default=8)
    ap.add_argument("--cache-rounds", type=int, default=5)
    ap.add_argument("--ramp", default="1,2,4,8,16,32")
    ap.add_argument("--step-duration", type=int, default=60)
    ap.add_argument("--prompt-chars", type=int, default=1500)
    ap.add_argument("--max-tokens", type=int, default=128)
    args = ap.parse_args()

    print(f"Base URL: {BASE_URL}")
    print(f"Model:    {MODEL}")
    print(f"API Key:  {(API_KEY[:10] + '...' + API_KEY[-6:]) if len(API_KEY) > 16 else '(未设置)'}")
    if not API_KEY:
        print("\n❌ 未检测到 yundun-key（.env）")
        raise SystemExit(1)

    ramp = [int(x) for x in args.ramp.split(",") if x.strip()]
    if args.phase in ("all", "ttft"):
        phase_ttft(args.ttft_samples)
    if args.phase in ("all", "cache"):
        phase_cache(args.cache_rounds)
    if args.phase in ("all", "tpm"):
        phase_tpm(ramp, args.step_duration, args.prompt_chars, args.max_tokens)
    print("\n完成。")


if __name__ == "__main__":
    main()
