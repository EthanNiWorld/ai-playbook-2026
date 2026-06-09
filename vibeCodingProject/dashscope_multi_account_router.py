"""
DashScope 多账号负载均衡路由器
==============================

功能
----
- 多账号轮询/加权调度
- 429 限流自动熔断与恢复
- 指数退避重试
- 异步并发安全
- 实时用量统计

配置
----
通过环境变量配置账号（推荐 3 个起步验证），格式：
  DASHSCOPE_ACCOUNT_1_KEY=sk-xxx
  DASHSCOPE_ACCOUNT_1_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
  DASHSCOPE_ACCOUNT_1_WEIGHT=1

  DASHSCOPE_ACCOUNT_2_KEY=sk-yyy
  DASHSCOPE_ACCOUNT_2_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
  DASHSCOPE_ACCOUNT_2_WEIGHT=1

  DASHSCOPE_ACCOUNT_3_KEY=sk-zzz
  DASHSCOPE_ACCOUNT_3_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
  DASHSCOPE_ACCOUNT_3_WEIGHT=1

运行模式
--------
  python dashscope_multi_account_router.py            # 真实调用，需配置上述环境变量
  python dashscope_multi_account_router.py --dry-run  # Mock 模式，无需真实 Key，验证路由逻辑

依赖
----
  pip install openai

参考文档
--------
- 百炼限流说明: https://www.alibabacloud.com/help/en/model-studio/rate-limit
- OpenAI SDK: https://github.com/openai/openai-python
"""

import os
import time
import random
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from collections import defaultdict

import httpx
from openai import AsyncOpenAI, APIStatusError

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dashscope_router")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Account:
    """单个百炼账号配置"""
    uid: str
    api_key: str
    base_url: str
    weight: int = 1

    # 运行时状态（由 Router 维护）
    cooldown_until: float = field(default=0.0, repr=False)
    success_count: int = field(default=0, repr=False)
    error_count: int = field(default=0, repr=False)
    total_tokens: int = field(default=0, repr=False)

    @property
    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    def cooldown(self, seconds: float = 70):
        """标记账号进入冷却期（默认 70s，官方说 1 分钟恢复，留缓冲）"""
        self.cooldown_until = time.time() + seconds
        logger.warning(f"[熔断] 账号 {self.uid} 进入冷却期 {seconds}s")

    def record_success(self, tokens: int = 0):
        self.success_count += 1
        self.total_tokens += tokens

    def record_error(self):
        self.error_count += 1


# ---------------------------------------------------------------------------
# 核心路由器
# ---------------------------------------------------------------------------
class DashScopeRouter:
    """
    多账号负载均衡路由器

    调度策略:
    - weighted_round_robin: 按权重轮询（默认）
    - least_loaded: 优先选择成功数最少的账号
    - random: 纯随机
    """

    def __init__(
        self,
        accounts: List[Account],
        strategy: str = "weighted_round_robin",
        max_retries: int = 3,
        cooldown_seconds: float = 70.0,
        default_model: str = "qwen-plus",
        max_connections: int = 1000,
        max_keepalive: int = 200,
        request_timeout: float = 120.0,
    ):
        self.accounts = accounts
        self.strategy = strategy
        self.max_retries = max_retries
        self.cooldown_seconds = cooldown_seconds
        self.default_model = default_model

        # 加权轮询游标
        self._wrr_index = 0
        self._wrr_counter = 0
        self._lock = asyncio.Lock()

        # 统计
        self._global_requests = 0
        self._global_errors = 0

        # 高并发 httpx 连接池 + 复用 AsyncOpenAI 客户端
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
        )
        timeout = httpx.Timeout(request_timeout, connect=10.0)
        self._clients: Dict[str, AsyncOpenAI] = {}
        for acc in accounts:
            http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
            self._clients[acc.uid] = AsyncOpenAI(
                api_key=acc.api_key,
                base_url=acc.base_url,
                http_client=http_client,
                max_retries=0,  # 重试逻辑交给 router 控制
            )

        logger.info(
            f"[初始化] 加载 {len(accounts)} 个账号，策略={strategy}，"
            f"冷却={cooldown_seconds}s，最大重试={max_retries}，"
            f"max_connections={max_connections}、keepalive={max_keepalive}"
        )

    # --- 账号选择 -----------------------------------------------------------

    def _available_accounts(self) -> List[Account]:
        return [a for a in self.accounts if a.is_available]

    def _select_weighted_round_robin(self, available: List[Account]) -> Optional[Account]:
        if not available:
            return None
        total_weight = sum(a.weight for a in available)
        idx = self._wrr_index % total_weight
        cumulative = 0
        for acc in available:
            cumulative += acc.weight
            if idx < cumulative:
                self._wrr_index = (self._wrr_index + 1) % total_weight
                return acc
        return available[-1]

    def _select_least_loaded(self, available: List[Account]) -> Optional[Account]:
        if not available:
            return None
        return min(available, key=lambda a: a.success_count + a.error_count)

    def _select_random(self, available: List[Account]) -> Optional[Account]:
        if not available:
            return None
        return random.choice(available)

    def _select_account(self) -> Optional[Account]:
        available = self._available_accounts()
        if not available:
            return None

        if self.strategy == "weighted_round_robin":
            return self._select_weighted_round_robin(available)
        elif self.strategy == "least_loaded":
            return self._select_least_loaded(available)
        elif self.strategy == "random":
            return self._select_random(available)
        else:
            return self._select_weighted_round_robin(available)

    # --- 核心调用 -----------------------------------------------------------

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        发送 Chat Completion 请求，自动处理多账号调度与限流重试

        返回格式:
        {
            "success": bool,
            "content": str | None,
            "model": str,
            "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
            "account_uid": str,
            "latency_ms": float,
            "error": str | None,
        }
        """
        model = model or self.default_model
        last_error = None

        for attempt in range(self.max_retries):
            account = self._select_account()
            if account is None:
                # 所有账号都在冷却，等一会再试
                wait = min(2 ** attempt, 30)
                logger.warning(f"[重试 {attempt+1}/{self.max_retries}] 所有账号冷却中，等待 {wait}s")
                await asyncio.sleep(wait)
                continue

            client = self._clients[account.uid]

            start = time.perf_counter()
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                latency_ms = (time.perf_counter() - start) * 1000

                content = response.choices[0].message.content if response.choices else ""
                usage = response.usage
                total_tokens = usage.total_tokens if usage else 0

                account.record_success(total_tokens)
                self._global_requests += 1

                logger.info(
                    f"[成功] 账号={account.uid} 模型={model} "
                    f"延迟={latency_ms:.1f}ms tokens={total_tokens}"
                )

                return {
                    "success": True,
                    "content": content,
                    "model": model,
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens if usage else 0,
                        "completion_tokens": usage.completion_tokens if usage else 0,
                        "total_tokens": total_tokens,
                    },
                    "account_uid": account.uid,
                    "latency_ms": latency_ms,
                    "error": None,
                }

            except APIStatusError as e:
                latency_ms = (time.perf_counter() - start) * 1000
                account.record_error()
                self._global_errors += 1
                last_error = f"APIError {e.status_code}: {e.message}"

                if e.status_code == 429:
                    # 限流 -> 熔断该账号，立刻重试其他账号
                    account.cooldown(self.cooldown_seconds)
                    logger.warning(
                        f"[限流] 账号={account.uid} 429 -> 熔断 "
                        f"{self.cooldown_seconds}s，立即重试其他账号"
                    )
                    continue  # 不 sleep，直接换账号
                else:
                    # 其他错误 -> 指数退避
                    wait = min(2 ** attempt, 30)
                    logger.error(
                        f"[错误] 账号={account.uid} 状态码={e.status_code} "
                        f"错误={e.message}，{wait}s 后重试"
                    )
                    await asyncio.sleep(wait)

            except Exception as e:
                latency_ms = (time.perf_counter() - start) * 1000
                account.record_error()
                self._global_errors += 1
                last_error = str(e)
                wait = min(2 ** attempt, 30)
                logger.error(f"[异常] 账号={account.uid} {e}，{wait}s 后重试")
                await asyncio.sleep(wait)

        # 所有重试耗尽
        logger.error(f"[失败] 所有账号重试耗尽，最后错误: {last_error}")
        return {
            "success": False,
            "content": None,
            "model": model,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "account_uid": None,
            "latency_ms": 0,
            "error": last_error,
        }

    # --- 批量并发调用 -------------------------------------------------------

    async def batch_chat(
        self,
        tasks: List[List[Dict[str, str]]],
        model: Optional[str] = None,
        concurrency: int = 10,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        批量并发调用，控制并发数防止瞬间打满所有账号

        tasks: 每个元素是一组 messages，如 [[{"role":"user","content":"hello"}], ...]
        concurrency: 最大并发数
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _wrapped(messages):
            async with semaphore:
                return await self.chat_completion(messages, model=model, **kwargs)

        return await asyncio.gather(*[_wrapped(m) for m in tasks])

    # --- 统计信息 -----------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """返回各账号及全局统计"""
        account_stats = []
        for a in self.accounts:
            account_stats.append({
                "uid": a.uid,
                "available": a.is_available,
                "cooldown_remaining": max(0, a.cooldown_until - time.time()),
                "success_count": a.success_count,
                "error_count": a.error_count,
                "total_tokens": a.total_tokens,
            })
        return {
            "global_requests": self._global_requests,
            "global_errors": self._global_errors,
            "accounts": account_stats,
        }

    def print_stats(self):
        """打印统计到控制台"""
        stats = self.stats()
        print("\n" + "=" * 60)
        print("DashScope 多账号路由统计")
        print("=" * 60)
        print(f"总请求: {stats['global_requests']}  总错误: {stats['global_errors']}")
        print("-" * 60)
        print(f"{'账号':<12} {'可用':<6} {'冷却剩余':<10} {'成功':<8} {'失败':<8} {'Tokens':<10}")
        for a in stats["accounts"]:
            status = "是" if a["available"] else "否"
            cd = f"{a['cooldown_remaining']:.0f}s" if a["cooldown_remaining"] > 0 else "-"
            print(
                f"{a['uid']:<12} {status:<6} {cd:<10} "
                f"{a['success_count']:<8} {a['error_count']:<8} {a['total_tokens']:<10}"
            )
        print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# 从环境变量加载账号配置
# ---------------------------------------------------------------------------
def load_accounts_from_env() -> List[Account]:
    """
    读取环境变量中的账号配置，格式:
      DASHSCOPE_ACCOUNT_{N}_KEY=sk-xxx
      DASHSCOPE_ACCOUNT_{N}_BASE_URL=...
      DASHSCOPE_ACCOUNT_{N}_WEIGHT=1  (可选，默认1)
    """
    accounts = []
    index = 1
    while True:
        key = os.getenv(f"DASHSCOPE_ACCOUNT_{index}_KEY")
        if not key:
            break
        base_url = os.getenv(
            f"DASHSCOPE_ACCOUNT_{index}_BASE_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        weight = int(os.getenv(f"DASHSCOPE_ACCOUNT_{index}_WEIGHT", "1"))
        accounts.append(
            Account(uid=f"acc{index}", api_key=key, base_url=base_url, weight=weight)
        )
        index += 1

    if not accounts:
        raise ValueError(
            "未找到账号配置。请设置环境变量:\n"
            "  DASHSCOPE_ACCOUNT_1_KEY=sk-xxx\n"
            "  DASHSCOPE_ACCOUNT_1_BASE_URL=https://...\n"
            "  DASHSCOPE_ACCOUNT_2_KEY=sk-yyy\n"
            "  ..."
        )

    return accounts


# ---------------------------------------------------------------------------
# 演示 / 测试 - 真实调用模式
# ---------------------------------------------------------------------------
async def demo():
    """3 账号真实调用：并发发送多条请求，观察账号调度与限流熔断"""

    accounts = load_accounts_from_env()
    print(f"\n[demo] 加载到 {len(accounts)} 个账号: {[a.uid for a in accounts]}\n")

    router = DashScopeRouter(
        accounts=accounts,
        strategy="weighted_round_robin",
        cooldown_seconds=70.0,
    )

    # 3 账号测试规模：9 条请求，并发 3
    messages = [[{"role": "user", "content": f"你好，这是第 {i} 条测试消息"}] for i in range(1, 10)]

    print("开始 3 账号并发测试 (9 请求, 并发=3)...")
    results = await router.batch_chat(
        tasks=messages,
        model="qwen-plus",
        concurrency=3,
    )

    success = sum(1 for r in results if r["success"])
    failed = len(results) - success
    print(f"\n结果: 成功 {success} / 失败 {failed}")

    router.print_stats()

    for r in results:
        if r["success"]:
            print(f"\n示例响应 (账号={r['account_uid']}, 延迟={r['latency_ms']:.1f}ms):")
            print((r["content"] or "")[:200] + "...")
            break


# ---------------------------------------------------------------------------
# 演示 / 测试 - Mock 模式（无需真实 Key）
# ---------------------------------------------------------------------------
async def demo_dryrun():
    """
    Mock 模式：不发真实请求，验证路由器逻辑
    - 模拟 3 个账号
    - acc1 前 2 次返回 429 限流，之后正常
    - acc2 / acc3 全部正常
    """
    from unittest.mock import patch, AsyncMock, MagicMock
    import httpx

    accounts = [
        Account(uid="acc1", api_key="sk-mock1", base_url="https://mock.example.com", weight=1),
        Account(uid="acc2", api_key="sk-mock2", base_url="https://mock.example.com", weight=1),
        Account(uid="acc3", api_key="sk-mock3", base_url="https://mock.example.com", weight=1),
    ]
    router = DashScopeRouter(
        accounts=accounts,
        strategy="weighted_round_robin",
        cooldown_seconds=2.0,  # 测试用短冷却
        max_retries=5,
    )

    # 计数器：acc1 前 2 次返回 429
    call_count = {"acc1": 0}

    def make_response(uid: str, content: str):
        """构造一个模拟的 ChatCompletion 响应"""
        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 20
        usage.total_tokens = 30
        msg = MagicMock()
        msg.content = f"[mock from {uid}] {content}"
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage = usage
        return resp

    async def fake_create(self, *args, **kwargs):
        # self 是 AsyncOpenAI 实例，从 api_key 反查 uid
        uid_map = {a.api_key: a.uid for a in accounts}
        uid = uid_map.get(self._client.api_key, "unknown")
        if uid == "acc1" and call_count["acc1"] < 2:
            call_count["acc1"] += 1
            # 模拟 429 限流
            req = httpx.Request("POST", "https://mock.example.com/v1/chat/completions")
            resp = httpx.Response(429, request=req)
            raise APIStatusError(
                message="Mock rate limit (429)",
                response=resp,
                body={"error": {"message": "rate_limit_exceeded"}},
            )
        await asyncio.sleep(0.05)  # 模拟网络延迟
        return make_response(uid, kwargs.get("messages", [{}])[0].get("content", ""))

    print("\n[Mock 模式] 验证 3 账号路由器逻辑")
    print("  - acc1 前 2 次会触发 429，被熔断 2s")
    print("  - 期望：请求自动切到 acc2/acc3，无失败\n")

    messages = [[{"role": "user", "content": f"req-{i}"}] for i in range(1, 10)]

    with patch(
        "openai.resources.chat.completions.AsyncCompletions.create",
        new=fake_create,
    ):
        results = await router.batch_chat(tasks=messages, model="qwen-plus", concurrency=3)

    success = sum(1 for r in results if r["success"])
    failed = len(results) - success
    print(f"\n结果: 成功 {success} / 失败 {failed}")
    router.print_stats()

    # 打印每个账号承担的请求分布
    dist = {}
    for r in results:
        if r["success"]:
            dist[r["account_uid"]] = dist.get(r["account_uid"], 0) + 1
    print(f"账号分布: {dist}")


if __name__ == "__main__":
    import sys
    if "--dry-run" in sys.argv:
        asyncio.run(demo_dryrun())
    else:
        asyncio.run(demo())
