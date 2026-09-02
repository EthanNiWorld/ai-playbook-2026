"""
================================================================================
百炼（DashScope）缓存命中率最大化 · 最佳实践 Demo（以 GLM-5.2 为例）
================================================================================

本文件是 dashscope_multi_account_router.py（多账号负载均衡）与
dashscope_multi_account_router_upgrade_with_cache.py（缓存亲和路由）的泛化整合版，
目标是给出「在多账号聚合场景下，如何把上下文缓存命中率做到最高」的可运行参考实现，
并输出与 llm_api_perf_benchmark/results_2m_tpm_768s.txt 一致的标准压测报告。

--------------------------------------------------------------------------------
一、上下文缓存（Context Cache）工作原理与命中前提
--------------------------------------------------------------------------------
百炼商业模型（GLM-5.2 / Qwen 等）默认开启「上下文缓存」：把请求 prompt 的前缀
KV 计算结果缓存在推理实例上，后续请求若前缀逐 token 一致即可复用，省去重复 prefill。
命中信息通过 OpenAI 兼容响应的 usage.prompt_tokens_details.cached_tokens 返回。

命中的三个硬前提（缺一不可）：
  1. 逐 token 完全一致：从第 1 个 token 起连续匹配，遇到第一个不同 token 即断裂；
     不是"语义相似"，是"字节级相同"。
  2. 缓存有归属：缓存绑定在具体 workspace/账号/实例上，跨 key 不共享。
  3. 前缀足够长且未过期：太短不进缓存；冷门前缀会被 TTL 淘汰。

--------------------------------------------------------------------------------
二、多账号聚合下"最大化命中率"的 6 条最佳实践（本 Demo 全部落地）
--------------------------------------------------------------------------------
1) 缓存亲和路由（Cache-Affinity Routing）
   按"前缀指纹"一致性哈希选账号，同一前缀恒定路由到同一账号，让缓存持续保温。
   —— 对应 CacheAffinityRouter.route()。这是与朴素轮询/随机路由的本质区别：
      轮询会把同一前缀打散到多个账号，每个账号各自冷启动，命中率被稀释。

2) 会话粘性（Session Stickiness）
   多轮对话用同一 affinity_key（会话稳定前缀的指纹）→ 整个会话锁定同一账号，
   使逐轮累积的长前缀在该账号上持续复用。—— 对应 run_session() 传入的 affinity_key。

3) 稳定前缀前置、动态内容后置
   system + 少样本 + 固定知识块放最前（静态），用户实时问题放最后（动态）。
   只要动态内容在尾部，前面的长前缀就能稳定命中。—— 对应 build_prefix()。

4) 前缀规范化（Normalization）
   前缀内禁止出现时间戳、UUID、随机 traceId；JSON 固定字段顺序；统一 system 版本。
   任何"看不见的抖动"都会让逐 token 匹配断裂。

5) 平滑爬坡（Burst-Aware Ramp）
   百炼对"负载爬升速度"有单独限流（Throttling.BurstRate，令牌桶：容量≈瞬时突发头寸，
   回填速率≈稳态 TPM/60）。发包必须平滑：每窗口新增 token 增量 ≤ 稳态 TPM/60。
   —— 对应 main() 中的分波启动（wave/ramp）。

6) 429 分类退避
   BurstRate → 短退避（斜率问题，稍等即可重试，无需切账号）；
   limit_requests / limit_tokens → 冷却该账号、切到其他账号（稳态额度问题）。
   —— 对应 CacheAffinityRouter.chat_stream() 的异常分支。

--------------------------------------------------------------------------------
补充：50 UID 规模下的 cache/TPM 平衡（有界扇出 Bounded Fanout）
--------------------------------------------------------------------------------
聚合平台汇聚 50 个 UID 是为了突破"单 key TPM 固定"的上限——把多个 UID 的 TPM
叠加起来支撑更大总吞吐。但缓存绑定在 UID 维度、跨 UID 不共享，于是产生核心矛盾：
  - 完全打散（把同一前缀分散到 50 个 UID）→ 总 TPM 最大，但每个 UID 各自冷启动，
    缓存命中率趋近 0。
  - 完全亲和（同一前缀锁定 1 个 UID）→ 缓存命中率最高，但该前缀吞吐被单 UID 的
    固定 TPM 卡死，失去聚合意义。
解法是「有界扇出」：prefix 一致性哈希到一个大小为 G 的账号组，组内负载均衡。
  - G=1：最大缓存局部性（命中率最高，适合冷门/中频前缀）
  - G=n：完全打散（等价朴素轮询，缓存最低）
  - 生产取值：G ≈ ceil(该前缀峰值 TPM / 单 UID TPM 上限)，即"够用就好"的最小 G，
    只为该前缀维持 G 份缓存副本而非 50 份，兼顾命中率与 TPM 聚合。
  —— 对应 CacheAffinityRouter(group_size=G) 与 --sweep-groups 扫描。
本 Demo 用 2~4 个 key 即可验证该机制：--sweep-groups 会打印 G=1..n 下的
「缓存命中率 vs 最热账号流量占比」，直观看到平衡点；结论可线性外推到 50 UID。

--------------------------------------------------------------------------------
三、各项指标的定义、测量方式、报告口径与重要性
--------------------------------------------------------------------------------
【Cache hit rate（缓存命中率）】—— 本 Demo 的核心优化目标
  测量：measure_turn() 解析 usage.prompt_tokens_details.cached_tokens
  计算：sum(cached_tokens) / sum(prompt_tokens) × 100%
  报告：BENCHMARK RESULTS 段总命中率；PER-ROUND BREAKDOWN 段分轮命中率
  重要性：直接决定 prefill 成本与 TTFT。命中率越高，重复前缀几乎零成本，
          TTFT 显著下降、有效吞吐上升。多轮场景应看到 round0≈0%、后续轮快速抬升。

【TTFT（首 token 延迟，Time To First Token）】
  测量：measure_turn() 中 ttft = first_token_time - start，流式逐 chunk 计时，
        取首个任意 token（thinking 开启时含 reasoning_content）
  报告：TTFT 专段输出 avg/p50/p75/p90/p95/p99（秒）
  SLA 判定：p50<4s / p75<8s / p90<12s / p99<30s，纳入 OVERALL PASS/FAIL
  重要性：交互体验的第一印象；命中缓存可大幅缩短（省去长前缀 prefill）。

【TPOT（每输出 token 耗时，Time Per Output Token）】
  计算：tpot_ms = gen_time / max(n_out - 1, 1) * 1000，
        即 (末 token 时间 - 首 token 时间) / (输出 token 数 - 1)，逐请求一个值
  报告：TPOT 专段输出 avg/p50/p75/p90/p95/p99（毫秒）
  仅展示，无 SLA 验收项（验收只对 TTFT 和 TPS 设阈值）
  重要性：反映稳定生成阶段的单 token 时延，衡量解码速度与负载压力。

【ITL（相邻 token 到达间隔，Inter-Token Latency）】
  计算：相邻 chunk 到达时间差（ms），逐 chunk 收集后汇总
  报告：ITL 专段 avg/p50/p75/p90/p95/p99（毫秒），仅展示
  重要性：反映流式输出的"顺滑度"，高并发下抖动会放大 p90/p99。

【TPS（单请求输出速率，output tok/s）】
  计算：tps = n_out / gen_time，逐请求一个值
  报告：TPS 专段 avg/p50/p75/p90/p95/p99（tok/s）
  SLA 判定：p50>70 / p99>25 tok/s，纳入 OVERALL
  重要性：单请求生成快慢；满载时会下降，是压力的直接体现。

【LATENCY（端到端延迟）】
  计算：latency = last_token_time - start（含 TTFT + 全部生成时间）
  报告：LATENCY 专段 avg/p50/.../p99（秒），仅展示
  重要性：用户拿到完整回复的总耗时。

【THROUGHPUT（吞吐）】
  计算：Request=成功数/duration；Input=Σprompt_tokens/duration；Output=Σ完成/duration
  报告：THROUGHPUT 段 req/s、input tok/s、output tok/s
  重要性：聚合平台的产能标尺；结合命中率看"有效算力利用"。

【PER-ROUND BREAKDOWN（分轮拆解）】
  报告：每一轮的请求数、TTFT avg、Latency avg、Cache 命中率
  重要性：直观展示"缓存随轮次升温"——最佳实践下应看到命中率逐轮抬升。

用法：
  # 最佳实践跑（缓存亲和 + 会话粘性 + 平滑爬坡），输出标准报告
  python dashscope_cache_maximization_demo.py --sessions 12 --concurrency 3

  # 加 --compare 同时跑朴素轮询基线，对比命中率差距
  python dashscope_cache_maximization_demo.py --sessions 12 --compare

账号配置（二选一，按顺序探测）：
  1) 通用：DASHSCOPE_ACCOUNT_1_KEY / DASHSCOPE_ACCOUNT_1_BASE_URL（可配 N 个）
  2) 回退：自动发现 .env 中已知的北京节点 GLM-5.2 key（CN / CN_TEST / INTL_BJ_TEST）
"""

import os
import sys
import time
import json
import hashlib
import asyncio
import argparse
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import httpx
from openai import AsyncOpenAI, APIStatusError

# ---------------------------------------------------------------------------
# .env 加载（本文件位于 alibaba-ai-hub/maas/api-sample/，向上 3 级到仓库根）
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_ENV_PATH = os.path.join(_ROOT, ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

MODEL = os.getenv("GLM52_MODEL", "glm-5.2")


# ---------------------------------------------------------------------------
# 账号：运行时统计 + 429 熔断
# ---------------------------------------------------------------------------
@dataclass
class Account:
    uid: str
    api_key: str
    base_url: str
    client: AsyncOpenAI = field(default=None, repr=False)
    cooldown_until: float = 0.0
    req_ok: int = 0
    req_429: int = 0
    inflight: int = 0
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0

    @property
    def available(self) -> bool:
        return time.time() >= self.cooldown_until

    def cooldown(self, seconds: float):
        self.cooldown_until = time.time() + seconds


def load_accounts() -> List[Account]:
    """泛化账号加载：先通用格式，回退到 .env 已知北京节点 GLM-5.2 key。"""
    specs: List[tuple] = []
    # 1) 通用：DASHSCOPE_ACCOUNT_{N}_KEY / _BASE_URL
    i = 1
    while True:
        key = os.getenv(f"DASHSCOPE_ACCOUNT_{i}_KEY")
        if not key:
            break
        url = os.getenv(f"DASHSCOPE_ACCOUNT_{i}_BASE_URL")
        specs.append((f"acc{i}", key, url))
        i += 1
    # 2) 回退：已知北京节点 key（GLM-5.2 可用）
    if not specs:
        known = [
            ("CN", "DASHSCOPE_API_KEY_CN", "DASHSCOPE_API_KEY_CN_url"),
            ("CN_TEST", "DASHSCOPE_API_KEY_CN_TEST", "DASHSCOPE_API_KEY_CN_URL"),
            ("INTL_BJ_TEST", "DASHSCOPE_API_KEY_INTL_BJ_TEST", "DASHSCOPE_API_KEY_INTL_BJ_TEST_URL"),
        ]
        for uid, ke, ue in known:
            key, url = os.getenv(ke), os.getenv(ue)
            if key and url:
                specs.append((uid, key, url))

    accounts: List[Account] = []
    for uid, key, url in specs:
        if not key or not url:
            continue
        acc = Account(uid=uid, api_key=key, base_url=url)
        acc.client = AsyncOpenAI(
            api_key=key, base_url=url, max_retries=0,
            http_client=httpx.AsyncClient(
                limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
                timeout=httpx.Timeout(300.0, connect=15.0),
            ),
        )
        accounts.append(acc)
    if not accounts:
        print("❌ 未找到账号配置。请在 .env 配置 DASHSCOPE_ACCOUNT_1_KEY/_BASE_URL，"
              "或提供 DASHSCOPE_API_KEY_CN(+_url) 等北京节点 key。")
        sys.exit(1)
    return accounts


# ---------------------------------------------------------------------------
# 指标数据结构
# ---------------------------------------------------------------------------
@dataclass
class TurnResult:
    session_id: int
    turn_index: int
    success: bool
    account_uid: str = ""
    ttft: float = 0.0
    latency: float = 0.0
    tps: float = 0.0
    tpot_ms: float = 0.0
    itl_ms: List[float] = field(default_factory=list)
    prompt_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    content: str = ""
    error: Optional[str] = None


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    n = len(s)
    if n == 1:
        return s[0]
    k = (n - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < n else f
    return s[f] + (k - f) * (s[c] - s[f])


def _extract_cached(usage) -> int:
    details = getattr(usage, "prompt_tokens_details", None)
    if details is None:
        return 0
    if isinstance(details, dict):
        return int(details.get("cached_tokens", 0) or 0)
    return int(getattr(details, "cached_tokens", 0) or 0)



# ---------------------------------------------------------------------------
# 单轮流式请求：精确测量 TTFT / TPOT / ITL / TPS / Cache
# ---------------------------------------------------------------------------
async def measure_turn(client: AsyncOpenAI, session_id: int, turn_index: int,
                       messages: List[Dict[str, str]], max_tokens: int,
                       enable_thinking: bool, reasoning_effort: str) -> TurnResult:
    kwargs: Dict[str, Any] = dict(
        model=MODEL, messages=messages, max_tokens=max_tokens, temperature=0.7,
        stream=True, stream_options={"include_usage": True},
    )
    if enable_thinking:
        kwargs["extra_body"] = {"thinking": {"type": "enabled"},
                                "reasoning_effort": reasoning_effort}

    start = time.perf_counter()
    first_t: Optional[float] = None
    last_t: Optional[float] = None
    chunk_times: List[float] = []
    parts: List[str] = []
    prompt_tokens = output_tokens = cached_tokens = 0

    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        now = time.perf_counter()
        if chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens or 0
            output_tokens = chunk.usage.completion_tokens or 0
            cached_tokens = _extract_cached(chunk.usage)
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            if first_t is None:
                first_t = now
            chunk_times.append(now)
            last_t = now
        if delta.content:
            if first_t is None:
                first_t = now
            chunk_times.append(now)
            last_t = now
            parts.append(delta.content)

    if first_t is None or last_t is None:
        return TurnResult(session_id, turn_index, False,
                          error=f"no tokens (output={output_tokens})")

    ttft = first_t - start
    latency = last_t - start
    gen = max(last_t - first_t, 1e-6)
    n_out = output_tokens if output_tokens > 0 else len(parts)
    itl = [(chunk_times[i] - chunk_times[i - 1]) * 1000 for i in range(1, len(chunk_times))]
    return TurnResult(
        session_id, turn_index, True,
        ttft=ttft, latency=latency, tps=n_out / gen,
        tpot_ms=gen / max(n_out - 1, 1) * 1000, itl_ms=itl,
        prompt_tokens=prompt_tokens, output_tokens=n_out,
        cached_tokens=cached_tokens, content="".join(parts),
    )


# ---------------------------------------------------------------------------
# 缓存亲和路由器：一致性哈希 + 会话粘性 + 429 分类退避
# ---------------------------------------------------------------------------
class CacheAffinityRouter:
    """
    最佳实践路由器：
    - route(): 按 affinity_key 一致性哈希选账号，同前缀恒定落到同账号（缓存保温）；
      若首选账号在冷却中，沿哈希环顺延到下一个可用账号。
    - chat_stream(): 429 分类退避——BurstRate 短退避重试；limit_* 冷却该账号并换账号。
    """
    BURST_BACKOFF = 3.0      # BurstRate：短退避（斜率问题）
    LIMIT_COOLDOWN = 65.0    # limit_requests/limit_tokens：账号冷却一个窗口

    def __init__(self, accounts: List[Account], max_retries: int = 4, group_size: int = 1):
        self.accounts = accounts
        self.max_retries = max_retries
        self.group_size = max(1, group_size)   # 有界扇出：prefix→G 个账号的组，组内均衡

    def route(self, affinity_key: str) -> Optional[Account]:
        """有界扇出路由：prefix 一致性哈希定位起点，取 G 个账号的组，组内挑在途最少的
        可用账号。G=1→最大缓存局部性；G=n→完全打散（等价朴素轮询）。"""
        n = len(self.accounts)
        base = int(hashlib.md5(affinity_key.encode()).hexdigest(), 16) % n
        group = [self.accounts[(base + o) % n] for o in range(min(self.group_size, n))]
        avail = [a for a in group if a.available]
        if not avail:                              # 组内全部冷却 → 兜底任意可用账号
            avail = [a for a in self.accounts if a.available]
        if not avail:
            return None
        return min(avail, key=lambda a: (a.inflight, a.req_ok))

    @staticmethod
    def _err_code(e: APIStatusError) -> str:
        code = getattr(e, "code", None)
        if not code:
            body = getattr(e, "body", None)
            if isinstance(body, dict):
                code = body.get("code")
        return code or f"http_{getattr(e, 'status_code', '?')}"

    async def chat_stream(self, session_id: int, turn_index: int,
                          messages: List[Dict[str, str]], affinity_key: str,
                          max_tokens: int, enable_thinking: bool,
                          reasoning_effort: str) -> TurnResult:
        last_err = None
        for attempt in range(self.max_retries):
            acc = self.route(affinity_key)
            if acc is None:                        # 全部冷却，稍等
                await asyncio.sleep(min(2 ** attempt, 8))
                continue
            acc.inflight += 1
            try:
                r = await measure_turn(acc.client, session_id, turn_index, messages,
                                       max_tokens, enable_thinking, reasoning_effort)
                r.account_uid = acc.uid
                if r.success:
                    acc.req_ok += 1
                    acc.prompt_tokens += r.prompt_tokens
                    acc.cached_tokens += r.cached_tokens
                    acc.completion_tokens += r.output_tokens
                return r
            except APIStatusError as e:
                code = self._err_code(e)
                last_err = f"{code}"
                if e.status_code == 429:
                    acc.req_429 += 1
                    if code == "Throttling.BurstRate":
                        await asyncio.sleep(self.BURST_BACKOFF)   # 短退避，不切账号
                    else:                                          # limit_requests/limit_tokens
                        acc.cooldown(self.LIMIT_COOLDOWN)          # 冷却并换账号
                    continue
                await asyncio.sleep(min(2 ** attempt, 8))
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                await asyncio.sleep(min(2 ** attempt, 8))
            finally:
                acc.inflight -= 1
        return TurnResult(session_id, turn_index, False, error=last_err or "exhausted")


# ---------------------------------------------------------------------------
# Workload：长稳定前缀（前置）+ 多轮短追问（后置）；affinity_key = 会话主题指纹
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "你是一名资深软件架构师与全栈工程师，正在通过 IM 与开发者进行多轮技术对话。"
    "回答直接、专业，优先给出可运行代码与可落地方案；多轮中须记住上下文、保持结论一致；"
    "每次回复控制在 300 字以内（代码除外），不重复前文。"
)

# 每个主题的稳定长前缀（静态：背景 + 代码上下文），逐 token 稳定 → 可被缓存复用
TOPICS = [
    ("async_queue", "asyncio 任务队列偶发任务丢失排查"),
    ("go_crawler", "Go 并发爬虫压测内存持续上涨 OOM 分析"),
    ("ts_store", "TypeScript 状态管理库大型表单渲染卡顿优化"),
    ("java_timeout", "Java 微服务调用链大促大面积超时根因分析"),
]

FOLLOWUPS = [
    "这个方案在高并发下有什么潜在问题？请详细分析。",
    "帮我为上面的代码补充完整的单元测试。",
    "能进一步优化性能吗？给出优化后的完整代码。",
    "如果要支持分布式部署，需要做哪些改造？",
    "请解释核心实现原理，越详细越好。",
    "帮我做一次代码审查，指出潜在 bug 与安全风险。",
]


def build_prefix(topic_desc: str, pad_units: int) -> str:
    """构造稳定长前缀：背景 + 结构化知识块（静态、逐 token 稳定、无时间戳/随机量）。"""
    kb = "\n".join(
        f"- 规范 R{j}：针对「{topic_desc}」场景的第 {j} 项工程约束，须核对上下文、"
        f"确认边界条件、给出可执行修复，并提示并发安全与资源释放要求。"
        for j in range(1, pad_units + 1)
    )
    return (
        f"【任务背景】{topic_desc}。以下是团队沉淀的工程规范与知识库，"
        f"请通读并作为本次会话所有回答的依据：\n\n===== 知识库 =====\n{kb}\n\n"
        f"===== 首个问题 =====\n请先概述你将如何系统性地排查/优化该问题。"
    )



# ---------------------------------------------------------------------------
# 会话执行：会话内串行多轮，affinity_key 固定 → 整会话锁同账号（会话粘性）
# ---------------------------------------------------------------------------
async def run_session(router: CacheAffinityRouter, session_id: int, num_turns: int,
                      args: argparse.Namespace, sticky: bool,
                      progress: Dict[str, int]) -> List[TurnResult]:
    topic_key, topic_desc = TOPICS[session_id % len(TOPICS)]
    # affinity_key：sticky=True 用会话主题指纹（同主题→同账号，缓存保温）；
    #               sticky=False 用逐请求变化的 key（模拟朴素轮询打散，对照用）
    prefix = build_prefix(topic_desc, args.prefix_units)
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prefix}]
    results: List[TurnResult] = []
    for turn in range(num_turns):
        if turn > 0:
            messages.append({"role": "user", "content": FOLLOWUPS[(turn - 1) % len(FOLLOWUPS)]})
        affinity = topic_key if sticky else f"{topic_key}-{session_id}-{turn}"
        r = await router.chat_stream(session_id, turn, messages, affinity,
                                     args.max_tokens, args.enable_thinking, args.reasoning_effort)
        results.append(r)
        progress["done"] += 1
        if not r.success:
            progress["failed"] += 1
            break
        messages.append({"role": "assistant", "content": r.content})
    return results


# ---------------------------------------------------------------------------
# 标准报告（对齐 results_2m_tpm_768s.txt 格式）
# ---------------------------------------------------------------------------
TABLE_W = 60


def build_report(results: List[TurnResult], duration: float,
                 accounts: List[Account], cache_target: float) -> str:
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
        hline(); title(name); hline()
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
    cache_rate = total_cached / total_prompt * 100 if total_prompt else 0.0

    hline(); title("BENCHMARK RESULTS"); hline()
    kv("Total requests", f"{len(ok)}")
    if failed:
        kv("Failed requests", f"{failed}")
    kv("Duration", f"{duration:.1f} s")
    kv("Avg prompt length", f"{statistics.mean([r.prompt_tokens for r in ok]):.0f} tok")
    kv("Avg output length", f"{statistics.mean([r.output_tokens for r in ok]):.0f} tok")
    kv("Cache hit rate", f"{cache_rate:.2f}%")

    hline(); title("THROUGHPUT"); hline()
    kv("Request", f"{len(ok) / duration:.2f} req/s")
    kv("Input tokens", f"{total_prompt / duration:.1f} tok/s")
    kv("Output tokens", f"{total_output / duration:.1f} tok/s")

    stat_section("TTFT", ttfts, "s")
    stat_section("LATENCY (end-to-end)", lats, "s")
    stat_section("TPOT (time per output token)", tpots, "ms")
    if tpss:
        stat_section("TPS (output tok/s, per-request)", tpss, "tok/s", fmt="{:.1f}")
    if itls:
        stat_section("ITL (inter-token latency)", itls, "ms")

    # PER-ROUND BREAKDOWN
    rounds: Dict[int, List[TurnResult]] = {}
    for r in ok:
        rounds.setdefault(r.turn_index, []).append(r)
    hline(); title("PER-ROUND BREAKDOWN"); hline()
    A(("|  Round   Reqs    TTFT avg     Lat avg     Cache").ljust(TABLE_W + 1) + "|")
    A("|  " + "-" * (TABLE_W - 4) + "  |")
    for ti in sorted(rounds):
        rs = rounds[ti]
        rp = sum(r.prompt_tokens for r in rs)
        rc = sum(r.cached_tokens for r in rs)
        row = (f"|  {ti:>5}  {len(rs):>6}  {statistics.mean([r.ttft for r in rs]):>7.2f} s  "
               f"{statistics.mean([r.latency for r in rs]):>8.2f} s  "
               f"{(rc / rp * 100 if rp else 0):>6.2f}%")
        A(row.ljust(TABLE_W + 1) + "|")

    # PER-ACCOUNT（多账号缓存亲和分布）
    hline(); title("PER-ACCOUNT (cache-affinity 分布)"); hline()
    A(("|  Account         Reqs   429   Cache        tokens").ljust(TABLE_W + 1) + "|")
    A("|  " + "-" * (TABLE_W - 4) + "  |")
    for a in accounts:
        cr = a.cached_tokens / a.prompt_tokens * 100 if a.prompt_tokens else 0.0
        row = (f"|  {a.uid:<14} {a.req_ok:>5} {a.req_429:>5}  {cr:>6.2f}%  "
               f"{a.prompt_tokens + a.completion_tokens:>10}")
        A(row.ljust(TABLE_W + 1) + "|")

    # SLA VERIFICATION
    hline(); title("SLA VERIFICATION"); hline()
    checks = [
        ("TTFT p50 < 4s", percentile(ttfts, 50), 4.0, "<", "s"),
        ("TTFT p75 < 8s", percentile(ttfts, 75), 8.0, "<", "s"),
        ("TTFT p90 < 12s", percentile(ttfts, 90), 12.0, "<", "s"),
        ("TTFT p99 < 30s", percentile(ttfts, 99), 30.0, "<", "s"),
    ]
    if tpss:
        checks += [("TPS p50 > 70 tok/s", percentile(tpss, 50), 70.0, ">", "tok/s"),
                   ("TPS p99 > 25 tok/s", percentile(tpss, 99), 25.0, ">", "tok/s")]
    checks.append((f"Cache hit rate > {cache_target:.0f}%", cache_rate, cache_target, ">", "%"))

    all_pass = True
    for label, actual, target, op, unit in checks:
        passed = actual < target if op == "<" else actual > target
        all_pass = all_pass and passed
        mark = "PASS" if passed else "FAIL"
        if unit == "%":
            val = f"{actual:.2f}%  {mark}"
        elif unit == "tok/s":
            val = f"{actual:.1f} tok/s  {mark}"
        else:
            val = f"{actual:.2f} s  {mark}"
        kv(label, val)
    hline(); kv("OVERALL", "PASS" if all_pass else "FAIL"); hline()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口：平滑爬坡启动会话（burst-aware），会话间并发、会话内串行
# ---------------------------------------------------------------------------
async def run_all(router: CacheAffinityRouter, args: argparse.Namespace,
                  sticky: bool) -> tuple:
    import random
    random.seed(args.seed)
    plans = [(sid, random.randint(1, args.max_turns)) for sid in range(args.sessions)]
    progress = {"done": 0, "failed": 0}
    sem = asyncio.Semaphore(args.concurrency)

    async def _wrapped(sid, turns):
        async with sem:
            return await run_session(router, sid, turns, args, sticky, progress)

    start = time.perf_counter()
    tasks = []
    # 平滑爬坡：分波启动，避免瞬时突发触发 Throttling.BurstRate
    for i, (sid, turns) in enumerate(plans):
        tasks.append(asyncio.create_task(_wrapped(sid, turns)))
        if args.ramp_gap > 0 and (i + 1) % max(1, args.ramp_batch) == 0:
            await asyncio.sleep(args.ramp_gap)
    nested = await asyncio.gather(*tasks)
    duration = time.perf_counter() - start
    return [r for rs in nested for r in rs], duration


async def sweep_groups(router: CacheAffinityRouter, accounts: List[Account],
                       args: argparse.Namespace):
    """扫描 group-size=1..n：展示「缓存命中率 vs TPM 分散度」的平衡曲线。
    group 越小→缓存局部性越强(命中率高)但流量越集中(受单UID TPM限)；
    group 越大→流量越分散(可聚合更多TPM)但缓存被稀释。生产按单UID TPM上限选最小可行 group。"""
    print("🔬 group-size 扫描（缓存命中率 vs 最热账号流量占比）\n")
    for g in range(1, len(accounts) + 1):
        for a in accounts:
            a.req_ok = a.req_429 = a.prompt_tokens = a.cached_tokens = a.completion_tokens = 0
            a.cooldown_until = 0.0
            a.inflight = 0
        router.group_size = g
        res, _ = await run_all(router, args, sticky=True)
        okk = [r for r in res if r.success]
        tp = sum(r.prompt_tokens for r in okk)
        cc = sum(r.cached_tokens for r in okk)
        rate = cc / tp * 100 if tp else 0.0
        toks = [a.prompt_tokens + a.completion_tokens for a in accounts]
        share = max(toks) / max(sum(toks), 1) * 100 if toks else 0.0
        print(f"  group={g}/{len(accounts)}: 缓存命中率={rate:5.2f}%   最热账号tokens占比={share:5.1f}%")
    print("\n  → group 越小缓存越高但越集中；group 越大越分散但缓存越低。")
    print("     生产：按「单 UID TPM 上限」选能承载该前缀 QPS 的最小 group。")


async def main():
    ap = argparse.ArgumentParser(description="百炼缓存命中率最大化最佳实践 Demo（GLM-5.2）")
    ap.add_argument("--sessions", type=int, default=12, help="会话数（默认 12）")
    ap.add_argument("--max-turns", type=int, default=6, help="每会话最大轮数（默认 6）")
    ap.add_argument("--concurrency", type=int, default=3, help="并发会话数（默认 3）")
    ap.add_argument("--max-tokens", type=int, default=400, help="单轮最大输出 tokens")
    ap.add_argument("--prefix-units", type=int, default=40, help="稳定前缀知识条目数（控制前缀长度）")
    ap.add_argument("--ramp-batch", type=int, default=2, help="平滑爬坡：每启动几个会话暂停一次")
    ap.add_argument("--ramp-gap", type=float, default=1.5, help="平滑爬坡：每波暂停秒数")
    ap.add_argument("--cache-target", type=float, default=30.0, help="缓存命中率验收目标%%")
    ap.add_argument("--enable-thinking", action="store_true")
    ap.add_argument("--reasoning-effort", choices=["high", "max"], default="high")
    ap.add_argument("--compare", action="store_true", help="额外跑朴素轮询基线做对比")
    ap.add_argument("--group-size", type=int, default=1,
                    help="有界扇出：每个前缀路由到的账号组大小（1=最大缓存局部性，n=完全打散）")
    ap.add_argument("--sweep-groups", action="store_true",
                    help="扫描 group-size=1..n，展示缓存命中率与 TPM 分散度的平衡")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=str, default=None, help="报告保存路径")
    args = ap.parse_args()

    accounts = load_accounts()
    print(f"{'=' * 66}")
    print("百炼缓存命中率最大化 · 最佳实践 Demo")
    print(f"{'=' * 66}")
    print(f"  Model      : {MODEL}")
    print(f"  Accounts   : {[a.uid for a in accounts]}（{len(accounts)} 个）")
    print(f"  Sessions   : {args.sessions}（每会话 1~{args.max_turns} 轮），并发 {args.concurrency}")
    print(f"  最佳实践    : 缓存亲和路由 + 会话粘性 + 稳定前缀前置 + 平滑爬坡 + 429分类退避")
    print(f"{'=' * 66}\n")

    router = CacheAffinityRouter(accounts, group_size=args.group_size)
    if args.sweep_groups:
        await sweep_groups(router, accounts, args)
        return

    # 最佳实践跑：sticky=True（缓存亲和 + 会话粘性）
    print(f"🚀 [最佳实践] 缓存亲和 + 会话粘性（group-size={args.group_size}）运行中...")
    results, duration = await run_all(router, args, sticky=True)
    ok = sum(1 for r in results if r.success)
    print(f"✅ 完成：成功 {ok}/{len(results)} 轮，耗时 {duration:.1f}s\n")
    report = build_report(results, duration, accounts, args.cache_target)
    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n📄 报告已保存: {args.output}")

    # 对照跑：sticky=False（朴素打散），仅比总命中率
    if args.compare:
        for a in accounts:
            a.req_ok = a.req_429 = a.prompt_tokens = a.cached_tokens = a.completion_tokens = 0
            a.cooldown_until = 0.0
        print(f"\n{'=' * 66}\n🔁 [对照基线] 朴素打散（无亲和/无粘性）运行中...\n{'=' * 66}")
        base_results, base_dur = await run_all(router, args, sticky=False)
        bok = [r for r in base_results if r.success]
        bp = sum(r.prompt_tokens for r in bok)
        bc = sum(r.cached_tokens for r in bok)
        base_rate = bc / bp * 100 if bp else 0.0
        best_ok = [r for r in results if r.success]
        best_rate = (sum(r.cached_tokens for r in best_ok) /
                     max(sum(r.prompt_tokens for r in best_ok), 1) * 100)
        print(f"\n>>> 缓存命中率对比：朴素打散 {base_rate:.2f}%  →  最佳实践 {best_rate:.2f}%"
              f"（+{best_rate - base_rate:.2f} 个百分点）")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[中断] 用户取消")
