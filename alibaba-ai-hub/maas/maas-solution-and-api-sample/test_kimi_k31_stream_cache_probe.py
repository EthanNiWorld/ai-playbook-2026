"""kimi-k3.1-pro 国际站节点：流式 usage 形态 + 隐式缓存命中 + 视频边界探针

背景：客户 vendor 报告（2026-11-12）对百炼托管 kimi-k3.1-pro 提出三点质疑：
  1) 视频 base64/URL 至少支持一个；
  2) 流式最后一个带 usage 的 chunk 必须 choices=[]（客户观测到有内容）；
  3) 响应体无 cache_write_tokens → 推断"缓存写入不支持"。
本脚本在国际站节点实测三个事实，为客户回复提供一手证据：
  Case A: stream + stream_options.include_usage=true → 末块是否 OpenAI 标准形态
          （choices=[] 且 usage 在 chunk 顶层）
  Case B: stream 默认（不传 stream_options）→ 复现客户观测的 usage 位置
  Case C: 同一长前缀（>1024 token）连续重放 → cached_tokens 是否命中
          （"缓存是否生效"的正确判据；cache_write_tokens 系 Moonshot 私有扩展字段）
  Case D: 视频 URL 输入（嵌套格式）→ 确认国际节点能力边界

端点与凭证：DASHSCOPE_API_KEY_INTL_SG_TEST + DASHSCOPE_API_KEY_INTL_SG_TEST_URL（.env）
模型 ID：默认 kimi-k3.1-pro，可用 TEST_MODEL 覆盖；若 404 自动尝试 kimi/ 前缀变体。
运行：ai-guardrails/.venv/bin/python test_kimi_k31_stream_cache_probe.py

实测结论（2026-11-12，国际站 SG workspace 端点，kimi-k3.1-pro，两轮复跑一致）：
  A. include_usage=true → [DONE] 前出现标准末块 choices=[] + 顶层 usage ✅
     （其前另有一个 usage 内嵌 choices[0] 的 DashScope 形态块，不影响“末块”断言）
  B. 默认流式 → usage 仅内嵌于末块 choices[0]，顶层 usage=null
     （复现客户 vendor 报告观测；OpenAI SDK 解析不受影响，仅 chunk.usage 读空）
  C. 1169 token 前缀、3s 间隔重放 3 次 → cached_tokens 均为 0
  C2. 2577 token 前缀 → 首次 0，15s 后第二次 cached_tokens=2048，45s 后第三次仍 2048
     → 隐式缓存生效；短前缀（~1180，即客户用例长度）未触发；
       验证建议用 ≥2048 token 前缀、≥10s 间隔，判据用 cached_tokens
  D. 视频 URL → 400 "Video inputs are not supported by this model"（与北京节点一致）
  E. 对照 kimi-k2.6 → 403 access_denied（该 workspace 未授权此模型，
     视频替代方案需另行在已授权端点验证；北京 workspace 此前实测 k2.6 视频可用）
  协议定位：cache_write_tokens / prompt_cache_options 系 Moonshot 私有缓存扩展，
  本网关不透出；OpenAI Chat Completions 请求 schema 无 prompt_cache_options
  （仅 Responses API 有，gpt-5.6+），cache_write_tokens 在最新 SDK 中亦为 Optional。
"""
import httpx
import json
import os
import time
import uuid

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

API_KEY = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", "").strip()
BASE_URL = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "").strip()
MODEL = os.getenv("TEST_MODEL", "kimi-k3.1-pro")
VIDEO_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241115/cqqkru/1.mp4"

if not API_KEY or not BASE_URL:
    raise SystemExit("❌ 缺少 DASHSCOPE_API_KEY_INTL_SG_TEST / _URL（.env）")

print(f"Base URL: {BASE_URL}")
print(f"Model: {MODEL}")
client = httpx.Client(timeout=180)


def post(payload, stream=False, retries=3):
    """带 429 退避重试的请求；stream=True 时返回原始 SSE data 行列表。"""
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    for attempt in range(retries):
        if stream:
            lines = []
            with client.stream("POST", BASE_URL.rstrip("/") + "/chat/completions",
                               json=payload, headers=headers) as r:
                status = r.status_code
                if status == 429:
                    r.read()
                    wait = 8 * (attempt + 1)
                    print(f"  429 限流，{wait}s 后重试 ({attempt + 1}/{retries})")
                    time.sleep(wait)
                    continue
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        lines.append(line[5:].strip())
                return status, lines
        r = client.post(BASE_URL.rstrip("/") + "/chat/completions",
                        json=payload, headers=headers)
        if r.status_code == 429 and attempt < retries - 1:
            wait = 8 * (attempt + 1)
            print(f"  429 限流，{wait}s 后重试 ({attempt + 1}/{retries})")
            time.sleep(wait)
            continue
        return r.status_code, r.json()
    return 429, {"error": "retries exhausted"}


def show(title):
    print(f"\n{'=' * 62}\n{title}\n{'=' * 62}")


# ---- Case 0: 连通性 + 模型 ID 探测 ----
show("Case 0: 文本连通性")
status, body = post({"model": MODEL, "max_tokens": 8,
                     "messages": [{"role": "user", "content": "hi"}]})
if status == 404 or (isinstance(body, dict) and "model" in str(body.get("error", {})).lower()
                     and status == 400):
    alt = f"kimi/{MODEL}" if "/" not in MODEL else MODEL.split("/", 1)[1]
    print(f"  {MODEL} 不可用（{status}），尝试 {alt}")
    status, body = post({"model": alt, "max_tokens": 8,
                         "messages": [{"role": "user", "content": "hi"}]})
    if status == 200:
        MODEL = alt
print(f"  status={status}  model={MODEL}")
if status != 200:
    print(json.dumps(body, ensure_ascii=False)[:500])
    raise SystemExit("❌ 连通性失败，终止")

# ---- Case A: include_usage=true 的末块形态 ----
show("Case A: stream + stream_options.include_usage=true")
status, lines = post({"model": MODEL, "stream": True,
                      "stream_options": {"include_usage": True},
                      "max_tokens": 64,
                      "messages": [{"role": "user", "content": "Say hello in one word."}]},
                     stream=True)
print(f"  status={status}  共 {len(lines)} 个 data 行")
for raw in lines[-3:]:
    print(f"  尾部原始块: {raw[:600]}")
usage_chunks = [json.loads(x) for x in lines if x != "[DONE]"
                and json.loads(x).get("usage")]
if usage_chunks:
    last = usage_chunks[-1]
    print(f"  带 usage 的末块: choices={last.get('choices')}  "
          f"顶层usage={'有' if last.get('usage') else '无'}")
    print(f"  ✅ OpenAI 标准形态（choices=[] 且顶层 usage）: "
          f"{last.get('choices') == [] and bool(last.get('usage'))}")
else:
    print("  ⚠️ 未找到任何带 usage 的块")

# ---- Case B: 默认流式（不传 stream_options） ----
show("Case B: stream 默认形态（复现客户观测）")
status, lines = post({"model": MODEL, "stream": True, "max_tokens": 64,
                      "messages": [{"role": "user", "content": "Say hello in one word."}]},
                     stream=True)
print(f"  status={status}  共 {len(lines)} 个 data 行")
for raw in lines[-2:]:
    print(f"  尾部原始块: {raw[:600]}")

# ---- Case C: 同前缀重放缓存命中 ----
show("Case C: 长前缀重放 → cached_tokens 命中验证")
para = ("The history of navigation is a long dialogue between human patience and the "
        "uncertainty of the sea. Early mariners read the color of waves, the flight of "
        "birds, and the temperature of currents to infer the presence of land. ")
prefix = f"Cache probe edition {uuid.uuid4().hex[:8]}\n\n" + para * 24  # 约 1400+ token
msgs = [{"role": "system", "content": prefix},
        {"role": "user", "content": "用一句话概括你的角色。"}]
for i in range(3):
    status, body = post({"model": MODEL, "max_tokens": 64, "reasoning_effort": "low",
                         "messages": msgs})
    if status == 200:
        u = body.get("usage", {})
        print(f"  第{i + 1}次: prompt_tokens={u.get('prompt_tokens')}  "
              f"prompt_tokens_details={json.dumps(u.get('prompt_tokens_details', {}), ensure_ascii=False)}")
    else:
        print(f"  第{i + 1}次: status={status}  {json.dumps(body, ensure_ascii=False)[:300]}")
    time.sleep(3)

# ---- Case C2: 更长前缀 + 更长间隔的缓存复核 ----
show("Case C2: 约2600 token 前缀，间隔 15s/45s 复核缓存")
prefix2 = f"Cache probe edition {uuid.uuid4().hex[:8]}\n\n" + para * 56
msgs2 = [{"role": "system", "content": prefix2},
         {"role": "user", "content": "用一句话概括你的角色。"}]
for i, wait in enumerate([0, 15, 45]):
    if wait:
        print(f"  等待 {wait}s ...")
        time.sleep(wait)
    status, body = post({"model": MODEL, "max_tokens": 64, "reasoning_effort": "low",
                         "messages": msgs2})
    if status == 200:
        u = body.get("usage", {})
        print(f"  第{i + 1}次: prompt_tokens={u.get('prompt_tokens')}  "
              f"prompt_tokens_details={json.dumps(u.get('prompt_tokens_details', {}), ensure_ascii=False)}")
    else:
        print(f"  第{i + 1}次: status={status}  {json.dumps(body, ensure_ascii=False)[:300]}")

# ---- Case D: 视频 URL 边界 ----
show("Case D: 视频 URL 输入（嵌套格式）")
status, body = post({"model": MODEL, "max_tokens": 256,
                     "messages": [{"role": "user", "content": [
                         {"type": "text", "text": "请提取视频中的文字"},
                         {"type": "video_url", "video_url": {"url": VIDEO_URL}}]}]})
print(f"  status={status}")
print(f"  {json.dumps(body, ensure_ascii=False)[:400]}")

# ---- Case E: 对照组 kimi-k2.6 视频（同节点替代方案验证） ----
show("Case E: 对照组 kimi-k2.6 视频 URL")
status, body = post({"model": "kimi-k2.6", "max_tokens": 512,
                     "messages": [{"role": "user", "content": [
                         {"type": "text", "text": "请提取视频中的文字"},
                         {"type": "video_url", "video_url": {"url": VIDEO_URL}}]}]})
print(f"  status={status}")
if status == 200:
    print(f"  content: {body['choices'][0]['message'].get('content', '')[:200]}")
else:
    print(f"  {json.dumps(body, ensure_ascii=False)[:300]}")

print("\n完成。")