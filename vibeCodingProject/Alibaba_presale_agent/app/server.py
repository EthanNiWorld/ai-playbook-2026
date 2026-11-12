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

from . import asr, guide, knowledge, llm, pipeline, store, vendor_report
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
    history: list = Field(default_factory=list)  # [{"role": "user"|"assistant", "content": str|list}]
    # 截图/图片输入（多模态）：data URL（data:image/png;base64,...）数组。
    # 前端限制单次最多 4 张、每张 ≤5MB；服务端仅做上限与格式校验。
    images: list[str] = Field(default_factory=list)


# 图片 data URL 校验：前缀白名单 + 大小上限（base64 后 ≤ 5MB×1.4）
_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
_MAX_IMAGE_B64 = 7 * 1024 * 1024
_MAX_IMAGES = 4


class FeedbackRequest(BaseModel):
    answer_id: int
    rating: str  # "up" | "down"
    reason: str = ""


class AsrRequest(BaseModel):
    # 语音识别：data:audio/wav;base64,... 或裸 base64（前端限制录音 ≤60s）。
    # context：实时分段识别时传上一段已识别文本（qwen-audio 上下文增强，≤400 字）
    audio: str
    context: str = ""


_MAX_AUDIO_B64 = 14 * 1024 * 1024  # base64 后 ≈10MB 音频上限


class ReportRequest(BaseModel):
    # 供应商测试报告 HTML 原文（前端 FileReader.readAsText 读入）。
    # 仅做报告内证据的智能定界分析，不执行报告里的请求、不打真实端点。
    html: str
    filename: str = ""


_MAX_REPORT_CHARS = 3 * 1024 * 1024  # HTML 原文 ≈3MB 上限


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
    # 截图问答：允许无文本纯图提问（“[图片]”占位后仍可走检索），但图数超限直接拒
    if not question and not req.images:
        raise HTTPException(status_code=400, detail="question is empty")
    images = [img for img in req.images if isinstance(img, str)][:_MAX_IMAGES]
    for img in images:
        if not img.startswith(_IMAGE_PREFIXES):
            raise HTTPException(status_code=400, detail="unsupported image format")
        if len(img) > _MAX_IMAGE_B64:
            raise HTTPException(status_code=400, detail="image too large (max 5MB)")
    session_id = (req.session_id or "anonymous")[:64]
    client_ip = client_ip_of(request)
    user_agent = request.headers.get("user-agent", "")[:300]
    log.info(
        "chat session=%s ip=%s images=%d",
        session_id,
        client_ip,
        len(images),
    )

    async def event_gen():
        try:
            async for ev in pipeline.stream_answer(
                question,
                req.history,
                session_id,
                client_ip=client_ip,
                user_agent=user_agent,
                images=images,
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


@app.post("/api/asr")
async def speech_to_text(req: AsrRequest):
    """语音识别：qwen-audio-3.1-asr-flash（3.0 兜底），wav base64 → 文本。"""
    audio = (req.audio or "").strip()
    if not audio:
        raise HTTPException(status_code=400, detail="audio is empty")
    if len(audio) > _MAX_AUDIO_B64:
        raise HTTPException(status_code=400, detail="audio too large (max ~10MB)")
    result = await asr.transcribe(audio, (req.context or "")[:400])
    if result.get("error"):
        return {"ok": False, "error": result["error"]}
    return {"ok": True, "text": result.get("text", ""), "model": result.get("model", "")}


# ──────────────────────────── 供应商报告定界分析 ────────────────────────────


@app.post("/api/report/analyze")
async def report_analyze(req: ReportRequest):
    """上传供应商测试报告 HTML → 解析阻塞性失败用例 → 流式输出逐条技术定界。

    事件类型与 /api/chat 对齐（meta/status/think/delta/done/error），前端复用渲染。
    不做 DB 落库与反馈（报告分析是一次性技术结论，非售前问答）。
    """
    html_text = req.html or ""
    if not html_text.strip():
        raise HTTPException(status_code=400, detail="report is empty")
    if len(html_text) > _MAX_REPORT_CHARS:
        raise HTTPException(status_code=400, detail="report too large (max ~3MB)")
    if "template-group-heading" not in html_text:
        raise HTTPException(status_code=400, detail="不是可识别的供应商测试报告（缺少分组结构）")
    parsed = vendor_report.parse_report(html_text)
    st = parsed["stats"]
    log.info(
        "report analyze filename=%s model=%s blocking=%d/%d failures=%d",
        (req.filename or "")[:120],
        parsed["meta"].get("模型 ID", "?"),
        st["blocking_passed"],
        st["blocking_total"],
        st["failure_count"],
    )

    async def event_gen():
        try:
            meta_ev = {
                "type": "meta",
                "summary": vendor_report.summary_text(parsed),
                "stats": st,
                "meta": parsed["meta"],
            }
            yield f"data: {json.dumps(meta_ev, ensure_ascii=False)}\n\n"
            if not parsed["groups"]:
                msg = ("⚠️ 未能识别报告的分组结构。本工具适配含「template-group-heading」分组的供应商测试报告模板；"
                       "当前文件虽含该标记但未解析出有效分组，可能是模板版本不同或文件损坏，请确认报告格式后重试。")
                yield f"data: {json.dumps({'type': 'delta', 'text': msg}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                return
            if not parsed["blocking_failures"]:
                msg = "✅ 该报告阻塞性分组全部通过，没有需要定界的失败用例。"
                nb = [g for g in parsed["groups"]
                      if not g["blocking"] and g["passed"] < g["total"]]
                if nb:
                    msg += "\n\n非阻塞组未满足项（仅统计，不影响验收）：" + "；".join(
                        f"{g['name']} {g['passed']}/{g['total']}" for g in nb)
                yield f"data: {json.dumps({'type': 'delta', 'text': msg}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                return
            status_ev = {"type": "status",
                         "message": f"正在定界 {st['failure_count']} 条阻塞失败用例…"}
            yield f"data: {json.dumps(status_ev, ensure_ascii=False)}\n\n"
            messages = vendor_report.build_messages(parsed)
            async for kind, text in llm.stream_chat(
                messages, enable_thinking=True, max_tokens=8192
            ):
                if kind == "think":
                    yield f"data: {json.dumps({'type': 'think', 'text': text}, ensure_ascii=False)}\n\n"
                elif kind == "text":
                    yield f"data: {json.dumps({'type': 'delta', 'text': text}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            log.exception("report analyze 异常")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
