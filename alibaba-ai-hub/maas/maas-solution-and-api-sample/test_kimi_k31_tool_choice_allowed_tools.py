"""kimi-k3.1-pro tool_choice=allowed_tools 兼容性探针（百炼 MaaS 端点）

背景：客户 vendor 评估（2026-11-13）发现同一请求体在 Kimi 原厂 API 返回 200，
在百炼托管 kimi-k3.1-pro 返回 400。差异点为 tool_choice 使用了 OpenAI 新式
allowed_tools 形态（GPT-5 系引入，Kimi 原厂已跟进）：
  {"type":"allowed_tools","allowed_tools":{"mode":"required","tools":[...]}}
本脚本在百炼端点实测各 tool_choice 形态，定位 400 根因并验证替代写法。

用例（messages / tools 与客户 payload 完全一致）：
  A. allowed_tools + mode=required（客户原始 payload 复现）
  B. allowed_tools + mode=auto
  C. tool_choice="required"（OpenAI 标准字符串）
  D. tool_choice={"type":"function","function":{"name":"get_weather"}}（指定单工具）
  E. tool_choice="auto"（基线对照）
  F. A 的 payload + model="moonshotai/kimi-k3.1-pro"（验证模型 ID 前缀影响）
  G. 对照组：同端点 qwen3.8-max 跑 A payload（区分网关级 vs 模型级限制）
  H. 等价替代方案：tools 裁剪为仅 get_weather + tool_choice="required"
     （allowed_tools required 子集的语义 = 强制调用 ∩ 候选集裁剪）

端点与凭证（.env，sk-ws- 前缀 workspace Key 必须配 workspace 端点）：
  SG: DASHSCOPE_API_KEY_INTL_SG_TEST + _URL（国际站新加坡 workspace）
  CN: DASHSCOPE_API_KEY_CN_TEST + _URL（北京 workspace）
模型 ID：workspace 专属端点上为 kimi-k3.1-pro（无 kimi/ 前缀）。
运行：vibeCodingProject/Alibaba_presale_agent/.venv/bin/python test_kimi_k31_tool_choice_allowed_tools.py
（需 httpx；ai-guardrails/.venv 未装 httpx。可用 ONLY_CASES=H / ONLY_ENDPOINT=SG 过滤复跑）

实测结论（2026-11-13，SG + CN 双 workspace 端点）：
  A/B. allowed_tools（required/auto）→ 400 "Expected field `function` in
       `tool_choice`"，双端点一致复现客户问题；
  G. 同端点 qwen3.8-max 跑同一 payload 报同一 400 → 系百炼 compatible-mode
     网关参数校验层限制（tool_choice 对象仅认 type=function），非 kimi 专属；
  C. "required" → 200，finish_reason=tool_calls 正常（双端点一致）；
  D. 指定函数对象 → SG 端点校验通过但模型陷入重复调用 get_weather 直至
     finish_reason=length（8192 token 耗尽）；Kimi 原厂文档明示指定函数与
     思考开启不兼容（400），k3.1-pro 始终思考 → 此路原厂/百炼均不可用；
  E. "auto" → 200 正常；
  F. moonshotai/ 前缀模型名在 workspace 端点 → 404 model_not_found
     （workspace 端点模型 ID 无前缀；客户该 ID 应属标准公共端点）；
  H. tools 裁剪 + "required" → 200，仅调用 get_weather({"location":"上海"})，
     finish_reason=tool_calls 正常 → 与 allowed_tools required 子集语义等价，
     为推荐替代方案（SG 端点实测）。
官方口径：百炼 kimi 文档明示 tool_choice 仅支持 auto/none/required 三档
（help.aliyun.com/zh/model-studio/kimi-api-by-moonshot-ai）；Kimi 原厂公开
schema 同样未列 allowed_tools（platform.kimi.com/docs/api/chat），客户实测
原厂 200 属未文档化扩展/文档滞后，以实测为准。
"""
import httpx
import json
import os
import time

# 加载 .env（.env 已被 .gitignore 忽略，密钥不进 Git）
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

MODEL = os.getenv("TEST_MODEL", "kimi-k3.1-pro").strip()

# 客户原始 payload 中的 messages 与 tools（完全一致）
MESSAGES = [{"role": "user", "content": "请处理上海相关的信息。"}]
TOOLS = [
    {"type": "function", "function": {
        "name": "get_weather", "description": "查询指定城市的当前天气",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}},
                       "required": ["location"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "get_current_time", "description": "查询指定城市的当前时间",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}},
                       "required": ["location"], "additionalProperties": False}}},
]
ALLOWED_REQUIRED = {"type": "allowed_tools", "allowed_tools": {
    "mode": "required", "tools": [{"type": "function", "function": {"name": "get_weather"}}]}}
ALLOWED_AUTO = {"type": "allowed_tools", "allowed_tools": {
    "mode": "auto", "tools": [{"type": "function", "function": {"name": "get_weather"}}]}}
NAMED_FUNC = {"type": "function", "function": {"name": "get_weather"}}

CASES = [
    ("A. allowed_tools+required（客户原样）", ALLOWED_REQUIRED, MODEL, TOOLS),
    ("B. allowed_tools+auto", ALLOWED_AUTO, MODEL, TOOLS),
    ("C. tool_choice=\"required\"", "required", MODEL, TOOLS),
    ("D. tool_choice=指定 get_weather", NAMED_FUNC, MODEL, TOOLS),
    ("E. tool_choice=\"auto\"（基线）", "auto", MODEL, TOOLS),
    ("F. A payload + moonshotai/ 前缀模型名", ALLOWED_REQUIRED, "moonshotai/kimi-k3.1-pro", TOOLS),
    ("G. 对照 qwen3.8-max + A payload", ALLOWED_REQUIRED, "qwen3.8-max", TOOLS),
    ("H. 等价方案：tools 裁剪 + required", "required", MODEL, TOOLS[:1]),
]
# CN 端点只跑关键子集（配额较紧）：A 复现 + C/D 替代方案 + G 对照 + H 等价方案
CN_CASES = [c for c in CASES if c[0].startswith(("A.", "C.", "D.", "G.", "H."))]
# 过滤开关：ONLY_CASES=H 只跑 H；ONLY_ENDPOINT=SG 只跑 SG 端点
ONLY_CASES = os.getenv("ONLY_CASES", "").strip()
ONLY_ENDPOINT = os.getenv("ONLY_ENDPOINT", "").strip()


def run_case(client, base_url, api_key, name, tool_choice, model, tools):
    """流式请求：非 200 直接打印错误体；200 则收集 tool_calls 与 finish_reason。"""
    payload = {"model": model, "messages": MESSAGES, "tools": tools,
               "tool_choice": tool_choice, "stream": True,
               "max_completion_tokens": 8192}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    print(f"\n{'=' * 16} {name} {'=' * 16}")
    print(f"model={model}  tool_choice={json.dumps(tool_choice, ensure_ascii=False)}")
    t0 = time.time()
    for attempt in range(3):
        try:
            with client.stream("POST", base_url.rstrip("/") + "/chat/completions",
                               json=payload, headers=headers) as r:
                if r.status_code != 200:
                    body = r.read().decode("utf-8", errors="replace")
                    print(f"❌ HTTP {r.status_code}（{(time.time() - t0) * 1000:.0f}ms）")
                    print(f"   {body[:800]}")
                    return r.status_code
                # 200：收集流式增量直到 finish_reason
                calls, finish, reasoning_len = {}, None, 0
                for line in r.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    for ch in chunk.get("choices") or []:
                        delta = ch.get("delta") or {}
                        if delta.get("reasoning_content"):
                            reasoning_len += len(delta["reasoning_content"])
                        for tc in delta.get("tool_calls") or []:
                            idx = tc.get("index", 0)
                            slot = calls.setdefault(idx, {"name": "", "args": ""})
                            fn = tc.get("function") or {}
                            if fn.get("name"):
                                slot["name"] = fn["name"]
                            if fn.get("arguments"):
                                slot["args"] += fn["arguments"]
                        if ch.get("finish_reason"):
                            finish = ch["finish_reason"]
                    if finish:
                        break
                ms = (time.time() - t0) * 1000
                print(f"✅ HTTP 200（{ms:.0f}ms，思考 {reasoning_len} 字，finish_reason={finish}）")
                for slot in calls.values():
                    print(f"   tool_call → {slot['name']}({slot['args'][:200]})")
                if not calls:
                    print("   （未产生 tool_call）")
                return 200
        except Exception as e:
            if "429" in str(e) or "Throttling" in str(e):
                wait = 8 * (attempt + 1)
                print(f"⏳ 429 限流，{wait}s 后重试（{attempt + 1}/3）")
                time.sleep(wait)
                continue
            print(f"❌ 异常：{type(e).__name__}: {e}")
            return -1
    print("❌ 429 重试 3 次仍失败")
    return 429


def main():
    endpoints = []
    sg_key = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", "").strip()
    sg_url = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "").strip()
    if sg_key and sg_url and ONLY_ENDPOINT in ("", "SG"):
        endpoints.append(("SG workspace", sg_url, sg_key, CASES))
    cn_key = os.getenv("DASHSCOPE_API_KEY_CN_TEST", "").strip()
    cn_url = os.getenv("DASHSCOPE_API_KEY_CN_URL", "").strip()
    if cn_key and cn_url and ONLY_ENDPOINT in ("", "CN"):
        endpoints.append(("CN workspace", cn_url, cn_key, CN_CASES))
    if not endpoints:
        raise SystemExit("❌ .env 缺少 SG/CN workspace 端点凭证")

    summary = []
    for label, url, key, cases in endpoints:
        print(f"\n{'#' * 60}\n# 端点：{label}  {url}\n{'#' * 60}")
        with httpx.Client(timeout=180) as client:
            for name, tc, model, tools in cases:
                if ONLY_CASES and not name.startswith(tuple(
                        x.strip() + "." for x in ONLY_CASES.split(","))):
                    continue
                status = run_case(client, url, key, name, tc, model, tools)
                summary.append((label, name, status))
                time.sleep(2)  # 间隔，降低限流概率

    print(f"\n{'=' * 20} 结论汇总 {'=' * 20}")
    for label, name, status in summary:
        mark = "✅" if status == 200 else "❌"
        print(f"  [{label}] {name}: {mark} HTTP {status}")


if __name__ == "__main__":
    main()