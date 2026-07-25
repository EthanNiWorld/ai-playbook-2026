"""
令牌桶「回填速率」测量 —— BurstRate 时间维度验证
====================================================
上一步只测到「瞬时突发允许量（桶容量）≈650K token」，属于满桶一次性头寸。
本脚本测「回填速率」：桶多久回满、每秒能持续加多少 token 而不触发 BurstRate。

方法（令牌桶判别）：
  1. drain：先用大突发把桶打空（触发 BurstRate 即已见底）
  2. 空桶状态下按固定节奏 cadence：每 gap 秒加 wave_size×ptok tokens
     - 若 per-wave 速率 > 回填速率 → 桶补不回来，BurstRate 很快持续出现
     - 若 ≤ 回填速率 → 一路通过
  对比不同 cadence 速率，即可把回填速率夹逼出来（预期 ≈ TPM 2M/min ≈ 33K token/s）。

用法：
  python probe_refill.py --wave-size 4 --wave-gap 6 --waves 4   # 40K/s，预期触发
  python probe_refill.py --wave-size 3 --wave-gap 6 --waves 4   # 30K/s，预期通过
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
        return ("ok", (u.prompt_tokens + u.completion_tokens) if u else 0)
    except openai.APIStatusError as e:
        code = getattr(e, "code", None)
        if not code:
            body = getattr(e, "body", None)
            if isinstance(body, dict):
                code = body.get("code")
        return (code or f"http_{e.status_code}", 0)
    except Exception as e:
        return (f"err_{type(e).__name__}", 0)


def batch_msgs(n, ptok, tag):
    return [[{"role": "user",
              "content": build_context(ptok, salt=f"{tag}-{i}") + "\n\n请只回复 OK。"}]
            for i in range(n)]


def tally(res):
    counts, tok = {}, 0
    for code, t in res:
        counts[code] = counts.get(code, 0) + 1
        tok += t
    return counts, tok


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-tokens", type=int, default=60000)
    ap.add_argument("--drain-n", type=int, default=14, help="drain 阶段并发数（打空桶）")
    ap.add_argument("--wave-size", type=int, default=4, help="cadence 每波请求数")
    ap.add_argument("--wave-gap", type=float, default=6.0, help="cadence 波间隔秒")
    ap.add_argument("--waves", type=int, default=4, help="cadence 波数")
    ap.add_argument("--max-tokens", type=int, default=1)
    args = ap.parse_args()

    if not API_KEY or not BASE_URL:
        print("缺少 DASHSCOPE_API_KEY_CN / _url")
        return

    rate = args.wave_size * args.prompt_tokens / args.wave_gap
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL,
                         timeout=httpx.Timeout(150.0, connect=15.0), max_retries=0)

    print(f"Endpoint : {BASE_URL}")
    print(f"cadence  : 每 {args.wave_gap:.0f}s 加 {args.wave_size}×{args.prompt_tokens//1000}K "
          f"= {args.wave_size*args.prompt_tokens:,} tok/波  →  {rate/1000:.1f}K token/s")
    print(f"(对照：2M TPM ≈ 33.3K token/s)\n")

    # ---- 1) drain：打空桶 ----
    print(f"{'='*66}\n[drain] {args.drain_n}×{args.prompt_tokens//1000}K 突发打空令牌桶\n{'='*66}")
    dc, dtok = tally(await asyncio.gather(
        *[fire(client, m, args.max_tokens) for m in batch_msgs(args.drain_n, args.prompt_tokens, "drain")]))
    print(f"  {dc}  接纳≈{dtok:,} tok  "
          f"(BurstRate={dc.get('Throttling.BurstRate',0)} → 桶已见底)")

    # ---- 2) cadence：空桶起步，固定节奏加压 ----
    print(f"\n{'='*66}\n[cadence] 空桶起步，每 {args.wave_gap:.0f}s 加 {args.wave_size} 个，共 {args.waves} 波\n{'='*66}")
    total = {}
    for w in range(args.waves):
        wc, _ = tally(await asyncio.gather(
            *[fire(client, m, args.max_tokens) for m in batch_msgs(args.wave_size, args.prompt_tokens, f"cad{w}")]))
        for k, v in wc.items():
            total[k] = total.get(k, 0) + v
        br = wc.get("Throttling.BurstRate", 0)
        print(f"  wave {w+1}: {wc}  {'⚠️ BurstRate' if br else '✓ 通过'}")
        if w < args.waves - 1:
            await asyncio.sleep(args.wave_gap)

    br_total = total.get("Throttling.BurstRate", 0)
    print(f"\n{'#'*66}")
    print(f"# cadence {rate/1000:.1f}K tok/s 结果: {total}")
    if br_total > 0:
        print(f"# → 触发 BurstRate：该速率 > 回填速率（桶补不回来）")
    else:
        print(f"# → 全程通过：该速率 ≤ 回填速率（可持续）")
    print(f"{'#'*66}")


if __name__ == "__main__":
    asyncio.run(main())
