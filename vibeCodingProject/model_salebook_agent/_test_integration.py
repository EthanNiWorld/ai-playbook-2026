"""
集成测试脚本 — 模拟一个完整的对话场景
不需要人工输入，自动注入预设回答验证整个 graph 流程
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from langgraph.types import Command
from graph import build_graph


# 模拟用户回答序列（按对话顺序）
SCENARIO = {
    "target_model": "Qwen3.7-Max",
    "answers": [
        # 第一句：透露多个字段
        "客户现在用 Claude Opus 4.8，但觉得太贵想换，他们核心是做 AI Coding 工具，技术团队主导决策",
        # 补充
        "预算很紧，希望能省 30% 以上",
        # 如果 LLM 还问就告诉它
        "调用量每天大概 500 万 tokens，对响应延迟敏感",
        # 兜底强制结束
        "done",
        # confirm 节点确认
        "y",
        # review 节点确认
        "y",
    ],
}


def run_test():
    print("=" * 60)
    print(f"🧪 集成测试 — {SCENARIO['target_model']}")
    print("=" * 60)

    graph = build_graph()
    config = {"configurable": {"thread_id": "test-session-1"}}

    # 启动
    result = graph.invoke({"target_model": SCENARIO["target_model"]}, config=config)

    answer_idx = 0
    max_turns = 30  # 防死循环
    turn = 0

    while turn < max_turns:
        turn += 1

        if not (isinstance(result, dict) and "__interrupt__" in result):
            break

        interrupts = result["__interrupt__"]
        if not interrupts:
            break

        info = interrupts[0].value
        question = info.get("question", "")
        field = info.get("field", "")

        print(f"\n--- Turn {turn} ---")
        print(f"🤖 [{field}] {question[:200]}")

        if answer_idx >= len(SCENARIO["answers"]):
            answer = "done"
        else:
            answer = SCENARIO["answers"][answer_idx]
            answer_idx += 1

        print(f"👤 {answer}")

        result = graph.invoke(Command(resume=answer), config=config)

    print("\n" + "=" * 60)
    if isinstance(result, dict):
        print("✅ 流程完成")
        print(f"  策略类型: {result.get('strategy_type')}")
        print(f"  策略原因: {(result.get('strategy_rationale') or '')[:120]}")
        print(f"  核心卖点: {result.get('key_selling_points', [])[:3]}")
        print(f"  推荐场景: {result.get('recommended_scenarios', [])[:3]}")
        print(f"  输出文件: {result.get('output_path')}")
        print(f"  收集字段:")
        for f in ["customer_current_model", "deal_type", "customer_scenario",
                  "budget_sensitivity", "decision_driver"]:
            print(f"    - {f}: {result.get(f, '(空)')}")
        print(f"  对话轮数: {len(result.get('chat_history') or [])}")
    else:
        print(f"⚠️ 异常结束: {type(result)}")

    print("=" * 60)


if __name__ == "__main__":
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("❌ 需要设置 DASHSCOPE_API_KEY")
        sys.exit(1)
    run_test()
