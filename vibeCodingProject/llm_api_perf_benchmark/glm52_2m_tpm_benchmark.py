"""
GLM-5.2 · 2M TPM 定向压测（coding/agent 长上下文场景）
================================================================

与 glm52_multiturn_benchmark.py 的区别
  - 该脚本是「按时长运行 + 闭环控制并发」，把总吞吐锁定在目标 TPM（默认 2,000,000）
  - 场景：coding/agent，单请求输入 ~60000 tok（大代码库/仓库上下文）+ 输出 ~600 tok
  - 会话内多轮，长上下文前缀被 context cache 逐轮复用（per-round 命中率递增）
  - 复用现有 measure_turn / build_report / 表格格式，保证输出风格一致

闭环控制
  - 每隔数秒测量滑动窗口内的实际 TPM（usage 口径：prompt_tokens + completion_tokens）
  - 低于目标则加并发，高于目标则减并发，收敛到目标 TPM
  - 若 workspace 限额低于目标，TPM 会在上限附近平台化（可据此判断真实承载）

运行
  # 烟雾测试（~40s）
  python glm52_2m_tpm_benchmark.py --duration 40

  # 正式：2M TPM 持续 768s
  python glm52_2m_tpm_benchmark.py --target-tpm 2000000 --duration 768

环境变量（复用 glm52_multiturn_benchmark 的加载逻辑，来自项目根 .env）
  DASHSCOPE_API_KEY_CN / DASHSCOPE_API_KEY_CN_url / GLM52_MODEL
"""

import os
import sys
import time
import asyncio
import argparse
import random
from collections import deque
from types import SimpleNamespace
from typing import List, Dict, Set

import httpx
from openai import AsyncOpenAI

# 复用主压测脚本的测量、报表与内容库
from glm52_multiturn_benchmark import (
    measure_turn,
    build_report,
    TurnResult,
    SYSTEM_PROMPT,
    FOLLOWUP_QUESTIONS,
    MODEL,
    API_KEY,
    BASE_URL,
)


# ---------------------------------------------------------------------------
# 长上下文构造：合成一个 ~60K token 的 coding/agent 仓库上下文
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
# 吞吐度量（滑动窗口）
# ---------------------------------------------------------------------------
class Throughput:
    def __init__(self, window: float = 30.0):
        self.window = window
        self.events: deque = deque()   # (t, tokens)
        self.t0 = time.perf_counter()

    def record(self, tokens: int):
        self.events.append((time.perf_counter(), tokens))

    def tpm(self) -> float:
        now = time.perf_counter()
        while self.events and now - self.events[0][0] > self.window:
            self.events.popleft()
        tok = sum(t for _, t in self.events)
        span = min(self.window, max(now - self.t0, 1e-6))
        return tok / span * 60.0


def geometric_turns(max_turns: int, p: float = 0.82) -> int:
    """几何衰减的会话轮数（复现参考里的 per-round 递减分布）。"""
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
    max_turns = args.max_turns
    turns_planned = geometric_turns(max_turns)
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
                context
                + "\n\n" + task
                + "\n\n请给出详细、完整、可运行的分析与代码，篇幅约 600 tokens。"
            )
        else:
            user_msg = random.choice(FOLLOWUP_QUESTIONS) + "（请详细回答，约 600 tokens）"
        messages.append({"role": "user", "content": user_msg})

        r = await measure_turn(
            client, sid, turn, messages,
            args.out_max_tokens, args.enable_thinking, args.reasoning_effort,
        )
        results.append(r)
        if not r.success:
            break
        tp.record(r.prompt_tokens + r.output_tokens)
        messages.append({"role": "assistant", "content": r.content})

    return results


# ---------------------------------------------------------------------------
# 闭环驱动：按时长运行，动态调并发把 TPM 锁定在目标
# ---------------------------------------------------------------------------
async def drive(client: AsyncOpenAI, cpt: float, args: argparse.Namespace,
                init_conc: int) -> tuple:
    tp = Throughput(window=args.window)
    results: List[TurnResult] = []
    active: Set[asyncio.Task] = set()
    start = time.perf_counter()
    sid = 0
    target_conc = max(1, init_conc)
    # 安全上限：以标定值为基准适度放宽，防止暴冲到 429
    ceil_conc = min(args.max_concurrency, max(init_conc * 2, init_conc + 8))
    last_adjust = start
    last_print = start
    target_tpm = args.target_tpm

    while (time.perf_counter() - start < args.duration) or active:
        now = time.perf_counter()
        within = now - start < args.duration

        # 补齐并发
        while within and len(active) < target_conc:
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
        # 否则初期完成数为 0 → TPM误读为0 → 狂加并发→暴冲
        warmed = (now - start >= args.window) and (len(results) >= init_conc)
        if within and warmed and now - last_adjust >= args.adjust_interval:
            cur = tp.tpm()
            if cur < target_tpm * 0.90:
                target_conc = min(ceil_conc, target_conc + 1)
            elif cur > target_tpm * 1.10:
                target_conc = max(1, target_conc - 1)
            last_adjust = now

        # 进度
        if now - last_print >= 10:
            elapsed = now - start
            phase = "warmup" if not ((now - start >= args.window) and (len(results) >= init_conc)) else "steady"
            print(
                f"  [t={elapsed:5.0f}s|{phase:<6}] TPM={tp.tpm():>10,.0f}  target={target_tpm:,}  "
                f"conc={len(active)}/{target_conc}(max{ceil_conc})  reqs={len(results)}",
                flush=True,
            )
            last_print = now

    duration = time.perf_counter() - start
    return results, duration


# ---------------------------------------------------------------------------
# 标定：发 1~2 个请求，把上下文精确校正到 ~target 输入 tokens，并估算初始并发
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
                           args.enable_thinking, args.reasoning_effort)
    lat = time.perf_counter() - t0
    if not r.success:
        print(f"  ❌ 标定请求失败: {r.error}")
        sys.exit(1)

    print(f"  实测: prompt={r.prompt_tokens:,} tok  output={r.output_tokens} tok  "
          f"latency={lat:.1f}s  cached={r.cached_tokens}")

    # 校正每 token 字符数（供会话重建唯一上下文时使用）
    cpt = len(context) / max(r.prompt_tokens, 1)
    if abs(r.prompt_tokens - args.input_tokens) / args.input_tokens > 0.08:
        print(f"  校正: 按 {cpt:.2f} chars/tok（原偏差 {(r.prompt_tokens-args.input_tokens):+,} tok，会话将按此重建）")

    # 初始并发估算：conc = target_tps * latency / tokens_per_req（Little's law）
    target_tps = args.target_tpm / 60.0
    tokens_per_req = r.prompt_tokens + r.output_tokens
    init_conc = max(2, round(target_tps * lat / max(tokens_per_req, 1)))
    init_conc = min(init_conc, args.max_concurrency)
    print(f"  初始并发估算: {init_conc}（target_tps={target_tps:.0f}, "
          f"tokens/req≈{tokens_per_req:,}, lat≈{lat:.1f}s）")
    return cpt, init_conc


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(description="GLM-5.2 2M TPM 定向压测（长上下文 coding/agent）")
    parser.add_argument("--target-tpm", type=int, default=2_000_000, help="目标 TPM（默认 2,000,000）")
    parser.add_argument("--duration", type=float, default=768.0, help="压测时长秒（默认 768）")
    parser.add_argument("--input-tokens", type=int, default=60000, help="单请求目标输入 tokens（默认 60000）")
    parser.add_argument("--out-max-tokens", type=int, default=800, help="单轮最大输出 tokens（默认 800，目标 avg~600）")
    parser.add_argument("--max-turns", type=int, default=8, help="单会话最大轮数（默认 8，几何衰减）")
    parser.add_argument("--max-concurrency", type=int, default=80, help="并发上限（默认 80）")
    parser.add_argument("--window", type=float, default=30.0, help="TPM 滑动窗口秒（默认 30）")
    parser.add_argument("--adjust-interval", type=float, default=6.0, help="并发调节间隔秒（默认 6）")
    parser.add_argument("--enable-thinking", action="store_true", help="开启深度思考")
    parser.add_argument("--reasoning-effort", choices=["high", "max"], default="high")
    parser.add_argument("--cache-target", type=float, default=10.0, help="缓存命中率验收目标%%（默认 10）")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=None, help="报告保存路径")
    args = parser.parse_args()

    if not API_KEY or not BASE_URL:
        print("❌ 缺少 DASHSCOPE_API_KEY_CN / DASHSCOPE_API_KEY_CN_url")
        sys.exit(1)

    random.seed(args.seed)

    print(f"\n{'=' * 66}")
    print("GLM-5.2 · 2M TPM 定向压测（coding/agent 长上下文）")
    print(f"{'=' * 66}")
    print(f"  Endpoint    : {BASE_URL}")
    print(f"  Model       : {MODEL}")
    print(f"  Target TPM  : {args.target_tpm:,}")
    print(f"  Duration    : {args.duration:.0f} s")
    print(f"  Per-req     : input ~{args.input_tokens:,} tok / output ~600 tok")
    print(f"  Thinking    : {'on (' + args.reasoning_effort + ')' if args.enable_thinking else 'off'}")
    print(f"{'=' * 66}")

    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=httpx.Timeout(600.0, connect=30.0),
        max_retries=0,
    )

    cpt, init_conc = await calibrate(client, args)

    print(f"\n🚀 开始闭环压测：锁定 {args.target_tpm:,} TPM，持续 {args.duration:.0f}s\n")
    results, duration = await drive(client, cpt, args, init_conc)

    ok = sum(1 for r in results if r.success)
    print(f"\n✅ 压测结束：成功 {ok}/{len(results)} 轮，实际耗时 {duration:.1f}s\n")

    # 失败原因归类（判断是否限流 429 / 超时）
    errs: Dict[str, int] = {}
    for r in results:
        if not r.success and r.error:
            key = r.error.split(":")[0][:40]
            errs[key] = errs.get(key, 0) + 1
    if errs:
        print("失败原因分布:")
        for k, v in sorted(errs.items(), key=lambda x: -x[1]):
            print(f"  {v:>4}  {k}")
        print()

    report_args = SimpleNamespace(cache_target=args.cache_target)
    report = build_report(results, duration, report_args)
    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n📄 报告已保存: {args.output}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[中断] 用户取消")
