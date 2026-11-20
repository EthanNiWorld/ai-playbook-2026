"""线上交付日报 — 只读快照 + 确定性检查 + 重点语义抽审

默认流程：
  1. 云助手在容器内 VACUUM INTO 一致性快照，经私有 OSS 取回，不停止服务；
  2. 检查上一游标后的新记录，排除评测自身会话，不重放客户问题；
  3. 全量检查踩/价格审计/中断/路径泄漏/耗时，最多抽审 8 条重点记录；
  4. 输出问题证据、候选优化方向、影响面与回归入口，绝不自动改代码。

运行（实例 ID 也可放 QA_AUDIT_INSTANCE_ID 环境变量）：
  .venv/bin/python tests/e2e/daily_audit.py --instance-id <ECS_INSTANCE_ID>
  .venv/bin/python tests/e2e/daily_audit.py --skip-sync --since-hours 24

产物均在 Git 忽略的 data/ 下：data/eval/remote-qa.db、daily_audit_state.json，
以及 data/reports/daily-<ts>.md/.json。原始问答不进入公开仓库。
"""

import argparse
import base64
import gzip
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import oss2
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_harness import _llm_json, _percentile  # noqa: E402
from judge_quality import RUBRIC, hard_checks  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT.parent.parent
DATA_DIR = ROOT / "data" / "eval"
DEFAULT_DB = DATA_DIR / "remote-qa.db"
STATE_PATH = DATA_DIR / "daily_audit_state.json"
REPORT_DIR = ROOT / "data" / "reports"
OSS_OBJECT = "presale-agent/eval/remote-qa.db.gz"
INTERNAL_SESSION_RE = re.compile(r"^(judge|replay|diagnose|daily-audit)-", re.I)

# 远端只读快照：不上传脚本、不改配置、不重启容器。临时文件上传成功后删除。
_REMOTE_SNAPSHOT_PY = r'''
import gzip
import json
import os
import sqlite3
import oss2
from app.config import get_oss_config

path = "/tmp/daily-audit-qa.db"
if os.path.exists(path):
    os.remove(path)
conn = sqlite3.connect("/app/data/qa.db")
try:
    conn.execute("VACUUM INTO ?", (path,))
    row = conn.execute("SELECT COUNT(*), MAX(id), MAX(created_at) FROM answers").fetchone()
finally:
    conn.close()
with open(path, "rb") as f:
    payload = gzip.compress(f.read())
os.remove(path)
cfg = get_oss_config()
if not cfg["key_id"] or not cfg["key_secret"]:
    raise RuntimeError("OSS credential is not configured")
bucket = oss2.Bucket(oss2.Auth(cfg["key_id"], cfg["key_secret"]),
                     cfg["endpoint"], cfg["bucket"])
key = "presale-agent/eval/remote-qa.db.gz"
bucket.put_object(key, payload)
print(json.dumps({"bucket": cfg["bucket"], "endpoint": cfg["endpoint"],
                  "object": key, "records": row[0], "max_id": row[1],
                  "latest": row[2], "gzip_bytes": len(payload)}, ensure_ascii=False))
'''

_AUDIT_RUBRIC = """请评审一条已经交付的真实回答，判断它当时是否符合用户预期。
除表达质量外，重点识别：答非所问、多轮上下文丢失、应调用工具却凭记忆回答、
知识或定价口径陈旧、来源不支持结论、内部实现痕迹、无意义反问、过度冗长。

你不能用自己的记忆判定价格数字或模型规格对错；价格硬证据以 system_meta 为准。
derived_price_audit 仅表示小计/合计等派生金额不在官方单价表内，不是计算错误证据；
不得仅凭 price_audit=mismatch 断言派生测算数字不一致，应检查回答内部算式或后续纠正证据。
若仅靠历史问答无法确认事实，请标 warn 并写 needs_replay=true，不要猜。
建议只写优化方向，不要编造具体代码修改。

输出严格 JSON：
{"verdict":"pass|warn|fail","category":"pricing|retrieval|followup|orchestration|presentation|performance|storage|other",
 "issues":["具体、可复核的问题"],"expected":"一句话说明是否符合预期",
 "suggestion":"候选优化方向；无需优化则空字符串","needs_replay":true|false}
"""


_EXPRESSION_RUBRIC = RUBRIC.split("输出严格 JSON", 1)[0]


def _judge_model() -> str:
    return os.getenv("DAILY_JUDGE_MODEL") or "glm-5.2"


def _load_environment() -> None:
    """加载工作区与项目配置；仅在本进程内映射评审所需密钥。"""
    load_dotenv(WORKSPACE_ROOT / ".env")
    load_dotenv(ROOT / ".env")
    # 评审凭证与问答运行凭证解耦：显式 JUDGE_* 优先；其次用已验证的 SG 测试组合，
    # 避免调用方 shell 中残留的 DASHSCOPE_* 与评审 workspace 错配（403）。
    if not os.getenv("JUDGE_API_KEY"):
        os.environ["JUDGE_API_KEY"] = (
            os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST") or os.getenv("DASHSCOPE_API_KEY", "")
        )
    if not os.getenv("JUDGE_BASE_URL"):
        os.environ["JUDGE_BASE_URL"] = (
            os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL") or os.getenv("DASHSCOPE_BASE_URL", "")
        )


def _cli(profile: str, *args: str) -> dict:
    proc = subprocess.run(
        ["aliyun", *args, "--profile", profile],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode:
        raise RuntimeError(f"aliyun {' '.join(args[:3])} 失败: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def _run_remote(script: str, args: argparse.Namespace) -> str:
    encoded = base64.b64encode(script.encode()).decode()
    result = _cli(
        args.profile, "ecs", "RunCommand", "--RegionId", args.region,
        "--Type", "RunShellScript", "--ContentEncoding", "Base64",
        "--CommandContent", encoded, "--InstanceId.1", args.instance_id,
        "--Timeout", str(args.remote_timeout), "--Username", "root",
    )
    invoke_id = result["InvokeId"]
    deadline = time.time() + args.remote_timeout + 60
    while time.time() < deadline:
        time.sleep(3)
        result = _cli(
            args.profile, "ecs", "DescribeInvocationResults",
            "--RegionId", args.region, "--InvokeId", invoke_id,
        )
        item = result["Invocation"]["InvocationResults"]["InvocationResult"][0]
        status = item["InvokeRecordStatus"]
        if status in ("Finished", "Failed", "Stopped", "PartialFailed"):
            output = base64.b64decode(item.get("Output", "")).decode("utf-8", "replace")
            if status != "Finished" or item.get("ExitCode") not in (0, "0", None):
                raise RuntimeError(f"远端快照失败 {status}/{item.get('ExitCode')}: {output[:500]}")
            return output.strip()
    raise TimeoutError("云助手快照超时")


def sync_snapshot(args: argparse.Namespace) -> dict:
    """容器内一致性快照 → 私有 OSS → 本地原子替换，全程不输出凭证。"""
    if not args.instance_id:
        raise SystemExit("缺少 --instance-id 或 QA_AUDIT_INSTANCE_ID")
    remote_code = base64.b64encode(_REMOTE_SNAPSHOT_PY.encode()).decode()
    executor = f"import base64;exec(base64.b64decode('{remote_code}'))"
    command = f"docker exec {shlex.quote(args.container)} python -c {shlex.quote(executor)}"
    output = _run_remote(command, args)
    try:
        meta = json.loads(output.splitlines()[-1])
    except Exception as exc:
        raise RuntimeError(f"无法解析远端快照结果: {output[:500]}") from exc

    key_id = os.getenv("oss_AccessKey_ID", "")
    key_secret = os.getenv("oss_AccessKey_key", "")
    if not key_id or not key_secret:
        raise SystemExit("本地缺少 oss_AccessKey_ID / oss_AccessKey_key，无法下载快照")
    bucket = oss2.Bucket(oss2.Auth(key_id, key_secret), meta["endpoint"], meta["bucket"])
    payload = bucket.get_object(meta["object"]).read()
    raw = gzip.decompress(payload)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = args.db.with_suffix(".db.tmp")
    tmp.write_bytes(raw)
    tmp.replace(args.db)
    print(f"快照完成: {meta['records']} 条，max_id={meta['max_id']}，latest={meta['latest']}")
    return meta


def _read_rows(db_path: Path, after_id: int, since_hours: int,
               include_ids: list[int] | None = None) -> tuple[list[dict], int]:
    cutoff = (datetime.now().astimezone() - timedelta(hours=since_hours)).isoformat(timespec="seconds")
    where = "(id > ? AND created_at >= ?)"
    params: list = [after_id, cutoff]
    retry_ids = sorted(set(include_ids or []))
    if retry_ids:
        placeholders = ",".join("?" for _ in retry_ids)
        where = f"({where} OR id IN ({placeholders}))"
        params.extend(retry_ids)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""SELECT id, session_id, question, answer, sources_json, price_status,
                       price_audit, llm_model, latency_ms, interrupted, created_at,
                       feedback, feedback_reason
                FROM answers WHERE {where} ORDER BY id""",
            params,
        ).fetchall()
        real, excluded = [], 0
        for row in rows:
            item = dict(row)
            if INTERNAL_SESSION_RE.match(item.get("session_id") or ""):
                excluded += 1
                continue
            # answers 没存原始 history，但同 session 的既有交付记录可恢复部分文本上下文。
            history = conn.execute(
                """SELECT id, question, answer FROM answers
                   WHERE session_id=? AND id<? ORDER BY id DESC LIMIT 4""",
                (item["session_id"], item["id"]),
            ).fetchall()
            item["history"] = [dict(x) for x in reversed(history)]
            real.append(item)
    finally:
        conn.close()
    return real, excluded


def _sources(row: dict) -> list:
    try:
        value = json.loads(row.get("sources_json") or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


def inspect_row(row: dict) -> dict:
    answer = row.get("answer") or ""
    hard = hard_checks(answer, row.get("price_status") or "")
    flags = []
    if not answer.strip():
        flags.append("empty_answer")
    if row.get("feedback") == "down":
        flags.append("feedback_down")
    if (row.get("price_audit") or "").startswith("mismatch"):
        # 审计器只掌握官方单价；用量×单价得到的小计/合计天然可能不在证据表内。
        # 派生计算先进入复核，不能仅凭 mismatch 直接判回答错误。
        derived = ("小计" in answer or "合计" in answer) and (
            "×" in answer or bool(re.search(r"附\s*\d+\s*张截图", row.get("question") or ""))
        )
        flags.append("derived_price_audit" if derived else "price_mismatch")
    if row.get("interrupted"):
        flags.append("interrupted")
    if hard["kb_leak"]:
        flags.append("internal_path_leak")
    latency = row.get("latency_ms") or 0
    if latency > 120000:
        flags.append("slow_over_120s")
    elif latency > 60000:
        flags.append("slow_over_60s")
    if answer.strip() and not _sources(row) and row.get("price_status") == "official":
        flags.append("official_without_sources")
    context_limits = []
    if re.search(r"附\s*\d+\s*张截图|\[图片\]", row.get("question") or ""):
        context_limits.append("image_unavailable")
    return {**row, "flags": flags, "hard": hard, "source_count": len(_sources(row)),
            "context_limits": context_limits}


def _mark_later_corrections(rows: list[dict]) -> None:
    """同会话后续明确承认“上一轮误写/确实算错”时，前一轮是已证实失败。"""
    for later in rows:
        answer = later.get("answer") or ""
        if "上一轮误" not in answer and "确实算错" not in answer:
            continue
        previous = [x for x in rows
                    if x["session_id"] == later["session_id"] and x["id"] < later["id"]]
        if not previous:
            continue
        row = max(previous, key=lambda x: x["id"])
        if "later_corrected_error" not in row["flags"]:
            row["flags"].append("later_corrected_error")
        row["corrected_by"] = later["id"]


def _priority(row: dict) -> tuple:
    severe = {"feedback_down", "price_mismatch", "empty_answer", "internal_path_leak",
              "later_corrected_error"}
    return (not row.get("retry_pending", False),
            not bool(severe.intersection(row["flags"])), not bool(row["flags"]), -row["id"])


def _judge(client: OpenAI, row: dict) -> dict:
    meta = {
        "price_status": row.get("price_status") or "",
        "price_audit": row.get("price_audit") or "",
        "latency_ms": row.get("latency_ms") or 0,
        "interrupted": bool(row.get("interrupted")),
        "source_count": row["source_count"],
        "deterministic_flags": row["flags"],
        "context_limits": row.get("context_limits", []),
    }
    history = "\n\n".join(
        f"#{h['id']} Q: {h['question'][:800]}\nA: {(h.get('answer') or '')[:1200]}"
        for h in row.get("history", [])[-2:]
    ) or "（无可用历史）"
    context_note = ""
    if row.get("context_limits"):
        context_note = ("原图未归档只是评审看不到，不代表当时的问答模型看不到；不得要求原回答"
                        "声明无法读图，也不得据此认定凭空捏造。只能检查文本内部一致性、后续轮次"
                        "是否承认并纠正错误。不要猜测图片内容，needs_replay=true。")
    prompt = f"""{_EXPRESSION_RUBRIC}

{_AUDIT_RUBRIC}
{context_note}
<history>
{history}
</history>
<question>
{row['question'][:2500]}
</question>
<answer>
{(row.get('answer') or '')[:5000]}
</answer>
<system_meta>{json.dumps(meta, ensure_ascii=False)}</system_meta>
history 是较早轮次，question/answer 才是本轮；system_meta 不属于回答正文。"""
    result = _llm_json(client, prompt, max_tokens=4000, retries=1,
                       model=_judge_model(), enable_thinking=False)
    if result and row.get("context_limits"):
        result["needs_replay"] = True
    return result


def _final_verdict(row: dict) -> str:
    hard_fail = {"empty_answer", "price_mismatch", "internal_path_leak", "later_corrected_error"}
    if hard_fail.intersection(row["flags"]):
        return "fail"
    judge = row.get("judge")
    if not judge:
        # 点踩或派生金额审计命中代表“需要复核”，不是已证实的语义失败。
        if {"feedback_down", "derived_price_audit"}.intersection(row["flags"]):
            return "warn"
        return "unreviewed"
    if judge.get("verdict") in ("pass", "warn", "fail"):
        return judge["verdict"]
    return "warn"


_IMPACT = {
    "pricing": ("app/price_verifier.py / app/tools.py", "高：影响报价与审计口径",
                "test_product_pricing.py、test_price_followup_competitor.py、价格审计"),
    "retrieval": ("app/knowledge.py / app/pipeline.py", "高：影响知识召回与来源展示",
                  "test_self.py、选型/方案题回放、来源人工核对"),
    "followup": ("app/pipeline.py / app/prompts.py", "高：影响多轮上下文与省略式追问",
                 "test_followup.py、test_colloquial_model.py、原会话带 history 重放"),
    "orchestration": ("app/pipeline.py / app/tools.py / app/prompts.py", "高：影响工具路由与主问答链路",
                      "test_toolloop_fx_clarify.py、test_toolcall_probe.py、重点 bad case 重放"),
    "presentation": ("app/prompts.py（必要时价格渲染代码）", "中：主要影响表达，不应改数值证据链",
                     "judge_quality.py、test_pitfall_regressions.py、客户可转发性复核"),
    "performance": ("app/pipeline.py / app/llm.py / app/searcher.py", "高：影响延迟、超时与工具调用策略",
                    "记录 avg/p95/max，与原日报对比；排除跨洋网络抖动后复测"),
    "storage": ("app/store.py / app/server.py", "中：影响落库和后台，不直接改变回答",
                "test_self.py、后台 stats/answers/export 鉴权回归"),
    "observability": ("app/store.py / app/pipeline.py / app/server.py",
                      "中：扩展审计元数据，不改变回答；需控制敏感数据保留范围",
                      "SQLite 老库迁移、截图/多轮问答、data 目录不入库、后台脱敏回归"),
    "other": ("待人工定位", "未知：先重放并归因，暂不建议改代码", "补充最小复现后再定回归范围"),
}


def _recommendations(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        if row["verdict"] not in ("fail", "warn"):
            continue
        judge = row.get("judge") or {}
        if "later_corrected_error" in row.get("flags", []):
            category = "orchestration"
            judge = {**judge, "suggestion": "后续轮次已证实前一轮计算错误；优先强制确定性计算工具并直接渲染成品，禁止 LLM 心算汇总"}
        elif not judge:
            # 点踩/派生审计/评审失败只是复核信号，没有语义证据时不自动生成代码建议。
            if "price_mismatch" in row["flags"]:
                category = "pricing"
            elif "internal_path_leak" in row["flags"]:
                category = "presentation"
            else:
                continue
        else:
            category = judge.get("category") or "other"
        if category not in _IMPACT:
            category = "other"
        groups[category].append(row)
    out = []
    for category, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        files, impact, regression = _IMPACT[category]
        suggestions = []
        for item in items:
            if "later_corrected_error" in item.get("flags", []):
                text = "后续轮次已证实前一轮计算错误；优先强制确定性计算工具并直接渲染成品，禁止 LLM 心算汇总"
            else:
                text = ((item.get("judge") or {}).get("suggestion") or "").strip()
            if text and text not in suggestions:
                suggestions.append(text)
        out.append({
            "category": category, "count": len(items),
            "answer_ids": [x["id"] for x in items], "files": files,
            "impact": impact, "regression": regression,
            "suggestions": suggestions[:3],
            "needs_replay": any((x.get("judge") or {}).get("needs_replay") for x in items),
        })
    limited = [x for x in rows if x.get("context_limits")]
    if limited:
        files, impact, regression = _IMPACT["observability"]
        out.append({
            "category": "observability", "count": len(limited),
            "answer_ids": [x["id"] for x in limited], "files": files,
            "impact": impact, "regression": regression,
            "suggestions": ["补存脱敏 history_json、tool_trace_json、image_count 与 request_id；不默认保存原图，避免扩大隐私面"],
            "needs_replay": False,
        })
    return out


def _write_report(rows: list[dict], excluded: int, args: argparse.Namespace,
                  before_id: int, max_id: int) -> tuple[Path, Path]:
    ts = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    counts = Counter(x["verdict"] for x in rows)
    latencies = [x["latency_ms"] / 1000 for x in rows if x.get("latency_ms")]
    flag_counts = Counter(flag for x in rows for flag in x["flags"])
    judged = sum(bool(x.get("judge")) for x in rows)
    judge_errors = sum(bool(x.get("judge_error")) for x in rows)
    context_limited = sum(bool(x.get("context_limits")) for x in rows)
    recommendations = _recommendations(rows)
    payload = {
        "ts": ts, "window_hours": args.since_hours, "after_id": before_id,
        "max_id": max_id, "records": len(rows), "excluded_internal": excluded,
        "judged": judged, "judge_errors": judge_errors, "context_limited": context_limited,
        "judge_model": _judge_model() if judged else "",
        "verdicts": dict(counts), "flags": dict(flag_counts),
        "latency_seconds": {
            "avg": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "p50": round(_percentile(latencies, 50), 1),
            "p95": round(_percentile(latencies, 95), 1),
            "max": round(max(latencies), 1) if latencies else 0,
        },
        "recommendations": recommendations, "results": rows,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / f"daily-{ts}.json"
    md_path = REPORT_DIR / f"daily-{ts}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [
        f"# 线上交付日报 {ts}", "",
        f"- 窗口：近 {args.since_hours} 小时，且 id > {before_id}；远端 max_id={max_id}",
        f"- 真实记录：**{len(rows)}**；排除内部评测：{excluded}；语义抽审成功/失败：{judged}/{judge_errors}（上限 {args.judge_limit}）",
        f"- 上下文受限（原图未归档）：{context_limited}；这些记录只能检查文本一致性，不能验证读图",
        f"- 判定：pass={counts['pass']} / warn={counts['warn']} / fail={counts['fail']} / 未抽审={counts['unreviewed']}",
        f"- 耗时：avg={payload['latency_seconds']['avg']}s / p50={payload['latency_seconds']['p50']}s "
        f"/ p95={payload['latency_seconds']['p95']}s / max={payload['latency_seconds']['max']}s",
        f"- 确定性信号：{json.dumps(dict(flag_counts), ensure_ascii=False) if flag_counts else '无'}", "",
        "> 未抽审不等于通过；语义评审不凭模型记忆判价格/规格事实。needs_replay=true 的条目需带原 history 重放后才能定界。",
        "> 本报告只给候选建议，未修改代码、未重启服务、未向线上追加测试请求。", "",
        "## 候选优化建议（需人工批准）", "",
    ]
    if not recommendations:
        md.append("本轮没有可由现有证据支持的代码优化项；保持观察，不为改而改。")
    for rec in recommendations:
        md += [
            f"### {rec['category']} · {rec['count']} 条", "",
            f"- 证据记录：{', '.join('#' + str(x) for x in rec['answer_ids'])}",
            f"- 候选方向：{'; '.join(rec['suggestions']) if rec['suggestions'] else '先人工复核明细，暂不落代码建议'}",
            f"- 若修改，重点文件：{rec['files']}",
            f"- 影响：{rec['impact']}",
            f"- 回归：{rec['regression']}",
            f"- 是否需先重放：{'是' if rec['needs_replay'] else '否/可由现有证据确认'}", "",
        ]
    md += ["## 重点明细", ""]
    for row in rows:
        if row["verdict"] == "pass":
            continue
        judge = row.get("judge") or {}
        md += [
            f"### #{row['id']} · {row['verdict'].upper()} · {row['created_at']}", "",
            f"**问题**：{row['question'][:1000]}", "",
            f"- 硬信号：{', '.join(row['flags']) or '无'}；耗时 {(row.get('latency_ms') or 0)/1000:.1f}s；来源 {row['source_count']} 条"
            + (f"；后续纠正证据 #{row['corrected_by']}" if row.get("corrected_by") else ""),
            f"- 价格证据：status={row.get('price_status') or '-'} / audit={row.get('price_audit') or '-'}",
            f"- 评审结论：{judge.get('expected') or row.get('judge_error') or '未语义抽审'}",
        ]
        issues = judge.get("issues") or []
        if issues:
            md += ["- 问题项："] + [f"  - {issue}" for issue in issues]
        if row.get("feedback_reason"):
            md.append(f"- 用户反馈：{row['feedback_reason'][:500]}")
        md += ["", "**回答节选**：", "", "```", (row.get("answer") or "")[:1800], "```", ""]
    md_path.write_text("\n".join(md), encoding="utf-8")
    return md_path, json_path


def run(args: argparse.Namespace) -> None:
    _load_environment()
    if not args.skip_sync:
        sync_snapshot(args)
    if not args.db.exists():
        raise SystemExit(f"快照不存在: {args.db}")
    state = {}
    if STATE_PATH.exists() and not args.reset_cursor:
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except ValueError:
            print("游标文件损坏，本轮按时间窗口读取")
    before_id = args.after_id if args.after_id is not None else int(state.get("last_id", 0))
    retry_ids = [] if args.reset_cursor or args.after_id is not None else state.get("retry_ids", [])
    raw_rows, excluded = _read_rows(args.db, before_id, args.since_hours, retry_ids)
    rows = [inspect_row(row) for row in raw_rows]
    _mark_later_corrections(rows)
    for row in rows:
        row["retry_pending"] = row["id"] in retry_ids
    max_id = 0
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM answers").fetchone()[0]
    finally:
        conn.close()

    selected = sorted(rows, key=_priority)[:args.judge_limit]
    if selected and not args.no_judge:
        if not os.getenv("JUDGE_API_KEY") or not os.getenv("JUDGE_BASE_URL"):
            raise SystemExit("语义抽审需要 JUDGE_API_KEY / JUDGE_BASE_URL；可用 --no-judge 跳过")
        client = OpenAI(api_key=os.environ["JUDGE_API_KEY"], base_url=os.environ["JUDGE_BASE_URL"],
                        timeout=120, max_retries=0)
        print(f"日报评审模型: {_judge_model()}（关闭思考）")
        selected_ids = {x["id"] for x in selected}
        consecutive_failures = 0
        for index, row in enumerate(selected, 1):
            print(f"抽审 {index}/{len(selected)} #{row['id']} {row['question'][:50]}")
            result = _judge(client, row)
            if result:
                row["judge"] = result
                consecutive_failures = 0
                continue
            row["judge_error"] = "评审调用或 JSON 解析失败"
            consecutive_failures += 1
            if consecutive_failures >= 2:
                print("连续两次评审失败，本轮熔断其余抽审；确定性报告仍正常生成")
                for pending in selected[index:]:
                    pending["judge_error"] = "评审熔断，未调用"
                break
        for row in rows:
            row["judge_selected"] = row["id"] in selected_ids
    for row in rows:
        row["verdict"] = _final_verdict(row)
        row.pop("sources_json", None)

    md_path, json_path = _write_report(rows, excluded, args, before_id, max_id)
    next_retry_ids = (
        retry_ids if args.judge_limit == 0
        else sorted(x["id"] for x in rows if x.get("judge_error"))
    )
    STATE_PATH.write_text(json.dumps({
        "last_id": max_id, "retry_ids": next_retry_ids,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "report": md_path.name,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"日报: {md_path}")
    print(f"结构化结果: {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="线上问答只读日报")
    parser.add_argument("--instance-id", default=os.getenv("QA_AUDIT_INSTANCE_ID", ""))
    parser.add_argument("--region", default=os.getenv("QA_AUDIT_ECS_REGION", "cn-beijing"))
    parser.add_argument("--profile", default=os.getenv("QA_AUDIT_ECS_PROFILE", "ecsdeploy"))
    parser.add_argument("--container", default=os.getenv("QA_AUDIT_CONTAINER", "alibaba-presale-agent"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--skip-sync", action="store_true", help="复用本地快照，不访问 ECS/OSS")
    parser.add_argument("--since-hours", type=int, default=24)
    parser.add_argument("--after-id", type=int, default=None, help="本轮覆盖游标，仅用于补跑/首次基线")
    parser.add_argument("--reset-cursor", action="store_true", help="忽略已存游标，按时间窗口补跑")
    parser.add_argument("--judge-limit", type=int, default=8, help="语义抽审上限，0 等同 --no-judge")
    parser.add_argument("--no-judge", action="store_true", help="只做确定性检查，不调用评审模型")
    parser.add_argument("--remote-timeout", type=int, default=120)
    args = parser.parse_args()
    if args.since_hours <= 0 or args.judge_limit < 0:
        parser.error("since-hours 必须 >0，judge-limit 必须 >=0")
    if args.no_judge:
        args.judge_limit = 0
    run(args)


if __name__ == "__main__":
    main()
