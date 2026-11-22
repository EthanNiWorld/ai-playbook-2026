# -*- coding: utf-8 -*-
"""
kimi-k3.1-pro reasoning_effort=max 但 usage.output_tokens_details.reasoning_tokens=0 归因探针

客户现象（OpenAI 兼容协议，非流式）：
  {"input_tokens":37699,"output_tokens":94,"total_tokens":37793,
   "output_tokens_details":{"reasoning_tokens":0}}
  请求带 reasoning_effort=max，但无任何思考 token 计费。

官方口径（knowledge/moonshot/kimi-k-series.md）：K3.1 Pro 思考始终开启，
reasoning_effort low/high/max（默认 max）。两种竞争假设：
  H1 参数/部署层：百炼网关托管版没把 OpenAI reasoning_effort 映射到 Moonshot 思考控制，
     思考实际关闭 → reasoning_tokens 真为 0（与 prompt_cache_options ttl 静默接受同源）
  H2 计费字段层：思考实际发生，但网关不把 Moonshot 内部思考计数透出到
     output_tokens_details.reasoning_tokens → 字段假 0

判据设计：
  A 非流式 + reasoning_effort=max，难题：看 message 是否含 reasoning_content、
    output_tokens 与 reasoning_tokens、content 是否内嵌 <think>
  B 同题不传 reasoning_effort（默认 max）对照
  C 同题 reasoning_effort=low 对照（若 A/C 输出量级一致且都无思考 → 参数不生效）
  D DashScope 原生思考开关 enable_thinking=true 对照（兼容模式透传给 kimi 部署）
  E 流式 + include_usage：看 delta 是否出现 reasoning_content 增量

密钥从仓库根 .env 安全解析。端点默认北京 workspace 专属网关，可 TEST_BASE_URL/TEST_API_KEY 覆盖。

实测结论（2026-11-22，北京 workspace 端点 + 公共 dashscope 端点交叉验证）：
  ① reasoning_effort 在 kimi-k3.1-pro 上完全生效且 reasoning_tokens 如实计费：
     max=195 / 默认(不传)=485 / low=80（同题鸡兔同笼，北京端点）；
     公共端点 max=298。message.reasoning_content 正常分离，content 干净无 think 标签。
     H1/H2 均不成立：参数生效、计费字段透出。
  ② 症状精确复现路径：请求体混入 enable_thinking=false（DashScope 原生思考开关）→
     reasoning_effort=max 被覆盖，reasoning_tokens=0、reasoning_content 为空串、
     content 为干净直答——与客户现象（output_tokens=94、reasoning_tokens=0）完全一致。
     DashScope 网关上 enable_thinking 优先级高于 reasoning_effort，后者只调强度不能开启思考。
  ③ 工具调用场景思考仍开启（tool_calls 响应 reasoning_tokens=56），排除工具链路假设。
  ④ /responses（Responses API）在 workspace 网关可用，默认思考开启（reasoning_tokens=348），
     参数为 reasoning.effort 而非 reasoning_effort；其 usage 命名为 input_tokens/output_tokens
     风格——客户 usage JSON 混合 input_tokens_details.text_tokens（Responses/原生风格）与
     prompt_tokens_details.cached_tokens（Chat Completions 风格），非 compatible-mode 原始格式，
     说明其响应经过了中转/归一化层（与 vendor 报告 HK 网关吞参数、不透出 Moonshot 私有字段的行为同源）。
  归因排序：客户请求中大概率存在 enable_thinking=false（客户端/框架注入）或
  中转网关未映射思考参数且默认关闭思考；reasoning_effort=max 本身不是原因。
排查建议：①打印实际发出的请求体查 enable_thinking/thinking 字段；②看响应 message.reasoning_content
是否为空（空=思考真没开；非空但 usage=0=网关计费字段丢失）；③绕过中转直连公共 compatible-mode 端点对照。

追加实测（2026-11-22 第二轮，客户反馈其请求带 enable_thinking=true 后）：
  四端点交叉验证 enable_thinking=true / reasoning_effort=max / 两者同传，reasoning_tokens 均非 0：
    国际站SG workspace：max=306 / enable_thinking=true=196 / 同传=558；
    国际站BJ workspace：max=353 / enable_thinking=true=472 / 同传=232；
    （加上第一轮：CN公共端点 max=298、北京 workspace max=195/enable_thinking=true=378）
  边界组合（北京 workspace，max+enable_thinking=true）：JSON mode(response_format)=153、
  temperature=0=152、tool_choice=none=107 —— 均思考正常。
  结论：enable_thinking=true 只要到达百炼就不可能 reasoning_tokens=0；客户现象只能出在其
  调用链路——①中转/聚合网关丢掉思考参数且默认关思考；②自建 serving（vLLM 等）未配
  reasoning parser，思考要么没启用要么混入 content（看 content 是否含 think 标签可判）；
  ③其 usage 混合 input_tokens/output_tokens 与 prompt_tokens_details.cached_tokens 两种
  命名风格，非百炼 compatible-mode 原始格式，可从命名反推实际 serving 栈。

追加实测（2026-11-22 第三轮，客户确认走 /compatible-mode/v1/chat/completions 后）：
  新发现第二个静默关闭路径：请求体顶层混入 Anthropic 风格 thinking 对象
  {"thinking": {"type": "disabled"}} → 200 接受，reasoning_tokens=0、reasoning_content 空、
  优先级高于 reasoning_effort=max 与 enable_thinking=true；thinking.type=enabled 无影响（221）。
  thinking_budget=0/1 → 400 "Parameter thinking_budget is not supported."（会报错，可排除）；
  chat_template_kwargs 关思考被忽略（495）；max_tokens=100 不影响思考优先消耗（387+正文截断）。
  决定性证据：无论请求带 thinking/reasoning 对象与否，百炼 compatible-mode 的 usage 键恒为
  [completion_tokens, completion_tokens_details, prompt_tokens, prompt_tokens_details, total_tokens]
  ——客户 input_tokens/output_tokens/output_tokens_details 风格的 usage 不可能来自百炼
  compatible-mode 原始响应，必经过中转/转换层（或在打非百炼端点）。
  客户侧两大候选根因（均可在其请求体/日志中直接验证）：
  ①请求体混入 thinking:{"type":"disabled"}（Anthropic SDK/中间层自动注入）；
  ②中转层默认关思考且未映射 enable_thinking/reasoning_effort（usage 命名风格即铁证）。
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
BASE_URL = (os.getenv("TEST_BASE_URL") or os.getenv("DASHSCOPE_API_KEY_CN_URL", "")
            or "https://llm-7ufq8xadyf99jlbp.cn-beijing.maas.aliyuncs.com/compatible-mode/v1").rstrip("/")
MODEL = os.getenv("TEST_MODEL", "kimi-k3.1-pro")
URL = BASE_URL + "/chat/completions"
HDR = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}

Q = "一个笼子里鸡兔共35个头、94只脚，鸡兔各几只？请一步步推理后给出答案。"


def _post(payload, tries=4):
    for i in range(tries):
        r = httpx.post(URL, headers=HDR, json=payload, timeout=180)
        if r.status_code == 429:
            time.sleep(5 * (i + 1))
            continue
        return r
    return r


def _brief(r):
    print(f"  status={r.status_code}")
    if r.status_code != 200:
        print("  err =", r.text[:300])
        return
    body = r.json()
    usage = body.get("usage", {})
    msg = (body.get("choices") or [{}])[0].get("message", {})
    print("  usage =", json.dumps(usage, ensure_ascii=False))
    rc = msg.get("reasoning_content")
    print(f"  message.reasoning_content 存在={('reasoning_content' in msg)} "
          f"非空={bool(rc)} len={len(rc) if rc else 0}")
    content = msg.get("content") or ""
    print(f"  message.content len={len(content)} 含<think>={'<think>' in content}")
    print("  content[:200] =", content[:200].replace("\n", " "))
    return usage


def run(label, extra):
    print(f"\n===== {label} =====")
    payload = {"model": MODEL, "max_completion_tokens": 2048,
               "messages": [{"role": "user", "content": Q}]}
    payload.update(extra)
    _brief(_post(payload))
    time.sleep(3)


def test_stream():
    print("\n===== E 流式 + include_usage：delta 形态 =====")
    payload = {"model": MODEL, "max_completion_tokens": 2048, "stream": True,
               "stream_options": {"include_usage": True},
               "reasoning_effort": "max",
               "messages": [{"role": "user", "content": Q}]}
    rc_len, c_len, usage = 0, 0, None
    with httpx.stream("POST", URL, headers=HDR, json=payload, timeout=180) as r:
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
                d = ch.get("delta") or {}
                rc_len += len(d.get("reasoning_content") or "")
                c_len += len(d.get("content") or "")
    print(f"  累计 delta.reasoning_content len={rc_len}")
    print(f"  累计 delta.content len={c_len}")
    print("  末块 usage =", json.dumps(usage, ensure_ascii=False))


if __name__ == "__main__":
    print(f"端点: {BASE_URL}\n模型: {MODEL}")
    run("A reasoning_effort=max（复现客户参数）", {"reasoning_effort": "max"})
    run("B 不传 reasoning_effort（官方默认 max）", {})
    run("C reasoning_effort=low", {"reasoning_effort": "low"})
    run("D DashScope 原生 enable_thinking=true 对照", {"enable_thinking": True})
    test_stream()
    print("\n===== 完成 =====")
