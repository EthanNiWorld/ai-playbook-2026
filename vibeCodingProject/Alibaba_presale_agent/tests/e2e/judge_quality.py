"""回答质量评审 — 代码硬指标 + GLM-5.3 表达评审（交叉厂商，避免自评偏好）

运行:
  .venv/bin/python tests/e2e/judge_quality.py          # 全量 6 个 case
  .venv/bin/python tests/e2e/judge_quality.py 2        # 只跑前 2 个（快速自检）

前置: 8000 端口服务已就绪；环境变量需含 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL

分层原则（沿用项目「按出错成本分层」）：
  代码层负责确定性的东西 —— 价格数字集合、表格列序、内部路径泄漏、长度。
  GLM-5.3 只负责它擅长的表达层 —— 结构可读性、口径、简洁度、客户可用性。
  绝不让 judge 用自身记忆判价格对错（价格只来自定价页证据）。

产物: data/reports/quality-<ts>.md + .json（data/ 已 gitignore）
副作用: 每个 case 会向 data/qa.db 写入 1 条回答记录，验证后可按时间清理。
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from openai import OpenAI

BASE = "http://127.0.0.1:8000"
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "glm-5.3")
REPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "reports"

# ── 覆盖面：不同题型 + 一条幻觉诱导 ──
CASES = [
    {"id": "price-main", "q": "Qwen3.8-Max 的价格是多少？",
     "focus": "主定价页路径 · 六列表格"},
    {"id": "price-detail", "q": "qwen3.8-flash 的价格是多少？",
     "focus": "模型详情页路径 · 缓存拆列"},
    {"id": "price-halluc", "q": "glm-9.9-turbo 的价格是多少？",
     "focus": "不存在的模型 · 抗幻觉/拒答边界"},
    {"id": "compare", "q": "qwen3.8-max 和 deepseek-v4-pro 哪个更适合长文本 RAG 场景？",
     "focus": "选型对比 · 无表格也应有结论"},
    {"id": "agent", "q": "百炼平台上怎么搭建一个多 Agent 协作的应用？",
     "focus": "方案类 · 可执行性"},
    {"id": "video", "q": "Wan3.0-Video 支持哪些分辨率和规格？",
     "focus": "规格类 · 结构化列举"},
]

TABLE_HEADER = ("| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) "
                "| 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |")
KB_LEAK_RE = re.compile(r"knowledge/|alibaba-ai-hub/|[\w-]+\.md\b")
PRICE_RE = re.compile(r"\$\s?\d+(?:\.\d+)?")

RUBRIC = """你是阿里云百炼模型问答服务的质量评审员，服务对象是内部 BD 与客户。

【重要边界】价格数字由代码从阿里云官方定价页抽取并注入表格，生成模型不得改动。
不要用你自己的记忆去判断价格对错，也不要质疑数字是否"符合你的印象"。
你只评审表达与交付质量。

评分维度（各 1-5 分，5 为最好）：
- structure：结构可读性。价格类是否给出六列表格（Region/输入/缓存输入/输出/显式缓存创建/备注）、
  列序一致；非价格类是否有清晰分层（结论先行、要点可扫描）。
- caliber：口径一致性。以新加坡节点 USD 为主口径；未混入 Batch 折扣价；
  未输出免费额度/营销话术；未把内地人民币价当主口径。
- brevity：简洁度。价格类表格之外不超过 2 句说明；无模板化开场与重复啰嗦。
- usability：客户可用性。BD 能否直接转发；是否答非所问；有无内部实现痕迹
  （文件路径、变量名、prompt 字样、"系统"自述等）。

输出严格 JSON（不要 markdown 代码块、不要任何额外文字）：
{"scores":{"structure":n,"caliber":n,"brevity":n,"usability":n},
 "verdict":"pass|warn|fail",
 "issues":["具体、可执行的问题；没有则空数组"],
 "one_line":"一句话结论"}

判 fail：答非所问、编造证据、泄漏内部实现细节。
判 warn：有轻微冗余或口径瑕疵，但客户仍可读。"""


def ask(question: str) -> dict:
    """调 /api/chat 跑一轮真实问答，返回答案与元信息"""
    t0 = time.time()
    r = httpx.post(f"{BASE}/api/chat",
                   json={"question": question, "history": [],
                         "session_id": f"judge-{int(time.time())}"},
                   timeout=240)
    parts, done, err = [], {}, ""
    for line in r.text.splitlines():
        if not line.startswith("data: "):
            continue
        ev = json.loads(line[6:])
        if ev["type"] == "delta":
            parts.append(ev["text"])
        elif ev["type"] == "done":
            done = ev
        elif ev["type"] == "error":
            err = ev.get("message", "")
    return {"answer": "".join(parts), "done": done, "error": err,
            "elapsed": round(time.time() - t0, 1)}


def hard_checks(answer: str, price_status: str) -> dict:
    """代码层：确定性指标，不依赖任何模型判断"""
    lines = answer.splitlines()
    has_table = any(l.strip().startswith("| Region") for l in lines)
    header_ok = TABLE_HEADER in answer.replace("  ", " ")
    # 表格外正文长度（粗略：去掉表格行与链接行）
    prose = [l for l in lines
             if not l.strip().startswith("|") and l.strip()]
    prose_chars = len("\n".join(prose))
    leaks = KB_LEAK_RE.findall(answer)
    return {
        "price_status": price_status,
        "has_table": has_table,
        "header_order_ok": header_ok,
        "kb_leak": sorted(set(leaks)),
        "price_numbers": sorted(set(PRICE_RE.findall(answer))),
        "prose_chars": prose_chars,
        "chars": len(answer),
    }


def judge(client: OpenAI, question: str, answer: str, hard: dict) -> dict:
    """GLM-5.3 表达评审。元信息用标签隔离，避免被判成"回答内容"（实测踩过）"""
    prompt = f"""{RUBRIC}

<question>
{question}
</question>

<answer>
{answer}
</answer>

<system_meta has_table="{hard['has_table']}" price_status="{hard['price_status']}"
 kb_leak="{len(hard['kb_leak']) > 0}" />
<!-- system_meta 是系统元数据，不属于回答内容，仅供你判断结构类型，不要当作回答泄漏来扣分 -->

只评审 <answer> 标签内的文本，直接输出 JSON。"""
    t0 = time.time()
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        # GLM-5.3 强制思考，实测思考可吃 3.6k tokens，预算不足会把正文挤空
        max_tokens=8000,
        temperature=0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.M).strip()
    out = {"raw_ok": True, "elapsed": round(time.time() - t0, 1),
           "tokens": resp.usage.total_tokens if resp.usage else None}
    try:
        out.update(json.loads(raw))
    except Exception as e:
        out.update({"raw_ok": False, "parse_error": str(e)[:120], "raw": raw[:400],
                    "verdict": "unknown", "scores": {}, "issues": [], "one_line": ""})
        print(f"    [judge 解析失败] {str(e)[:80]} | raw={raw[:200]!r}")
    return out


def verdict_of(hard: dict, jd: dict) -> str:
    """代码层硬失败优先于 judge 结论"""
    if hard["kb_leak"]:
        return "fail"
    if jd.get("verdict") == "fail":
        return "fail"
    if not jd.get("raw_ok"):
        return "warn"
    if jd.get("verdict") == "warn":
        return "warn"
    weak = [k for k, v in (jd.get("scores") or {}).items() if isinstance(v, int) and v <= 3]
    return "warn" if weak else "pass"


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(CASES)
    cases = CASES[:limit]

    if not os.getenv("DASHSCOPE_API_KEY"):
        print("未设置 DASHSCOPE_API_KEY")
        sys.exit(2)
    try:
        httpx.get(f"{BASE}/api/health", timeout=5).raise_for_status()
    except Exception as e:
        print(f"服务不可用: {e}")
        sys.exit(2)

    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                    base_url=os.environ["DASHSCOPE_BASE_URL"])

    print("=" * 64)
    print(f"回答质量评审 — 生成 qwen / 评审 {JUDGE_MODEL}（交叉厂商）")
    print("=" * 64)

    results = []
    for i, case in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] {case['id']} · {case['focus']}")
        print(f"  Q: {case['q']}")
        r = ask(case["q"])
        if r["error"] or not r["answer"]:
            print(f"  ❌ 问答失败: {r['error'][:100]}")
            results.append({**case, "verdict": "fail", "phase": "answer",
                            "answer": r["answer"], "issues": [r["error"]]})
            continue
        hard = hard_checks(r["answer"], r["done"].get("price_status", ""))
        print(f"  A: {len(r['answer'])} 字 / {r['elapsed']}s / "
              f"price_status={hard['price_status'] or '-'}")
        print(f"  硬指标: 表格={hard['has_table']} 列序={hard['header_order_ok']} "
              f"路径泄漏={hard['kb_leak'] or '无'} 数字={hard['price_numbers'] or '无'}")

        jd = judge(client, case["q"], r["answer"], hard)
        v = verdict_of(hard, jd)
        s = jd.get("scores") or {}
        print(f"  评审({jd['elapsed']}s, {jd.get('tokens')} tok): {v.upper()} "
              + " ".join(f"{k}={s.get(k, '-')}" for k in
                         ("structure", "caliber", "brevity", "usability")))
        print(f"  结论: {jd.get('one_line', '')}")
        for iss in jd.get("issues") or []:
            print(f"    - {iss}")

        results.append({**case, "answer": r["answer"], "hard": hard, "judge": jd,
                        "verdict": v, "answer_id": r["done"].get("answer_id"),
                        "latency_ms": r["done"].get("latency_ms")})

    # ── 汇总 ──
    cnt = {"pass": 0, "warn": 0, "fail": 0}
    for x in results:
        cnt[x["verdict"]] = cnt.get(x["verdict"], 0) + 1
    scored = [x["judge"]["scores"] for x in results if x.get("judge", {}).get("scores")]
    avg = {}
    for k in ("structure", "caliber", "brevity", "usability"):
        vals = [s[k] for s in scored if isinstance(s.get(k), int)]
        avg[k] = round(sum(vals) / len(vals), 2) if vals else None

    print("\n" + "-" * 64)
    print(f"汇总: pass={cnt['pass']} warn={cnt['warn']} fail={cnt['fail']}")
    print(f"均分(n={len(scored)}): " + " ".join(f"{k}={v}" for k, v in avg.items()))
    tok = sum((x.get("judge", {}).get("tokens") or 0) for x in results)
    print(f"评审消耗: {tok} tokens（约 ${tok / 1_000_000 * 2.8:.4f} 混合均价估算）")

    # ── 落报告 ──
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    (REPORT_DIR / f"quality-{ts}.json").write_text(
        json.dumps({"model": JUDGE_MODEL, "avg": avg, "count": cnt,
                    "results": results}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    md = [f"# 回答质量评审 {ts}", "",
          f"- 生成模型: {os.getenv('QA_MODEL', 'qwen3.8-max')}　评审模型: {JUDGE_MODEL}",
          f"- 结果: pass={cnt['pass']} / warn={cnt['warn']} / fail={cnt['fail']}",
          f"- 均分: " + " ".join(f"{k} {v}" for k, v in avg.items()), ""]
    for x in results:
        md += [f"## {x['id']} · {x['verdict'].upper()}", "",
               f"**问题**：{x['q']}　", f"**关注点**：{x['focus']}", ""]
        if x.get("judge"):
            s = x["judge"].get("scores") or {}
            md += [f"**评分**：" + " ".join(f"{k}={s.get(k, '-')}" for k in
                                          ("structure", "caliber", "brevity", "usability")),
                   "", f"**结论**：{x['judge'].get('one_line', '')}", ""]
            if x["judge"].get("issues"):
                md += ["**问题项**："] + [f"- {i}" for i in x["judge"]["issues"]] + [""]
        else:
            md += [f"**问题项**：{x.get('issues')}", ""]
        if x.get("hard"):
            md += [f"**硬指标**：表格={x['hard']['has_table']} "
                   f"列序={x['hard']['header_order_ok']} "
                   f"路径泄漏={x['hard']['kb_leak'] or '无'} "
                   f"正文={x['hard']['prose_chars']}字 "
                   f"数字={x['hard']['price_numbers'] or '无'}", ""]
        md += ["**回答原文**：", "", "```", x.get("answer", "")[:2000], "```", ""]
    (REPORT_DIR / f"quality-{ts}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"报告: {REPORT_DIR}/quality-{ts}.md")

    sys.exit(0 if cnt["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
