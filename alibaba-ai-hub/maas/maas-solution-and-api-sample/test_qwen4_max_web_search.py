"""
实测 qwen4-max 联网搜索（enable_search）支持性与用法（国际站新加坡端点）。

用法口径（OpenAI 兼容协议）：
  extra_body={"enable_search": True,
              "search_options": {"forced_search": True, "enable_source": True,
                                 "enable_citation": True,
                                 "citation_format": "[ref_<number>]"},
              "thinking_budget": 1024}
  ⚠️ thinking_budget 与 reasoning_effort 互斥（同设 400），限思考防长考超时
  （实测教训：不限预算时开放问题长考 25s+ 超时，搜索被静默降级为空）。

测试策略：
  A 无搜索基线（enable_thinking=False，纯记忆答实时问题）
  B 兼容模式 enable_search + 引用/来源开关，看回答是否带实时数据与引用
  C DashScope 原生协议 enable_search，抓 output.search_info 实锤搜索发生
"""
import json
import os
import time
import urllib.request

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

KEY = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST")
BASE = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL")
client = OpenAI(api_key=KEY, base_url=BASE, timeout=90)
MODEL = "qwen4-max"
# 实时性问题：训练记忆答不出"今天的日期/最新汇率"，搜索与否差异可判
Q = "现在最新美元兑人民币汇率是多少？请给出数据日期。"

SEARCH_OPTS = {"forced_search": True, "enable_source": True,
               "enable_citation": True, "citation_format": "[ref_<number>]"}


def show(name, resp, t0):
    ch = resp.choices[0]
    u = resp.usage
    rt = getattr(u.completion_tokens_details, "reasoning_tokens", None)
    print("=" * 70)
    print(f"{name} | {time.time() - t0:.1f}s | completion={u.completion_tokens} (reasoning={rt})")
    extra = resp.model_extra or {}
    if "search_info" in extra:
        results = extra["search_info"].get("search_results", [])
        print(f"   search_info: {len(results)} 条来源")
        for r in results[:3]:
            print(f"     - {r.get('title', '')[:40]} | {r.get('url', '')[:70]}")
    print("   answer:", (ch.message.content or "")[:600])
    return ch.message.content or ""


# ── A 基线：不联网 ──
t0 = time.time()
a = show("A 无搜索基线", client.chat.completions.create(
    model=MODEL, messages=[{"role": "user", "content": Q}],
    max_tokens=300, extra_body={"enable_thinking": False}), t0)

# ── B 兼容模式联网搜索 ──
t0 = time.time()
b = show("B enable_search+引用来源", client.chat.completions.create(
    model=MODEL, messages=[{"role": "user", "content": Q}],
    max_tokens=2048,
    extra_body={"enable_search": True, "search_options": SEARCH_OPTS,
                "thinking_budget": 1024}), t0)

# ── C 原生协议：抓 search_info 实锤 ──
# 实测路径结论（2026-11-18）：
#  - qwen4-max 原生 DashScope 走 multimodal-generation 路径（多模态模型），
#    text-generation 路径两节点均报 url error；
#  - workspace 专属域名只支持 compatible-mode，原生须用常规 dashscope 端点；
#  - search_info 需 search_options.enable_source=True 才返回。
KEY_CN = os.getenv("DASHSCOPE_API_KEY_CN_TEST")
native_url = ("https://dashscope.aliyuncs.com"
              "/api/v1/services/aigc/multimodal-generation/generation")
body = {"model": MODEL,
        "input": {"messages": [{"role": "user", "content": [{"text": Q}]}]},
        "parameters": {"enable_search": True, "thinking_budget": 1024,
                       "max_tokens": 2048, "result_format": "message",
                       "search_options": {"forced_search": True,
                                          "enable_source": True}}}
t0 = time.time()
req = urllib.request.Request(
    native_url, data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {KEY_CN}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode())
    print("=" * 70)
    print(f"C 原生协议(CN multimodal-generation) | {time.time() - t0:.1f}s")
    si = d.get("output", {}).get("search_info") or d.get("search_info") or {}
    results = si.get("search_results", [])
    print(f"   search_info: {len(results)} 条来源")
    for r in results[:5]:
        print(f"     - {r.get('title', '')[:40]} | {r.get('site_name', '')} | {r.get('url', '')[:70]}")
    content = d["output"]["choices"][0]["message"]["content"]
    txt = "".join(b.get("text", "") for b in content) if isinstance(content, list) else str(content)
    print("   answer:", txt[:400])
except Exception as e:
    print(f"C 原生协议失败: {type(e).__name__}: {str(e)[:200]}")

print("=" * 70)
print("判定: B/C 回答含 2026-11 近期日期或引用标记、且 search_info 非空 => 联网搜索真实生效")