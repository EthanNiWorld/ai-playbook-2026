"""
Qwen3.8-Max · TPM 定向压测（北京节点，长上下文 coding/agent 场景）
====================================================================

对标 SLA（技术规范书·并发性能表）场景 3（32K ≤ 输入 ≤ 64K）：
  平均 TTFT ≤ 3.0s | P99 TTFT ≤ 3.5s | 平均 TPOT ≤ 0.04s | P99 TPOT ≤ 0.05s
  输出速度 ≥ 90 tok/s | 请求成功率 ≥ 99.90% | 缓存命中率 ≥ 90%
  （并发总要求：TPM ≥ 5 亿、RPM ≥ 10000 —— 本次按用户要求压到 3000 万 TPM 探测）

与 glm52_2m_tpm_benchmark.py 同架构：
  - 按时长运行 + 闭环控制并发，把总吞吐锁定在目标 TPM（默认 30,000,000）
  - 场景：单请求输入 ~60000 tok + 输出 ~600 tok，会话内多轮前缀复用 context cache
  - 会话唯一 salt 防止跨会话共享缓存，还原真实命中曲线（round0 miss → round1+ hit）
  - 预热保护 + 温和渐进加并发（规避 Throttling.BurstRate 斜率限流）

运行
  # 烟雾测试（~90s，目标 500K TPM）
  python qwen38_max_tpm_benchmark.py --target-tpm 500000 --duration 60

  # 正式：30M TPM 持续 600s
  python qwen38_max_tpm_benchmark.py --target-tpm 30000000 --duration 600 \
      --output results_qwen38max_30m_tpm.txt

环境变量（来自项目根 .env）
  DASHSCOPE_API_KEY_CN       - 北京节点 API Key（必填）
  DASHSCOPE_API_KEY_CN_url   - 北京节点 endpoint（必填）
  QWEN38MAX_MODEL            - 可覆盖模型名，默认 qwen3.8-max
"""

import os
import sys
import time
import asyncio
import argparse
import random
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(_ENV_PATH)

BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_url")
API_KEY = os.getenv("DASHSCOPE_API_KEY_CN")
MODEL = os.getenv("QWEN38MAX_MODEL", "qwen3.8-max")

# ---------------------------------------------------------------------------
# SLA 阈值（技术规范书并发性能表 · 场景 3：32K ≤ 输入 ≤ 64K）
# ---------------------------------------------------------------------------
SLA = {
    "ttft_avg": 3.0,      # s
    "ttft_p99": 3.5,      # s
    "tpot_avg": 0.04,     # s  (=40ms)
    "tpot_p99": 0.05,     # s  (=50ms)
    "gen_speed": 90.0,    # tok/s
    "success_rate": 99.90,  # %
    "cache_rate": 90.0,   # %
}

SYSTEM_PROMPT = (
    "你是一名资深软件架构师与全栈工程师，正在通过 IM 与开发者进行多轮技术对话。\n"
    "要求：\n"
    "1. 回答直接、专业，优先给出可运行的代码与可落地的方案；\n"
    "2. 涉及代码时遵循生产级标准：类型标注、错误处理、日志、并发安全；\n"
    "3. 多轮对话中记住上下文，后续回答必须与前面结论保持一致；\n"
    "4. 每次回复控制在 300 字以内（代码除外），不要重复前文已说过的内容。"
)

FOLLOWUP_QUESTIONS = [
    "这个方案在高并发场景下有什么潜在问题？请详细分析。",
    "帮我为上面的代码补充完整的单元测试。",
    "能进一步优化性能吗？给出优化后的完整代码。",
    "如果要支持分布式部署，需要做哪些改造？",
    "请解释一下核心实现原理，越详细越好。",
    "有没有更优雅的替代方案？对比一下优缺点。",
    "帮我加上完善的错误处理和结构化日志。",
    "写一个使用示例，覆盖主要边界情况。",
    "如何监控这个组件的运行状态？给出埋点与告警方案。",
    "如果数据量增长 100 倍，架构需要怎么调整？",
    "帮我做一次代码审查，指出潜在 bug 和安全风险。",
    "总结一下这次讨论的要点和后续行动项。",
]

# ---------------------------------------------------------------------------
# 长上下文构造：合成 ~60K token 的 coding/agent 仓库上下文
# ---------------------------------------------------------------------------
_CODE_BLOCK = '''\
# ============================================================
# File: services/{pkg}/handler_{idx}.py
# ------------------------------------------------------------
"""模块 {idx}：{pkg} 域的请求处理器，负责校验、编排与持久化。"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger("{pkg}.handler_{idx}")


@dataclass
class Ctx_{idx}:
    request_id: str
    tenant: str
    payload: Dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    deadline_ms: int = 3000


class Repo_{idx}:
    """{pkg} 的数据访问层，封装连接池与重试。"""

    def __init__(self, pool_size: int = {pool}) -> None:
        self._pool_size = pool_size
        self._sem = asyncio.Semaphore(pool_size)
        self._cache: Dict[str, Any] = {{}}

    async def get(self, key: str) -> Optional[Any]:
        async with self._sem:
            if key in self._cache:
                return self._cache[key]
            await asyncio.sleep(0)  # 模拟 IO
            return None

    async def put(self, key: str, val: Any) -> None:
        async with self._sem:
            self._cache[key] = val


async def handle_{idx}(ctx: Ctx_{idx}, repo: Repo_{idx}) -> Dict[str, Any]:
    """核心编排：校验 -> 读缓存 -> 计算 -> 落库。已知在高并发下偶发超时。"""
    if not ctx.tenant:
        raise ValueError("tenant required")
    cached = await repo.get(ctx.request_id)
    if cached is not None:
        return {{"status": "hit", "data": cached}}
    result = {{"status": "ok", "score": {idx} * 7 % 101, "items": list(range({items}))}}
    await repo.put(ctx.request_id, result)
    logger.info("handled req=%s tenant=%s", ctx.request_id, ctx.tenant)
    return result
'''

_PKGS = ["order", "inventory", "billing", "auth", "search", "notify", "gateway", "audit"]


def build_context(target_tokens: int, salt: str = "", chars_per_token: float = 3.6) -> str:
    """按字符启发式生成接近 target_tokens 的代码上下文（实际 token 数由 API 标定校正）。
    salt 使每个会话的前缀唯一（顶部 build-tag + 内容起点偏移），
    防止跨会话共享缓存，只保留会话内前缀复用（还原真实命中曲线）。"""
    target_chars = int(target_tokens * chars_per_token)
    head = f"// build-tag: {salt}\n" if salt else ""
    parts: List[str] = [
        head + "以下是我们线上微服务系统的核心代码库快照（多文件）。请通读并作为后续所有问题的上下文：\n\n"
    ]
    idx = (abs(hash(salt)) % 997) if salt else 0   # 每会话内容起点不同，增加差异
    total = len(parts[0])
    while total < target_chars:
        block = _CODE_BLOCK.format(
            pkg=_PKGS[idx % len(_PKGS)],
            idx=idx,
            pool=8 + idx % 20,
            items=16 + idx % 48,
        )
        parts.append(block)
        total += len(block)
        idx += 1
    return "".join(parts)


OPENING_TASKS = [
    "问题：请通读上述代码库，指出 handle_* 系列在高并发下导致偶发超时与任务丢失的所有根因，并给出修复后的关键实现。",
    "问题：以上述代码库为基础，设计一套统一的重试+熔断+超时治理方案，给出可落地的核心代码与配置。",
    "问题：请对上述代码库做一次架构级 code review，按严重程度列出并发安全、资源泄漏、可观测性缺陷，并给出改进代码。",
    "问题：上述系统在大促时出现雪崩，请从连接池、信号量、缓存一致性角度定位瓶颈，并给出优化后的实现。",
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class TurnResult:
    session_id: int
    turn_index: int
    success: bool
    ttft: float = 0.0                       # 首 token 延迟（s）
    latency: float = 0.0                    # 端到端延迟（s）
    gen_time: float = 0.0                   # 首 token → 末 token 生成耗时（s）
    tps: float = 0.0                        # 生成速率（tok/s，单请求口径）
    tpot_ms: float = 0.0                    # 每输出 token 平均耗时（ms）
    prompt_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    content: str = ""
    error: Optional[str] = None
    err_kind: str = ""                      # 429 / throttle / timeout / other / ""


def classify_error(e: Exception) -> str:
    name = type(e).__name__
    text = str(e)
    if "429" in text or "Throttling" in text or name == "RateLimitError":
        if "burst" in text.lower() or "Throttling.BurstRate" in text:
            return "throttle-burst"
        return "throttle-429"
    if "timeout" in text.lower() or name in ("APITimeoutError", "ReadTimeout", "ConnectTimeout"):
        return "timeout"
    if "400" in text or "BadRequest" in name:
        return "badrequest"
    return "other"


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sd = sorted(data)
    n = len(sd)
    if n == 1:
        return sd[0]
    k = (n - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < n else f
    d = k - f
    return sd[f] + d * (sd[c] - sd[f])


# ---------------------------------------------------------------------------
# 单轮请求：流式逐 chunk 精确计时
# ---------------------------------------------------------------------------
async def measure_turn(
    client: AsyncOpenAI,
    session_id: int,
    turn_index: int,
    messages: List[Dict[str, str]],
    max_tokens: int,
    enable_thinking: bool,
) -> TurnResult:
    kwargs = dict(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=1.0,
        stream=True,
        stream_options={"include_usage": True},
        extra_body={"enable_thinking": enable_thinking},
    )

    try:
        start = time.perf_counter()
        first_token_time: Optional[float] = None
        last_token_time: Optional[float] = None
        prompt_tokens = output_tokens = cached_tokens = 0
        chunk_count = 0
        content_parts: List[str] = []

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            now = time.perf_counter()

            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0
                details = getattr(chunk.usage, "prompt_tokens_details", None)
                if details is not None:
                    cached_tokens = getattr(details, "cached_tokens", 0) or 0

            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # thinking 模式下 reasoning_content 先到，同样计入 TTFT（首任意 token 口径）
            reasoning = getattr(delta, "reasoning_content", None)
            content = delta.content
            if reasoning or content:
                if first_token_time is None:
                    first_token_time = now
                last_token_time = now
                chunk_count += 1
                if content:
                    content_parts.append(content)

        if first_token_time is None or last_token_time is None:
            return TurnResult(
                session_id=session_id, turn_index=turn_index, success=False,
                error=f"no tokens received (output_tokens={output_tokens})",
                err_kind="other",
            )

        ttft = first_token_time - start
        latency = last_token_time - start
        gen_time = max(last_token_time - first_token_time, 1e-6)
        n_out = output_tokens if output_tokens > 0 else chunk_count
        tps = n_out / gen_time
        tpot_ms = gen_time / max(n_out - 1, 1) * 1000

        return TurnResult(
            session_id=session_id, turn_index=turn_index, success=True,
            ttft=ttft, latency=latency, gen_time=gen_time,
            tps=tps, tpot_ms=tpot_ms,
            prompt_tokens=prompt_tokens, output_tokens=n_out,
            cached_tokens=cached_tokens,
            content="".join(content_parts),
        )

    except Exception as e:
        return TurnResult(
            session_id=session_id, turn_index=turn_index, success=False,
            error=f"{type(e).__name__}: {e}",
            err_kind=classify_error(e),
        )


# ---------------------------------------------------------------------------
# 吞吐度量（滑动窗口）：TPM 与 RPM
# ---------------------------------------------------------------------------
class Throughput:
    def __init__(self, window: float = 30.0):
        self.window = window
        self.tok_events: deque = deque()    # (t, tokens)
        self.req_events: deque = deque()     # (t, 1)
        self.t0 = time.perf_counter()
        self.peak_tpm = 0.0
        self.peak_rpm = 0.0

    def record(self, tokens: int, ok: bool):
        now = time.perf_counter()
        self.tok_events.append((now, tokens))
        self.req_events.append((now, 1))

    def _trim(self, now: float):
        while self.tok_events and now - self.tok_events[0][0] > self.window:
            self.tok_events.popleft()
        while self.req_events and now - self.req_events[0][0] > self.window:
            self.req_events.popleft()

    def tpm(self) -> float:
        now = time.perf_counter()
        self._trim(now)
        tok = sum(t for _, t in self.tok_events)
        span = min(self.window, max(now - self.t0, 1e-6))
        v = tok / span * 60.0
        self.peak_tpm = max(self.peak_tpm, v)
        return v

    def rpm(self) -> float:
        now = time.perf_counter()
        self._trim(now)
        n = len(self.req_events)
        span = min(self.window, max(now - self.t0, 1e-6))
        v = n / span * 60.0
        self.peak_rpm = max(self.peak_rpm, v)
        return v


def geometric_turns(max_turns: int, p: float = 0.82) -> int:
    """几何衰减的会话轮数（复现 per-round 递减分布）。"""
    turns = 1
    while turns < max_turns and random.random() < p:
        turns += 1
    return turns


# ---------------------------------------------------------------------------
# 单会话：巨型开场 + 短追问，多轮累积复用长前缀
# ---------------------------------------------------------------------------
async def run_session(
    client: AsyncOpenAI,
    sid: int,
    cpt: float,
    tp: Throughput,
    args: argparse.Namespace,
    start: float,
) -> List[TurnResult]:
    turns_planned = geometric_turns(args.max_turns, p=args.turn_p)
    # 每个会话唯一上下文（salt=sid）：跨会话不共享缓存，仅会话内前缀复用
    context = build_context(args.input_tokens, salt=f"S{sid}", chars_per_token=cpt)
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    results: List[TurnResult] = []

    for turn in range(turns_planned):
        if time.perf_counter() - start >= args.duration:
            break
        if turn == 0:
            task = random.choice(OPENING_TASKS)
            user_msg = (
                context + "\n\n" + task
                + "\n\n请给出详细、完整、可运行的分析与代码，篇幅约 600 tokens。"
            )
        else:
            user_msg = random.choice(FOLLOWUP_QUESTIONS) + "（请详细回答，约 600 tokens）"
        messages.append({"role": "user", "content": user_msg})

        r = await measure_turn(
            client, sid, turn, messages,
            args.out_max_tokens, args.enable_thinking,
        )
        results.append(r)
        if not r.success:
            break
        tp.record(r.prompt_tokens + r.output_tokens, True)
        messages.append({"role": "assistant", "content": r.content})

    return results


# ---------------------------------------------------------------------------
# 闭环驱动：按时长运行，动态调并发把 TPM 锁定在目标（温和渐进，规避 BurstRate）
# ---------------------------------------------------------------------------
async def drive(client: AsyncOpenAI, cpt: float, args: argparse.Namespace,
                init_conc: int) -> tuple:
    tp = Throughput(window=args.window)
    results: List[TurnResult] = []
    active: set = set()
    start = time.perf_counter()
    sid = 0
    target_conc = max(1, init_conc)
    ceil_conc = args.max_concurrency
    last_adjust = start
    last_print = start
    target_tpm = args.target_tpm

    while (time.perf_counter() - start < args.duration) or active:
        now = time.perf_counter()
        within = now - start < args.duration

        # 分波补齐并发（波间留 ~2s，压平负载斜率；波幅由 --spawn-batch 控制）
        if within and len(active) < target_conc:
            batch = min(args.spawn_batch, target_conc - len(active))
            for _ in range(batch):
                t = asyncio.create_task(run_session(client, sid, cpt, tp, args, start))
                active.add(t)
                sid += 1

        if not active:
            break

        done, active = await asyncio.wait(
            active, timeout=2.0, return_when=asyncio.FIRST_COMPLETED
        )
        for d in done:
            try:
                results.extend(d.result())
            except Exception as e:
                print(f"  [session error] {e}", flush=True)

        # 闭环调节并发：必须等管道预热（已过一个窗口且有足够完成）后再调，
        # 否则初期完成数为 0 → TPM 误读为 0 → 狂加并发 → 暴冲 429
        warmed = (now - start >= args.window) and (len(results) >= init_conc)
        if within and warmed and now - last_adjust >= args.adjust_interval:
            cur = tp.tpm()
            if cur < target_tpm * 0.90:
                # 温和渐进：步长随缺口放大但封顶，避免触发 BurstRate 斜率限流
                step = min(args.max_step, max(2, int(target_conc * 0.12) + 2))
                target_conc = min(ceil_conc, target_conc + step)
            elif cur > target_tpm * 1.10:
                target_conc = max(1, target_conc - max(2, target_conc // 10))
            last_adjust = now

        # 进度
        if now - last_print >= 10:
            elapsed = now - start
            phase = "warmup" if not warmed else "steady"
            err429 = sum(1 for r in results if not r.success)
            print(
                f"  [t={elapsed:5.0f}s|{phase:<6}] TPM={tp.tpm():>12,.0f}  "
                f"RPM={tp.rpm():>7,.0f}  target={target_tpm:,}  "
                f"conc={len(active)}/{target_conc}(max{ceil_conc})  "
                f"turns={len(results)} fail={err429}",
                flush=True,
            )
            last_print = now

    duration = time.perf_counter() - start
    return results, duration, tp


# ---------------------------------------------------------------------------
# 标定：发 1 个请求，把上下文精确校正到 ~target 输入 tokens，并估算初始并发
# ---------------------------------------------------------------------------
async def calibrate(client: AsyncOpenAI, args: argparse.Namespace):
    print(f"\n⏳ 标定上下文长度（目标输入 ~{args.input_tokens:,} tok）...")
    context = build_context(args.input_tokens)
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context + "\n\n" + OPENING_TASKS[0]
         + "\n\n请给出详细、完整的分析与代码，篇幅约 600 tokens。"},
    ]
    t0 = time.perf_counter()
    r = await measure_turn(client, -1, 0, msgs, args.out_max_tokens,
                           args.enable_thinking)
    lat = time.perf_counter() - t0
    if not r.success:
        print(f"  ❌ 标定请求失败: {r.error}")
        sys.exit(1)

    print(f"  实测: prompt={r.prompt_tokens:,} tok  output={r.output_tokens} tok  "
          f"latency={lat:.1f}s  ttft={r.ttft:.2f}s  tps={r.tps:.1f} tok/s  cached={r.cached_tokens}")

    # 校正每 token 字符数（供会话重建唯一上下文时使用）
    cpt = len(context) / max(r.prompt_tokens, 1)
    if abs(r.prompt_tokens - args.input_tokens) / args.input_tokens > 0.08:
        print(f"  校正: 按 {cpt:.2f} chars/tok（原偏差 {(r.prompt_tokens - args.input_tokens):+,} tok，会话将按此重建）")

    # 初始并发估算：conc = target_tps * latency / tokens_per_req（Little's law）
    target_tps = args.target_tpm / 60.0
    tokens_per_req = r.prompt_tokens + r.output_tokens
    init_conc = max(2, round(target_tps * lat / max(tokens_per_req, 1)))
    init_conc = min(init_conc, args.max_concurrency)
    print(f"  初始并发估算: {init_conc}（target_tps={target_tps:.0f}, "
          f"tokens/req≈{tokens_per_req:,}, lat≈{lat:.1f}s）")
    return cpt, init_conc


# ---------------------------------------------------------------------------
# 报告生成（ASCII 表格，含 SLA 场景 3 对标）
# ---------------------------------------------------------------------------
TABLE_W = 68


def build_report(results: List[TurnResult], duration: float, tp: Throughput,
                 args: argparse.Namespace) -> str:
    lines: List[str] = []
    A = lines.append

    def hline():
        A("+" + "-" * TABLE_W + "+")

    def title(t: str):
        A("| " + t.ljust(TABLE_W - 2) + " |")

    def kv(label: str, value: str, indent: int = 2):
        dots = TABLE_W + 1 - indent - len(label) - 1 - len(value) - 2
        A("|" + " " * indent + label + "." * max(dots, 2) + " " + value + "  |")

    def stat_section(name: str, values: List[float], unit: str, fmt="{:.2f}"):
        hline()
        title(name)
        hline()
        rows = [("avg", statistics.mean(values))]
        for p in (50, 90, 95, 99):
            rows.append((f"p{p}", percentile(values, p)))
        for label, v in rows:
            kv(label, f"{fmt.format(v)} {unit}", indent=4)

    ok = [r for r in results if r.success]
    failed = len(results) - len(ok)
    if not ok:
        return "ALL REQUESTS FAILED"

    ttfts = [r.ttft for r in ok]
    tpots = [r.tpot_ms for r in ok]
    tpss = [r.tps for r in ok if r.tps > 0]
    total_prompt = sum(r.prompt_tokens for r in ok)
    total_output = sum(r.output_tokens for r in ok)
    total_cached = sum(r.cached_tokens for r in ok)
    cache_rate = total_cached / total_prompt * 100 if total_prompt > 0 else 0.0
    success_rate = len(ok) / len(results) * 100 if results else 0.0
    # 聚合口径生成速度：总输出 token / 总生成阶段耗时
    gen_speed_agg = total_output / sum(r.gen_time for r in ok) if ok else 0.0

    # steady 口径：剔除 round0（冷 prefill、缓存必 miss 的首轮）
    ok_steady = [r for r in ok if r.turn_index >= 1]
    failed_steady = sum(1 for r in results if not r.success and r.turn_index >= 1)
    if ok_steady:
        ttfts_s = [r.ttft for r in ok_steady]
        tpots_s = [r.tpot_ms for r in ok_steady]
        tpss_s = [r.tps for r in ok_steady if r.tps > 0]
        prompt_s = sum(r.prompt_tokens for r in ok_steady)
        output_s = sum(r.output_tokens for r in ok_steady)
        cached_s = sum(r.cached_tokens for r in ok_steady)
        cache_rate_s = cached_s / prompt_s * 100 if prompt_s > 0 else 0.0
        success_rate_s = len(ok_steady) / (len(ok_steady) + failed_steady) * 100
        gen_speed_s = output_s / sum(r.gen_time for r in ok_steady)
    else:
        ttfts_s = tpots_s = tpss_s = []
        cache_rate_s = success_rate_s = gen_speed_s = 0.0

    # ---- BENCHMARK RESULTS ----
    hline()
    title("BENCHMARK RESULTS · Qwen3.8-Max Beijing")
    hline()
    kv("Model", MODEL)
    kv("Target TPM", f"{args.target_tpm:,}")
    kv("Peak TPM (30s win)", f"{tp.peak_tpm:,.0f}")
    kv("End TPM (30s win)", f"{tp.tpm():,.0f}")
    kv("Peak RPM (30s win)", f"{tp.peak_rpm:,.0f}")
    kv("Total turns", f"{len(results)}")
    kv("Success turns", f"{len(ok)}")
    kv("Failed turns", f"{failed}")
    kv("Duration", f"{duration:.1f} s")
    kv("Avg prompt length", f"{statistics.mean([r.prompt_tokens for r in ok]):.0f} tok")
    kv("Avg output length", f"{statistics.mean([r.output_tokens for r in ok]):.0f} tok")

    # ---- THROUGHPUT ----
    hline()
    title("THROUGHPUT")
    hline()
    kv("Request rate", f"{len(results) / duration:.2f} req/s")
    kv("Input tokens", f"{total_prompt / duration:,.0f} tok/s")
    kv("Output tokens", f"{total_output / duration:,.0f} tok/s")
    kv("Total tokens", f"{(total_prompt + total_output) / duration * 60:,.0f} TPM (avg)")

    # ---- 延迟与生成指标（OVERALL：含 round0）----
    stat_section("TTFT (s) · overall", ttfts, "s")
    stat_section("TPOT (ms/tok) · overall", tpots, "ms")
    if tpss:
        stat_section("TPS (tok/s) · overall", tpss, "tok/s", fmt="{:.1f}")
        kv("Gen speed (aggregate)", f"{gen_speed_agg:.1f} tok/s", indent=4)
    kv("Cache hit rate", f"{cache_rate:.2f}%", indent=4)

    # ---- 延迟与生成指标（STEADY：剔除 round0）----
    if ok_steady:
        hline()
        title("STEADY · round≥1（剔除 round0 冷 prefill / 冷 miss）")
        hline()
        stat_section("TTFT (s) · steady", ttfts_s, "s")
        stat_section("TPOT (ms/tok) · steady", tpots_s, "ms")
        if tpss_s:
            stat_section("TPS (tok/s) · steady", tpss_s, "tok/s", fmt="{:.1f}")
            kv("Gen speed (aggregate)", f"{gen_speed_s:.1f} tok/s", indent=4)
        kv("Cache hit rate", f"{cache_rate_s:.2f}%", indent=4)
        kv("Success rate (round≥1)", f"{success_rate_s:.2f}%", indent=4)

    # ---- PER-ROUND BREAKDOWN ----
    rounds: Dict[int, List[TurnResult]] = {}
    for r in ok:
        rounds.setdefault(r.turn_index, []).append(r)

    hline()
    title("PER-ROUND BREAKDOWN")
    hline()
    header = "|  Round   Reqs    TTFT avg     Lat avg     Cache"
    A(header.ljust(TABLE_W + 1) + "|")
    A("|  " + "-" * (TABLE_W - 4) + "  |")
    for turn_idx in sorted(rounds.keys()):
        rs = rounds[turn_idx]
        n = len(rs)
        ttft_avg = statistics.mean([r.ttft for r in rs])
        lat_avg = statistics.mean([r.latency for r in rs])
        r_prompt = sum(r.prompt_tokens for r in rs)
        r_cached = sum(r.cached_tokens for r in rs)
        r_cache = r_cached / r_prompt * 100 if r_prompt > 0 else 0.0
        row = (
            f"|  {turn_idx:>5}  {n:>6}  "
            f"{ttft_avg:>7.2f} s  {lat_avg:>8.2f} s  {r_cache:>6.2f}%"
        )
        A(row.ljust(TABLE_W + 1) + "|")

    # ---- SLA VERIFICATION（场景 3 · steady 口径：剔除 round0）----
    hline()
    title("SLA VERIFICATION（场景3 · steady，剔除 round0）")
    hline()
    _ttfts = ttfts_s or ttfts
    _tpots = tpots_s or tpots
    _gen = gen_speed_s or gen_speed_agg
    _succ = success_rate_s or success_rate
    _cache = cache_rate_s or cache_rate
    checks = [
        ("平均 TTFT ≤ 3.0s", statistics.mean(_ttfts), SLA["ttft_avg"], "<", "s"),
        ("P99 TTFT ≤ 3.5s", percentile(_ttfts, 99), SLA["ttft_p99"], "<", "s"),
        ("平均 TPOT ≤ 40ms", statistics.mean(_tpots), SLA["tpot_avg"] * 1000.0, "<", "ms"),
        ("P99 TPOT ≤ 50ms", percentile(_tpots, 99), SLA["tpot_p99"] * 1000.0, "<", "ms"),
        ("输出速度 ≥ 90 tok/s（聚合）", _gen, SLA["gen_speed"], ">", "tok/s"),
        ("成功率 ≥ 99.90%", _succ, SLA["success_rate"], ">", "%"),
        ("缓存命中率 ≥ 90%", _cache, SLA["cache_rate"], ">", "%"),
    ]
    all_pass = True
    for label, actual, target, op, unit in checks:
        passed = actual < target if op == "<" else actual > target
        if not passed:
            all_pass = False
        mark = "PASS" if passed else "FAIL"
        if unit == "%":
            val = f"{actual:.2f}%  {mark}"
        elif unit == "tok/s":
            val = f"{actual:.1f} tok/s  {mark}"
        elif unit == "ms":
            val = f"{actual:.2f} ms  {mark}"
        else:
            val = f"{actual:.2f} s  {mark}"
        kv(label, val)
    hline()
    kv("OVERALL (场景3 SLA · steady)", "PASS" if all_pass else "FAIL")
    hline()

    # ---- 失败原因分布 ----
    if failed:
        A("")
        A("失败原因分布:")
        kinds: Dict[str, int] = {}
        for r in results:
            if not r.success:
                key = r.err_kind or (r.error or "?").split(":")[0][:40]
                kinds[key] = kinds.get(key, 0) + 1
        for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
            A(f"  {v:>5}  {k}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(
        description="Qwen3.8-Max 北京节点 30M TPM 定向压测（长上下文 coding/agent）")
    parser.add_argument("--target-tpm", type=int, default=30_000_000,
                        help="目标 TPM（默认 30,000,000）")
    parser.add_argument("--duration", type=float, default=600.0,
                        help="压测时长秒（默认 600）")
    parser.add_argument("--input-tokens", type=int, default=60000,
                        help="单请求目标输入 tokens（默认 60000，对应 SLA 场景3）")
    parser.add_argument("--out-max-tokens", type=int, default=800,
                        help="单轮最大输出 tokens（默认 800，目标 avg~600）")
    parser.add_argument("--max-turns", type=int, default=8,
                        help="单会话最大轮数（默认 8，几何衰减）")
    parser.add_argument("--turn-p", type=float, default=0.82,
                        help="几何衰减继续轮概率（默认 0.82，调高可降低 round0 占比）")
    parser.add_argument("--max-concurrency", type=int, default=400,
                        help="并发上限（默认 400）")
    parser.add_argument("--max-step", type=int, default=8,
                        help="单波最大加并发数（默认 8，规避 BurstRate）")
    parser.add_argument("--spawn-batch", type=int, default=8,
                        help="单波最大补齐会话数（默认 8，高并发档可调大加速爬坡）")
    parser.add_argument("--window", type=float, default=30.0,
                        help="TPM 滑动窗口秒（默认 30）")
    parser.add_argument("--adjust-interval", type=float, default=5.0,
                        help="并发调节间隔秒（默认 5）")
    parser.add_argument("--enable-thinking", action="store_true",
                        help="开启思考模式（默认关闭，保证输出 ~600 tok 口径）")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=None, help="报告保存路径")
    args = parser.parse_args()

    if not API_KEY or not BASE_URL:
        print("❌ 缺少 DASHSCOPE_API_KEY_CN / DASHSCOPE_API_KEY_CN_url")
        sys.exit(1)

    random.seed(args.seed)

    print(f"\n{'=' * 70}")
    print("Qwen3.8-Max · TPM 定向压测（北京节点 · coding/agent 长上下文）")
    print(f"{'=' * 70}")
    print(f"  Endpoint    : {BASE_URL}")
    print(f"  Model       : {MODEL}")
    print(f"  Target TPM  : {args.target_tpm:,}")
    print(f"  Duration    : {args.duration:.0f} s")
    print(f"  Per-req     : input ~{args.input_tokens:,} tok / output ~600 tok")
    print(f"  Thinking    : {'on' if args.enable_thinking else 'off'}")
    print(f"  SLA(场景3)  : avgTTFT≤3.0s p99TTFT≤3.5s avgTPOT≤40ms p99TPOT≤50ms")
    print(f"                gen≥90tok/s success≥99.90% cache≥90%")
    print(f"{'=' * 70}")

    # 高连接池上限，避免客户端 100 连接默认值成为瓶颈（随并发上限扩容）
    _conn_cap = max(2000, args.max_concurrency * 4)
    http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=_conn_cap,
                            max_keepalive_connections=_conn_cap // 2),
        timeout=httpx.Timeout(600.0, connect=30.0),
    )
    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        http_client=http_client,
        max_retries=0,
    )

    cpt, init_conc = await calibrate(client, args)

    print(f"\n🚀 开始闭环压测：锁定 {args.target_tpm:,} TPM，持续 {args.duration:.0f}s\n")
    results, duration, tp = await drive(client, cpt, args, init_conc)

    ok = sum(1 for r in results if r.success)
    print(f"\n✅ 压测结束：成功 {ok}/{len(results)} 轮，实际耗时 {duration:.1f}s")
    print(f"   峰值 TPM={tp.peak_tpm:,.0f}  峰值 RPM={tp.peak_rpm:,.0f}\n")

    report = build_report(results, duration, tp, args)
    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"# Qwen3.8-Max {args.target_tpm:,} TPM 压测 · {MODEL} · 北京节点\n")
            f.write(f"# target={args.target_tpm:,} duration={args.duration:.0f}s "
                    f"input~{args.input_tokens:,}tok thinking={'on' if args.enable_thinking else 'off'}\n")
            f.write(report + "\n")
        print(f"\n📄 报告已保存: {args.output}")

    await http_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[中断] 用户取消")
