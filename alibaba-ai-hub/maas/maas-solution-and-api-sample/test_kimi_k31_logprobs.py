# -*- coding: utf-8 -*-
"""
kimi-k3.1-pro logprobs / top_logprobs 支持边界探针（OpenAI 兼容 compatible-mode）

客户问题（OpenRouter 风格请求体，stream=true + thinking.type=disabled +
logprobs=true + top_logprobs=20）原样打到百炼是否可用、top_logprobs 支持多大。

实测结论（2026-11-23，CN 公共端点 https://dashscope.aliyuncs.com/compatible-mode/v1）：
  ① 支持 logprobs/top_logprobs，数据完整（token/logprob/bytes/top_logprobs[]）。
  ② top_logprobs 取值范围是 [0, 5]——OpenAI 是 [0, 20]。
     客户原样 top_logprobs=20 → HTTP 400
     {"code":"invalid_parameter_error","message":"Range of top_logprobs should be [0, 5]"}。
     OpenAI 生态代码直接迁移必踩 400，需降为 ≤5。
  ③ 只传 top_logprobs 不传 logprobs=true：百炼 200 静默忽略（logprobs 字段不出现），
     OpenAI 则显式 400——又一个"参数被接受 ≠ 语义被实现"的静默陷阱，
     排查时易被 200 成功骗过、误判为"模型不支持 logprobs"。
  ④ logprobs=true 单传（不带 top_logprobs）：默认 top_logprobs=0，
     只返回每 token 的 logprob，无候选列表。
  ⑤ 流式可用；logprobs 挂载在 choices[].logprobs 层（与 OpenAI 流式一致，
     不在 delta 内）——流式解析时勿只查 delta.logprobs，否则误判"流式不带 logprobs"。
  ⑥ thinking.type=disabled 与 logprobs 兼容（reasoning_tokens=0、直答）；
     思考开启时 logprobs 覆盖全部输出 token（含思考段），做 token 分析需注意区分。
  ⑦ 模型名：OpenRouter 的 "moonshotai/kimi-k3.1-pro" 前缀百炼不识别，需用 kimi-k3.1-pro。
  ⑧ 429（Throttling.ResourceExhausted）连续请求易触发，脚本内置等待重试。

业务影响（上限 5 vs OpenAI 20，按受影响程度）：
  A 迁移兼容（最常见）：OpenAI 生态代码/文档标准值就是 top_logprobs=20，原样迁移到百炼必 400，
     联调期需逐字段核对；更隐蔽的是只传 top_logprobs 忘传 logprobs=true 时百炼静默忽略（200 无字段），
     下游拿到 null 误判"模型不支持 logprobs"——200 成功比 400 更难排查。
  B 长尾审计漏检（安全/合规，实质影响）：top5 通常覆盖 95%~99% 概率质量，多数场景够用；
     但风险审计恰恰要看长尾——例：推荐类回答的第 8 名候选可能藏有黑名单机构（logprob≈-6，0.25%，
     400 次里会真吐 1 次），top5 结构性拿不到该信号。同理竞品词/敏感词倾向检测。
     应对：多次采样（temperature>0 跑 N 次）逼近长尾，或评估换可返回 top20 的服务面。
  C 度量精度（评测/研究）：用 top-K 估 token 分布熵、做置信度校准时 K=5 会系统性低估不确定性
     （尾部质量被截断）；跨厂商评测 pipeline 两边 K 不同则口径不可对齐、对比结论失真。
  D 基本无影响（多数业务在此）：幻觉片段定位只看 top1 自己的 logprob、二选一 margin 只看 top2~3，
     设 5 或不带 top_logprobs 均零损失。

密钥从仓库根 .env 安全解析。端点默认 CN 公共 compatible-mode，可 TEST_BASE_URL/TEST_API_KEY 覆盖。
"""
import os
import json
import time

import httpx

# ---- 安全加载 .env（仅 KEY=VALUE 行，覆盖式）----
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
_env = os.path.join(_root, ".env")
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("TEST_API_KEY") or os.getenv("DASHSCOPE_API_KEY_CN_TEST", "")
BASE_URL = (os.getenv("TEST_BASE_URL")
            or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
MODEL = os.getenv("TEST_MODEL", "kimi-k3.1-pro")
URL = BASE_URL + "/chat/completions"
HDR = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}

Q = "Reply with the single word: hello."


def _post(payload, tries=4):
    for i in range(tries):
        r = httpx.post(URL, headers=HDR, json=payload, timeout=120)
        if r.status_code == 429:
            time.sleep(8 * (i + 1))
            continue
        return r
    return r


def _brief(r):
    print(f"  status={r.status_code}")
    if r.status_code != 200:
        print("  err =", r.text[:300])
        return
    body = r.json()
    msg = (body.get("choices") or [{}])[0]
    lp = msg.get("logprobs")
    print("  content =", (msg.get("message") or {}).get("content"))
    print("  logprobs 出现 =", lp is not None)
    if lp:
        cs = lp.get("content") or []
        print(f"  content 长度 = {len(cs)}（每 token 一条）")
        if cs:
            e0 = cs[0]
            print(f"  首 token: token={e0.get('token')!r} logprob={e0.get('logprob')}"
                  f" top数={len(e0.get('top_logprobs') or [])}")
            print("  首 token top_logprobs =", json.dumps(e0.get("top_logprobs"), ensure_ascii=False)[:400])


def run(label, extra):
    print(f"\n===== {label} =====")
    payload = {"model": MODEL, "max_tokens": 32, "messages": [{"role": "user", "content": Q}]}
    payload.update(extra)
    _brief(_post(payload))
    time.sleep(5)


def test_stream():
    print("\n===== G 流式 + logprobs + top_logprobs=5（验证挂载层级）=====")
    payload = {"model": MODEL, "max_tokens": 32, "messages": [{"role": "user", "content": Q}],
               "stream": True, "logprobs": True, "top_logprobs": 5,
               "stream_options": {"include_usage": True},
               "thinking": {"type": "disabled"}}
    lp_first, content, usage = None, "", None
    with httpx.stream("POST", URL, headers=HDR, json=payload, timeout=120) as r:
        print(f"  status={r.status_code}")
        if r.status_code != 200:
            print("  err =", r.read()[:300])
            return
        for line in r.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                continue
            try:
                c = json.loads(data)
            except Exception:
                continue
            if c.get("usage"):
                usage = c["usage"]
            for ch in c.get("choices") or []:
                lp = ch.get("logprobs")
                if lp is not None and lp_first is None:
                    lp_first = lp
                d = ch.get("delta") or {}
                if d.get("content"):
                    content += d["content"]
    print(f"  content = {content!r}")
    print("  choices[].logprobs 出现 =", lp_first is not None)
    if lp_first:
        print("  首条 =", json.dumps(lp_first, ensure_ascii=False)[:400])
    print("  usage =", json.dumps(usage, ensure_ascii=False))


if __name__ == "__main__":
    print(f"端点: {BASE_URL}\n模型: {MODEL}")
    run("A 客户原样 top_logprobs=20（预期 400 超百炼上限）",
        {"logprobs": True, "top_logprobs": 20, "thinking": {"type": "disabled"}})
    run("B logprobs + top_logprobs=5（有效值）",
        {"logprobs": True, "top_logprobs": 5, "thinking": {"type": "disabled"}})
    run("C 只传 logprobs=true（默认 top_logprobs=0）",
        {"logprobs": True, "thinking": {"type": "disabled"}})
    run("D 只传 top_logprobs=5 不带 logprobs（预期静默忽略）",
        {"top_logprobs": 5, "thinking": {"type": "disabled"}})
    run("E 不禁思考 + logprobs + top_logprobs=5（logprobs 覆盖思考段）",
        {"logprobs": True, "top_logprobs": 5})
    test_stream()
    print("\n===== 完成 =====")
