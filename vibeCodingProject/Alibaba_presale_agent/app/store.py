"""
交付记录存储 — SQLite（问答、来源、价格校验状态、👍/👎 反馈）
================================================================
每条回答即一条交付记录，供后台分析踩率、定位坏 case、迭代知识库与 prompt。
"""

import csv
import io
import json
import sqlite3
from datetime import datetime, timedelta

from .config import get_db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    thinking        TEXT DEFAULT '',          -- 模型思考过程 reasoning_content
    sources_json    TEXT DEFAULT '[]',
    price_status    TEXT DEFAULT '',          -- ''|official|web|none|error
    llm_model       TEXT DEFAULT '',
    latency_ms      INTEGER DEFAULT 0,
    client_ip       TEXT DEFAULT '',          -- 提问者 IP（反代场景取 X-Forwarded-For 首跳）
    user_agent      TEXT DEFAULT '',          -- 提问者 UA（用于区分人员/终端）
    interrupted     INTEGER DEFAULT 0,        -- 1 = 用户主动停止，仅保存已生成部分
    created_at      TEXT NOT NULL,            -- ISO 本地时间
    feedback        TEXT,                     -- 'up' | 'down' | NULL
    feedback_reason TEXT DEFAULT '',
    feedback_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_answers_created ON answers(created_at);
CREATE INDEX IF NOT EXISTS idx_answers_feedback ON answers(feedback);
CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id);
"""

# 老库补列：CREATE TABLE IF NOT EXISTS 不会给已存在的表加字段
_MIGRATIONS = {
    "thinking": "TEXT DEFAULT ''",
    "client_ip": "TEXT DEFAULT ''",
    "user_agent": "TEXT DEFAULT ''",
    "interrupted": "INTEGER DEFAULT 0",
}

# 依赖补列后才能建的索引（放在补列之后执行，否则老库报 no such column）
_POST_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_answers_client_ip ON answers(client_ip)",
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(answers)")}
        for name, decl in _MIGRATIONS.items():
            if name not in cols:
                conn.execute(f"ALTER TABLE answers ADD COLUMN {name} {decl}")
        for stmt in _POST_INDEXES:
            conn.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def insert_answer(
    session_id: str,
    question: str,
    answer: str,
    sources: list,
    price_status: str,
    llm_model: str,
    latency_ms: int,
    thinking: str = "",
    client_ip: str = "",
    user_agent: str = "",
    interrupted: bool = False,
) -> int:
    """写入一条交付记录，返回 id（前端反馈凭此 id 关联）"""
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                """INSERT INTO answers
                   (session_id, question, answer, thinking, sources_json, price_status,
                    llm_model, latency_ms, client_ip, user_agent, interrupted, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    question,
                    answer,
                    thinking,
                    json.dumps(sources, ensure_ascii=False),
                    price_status,
                    llm_model,
                    latency_ms,
                    client_ip,
                    user_agent,
                    1 if interrupted else 0,
                    now,
                ),
            )
            return cur.lastrowid
    finally:
        conn.close()


def add_feedback(answer_id: int, rating: str, reason: str = "") -> bool:
    """记录 👍/👎；允许修改（误触可更正）。返回是否命中记录"""
    if rating not in ("up", "down"):
        return False
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                """UPDATE answers
                   SET feedback=?, feedback_reason=?, feedback_at=?
                   WHERE id=?""",
                (rating, reason[:1000], now, answer_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def stats() -> dict:
    """后台分析汇总"""
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) c FROM answers").fetchone()["c"]
        up = conn.execute("SELECT COUNT(*) c FROM answers WHERE feedback='up'").fetchone()["c"]
        down = conn.execute("SELECT COUNT(*) c FROM answers WHERE feedback='down'").fetchone()["c"]
        official = conn.execute(
            "SELECT COUNT(*) c FROM answers WHERE price_status='official'"
        ).fetchone()["c"]
        avg = conn.execute("SELECT AVG(latency_ms) a FROM answers").fetchone()["a"] or 0
        week_ago = (datetime.now() - timedelta(days=7)).astimezone().isoformat(timespec="seconds")
        recent = conn.execute(
            "SELECT COUNT(*) c FROM answers WHERE created_at >= ?", (week_ago,)
        ).fetchone()["c"]
        interrupted = conn.execute(
            "SELECT COUNT(*) c FROM answers WHERE interrupted=1"
        ).fetchone()["c"]
    finally:
        conn.close()
    return {
        "total": total,
        "up": up,
        "down": down,
        "down_rate": round(down / total * 100, 1) if total else 0.0,
        "price_official_verified": official,
        "avg_latency_ms": int(avg),
        "recent_7d": recent,
        "interrupted": interrupted,
    }


def list_answers(
    limit: int = 50,
    offset: int = 0,
    rating: str | None = None,
    q: str | None = None,
) -> list[dict]:
    """后台列表查询：可按反馈类型/关键词过滤"""
    sql = "SELECT * FROM answers"
    where: list[str] = []
    params: list = []
    if rating in ("up", "down"):
        where.append("feedback = ?")
        params.append(rating)
    if q:
        where.append(
            "(question LIKE ? OR answer LIKE ? OR thinking LIKE ? OR client_ip LIKE ?)"
        )
        params.extend([f"%{q}%"] * 4)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = _connect()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    items = []
    for r in rows:
        item = dict(r)
        try:
            item["sources"] = json.loads(item.pop("sources_json") or "[]")
        except Exception:
            item["sources"] = []
        items.append(item)
    return items


def export_csv() -> str:
    """全量导出 CSV（后台离线分析用）"""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, session_id, client_ip, user_agent, question, answer, thinking,"
            " price_status, llm_model, latency_ms, interrupted, created_at, feedback,"
            " feedback_reason, feedback_at, sources_json"
            " FROM answers ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "session_id", "client_ip", "user_agent", "question", "answer",
         "thinking", "price_status", "llm_model", "latency_ms", "interrupted",
         "created_at", "feedback", "feedback_reason", "feedback_at", "sources"]
    )
    for r in rows:
        writer.writerow(list(r))
    return buf.getvalue()
