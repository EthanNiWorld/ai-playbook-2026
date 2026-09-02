#!/usr/bin/env python3
"""
qwen3.8-27b（Qwen3.8 系列 27B Dense 视觉语言开源模型）思考模式测试套件

测试分组：
  A. 思考开关（主测 CN 专属端点，A1 关键用例三端点交叉验证）
    A1. enable_thinking=False（API 硬开关）—— 关键用例
    A2. 不传 enable_thinking（默认行为探测）
    A3. enable_thinking=True + 提示词追加 /no_think（软开关）
    A4. enable_thinking=True（对照组）
  B. 思考长度控制
    B1. thinking_budget=1024
    B2. reasoning_effort=low
  C. 边界行为
    C1. reasoning_effort=none（官方语义：等价 enable_thinking=False）
    C2. thinking_budget 与 reasoning_effort 同时设置（互斥验证）

正常用例重复 REPEAT 次（默认 3）以观察方差；报错用例跑 1 次即停。
对照：qwen3.8-2.4t-a95b 实测为仅思考模式（enable_thinking 仅接受 True），
本脚本验证 27b 是否同样受限。
"""
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 文件（从项目根目录向上查找）
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

ENDPOINTS = {
    "CN专属": (os.getenv("DASHSCOPE_API_KEY_CN_TEST", ""), os.getenv("DASHSCOPE_API_KEY_CN_URL", "")),
    "国际站BJ": (os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST", ""), os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST_URL", "")),
    "国际站SG": (os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", ""), os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "")),
}

MODEL = "qwen3.8-27b"
REPEAT = 3  # 正常用例重复次数

# 推理题：与 a95b 测试同题，便于横向对比
PROMPT = "一个水库的水位每天翻倍，50天灌满，第几天灌一半？请简要推理。"

main_key, main_url = ENDPOINTS["CN专属"]
if not main_key or not main_url:
    print("Error: 请在 .env 文件中配置 DASHSCOPE_API_KEY_CN_TEST 和 DASHSCOPE_API_KEY_CN_URL")
    sys.exit(1)

client = OpenAI(api_key=main_key, base_url=main_url)

results = []  # [(用例名, 结果行)]，最后汇总打印


def run_once(cli, extra_body, prompt, model=MODEL):
    """单次调用，返回 (思考字符数, 回复字符数, 耗时s) 或报错信息字符串"""
    start = time.time()
    reasoning_len = 0
    content_len = 0
    try:
        completion = cli.chat.completions.create(
            model=model,
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
        return f"ERR {type(e).__name__}: {str(e)[:150]}"
    return reasoning_len, content_len, time.time() - start


def run_case(case_id, title, extra_body, prompt=PROMPT, repeat=1):
    """执行测试用例并记录结果（自适应：报错或成功均完整记录）"""
    print(f"\n{'=' * 12} [{case_id}] {title} {'=' * 12}")
    runs = []
    for i in range(repeat):
        out = run_once(client, extra_body, prompt)
        if isinstance(out, str):
            print(f"  第{i + 1}次: {out}")
            runs.append(out)
            break  # 报错即停，无需重复
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
             {"enable_thinking": False}, repeat=REPEAT)
    run_case("A2", "不传 enable_thinking（默认行为探测）",
             {}, repeat=REPEAT)
    run_case("A3", "enable_thinking=True + 提示词追加 /no_think（软开关）",
             {"enable_thinking": True}, prompt=PROMPT + " /no_think", repeat=REPEAT)
    run_case("A4", "enable_thinking=True（对照组）",
             {"enable_thinking": True}, repeat=REPEAT)

    # ===== B. 思考长度控制 =====
    run_case("B1", "thinking_budget=1024",
             {"enable_thinking": True, "thinking_budget": 1024}, repeat=REPEAT)
    run_case("B2", "reasoning_effort=low",
             {"enable_thinking": True, "reasoning_effort": "low"}, repeat=REPEAT)

    # ===== C. 边界行为 =====
    run_case("C1", "reasoning_effort=none（官方语义等价 enable_thinking=False）",
             {"enable_thinking": True, "reasoning_effort": "none"})
    run_case("C2", "thinking_budget=4096 + reasoning_effort=low 同时设置（互斥验证）",
             {"enable_thinking": True, "thinking_budget": 4096, "reasoning_effort": "low"})

    # ===== A1 三端点交叉验证（若主端点关闭成功/报错，验证其他端点行为是否一致）=====
    print(f"\n{'=' * 12} [X] A1 enable_thinking=False 三端点交叉验证 {'=' * 12}")
    for name, (key, url) in ENDPOINTS.items():
        if not key or not url:
            print(f"  {name}: 缺少配置，跳过")
            continue
        cli = OpenAI(api_key=key, base_url=url)
        out = run_once(cli, {"enable_thinking": False}, PROMPT)
        if isinstance(out, str):
            print(f"  {name}: {out}")
            results.append((f"[X] {name} enable_thinking=False", out))
        else:
            r_len, c_len, el = out
            concl = f"思考字符={r_len}, 回复字符={c_len} -> 思考模式{'开启' if r_len > 0 else '关闭'}"
            print(f"  {name}: {concl}")
            results.append((f"[X] {name} enable_thinking=False", concl))

    # ===== 汇总表 =====
    print(f"\n{'=' * 20} 汇总 {'=' * 20}")
    for name, concl in results:
        print(f"{name}\n    {concl}")
