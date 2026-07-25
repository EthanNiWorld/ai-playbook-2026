"""
Throttling.BurstRate 阈值扫描
==============================
目标：标定本 workspace 的「瞬时突发允许量」，并判别它按 token 增量还是请求数增量计。

方法：多组「冷启动突发」——每组从空闲态一次性并发打出 n 个请求，单请求 prompt≈ptok。
组间冷却，等突发窗口重置。对每组记录 ok / BurstRate / limit_requests / 实际接纳 tokens。

判别逻辑：
  - 若「40×20K」与「80×10K」（token 需求都=800K）接纳的 tokens 相近 → token-bound
  - 若两者接纳的「请求数」相近 → request-bound

用法：
  python probe_scan.py --configs "8:60000,20:60000,40:20000,80:10000" --cooldown 50
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


async def run_config(client, n, ptok, max_tokens):
    # 每请求唯一 salt，避免同批缓存互相影响（不影响限流器，仅保证独立）
    msgs = [
        [{"role": "user", "content": build_context(ptok, salt=f"scan-{n}-{ptok}-{i}") + "\n\n请只回复 OK。"}]
        for i in range(n)
    ]
    res = await asyncio.gather(*[fire(client, m, max_tokens) for m in msgs])
    counts, adm_tok = {}, 0
    for code, tok in res:
        counts[code] = counts.get(code, 0) + 1
        adm_tok += tok
    return counts, adm_tok


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", type=str, default="8:60000,20:60000,40:20000,80:10000",
                    help="逗号分隔的 n:prompt_tokens 组合")
    ap.add_argument("--cooldown", type=float, default=50.0, help="组间冷却秒")
    ap.add_argument("--max-tokens", type=int, default=1)
    args = ap.parse_args()

    if not API_KEY or not BASE_URL:
        print("缺少 DASHSCOPE_API_KEY_CN / _url")
        return

    configs = []
    for part in args.configs.split(","):
        n, ptok = part.split(":")
        configs.append((int(n), int(ptok)))

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL,
                         timeout=httpx.Timeout(150.0, connect=15.0), max_retries=0)

    print(f"Endpoint : {BASE_URL}")
    print(f"Model    : {MODEL}")
    print(f"扫描组    : {configs}  |  组间冷却 {args.cooldown:.0f}s\n")

    rows = []
    total_tok = 0
    for i, (n, ptok) in enumerate(configs):
        demand = n * ptok
        print(f"{'='*70}\n[{i+1}/{len(configs)}] 冷启动突发: {n} 并发 × {ptok:,} tok  (瞬时需求 {demand:,} tok)\n{'='*70}")
        counts, adm = await run_config(client, n, ptok, args.max_tokens)
        total_tok += adm
        ok = counts.get("ok", 0)
        br = counts.get("Throttling.BurstRate", 0)
        lr = counts.get("limit_requests", 0)
        lt = counts.get("limit_tokens", 0)
        print(f"  分布: {counts}")
        print(f"  ok={ok}  BurstRate={br}  limit_requests={lr}  limit_tokens={lt}")
        print(f"  实际接纳 tokens ≈ {adm:,}")
        rows.append((n, ptok, demand, ok, br, lr, lt, adm))
        if i < len(configs) - 1:
            print(f"\n⏳ 冷却 {args.cooldown:.0f}s...\n")
            await asyncio.sleep(args.cooldown)

    print(f"\n{'#'*70}\n# 扫描汇总\n{'#'*70}")
    print(f"{'n×ptok':<16}{'需求tok':>12}{'ok':>5}{'Burst':>7}{'limReq':>8}{'接纳tok':>12}")
    print("-" * 70)
    for n, ptok, demand, ok, br, lr, lt, adm in rows:
        print(f"{f'{n}×{ptok//1000}K':<16}{demand:>12,}{ok:>5}{br:>7}{lr:>8}{adm:>12,}")
    print(f"\n总消耗 tokens ≈ {total_tok:,}")


if __name__ == "__main__":
    asyncio.run(main())
