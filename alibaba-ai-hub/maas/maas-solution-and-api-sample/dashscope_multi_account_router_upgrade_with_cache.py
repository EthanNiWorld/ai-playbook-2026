"""
DashScope 多账号路由器 · 缓存亲和升级版
========================================

对比两种路由策略在"多账号聚合"场景下的缓存命中率与 TPM 分布：

  1. baseline  = 打散路由（random）—— 原始多账号负载均衡的做法
                 同一前缀被随机分到不同 key，缓存各自冷启动，命中率被稀释
  2. affinity  = 缓存亲和路由（一致性哈希）—— 升级做法
                 相同前缀锁定同一 key，缓存持续保温，命中率提升

缓存命中率如何度量
------------------
百炼 Qwen 商业模型（qwen-plus 等）默认开启"上下文缓存"，OpenAI 兼容接口的
usage 中返回 prompt_tokens_details.cached_tokens。
命中率 = sum(cached_tokens) / sum(prompt_tokens)

关键前提
--------
- 缓存绑定在 workspace/账号 维度，跨 key 不共享 —— 这正是打散路由的代价来源
- 前缀需足够长（>1K token）且逐 token 稳定，才能进入缓存
- 稳定内容（system/知识块）前置，动态内容（用户问题）后置

用法
----
  python dashscope_multi_account_router_upgrade_with_cache.py

需要环境变量（已在项目 .env 中）：
  DASHSCOPE_API_KEY_CN_TEST        + DASHSCOPE_API_KEY_CN_URL
  DASHSCOPE_API_KEY_INTL_BJ_TEST   + DASHSCOPE_API_KEY_INTL_BJ_TEST_URL
"""

import os
import time
import json
import hashlib
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional

from openai import OpenAI

# ---------------------------------------------------------------------------
# 手动加载 .env（本文件位于 alibaba-ai-hub/maas/api-sample/，向上 3 级到根目录）
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

MODEL = "qwen-plus"
MAX_TOKENS = 20          # 限制输出，聚焦输入缓存对比，控制成本
TEMPERATURE = 0.0
REPEAT_PER_PREFIX = 6    # 每个前缀重复请求次数（首次 miss，后续应命中）
REQUEST_GAP = 0.4        # 请求间隔（秒），给上下文缓存落盘时间


# ---------------------------------------------------------------------------
# 账号
# ---------------------------------------------------------------------------
@dataclass
class Account:
    uid: str
    api_key: str
    base_url: str
    client: OpenAI = field(default=None, repr=False)
    # 运行时统计
    req_count: int = 0
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0

    def reset(self):
        self.req_count = 0
        self.prompt_tokens = 0
        self.cached_tokens = 0
        self.completion_tokens = 0


def load_two_accounts() -> List[Account]:
    specs = [
        ("CN_TEST", "DASHSCOPE_API_KEY_CN_TEST", "DASHSCOPE_API_KEY_CN_URL"),
        ("INTL_BJ_TEST", "DASHSCOPE_API_KEY_INTL_BJ_TEST", "DASHSCOPE_API_KEY_INTL_BJ_TEST_URL"),
    ]
    accounts = []
    for uid, key_env, url_env in specs:
        key = os.getenv(key_env)
        url = os.getenv(url_env)
        if not key or not url:
            raise ValueError(f"缺少环境变量 {key_env} 或 {url_env}")
        acc = Account(uid=uid, api_key=key, base_url=url)
        acc.client = OpenAI(api_key=key, base_url=url, max_retries=0, timeout=60.0)
        accounts.append(acc)
    return accounts


# ---------------------------------------------------------------------------
# Workload：长稳定前缀（system）+ 短动态问题（user）
# ---------------------------------------------------------------------------
def _long_system(theme: str, rules: List[str], salt: str) -> str:
    """构造一个足够长（>1K token）且稳定的 system prompt。
    salt 用于隔离不同实验轮次的缓存，放在开头且同一轮内固定。"""
    header = (
        f"[实验批次:{salt}]\n"
        f"你是一个专业的{theme}智能助手。请严格遵循以下工作规范与知识库作答，"
        f"回答需专业、准确、简洁，禁止编造，遇到不确定信息应明确说明。\n\n"
        f"===== 工作规范 =====\n"
    )
    body = []
    for i, r in enumerate(rules, 1):
        # 每条规则重复展开，凑够前缀长度，模拟真实的长 system + 知识块
        body.append(
            f"{i}. {r} 该条规范适用于所有相关业务场景，处理时须核对上下文、"
            f"确认用户意图、给出可执行建议，并在必要时提示风险与合规要求。"
        )
    kb = "\n".join(f"- 知识条目 K{j}：{theme}领域标准操作流程第 {j} 项要点说明。" for j in range(1, 21))
    return header + "\n".join(body) + "\n\n===== 领域知识库 =====\n" + kb + "\n\n请基于以上规范与知识库回答用户问题。"


def build_prefixes(salt: str) -> List[Dict[str, str]]:
    themes = [
        ("金融客服", ["核实账户身份后再提供敏感信息", "涉及转账须二次确认", "利率以官方公告为准", "投诉须记录工单编号"]),
        ("医疗健康问答", ["不提供确诊结论只做科普", "急症建议立即就医", "用药须遵医嘱", "隐私信息严格保密"]),
        ("法律咨询", ["仅提供一般性法律信息", "重大纠纷建议咨询执业律师", "引用法条须注明出处", "不代替正式法律意见"]),
        ("电商导购", ["根据预算与需求推荐", "价格以下单页为准", "促销规则须明确告知", "支持七天无理由退换"]),
    ]
    prefixes = []
    for name, rules in themes:
        prefixes.append({"name": name, "system": _long_system(name, rules, salt)})
    return prefixes


QUESTIONS = [
    "请用一句话说明你的核心职责。",
    "如果用户情绪激动，你会怎么处理？",
    "遇到超出你知识范围的问题该如何应对？",
    "请给出一条最重要的注意事项。",
    "如何确保回答的合规性？",
]


def build_tasks(salt: str) -> List[Dict[str, Any]]:
    """生成任务列表：按前缀分组连续发送（P0×N, P1×N, ...）。
    分组连续 + 全局 round-robin 能真实体现"同一前缀被打散到多个 key"的代价，
    避免交错顺序在偶数 key 下产生的亲和假象。"""
    prefixes = build_prefixes(salt)
    tasks = []
    for p in prefixes:
        for r in range(REPEAT_PER_PREFIX):
            q = QUESTIONS[r % len(QUESTIONS)]
            tasks.append({
                "prefix_key": p["name"],
                "messages": [
                    {"role": "system", "content": p["system"]},
                    {"role": "user", "content": f"{q}（第{r+1}轮）"},
                ],
            })
    return tasks


# ---------------------------------------------------------------------------
# 路由策略
# ---------------------------------------------------------------------------
def router_round_robin() -> Callable[[Dict, List[Account]], Account]:
    """打散路由：全局轮询。配合"同前缀连续发送"，同一前缀会被轮流打到不同 key，
    每个 key 都要为该前缀各自冷启动缓存 —— 这就是原始负载均衡对缓存的伤害。"""
    state = {"i": 0}
    def _pick(task, accounts):
        acc = accounts[state["i"] % len(accounts)]
        state["i"] += 1
        return acc
    return _pick


def router_random(rng: random.Random) -> Callable[[Dict, List[Account]], Account]:
    """打散路由：完全随机（模拟原始负载均衡对缓存的伤害）"""
    def _pick(task, accounts):
        return rng.choice(accounts)
    return _pick


def router_cache_affinity() -> Callable[[Dict, List[Account]], Account]:
    """缓存亲和路由：按前缀指纹一致性哈希，同前缀锁定同 key"""
    def _pick(task, accounts):
        h = hashlib.md5(task["prefix_key"].encode("utf-8")).hexdigest()
        idx = int(h, 16) % len(accounts)
        return accounts[idx]
    return _pick


# ---------------------------------------------------------------------------
# 单请求调用 + usage 解析
# ---------------------------------------------------------------------------
def _extract_cached(usage) -> int:
    details = getattr(usage, "prompt_tokens_details", None)
    if details is None:
        return 0
    if isinstance(details, dict):
        return int(details.get("cached_tokens", 0) or 0)
    return int(getattr(details, "cached_tokens", 0) or 0)


def call_once(acc: Account, messages: List[Dict[str, str]], debug: bool = False) -> Dict[str, Any]:
    resp = acc.client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    usage = resp.usage
    pt = usage.prompt_tokens
    ct = usage.completion_tokens
    cached = _extract_cached(usage)

    if debug:
        try:
            print("  [debug] 原始 usage:", json.dumps(usage.model_dump(), ensure_ascii=False))
        except Exception:
            print("  [debug] 原始 usage:", usage)

    acc.req_count += 1
    acc.prompt_tokens += pt
    acc.cached_tokens += cached
    acc.completion_tokens += ct
    return {"prompt_tokens": pt, "cached_tokens": cached, "completion_tokens": ct}


# ---------------------------------------------------------------------------
# 实验
# ---------------------------------------------------------------------------
def run_experiment(name: str, accounts: List[Account], picker: Callable, salt: str) -> Dict[str, Any]:
    for a in accounts:
        a.reset()
    tasks = build_tasks(salt)

    print(f"\n{'='*66}\n[{name}] 开始：{len(tasks)} 请求，2 账号，模型={MODEL}\n{'='*66}")
    api_elapsed = 0.0   # 纯 API 耗时（不含请求间隔），用于算等效 TPM
    start = time.time()
    first = True
    for i, task in enumerate(tasks, 1):
        acc = picker(task, accounts)
        try:
            t0 = time.time()
            r = call_once(acc, task["messages"], debug=first)
            api_elapsed += time.time() - t0
            first = False
            hit = "命中" if r["cached_tokens"] > 0 else "未命中"
            print(f"  #{i:02d} 前缀={task['prefix_key']:<8} → {acc.uid:<12} "
                  f"prompt={r['prompt_tokens']:<5} cached={r['cached_tokens']:<5} [{hit}]")
        except Exception as e:
            print(f"  #{i:02d} 前缀={task['prefix_key']:<8} → {acc.uid:<12} [错误] {e}")
        time.sleep(REQUEST_GAP)
    elapsed = time.time() - start

    total_prompt = sum(a.prompt_tokens for a in accounts)
    total_cached = sum(a.cached_tokens for a in accounts)
    total_completion = sum(a.completion_tokens for a in accounts)
    total_tokens = total_prompt + total_completion
    hit_rate = (total_cached / total_prompt * 100) if total_prompt else 0.0
    eff_tpm = total_tokens / (api_elapsed / 60) if api_elapsed > 0 else 0

    return {
        "name": name,
        "elapsed": elapsed,
        "total_prompt": total_prompt,
        "total_cached": total_cached,
        "total_completion": total_completion,
        "total_tokens": total_tokens,
        "hit_rate": hit_rate,
        "eff_tpm": eff_tpm,
        "per_account": [
            {"uid": a.uid, "req": a.req_count, "prompt": a.prompt_tokens,
             "cached": a.cached_tokens, "tokens": a.prompt_tokens + a.completion_tokens}
            for a in accounts
        ],
    }


def print_summary(baseline: Dict, affinity: Dict):
    print(f"\n\n{'#'*66}\n# 对比结果\n{'#'*66}")
    rows = [
        ("策略", baseline["name"], affinity["name"]),
        ("耗时(s)", f"{baseline['elapsed']:.1f}", f"{affinity['elapsed']:.1f}"),
        ("总 prompt tokens", baseline["total_prompt"], affinity["total_prompt"]),
        ("其中缓存命中 tokens", baseline["total_cached"], affinity["total_cached"]),
        ("缓存命中率", f"{baseline['hit_rate']:.1f}%", f"{affinity['hit_rate']:.1f}%"),
        ("总 tokens", baseline["total_tokens"], affinity["total_tokens"]),
        ("等效 TPM", f"{baseline['eff_tpm']:.0f}", f"{affinity['eff_tpm']:.0f}"),
    ]
    print(f"\n{'指标':<22}{'baseline(打散)':<22}{'affinity(亲和)':<22}")
    print("-" * 66)
    for label, b, a in rows:
        print(f"{label:<22}{str(b):<22}{str(a):<22}")

    print("\n各账号 TPM/请求分布：")
    print(f"{'账号':<16}{'baseline 请求/tokens':<28}{'affinity 请求/tokens':<28}")
    print("-" * 66)
    b_map = {x["uid"]: x for x in baseline["per_account"]}
    a_map = {x["uid"]: x for x in affinity["per_account"]}
    for uid in b_map:
        b, a = b_map[uid], a_map[uid]
        b_cell = "{} / {}".format(b["req"], b["tokens"])
        a_cell = "{} / {}".format(a["req"], a["tokens"])
        print("{:<16}{:<28}{:<28}".format(uid, b_cell, a_cell))

    delta = affinity["hit_rate"] - baseline["hit_rate"]
    print(f"\n>>> 缓存命中率提升：{baseline['hit_rate']:.1f}% → {affinity['hit_rate']:.1f}%（+{delta:.1f} 个百分点）")


def main():
    accounts = load_two_accounts()
    print(f"已加载账号：{[a.uid for a in accounts]}")

    ts = int(time.time())
    # 两轮用不同 salt，保证 affinity 轮不会命中 baseline 轮遗留缓存，对比公平
    baseline = run_experiment(
        "baseline(打散/round-robin)", accounts,
        router_round_robin(), salt=f"BASE-{ts}"
    )
    time.sleep(2)
    affinity = run_experiment(
        "affinity(缓存亲和/一致性哈希)", accounts,
        router_cache_affinity(), salt=f"AFF-{ts}"
    )

    print_summary(baseline, affinity)


if __name__ == "__main__":
    main()
