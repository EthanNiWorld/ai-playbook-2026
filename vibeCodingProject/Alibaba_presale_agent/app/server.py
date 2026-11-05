"""
FastAPI 入口 — 聊天 SSE / 反馈 / 后台分析 / 知识库同步
========================================================
启动:
    uvicorn app.server:app --host 0.0.0.0 --port 8000
    # 或本地开发: python run.py
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import knowledge, pipeline, store
from .config import PROJECT_ROOT, get_admin_token, get_llm_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("server")

STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    try:
        n = knowledge.build_default_index()
        log.info("知识库索引就绪: %d 个片段", n)
    except Exception:
        log.exception("启动时知识库构建失败（服务继续运行，可稍后在后台手动同步）")
    yield


app = FastAPI(title="阿里小可爱AI问答助手", lifespan=lifespan)


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


# ──────────────────────────── 页面 ────────────────────────────


# 页面 HTML 禁缓存：保证样式/脚本版本参数改动后一次普通刷新即生效
_NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html", headers=_NO_CACHE)


@app.get("/admin", include_in_schema=False)
async def admin_page():
    return FileResponse(STATIC_DIR / "admin.html", headers=_NO_CACHE)


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "kb_chunks": knowledge.get_index().size,
        "llm_model": get_llm_config()["model"],
    }


# ──────────────────────────── 聊天（SSE 流式） ────────────────────────────


@app.post("/api/chat")
async def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is empty")
    session_id = (req.session_id or "anonymous")[:64]

    async def event_gen():
        try:
            async for ev in pipeline.stream_answer(question, req.history, session_id):
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
