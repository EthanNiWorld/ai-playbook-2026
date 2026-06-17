# =============================================================================
# test_cache.py — DashScope / 百炼 Prompt Cache 双节点并行测试脚本
#（显式 cache_control:ephemeral vs 隐式 无 cache_control）
#
# 百炼 PTU（Provisioned Throughput Unit）说明：
# 开通 PTU 实例时，系统会基于主账号（main account）所属空间的工作空间 ID 和 host
# 生成一个专属实例。该实例绑定到特定工作空间，拥有独立的域名和模型 ID（带 hash 后缀）。
# PTU 实例的接入方式（工作空间专属域名 + 内部模型 ID）与标准百炼 API 存在差异，
# 以下测试结论中的缓存行为差异即源于此。
#
# 测试结论备忘（2026-06-17 实测）：
#
# 1. 模型名决定缓存是否生效：
#    - 标准模型名（如 glm-5.1、qwen3.7-max）→ 支持 cache_control: ephemeral
#    - 带 hash 后缀的工作空间内部 ID（如 glm-5.1-7f55d130efb8）→ 服务端静默忽略，不返回 cached_tokens
#
# 2. API Key 与 base_url 严格绑定：
#    - sk-ws- 前缀 key 只能访问对应工作空间专属域名（https://{WORKSPACE_ID}.{region}.maas.aliyuncs.com）
#    - 标准百炼 key（sk- 前缀）使用 https://dashscope.aliyuncs.com/compatible-mode/v1
#    - 混用会报 403 "Workspace endpoint access denied" 或 401 "invalid_api_key"
#
# 3. 耗时解读注意事项：
#    - 开启 enable_thinking 后，总耗时 = prompt 处理（含缓存读取）+ reasoning + 回复生成
#    - 缓存命中仅加速 prompt 处理阶段，reasoning_tokens 波动会掩盖缓存收益
#    - 建议对比测试时设置 DASHSCOPE_DISABLE_THINKING=1 以隔离 prompt 处理耗时
#
# 4. 实测数据参考（5 轮，prompt ~20k tokens）：
#    | 接入方式                          | 模型名                    | 缓存 | 首次命中耗时 |
#    |-----------------------------------|---------------------------|------|-------------|
#    | 标准百炼 API (dashscope.aliyuncs) | glm-5.1                   | ✅   | 6.4s (↓58%) |
#    | 工作空间专属域名 (llm-xxx)        | glm-5.1-7f55d130efb8      | ❌   | —           |
#    | 工作空间专属域名 (ws-xxx)         | qwen3.7-max               | ✅   | 2.2s (↓41%) |
#
# 5. 标准百炼 API（dashscope.aliyuncs.com + glm-5.1）双节点并行测试（2026-06-17）：
#    显式 vs 隐式缓存对比，各 5 轮，prompt ~20k tokens：
#
#    | 指标                       | 显式 (explicit)                 | 隐式 (implicit)                 |
#    |----------------------------|---------------------------------|---------------------------------|
#    | cached_tokens              | [0, 20015, 20015, 20015, 20015] | [0, 19840, 19840, 19840, 19840] |
#    | cache_creation_input_tokens | [20015, 0, 0, 0, 0]             | 全部 None（字段不返回）          |
#    | 缓存命中轮次               | 第2~5轮（4/5 命中）             | 第2~5轮（4/5 命中）             |
#    | 耗时中位数                 | 9.135s                          | 10.929s                         |
#
#    关键差异：
#    - 显式模式首轮返回 cache_creation_input_tokens: 20015（明确告知缓存已创建）
#    - 隐式模式不返回 cache_creation_input_tokens 字段，但 cached_tokens 照常返回
#    - 隐式 cached_tokens=19840 < 显式 20015（隐式仅缓存 system 重复上下文，不含 user question）
#
# 6. PTU 工作空间端点 vs 标准百炼 API 缓存可见性对比：
#    | 接入方式                          | 模型名                | 显式缓存 | 隐式缓存 |
#    |-----------------------------------|----------------------|---------|---------|
#    | 标准百炼 API (dashscope.aliyuncs) | glm-5.1              | ✅ 命中 | ✅ 命中 |
#    | PTU 工作空间域名 (llm-xxx)        | glm-5.1-7f55d130efb8 | ❌ 不命中| ❌ 不命中|
#    → PTU 接入层未暴露缓存指标字段，两种缓存模式均无法通过 usage 观测
#
# 快速运行示例：
#   # 标准百炼 API + glm-5.1（推荐，缓存生效）
#   DASHSCOPE_API_KEY="$DASHSCOPE_API_KEY_CN" \
#   DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1" \
#   DASHSCOPE_MODEL="glm-5.1" \
#   python3 test_cache.py
#
#   # 工作空间专属域名 + qwen3.7-max
#   DASHSCOPE_API_KEY="sk-ws-xxx" \
#   DASHSCOPE_MODEL="qwen3.7-max" \
#   python3 test_cache.py
# =============================================================================

import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI


MODEL = os.getenv("DASHSCOPE_MODEL", "glm-5.1-7f55d130efb8")
REPEATS = int(os.getenv("CACHE_TEST_REPEATS", "5"))
PRINT_RAW = os.getenv("CACHE_TEST_PRINT_RAW", "0") == "1"
DISABLE_THINKING = os.getenv("DASHSCOPE_DISABLE_THINKING", "0") == "1"
WORKSPACE_ID = os.getenv("DASHSCOPE_WORKSPACE_ID", "llm-ablnum2bgfvl34hs")
REGION = os.getenv("DASHSCOPE_REGION", "ap-southeast-1")
BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    f"https://{WORKSPACE_ID}.{REGION}.maas.aliyuncs.com/compatible-mode/v1",
)

client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=BASE_URL,
)

long_context = (
    "你是一个严谨的测试助手。以下是固定上下文：\n"
    + ("缓存测试资料。请严格基于资料回答。\n" * 2000)
)


def usage_to_dict(usage):
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        # exclude_none=True avoids OpenAI SDK default fields looking like
        # server-returned null values.
        return usage.model_dump(exclude_none=True)
    return dict(usage)


def get_nested(data, *keys):
    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def get_request_id(raw_response):
    request_id = getattr(raw_response, "request_id", None)
    if request_id:
        return request_id

    for header_name in (
        "x-request-id",
        "x-acs-request-id",
        "x-dashscope-request-id",
        "dashscope-request-id",
    ):
        header_value = raw_response.headers.get(header_name)
        if header_value:
            return header_value

    return None


def build_request(question, cache_mode="explicit"):
    system_content = {"type": "text", "text": long_context}
    if cache_mode == "explicit":
        system_content["cache_control"] = {"type": "ephemeral"}

    request = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": [system_content],
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0,
        # Keep generation short so latency mostly reflects prompt processing.
        "max_tokens": 16,
    }

    if DISABLE_THINKING:
        # 关闭思考可隔离 prompt 处理耗时，更准确地衡量缓存收益
        request["extra_body"] = {"enable_thinking": False}
    else:
        # 开启深度思考；注意：reasoning_tokens 波动大（100~600+），会显著影响总耗时
        request["extra_body"] = {"enable_thinking": True}

    return request


def run_once(index, question, cache_mode="explicit"):
    start = time.perf_counter()
    raw_response = client.chat.completions.with_raw_response.create(**build_request(question, cache_mode))
    elapsed = time.perf_counter() - start

    response = raw_response.parse()
    response_json = json.loads(raw_response.text)
    request_id = get_request_id(raw_response)
    completion_id = response_json.get("id")
    raw_usage = response_json.get("usage") or {}
    cached_tokens = get_nested(raw_usage, "prompt_tokens_details", "cached_tokens")
    cache_creation_input_tokens = get_nested(raw_usage, "prompt_tokens_details", "cache_creation_input_tokens")

    print(f"[{cache_mode}] run: {index}")
    print(f"[{cache_mode}] request_id: {request_id if request_id else 'not returned'}")
    print(f"[{cache_mode}] elapsed: {round(elapsed, 3)} s")
    print(f"[{cache_mode}] cached_tokens: {cached_tokens if cached_tokens is not None else 'not returned'}")
    print(f"[{cache_mode}] cache_creation_input_tokens: {cache_creation_input_tokens if cache_creation_input_tokens is not None else 'not returned'}")
    print(f"[{cache_mode}] raw_has_cached_tokens: {'cached_tokens' in raw_response.text}")

    if PRINT_RAW:
        print(f"[{cache_mode}] raw_response: {json.dumps(response_json, ensure_ascii=False, indent=2)}")

    return {
        "cache_mode": cache_mode,
        "request_id": request_id,
        "completion_id": completion_id,
        "elapsed": elapsed,
        "prompt_tokens": raw_usage.get("prompt_tokens"),
        "completion_tokens": raw_usage.get("completion_tokens"),
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cached_tokens": cached_tokens,
        "has_cached_tokens_field": "cached_tokens" in raw_response.text,
    }


def run_node(cache_mode):
    """Run all REPEATS requests for a given cache_mode, return results list."""
    question = "请只回答两个字：收到。"
    print(f"\n{'=' * 60}")
    print(f">>> Node [{cache_mode}] starting {REPEATS} runs...")
    print(f"{'=' * 60}")
    results = [run_once(i, question, cache_mode) for i in range(1, REPEATS + 1)]
    print(f">>> Node [{cache_mode}] done.")
    return results


def print_summary(results, label):
    elapsed_values = [item["elapsed"] for item in results]
    creation_values = [
        item["cache_creation_input_tokens"]
        for item in results
        if item["cache_creation_input_tokens"] is not None
    ]
    cached_values = [item["cached_tokens"] for item in results if item["cached_tokens"] is not None]
    has_cache_field = any(item["has_cached_tokens_field"] for item in results)

    print(f"\n{'=' * 60}")
    print(f"summary [{label}]")
    print("model:", MODEL)
    print("base_url", BASE_URL)
    print("prompt_tokens", [item["prompt_tokens"] for item in results])
    print("completion_tokens", [item["completion_tokens"] for item in results])
    print("cache_creation_input_tokens", [item["cache_creation_input_tokens"] for item in results])
    print("cached_tokens", [item["cached_tokens"] for item in results])
    print("elapsed_seconds", [round(v, 3) for v in elapsed_values])
    print("elapsed_median", round(statistics.median(elapsed_values), 3), "s")

    if MODEL.startswith("glm-"):
        print("note: 当前模型名以 glm- 开头。")
        print("      - 标准名（如 glm-5.1）+ 标准百炼 API → 支持显式缓存")
        print("      - 带 hash 后缀的工作空间 ID（如 glm-5.1-7f55d130efb8）→ 显式缓存不支持")
        print("      - PTU 模式下隐式缓存可能仍然生效（研发确认）")

    if cached_values:
        print(f"verdict: 服务端返回了 cached_tokens，缓存命中（{label}）。")
        if creation_values:
            print("cache_created", creation_values)
    elif has_cache_field:
        print("verdict: 服务端返回了 cached_tokens 字段，但本次没有有效数值。")
    else:
        print("verdict: 服务端没有返回 cached_tokens 字段；当前 base_url/model 可能不支持缓存。")


def main():
    print(f"\n{'=' * 60}")
    print("Dual-node parallel test: explicit vs implicit cache")
    print(f"model: {MODEL}  |  base_url: {BASE_URL}  |  repeats: {REPEATS}")
    print(f"{'=' * 60}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_node, "explicit"): "explicit",
            executor.submit(run_node, "implicit"): "implicit",
        }
        all_results = {}
        for future in as_completed(futures):
            label = futures[future]
            all_results[label] = future.result()

    # Print individual summaries
    for label in ("explicit", "implicit"):
        print_summary(all_results[label], label)

    # Comparative verdict
    print(f"\n{'=' * 60}")
    print("COMPARATIVE VERDICT")
    exp = all_results["explicit"]
    imp = all_results["implicit"]
    exp_median = round(statistics.median([r["elapsed"] for r in exp]), 3)
    imp_median = round(statistics.median([r["elapsed"] for r in imp]), 3)
    exp_cached = [r["cached_tokens"] for r in exp if r["cached_tokens"] is not None]
    imp_cached = [r["cached_tokens"] for r in imp if r["cached_tokens"] is not None]
    print(f"  explicit median: {exp_median}s  cached_tokens: {exp_cached}")
    print(f"  implicit median: {imp_median}s  cached_tokens: {imp_cached}")

    if exp_cached and imp_cached:
        print("  Both modes returned cached_tokens → both explicit and implicit cache work on this endpoint.")
    elif exp_cached and not imp_cached:
        print("  Only explicit returned cached_tokens → implicit cache not visible via usage field (may still reduce TTFT).")
    elif not exp_cached and imp_cached:
        print("  Only implicit returned cached_tokens → explicit cache_control ignored, implicit auto-cache works.")
    else:
        print("  Neither returned cached_tokens → no cache observable via usage on this endpoint.")
        print("  Check if TTFT still drops on repeated requests (latency comparison may reveal implicit cache).")


if __name__ == "__main__":
    main()
