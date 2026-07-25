"""
429 限流返回体探针
==================
用并发突发请求触发一次真实 429（RateLimitError），完整打印：
  - HTTP status_code
  - 限流相关响应头（retry-after / x-ratelimit-* / request-id / date）
  - 原始 body 文本 + 解析后的 JSON（error.code / message）
  - openai SDK 异常字段（.message / .code / .request_id）

成本控制：默认先用微小请求高并发触发（RPM/并发限流，几乎不耗 token）。
若未触发，可加 --big 用 ~60K 大请求压 TPM 限流（会消耗 token）。

  python probe_429.py --burst 120                 # 微小请求突发
  python probe_429.py --burst 60 --big            # 60K 大请求压 TPM
"""

import os
import json
import asyncio
import argparse

import httpx
import openai
from openai import AsyncOpenAI

from glm52_multiturn_benchmark import MODEL, API_KEY, BASE_URL
from glm52_2m_tpm_benchmark import build_context


def dump_rate_limit_error(tag: str, e: openai.APIStatusError):
    print(f"\n{'='*70}\n触发 429 @ {tag}\n{'='*70}")
    print(f"status_code : {getattr(e, 'status_code', 'n/a')}")
    print(f"sdk.message : {getattr(e, 'message', 'n/a')}")
    print(f"sdk.code    : {getattr(e, 'code', 'n/a')}")
    print(f"request_id  : {getattr(e, 'request_id', 'n/a')}")

    resp = getattr(e, "response", None)
    if resp is not None:
        print(f"\n--- 关键响应头 ---")
        interesting = [
            "retry-after", "date", "x-request-id", "x-ratelimit-limit",
            "x-ratelimit-remaining", "x-ratelimit-reset",
        ]
        for k, v in resp.headers.items():
            kl = k.lower()
            if kl in interesting or "ratelimit" in kl or "request" in kl or "retry" in kl:
                print(f"  {k}: {v}")

        print(f"\n--- 原始 body ---")
        try:
            print(resp.text)
        except Exception as ex:
            print(f"(读取 body 失败: {ex})")

        print(f"\n--- 解析 JSON ---")
        try:
            print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
        except Exception:
            print("(body 非 JSON)")


async def fire(client: AsyncOpenAI, idx: int, messages, max_tokens: int):
    try:
        await client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=max_tokens,
            temperature=0.7, stream=False,
        )
        return ("ok", None)
    except openai.RateLimitError as e:
        return ("429", e)
    except openai.APIStatusError as e:
        return (f"http_{e.status_code}", e)
    except Exception as e:
        return (f"err_{type(e).__name__}", e)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--burst", type=int, default=120, help="并发突发请求数")
    ap.add_argument("--big", action="store_true", help="用 ~60K 大请求压 TPM（耗 token）")
    ap.add_argument("--input-tokens", type=int, default=60000)
    ap.add_argument("--max-tokens", type=int, default=1)
    args = ap.parse_args()

    if not API_KEY or not BASE_URL:
        print("缺少 DASHSCOPE_API_KEY_CN / _url")
        return

    if args.big:
        ctx = build_context(args.input_tokens, salt="probe")
        messages = [{"role": "user", "content": ctx + "\n\n请只回复 OK。"}]
        mode = f"big ~{args.input_tokens//1000}K prompt"
    else:
        messages = [{"role": "user", "content": "hi"}]
        mode = "tiny prompt"

    print(f"Endpoint : {BASE_URL}")
    print(f"Model    : {MODEL}")
    print(f"突发      : {args.burst} 并发 × [{mode}], max_tokens={args.max_tokens}")

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL,
                         timeout=httpx.Timeout(120.0, connect=15.0), max_retries=0)

    results = await asyncio.gather(*[fire(client, i, messages, args.max_tokens)
                                     for i in range(args.burst)])

    counts = {}
    samples = {}   # code -> exception
    for status, e in results:
        counts[status] = counts.get(status, 0) + 1
        if status == "429" and e is not None:
            code = getattr(e, "code", None) or "unknown"
            counts_key = f"429:{code}"
            counts[counts_key] = counts.get(counts_key, 0) + 1
            if code not in samples:
                samples[code] = e

    print(f"\n结果分布: {counts}")

    if samples:
        for code, e in samples.items():
            dump_rate_limit_error(f"{mode} | code={code}", e)
    else:
        print("\n未触发 429。可加大 --burst，或加 --big 用大请求压 TPM。")


if __name__ == "__main__":
    asyncio.run(main())
