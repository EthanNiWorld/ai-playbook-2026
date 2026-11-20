"""短剧生产流水线 · Web 服务（FastAPI + SSE，前端风格对齐 Alibaba_presale_agent）

启动：
    .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 7861
    # 或 python server.py

接口：
- GET  /                首页（static/index.html，禁缓存）
- GET  /api/health      健康检查 + 当前模型配置 + 可续跑任务探测
- GET  /api/runs        历史执行记录列表（按时间倒序，含主题/剧名/产物计数）
- POST /api/run         启动流水线，SSE 流式推送日志与产物（asset 事件）；
                        resume=true 时从最新未完成 run 的 checkpoint 断点续跑；
                        manual=true（默认）为打磨模式：分镜/图像/验收/视频四步后推
                        confirm 事件暂停，等人工点确认再继续（可重做/终止）
- POST /api/run/confirm 打磨模式人工确认（continue / redo / abort；分镜可带编辑后 JSON）
（压测能力已收敛到 CLI：run_demo.py --pressure，Web 界面不再提供）
- GET  /files/*         运行产物静态文件（output/ 目录）
"""
import asyncio
import glob
import json
import os
import sys
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402  （依赖 PROJECT_ROOT 先入 sys.path）
from pipeline import ShortDramaPipeline  # noqa: E402
from task_manager import TaskManager  # noqa: E402
from bailian_client import BailianAsyncClient  # noqa: E402

STATIC_DIR = PROJECT_ROOT / "static"
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="短剧生产流水线 · 北京节点 demo")
_NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

# 同一时刻只允许一条流水线在跑（两条并行会互抢 stdout 与确认状态）
_RUN_LOCK = threading.Lock()
# 打磨模式当前待确认的步骤：{"event": Event, "step": str, "result": (action, edited), "done": bool}
_PENDING_CONFIRM = {}
_CONFIRM_LOCK = threading.Lock()

_GATE_TITLES = {
    "storyboard": "剧本分镜",
    "images": "海报 / 剧照",
    "qa": "质量验收",
    "video": "图生视频",
}


def _sse(ev: dict) -> str:
    return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html", headers=_NO_CACHE)


@app.get("/api/health")
async def health():
    resumable = _find_resumable_run()
    return {
        "ok": True,
        "video_model": config.VIDEO_MODEL,
        "image_model": config.IMAGE_MODEL,
        "llm_model": config.LLM_MODEL,
        "credentials_ok": config.check_credentials(),
        # 最新未完成的 run 目录名（无则 null），前端据此展示「续跑」按钮
        "resumable_run": os.path.basename(resumable) if resumable else None,
    }


def _load_ckpt(d):
    """读 run 目录的 checkpoint（无/损坏返回 None）。"""
    ckpt_path = os.path.join(d, "checkpoint.json")
    if not os.path.isfile(ckpt_path):
        return None
    try:
        with open(ckpt_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _is_resumable(d):
    """可续跑判定：有 checkpoint、分镜已落盘且未标记 finished。"""
    ckpt = _load_ckpt(d)
    return bool(ckpt and ckpt.get("storyboard") and not ckpt.get("finished"))


def _find_resumable_run():
    """找最新的可续跑 run 目录（按修改时间，不依赖命名规则）。"""
    best = None
    for d in sorted(glob.glob(os.path.join(config.OUTPUT_DIR, "run_*")),
                   key=os.path.getmtime):
        if os.path.isdir(d) and _is_resumable(d):
            best = d
    return best


@app.get("/api/runs")
async def list_runs():
    """历史执行记录：列出全部 run 目录，按时间倒序（最新的在前）。"""
    runs = []
    for d in sorted(glob.glob(os.path.join(config.OUTPUT_DIR, "run_*")),
                    key=os.path.getmtime, reverse=True):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        entry = {
            "name": name,
            "mtime": os.path.getmtime(d),
            "theme": None, "title": None, "finished": None,
            "resumable": False,  # 有 checkpoint 且未完成：前端展示「续跑」按钮
            "assets": {"image": 0, "video": 0},
            "files": [],  # 真实产物文件清单：前端回看按此加载，不猜文件名
        }
        # 主题/剧名/完成状态从 checkpoint 或 storyboard.json 读取（无则留空）
        ckpt_path = os.path.join(d, "checkpoint.json")
        board_path = os.path.join(d, "storyboard.json")
        ckpt = {}
        if os.path.isfile(ckpt_path):
            try:
                with open(ckpt_path) as f:
                    ckpt = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        board = ckpt.get("storyboard")
        if board is None and os.path.isfile(board_path):
            try:
                with open(board_path) as f:
                    board = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        entry["theme"] = ckpt.get("theme")
        entry["finished"] = ckpt.get("finished")
        entry["resumable"] = bool(ckpt and ckpt.get("storyboard") and not ckpt.get("finished"))
        if board:
            entry["title"] = board.get("title")
        # 产物计数与文件清单（回看按钮按真实文件加载，final_cut 置顶）
        try:
            for f in os.listdir(d):
                if f.endswith(".png"):
                    entry["assets"]["image"] += 1
                    entry["files"].append({"name": f, "kind": "image"})
                elif f.endswith(".mp4"):
                    entry["assets"]["video"] += 1
                    entry["files"].append({"name": f, "kind": "video"})
            # 展示排序：全片 > 编辑成片 > 原始视频 > 图片（final_cut 最优先）
            def rank(fi):
                n = fi["name"]
                if n == "final_cut.mp4":
                    return (0, n)
                if "edited" in n:
                    return (1, n)
                if "raw" in n:
                    return (2, n)
                return (3, n)
            entry["files"].sort(key=rank)
        except OSError:
            pass
        runs.append(entry)
    return {"ok": True, "runs": runs}


class RunRequest(BaseModel):
    theme: str = "都市逆袭短剧"
    scenes: int = 1
    resume: bool = False
    # 指定从哪个历史 run 续跑（目录名，如 run_008_20261120_180542）；
    # 缺省时自动选最新可续跑 run。仅允许 basename，防止路径注入。
    resume_run: str | None = None
    manual: bool = True  # 打磨模式：四步人工确认（勾掉则全自动一次跑到底）


class ConfirmRequest(BaseModel):
    action: str  # continue / redo / abort
    storyboard: str | None = None  # 仅分镜确认点：人工编辑后的分镜 JSON 全文


@app.post("/api/run/confirm")
async def confirm_step(req: ConfirmRequest):
    """打磨模式确认：前端按钮触发，解除 worker 线程的阻塞继续/重做/终止。"""
    if req.action not in ("continue", "redo", "abort"):
        return {"ok": False, "error": "action 非法（仅 continue/redo/abort）"}
    with _CONFIRM_LOCK:
        ev = _PENDING_CONFIRM.get("event")
        if ev is None or _PENDING_CONFIRM.get("done"):
            return {"ok": False, "error": "当前没有等待确认的步骤"}
        edited = None
        if req.action == "continue" and req.storyboard is not None \
                and _PENDING_CONFIRM.get("step") == "storyboard":
            try:
                edited = json.loads(req.storyboard)
            except json.JSONDecodeError as e:
                return {"ok": False, "error": "分镜 JSON 解析失败：" + str(e)}
            if not isinstance(edited, dict) or not edited.get("scenes"):
                return {"ok": False, "error": "分镜 JSON 缺少 scenes 字段或场景为空"}
        _PENDING_CONFIRM["result"] = (req.action, edited)
        _PENDING_CONFIRM["done"] = True
        ev.set()
    return {"ok": True, "action": req.action}


def make_web_confirm(emit, holder):
    """把 pipeline 的确认点接到 Web：推 confirm 事件后阻塞 worker 线程，
    等 /api/run/confirm 把用户的选择写进来再返回；SSE 断开（用户关页面）
    时由 holder["closed"] 兑底返回 abort，避免 worker 永久卡死、锁死 _RUN_LOCK。"""
    def confirm(step, payload):
        ev = threading.Event()
        with _CONFIRM_LOCK:
            _PENDING_CONFIRM.clear()
            _PENDING_CONFIRM.update({"event": ev, "step": step, "result": None, "done": False})
        emit({
            "type": "confirm",
            "step": step,
            "title": _GATE_TITLES.get(step, step),
            "tip": ShortDramaPipeline.GATE_TIPS.get(step, ""),
            "payload": payload,
        })
        while not ev.wait(timeout=10):
            # 周期醒来看看 SSE 是否已断开：断开则视为终止，释放流水线锁
            if holder.get("closed"):
                with _CONFIRM_LOCK:
                    if not _PENDING_CONFIRM.get("done"):
                        _PENDING_CONFIRM["result"] = ("abort", None)
                        _PENDING_CONFIRM["done"] = True
                        ev.set()
                break
        with _CONFIRM_LOCK:
            result = _PENDING_CONFIRM.get("result") or ("abort", None)
            _PENDING_CONFIRM.clear()
        return result
    return confirm


# 产物文件 → asset 事件的识别规则（exp_/verify_ 前缀为实验产物，
# checkpoint.json 为断点续传内部状态，均不在界面展示）
_ASSET_KINDS = {".png": "image", ".mp4": "video", ".json": "json"}


def _scan_assets(run_dir: str, emitted: set) -> list:
    events = []
    for f in sorted(glob.glob(os.path.join(run_dir, "*"))):
        name = os.path.basename(f)
        if f in emitted or name.startswith(("exp", "verify", "retest")) \
                or name == "checkpoint.json":
            continue
        kind = _ASSET_KINDS.get(os.path.splitext(name)[1])
        if not kind:
            continue
        emitted.add(f)
        rel = os.path.relpath(f, config.OUTPUT_DIR).replace(os.sep, "/")
        events.append({"type": "asset", "kind": kind, "label": name, "url": f"/files/{rel}"})
    return events


@app.post("/api/run")
async def run_pipeline(req: RunRequest):
    if not config.check_credentials():
        async def missing():
            yield _sse({"type": "error",
                        "message": "缺少环境变量 DASHSCOPE_API_KEY_CN_TEST / DASHSCOPE_API_KEY_CN_URL"})
        return StreamingResponse(missing(), media_type="text/event-stream", headers=_SSE_HEADERS)

    async def event_gen():
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def emit(ev: dict):
            loop.call_soon_threadsafe(q.put_nowait, ev)

        class _StreamWriter:
            """把流水线 print 输出转成 log 事件；空行丢弃。"""

            def write(self, s):
                for line in s.splitlines():
                    if line.strip():
                        emit({"type": "log", "text": line.rstrip()})

            def flush(self):
                pass

        holder = {}

        def worker():
            if not _RUN_LOCK.acquire(blocking=False):
                emit({"type": "error", "message": "已有流水线在运行中，请等当前任务结束"})
                emit({"type": "__end__"})
                return
            old_stdout = sys.stdout
            sys.stdout = _StreamWriter()
            resume_dir = None
            try:
                if req.resume:
                    if req.resume_run:
                        # 历史记录指定续跑：仅接受 basename，目标必须真实可续跑
                        name = os.path.basename(req.resume_run)
                        target = os.path.join(config.OUTPUT_DIR, name)
                        if not _is_resumable(target):
                            emit({"type": "error", "message": f"{name} 不可续跑（无 checkpoint 或已完成）"})
                            return
                        resume_dir = target
                    else:
                        resume_dir = _find_resumable_run()
                        if resume_dir is None:
                            emit({"type": "error", "message": "没有可续跑的任务（未找到未完成的 checkpoint）"})
                            return
                p = ShortDramaPipeline(
                    theme=(req.theme or "都市逆袭短剧").strip(),
                    num_scenes=max(1, min(3, int(req.scenes))),
                    resume_dir=resume_dir,
                    confirm_cb=make_web_confirm(emit, holder) if req.manual else None,
                )
                holder["run_dir"] = p.run_dir
                holder["pipeline"] = p
                report = p.run()
                summary = {
                    "run_dir": os.path.relpath(report.get("run_dir", ""), PROJECT_ROOT),
                    "models_used": report.get("models_used", []),
                    "task_stats": {k: v for k, v in report.get("task_stats", {}).items()
                                   if k in ("queries", "throttled")},
                }
                if report.get("paused"):
                    # 打磨模式确认点选择终止：已完成步骤都在 checkpoint，可续跑
                    emit({"type": "paused", "report": summary})
                else:
                    emit({"type": "done", "report": summary})
            except Exception as e:  # 流水线异常不打断 SSE，前端展示错误条
                emit({"type": "error", "message": f"{type(e).__name__}: {e}"})
            finally:
                sys.stdout = old_stdout
                _RUN_LOCK.release()
                emit({"type": "__end__"})

        threading.Thread(target=worker, daemon=True).start()

        emitted_files = set()
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=2.0)
                    if ev["type"] == "__end__":
                        break
                    yield _sse(ev)
                except asyncio.TimeoutError:
                    pass
                # 每轮顺带扫描新产物（进度可视化：图片/视频边生成边出现）
                run_dir = holder.get("run_dir")
                if run_dir:
                    for asset_ev in _scan_assets(run_dir, emitted_files):
                        yield _sse(asset_ev)
            # 收尾补扫一次，确保最后一个产物不遗漏
            run_dir = holder.get("run_dir")
            if run_dir:
                for asset_ev in _scan_assets(run_dir, emitted_files):
                    yield _sse(asset_ev)
        finally:
            # SSE 断开（用户关页面/断网）：标记 closed，让阻塞在确认点的 worker
            # 兑底返回 abort，避免流水线锁永久占用、后续生产全部被拒
            holder["closed"] = True

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=_SSE_HEADERS)


# 运行产物静态服务（最后挂载，避免遮蔽 API 路由）
app.mount("/files", StaticFiles(directory=config.OUTPUT_DIR), name="files")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7861)
