"""
DeepSeek-V4-Flash TPOT (Time Per Output Token) 测试脚本
=======================================================

测量指标
--------
- TTFT: Time To First Token（首 token 延迟）
- TPOT: Time Per Output Token（每个输出 token 的平均耗时）
- TPS:  Tokens Per Second（输出吞吐率）

测试方法
--------
使用流式 (streaming) 调用，记录每个 chunk 到达时间戳，
TPOT = (总生成时间 - TTFT) / (output_tokens - 1)

运行
----
  # 默认 5 轮测试
  python test_ds_v4_flash_tpot.py

  # 自定义轮次和 max_tokens
  python test_ds_v4_flash_tpot.py --rounds 10 --max-tokens 1024

环境变量
--------
  DASHSCOPE_API_KEY_INTL_BJ_TEST  (国际站北京节点 API Key)

节点
----
  国际站北京: https://llm-kvw0aiysjfv4g6fh.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
"""

import os
import sys
import time
import statistics
import argparse
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# 加载项目根目录 .env
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# ---------- 配置 ----------
BASE_URL = "https://llm-kvw0aiysjfv4g6fh.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
API_KEY_ENV = "DASHSCOPE_API_KEY_INTL_BJ_TEST"
MODEL = "deepseek-v4-flash"

PROMPT = "请用中文详细介绍量子计算的基本原理、当前进展和未来应用前景，至少800字。"


def run_single_round(client: OpenAI, max_tokens: int, round_idx: int) -> dict:
    """执行单轮流式调用，返回延迟指标"""
    token_timestamps = []
    ttft = None
    output_tokens = 0
    usage_info = None

    t_start = time.perf_counter()

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": PROMPT},
        ],
        stream=True,
        stream_options={"include_usage": True},
        max_tokens=max_tokens,
        temperature=1.0,
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            now = time.perf_counter()
            if ttft is None:
                ttft = (now - t_start) * 1000  # ms
            token_timestamps.append(now)
            output_tokens += 1
        if chunk.usage:
            usage_info = chunk.usage

    t_end = time.perf_counter()
    total_time_ms = (t_end - t_start) * 1000

    # 用 API 返回的 completion_tokens 作为准确 token 数
    actual_output_tokens = usage_info.completion_tokens if usage_info else output_tokens

    # TPOT = (总时间 - TTFT) / (output_tokens - 1)
    generation_time_ms = total_time_ms - (ttft or 0)
    tpot_ms = generation_time_ms / max(actual_output_tokens - 1, 1)
    tps = actual_output_tokens / (generation_time_ms / 1000) if generation_time_ms > 0 else 0

    result = {
        "round": round_idx,
        "ttft_ms": ttft or 0,
        "total_ms": total_time_ms,
        "output_tokens": actual_output_tokens,
        "tpot_ms": tpot_ms,
        "tps": tps,
    }

    print(
        f"  Round {round_idx:>2}: "
        f"TTFT={result['ttft_ms']:>7.1f}ms  "
        f"TPOT={result['tpot_ms']:>6.2f}ms  "
        f"TPS={result['tps']:>6.1f}  "
        f"tokens={actual_output_tokens}"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="DeepSeek-V4-Flash TPOT Benchmark")
    parser.add_argument("--rounds", type=int, default=5, help="测试轮次 (默认 5)")
    parser.add_argument("--max-tokens", type=int, default=2048, help="最大输出 tokens (默认 2048)")
    parser.add_argument("--warmup", type=int, default=1, help="预热轮次 (默认 1)")
    args = parser.parse_args()

    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        print(f"[错误] 环境变量 {API_KEY_ENV} 未设置")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    print("=" * 65)
    print(f"  Model:    {MODEL}")
    print(f"  Endpoint: {BASE_URL}")
    print(f"  Rounds:   {args.rounds} (+ {args.warmup} warmup)")
    print(f"  MaxTokens:{args.max_tokens}")
    print(f"  Prompt:   {PROMPT[:50]}...")
    print("=" * 65)

    # 预热
    if args.warmup > 0:
        print(f"\n--- 预热 ({args.warmup} 轮) ---")
        for i in range(args.warmup):
            try:
                run_single_round(client, args.max_tokens, 0)
            except Exception as e:
                print(f"  预热失败: {e}")
                sys.exit(1)

    # 正式测试
    print(f"\n--- 正式测试 ({args.rounds} 轮) ---")
    results = []
    for i in range(1, args.rounds + 1):
        try:
            r = run_single_round(client, args.max_tokens, i)
            results.append(r)
        except Exception as e:
            print(f"  Round {i} 失败: {e}")
        time.sleep(0.5)  # 轮次间短暂间隔

    if not results:
        print("\n[错误] 无有效结果")
        sys.exit(1)

    # 汇总统计
    ttfts = [r["ttft_ms"] for r in results]
    tpots = [r["tpot_ms"] for r in results]
    tps_list = [r["tps"] for r in results]
    total_tokens = [r["output_tokens"] for r in results]

    print("\n" + "=" * 65)
    print("  TPOT 测试报告")
    print("=" * 65)
    print(f"  {'指标':<20}{'Avg':>10}{'P50':>10}{'P95':>10}{'Min':>10}{'Max':>10}")
    print(f"  {'-'*60}")

    for name, data in [("TTFT (ms)", ttfts), ("TPOT (ms)", tpots), ("TPS (tok/s)", tps_list)]:
        avg = statistics.mean(data)
        p50 = statistics.median(data)
        p95 = sorted(data)[int(len(data) * 0.95)] if len(data) >= 2 else data[0]
        mn = min(data)
        mx = max(data)
        print(f"  {name:<20}{avg:>10.2f}{p50:>10.2f}{p95:>10.2f}{mn:>10.2f}{mx:>10.2f}")

    print(f"  {'-'*60}")
    print(f"  有效轮次: {len(results)}/{args.rounds}")
    print(f"  平均输出 tokens: {statistics.mean(total_tokens):.0f}")
    print("=" * 65)


if __name__ == "__main__":
    main()
