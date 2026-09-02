#!/usr/bin/env python3
"""
qwen3.8-2.4t-a95b（百炼专属端点）思考模式与思考长度控制完整测试套件

测试分组：
  A. 思考开关
    A1. enable_thinking=False（API 硬开关）
    A2. enable_thinking=True + 提示词追加 /no_think（软开关）
    A3. enable_thinking=True（对照组）
  B. 思考长度控制（思考关不掉时的曲线方案）
    B1. thinking_budget=1 / 1024（Token 硬上限）
    B2. reasoning_effort=low / medium / high（推理力度档位）
  C. 边界行为
    C1. reasoning_effort=none（官方语义：等价 enable_thinking=False）
    C2. thinking_budget 与 reasoning_effort 同时设置（闭源版 max/flash 互斥，a95b 行为验证）

正常用例重复 REPEAT 次（默认 3）以观察方差；报错用例只跑 1 次。
测试结果沉淀：test_qwen38_a95b_thinking_switch_results_20260827.md
"""
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 文件（从项目根目录向上查找）
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

API_KEY = os.getenv("DASHSCOPE_API_KEY_CN_TEST", "")
BASE_URL = os.getenv("DASHSCOPE_API_KEY_CN_URL", "")

if not API_KEY or not BASE_URL:
    print("Error: 请在 .env 文件中配置 DASHSCOPE_API_KEY_CN_TEST 和 DASHSCOPE_API_KEY_CN_URL")
    sys.exit(1)

MODEL = "qwen3.8-2.4t-a95b"
REPEAT = 3  # 正常用例重复次数

# 推理题：有思考区分度，回复较短，便于对比思考长度差异
PROMPT = "一个水库的水位每天翻倍，50天灌满，第几天灌一半？请简要推理。"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

results = []  # [(用例名, 结果行)]，最后汇总打印


def run_once(extra_body, prompt):
    """单次调用，返回 (思考字符数, 回复字符数, 耗时s) 或报错信息字符串"""
    start = time.time()
    reasoning_len = 0
    content_len = 0
    try:
        # 开源系列模型建议流式调用
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            extra_body=extra_body,
            stream=True,
        )
        for chunk in completion:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                reasoning_len += len(delta.reasoning_content)
            if hasattr(delta, "content") and delta.content:
                content_len += len(delta.content)
    except Exception as e:
        return f"ERR {type(e).__name__}: {str(e)[:120]}"
    return reasoning_len, content_len, time.time() - start


def run_case(case_id, title, extra_body, prompt=PROMPT, repeat=1, expect_error=False):
    """执行测试用例并记录结果"""
    print(f"\n{'=' * 12} [{case_id}] {title} {'=' * 12}")
    runs = []
    for i in range(repeat):
        out = run_once(extra_body, prompt)
        if isinstance(out, str):
            print(f"  第{i + 1}次: {out}")
            runs.append(out)
            if expect_error:
                break  # 报错用例跑 1 次即可
        else:
            r_len, c_len, el = out
            print(f"  第{i + 1}次: 思考字符={r_len}, 回复字符={c_len}, 耗时={el:.1f}s")
            runs.append((r_len, c_len, el))

    # 汇总结论
    ok_runs = [r for r in runs if isinstance(r, tuple)]
    if ok_runs:
        think_lens = [r[0] for r in ok_runs]
        avg_think = sum(think_lens) / len(think_lens)
        has_think = all(l > 0 for l in think_lens)
        concl = f"思考={avg_think:.0f}字符(均值, 轮次{think_lens}) -> 思考模式{'开启' if has_think else '关闭'}"
    else:
        concl = runs[0] if runs else "无结果"
    print(f"  >>> {concl}")
    results.append((f"[{case_id}] {title}", concl))


if __name__ == "__main__":
    # ===== A. 思考开关 =====
    run_case("A1", "enable_thinking=False（API 硬开关）",
             {"enable_thinking": False}, expect_error=True)
    run_case("A2", "enable_thinking=True + 提示词追加 /no_think（软开关）",
             {"enable_thinking": True}, prompt=PROMPT + " /no_think", repeat=REPEAT)
    run_case("A3", "enable_thinking=True（对照组）",
             {"enable_thinking": True}, repeat=REPEAT)

    # ===== B. 思考长度控制 =====
    run_case("B1a", "thinking_budget=1（Token 硬上限压至极短）",
             {"enable_thinking": True, "thinking_budget": 1}, repeat=REPEAT)
    run_case("B1b", "thinking_budget=1024",
             {"enable_thinking": True, "thinking_budget": 1024}, repeat=REPEAT)
    run_case("B2a", "reasoning_effort=low（轻度推理）",
             {"enable_thinking": True, "reasoning_effort": "low"}, repeat=REPEAT)
    run_case("B2b", "reasoning_effort=medium（中力度推理）",
             {"enable_thinking": True, "reasoning_effort": "medium"}, repeat=REPEAT)
    run_case("B2c", "reasoning_effort=high（高力度推理）",
             {"enable_thinking": True, "reasoning_effort": "high"}, repeat=REPEAT)

    # ===== C. 边界行为 =====
    run_case("C1", "reasoning_effort=none（官方语义等价 enable_thinking=False）",
             {"enable_thinking": True, "reasoning_effort": "none"}, expect_error=True)
    run_case("C2", "thinking_budget=4096 + reasoning_effort=low 同时设置（闭源版互斥，a95b 验证）",
             {"enable_thinking": True, "thinking_budget": 4096, "reasoning_effort": "low"},
             repeat=1, expect_error=True)

    # ===== 汇总表 =====
    print(f"\n{'=' * 20} 汇总 {'=' * 20}")
    for name, concl in results:
        print(f"{name}\n    {concl}")
