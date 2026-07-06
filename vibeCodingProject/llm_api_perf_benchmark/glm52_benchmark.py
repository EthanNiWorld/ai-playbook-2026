"""
GLM-5.2 国际站→北京节点 TTFT / TPS / TPM 性能基准测试（优化版）
================================================================

优化设计（比原版快 3-5x）：
  - TTFT 测试：首 token 到达后立即取消，不等完整响应（每请求 1-5s）
  - TPS 测试：reasoning_effort=high，加速推理阶段，专注测生成速率
  - Warm-up：1 个轻量请求（提前取消模式）
  - TTFT / TPS 分离独立测试，各自最优配置

测试指标：
  Phase 1A - TTFT 专项：early_exit + max_tokens=256 + effort=max
  Phase 1B - TPS 专项：effort=high + max_tokens=4096
  Phase 2  - TPM 压测：高并发 120s 窗口

运行：
  # 连通性验证
  python glm52_benchmark.py --phase latency --samples 3 --concurrency 3

  # 正式延迟测试（TTFT + TPS）
  python glm52_benchmark.py --phase latency --samples 100 --concurrency 10

  # TPM 压测
  python glm52_benchmark.py --phase tpm --duration 120 --tpm-concurrency 30

  # 完整测试
  python glm52_benchmark.py --samples 100 --concurrency 10

环境变量：
  DASHSCOPE_API_KEY_CN      - 北京节点 API Key（必填，来自 .env）
  DASHSCOPE_API_KEY_CN_url  - 北京节点 endpoint（必填，来自 .env）
  GLM52_MODEL               - 可覆盖模型名，默认 glm-5.2
"""

import os
import sys
import time
import asyncio
import argparse
import statistics
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from dotenv import load_dotenv
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------
# 加载项目根目录 .env（ai-knowledge-base/.env）
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_ENV_PATH)

BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_url")
API_KEY = os.getenv("DASHSCOPE_API_KEY_CN")
MODEL = os.getenv("GLM52_MODEL", "glm-5.2")

# ---------------------------------------------------------------------------
# Prompt 库（AI Coding + Agentic 场景）
# ---------------------------------------------------------------------------
CODING_PROMPTS = [
    "请用 Python 实现一个支持并发的 LRU Cache，要求线程安全，支持 TTL 过期淘汰，包含完整的单元测试。输出完整可运行的代码。",
    "请用 Go 语言实现一个轻量级的任务调度器（Task Scheduler），支持定时任务、重试机制、优先级队列，并写出使用示例。",
    "设计一个 AI Agent 的工具调用框架：支持工具注册、参数校验、重试策略、并发调用编排。用 Python 实现核心代码，包含 type hints。",
    "请实现一个 Git diff 解析器：输入 unified diff 格式文本，输出结构化的变更信息（文件名、行号、增删内容）。用 Python 实现，包含边界情况处理。",
    "用 TypeScript 实现一个响应式状态管理库（类似 Zustand），支持 computed 属性、中间件、持久化、DevTools 集成。输出核心实现代码。",
]

AGENTIC_PROMPTS = [
    "你是一个代码审查 Agent。请分析以下需求并制定执行计划：需要重构一个 10 万行的 Java 微服务项目，将其从 Spring Boot 2 迁移到 Spring Boot 3，同时升级 Java 8 到 Java 17。请输出详细的步骤规划、风险评估、回滚方案。",
    "作为项目规划 Agent，请为以下目标制定技术方案：构建一个支持 100 万日活的实时聊天系统，要求消息延迟 < 200ms、支持消息撤回、已读回执、离线消息同步。输出完整的架构设计、技术选型、容量规划。",
    "你是 DevOps Agent，请为以下场景设计 CI/CD Pipeline：一个包含 5 个微服务的 Kubernetes 集群，需要支持蓝绿部署、金丝雀发布、自动回滚、性能回归测试。输出完整的 Pipeline YAML 和部署策略。",
]

ALL_PROMPTS = CODING_PROMPTS + AGENTIC_PROMPTS

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class LatencyResult:
    ttft_seconds: float
    tps: float
    total_seconds: float
    output_tokens: int
    input_tokens: int
    success: bool
    error: Optional[str] = None
    extra: Optional[dict] = field(default=None)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def percentile(data: List[float], p: float) -> float:
    """计算百分位数（线性插值）"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    k = (n - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < n else f
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


# ---------------------------------------------------------------------------
# Phase 1: 延迟测试（流式，精确测量 TTFT + TPS）
# ---------------------------------------------------------------------------

async def measure_single_request(
    client: AsyncOpenAI,
    prompt: str,
    max_tokens: int = 2048,
    early_exit_after_ttft: bool = False,
    reasoning_effort: str = "max",
) -> LatencyResult:
    """单次流式请求，精确测量 TTFT 和 TPS"""
    messages = [
        {
            "role": "system",
            "content": "You are an expert software engineer and system architect. "
                       "Respond with detailed, production-ready code and analysis.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        start_time = time.perf_counter()
        first_any_token_time = None      # TTFT（SLA 口径：首任意 token，reasoning 或 content）
        first_content_token_time = None  # 首 content token（参考指标）
        last_content_token_time = None
        client_token_count = 0
        reasoning_token_count = 0
        input_tokens = 0
        output_tokens = 0

        stream = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=1.0,
            stream=True,
            stream_options={"include_usage": True},
            # GLM-5.2 深度思考 + reasoning_effort=max（深度推理，默认值）
            extra_body={
                "thinking": {"type": "enabled"},
                "reasoning_effort": "high",
            },
        )

        async for chunk in stream:
            now = time.perf_counter()

            # 最后一条 chunk 带 usage（OpenAI 兼容协议）
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0

            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # GLM-5.2 thinking 模式：reasoning_content 在 content 之前到达
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                reasoning_token_count += 1
                # TTFT：首个任意类型 token 到达时间（业内标准口径）
                if first_any_token_time is None:
                    first_any_token_time = now
                    # TTFT-only 模式：首 token 到达后立即取消，不等完整响应
                    if early_exit_after_ttft:
                        break

            # 记录首/末 content token 时间戳
            if hasattr(delta, 'content') and delta.content:
                # TTFT：content 也是有效 token，如果 reasoning 没先到，这里也算
                if first_any_token_time is None:
                    first_any_token_time = now
                if first_content_token_time is None:
                    first_content_token_time = now
                last_content_token_time = now
                client_token_count += 1

        total_time = time.perf_counter() - start_time

        if first_any_token_time is None:
            reason = (
                f"No tokens received at all "
                f"(output_tokens={output_tokens}，"
                f"max_tokens={max_tokens})"
            )
            return LatencyResult(
                ttft_seconds=total_time,
                tps=0,
                total_seconds=total_time,
                output_tokens=output_tokens,
                input_tokens=input_tokens,
                success=False,
                error=reason,
            )

        # TTFT（SLA 口径）：首任意 token 到达时间
        ttft = first_any_token_time - start_time
        # content_ttft（参考）：首 content token 到达时间
        content_ttft = (
            (first_content_token_time - start_time)
            if first_content_token_time else None
        )
        # TPS：基于 content 生成阶段（首 content → 末 content）
        if first_content_token_time and last_content_token_time:
            generation_time = max(last_content_token_time - first_content_token_time, 0.001)
            actual_output_tokens = output_tokens if output_tokens > 0 else client_token_count
            tps = actual_output_tokens / generation_time
        else:
            # 只有 reasoning 没有 content（max_tokens 不足）
            tps = 0
            actual_output_tokens = output_tokens or reasoning_token_count

        return LatencyResult(
            ttft_seconds=ttft,
            tps=tps,
            total_seconds=total_time,
            output_tokens=actual_output_tokens,
            input_tokens=input_tokens,
            success=True,
            extra={"content_ttft": content_ttft, "reasoning_chunks": reasoning_token_count},
        )

    except Exception as e:
        return LatencyResult(
            ttft_seconds=0,
            tps=0,
            total_seconds=0,
            output_tokens=0,
            input_tokens=0,
            success=False,
            error=f"{type(e).__name__}: {e}",
        )


WARMUP_COUNT = 1  # warm-up 请求数（1 个即可，轻量快速）


def print_ttft_report(results: List[LatencyResult]):
    """TTFT 统计报告"""
    success_results = [r for r in results if r.success]
    failed_count = len(results) - len(success_results)
    if not success_results:
        print("\n❌ 所有请求均失败")
        return
    ttft_values = [r.ttft_seconds for r in success_results]
    print(f"\n{'─'*70}")
    print(f"TTFT 统计  (成功 {len(success_results)}/{len(results)}，失败 {failed_count})")
    print(f"{'─'*70}")
    print(f"  {'指标':<8} {'实测值':>10}  {'验收标准':>12}  {'结果':>4}")
    print(f"  {'─'*50}")
    ttft_targets = [
        ("P50", 50, 4.0,  "< 4s"),
        ("P75", 75, 8.0,  "< 8s"),
        ("P90", 90, 12.0, "< 12s"),
        ("P99", 99, 30.0, "< 30s"),
    ]
    all_pass = True
    for label, pct, target, display in ttft_targets:
        val = percentile(ttft_values, pct)
        passed = val < target
        if not passed:
            all_pass = False
        mark = "✅" if passed else "❌"
        print(f"  {label:<8} {val:>8.2f}s  {display:>12}  {mark}")
    print(f"\n  Min={min(ttft_values):.2f}s  Max={max(ttft_values):.2f}s  "
          f"Mean={statistics.mean(ttft_values):.2f}s  "
          f"Stdev={statistics.stdev(ttft_values) if len(ttft_values) > 1 else 0:.2f}s")
    print(f"\n  → {'✅ TTFT PASS' if all_pass else '❌ TTFT FAIL'}")


def print_tps_report(results: List[LatencyResult]):
    """TPS 统计报告"""
    success_results = [r for r in results if r.success and r.tps > 0]
    failed_count = len(results) - len(success_results)
    if not success_results:
        print("\n❌ 无有效 TPS 数据")
        return
    tps_values = [r.tps for r in success_results]
    print(f"\n{'─'*70}")
    print(f"TPS 统计 (Output Tokens/Second，成功 {len(success_results)}/{len(results)}，失败 {failed_count})")
    print(f"{'─'*70}")
    print(f"  {'指标':<8} {'实测值':>12}  {'验收标准':>14}  {'结果':>4}")
    print(f"  {'─'*50}")
    tps_targets = [
        ("P50", 50, 70.0, "> 70 tok/s"),
        ("P99", 99, 25.0, "> 25 tok/s"),
    ]
    all_pass = True
    for label, pct, target, display in tps_targets:
        val = percentile(tps_values, pct)
        passed = val > target
        if not passed:
            all_pass = False
        mark = "✅" if passed else "❌"
        print(f"  {label:<8} {val:>10.1f} tok/s  {display:>14}  {mark}")
    print(f"\n  Min={min(tps_values):.1f}  Max={max(tps_values):.1f}  "
          f"Mean={statistics.mean(tps_values):.1f}  "
          f"Stdev={statistics.stdev(tps_values) if len(tps_values) > 1 else 0:.1f} tok/s")
    print(f"\n  → {'✅ TPS PASS' if all_pass else '❌ TPS FAIL'}")
    avg_output = statistics.mean([r.output_tokens for r in success_results])
    print(f"\n  平均输出 tokens: {avg_output:.0f}")


async def phase_latency(client: AsyncOpenAI, samples: int, concurrency: int, max_tokens: int):
    """Phase 1: 延迟测试主函数（TTFT + TPS 分离优化）"""
    print(f"\n{'='*70}")
    print(f"Phase 1: 延迟测试 (TTFT + TPS，分离优化)")
    print(f"  样本数: {samples}  |  并发: {concurrency}  |  模型: {MODEL}")
    print(f"  RPM 限制: 500  |  预估 RPM 占用: ~{concurrency * 2} (安全)")
    print(f"{'='*70}")

    # ── Warm-up（1 个轻量请求，排除冷启动）────────────────────
    print(f"\n  ⏳ Warm-up: 1 个轻量预热请求...")
    result = await measure_single_request(
        client, ALL_PROMPTS[0], max_tokens=256,
        early_exit_after_ttft=True, reasoning_effort="high",
    )
    status = f"TTFT={result.ttft_seconds:.2f}s" if result.success else f"✗ {result.error}"
    print(f"    warm-up {status}")
    print(f"  ✓ Warm-up 完成\n")

    prompt_seq = (ALL_PROMPTS * ((samples // len(ALL_PROMPTS)) + 1))[:samples]
    semaphore = asyncio.Semaphore(concurrency)

    # ── 子测试 A: TTFT-only（首 token 后立即取消，超快）──────────
    print(f"{'='*70}")
    print(f"  子测试 A: TTFT 专项 (early_exit + max_tokens=256 + effort=max)")
    print(f"  → 首 token 到达后立即取消，每请求预计 1-5s")
    print(f"{'='*70}")

    async def ttft_request(idx: int, prompt: str) -> LatencyResult:
        async with semaphore:
            r = await measure_single_request(
                client, prompt, max_tokens=256,
                early_exit_after_ttft=True, reasoning_effort="max",
            )
            print(f"  [{idx+1:>3}/{samples}] TTFT={r.ttft_seconds:.2f}s"
                  f"{'  ✓' if r.success else '  ✗ ' + (r.error or '')}")
            return r

    ttft_results = await asyncio.gather(*[ttft_request(i, p) for i, p in enumerate(prompt_seq)])
    print_ttft_report(ttft_results)

    # ── 子测试 B: TPS-only（轻量推理 + 足够生成空间）─────────────
    print(f"\n{'='*70}")
    print(f"  子测试 B: TPS 专项 (effort=high + max_tokens=4096)")
    print(f"  → 推理阶段加速，专注测量生成速率，每请求预计 20-60s")
    print(f"{'='*70}")

    async def tps_request(idx: int, prompt: str) -> LatencyResult:
        async with semaphore:
            r = await measure_single_request(
                client, prompt, max_tokens=4096,
                early_exit_after_ttft=False, reasoning_effort="high",
            )
            status = f"TPS={r.tps:.1f} tok/s  out={r.output_tokens} tok  total={r.total_seconds:.1f}s" if r.success else f"✗ {r.error}"
            print(f"  [{idx+1:>3}/{samples}] {status}")
            return r

    tps_results = await asyncio.gather(*[tps_request(i, p) for i, p in enumerate(prompt_seq)])
    print_tps_report(tps_results)


# ---------------------------------------------------------------------------
# Phase 2: TPM 压测（非流式，全力打满）
# ---------------------------------------------------------------------------

async def phase_tpm(client: AsyncOpenAI, duration: int, concurrency: int, max_tokens: int, reasoning_effort: str = "high"):
    """Phase 2: TPM 压测主函数"""
    print(f"\n{'='*70}")
    print(f"Phase 2: TPM 压测")
    print(f"  持续: {duration}s  |  并发: {concurrency}  |  模型: {MODEL}")
    print(f"  max_tokens: {max_tokens}  |  reasoning_effort: {reasoning_effort}")
    print(f"{'='*70}")

    counters = {
        "success": 0,
        "errors": 0,
        "rate_limited": 0,
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }

    start = time.time()
    end = start + duration

    # 使用固定 coding prompt（模拟稳定负载）
    prompt = (
        "请用 Python 实现一个完整的 HTTP 服务器框架，支持路由注册、中间件、"
        "请求解析、响应序列化、WebSocket 支持。输出完整代码。"
    )

    async def worker():
        """单个 worker：循环发请求直到时间到"""
        while time.time() < end:
            try:
                resp = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {"role": "system", "content": "You are an expert programmer."},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=max_tokens,
                        temperature=1.0,
                        # GLM-5.2 深度思考 + reasoning_effort（可配置深度）
                        extra_body={
                            "thinking": {"type": "enabled"},
                            "reasoning_effort": reasoning_effort,
                        },
                    ),
                    timeout=120,
                )
                if resp.usage:
                    counters["total_tokens"] += resp.usage.total_tokens
                    counters["input_tokens"] += resp.usage.prompt_tokens
                    counters["output_tokens"] += resp.usage.completion_tokens
                counters["success"] += 1
            except asyncio.TimeoutError:
                counters["errors"] += 1
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                    counters["rate_limited"] += 1
                    # 限流后短暂冷却，避免持续浪费请求
                    await asyncio.sleep(2)
                else:
                    counters["errors"] += 1

    async def progress_printer():
        """每 10s 打印进度"""
        while time.time() < end:
            await asyncio.sleep(10)
            elapsed = time.time() - start
            current_tpm = counters["total_tokens"] / elapsed * 60 if elapsed > 0 else 0
            print(
                f"  +{elapsed:>3.0f}s  "
                f"成功={counters['success']:<4}  "
                f"限流={counters['rate_limited']:<3}  "
                f"错误={counters['errors']:<3}  "
                f"窗口TPM≈{current_tpm:>12,.0f}"
            )

    progress_task = asyncio.create_task(progress_printer())
    workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
    await asyncio.gather(*workers, return_exceptions=True)
    progress_task.cancel()
    try:
        await progress_task
    except asyncio.CancelledError:
        pass

    elapsed = time.time() - start
    actual_tpm = counters["total_tokens"] / elapsed * 60 if elapsed > 0 else 0
    estimated_rpm = counters["success"] / elapsed * 60 if elapsed > 0 else 0

    print(f"\n{'─'*70}")
    print(f"TPM 测试结果")
    print(f"{'─'*70}")
    print(f"  实测持续:       {elapsed:.1f}s")
    print(f"  成功请求:       {counters['success']:,}")
    print(f"  限流次数:       {counters['rate_limited']}")
    print(f"  错误次数:       {counters['errors']}")
    print(f"  Token 总量:     {counters['total_tokens']:,} "
          f"(入: {counters['input_tokens']:,}，出: {counters['output_tokens']:,})")
    print(f"  ★ 实测 TPM:    {actual_tpm:,.0f}")
    print(f"  推算 RPM:       {estimated_rpm:,.0f}")

    if counters["rate_limited"] > 0:
        print(f"\n  ⚠️  触发限流 {counters['rate_limited']} 次")
        print(f"     → 实测 TPM 接近该账号的配额上限")
        print(f"     → 若需更高 TPM，考虑申请配额提升或使用多账号路由")
    else:
        print(f"\n  ℹ️  未触发限流，TPM 可能还有余量")
        print(f"     → 可尝试提高 --tpm-concurrency 继续压测")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="GLM-5.2 国际站→北京节点 TTFT/TPS/TPM 性能基准测试"
    )
    parser.add_argument(
        "--phase",
        choices=["latency", "tpm", "all"],
        default="all",
        help="测试阶段：latency（延迟）/ tpm（压测）/ all（两者）",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=500,
        help="延迟测试样本数（默认 500，P99 需至少 500 样本）",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="延迟测试并发数（默认 10，TTFT 提前取消模式下并发可以更高）",
    )
    parser.add_argument(
        "--tpm-concurrency",
        type=int,
        default=30,
        help="TPM 测试并发数（默认 30，RPM=500 下安全）",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="TPM 测试持续秒数（默认 120）",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="TPM 测试单次最大输出 tokens（默认 4096，Phase 1 内部管理无需此参数）",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["high", "max"],
        default="high",
        help="TPM 测试推理深度（默认 high，high 更快且足够压测）",
    )
    args = parser.parse_args()

    if not API_KEY:
        print("❌ 未找到 DASHSCOPE_API_KEY_CN 环境变量")
        print("   请在 .env 中配置：DASHSCOPE_API_KEY_CN=sk-xxx")
        sys.exit(1)

    if not BASE_URL:
        print("❌ 未找到 DASHSCOPE_API_KEY_CN_url 环境变量")
        print("   请在 .env 中配置：DASHSCOPE_API_KEY_CN_url=https://llm-xxx.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"GLM-5.2 国际站→北京节点  性能基准测试")
    print(f"{'='*70}")
    print(f"  Endpoint : {BASE_URL}")
    print(f"  Model    : {MODEL}")
    print(f"  场景     : AI Coding / Agentic Application")
    print(f"  Phase    : {args.phase}")
    print(f"{'='*70}")

    # 显式设置长超时（reasoning_effort=max 下单请求可耗时 5-10 分钟）
    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=httpx.Timeout(900.0, connect=30.0),  # 15 分钟总超时，30s 连接超时
    )

    if args.phase in ("latency", "all"):
        await phase_latency(client, args.samples, args.concurrency, args.max_tokens)

    if args.phase in ("tpm", "all"):
        if args.phase == "all":
            print(f"\n⏳ 延迟测试完成，等待 10s 让请求排空后开始 TPM 压测...")
            await asyncio.sleep(10)
        await phase_tpm(client, args.duration, args.tpm_concurrency, args.max_tokens, args.reasoning_effort)

    print(f"\n{'='*70}")
    print("测试完成")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
