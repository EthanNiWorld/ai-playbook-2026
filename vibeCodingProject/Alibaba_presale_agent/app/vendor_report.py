# -*- coding: utf-8 -*-
"""
Vendor 测试报告解析 + 阻塞项定界分析
====================================
上传客户「供应商测试报告」HTML（OpenAI Chat 协议兼容性验收），确定性提取
「阻塞性 · 必须全部通过」分组里的失败用例及其请求/响应/断言证据，再交给 LLM
按「三层核对 + 层次归因」方法论逐条定界：问题是否存在 / 是否影响使用 / 为什么。

设计边界（与人工定界一致）：
- 只做报告内证据的智能分析，不在本模块打真实端点（避免执行上传文件解析出的请求
  带来的安全/成本/限流问题，也保证对任意厂商报告通用）。
- 解析用 stdlib（re + html），不引入 bs4 依赖；报告结构高度规整，标记稳定。
- 证据压缩：保留模型与关键参数、usage 明细、失败断言原文；截断超长正文前缀，
  控制送入 LLM 的上下文规模。
"""
from __future__ import annotations

import html
import json
import re

# ── 报告结构标记（与 vendor-report-*.html 实测一致）──
_RE_TOP_GROUP = re.compile(
    r'<summary class="template-group-heading"><strong>(.*?)</strong>'
    r'<span class="status (?:ok|bad)">(.*?)</span>'
    r'<span>通过\s*(\d+)\s*/\s*(\d+)</span>',
    re.S,
)
_RE_SUB_GROUP = re.compile(r'<div class="case-group-heading"><strong>(.*?)</strong>', re.S)
_RE_CASE_START = re.compile(r'<details class="case">')
_RE_NAME = re.compile(r'<span class="name">(.*?)</span>', re.S)
_RE_STATUS_BAD = re.compile(r'<span class="status bad">')
_RE_BAD_ASSERT = re.compile(r'<li class="bad">(.*?)</li>', re.S)
_RE_REQUEST = re.compile(r'<h5>请求体</h5>\s*<pre>(.*?)</pre>', re.S)
_RE_RESPONSE = re.compile(r'<h5>响应体</h5>\s*<pre>(.*?)</pre>', re.S)
_RE_OVERVIEW = re.compile(
    r'<span class="overview-label">(.*?)</span><span class="overview-value">(.*?)</span>', re.S
)
_RE_CASE_ID = re.compile(r'TC-\d+-[0-9A-Za-z]+')
_RE_TAGS = re.compile(r'<[^>]+>')

_MAX_CASES = 12          # 单次最多分析的阻塞失败用例数（超出截断并提示）
_MAX_FIELD_CHARS = 1400  # 单个请求/响应证据压缩后的字符上限


def _strip(s: str) -> str:
    """去标签 + 反转义 + 折叠空白"""
    s = html.unescape(s or "")
    s = _RE_TAGS.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def _is_blocking(constraint: str) -> bool:
    return "阻塞性" in constraint and "非阻塞" not in constraint


def _preview_content(content, limit: int = 160) -> str:
    """messages.content 可能是 str 或多模态 blocks 数组"""
    if isinstance(content, str):
        return content[:limit] + ("…" if len(content) > limit else "")
    if isinstance(content, list):
        parts = []
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text":
                parts.append("text:" + str(b.get("text", ""))[:80])
            elif b.get("type") == "image_url":
                iu = b.get("image_url", {}) or {}
                d = iu.get("detail", "(未设)")
                parts.append(f"image_url(detail={d})")
            elif b.get("type") == "video_url":
                parts.append("video_url")
            else:
                parts.append(str(b.get("type", "?")))
        return " | ".join(parts)[:limit]
    return str(content)[:limit]


def _compact_request(raw: str) -> str:
    """压缩请求体：保留所有顶层参数（任何模型都不丢证据），仅 messages 做预览、
    tools 收敛为计数+名称、超长字符串值截断。不用参数白名单——新模型的 novel
    参数（如 enable_search/do_sample/新思考开关）也能完整送给 LLM 定界。"""
    txt = html.unescape(raw or "").strip()
    try:
        obj = json.loads(txt)
    except Exception:
        return txt[:_MAX_FIELD_CHARS]
    if not isinstance(obj, dict):
        return txt[:_MAX_FIELD_CHARS]
    out = {}
    for k, v in obj.items():
        if k == "messages":
            continue
        if k == "tools" and isinstance(v, list):
            out["tools_count"] = len(v)
            out["tool_names"] = [
                (t.get("function", {}) or {}).get("name")
                for t in v if isinstance(t, dict)
            ][:8]
            continue
        if isinstance(v, str) and len(v) > 240:
            out[k] = v[:240] + "…"
        else:
            out[k] = v
    msgs = obj.get("messages")
    if isinstance(msgs, list):
        out["messages"] = [
            {"role": m.get("role"), "content": _preview_content(m.get("content"))}
            for m in msgs if isinstance(m, dict)
        ]
    return json.dumps(out, ensure_ascii=False)[:_MAX_FIELD_CHARS]


def _compact_response(raw: str) -> str:
    """压缩响应体：保留 usage 全量 + error + choices 结构（截断正文）"""
    txt = html.unescape(raw or "").strip()
    try:
        obj = json.loads(txt)
    except Exception:
        return txt[:_MAX_FIELD_CHARS]
    if not isinstance(obj, dict):
        return txt[:_MAX_FIELD_CHARS]
    out = {}
    if "usage" in obj:
        out["usage"] = obj["usage"]
    if "error" in obj:
        out["error"] = obj["error"]
    for k in ("id", "model", "object"):
        if k in obj:
            out[k] = obj[k]
    choices = obj.get("choices")
    if isinstance(choices, list):
        cc = []
        for c in choices[:3]:
            if not isinstance(c, dict):
                continue
            msg = c.get("message", {}) or {}
            delta = c.get("delta", {}) or {}
            item = {"index": c.get("index"), "finish_reason": c.get("finish_reason")}
            content = msg.get("content", delta.get("content"))
            if content is not None:
                item["content"] = _preview_content(content, 120)
            if "reasoning_content" in msg:
                rc = msg.get("reasoning_content")
                item["reasoning_content"] = (
                    f"<{type(rc).__name__}, len={len(rc)}>" if isinstance(rc, str)
                    else rc
                )
            if "tool_calls" in msg:
                item["tool_calls"] = msg["tool_calls"]
            cc.append(item)
        out["choices"] = cc
    return json.dumps(out, ensure_ascii=False)[:_MAX_FIELD_CHARS]


def parse_report(html_text: str) -> dict:
    """解析报告 → {meta, groups, blocking_failures[], stats}"""
    meta = {}
    for label, value in _RE_OVERVIEW.findall(html_text or ""):
        meta[_strip(label)] = _strip(value)

    # 顶层分组（含位置，用于判定每个用例所属组是否阻塞）
    tops = []
    for m in _RE_TOP_GROUP.finditer(html_text):
        tops.append({
            "pos": m.start(),
            "name": _strip(m.group(1)),
            "constraint": _strip(m.group(2)),
            "blocking": _is_blocking(_strip(m.group(2))),
            "passed": int(m.group(3)),
            "total": int(m.group(4)),
        })
    groups = [{k: v for k, v in t.items() if k != "pos"} for t in tops]

    # 子分组位置（用于用例归属子组名）
    subs = [(m.start(), _strip(m.group(1))) for m in _RE_SUB_GROUP.finditer(html_text)]
    case_starts = [m.start() for m in _RE_CASE_START.finditer(html_text)]

    def _top_of(pos: int):
        cur = None
        for t in tops:
            if t["pos"] <= pos:
                cur = t
            else:
                break
        return cur

    def _sub_of(pos: int):
        cur = ""
        for p, name in subs:
            if p <= pos:
                cur = name
            else:
                break
        return cur

    failures = []
    for i, start in enumerate(case_starts):
        top = _top_of(start)
        if not top or not top["blocking"]:
            continue
        end = case_starts[i + 1] if i + 1 < len(case_starts) else len(html_text)
        # 不跨越下一个顶层分组
        for t in tops:
            if t["pos"] > start:
                end = min(end, t["pos"])
                break
        block = html_text[start:end]
        if not _RE_STATUS_BAD.search(block):
            continue
        name_m = _RE_NAME.search(block)
        name = _strip(name_m.group(1)) if name_m else "(未命名用例)"
        asserts = [_strip(a) for a in _RE_BAD_ASSERT.findall(block)]
        req_m = _RE_REQUEST.search(block)
        resp_m = _RE_RESPONSE.search(block)
        failures.append({
            "name": name,
            "top_group": top["name"],
            "sub_group": _sub_of(start),
            "failed_assertions": asserts,
            "request": _compact_request(req_m.group(1)) if req_m else "",
            "response": _compact_response(resp_m.group(1)) if resp_m else "",
        })

    truncated = len(failures) > _MAX_CASES
    failures = failures[:_MAX_CASES]
    blocking_groups = [g for g in groups if g["blocking"]]
    b_passed = sum(g["passed"] for g in blocking_groups)
    b_total = sum(g["total"] for g in blocking_groups)
    return {
        "meta": meta,
        "groups": groups,
        "blocking_failures": failures,
        "stats": {
            "blocking_passed": b_passed,
            "blocking_total": b_total,
            "blocking_failed": b_total - b_passed,
            "failure_count": len(failures),
            "truncated": truncated,
        },
    }


def summary_text(parsed: dict) -> str:
    """给前端 meta 事件的一行概览"""
    meta = parsed.get("meta", {})
    st = parsed.get("stats", {})
    model = meta.get("模型 ID") or meta.get("模型") or "?"
    platform = meta.get("平台 / 供应商") or meta.get("平台") or "?"
    names = "、".join(f["name"] for f in parsed.get("blocking_failures", []))
    s = (f"模型 {model} · 平台 {platform} · 阻塞组 {st.get('blocking_passed', 0)}/"
         f"{st.get('blocking_total', 0)}，失败 {st.get('failure_count', 0)} 条")
    if names:
        s += "：" + names
    if st.get("truncated"):
        s += f"（仅分析前 {_MAX_CASES} 条）"
    return s


# ──────────────────────────── 定界方法论 Prompt ────────────────────────────

REPORT_SYSTEM_PROMPT = """你是阿里云百炼（Model Studio）的售前技术专家，负责分析客户提交的「供应商测试报告」（OpenAI Chat 协议兼容性验收），对其中「阻塞性 · 必须全部通过」分组里**未通过**的用例逐条定界：到底是被测平台的真实功能缺陷，还是测试侧的断言/配置问题。

【核心方法论 — 三层核对】判定任何失败前，依次核对：
1. 该字段/参数是否存在于 **OpenAI 官方 Chat Completions Schema**？（如 prompt_tokens_details 标准只含 cached_tokens / audio_tokens；message 标准只含 content/refusal/role/annotations/audio/function_call/tool_calls）
2. 是否为**厂商扩展字段**？（如 reasoning_content、cache_write_tokens、prompt_cache_options 是 Moonshot/Kimi 等厂商的扩展，非 OpenAI 强制）
3. 目标模型及其**上游厂商官方文档**是否声明支持该取值？（托管第三方模型时，须查上游厂商自己的 API 承诺，不能只看平台）

【层次归因】
- 报错为服务端 Pydantic literal_error / HTTP 400 / 耗时数十毫秒 / 无 usage 与 token 统计 → 在协议适配与参数校验层被拒，未到模型权重；多模型同报错指向公共请求 Schema 白名单。
- 区分「参数能否通过校验」与「参数通过后语义是否真正生效」两层：参数被接受 ≠ 语义被实现（如各档 image_tokens 全相同，提示降采样可能未生效）。

【常见误判知识卡 — 只是示例，非穷举】命中时优先据此定界；**未命中时按上述通用方法论 + 该模型上游官方协议推理，不得因知识卡未覆盖某模型就回避定界**。知识卡按厂商分组，被测模型可能是任何厂商（Qwen/DeepSeek/GLM/Kimi 等），须先识别模型再套用对应条目。

■ 通用（任何模型适用）
- **流式末块 choices 非空 / 无 choices:[] 的 usage 块**：独立的 choices:[] + 顶层 usage 块**仅在 stream_options.include_usage=true 时**才出现。请求只设 stream:true 而漏设 include_usage 时，usage 骑在 finish 块里属正常；断言「末块 choices==[]」是测试前提缺陷，非平台问题。
- **reasoning_content「意外存在」**：思考模型关闭思考时返回空字符串 "" 在类型上合法（厂商扩展字段 optional+nullable）。应以 reasoning_tokens 缺失或为 0 作主判据，而非「字段必须不存在/为 null」。空串 ≠ 思考未关闭。
- **参数被接受 ≠ 语义被实现**：某参数返回 200 不代表其语义生效（如各档 image_tokens 全相同提示降采样未生效）；需另立语义验证，不能仅凭「接受」判通过、也不能仅凭「拒绝某扩展值」判缺陷。

■ Moonshot / Kimi
- **cache_write_tokens 缺失**：Moonshot 写入侧诊断扩展字段（OpenAI SDK 中 Optional[int]=None，非强制必返）。缓存是否真生效看标准字段 cached_tokens 重放是否 >0。隐式缓存有激活门槛与写入延迟：前缀较短（约 <1200 token）或写入后紧接重放可能 cached_tokens=0，不能据此判缓存失效；建议 ≥2048 token 前缀、间隔 ≥10s 重放。报告若在首轮写入断言处即中止、命中轮从未执行，属测试设计假阴性。
- **prompt_cache_options / ttl 大写或未声明档位被接受(200)而非拒绝(400)**：prompt_cache_options 本身是 Moonshot 扩展（非 OpenAI 标准）；严格大小写拒绝是厂商校验风格，宽容接受使请求成功而非失败，不影响使用（最坏降级默认档）。

■ DeepSeek
- **image_url.detail=original 被 400**：DeepSeek 官方枚举为 low/high/original/auto，original 是上游合法承诺值；平台拒绝属对上游协议兼容不完整（非客户端用非法值）。high 保留原图、上游文档语义等价 original，可作功能替代但须区分「上游等价推导」与「平台官方替代方案」。

■ Qwen / 通义（DashScope）
- **enable_thinking / thinking 开关**：Qwen 思考模型用 enable_thinking（或 chat_template_kwargs）控制；关闭思考的判据同样是 reasoning_tokens=0 / 无思考文本，而非 reasoning_content 字段必须缺失。
- **enable_search / search_info 等联网扩展**：属 DashScope 扩展字段，非 OpenAI 标准；其返回形态差异不应判为协议不兼容。
- **上下文缓存**：DashScope 缓存命中看 usage.prompt_tokens_details.cached_tokens；cache_write_tokens 非 Qwen 必返字段。

■ GLM / 智谱
- **tool_choice 强制下 finish_reason=stop**：GLM 系列在强制 tool_choice 时 finish_reason 可能返回 stop 而非 tool_calls；判断是否发起工具调用应以 tool_calls 非空为准，不信任 finish_reason（既有实测教训）。
- **reasoning_content / thinking.type**：GLM 思考扩展字段，关闭思考判据同通用条（reasoning_tokens=0）。

【厂商识别】先从报告 meta 的「模型 ID」识别厂商（qwen*→Qwen、deepseek*→DeepSeek、glm*→GLM、kimi*→Moonshot），套用对应知识卡；混合/未知模型按通用方法论 + 上游官方协议处理。

【输出要求】
- 对**每一条**阻塞失败用例单独成节，标题用用例名，依次回答三个问题：
  1. **问题是否存在**：区分「狭义观察属实」（如某字段确实没返回）与「真实功能缺陷」。命中测试侧问题时明确指出是断言过严/漏设开关/把扩展字段当强制契约。
  2. **是否影响使用**：明确 Yes/No，紧扣真实业务（能否正常调用、计费/缓存/流式是否工作）。
  3. **为什么不影响**（或为什么影响）：给出协议层依据与机理。
- 末尾给：**总体定界**（几条属测试侧、几条属真实缺陷）+ **给客户的口径建议**（一段可直接转发的话）+ 如需进一步实证应补做的验证（如补设 include_usage 复测、换高分辨率图验证 detail 语义）。
- 用中文、Markdown，先结论后依据，简洁专业。

【纪律】
- 结论必须基于报告给出的请求/响应/断言证据，不臆造实测数字；本分析**未打真实端点**，不得声称「已实测通过」，需要实证处写明「建议复测」。
- 涉及协议枚举/字段地位不确定时，标注「需以当前官方 Schema 为准」，措辞用「暂未找到」而非「没有」。
- 不输出价格、不营销；聚焦协议兼容性与业务影响。"""


def build_messages(parsed: dict, focus: str = "") -> list[dict]:
    """把解析证据组装成 LLM 消息。focus 为用户随报告上传的补充关注点（可选）。"""
    meta = parsed.get("meta", {})
    st = parsed.get("stats", {})
    failures = parsed.get("blocking_failures", [])
    head = (
        f"被测模型：{meta.get('模型 ID', '?')}\n"
        f"平台/供应商：{meta.get('平台 / 供应商', '?')}\n"
        f"报告生成时间：{meta.get('生成时间', '?')}\n"
        f"阻塞组通过情况：{st.get('blocking_passed', 0)}/{st.get('blocking_total', 0)}，"
        f"失败 {st.get('failure_count', 0)} 条\n"
    )
    # 非阻塞组仅作背景提示
    non_blocking = [g for g in parsed.get("groups", []) if not g["blocking"]]
    if non_blocking:
        head += "非阻塞组（仅背景，不必逐条分析）：" + "；".join(
            f"{g['name']} {g['passed']}/{g['total']}（{g['constraint']}）" for g in non_blocking
        ) + "\n"
    if st.get("truncated"):
        head += f"注：失败用例超过 {_MAX_CASES} 条，以下仅列前 {_MAX_CASES} 条。\n"

    body = []
    for i, f in enumerate(failures, 1):
        sec = [f"\n### 失败用例 {i}：{f['name']}"]
        sec.append(f"所属分组：{f['top_group']} / {f['sub_group']}")
        if f.get("failed_assertions"):
            sec.append("失败断言：\n" + "\n".join("- " + a for a in f["failed_assertions"]))
        if f.get("request"):
            sec.append("请求体（关键参数，正文已截断）：\n```json\n" + f["request"] + "\n```")
        if f.get("response"):
            sec.append("响应体（usage/choices 摘要）：\n```json\n" + f["response"] + "\n```")
        body.append("\n".join(sec))

    user = (
        head + "\n以下是阻塞组失败用例的证据，请按方法论逐条定界（是否存在/是否影响使用/为什么），"
        "并给总体定界与客户口径建议：\n" + "\n".join(body)
    )
    if focus and focus.strip():
        user += (
            "\n\n【用户补充关注点】" + focus.strip()[:500]
            + "\n请在逐条定界的基础上，优先围绕该关注点展开说明。"
        )
    return [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]