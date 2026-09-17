"""yundun-key（AI DeepSign 网关 / Anthropic 协议）kimi-k3 会话式负载基准

负载模型（对齐客户参考参数"平均 32k 输入和 300 输出"，CLI 可覆盖）：
  - 会话到达率匀速爬坡：--arrival-rate-start 0.08 → --arrival-rate-end 1.0
    （sessions/s，历时 --ramp-duration-seconds 600），之后保持 --hold-duration-seconds
  - 每会话轮数：avg=30.2 p50=25 p75=34 p90=47 p95=57（分段线性逆CDF采样）
  - 轮间隔(s)：avg=18.6 p50=4 p75=10 p90=35 p95=86（重尾：多数轮次 4s 内到达）
  - 初始上下文(tokens)：avg=28568.9 p50=21983 p95=74262.9 → 会话 system 块
  - 每轮新增输入(tokens)：avg=1352.6 p50=493 p95=4740
  - 每轮输出(tokens)：avg=345.8 p50=68 p95=1514（k3 always-thinking，输出含思考；
    max_tokens = 采样值×1.5 + 1024 思考配额，实际输出以 usage 为准）

测量指标：
  1. TPM：60s 滑动窗口 tokens/min 曲线（含缓存读，对齐平台配额口径）
     + 稳态均值 + 峰值；429 触发时刻的窗口 TPM 即实测上限
     429 → AIMD（到达率 ×0.75，无 429 窗口 ×1.15 恢复），收敛至可持续 TPM
  2. 缓存命中率：多轮会话天然前缀复用；预检自动探测
     - 隐式：相同请求重复 2 次，看 cache_read / prompt_tokens_details.cached_tokens
     - 显式：Anthropic cache_control(ephemeral)，看 cache_creation/cache_read
     命中率 = max(cache_read, cached) / (input + cache_creation + max(cache_read, cached))
  3. TTFT：流式首 token 双口径——ttft_any（首个 delta，含 thinking）
     与 ttft_text（首个正文 delta），P50/P95，并按轮次/输入规模分桶

安全阀：--token-budget（默认 12M tokens，达到即停止新会话并收尾）、
        --max-duration（默认 1200s 硬停）。

运行：
  python3 yundun_k3_session_bench.py --smoke           # 冒烟（~2min）
  python3 yundun_k3_session_bench.py                    # 参考参数全量
  python3 yundun_k3_session_bench.py --run-tag $(date +%Y%m%d)

端点与凭证（.env）：yundun-key（sk-ds. JWT）、yundun-url
"""
import argparse
import heapq
import itertools
import json
import os
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# 配置加载（复用仓库惯例：直接解析根 .env 并覆盖）
# ---------------------------------------------------------------------------
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "..", ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("yundun-key", "").strip()
BASE_URL = os.getenv("yundun-url", "").strip() or \
    "https://api-aideepsign.cn-hangzhou.aliyuncs.com/v1/messages"
MODEL = "kimi-k3"
HEADERS = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}

# ---------------------------------------------------------------------------
# 分段线性逆 CDF 采样器：'avg=30.2,p50=25,p75=34,p90=47,p95=57'
# 保证 p50/p75/p90/p95 精确命中；均值靠 p95→cap 外推段近似（重尾）
# ---------------------------------------------------------------------------
class SpecSampler:
    def __init__(self, spec, name, min_value=0.0):
        kv = {}
        for part in spec.split(","):
            k, _, v = part.partition("=")
            kv[k.strip()] = float(v.strip())
        if "p50" not in kv or "p95" not in kv:
            raise ValueError(f"{name}: spec 至少需要 p50 与 p95")
        p50, p95 = kv["p50"], kv["p95"]
        p75 = kv.get("p75", (p50 * p95) ** 0.5)
        p90 = kv.get("p90", (p75 * p95) ** 0.5)
        floor = max(min_value, kv.get("min", p50 * 0.25))
        cap = p95 * 2.0
        self.name, self.avg = name, kv.get("avg")
        self.knots = [(0.0, floor), (0.5, p50), (0.75, p75),
                      (0.90, p90), (0.95, p95), (1.0, cap)]

    def sample(self):
        u = random.random()
        ks = self.knots
        for i in range(len(ks) - 1):
            (u0, v0), (u1, v1) = ks[i], ks[i + 1]
            if u <= u1:
                return v0 + (v1 - v0) * (u - u0) / (u1 - u0)
        return ks[-1][1]


# ---------------------------------------------------------------------------
# 语料生成（随机模板 × 词表 → 每会话/每轮内容天然唯一，避免跨会话前缀撞车）
# ---------------------------------------------------------------------------
_VOCAB = ["分布式推理", "KDA 线性注意力", "Mooncake 分离式架构", "上下文缓存",
          "KV 状态管理", "专家并行", "MXFP4 量化", "前缀匹配", "滚动窗口统计",
          "首 token 延迟", "解码吞吐", "限流与配额", "灰度发布", "混沌工程",
          "服务网格", "数据分片", "一致性哈希", "背压控制", "熔断降级",
          "弹性伸缩", "冷启动优化", "亲和路由", "请求排队", "负载水位"]
_SENT = [
    "{a}与{b}的协同设计，直接决定了{c}的上限。",
    "在{a}场景中，{b}的引入可以显著改善{c}的表现。",
    "针对{c}问题，工程上通常采用以{a}为主、{b}为辅的组合方案。",
    "{a}的额外开销由{b}承担，从而缓解了{c}的压力。",
    "实践表明，{b}在不牺牲{c}的前提下，能将{a}降低一个量级。",
    "当{a}超过阈值时，系统自动触发{b}，以保护{c}不被击穿。",
    "{c}的可观测性依赖{a}埋点与{b}聚合管道的配合。",
    "灰度期间，{a}按批次放量，{b}实时回传{c}指标。",
    "若{a}与{b}配置失配，{c}将在高峰期率先恶化。",
    "{a}的收益需要在{b}约束下评估，否则{c}的结论不可靠。",
    "针对长尾请求，{a}配额需要与{b}隔离，避免{c}被饿死。",
    "{b}的引入使{a}的边际成本下降，但提高了{c}的复杂度。",
]
_QUESTIONS = [
    "上述资料中提到的核心指标有哪些？",
    "请概括资料的主要论点。",
    "资料中提到了哪些工程权衡？",
    "请总结资料里关于稳定性的要点。",
    "资料对成本优化有什么建议？",
    "列出资料中的三个关键结论。",
    "资料中描述的架构有什么特点？",
    "请用一句话总结资料主旨。",
    "资料中提到了哪些风险点？",
    "资料中的数据说明了什么趋势？",
]


def gen_filler(chars, salt=None):
    parts = []
    if salt:
        parts.append(f"[会话标识 {salt}] 以下为技术背景资料。\n")
    n = sum(len(p) for p in parts)
    while n < chars:
        s = random.choice(_SENT).format(a=random.choice(_VOCAB),
                                        b=random.choice(_VOCAB),
                                        c=random.choice(_VOCAB))
        parts.append(s)
        n += len(s)
    return "".join(parts)


# ---------------------------------------------------------------------------
# HTTP 层（thread-local Session；流式解析 usage + 双口径 TTFT）
# ---------------------------------------------------------------------------
_tls = threading.local()


def http():
    s = getattr(_tls, "s", None)
    if s is None:
        s = requests.Session()
        _tls.s = s
    return s


def usage_norm(u):
    """归一化 usage：兼容 Anthropic(cache_read) 与 DashScope(cached_tokens) 两种口径"""
    u = u or {}
    cached = ((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0
    cache_read = u.get("cache_read_input_tokens") or 0
    return {
        "in": u.get("input_tokens") or 0,
        "out": u.get("output_tokens") or 0,
        "cache_create": u.get("cache_creation_input_tokens") or 0,
        "cache_read": max(cache_read, cached),  # 两种口径互斥，取大者
        "out_est": u.get("output_tokens") is None,
    }


def nonstream(body, timeout=120):
    r = http().post(BASE_URL, headers=HEADERS, json=body, timeout=timeout)
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code,
                "code": "", "msg": r.text[:200], "usage": None}
    try:
        d = r.json()
    except ValueError:
        return {"ok": False, "status": r.status_code,
                "code": "BadJSON", "msg": r.text[:200], "usage": None}
    if "content" not in d:
        return {"ok": False, "status": r.status_code,
                "code": d.get("code", ""), "msg": str(d.get("message", ""))[:200],
                "usage": None}
    return {"ok": True, "status": 200, "usage": d.get("usage") or {}, "data": d}


def stream_call(body, timeout=240):
    """流式调用：返回 ok/ttft_any/ttft_text/wall/usage/text/错误信息"""
    out = {"ok": False, "ttft_any": None, "ttft_text": None, "wall": 0.0,
           "usage": {}, "text": "", "status": 0, "code": "", "msg": ""}
    t0 = time.time()
    try:
        r = http().post(BASE_URL, headers=HEADERS, json=body,
                        timeout=timeout, stream=True)
        out["status"] = r.status_code
        if r.status_code != 200:
            try:
                d = r.json()
                out["code"] = d.get("code") or (d.get("error") or {}).get("type", "")
                out["msg"] = str(d.get("message") or (d.get("error") or {}).get("message", ""))[:200]
            except ValueError:
                out["msg"] = r.text[:200]
            r.close()
            out["wall"] = (time.time() - t0) * 1000
            return out
        usage, texts = {}, []
        for raw in r.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            chunk = raw[5:].strip()
            if not chunk:
                continue
            try:
                evt = json.loads(chunk)
            except ValueError:
                continue
            t = evt.get("type")
            if t == "message_start":
                usage = dict(((evt.get("message") or {}).get("usage")) or {})
            elif t == "content_block_delta":
                d = evt.get("delta") or {}
                dt = d.get("type", "")
                if out["ttft_any"] is None and dt in ("thinking_delta", "text_delta"):
                    out["ttft_any"] = (time.time() - t0) * 1000
                if dt == "text_delta":
                    if out["ttft_text"] is None:
                        out["ttft_text"] = (time.time() - t0) * 1000
                    if d.get("text"):
                        texts.append(d["text"])
            elif t == "message_delta":
                u2 = evt.get("usage") or {}
                for k in ("output_tokens", "input_tokens",
                          "cache_read_input_tokens", "cache_creation_input_tokens"):
                    if u2.get(k) is not None:
                        usage[k] = u2[k]
            elif t == "error":
                e = evt.get("error") or {}
                out["code"] = e.get("type", "stream_error")
                out["msg"] = str(e.get("message", evt))[:200]
                break
        r.close()
        out["usage"] = usage
        out["text"] = "".join(texts)
        out["wall"] = (time.time() - t0) * 1000
        out["ok"] = out["code"] == ""  # 无流内错误即成功
    except requests.RequestException as e:
        out["code"] = type(e).__name__
        out["msg"] = str(e)[:200]
        out["wall"] = (time.time() - t0) * 1000
    return out


def is_rate_limit(res):
    if res.get("status") == 429:
        return True
    s = (str(res.get("code", "")) + str(res.get("msg", ""))).lower()
    return any(k in s for k in ("throttl", "rate limit", "ratelimit",
                                "请求过于频繁", "请求频率", "limit exceeded", "限流"))


# ---------------------------------------------------------------------------
# 会话状态机
# ---------------------------------------------------------------------------
class Session:
    def __init__(self, sid, cfg):
        self.sid = sid
        self.cfg = cfg
        self.rounds = max(1, int(round(cfg["rounds"].sample())))
        init_tokens = cfg["init"].sample()
        self.system_text = gen_filler(max(200, int(init_tokens / cfg["ratio"])),
                                      salt=uuid.uuid4().hex[:8])
        self.history = []
        self.round_idx = 0
        self.alive = True
        self.consec_429 = 0
        self.err_retries = 0

    def prepare_turn(self):
        tin = self.cfg["input"].sample()
        out_t = self.cfg["output"].sample()
        chars = max(80, int(tin / self.cfg["ratio"]))
        k = max(1, min(12, round(out_t / 120)))
        user = gen_filler(chars) + \
            f"\n\n[问题] 基于以上资料，用不超过{k}句话简要回答：{random.choice(_QUESTIONS)}"
        max_tokens = min(8192, int(out_t * 1.5 + 1024))
        body = {"model": MODEL, "max_tokens": max_tokens, "stream": True,
                "messages": self.history + [{"role": "user", "content": user}]}
        if self.cfg["cache_mode"] == "explicit":
            body["system"] = [{"type": "text", "text": self.system_text,
                               "cache_control": {"type": "ephemeral"}}]
        else:
            body["system"] = self.system_text
        return body, user


# ---------------------------------------------------------------------------
# 主基准器
# ---------------------------------------------------------------------------
class Bench:
    def __init__(self, args):
        self.args = args
        self.ratio = 0.7  # chars/token，标定后覆盖
        self.cache_mode = "none"
        self.t0 = time.time()
        self.events = []            # (fire_time_offset_s, seq, session)
        self.seq = itertools.count()
        self.sched_lock = threading.Lock()
        self.rec_lock = threading.Lock()
        self.records = []
        self.budget_used = 0
        self.spawned = 0
        self.done_sessions = 0
        self.aborted_sessions = 0
        self.active = 0
        self.mult = 1.0            # AIMD 到达率乘子
        self.last_429_count = 0
        self.first_429_at = None
        self.stopping = False
        self.next_arrival = 0.0
        self.max_event_time = 0.0

    # ---- 预检：标定 chars/token + 缓存模式探测 ----
    def preflight(self):
        print("\n========== 预检：标定 + 缓存探测 ==========")
        text = gen_filler(2000) + "\n\n[问题] 一句话回答：资料主题是什么？"
        r = nonstream({"model": MODEL, "max_tokens": 64,
                       "messages": [{"role": "user", "content": text}]})
        if not r["ok"]:
            print(f"❌ 标定请求失败: HTTP {r['status']} {r['code']} {r['msg']}")
            raise SystemExit(1)
        u = usage_norm(r["usage"])
        self.ratio = max(0.2, u["in"] / len(text))
        print(f"标定: {len(text)} 字符 → {u['in']} tokens（ratio≈{self.ratio:.3f} chars→tok: "
              f"{1 / self.ratio:.2f} tok/char）")

        sys_text = gen_filler(int(5000 / self.ratio), salt="cacheprobe")
        q = "一句话回答：资料主题是什么？"
        print("\n-- 探测 A: 隐式缓存（无 cache_control，重复 2 次）--")
        implicit_hit = False
        for i in range(2):
            rr = nonstream({"model": MODEL, "max_tokens": 64, "system": sys_text,
                            "messages": [{"role": "user", "content": q}]})
            uu = usage_norm(rr["usage"])
            print(f"   第{i + 1}次: in={uu['in']} cache_read={uu['cache_read']} "
                  f"cache_create={uu['cache_create']}")
            if i == 1 and (uu["cache_read"] > 0 or uu["cache_create"] > 0):
                implicit_hit = True
            time.sleep(1)

        print("\n-- 探测 B: 显式 cache_control(ephemeral)（重复 2 次）--")
        explicit_hit, explicit_err = False, ""
        for i in range(2):
            rr = nonstream({"model": MODEL, "max_tokens": 64,
                            "system": [{"type": "text", "text": sys_text,
                                        "cache_control": {"type": "ephemeral"}}],
                            "messages": [{"role": "user", "content": q}]})
            if not rr["ok"]:
                explicit_err = f"HTTP {rr['status']} {rr['code']} {rr['msg'][:80]}"
                print(f"   第{i + 1}次: ❌ {explicit_err}")
                break
            uu = usage_norm(rr["usage"])
            print(f"   第{i + 1}次: in={uu['in']} cache_read={uu['cache_read']} "
                  f"cache_create={uu['cache_create']}")
            if uu["cache_read"] > 0 or uu["cache_create"] > 0:
                explicit_hit = True
            time.sleep(1)

        if self.args.cache_mode != "auto":
            self.cache_mode = self.args.cache_mode
        elif explicit_hit:
            self.cache_mode = "explicit"
        elif implicit_hit:
            self.cache_mode = "implicit"
        else:
            self.cache_mode = "none"
        mode_note = {"explicit": "显式 cache_control 生效", "implicit": "隐式前缀缓存生效",
                     "none": "❌ 未观测到缓存行为（命中率为 0 属正常）"}.get(self.cache_mode, "")
        print(f"\n缓存模式决策: {self.cache_mode} — {mode_note}")

    # ---- 请求执行（线程池 worker） ----
    def fire_turn(self, s):
        try:
            cfg = {"rounds": self.cfg_rounds, "init": self.cfg_init,
                   "input": self.cfg_input, "output": self.cfg_output,
                   "ratio": self.ratio, "cache_mode": self.cache_mode}
            body, user_text = s.prepare_turn()
            res = stream_call(body)
            now = time.time() - self.t0
            u = usage_norm(res["usage"])
            if u["out_est"] and res["text"]:
                u["out"] = int(len(res["text"]) * self.ratio)
            quota = u["in"] + u["out"] + u["cache_create"] + u["cache_read"]
            rec = {"ts": now, "sid": s.sid, "round": s.round_idx + 1,
                   "ok": res["ok"], "rl": (not res["ok"]) and is_rate_limit(res),
                   "ttft_any": res["ttft_any"], "ttft_text": res["ttft_text"],
                   "wall": res["wall"], "in": u["in"], "out": u["out"],
                   "cache_read": u["cache_read"], "cache_create": u["cache_create"],
                   "quota": quota, "status": res["status"],
                   "code": res["code"], "msg": res["msg"]}
            with self.rec_lock:
                self.records.append(rec)
                self.budget_used += quota
                if rec["rl"]:
                    if self.first_429_at is None:
                        self.first_429_at = now
                        print(f"\n  🚨 首个限流 @t={now:.0f}s: {res['status']} "
                              f"[{res['code']}] {res['msg'][:100]}")

            if res["ok"]:
                a_text = (res["text"] or "").strip() or "（本轮输出被截断）"
                s.history.append({"role": "user", "content": user_text})
                s.history.append({"role": "assistant", "content": a_text})
                s.round_idx += 1
                s.consec_429 = 0
                s.err_retries = 0
                if s.round_idx >= s.rounds:
                    s.alive = False
                    with self.rec_lock:
                        self.done_sessions += 1
                else:
                    delay = max(0.5, self.cfg_interval.sample())
                    self.schedule(s, now + delay)
            elif rec["rl"]:
                s.consec_429 += 1
                self.mult = max(0.05, self.mult * 0.75)
                if s.consec_429 <= 6:
                    self.schedule(s, now + min(120, 5 * 2 ** s.consec_429))
                else:
                    s.alive = False
                    with self.rec_lock:
                        self.aborted_sessions += 1
            else:
                s.err_retries += 1
                if s.err_retries <= 2:
                    self.schedule(s, now + 3)
                else:
                    s.alive = False
                    with self.rec_lock:
                        self.aborted_sessions += 1
        except Exception as e:  # worker 内部兜底，避免线程静默死亡
            s.alive = False
            with self.rec_lock:
                self.aborted_sessions += 1
            print(f"  [worker 异常] session {s.sid}: {type(e).__name__}: {e}")
        finally:
            with self.sched_lock:
                self.active -= 1

    def schedule(self, s, t):
        if not s.alive or self.stopping:
            return
        with self.sched_lock:
            heapq.heappush(self.events, (t, next(self.seq), s))
            self.max_event_time = max(self.max_event_time, t)

    # ---- 主调度循环 ----
    def arrival_rate(self, t):
        a = self.args
        if t >= a.ramp_duration_seconds:
            return a.arrival_rate_end
        w = t / max(1e-9, a.ramp_duration_seconds)
        return a.arrival_rate_start + (a.arrival_rate_end - a.arrival_rate_start) * w

    def run(self):
        a = self.args
        self.cfg_rounds = SpecSampler(a.num_rounds, "rounds", min_value=1)
        self.cfg_init = SpecSampler(a.init_prompt_length, "init", min_value=500)
        self.cfg_input = SpecSampler(a.input_length, "input", min_value=50)
        self.cfg_output = SpecSampler(a.output_length, "output", min_value=30)
        self.cfg_interval = SpecSampler(a.turn_interval, "interval", min_value=0.5)

        print(f"\n========== 会话负载基准启动 ==========")
        print(f"到达率: {a.arrival_rate_start} → {a.arrival_rate_end} sessions/s"
              f"（{a.ramp_duration_seconds}s 匀速爬坡，稳态 {a.hold_duration_seconds}s）")
        print(f"负载规格: rounds={a.num_rounds}")
        print(f"          interval={a.turn_interval}")
        print(f"          init={a.init_prompt_length}")
        print(f"          input={a.input_length}")
        print(f"          output={a.output_length}")
        print(f"并发池 {a.concurrency} | token 预算 {a.token_budget / 1e6:.1f}M | "
              f"硬停 {a.max_duration}s | 缓存模式 {self.cache_mode}")

        pool = ThreadPoolExecutor(max_workers=a.concurrency)
        next_status = 60.0
        end_arrivals = a.ramp_duration_seconds + a.hold_duration_seconds
        while True:
            now = time.time() - self.t0
            if now >= next_status:
                self.status_line(now)
                if self.last_429_count == self.count_429():
                    self.mult = min(1.0, self.mult * 1.15)
                else:
                    self.last_429_count = self.count_429()
                next_status += 60

            budget_hit = self.budget_used >= a.token_budget
            if not self.stopping and (budget_hit or now >= end_arrivals
                                      or now >= a.max_duration):
                self.stopping = True
                reason = ("token 预算耗尽" if budget_hit else
                          "到达爬坡+稳态窗口结束" if now >= end_arrivals else "硬停时间到")
                print(f"\n[t={now:.0f}s] 停止新流量（{reason}），排空在途请求…")
                with self.sched_lock:
                    self.events.clear()

            if self.stopping:
                with self.sched_lock:
                    idle = not self.events and self.active == 0
                if idle:
                    break
            else:
                while self.next_arrival <= now:
                    if a.total_sessions and self.spawned >= a.total_sessions:
                        break
                    s = Session(self.spawned + 1,
                                {"rounds": self.cfg_rounds, "init": self.cfg_init,
                                 "input": self.cfg_input, "output": self.cfg_output,
                                 "ratio": self.ratio, "cache_mode": self.cache_mode})
                    self.spawned += 1
                    with self.sched_lock:
                        self.active += 1
                    pool.submit(self.fire_turn, s)
                    rate = max(1e-4, self.arrival_rate(now) * self.mult)
                    self.next_arrival = now + random.expovariate(rate)

            with self.sched_lock:
                due = []
                while self.events and self.events[0][0] <= now:
                    due.append(heapq.heappop(self.events)[2])
            for s in due:
                if s.alive and not self.stopping:
                    with self.sched_lock:
                        self.active += 1
                    pool.submit(self.fire_turn, s)
            time.sleep(0.2)

        pool.shutdown(wait=True)
        print(f"\n[t={time.time() - self.t0:.0f}s] 全部请求排空，测试结束。")
        self.report()

    def count_429(self):
        with self.rec_lock:
            return sum(1 for r in self.records if r["rl"])

    def status_line(self, now):
        with self.rec_lock:
            win = [r for r in self.records if now - 60 <= r["ts"] <= now]
            ok = [r for r in self.records if r["ok"]]
            n429 = sum(1 for r in self.records if r["rl"])
            budget = self.budget_used
        wquota = sum(r["quota"] for r in win)
        wcache = sum(r["cache_read"] for r in win)
        wden = sum(r["in"] + r["cache_read"] + r["cache_create"] for r in win)
        cache_pct = (wcache / wden * 100) if wden else 0.0
        print(f"[t={now:4.0f}s] 会话 {self.spawned}（完成 "
              f"{self.done_sessions}/中断 {self.aborted_sessions}） 在途 {self.active} | "
              f"窗口 {len(win)} req | TPM {wquota / 1e3:8.0f}k | "
              f"缓存 {cache_pct:4.1f}% | 429×{n429} | "
              f"预算 {budget / 1e6:.2f}M/{self.args.token_budget / 1e6:.0f}M")

    # ---- 报告 ----
    def report(self):
        a = self.args
        with self.rec_lock:
            recs = list(self.records)
        ok = [r for r in recs if r["ok"]]
        rl = [r for r in recs if r["rl"]]
        errs = [r for r in recs if not r["ok"] and not r["rl"]]
        dur = (recs[-1]["ts"] - recs[0]["ts"]) if recs else 0

        tot_in = sum(r["in"] for r in ok)
        tot_out = sum(r["out"] for r in ok)
        tot_cr = sum(r["cache_read"] for r in ok)
        tot_cc = sum(r["cache_create"] for r in ok)
        quota_all = sum(r["quota"] for r in ok)
        cache_rate = tot_cr / max(1, tot_in + tot_cr + tot_cc) * 100

        def pct(vals, q):
            if not vals:
                return None
            vs = sorted(vals)
            return vs[max(0, min(len(vs) - 1, int(q * len(vs))))]

        # 60s 窗口曲线
        if recs:
            wmax = int(max(r["ts"] for r in recs) // 60) + 1
        else:
            wmax = 0
        windows = []
        for w in range(wmax):
            wr = [r for r in recs if w * 60 <= r["ts"] < (w + 1) * 60]
            if not wr:
                continue
            wok = [r for r in wr if r["ok"]]
            wq = sum(r["quota"] for r in wok)
            wc = sum(r["cache_read"] for r in wok)
            wd = sum(r["in"] + r["cache_read"] + r["cache_create"] for r in wok)
            windows.append({
                "w": w + 1, "t0": w * 60, "reqs": len(wok),
                "tokens": wq, "tpm": wq,  # 每 60s 窗口 tokens 即 TPM
                "cache_pct": (wc / wd * 100) if wd else 0.0,
                "n429": sum(1 for r in wr if r["rl"]),
                "ttft_p50": pct([r["ttft_any"] for r in wok
                                 if r["ttft_any"] is not None], 0.5),
            })
        peak = max((w["tpm"] for w in windows), default=0)
        hold_windows = [w for w in windows
                        if w["t0"] >= a.ramp_duration_seconds]
        steady = (sum(w["tpm"] for w in hold_windows) / len(hold_windows)
                  if hold_windows else None)
        # 429 上限口径：首个 429 前后 2 个窗口的峰值
        ceiling = None
        if self.first_429_at is not None:
            near = [w for w in windows
                    if abs(w["t0"] + 30 - self.first_429_at) <= 150]
            ceiling = max((w["tpm"] for w in near), default=None)

        ttft_any = [r["ttft_any"] for r in ok if r["ttft_any"] is not None]
        ttft_text = [r["ttft_text"] for r in ok if r["ttft_text"] is not None]
        r1 = [r for r in ok if r["round"] == 1]
        r2 = [r for r in ok if r["round"] > 1]

        lines = []
        lines.append(f"# yundun-key（AI DeepSign）kimi-k3 会话式负载基准结果")
        lines.append(f"\n- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"- 端点: {BASE_URL}")
        lines.append(f"- 负载: 到达率 {a.arrival_rate_start}→{a.arrival_rate_end}/s "
                     f"（{a.ramp_duration_seconds}s 爬坡 + {a.hold_duration_seconds}s 稳态），"
                     f"会话 {self.spawned}（完成 {self.done_sessions}/中断 "
                     f"{self.aborted_sessions}/终止子截止 "
                     f"{max(0, self.spawned - self.done_sessions - self.aborted_sessions)}）")
        lines.append(f"- 请求: 成功 {len(ok)} | 限流 {len(rl)} | 其他错误 {len(errs)} | "
                     f"有效时长 {dur:.0f}s")
        lines.append(f"- tokens: 输入 {tot_in / 1e3:.1f}k + 输出 {tot_out / 1e3:.1f}k + "
                     f"缓存读 {tot_cr / 1e3:.1f}k + 缓存写 {tot_cc / 1e3:.1f}k "
                     f"= 配额口径 {quota_all / 1e6:.2f}M")
        lines.append(f"- 缓存模式: {self.cache_mode}（预检决定，可用 --cache-mode 覆盖）")

        lines.append("\n## TPM 结论")
        lines.append(f"- 峰值 60s 窗口 TPM: **{peak / 1e3:.0f}k**"
                     f"（≈{peak / 1e6:.2f}M）")
        if steady is not None:
            lines.append(f"- 稳态期（爬坡结束后）平均 TPM: {steady / 1e3:.0f}k"
                         f"（≈{steady / 1e6:.2f}M，{len(hold_windows)} 个窗口）")
        if ceiling is not None:
            lines.append(f"- 🚨 **实测 TPM 上限 ≈ {ceiling / 1e3:.0f}k（≈{ceiling / 1e6:.2f}M）**"
                         f"（首个 429 @t={self.first_429_at:.0f}s 前后窗口峰值；"
                         f"限流共 {len(rl)} 次）")
        elif rl:
            lines.append(f"- 限流 {len(rl)} 次但样本不足，上限待复测")
        else:
            lines.append(f"- 未触发限流；受 token 预算/时长约束，"
                         f"下限结论: TPM ≥ {peak / 1e3:.0f}k")

        lines.append("\n## 缓存命中率")
        lines.append(f"- 总体: **{cache_rate:.1f}%**"
                     f"（cache_read {tot_cr / 1e3:.1f}k / 计费输入基数 "
                     f"{(tot_in + tot_cr + tot_cc) / 1e3:.1f}k）")
        for label, grp in (("首轮（system 初始化）", r1), ("第 2 轮起（前缀复用）", r2)):
            if grp:
                g_cr = sum(r["cache_read"] for r in grp)
                g_den = sum(r["in"] + r["cache_read"] + r["cache_create"] for r in grp)
                lines.append(f"- {label}: {g_cr / max(1, g_den) * 100:.1f}%"
                             f"（{len(grp)} 请求）")
        per_round = {}
        for r in ok:
            per_round.setdefault(min(r["round"], 8), []).append(r)
        if per_round:
            lines.append("\n| 轮次 | 请求数 | 命中率 | 平均输入 tokens |")
            lines.append("|---|---|---|---|")
            for k in sorted(per_round):
                g = per_round[k]
                g_cr = sum(r["cache_read"] for r in g)
                g_den = sum(r["in"] + r["cache_read"] + r["cache_create"] for r in g)
                lines.append(f"| {'≥8' if k == 8 else k} | {len(g)} | "
                             f"{g_cr / max(1, g_den) * 100:.1f}% | "
                             f"{sum(r['in'] + r['cache_read'] for r in g) / len(g) / 1e3:.1f}k |")

        lines.append("\n## TTFT（流式首 token）")
        for label, vals in (("任意首 token（含 thinking）", ttft_any),
                            ("正文首 token（text_delta）", ttft_text)):
            if vals:
                lines.append(f"- {label}: n={len(vals)} | "
                             f"P50 **{pct(vals, 0.5):.0f}ms** | "
                             f"P90 {pct(vals, 0.9):.0f}ms | "
                             f"P95 {pct(vals, 0.95):.0f}ms | "
                             f"max {max(vals):.0f}ms")
        for label, grp in (("首轮（初始上下文 ~28k）", r1), ("后续轮（增量输入）", r2)):
            vals = [r["ttft_any"] for r in grp if r["ttft_any"] is not None]
            if vals:
                lines.append(f"- {label} 任意首 token: P50 {pct(vals, 0.5):.0f}ms | "
                             f"P95 {pct(vals, 0.95):.0f}ms")

        lines.append("\n## 60s 窗口曲线")
        lines.append("\n| 窗口 | t(s) | 成功req | TPM | 缓存% | 429 | TTFT P50(ms) |")
        lines.append("|---|---|---|---|---|---|---|")
        for w in windows:
            ttft_cell = (f"{w['ttft_p50']:.0f}" if w["ttft_p50"] is not None else "—")
            lines.append(f"| {w['w']} | {w['t0']}-{w['t0'] + 60} | {w['reqs']} | "
                         f"{w['tpm'] / 1e3:.0f}k | {w['cache_pct']:.0f}% | "
                         f"{w['n429']} | {ttft_cell} |")

        if errs:
            lines.append("\n## 错误样例（非限流）")
            for r in errs[:5]:
                lines.append(f"- HTTP {r['status']} [{r['code']}] {r['msg'][:120]}")

        text = "\n".join(lines)
        print("\n" + "=" * 24 + " 结果报告 " + "=" * 24)
        print(text)
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 f"yundun_k3_session_bench_results_{a.run_tag}.md")
        with open(out_path, "w") as f:
            f.write(text + "\n")
        print(f"\n结果已写入: {out_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--total-sessions", type=int, default=0,
                    help="会话数上限（0=不限制，由爬坡/稳态/预算控制）")
    ap.add_argument("--arrival-rate-start", type=float, default=0.08)
    ap.add_argument("--arrival-rate-end", type=float, default=1.0)
    ap.add_argument("--ramp-duration-seconds", type=int, default=600)
    ap.add_argument("--hold-duration-seconds", type=int, default=300)
    ap.add_argument("--num-rounds",
                    default="avg=30.2,p50=25.0,p75=34.0,p90=47.0,p95=57.0")
    ap.add_argument("--turn-interval",
                    default="avg=18.6,p50=4.0,p75=10.0,p90=35.0,p95=86.0")
    ap.add_argument("--init-prompt-length",
                    default="avg=28568.9,p50=21983.0,p95=74262.9")
    ap.add_argument("--input-length",
                    default="avg=1352.6,p50=493.0,p95=4740.0")
    ap.add_argument("--output-length",
                    default="avg=345.8,p50=68.0,p95=1514.0")
    ap.add_argument("--concurrency", type=int, default=96)
    ap.add_argument("--token-budget", type=int, default=12_000_000)
    ap.add_argument("--max-duration", type=int, default=1200)
    ap.add_argument("--cache-mode", default="auto",
                    choices=["auto", "explicit", "implicit", "none"])
    ap.add_argument("--run-tag", default=datetime.now().strftime("%Y%m%d"))
    ap.add_argument("--smoke", action="store_true",
                    help="冒烟模式：微缩参数快速验证链路")
    args = ap.parse_args()

    if args.smoke:
        args.total_sessions = 2
        args.arrival_rate_start = args.arrival_rate_end = 0.5
        args.ramp_duration_seconds = 10
        args.hold_duration_seconds = 30
        args.num_rounds = "p50=3,p95=4"
        args.turn_interval = "p50=2,p95=5"
        args.init_prompt_length = "p50=2000,p95=3000"
        args.input_length = "p50=300,p95=600"
        args.output_length = "p50=100,p95=200"
        args.concurrency = 8
        args.token_budget = 300_000
        args.max_duration = 240

    print(f"Base URL: {BASE_URL}")
    print(f"Model:    {MODEL}")
    print(f"API Key:  {(API_KEY[:10] + '...' + API_KEY[-6:]) if len(API_KEY) > 16 else '(未设置)'}")
    if not API_KEY:
        print("\n❌ 未检测到 yundun-key（.env）")
        raise SystemExit(1)

    bench = Bench(args)
    bench.preflight()
    bench.run()


if __name__ == "__main__":
    main()
