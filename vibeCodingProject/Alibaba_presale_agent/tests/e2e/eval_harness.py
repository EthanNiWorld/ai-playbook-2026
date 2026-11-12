"""评测集闭环 — 从历史交付记录自迭代生成 golden set，回归评估当前架构

三个子命令（准确性优先，完成时间并列重要）：
  build    挖 qa.db 历史 → LLM 提炼评测锚点 → 生成 golden set
  run      回放 golden set 打当前架构 → 准确性(pass/warn/fail) + 耗时(avg/p95/max)
  refresh  评判新增历史记录 → 自迭代追加 golden set（覆盖新题型）

运行:
  .venv/bin/python tests/e2e/eval_harness.py build --limit 24
  .venv/bin/python tests/e2e/eval_harness.py run
  .venv/bin/python tests/e2e/eval_harness.py refresh --limit 10

前置: 8000 端口服务就绪；环境变量含 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL
产物: data/eval/golden_set.json（评测集，含真实客户问题 → 已 gitignore，不入库）
      data/reports/eval-<ts>.md/.json（回归报告）

分层判据（沿用项目「按出错成本分层」+ judge_quality.py）：
  - 代码硬指标：价格正确性由「实时证据链」保证——价格类硬门 = price_status==official
    且 price_audit 非 mismatch（**不**拿历史价格数字做等值断言，避免官方调价被误判回归）；
    内部路径泄漏、表格列序由代码判。
  - GLM-5.3 跨厂商评审：要点覆盖 + 表达四维（structure/caliber/brevity/usability），
    绝不用 judge 自身记忆判价格对错。
  - 耗时：pipeline 已落库 latency_ms，run 直接取 done 事件，统计 avg/p95/max。

已知局限：run 以单轮独立回放（不携带历史），依赖上下文的省略式追问
（如“似乎没明白打几折的意思”）复现会失真，build 后可人工剔除此类 case。
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import httpx
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge_quality import (  # noqa: E402  复用既有分层评审判据
    JUDGE_MODEL, RUBRIC, ask, hard_checks, verdict_of,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "qa.db"
SET_PATH = ROOT / "data" / "eval" / "golden_set.json"
BASELINE_PATH = ROOT / "data" / "eval" / "baseline.json"
REPORT_DIR = ROOT / "data" / "reports"
BASE = os.getenv("EVAL_BASE", "http://127.0.0.1:8000")
PRICE_RE = re.compile(r"\$\s?\d+(?:\.\d+)?")

# ── 评测锚点提炼（build/refresh 用）──
EXTRACT_RUBRIC = """你是问答服务评测集的构建员。给定一条真实客户问题与当时的回答，
提炼出可复现的评测锚点，用于日后回归测试同一架构。

【重要边界】价格数字由代码从官方定价页抽取注入，不要用你的记忆判断价格对错，
锚点也不要依赖具体价格数字（官方会调价，依赖数字会造成假回归）。

只提炼以下内容：
- type：题型，取值 price/compare/spec/agent/fx/tpm/chitchat/stock/love/other
- must_contain：正确回答必须覆盖的要点（2-5 条，表述稳定，如"给出新加坡USD六列表格"
  "结论先行对比两模型""明确拒答不存在的型号"，不要写具体价格）
- must_avoid：必须避免的问题（如"答非所问""泄漏内部文件路径""编造不存在的型号"）
- focus：一句话考点

输出严格 JSON（不要 markdown 代码块、不要额外文字）：
{"type":"...","must_contain":["..."],"must_avoid":["..."],"focus":"..."}"""


def _client() -> OpenAI:
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("未设置 DASHSCOPE_API_KEY")
        sys.exit(2)
    return OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                  base_url=os.environ["DASHSCOPE_BASE_URL"])


def _llm_json(client: OpenAI, prompt: str) -> dict:
    """调 judge 模型取严格 JSON（GLM-5.3 强制思考，max_tokens 给足预算）。

    带重试：远端 DashScope 端点偶发 DNS/连接抖动（本机 DNS 劫持），
    单次瞬时错误不应中断整轮评测。
    """
    last_err = ""
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                # 评审 prompt 较长，GLM-5.3 思考偶发吃 >16k tokens（实测 finish=length），
                # cap 提到 24000 防截断；正常 case 用量不变，仅 outlier 受益
                max_tokens=24000, temperature=0,
            )
            choice = resp.choices[0]
            raw = (choice.message.content or "").strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.M).strip()
            try:
                return json.loads(raw)
            except Exception as e:
                fin = choice.finish_reason
                used = resp.usage.total_tokens if resp.usage else "?"
                print(f"    [JSON 解析失败] {str(e)[:60]} | finish={fin} tokens={used} | raw={raw[:120]!r}")
                return {}
        except Exception as e:
            last_err = str(e)[:100]
            print(f"    [judge 连接失败 attempt{attempt + 1}/3] {last_err}")
            time.sleep(3 * (attempt + 1))
    print(f"    [judge 三次重试均失败] {last_err}")
    return {}


def _norm_q(q: str) -> str:
    return re.sub(r"\s+", "", (q or "").lower())


def _read_history(db_path: Path) -> list[dict]:
    """读历史交付记录（非中断、有答案），按 id 升序。

    排除 judge-* 会话：run/judge_quality 会往 qa.db 写评测记录，
    不过滤会让 refresh 把评测自身记录重新 ingest（自迭代污染）。
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, question, answer, price_status, price_audit, latency_ms,"
            " feedback, created_at FROM answers"
            " WHERE interrupted=0 AND answer!='' AND session_id NOT LIKE 'judge-%'"
            " ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    src = Path(db_path).stem
    out = []
    for r in rows:
        d = dict(r)
        d["_src"] = src          # 来源库标签（local/remote-qa），跨库 id 会碰撞，需前缀区分
        d["_db"] = str(db_path)
        out.append(d)
    return out


def _read_merged(db_paths: list[str]) -> list[dict]:
    """读多个 qa.db（本地 + 远端拷贝）并合并，每条带来源标签。"""
    rows: list[dict] = []
    for db in db_paths:
        p = Path(db)
        if not p.exists():
            print(f"[跳过] 库不存在: {db}")
            continue
        part = _read_history(p)
        print(f"  库 {p.name}: {len(part)} 条有效记录")
        rows += part
    return rows


def _pick_candidates(rows: list[dict], limit: int) -> list[dict]:
    """跨库去重 + 优先级排序：踩/审计不符(回归硬case) > 官方核实 > 其他。

    同问题跨库保留 created_at 最新一条；同优先级内新记录优先。
    """
    seen: dict[str, dict] = {}
    for r in rows:
        k = _norm_q(r["question"])
        if k not in seen or (r.get("created_at") or "") > (seen[k].get("created_at") or ""):
            seen[k] = r
    uniq = list(seen.values())

    def prio(r):
        if r.get("feedback") == "down" or (r.get("price_audit") or "").startswith("mismatch"):
            return 0
        if r.get("price_status") == "official":
            return 1
        return 2

    uniq.sort(key=lambda r: r.get("created_at") or "", reverse=True)  # 新→旧
    uniq.sort(key=prio)  # 稳定排序，同优先级内保持新记录优先
    return uniq[:limit]


def _extract_anchor(client: OpenAI, r: dict) -> dict:
    prompt = f"""{EXTRACT_RUBRIC}

<question>
{r['question']}
</question>

<answer>
{r['answer'][:3000]}
</answer>

只提炼锚点，直接输出 JSON。"""
    a = _llm_json(client, prompt)
    return {
        "type": a.get("type", "other"),
        "must_contain": a.get("must_contain", [])[:6],
        "must_avoid": a.get("must_avoid", [])[:6],
        "focus": a.get("focus", ""),
    }


def _load_set() -> dict:
    if SET_PATH.exists():
        return json.loads(SET_PATH.read_text(encoding="utf-8"))
    return {"meta": {}, "cases": []}


def _save_set(s: dict) -> None:
    SET_PATH.parent.mkdir(parents=True, exist_ok=True)
    SET_PATH.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_build(args) -> None:
    rows = _read_merged(args.db)
    cands = _pick_candidates(rows, args.limit)
    print(f"合并 {len(rows)} 条 → 跨库去重优先选取 {len(cands)} 条构建评测集")
    client = _client()
    cases = []
    for i, r in enumerate(cands, 1):
        print(f"[{i}/{len(cands)}] {r['_src']}#{r['id']} {r['question'][:46]}")
        anchor = _extract_anchor(client, r)
        ref_prices = sorted(set(PRICE_RE.findall(r["answer"]))) if r["price_status"] == "official" else []
        cases.append({
            "id": f"{r['_src']}-{r['id']}",
            "question": r["question"],
            "source": r["_src"],
            "source_answer_id": r["id"],
            "feedback": r.get("feedback") or "",
            "ref_price_status": r["price_status"],
            "ref_price_numbers": ref_prices,   # 仅信息展示，不作等值硬门
            "ref_latency_ms": r["latency_ms"],
            **anchor,
        })
        print(f"    type={anchor['type']} focus={anchor['focus'][:40]}")
    sources = {}
    for db in args.db:
        part = [r for r in rows if r["_db"] == str(Path(db))]
        sources[str(Path(db))] = {
            "last_max_id": max((r["id"] for r in part), default=0),
            "records": len(part),
        }
    s = {
        "meta": {
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "sources": sources,
            "judge_model": JUDGE_MODEL,
            "count": len(cases),
        },
        "cases": cases,
    }
    _save_set(s)
    print(f"\n评测集已生成: {SET_PATH}（{len(cases)} case，来源 {len(sources)} 库）")


def _run_judge(client: OpenAI, case: dict, answer: str, hard: dict) -> dict:
    """要点覆盖 + 表达四维评审（标签隔离，避免元数据被当回答内容）。"""
    mc = "\n".join(f"- {x}" for x in case.get("must_contain", [])) or "（无）"
    ma = "\n".join(f"- {x}" for x in case.get("must_avoid", [])) or "（无）"
    prompt = f"""{RUBRIC}

额外评审维度 coverage（1-5）：回答是否覆盖以下必须要点。
<must_contain>
{mc}
</must_contain>
<must_avoid>
{ma}
</must_avoid>

<question>
{case['question']}
</question>

<answer>
{answer}
</answer>

<system_meta has_table="{hard['has_table']}" price_status="{hard['price_status']}"
 kb_leak="{len(hard['kb_leak']) > 0}" />
<!-- system_meta 是系统元数据，不属于回答内容，不要当作回答泄漏来扣分 -->

只评审 <answer> 内文本。输出 JSON，scores 增加 coverage 键：
{{"scores":{{"structure":n,"caliber":n,"brevity":n,"usability":n,"coverage":n}},
 "verdict":"pass|warn|fail","issues":["..."],"one_line":"..."}}"""
    return _llm_json(client, prompt)


def _percentile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = max(0, min(len(s) - 1, int(round(p / 100 * (len(s) - 1)))))
    return s[k]


def cmd_run(args) -> None:
    s = _load_set()
    cases = s.get("cases", [])
    if not cases:
        print("评测集为空，先跑 build")
        sys.exit(2)
    if args.limit:
        cases = cases[:args.limit]
    try:
        httpx.get(f"{BASE}/api/health", timeout=5).raise_for_status()
    except Exception as e:
        print(f"服务不可用: {e}")
        sys.exit(2)
    client = _client()
    print("=" * 64)
    print(f"架构回归评测 — {len(cases)} case · 生成 qwen / 评审 {JUDGE_MODEL}")
    print("=" * 64)

    results = []
    for i, case in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] {case['id']} ({case.get('type')}) {case['question'][:46]}")
        try:
            r = ask(case["question"])
        except Exception as e:
            print(f"  ❌ 问答连接失败: {str(e)[:80]}")
            results.append({**case, "verdict": "fail", "phase": "answer",
                            "issues": [str(e)[:120]], "latency_ms": 0})
            continue
        if r["error"] or not r["answer"]:
            print(f"  ❌ 问答失败: {r['error'][:80]}")
            results.append({**case, "verdict": "fail", "phase": "answer",
                            "issues": [r["error"]], "latency_ms": 0})
            continue
        done = r["done"]
        pstatus = done.get("price_status", "")
        paudit = done.get("price_audit", "")
        latency = done.get("latency_ms") or int(r["elapsed"] * 1000)
        hard = hard_checks(r["answer"], pstatus)

        # 准确性硬门（代码层，先于 judge）
        hard_fail = []
        if hard["kb_leak"]:
            hard_fail.append("内部路径泄漏")
        # 价格硬门只作用于真正的价格题（走 verify_price 证据链）。
        # TPM/对比等题虽可能含官方价，但走 estimate_tpm_cost 等工具，
        # price_status 不由 verify_price 置位，不能拿它当硬门（否则误判）。
        if case.get("type") == "price":
            if pstatus != "official":
                hard_fail.append(f"价格未官方核实({pstatus or 'none'})")
            if paudit.startswith("mismatch"):
                hard_fail.append("价格审计不符")

        jd = _run_judge(client, case, r["answer"], hard)
        v = "fail" if hard_fail else verdict_of(hard, jd)
        sc = jd.get("scores") or {}
        print(f"  {len(r['answer'])}字 / {latency/1000:.1f}s / {v.upper()} "
              + " ".join(f"{k}={sc.get(k, '-')}" for k in
                         ("coverage", "structure", "caliber", "brevity", "usability")))
        if hard_fail:
            print(f"  硬门失败: {hard_fail}")
        print(f"  结论: {jd.get('one_line', '')[:70]}")
        results.append({
            **case, "answer": r["answer"], "hard": hard, "judge": jd,
            "verdict": v, "hard_fail": hard_fail, "latency_ms": latency,
            "price_status": pstatus, "price_audit": paudit,
            "answer_id": done.get("answer_id"),
        })

    _report(results, s, args)


def _compare(cur: dict, base: dict | None) -> dict:
    """本次 vs 基线：准确性/耗时双指标 delta + 逐 case 判定迁移 + 迭代结论。

    迭代判据（准确性优先，耗时并列）：
      - 准确性硬门退化（pass→fail 且含 hard_fail）是一票否决；
      - judge 判定退化（无 hard_fail）可能是评审噪声，提示复跑；
      - 通过率↑ 或 持平且 p95↓ → 改进。
    """
    if not base:
        return {"has_base": False}
    ca, ba = cur["accuracy"], base.get("accuracy", 0)
    cl, bl = cur["latency"], base.get("latency", {})
    acc_d = round(ca - ba, 1)
    lat_avg_d = round(cl["avg"] - bl.get("avg", 0), 1)
    lat_p95_d = round(cl["p95"] - bl.get("p95", 0), 1)
    bmap = {x["id"]: x for x in base.get("results", [])}
    regress, improve, hard_regress = [], [], []
    for x in cur["results"]:
        b = bmap.get(x["id"])
        if not b:
            continue
        bv, cv = b.get("verdict"), x["verdict"]
        if bv == "pass" and cv == "fail":
            regress.append(x["id"])
            if x.get("hard_fail"):
                hard_regress.append(x["id"])
        elif bv in ("fail", "warn") and cv == "pass":
            improve.append(x["id"])
    if hard_regress:
        verdict = "❌ 不可接受：准确性硬门退化"
    elif regress:
        verdict = "⚠️ judge 判定退化（可能噪声，建议复跑确认）"
    elif acc_d > 0 or (acc_d == 0 and lat_p95_d < -1):
        verdict = "✅ 改进"
    elif acc_d < 0:
        verdict = "⚠️ 通过率下降"
    elif lat_p95_d > 1:
        verdict = "⚠️ 耗时上升（准确性持平）"
    else:
        verdict = "➖ 基本持平"
    return {
        "has_base": True, "base_ts": base.get("ts", "?"),
        "acc_delta": acc_d, "lat_avg_delta": lat_avg_d, "lat_p95_delta": lat_p95_d,
        "regressions": regress, "improvements": improve, "hard_regressions": hard_regress,
        "verdict": verdict,
    }


def _report(results: list[dict], s: dict, args) -> None:
    cnt = {"pass": 0, "warn": 0, "fail": 0}
    for x in results:
        cnt[x["verdict"]] = cnt.get(x["verdict"], 0) + 1
    n = len(results)
    acc = round(cnt["pass"] / n * 100, 1) if n else 0.0
    lats = [x["latency_ms"] / 1000 for x in results if x.get("latency_ms")]
    lat_stat = {
        "avg": round(sum(lats) / len(lats), 1) if lats else 0,
        "p95": round(_percentile(lats, 95), 1),
        "max": round(max(lats), 1) if lats else 0,
    }
    scored = [x["judge"]["scores"] for x in results if x.get("judge", {}).get("scores")]
    avg = {}
    for k in ("coverage", "structure", "caliber", "brevity", "usability"):
        vals = [sc[k] for sc in scored if isinstance(sc.get(k), (int, float))]
        avg[k] = round(sum(vals) / len(vals), 2) if vals else None

    # 基线对比：优先 --baseline 指定 > 固定基线 baseline.json > 上次报告
    ts = time.strftime("%Y%m%d-%H%M%S")
    payload = {"ts": ts, "judge_model": JUDGE_MODEL, "accuracy": acc,
               "count": cnt, "latency": lat_stat, "avg_scores": avg,
               "set_meta": s.get("meta", {}), "results": results}
    base = None
    if getattr(args, "baseline", None):
        bp = Path(args.baseline)
        base = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else None
    elif BASELINE_PATH.exists():
        base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    else:
        base = _latest_report()
    cmp = _compare(payload, base)
    payload["comparison"] = cmp

    print("\n" + "-" * 64)
    print(f"准确性: pass={cnt['pass']} warn={cnt['warn']} fail={cnt['fail']} → 通过率 {acc}%")
    print(f"耗时: avg={lat_stat['avg']}s p95={lat_stat['p95']}s max={lat_stat['max']}s")
    print(f"均分(n={len(scored)}): " + " ".join(f"{k}={v}" for k, v in avg.items()))
    if cmp.get("has_base"):
        print(f"—— 对比基线 {cmp['base_ts']} ——")
        print(f"  准确性 {cmp['acc_delta']:+.1f}pp | 耗时 avg {cmp['lat_avg_delta']:+.1f}s / p95 {cmp['lat_p95_delta']:+.1f}s")
        if cmp["regressions"]:
            print(f"  ⚠️ 退化(pass→fail): {cmp['regressions']}")
        if cmp["improvements"]:
            print(f"  ✅ 改进(→pass): {cmp['improvements']}")
        print(f"  迭代结论: {cmp['verdict']}")
    else:
        print("（无基线，首次运行；用 --save-baseline 固定本次为基线）")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"eval-{ts}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [f"# 架构回归评测 {ts}", "",
          f"- 评测集: {s.get('meta', {}).get('count', '?')} case（构建于 {s.get('meta', {}).get('built_at', '?')}）",
          f"- 生成模型: {os.getenv('QA_MODEL', 'qwen3.8-max')} 评审: {JUDGE_MODEL}",
          f"- **准确性**: pass={cnt['pass']} / warn={cnt['warn']} / fail={cnt['fail']} → 通过率 **{acc}%**",
          f"- **耗时**: avg={lat_stat['avg']}s / p95={lat_stat['p95']}s / max={lat_stat['max']}s",
          f"- 均分: " + " ".join(f"{k} {v}" for k, v in avg.items()), ""]
    if cmp.get("has_base"):
        md += [f"## 基线对比（vs {cmp['base_ts']}）", "",
               f"- 准确性 **{cmp['acc_delta']:+.1f}pp** | 耗时 avg **{cmp['lat_avg_delta']:+.1f}s** / p95 **{cmp['lat_p95_delta']:+.1f}s**",
               f"- 迭代结论: **{cmp['verdict']}**", ""]
        if cmp["regressions"]:
            md += [f"> ⚠️ 退化(pass→fail): {', '.join(cmp['regressions'])}", ""]
        if cmp["improvements"]:
            md += [f"> ✅ 改进(→pass): {', '.join(cmp['improvements'])}", ""]
    md += ["| case | 题型 | 判定 | 耗时 | coverage | 硬门 | 结论 |",
           "|---|---|---|---|---|---|---|"]
    for x in results:
        sc = x.get("judge", {}).get("scores") or {}
        md.append(f"| {x['id']} | {x.get('type', '')} | {x['verdict']} | "
                  f"{(x.get('latency_ms') or 0)/1000:.1f}s | {sc.get('coverage', '-')} | "
                  f"{';'.join(x.get('hard_fail', [])) or '—'} | {x.get('judge', {}).get('one_line', '')[:40]} |")
    md += ["", "## 明细", ""]
    for x in results:
        md += [f"### {x['id']} · {x['verdict'].upper()} · {x.get('type', '')}", "",
               f"**问题**：{x['question']} ", f"**考点**：{x.get('focus', '')}", ""]
        if x.get("hard_fail"):
            md += [f"**硬门失败**：{'; '.join(x['hard_fail'])}", ""]
        if x.get("judge", {}).get("issues"):
            md += ["**问题项**："] + [f"- {i}" for i in x["judge"]["issues"]] + [""]
        md += ["**回答原文**：", "", "```", x.get("answer", "")[:1500], "```", ""]
    (REPORT_DIR / f"eval-{ts}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"报告: {REPORT_DIR}/eval-{ts}.md")
    if getattr(args, "save_baseline", False):
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"已固定为基线: {BASELINE_PATH}")
    sys.exit(0 if cnt["fail"] == 0 else 1)


def _latest_report() -> dict | None:
    files = sorted(REPORT_DIR.glob("eval-*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return None


def cmd_refresh(args) -> None:
    """自迭代：逐库评判 last_max_id 之后的新记录，追加覆盖新题型的 case。"""
    s = _load_set()
    if not s.get("cases"):
        print("评测集为空，先跑 build")
        sys.exit(2)
    meta = s.get("meta", {})
    sources = meta.get("sources", {})
    # 兼容旧单库格式 meta.last_max_id
    rows = _read_merged(args.db)
    new = []
    for db in args.db:
        key = str(Path(db))
        last_id = sources.get(key, {}).get("last_max_id", meta.get("last_max_id", 0))
        new += [r for r in rows if r["_db"] == key and r["id"] > last_id]
    existing = {_norm_q(c["question"]) for c in s["cases"]}
    fresh = [r for r in new if _norm_q(r["question"]) not in existing]
    fresh = _pick_candidates(fresh, args.limit)
    if not fresh:
        print(f"无新增可评测问题（新记录 {len(new)} 条均已覆盖）")
        return
    print(f"新增 {len(new)} 条 → 跨库去重后 {len(fresh)} 条待评判追加")
    client = _client()
    added = 0
    for i, r in enumerate(fresh, 1):
        print(f"[{i}/{len(fresh)}] {r['_src']}#{r['id']} {r['question'][:46]}")
        anchor = _extract_anchor(client, r)
        ref_prices = sorted(set(PRICE_RE.findall(r["answer"]))) if r["price_status"] == "official" else []
        s["cases"].append({
            "id": f"{r['_src']}-{r['id']}", "question": r["question"],
            "source": r["_src"], "source_answer_id": r["id"],
            "feedback": r.get("feedback") or "",
            "ref_price_status": r["price_status"], "ref_price_numbers": ref_prices,
            "ref_latency_ms": r["latency_ms"], "added_by": "refresh", **anchor,
        })
        added += 1
        print(f"    + type={anchor['type']} focus={anchor['focus'][:40]}")
    for db in args.db:
        key = str(Path(db))
        part = [r for r in rows if r["_db"] == key]
        prev = sources.get(key, {}).get("last_max_id", 0)
        sources[key] = {"last_max_id": max((r["id"] for r in part), default=prev),
                        "records": len(part)}
    meta["sources"] = sources
    meta.pop("last_max_id", None)
    meta["count"] = len(s["cases"])
    meta["refreshed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    s["meta"] = meta
    _save_set(s)
    print(f"\n自迭代追加 {added} case，评测集现 {len(s['cases'])} case → {SET_PATH}")


def main():
    ap = argparse.ArgumentParser(description="评测集闭环：build/run/refresh")
    ap.add_argument("cmd", choices=["build", "run", "refresh"])
    ap.add_argument("--limit", type=int, default=24, help="build/refresh 选取条数上限")
    ap.add_argument("--db", nargs="+", default=[str(DEFAULT_DB)],
                    help="qa.db 路径，可多个（本地 + 远端拷贝）合并去重")
    ap.add_argument("--save-baseline", action="store_true",
                    help="run 后把本次结果固定为基线（data/eval/baseline.json）")
    ap.add_argument("--baseline", default=None,
                    help="run 对比的基线文件（默认 baseline.json，无则上次报告）")
    args = ap.parse_args()
    {"build": cmd_build, "run": cmd_run, "refresh": cmd_refresh}[args.cmd](args)


if __name__ == "__main__":
    main()
