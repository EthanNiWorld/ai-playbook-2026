"""
DashScope 多账号 TPM 翻倍校验压测脚本
====================================

目的
----
验证"N 个独立 UID 账号 ≈ N 倍 TPM"的假设是否成立。

测试方法
--------
1. **基准阶段 (single)**：仅用 1 个账号，持续 60s 高并发压测，统计实际 TPM
2. **倍数阶段 (multi)**：用全部 N 个账号，持续 60s 高并发压测，统计实际 TPM
3. **校验**：实测倍数 = multi TPM / single TPM，理论上应接近 N

使用前提
--------
- 必须配置 ≥ 2 个账号（DASHSCOPE_ACCOUNT_1_KEY ... DASHSCOPE_ACCOUNT_N_KEY）
- 各账号 base_url 应一致（同一地域），否则限流上限不可比
- **建议使用独立 UID 的阿里云账号**；同 UID 多 Key 会共享限流，倍数不会翻倍（这正是本脚本要校验的）

运行
----
  # 默认对比模式：先单账号基准 60s，再多账号 60s
  python dashscope_tpm_benchmark.py

  # 仅跑单账号基准
  python dashscope_tpm_benchmark.py --mode single --duration 30

  # 仅跑多账号
  python dashscope_tpm_benchmark.py --mode multi --duration 30

  # 自定义模型与并发
  python dashscope_tpm_benchmark.py --model qwen-flash --concurrency 80 --max-tokens 800

参数说明
--------
- --mode:        single / multi / compare（默认 compare）
- --duration:    每阶段持续秒数（默认 60s）
- --concurrency: 单账号并发数（multi 模式自动 × 账号数）
- --model:       压测模型（推荐 qwen-flash，单价低 TPM 高）
- --max-tokens:  单次回复最大 tokens（越大越容易打满 TPM）

输出解读
--------
- 实测倍数 ≈ N         => 多账号扩展生效（独立 UID）
- 实测倍数 < 1.5       => 限流共享（同 UID 多 Key，无扩展效应）
- 单账号 TPM 达上限    => 已触及该模型 UID 级 TPM 配额

参考
----
- 百炼限流: https://www.alibabacloud.com/help/en/model-studio/rate-limit
"""

import os
import sys
import time
import asyncio
import argparse
import logging
import statistics
from collections import deque
from typing import Dict, Any

from dashscope_multi_account_router import (
    Account,
    DashScopeRouter,
    load_accounts_from_env,
)


# ---------------------------------------------------------------------------
# 滚动窗口 TPM 跟踪器
# ---------------------------------------------------------------------------
class TPMTracker:
    """60s 滚动窗口 token 统计"""

    def __init__(self, window_seconds: int = 60):
        self.window = window_seconds
        self.events: deque = deque()  # (ts, tokens)

    def record(self, tokens: int):
        now = time.time()
        self.events.append((now, tokens))
        self._evict(now)

    def _evict(self, now: float):
        cutoff = now - self.window
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def current_tpm(self) -> int:
        now = time.time()
        self._evict(now)
        return sum(t for _, t in self.events)


# ---------------------------------------------------------------------------
# 压测核心
# ---------------------------------------------------------------------------
async def benchmark(
    router: DashScopeRouter,
    duration_seconds: int,
    concurrency: int,
    model: str,
    max_tokens: int,
    prompt: str,
    label: str = "",
    extra_body: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    持续 duration 秒，concurrency 路并发，返回统计
    """
    tracker = TPMTracker(window_seconds=60)
    counters = {
        "requests": 0,
        "success": 0,
        "rate_limited": 0,
        "errors": 0,
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "latencies": [],
        "per_account_tokens": {},
    }

    start = time.time()
    end = start + duration_seconds

    async def worker(worker_id: int):
        """单个工作协程：循环发请求直到时间到"""
        while time.time() < end:
            counters["requests"] += 1
            kw = {}
            if extra_body:
                kw["extra_body"] = extra_body
            try:
                result = await asyncio.wait_for(
                    router.chat_completion(
                        messages=[{"role": "user", "content": prompt}],
                        model=model,
                        max_tokens=max_tokens,
                        temperature=0.7,
                        **kw,
                    ),
                    timeout=max(30, duration_seconds),
                )
            except asyncio.TimeoutError:
                counters["errors"] += 1
                continue
            except Exception:
                counters["errors"] += 1
                continue

            if result["success"]:
                counters["success"] += 1
                tokens = result["usage"]["total_tokens"]
                counters["total_tokens"] += tokens
                counters["input_tokens"] += result["usage"]["prompt_tokens"]
                counters["output_tokens"] += result["usage"]["completion_tokens"]
                counters["latencies"].append(result["latency_ms"])
                tracker.record(tokens)
                uid = result["account_uid"]
                counters["per_account_tokens"][uid] = (
                    counters["per_account_tokens"].get(uid, 0) + tokens
                )
            else:
                err = (result.get("error") or "").lower()
                if "429" in err or "rate" in err or "quota" in err:
                    counters["rate_limited"] += 1
                else:
                    counters["errors"] += 1

    # 进度打印任务
    async def progress_printer():
        while time.time() < end:
            await asyncio.sleep(5)
            elapsed = time.time() - start
            tpm = tracker.current_tpm()
            print(
                f"  [{label}] +{elapsed:>4.0f}s  "
                f"成功={counters['success']:<5} "
                f"限流={counters['rate_limited']:<4} "
                f"错误={counters['errors']:<3} "
                f"窗口TPM={tpm:>10,}",
                flush=True,
            )

    progress_task = asyncio.create_task(progress_printer())

    # 启动固定数量的 worker，避免任务堆积
    workers = [asyncio.create_task(worker(i)) for i in range(concurrency)]
    await asyncio.gather(*workers, return_exceptions=True)

    progress_task.cancel()
    try:
        await progress_task
    except asyncio.CancelledError:
        pass

    elapsed = time.time() - start
    latencies = counters["latencies"]
    actual_tpm = counters["total_tokens"] / elapsed * 60 if elapsed > 0 else 0

    return {
        "label": label,
        "duration": elapsed,
        "requests": counters["requests"],
        "success": counters["success"],
        "rate_limited": counters["rate_limited"],
        "errors": counters["errors"],
        "total_tokens": counters["total_tokens"],
        "input_tokens": counters["input_tokens"],
        "output_tokens": counters["output_tokens"],
        "actual_tpm": actual_tpm,
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "p95_latency_ms": (
            statistics.quantiles(latencies, n=20)[18]
            if len(latencies) >= 20
            else (max(latencies) if latencies else 0)
        ),
        "per_account_tokens": counters["per_account_tokens"],
    }


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def print_stats(stats: Dict[str, Any]):
    print(f"\n--- {stats['label']} 阶段结果 ---")
    print(f"  实际持续:        {stats['duration']:.1f} s")
    print(f"  请求总数:        {stats['requests']}")
    print(f"  成功 / 限流 / 错误: {stats['success']} / {stats['rate_limited']} / {stats['errors']}")
    print(f"  Token 总量:      {stats['total_tokens']:,} (入: {stats['input_tokens']:,}, 出: {stats['output_tokens']:,})")
    print(f"  实测 TPM:        {stats['actual_tpm']:,.0f}")
    print(f"  平均延迟:        {stats['avg_latency_ms']:.1f} ms")
    print(f"  P95 延迟:        {stats['p95_latency_ms']:.1f} ms")
    if stats["per_account_tokens"]:
        print(f"  各账号 token 分布:")
        for uid, tk in sorted(stats["per_account_tokens"].items()):
            print(f"    {uid}: {tk:,}")


def print_compare(single: Dict[str, Any], multi: Dict[str, Any], n_accounts: int):
    s_tpm = single["actual_tpm"]
    m_tpm = multi["actual_tpm"]
    ratio = m_tpm / s_tpm if s_tpm > 0 else 0
    achievement = ratio / n_accounts * 100 if n_accounts > 0 else 0

    print("\n" + "=" * 70)
    print("TPM 翻倍校验报告")
    print("=" * 70)
    print(f"{'指标':<24}{'单账号':>16}{'多账号(N=' + str(n_accounts) + ')':>20}")
    print("-" * 70)
    print(f"{'实测 TPM':<24}{s_tpm:>16,.0f}{m_tpm:>20,.0f}")
    print(f"{'成功请求数':<24}{single['success']:>16,}{multi['success']:>20,}")
    print(f"{'限流次数':<24}{single['rate_limited']:>16,}{multi['rate_limited']:>20,}")
    print(f"{'平均延迟 (ms)':<24}{single['avg_latency_ms']:>16.1f}{multi['avg_latency_ms']:>20.1f}")
    print("-" * 70)
    print(f"{'实测倍数':<24}{ratio:>16.2f}×")
    print(f"{'理论倍数':<24}{n_accounts:>16}×")
    print(f"{'达成率':<24}{achievement:>15.1f}%")
    print("=" * 70)

    # 结论判断
    if achievement >= 80:
        print("✅ 多账号扩展生效，符合 N 倍 TPM 假设（独立 UID）")
    elif achievement >= 50:
        print("⚠️  部分扩展生效，可能受限于：")
        print("   - 模型本身的全局调度容量")
        print("   - 客户端并发不足以打满")
        print("   - 部分账号属于同一 UID（限流共享）")
    else:
        print("❌ 扩展未生效，强烈怀疑账号同 UID 或共享限流池")
        print("   排查建议：")
        print("   1. 确认每个 KEY 来自独立的阿里云账号（UID）")
        print("   2. 检查 base_url 是否一致（不同地域不可比）")
        print("   3. 提高 --concurrency 参数确保单账号被打满")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(description="DashScope 多账号 TPM 翻倍校验")
    parser.add_argument("--mode", choices=["single", "multi", "compare"], default="compare")
    parser.add_argument("--duration", type=int, default=60, help="每阶段持续秒数")
    parser.add_argument("--concurrency", type=int, default=50, help="单账号并发数")
    parser.add_argument("--model", default="qwen-flash")
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument(
        "--prompt",
        default="请用中文写一段约 400 字的科幻短篇，主题：太空冒险中的意外发现",
    )
    parser.add_argument("--cooldown", type=int, default=10, help="429 后冷却秒数（压测用短冷却）")
    parser.add_argument("--cooldown-between", type=int, default=65, help="single 和 multi 之间的等待秒数")
    parser.add_argument("--enable-thinking", action="store_true", help="开启 deepseek-v4 思考模式（更易打满 TPM）")
    args = parser.parse_args()

    extra_body = {"enable_thinking": True} if args.enable_thinking else None

    # 高并发压测下限制 router 日志，避免 IO 拖累
    logging.getLogger("dashscope_router").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    accounts = load_accounts_from_env()
    n = len(accounts)
    print(f"加载 {n} 个账号: {[a.uid for a in accounts]}")

    if n < 2 and args.mode in ("multi", "compare"):
        print(f"⚠️  仅 {n} 个账号，multi/compare 模式无意义。建议至少配置 2 个账号。")
        if n < 1:
            sys.exit(1)

    print(f"压测参数: model={args.model} duration={args.duration}s "
          f"concurrency={args.concurrency} max_tokens={args.max_tokens}")

    single_stats = None
    multi_stats = None

    # ---- 单账号基准 ----
    if args.mode in ("single", "compare"):
        single_router = DashScopeRouter(
            accounts=accounts[:1],
            strategy="weighted_round_robin",
            cooldown_seconds=args.cooldown,
            max_retries=2,
        )
        print(f"\n========== [1/{2 if args.mode=='compare' else 1}] 单账号基准 ({args.duration}s) ==========")
        single_stats = await benchmark(
            single_router,
            args.duration,
            args.concurrency,
            args.model,
            args.max_tokens,
            args.prompt,
            label="single",
            extra_body=extra_body,
        )
        print_stats(single_stats)

    # ---- 多账号 ----
    if args.mode in ("multi", "compare"):
        if args.mode == "compare":
            print(f"\n等待 {args.cooldown_between}s 让限流窗口完全清零...")
            await asyncio.sleep(args.cooldown_between)

        multi_router = DashScopeRouter(
            accounts=accounts,
            strategy="weighted_round_robin",
            cooldown_seconds=args.cooldown,
            max_retries=2,
        )
        multi_concurrency = args.concurrency * n  # 并发也要 × N，否则打不满
        print(f"\n========== [2/2] {n} 账号扩展 ({args.duration}s, 并发={multi_concurrency}) ==========")
        multi_stats = await benchmark(
            multi_router,
            args.duration,
            multi_concurrency,
            args.model,
            args.max_tokens,
            args.prompt,
            label=f"multi(N={n})",
            extra_body=extra_body,
        )
        print_stats(multi_stats)

    # ---- 对比报告 ----
    if args.mode == "compare" and single_stats and multi_stats:
        print_compare(single_stats, multi_stats, n)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[中断] 用户取消")
