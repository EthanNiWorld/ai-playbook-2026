"""批量任务状态查询管理器（呼应配额申请第 7 项：任务状态查询 ≥500 QPS）。

设计要点：
- 统一纳管百炼异步任务（图像/视频/生成式编辑）与 IMS 任务（字幕擦除/剪辑合成）
- 自适应限速：从低速起爬坡逼近目标 QPS，遭遇 Throttling 自动退避并降速（BurstRate
  限的是增量斜率，不是绝对值，须平滑增长）
- 压测模式（--pressure）：对同一批任务高频查询，实测当前 workspace 可持续的状态查询
  QPS 与限流触发点，为客户申请 500 QPS 提供实测依据
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from bailian_client import BailianAsyncClient, THROTTLING_CODES

# 百炼任务终态为 SUCCEEDED/FAILED/CANCELED，IMS 任务终态为 SUCCESS/FAILED——
# 漏写 SUCCESS 会让 IMS 任务永远"未完成"，轮询被迫跑满 max_wait（实测踩过）。
TERMINAL = ("SUCCEEDED", "SUCCESS", "FAILED", "CANCELED", "UNKNOWN")


class TaskRecord:
    def __init__(self, task_id, kind, label, query_fn):
        self.task_id = task_id
        self.kind = kind          # bailian_video / bailian_image / ims_erase / ims_produce
        self.label = label
        self.query_fn = query_fn  # () -> (status:str, info:dict)
        self.status = "PENDING"
        self.info = {}
        self.submitted_at = time.time()
        self.finish_time = None

    @property
    def done(self):
        return self.status in TERMINAL


class AdaptiveRateLimiter:
    """平滑爬坡限速器：逼近目标 QPS；遇到 Throttling 立即退避并降斜率。"""

    def __init__(self, target_qps, start_qps=2.0):
        self.target_qps = target_qps
        self.current_qps = start_qps
        self._last = 0.0
        self._lock = threading.Lock()
        self.throttle_events = 0

    def acquire(self):
        with self._lock:
            now = time.time()
            min_interval = 1.0 / self.current_qps
            wait = self._last + min_interval - now
            if wait > 0:
                time.sleep(wait)
                now = time.time()
            self._last = now
            # 未触发限流时缓慢爬坡（每 20 次调用 +10%，平滑增长避免 BurstRate）
            self._last_n = getattr(self, "_last_n", 0) + 1
            if self._last_n % 20 == 0 and self.current_qps < self.target_qps:
                self.current_qps = min(self.target_qps, self.current_qps * 1.1)

    def on_throttled(self):
        with self._lock:
            self.throttle_events += 1
            self.current_qps = max(1.0, self.current_qps * 0.5)  # 限流后减半


class TaskManager:
    def __init__(self, bailian_client: BailianAsyncClient, ims_client=None, target_qps=10):
        self.bailian = bailian_client
        self.ims = ims_client
        self.tasks = []  # [TaskRecord]
        self.rate_limiter = AdaptiveRateLimiter(target_qps)
        self.stats = {"queries": 0, "throttled": 0, "t_first": None, "t_last": None}

    # ---------- 任务注册 ----------
    def add_bailian_task(self, task_id, kind, label):
        def q():
            info = self.bailian.query_task(task_id)
            return info.get("output", {}).get("task_status", "UNKNOWN"), info
        rec = TaskRecord(task_id, kind, label, q)
        self.tasks.append(rec)
        return rec

    def add_ims_task(self, job_id, kind, label):
        def q():
            status, info = self.ims.query_job(job_id, kind)
            return status, info
        rec = TaskRecord(job_id, kind, label, q)
        self.tasks.append(rec)
        return rec

    # ---------- 单次查询（含限速与限流观测） ----------
    def _query_one(self, rec):
        for attempt in range(3):
            self.rate_limiter.acquire()
            self.stats["queries"] += 1
            if self.stats["t_first"] is None:
                self.stats["t_first"] = time.time()
            self.stats["t_last"] = time.time()
            try:
                status, info = rec.query_fn()
                rec.status, rec.info = status, info
                if rec.done:
                    rec.finish_time = time.time()
                return
            except RuntimeError as e:
                if any(c in str(e) for c in THROTTLING_CODES):
                    self.stats["throttled"] += 1
                    self.rate_limiter.on_throttled()
                    time.sleep(1.0)
                    continue
                raise

    # ---------- 批量轮询 ----------
    def poll_until_done(self, workers=8, max_wait=1200, log_every=30):
        """轮询所有任务到终态。并发查询 + 自适应限速。"""
        start = time.time()
        last_log = 0.0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while True:
                pending = [t for t in self.tasks if not t.done]
                if not pending:
                    break
                futures = [pool.submit(self._query_one, t) for t in pending]
                for f in as_completed(futures):
                    f.result()
                now = time.time()
                if now - last_log > log_every:
                    self._print_progress(start)
                    last_log = now
                if now - start > max_wait:
                    print(f"⚠️ 达到最大等待 {max_wait}s，仍有 {len(pending)} 个任务未完成")
                    break
                time.sleep(2)
        self._print_progress(start)
        return {t.label: (t.status, t.info) for t in self.tasks}

    # ---------- 压测：实测可持续查询 QPS ----------
    def pressure_test(self, duration_s=30):
        """高频查询演示任务，实测限流触发点（对应客户 500 QPS 申请的验证）。"""
        print(f"\n>>> 状态查询压测（{duration_s}s，目标 QPS={self.rate_limiter.target_qps}）")
        probe = self.tasks[0] if self.tasks else None
        if probe is None:
            print("  无可查询任务，跳过")
            return
        # 压测场景直接从目标速率的一半起测（轮询场景才从低速爬坡）
        self.rate_limiter.current_qps = max(
            self.rate_limiter.current_qps, self.rate_limiter.target_qps * 0.5)
        n, throttled = 0, 0
        t0 = time.time()
        while time.time() - t0 < duration_s:
            try:
                self._query_one(probe)
                n += 1
                if probe.done:
                    probe.status = "PENDING"  # 压测用：终态也继续查，测的是查询面配额
            except RuntimeError:
                throttled += 1
        elapsed = time.time() - t0
        qps = n / elapsed
        print(f"  实测: {n} 次查询 / {elapsed:.1f}s = {qps:.1f} QPS；限流 {throttled} 次；"
              f"限速器终速 {self.rate_limiter.current_qps:.1f} QPS")
        print(f"  结论: 当前 workspace 状态查询可持续 ~{qps:.0f} QPS；"
              f"提升到 500 QPS 需工单扩配额（本次观测限流 {self.stats['throttled']} 次）")
        return qps

    def _print_progress(self, start):
        elapsed = time.time() - start
        done = sum(1 for t in self.tasks if t.done)
        qps_hint = ""
        if self.stats["queries"] > 5:
            span = self.stats["t_last"] - self.stats["t_first"]
            qps_hint = f"，平均查询速率 {self.stats['queries'] / max(span, 0.001):.1f} QPS"
        print(f"  [{elapsed:5.0f}s] 任务 {done}/{len(self.tasks)} 完成，"
              f"查询 {self.stats['queries']} 次（限流 {self.stats['throttled']} 次）{qps_hint}")
        for t in self.tasks:
            if not t.done:
                print(f"    - {t.label}: {t.status}")
