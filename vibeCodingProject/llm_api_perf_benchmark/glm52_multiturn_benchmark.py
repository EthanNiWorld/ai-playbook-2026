"""
GLM-5.2 多轮对话性能压测脚本
================================================================

场景：多轮对话（Multi-Turn Chat），模拟真实 Coding 助手 / 客服长会话流量
  - 每个会话（Session）包含 N 轮对话，N 在 [min_turns, max_turns] 随机
  - 每轮携带完整对话历史，prompt 随轮次累积变长（前缀一致 → 命中 context cache）
  - 会话间并发，会话内串行（必须等上一轮回复才能发下一轮）

测量指标（流式逐 chunk 计时）：
  - TTFT  : 首 token 延迟        SLA: p50<4s  p75<8s  p90<12s  p99<30s
  - TPS   : 生成速率 tok/s       SLA: p50>70  p99>25
  - TPOT  : 每输出 token 平均耗时（ms）
  - ITL   : 相邻 chunk 到达间隔分布（ms）
  - Cache : prompt 缓存命中率（usage.prompt_tokens_details.cached_tokens）

运行：
  # 连通性验证（4 会话 x 2~3 轮，并发 2）
  python glm52_multiturn_benchmark.py --sessions 4 --min-turns 2 --max-turns 3 --concurrency 2

  # 正式压测（400 会话，1~24 轮随机，50 并发）
  python glm52_multiturn_benchmark.py --sessions 400 --max-turns 24 --concurrency 50

  # 开启深度思考模式
  python glm52_multiturn_benchmark.py --sessions 100 --enable-thinking --reasoning-effort high

环境变量（来自项目根目录 .env）：
  DASHSCOPE_API_KEY_CN      - 北京节点 API Key（必填）
  DASHSCOPE_API_KEY_CN_url  - 北京节点 endpoint（必填）
  GLM52_MODEL               - 可覆盖模型名，默认 glm-5.2
"""

import os
import sys
import time
import asyncio
import argparse
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_ENV_PATH)

BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_url")
API_KEY = os.getenv("DASHSCOPE_API_KEY_CN")
MODEL = os.getenv("GLM52_MODEL", "glm-5.2")

# ---------------------------------------------------------------------------
# 多轮对话内容库（AI Coding 场景）
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "你是一名资深软件架构师与全栈工程师，正在通过 IM 与开发者进行多轮技术对话。\n"
    "要求：\n"
    "1. 回答直接、专业，优先给出可运行的代码与可落地的方案；\n"
    "2. 涉及代码时遵循生产级标准：类型标注、错误处理、日志、并发安全；\n"
    "3. 多轮对话中记住上下文，后续回答必须与前面结论保持一致；\n"
    "4. 每次回复控制在 300 字以内（代码除外），不要重复前文已说过的内容。"
)

# 每个主题的第 0 轮：场景描述 + 代码上下文 + 具体问题（模拟用户贴代码提问）
TOPICS = [
    {
        "name": "python_async_queue",
        "opening": (
            "我们有一个基于 asyncio 的任务队列，线上偶发任务丢失，帮忙排查。核心代码：\n\n"
            "```python\n"
            "import asyncio\n"
            "from collections import deque\n\n"
            "class TaskQueue:\n"
            "    def __init__(self, maxsize=1000):\n"
            "        self._queue = deque(maxlen=maxsize)\n"
            "        self._running = False\n\n"
            "    async def put(self, task):\n"
            "        self._queue.append(task)\n\n"
            "    async def worker(self):\n"
            "        while self._running:\n"
            "            if self._queue:\n"
            "                task = self._queue.popleft()\n"
            "                await self._execute(task)\n"
            "            else:\n"
            "                await asyncio.sleep(0.1)\n\n"
            "    async def _execute(self, task):\n"
            "        try:\n"
            "            await task()\n"
            "        except Exception:\n"
            "            pass\n"
            "```\n\n"
            "问题：1) 找出所有可能导致任务丢失的缺陷；2) 给出修复后的完整实现。"
        ),
    },
    {
        "name": "go_concurrent_crawler",
        "opening": (
            "下面这个 Go 并发爬虫在压测时内存持续上涨直到 OOM，帮忙分析。核心代码：\n\n"
            "```go\n"
            "func Crawl(urls []string, concurrency int) []Result {\n"
            "    results := make([]Result, 0, len(urls))\n"
            "    ch := make(chan string, len(urls))\n"
            "    var wg sync.WaitGroup\n"
            "    for _, u := range urls {\n"
            "        ch <- u\n"
            "    }\n"
            "    for i := 0; i < concurrency; i++ {\n"
            "        wg.Add(1)\n"
            "        go func() {\n"
            "            defer wg.Done()\n"
            "            for u := range ch {\n"
            "                body, _ := fetch(u) // 大响应体\n"
            "                results = append(results, parse(body))\n"
            "            }\n"
            "        }()\n"
            "    }\n"
            "    wg.Wait()\n"
            "    return results\n"
            "}\n"
            "```\n\n"
            "问题：1) 指出内存泄漏与并发安全问题；2) 给出修复后的完整实现。"
        ),
    },
    {
        "name": "ts_state_store",
        "opening": (
            "我们自研的 TypeScript 状态管理库在大型表单场景下渲染卡顿，帮忙优化。核心代码：\n\n"
            "```typescript\n"
            "type Listener = () => void;\n\n"
            "class Store<T extends object> {\n"
            "  private state: T;\n"
            "  private listeners: Listener[] = [];\n\n"
            "  constructor(initial: T) { this.state = initial; }\n\n"
            "  getState(): T { return this.state; }\n\n"
            "  setState(partial: Partial<T>) {\n"
            "    this.state = { ...this.state, ...partial };\n"
            "    this.listeners.forEach(l => l());\n"
            "  }\n\n"
            "  subscribe(l: Listener) {\n"
            "    this.listeners.push(l);\n"
            "    return () => {\n"
            "      this.listeners = this.listeners.filter(x => x !== l);\n"
            "    };\n"
            "  }\n"
            "}\n"
            "```\n\n"
            "问题：1) 分析渲染卡顿的根因；2) 给出支持 selector 细粒度订阅的优化实现。"
        ),
    },
    {
        "name": "java_microservice_timeout",
        "opening": (
            "我们的 Java 微服务调用链在大促时出现大面积超时，帮忙做根因分析。调用链配置：\n\n"
            "```yaml\n"
            "# 网关 -> 订单服务 -> 库存服务 -> 数据库\n"
            "gateway:\n"
            "  timeout: 3s\n"
            "  retry: 2\n"
            "order-service:\n"
            "  timeout: 5s\n"
            "  retry: 3\n"
            "  thread-pool: 200\n"
            "inventory-service:\n"
            "  timeout: 10s\n"
            "  retry: 3\n"
            "  connection-pool: 50\n"
            "```\n\n"
            "问题：1) 从超时与重试配置角度分析雪崩风险；2) 给出修复后的配置与兜底方案。"
        ),
    },
]

# 通用追问库（第 1 轮及以后，跨主题复用）
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
    "补充完整的文档注释和类型标注。",
    "设计一个压测方案来验证你给出的性能结论。",
    "如何做到平滑升级和灰度发布？",
    "总结一下这次讨论的要点和后续行动项。",
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
    tps: float = 0.0                        # 生成速率（tok/s）
    tpot_ms: float = 0.0                    # 每输出 token 平均耗时（ms）
    itl_ms: List[float] = field(default_factory=list)  # 相邻 chunk 间隔（ms）
    prompt_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    content: str = ""
    error: Optional[str] = None


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
# 单轮请求：流式逐 chunk 精确计时
# ---------------------------------------------------------------------------

async def measure_turn(
    client: AsyncOpenAI,
    session_id: int,
    turn_index: int,
    messages: List[Dict[str, str]],
    max_tokens: int,
    enable_thinking: bool,
    reasoning_effort: str,
) -> TurnResult:
    """单轮对话请求，流式测量 TTFT / TPS / TPOT / ITL / 缓存命中"""
    kwargs = dict(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
        stream=True,
        stream_options={"include_usage": True},
    )
    if enable_thinking:
        kwargs["extra_body"] = {
            "thinking": {"type": "enabled"},
            "reasoning_effort": reasoning_effort,
        }

    try:
        start = time.perf_counter()
        first_token_time: Optional[float] = None
        last_token_time: Optional[float] = None
        chunk_times: List[float] = []
        content_parts: List[str] = []
        prompt_tokens = output_tokens = cached_tokens = 0

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            now = time.perf_counter()

            # 最后一条 chunk 带 usage（OpenAI 兼容协议）
            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0
                details = getattr(chunk.usage, "prompt_tokens_details", None)
                if details is not None:
                    cached_tokens = getattr(details, "cached_tokens", 0) or 0

            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # thinking 模式：reasoning_content 先到，同样计入 TTFT（首任意 token 口径）
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                if first_token_time is None:
                    first_token_time = now
                chunk_times.append(now)
                last_token_time = now

            if delta.content:
                if first_token_time is None:
                    first_token_time = now
                chunk_times.append(now)
                last_token_time = now
                content_parts.append(delta.content)

        if first_token_time is None or last_token_time is None:
            return TurnResult(
                session_id=session_id, turn_index=turn_index, success=False,
                error=f"no tokens received (output_tokens={output_tokens})",
            )

        ttft = first_token_time - start
        latency = last_token_time - start
        gen_time = max(last_token_time - first_token_time, 1e-6)
        n_out = output_tokens if output_tokens > 0 else len(content_parts)
        tps = n_out / gen_time
        tpot_ms = gen_time / max(n_out - 1, 1) * 1000
        itl_ms = [
            (chunk_times[i] - chunk_times[i - 1]) * 1000
            for i in range(1, len(chunk_times))
        ]

        return TurnResult(
            session_id=session_id,
            turn_index=turn_index,
            success=True,
            ttft=ttft,
            latency=latency,
            tps=tps,
            tpot_ms=tpot_ms,
            itl_ms=itl_ms,
            prompt_tokens=prompt_tokens,
            output_tokens=n_out,
            cached_tokens=cached_tokens,
            content="".join(content_parts),
        )

    except Exception as e:
        return TurnResult(
            session_id=session_id, turn_index=turn_index, success=False,
            error=f"{type(e).__name__}: {e}",
        )


# ---------------------------------------------------------------------------
# 会话执行器：会话内串行多轮，会话间并发
# ---------------------------------------------------------------------------

async def run_session(
    client: AsyncOpenAI,
    session_id: int,
    num_turns: int,
    args: argparse.Namespace,
    semaphore: asyncio.Semaphore,
    progress: Dict[str, int],
) -> List[TurnResult]:
    async with semaphore:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        topic = random.choice(TOPICS)
        # 每个 session 一份乱序追问池，避免同 session 内追问重复
        followup_pool = FOLLOWUP_QUESTIONS.copy()
        random.shuffle(followup_pool)

        results: List[TurnResult] = []
        for turn in range(num_turns):
            if turn == 0:
                user_msg = topic["opening"]
            elif turn - 1 < len(followup_pool):
                user_msg = followup_pool[turn - 1]
            else:
                user_msg = random.choice(FOLLOWUP_QUESTIONS)
            messages.append({"role": "user", "content": user_msg})

            r = await measure_turn(
                client, session_id, turn, messages,
                args.max_tokens, args.enable_thinking, args.reasoning_effort,
            )
            results.append(r)
            progress["done"] += 1

            if not r.success:
                progress["failed_turns"] += 1
                break  # 某轮失败则终止该会话（后续轮次无上下文意义）

            # 用真实回复回填对话历史（reasoning_content 不回填，API 不接受）
            messages.append({"role": "assistant", "content": r.content})

        return results


async def progress_printer(progress: Dict[str, int], start: float, stop: asyncio.Event):
    """每 15s 打印一次整体进度"""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=15)
            break
        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - start
            print(
                f"  [progress] {progress['done']}/{progress['total']} turns done, "
                f"{elapsed:.0f}s elapsed, failed={progress['failed_turns']}",
                flush=True,
            )


# ---------------------------------------------------------------------------
# 报告生成（ASCII 表格，与参考输出风格一致）
# ---------------------------------------------------------------------------

TABLE_W = 60  # 内容区宽度（不含两侧 + 或 |）


def build_report(results: List[TurnResult], duration: float, args: argparse.Namespace) -> str:
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
        for p in (50, 75, 90, 95, 99):
            rows.append((f"p{p}", percentile(values, p)))
        for label, v in rows:
            kv(label, f"{fmt.format(v)} {unit}", indent=4)

    ok = [r for r in results if r.success]
    failed = len(results) - len(ok)
    if not ok:
        return "ALL REQUESTS FAILED"

    ttfts = [r.ttft for r in ok]
    lats = [r.latency for r in ok]
    tpots = [r.tpot_ms for r in ok]
    tpss = [r.tps for r in ok if r.tps > 0]
    itls = [v for r in ok for v in r.itl_ms]
    total_prompt = sum(r.prompt_tokens for r in ok)
    total_output = sum(r.output_tokens for r in ok)
    total_cached = sum(r.cached_tokens for r in ok)
    cache_rate = total_cached / total_prompt * 100 if total_prompt > 0 else 0.0

    # ---- BENCHMARK RESULTS ----
    hline()
    title("BENCHMARK RESULTS")
    hline()
    kv("Total requests", f"{len(ok)}")
    if failed:
        kv("Failed requests", f"{failed}")
    kv("Duration", f"{duration:.1f} s")
    kv("Avg prompt length", f"{statistics.mean([r.prompt_tokens for r in ok]):.0f} tok")
    kv("Avg output length", f"{statistics.mean([r.output_tokens for r in ok]):.0f} tok")
    kv("Cache hit rate", f"{cache_rate:.2f}%")

    # ---- THROUGHPUT ----
    hline()
    title("THROUGHPUT")
    hline()
    kv("Request", f"{len(ok) / duration:.2f} req/s")
    kv("Input tokens", f"{total_prompt / duration:.1f} tok/s")
    kv("Output tokens", f"{total_output / duration:.1f} tok/s")

    # ---- 延迟与生成指标 ----
    stat_section("TTFT", ttfts, "s")
    stat_section("LATENCY (end-to-end)", lats, "s")
    stat_section("TPOT (time per output token)", tpots, "ms")
    if tpss:
        stat_section("TPS (output tok/s, per-request)", tpss, "tok/s", fmt="{:.1f}")
    if itls:
        stat_section("ITL (inter-token latency)", itls, "ms")

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

    # ---- SLA VERIFICATION ----
    hline()
    title("SLA VERIFICATION")
    hline()
    checks = [
        ("TTFT p50 < 4s", percentile(ttfts, 50), 4.0, "<", "s"),
        ("TTFT p75 < 8s", percentile(ttfts, 75), 8.0, "<", "s"),
        ("TTFT p90 < 12s", percentile(ttfts, 90), 12.0, "<", "s"),
        ("TTFT p99 < 30s", percentile(ttfts, 99), 30.0, "<", "s"),
    ]
    if tpss:
        checks += [
            ("TPS p50 > 70 tok/s", percentile(tpss, 50), 70.0, ">", "tok/s"),
            ("TPS p99 > 25 tok/s", percentile(tpss, 99), 25.0, ">", "tok/s"),
        ]
    checks.append(
        (f"Cache hit rate > {args.cache_target:.0f}%", cache_rate, args.cache_target, ">", "%")
    )

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
        else:
            val = f"{actual:.2f} s  {mark}"
        kv(label, val)
    hline()
    kv("OVERALL", "PASS" if all_pass else "FAIL")
    hline()

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="GLM-5.2 多轮对话性能压测（TTFT/TPS/TPOT/ITL/缓存命中率）"
    )
    parser.add_argument("--sessions", type=int, default=400,
                        help="会话总数（默认 400）")
    parser.add_argument("--min-turns", type=int, default=1,
                        help="每会话最小轮次（默认 1）")
    parser.add_argument("--max-turns", type=int, default=24,
                        help="每会话最大轮次（默认 24）")
    parser.add_argument("--concurrency", type=int, default=50,
                        help="并发会话数（默认 50）")
    parser.add_argument("--max-tokens", type=int, default=512,
                        help="单轮最大输出 tokens（默认 512）")
    parser.add_argument("--cache-target", type=float, default=70.0,
                        help="缓存命中率验收目标 %%（默认 70）")
    parser.add_argument("--enable-thinking", action="store_true",
                        help="开启 GLM-5.2 深度思考模式")
    parser.add_argument("--reasoning-effort", choices=["high", "max"], default="high",
                        help="思考深度（默认 high，仅 --enable-thinking 时生效）")
    parser.add_argument("--warmup", type=int, default=2,
                        help="预热请求数（默认 2，排除冷启动）")
    parser.add_argument("--seed", type=int, default=42,
                        help="随机种子（默认 42，保证会话计划可复现）")
    parser.add_argument("--output", type=str, default=None,
                        help="可选：将报告同时保存到指定文件")
    args = parser.parse_args()

    if not API_KEY:
        print("❌ 未找到 DASHSCOPE_API_KEY_CN 环境变量")
        print("   请在 .env 中配置：DASHSCOPE_API_KEY_CN=sk-xxx")
        sys.exit(1)
    if not BASE_URL:
        print("❌ 未找到 DASHSCOPE_API_KEY_CN_url 环境变量")
        print("   请在 .env 中配置：DASHSCOPE_API_KEY_CN_url=https://llm-xxx.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
        sys.exit(1)

    random.seed(args.seed)

    print(f"\n{'=' * 62}")
    print("GLM-5.2 多轮对话性能压测")
    print(f"{'=' * 62}")
    print(f"  Endpoint   : {BASE_URL}")
    print(f"  Model      : {MODEL}")
    print(f"  Sessions   : {args.sessions}（每会话 {args.min_turns}~{args.max_turns} 轮随机）")
    print(f"  Concurrency: {args.concurrency} 会话")
    print(f"  max_tokens : {args.max_tokens}  |  thinking: "
          f"{'on (' + args.reasoning_effort + ')' if args.enable_thinking else 'off'}")
    print(f"  SLA        : TTFT p50<4s p75<8s p90<12s p99<30s | "
          f"TPS p50>70 p99>25 tok/s | Cache>{args.cache_target:.0f}%")
    print(f"{'=' * 62}")

    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=httpx.Timeout(600.0, connect=30.0),
    )

    # ---- Warm-up（排除冷启动）----
    print(f"\n⏳ Warm-up: {args.warmup} 个轻量请求...")
    for i in range(args.warmup):
        r = await measure_turn(
            client, -1, 0,
            [{"role": "user", "content": "你好，请用一句话介绍你自己。"}],
            64, args.enable_thinking, args.reasoning_effort,
        )
        status = f"TTFT={r.ttft:.2f}s" if r.success else f"✗ {r.error}"
        print(f"  warm-up {i + 1}: {status}")

    # ---- 生成会话计划（轮次随机，seed 保证可复现）----
    plans = [
        (sid, random.randint(args.min_turns, args.max_turns))
        for sid in range(args.sessions)
    ]
    total_turns = sum(t for _, t in plans)
    print(f"\n🚀 压测开始: {args.sessions} 个会话，共 {total_turns} 轮请求计划")

    semaphore = asyncio.Semaphore(args.concurrency)
    progress = {"done": 0, "total": total_turns, "failed_turns": 0}
    stop_event = asyncio.Event()

    start = time.perf_counter()
    printer = asyncio.create_task(progress_printer(progress, start, stop_event))
    nested = await asyncio.gather(
        *[run_session(client, sid, turns, args, semaphore, progress)
          for sid, turns in plans]
    )
    duration = time.perf_counter() - start
    stop_event.set()
    try:
        await printer
    except asyncio.CancelledError:
        pass

    results = [r for rs in nested for r in rs]
    ok_count = sum(1 for r in results if r.success)
    print(f"\n✅ 压测结束: 成功 {ok_count}/{len(results)} 轮，耗时 {duration:.1f}s\n")

    report = build_report(results, duration, args)
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
