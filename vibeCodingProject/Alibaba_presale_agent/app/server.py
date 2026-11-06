"""
FastAPI 入口 — 聊天 SSE / 反馈 / 后台分析 / 知识库同步
========================================================
启动:
    uvicorn app.server:app --host 0.0.0.0 --port 8000
    # 或本地开发: python run.py
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import guide, knowledge, pipeline, store
from .config import KB_SYNC_INTERVAL_HOURS, PROJECT_ROOT, get_admin_token, get_llm_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("server")

STATIC_DIR = PROJECT_ROOT / "static"


async def _kb_auto_sync_loop() -> None:
    """周期性检查知识库远端提交：有新提交才 pull 并重建索引（失败只告警不报错）"""
    if os.getenv("KB_AUTO_SYNC", "1") != "1":
        log.info("知识库自动同步已通过 KB_AUTO_SYNC=0 关闭")
        return
    interval_s = KB_SYNC_INTERVAL_HOURS * 3600
    log.info(
        "知识库自动同步已启用：每 %.1f 小时检查远端提交，有更新才拉取",
        KB_SYNC_INTERVAL_HOURS,
    )
    while True:
        await asyncio.sleep(interval_s)
        try:
            n = knowledge.sync_if_remote_changed()
            if n is not None:
                log.info("知识库自动同步完成，索引重建: %d 个片段", n)
        except Exception:
            log.warning("知识库自动同步异常（跳过本轮）", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    try:
        n = knowledge.build_default_index()
        log.info("知识库索引就绪: %d 个片段", n)
    except Exception:
        log.exception("启动时知识库构建失败（服务继续运行，可稍后在后台手动同步）")
    sync_task = asyncio.create_task(_kb_auto_sync_loop())
    yield
    sync_task.cancel()


app = FastAPI(title="阿里小可爱 EthanNi的小助手", lifespan=lifespan)


# ──────────────────────────── 请求模型 ────────────────────────────


class ChatRequest(BaseModel):
    question: str
    session_id: str = ""
    history: list = Field(default_factory=list)  # [{"role": "user"|"assistant", "content": str}]


class FeedbackRequest(BaseModel):
    answer_id: int
    rating: str  # "up" | "down"
    reason: str = ""


# ──────────────────────────── 鉴权 ────────────────────────────


def require_admin(x_admin_token: str = Header(default="")):
    """配置了 ADMIN_TOKEN 时，/api/admin/* 需带 X-Admin-Token 请求头"""
    token = get_admin_token()
    if token and x_admin_token != token:
        raise HTTPException(status_code=401, detail="invalid admin token")


def client_ip_of(request: Request) -> str:
    """取真实提问者 IP。

    优先级：X-Real-IP（nginx 用 $remote_addr 设置，客户无法伪造）
    > X-Forwarded-For 首跳 > 直连对端地址。XFF 首跳可被客户端伪造，
    故放在 X-Real-IP 之后。
    """
    ip = request.headers.get("x-real-ip", "").strip()
    if not ip:
        xff = request.headers.get("x-forwarded-for", "")
        ip = xff.split(",")[0].strip() if xff else ""
    if not ip and request.client:
        ip = request.client.host or ""
    # IPv4-mapped IPv6 / 本机回环归一化，便于排查
    if ip.startswith("::ffff:"):
        ip = ip[len("::ffff:"):]
    if ip in ("::1", "localhost"):
        ip = "127.0.0.1"
    return ip[:64]


# ──────────────────────────── 页面 ────────────────────────────


# 页面 HTML 禁缓存：保证样式/脚本版本参数改动后一次普通刷新即生效
_NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html", headers=_NO_CACHE)


@app.get("/admin", include_in_schema=False)
async def admin_page():
    return FileResponse(STATIC_DIR / "admin.html", headers=_NO_CACHE)


# 知识库未就绪时的兜底页：说明原因并给回首页的入口，而不是抛裸 404
_GUIDE_MISSING = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>售前指南暂不可用</title><style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#fcfbf9;color:#0d0d0d;
font-family:-apple-system,'PingFang SC',sans-serif;padding:24px}
div{max-width:520px;line-height:1.8}h1{font-size:18px;margin:0 0 12px}
p{color:#666;font-size:14px;margin:0 0 18px}
a{color:#ff6a00;font-size:14px}
</style></head><body><div>
<h1>售前指南暂不可用</h1>
<p>知识库尚未克隆完成，或 <code>alibaba-ai-hub/maas/sales-tools/</code>
下还没有 <code>ModelStudio-api-sales-guide-*.html</code>。等首次索引建好后刷新本页即可。</p>
<a href="/">← 返回问答首页</a>
</div></body></html>"""


@app.get("/guide", include_in_schema=False)
async def guide_page():
    """售前指南：始终指向知识库里版本日期最新的那份 HTML。"""
    page = guide.latest_guide()
    if page is None:
        return Response(_GUIDE_MISSING, status_code=404, media_type="text/html; charset=utf-8")
    # X-Guide-File 便于线上核对当前到底在放哪一版（文件名日期会滚动）
    return FileResponse(
        page,
        media_type="text/html; charset=utf-8",
        headers={**_NO_CACHE, "X-Guide-File": page.name},
    )


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "kb_chunks": knowledge.get_index().size,
        "llm_model": get_llm_config()["model"],
    }


# ──────────────────────────── 聊天（SSE 流式） ────────────────────────────


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is empty")
    session_id = (req.session_id or "anonymous")[:64]
    client_ip = client_ip_of(request)
    user_agent = request.headers.get("user-agent", "")[:300]
    log.info("chat session=%s ip=%s", session_id, client_ip)

    async def event_gen():
        try:
            async for ev in pipeline.stream_answer(
                question,
                req.history,
                session_id,
                client_ip=client_ip,
                user_agent=user_agent,
            ):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:
            log.exception("chat 管线异常")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 反代下禁用缓冲，保证 SSE 实时
        },
    )


# ──────────────────────────── 反馈 ────────────────────────────


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    ok = store.add_feedback(req.answer_id, req.rating, req.reason)
    if not ok:
        raise HTTPException(status_code=404, detail="answer not found or invalid rating")
    return {"ok": True}


# ──────────────────────────── 后台分析 ────────────────────────────


@app.get("/api/admin/stats", dependencies=[Depends(require_admin)])
async def admin_stats():
    return store.stats()


@app.get("/api/admin/answers", dependencies=[Depends(require_admin)])
async def admin_answers(
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    rating: str = Query("", pattern="^(up|down|)$"),
    q: str = Query("", max_length=100),
):
    items = store.list_answers(
        limit=limit,
        offset=offset,
        rating=rating or None,
        q=q or None,
    )
    return {"items": items}


@app.get("/api/admin/export.csv", dependencies=[Depends(require_admin)])
async def admin_export():
    csv_text = store.export_csv()
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=answers.csv"},
    )


@app.post("/api/admin/kb/sync", dependencies=[Depends(require_admin)])
async def admin_kb_sync():
    """手动同步知识库（git 拉最新）并重建索引"""
    try:
        n = knowledge.sync_and_rebuild()
        return {"ok": True, "chunks": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 静态资源（最后挂载，避免遮蔽上面的路由）
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
