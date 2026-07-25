"""
Throttling.BurstRate 机制验证探针
==================================
验证假设：BurstRate 限制的是「负载爬升速度」，而非绝对 RPM/TPM 上限。
方法：用同样的大请求（制造 token 陡增），对比两种投放方式的 429 code 分布：
  A. spike  —— 瞬时全部并发打出（陡峭爬升）
  B. ramp   —— 分小波缓慢投放，每波之间间隔数秒（平滑爬升）
若 ramp 的 Throttling.BurstRate 明显少于 spike，即证明其对「斜率」敏感。

  python probe_burst.py --prompt-tokens 60000 --spike-n 30 --ramp-n 12 --wave-size 2 --wave-gap 6

成本：仅被服务端「接纳」的请求消耗 token，被 429 拒绝的不计费。脚本会汇总实际消耗。
"""

import asyncio
import argparse

import httpx
import openai
from openai import AsyncOpenAI

from glm52_multiturn_benchmark import MODEL, API_KEY, BASE_URL
from glm52_2m_tpm_benchmark import build_context


async def fire(client, messages, max_tokens):
    try:
        resp = await client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=max_tokens,
            temperature=0.7, stream=False,
        )
        u = resp.usage
        tok = (u.prompt_tokens + u.completion_tokens) if u else 0
        return ("ok", tok)
    except openai.RateLimitError as e:
        return (getattr(e, "code", None) or "429", 0)
    except openai.APIStatusError as e:
        # Throttling.BurstRate 走原生错误，code 在这里
        code = getattr(e, "code", None)
        if not code:
            body = getattr(e, "body", None)
            if isinstance(body, dict):
                code = body.get("code")
        return (code or f"http_{e.status_code}", 0)
    except Exception as e:
        return (f"err_{type(e).__name__}", 0)


def tally(pairs):
    counts, tokens = {}, 0
    for code, tok in pairs:
        counts[code] = counts.get(code, 0) + 1
        tokens += tok
    return counts, tokens


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-tokens", type=int, default=60000)
    ap.add_argument("--spike-n", type=int, default=30, help="spike 阶段瞬时并发数")
    ap.add_argument("--ramp-n", type=int, default=12, help="ramp 阶段总请求数")
    ap.add_argument("--wave-size", type=int, default=2, help="ramp 每波请求数")
    ap.add_argument("--wave-gap", type=float, default=6.0, help="ramp 波间隔秒")
    ap.add_argument("--cooldown", type=float, default=65.0, help="两阶段之间冷却秒（等限流器重置）")
    ap.add_argument("--max-tokens", type=int, default=1)
    args = ap.parse_args()

    if not API_KEY or not BASE_URL:
        print("缺少 DASHSCOPE_API_KEY_CN / _url")
        return

    ctx = build_context(args.prompt_tokens, salt="burst")
    messages = [{"role": "user", "content": ctx + "\n\n请只回复 OK。"}]

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL,
                         timeout=httpx.Timeout(120.0, connect=15.0), max_retries=0)

    print(f"Endpoint : {BASE_URL}")
    print(f"Model    : {MODEL}  |  prompt ~{args.prompt_tokens//1000}K tok/请求\n")

    # ---- A. spike：瞬时全部并发 ----
    print(f"{'='*66}\n[A] SPIKE — {args.spike_n} 并发瞬时打出（陡峭爬升）\n{'='*66}")
    spike = await asyncio.gather(*[fire(client, messages, args.max_tokens)
                                   for _ in range(args.spike_n)])
    sc, stok = tally(spike)
    print(f"  code 分布: {sc}")
    print(f"  BurstRate 次数: {sc.get('Throttling.BurstRate', 0)}  |  接纳 ok: {sc.get('ok', 0)}  |  消耗 tokens: {stok:,}")

    print(f"\n⏳ 冷却 {args.cooldown:.0f}s 等限流器重置...")
    await asyncio.sleep(args.cooldown)

    # ---- B. ramp：分小波缓慢投放 ----
    n_waves = (args.ramp_n + args.wave_size - 1) // args.wave_size
    print(f"\n{'='*66}\n[B] RAMP — 共 {args.ramp_n} 请求，每 {args.wave_gap:.0f}s 投 {args.wave_size} 个（平滑爬升，{n_waves} 波）\n{'='*66}")
    ramp_all = []
    sent = 0
    for w in range(n_waves):
        k = min(args.wave_size, args.ramp_n - sent)
        wave = await asyncio.gather(*[fire(client, messages, args.max_tokens) for _ in range(k)])
        sent += k
        ramp_all.extend(wave)
        wc, _ = tally(wave)
        br = wc.get("Throttling.BurstRate", 0)
        print(f"  wave {w+1:>2}: 投 {k} → {wc}  {'⚠️BurstRate' if br else ''}")
        if sent < args.ramp_n:
            await asyncio.sleep(args.wave_gap)
    rc, rtok = tally(ramp_all)
    print(f"\n  ramp 汇总 code 分布: {rc}")
    print(f"  BurstRate 次数: {rc.get('Throttling.BurstRate', 0)}  |  接纳 ok: {rc.get('ok', 0)}  |  消耗 tokens: {rtok:,}")

    # ---- 结论 ----
    print(f"\n{'#'*66}\n# 对比结论\n{'#'*66}")
    print(f"  SPIKE : BurstRate={sc.get('Throttling.BurstRate',0):>3}  ok={sc.get('ok',0):>3}  (投 {args.spike_n})")
    print(f"  RAMP  : BurstRate={rc.get('Throttling.BurstRate',0):>3}  ok={rc.get('ok',0):>3}  (投 {args.ramp_n})")
    print(f"  总消耗 tokens: {stok + rtok:,}")


if __name__ == "__main__":
    asyncio.run(main())
