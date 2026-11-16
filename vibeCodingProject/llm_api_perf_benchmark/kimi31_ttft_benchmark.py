#!/usr/bin/env python3
"""kimi-k3.1 系列 TTFT 专项基准测试（百炼 MaaS workspace 专属端点）

口径（与 glm52_benchmark.py / SPEC.md 一致）：
  TTFT = 请求发出 → 首个任意 token（reasoning_content 或 content，SLA 行规口径）
  首 token 到达后立即取消流（early-exit），不等完整响应，单请求 1~5s 级
  kimi-k3 系列为 always-thinking，无需传 thinking/reasoning_effort 参数
  另可选 --wait-content：等到首个正文 content token 再取消，
  同时报告「首任意 token」与「首正文 token」两个口径（正文口径受思考长度影响）

SLA 验收阈值（模型服务对外交付口径）：
  TTFT P50 < 4s、P75 < 8s、P90 < 12s、P99 < 30s

端点与凭证（.env，默认国际站 SG workspace，2026-11-12 已验证 kimi-k3.1-pro 可用）：
  DASHSCOPE_API_KEY_INTL_SG_TEST + DASHSCOPE_API_KEY_INTL_SG_TEST_URL
  可用 KIMI_API_KEY / KIMI_BASE_URL 覆盖（如切北京 workspace：
  DASHSCOPE_API_KEY_INTL_BJ_TEST + _URL 的值）

运行：
  .venv/bin/python kimi31_ttft_benchmark.py --probe          # 探测模型 ID 可用性
  .venv/bin/python kimi31_ttft_benchmark.py --samples 30     # TTFT 专项
  .venv/bin/python kimi31_ttft_benchmark.py --wait-content --samples 10
"""
import argparse
import asyncio
import os
import statistics
import sys
import time
import uuid

import httpx
from openai import AsyncOpenAI, RateLimitError

# 加载 .env（.env 已被 .gitignore 忽略，密钥不进 Git）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(ROOT, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.getenv("KIMI_API_KEY") or os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", "")
BASE_URL = os.getenv("KIMI_BASE_URL") or os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "")

SYSTEM_PROMPT = (
    "You are an expert software engineer and system architect. "
    "Respond with detailed, production-ready code and analysis."
)
USER_PROMPT = (
    "Design a rate limiter for a high-concurrency API gateway. "
    "Compare token bucket vs sliding window, then give a Python implementation. "
    f"[request-nonce: {uuid.uuid4().hex}]"  # 每请求唯一，避免隐式缓存干扰 TTFT
)

SLA = [("P50", 50, 4.0), ("P75", 75, 8.0), ("P90", 90, 12.0), ("P99", 99, 30.0)]


def percentile(data, p):
    if not data:
        return 0.0
    s = sorted(data)
    n = len(s)
    if n == 1:
        return s[0]
    k = (n - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, n - 1)
    return s[f] + (k - f) * (s[c] - s[f])


async def measure_ttft(client, model, wait_content=False, max_tokens=256, retries=5):
    """单请求流式 TTFT 测量（429 指数退避重试）；返回 (ttft_any, ttft_content, error)"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]
    ttft_any = None
    ttft_content = None
    try:
        for attempt in range(retries):
            start = time.perf_counter()  # 每次重试重新计时，退避等待不计入 TTFT
            ttft_any = None
            ttft_content = None
            try:
                stream = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=1.0,
                    stream=True,
                )
                break
            except RateLimitError:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(5 * (attempt + 1))
        async for chunk in stream:
            now = time.perf_counter()
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            rc = getattr(delta, "reasoning_content", None)
            if rc and ttft_any is None:
                ttft_any = now - start
                if not wait_content:
                    break
            if delta.content:
                if ttft_any is None:
                    ttft_any = now - start
                if ttft_content is None:
                    ttft_content = now - start
                    break
        await stream.close()
        if ttft_any is None:
            return None, None, "no token received"
        return ttft_any, ttft_content, None
    except Exception as e:
        return None, None, f"{type(e).__name__}: {str(e)[:200]}"


async def probe(client):
    """探测候选模型 ID 在当前端点的可用性（max_tokens=16 轻量请求）"""
    for model in ["kimi-k3.1", "kimi-k3.1-pro"]:
        try:
            r = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=16,
            )
            print(f"  ✅ {model}: 可用 (finish_reason={r.choices[0].finish_reason})")
        except Exception as e:
            print(f"  ❌ {model}: {type(e).__name__}: {str(e)[:160]}")


async def run_bench(client, model, samples, concurrency, wait_content, interval):
    print(f"\n  预热 1 请求...")
    _, _, err = await measure_ttft(client, model, wait_content)
    if err:
        print(f"  ❌ 预热失败: {err}")
        sys.exit(1)

    print(f"  TTFT 专项: samples={samples} concurrency={concurrency} "
          f"interval={interval}s wait_content={wait_content}")
    sem = asyncio.Semaphore(concurrency)
    results = []

    async def one(i):
        await asyncio.sleep(i * interval)  # 错峰启动，控制到达率避开 RPM 限流
        async with sem:
            r = await measure_ttft(client, model, wait_content)
            results.append(r)
            any_t, content_t, err = r
            if err:
                print(f"    [{i+1}/{samples}] ❌ {err}")
            elif wait_content and content_t is not None:
                print(f"    [{i+1}/{samples}] any={any_t:.2f}s content={content_t:.2f}s")
            else:
                print(f"    [{i+1}/{samples}] TTFT={any_t:.2f}s")

    t0 = time.perf_counter()
    await asyncio.gather(*(one(i) for i in range(samples)))
    wall = time.perf_counter() - t0

    ok = [r for r in results if r[2] is None]
    errs = [r for r in results if r[2] is not None]
    any_times = [r[0] for r in ok]
    content_times = [r[1] for r in ok if r[1] is not None]

    print(f"\n{'='*64}")
    print(f"结果汇总  model={model}  endpoint={BASE_URL}")
    print(f"{'='*64}")
    print(f"  成功 {len(ok)}/{samples}，失败 {len(errs)}，总耗时 {wall:.1f}s")
    if errs:
        for _, _, e in errs[:5]:
            print(f"    error: {e}")
    if not any_times:
        return

    def report(name, times):
        print(f"\n  [{name}] n={len(times)}")
        print(f"    mean={statistics.mean(times):.2f}s  min={min(times):.2f}s  "
              f"max={max(times):.2f}s")
        for label, p, threshold in SLA:
            v = percentile(times, p)
            mark = "✅" if v < threshold else "❌"
            print(f"    {label}={v:.2f}s  (SLA < {threshold:.0f}s) {mark}")

    report("TTFT 首任意 token（SLA 口径）", any_times)
    if wait_content and content_times:
        report("首正文 content token（参考口径，含思考耗时）", content_times)


async def main():
    parser = argparse.ArgumentParser(description="kimi-k3.1 系列 TTFT 专项基准测试")
    parser.add_argument("--model", default=os.getenv("TEST_MODEL", "kimi-k3.1-pro"))
    parser.add_argument("--probe", action="store_true", help="仅探测模型 ID 可用性")
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--interval", type=float, default=2.0,
                        help="请求错峰启动间隔秒数（控制到达率，默认 2s ≈ 30 RPM）")
    parser.add_argument("--wait-content", action="store_true",
                        help="等到首个正文 token（同时报告双口径）")
    args = parser.parse_args()

    if not API_KEY or not BASE_URL:
        print("❌ 缺少端点/凭证：DASHSCOPE_API_KEY_INTL_SG_TEST(_URL) 或 KIMI_API_KEY/KIMI_BASE_URL")
        sys.exit(1)

    print(f"  Endpoint : {BASE_URL}")
    print(f"  Model    : {args.model}")
    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=httpx.Timeout(300.0, connect=30.0),
        max_retries=0,
    )
    if args.probe:
        await probe(client)
    else:
        await run_bench(client, args.model, args.samples, args.concurrency,
                        args.wait_content, args.interval)


if __name__ == "__main__":
    asyncio.run(main())