"""
Model Salebook Agent — 终端入口
================================

基于 LangGraph 的模型销售指导文档生成 Agent。
通过对话引导 BD/SA 梳理客户情况，自动生成定制化 HTML Salebook。

使用:
    python main.py                                    # 交互式（会提示输入模型名）
    python main.py --model "Qwen3.7-Max"              # 直接指定目标模型
    python main.py --llm qwen3.7-plus                 # 切换底层 LLM

环境变量:
    DASHSCOPE_API_KEY  — 必须，DashScope API Key
    SALEBOOK_MODEL     — 可选，底层 LLM（默认 qwen3.7-max，可用 --llm 覆盖）
"""

import sys
import re
import argparse

# 确保项目根目录在 path 中
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from langgraph.types import Command
from graph import build_graph
from config import MODEL_OPTIONS, DEFAULT_MODEL, set_runtime_model


MODEL_NAME_RE = re.compile(
    r"(qwen[\d.]+-(?:max|plus|flash)(?:-preview)?"
    r"|wan[\d.]+"
    r"|deepseek-v[\d.]+(?:-pro|-flash)?"
    r"|claude-(?:opus|sonnet|haiku)-?[\d.]*"
    r"|gpt-[\d.]+(?:-mini|-nano)?"
    r"|gemini-[\d.]+"
    r"|kimi-k[\d.]+"
    r"|glm-[\d.]+)",
    re.IGNORECASE,
)


def parse_first_message(text: str) -> tuple[str, str]:
    """从首条输入拆出 target_model + user_brief"""
    text = text.strip()
    m = MODEL_NAME_RE.search(text)
    if m:
        target = m.group(0)
        brief = (text[:m.start()] + " " + text[m.end():]).strip()
        return target, brief
    return text, ""


def main():
    parser = argparse.ArgumentParser(description="Model Salebook Agent")
    parser.add_argument(
        "--model", "-m", type=str, default="",
        help="首条输入：模型名 + 客户场景一句话（如 'Qwen3.7-Plus 德勤 3.6 升级'）",
    )
    parser.add_argument(
        "--llm", "-l", type=str, default="",
        choices=[""] + MODEL_OPTIONS,
        help=f"底层 LLM（可选 {' / '.join(MODEL_OPTIONS)}，默认 {DEFAULT_MODEL}）",
    )
    args = parser.parse_args()

    if args.llm:
        set_runtime_model(args.llm)
    active_llm = args.llm or DEFAULT_MODEL

    print(f"""
┌─ Model Salebook Agent v1.0
│  底层 LLM: {active_llm}
└──────────────────────────────
""")

    # 获取首条输入（模型名 + 客户背景一句话）
    first_msg = args.model
    if not first_msg:
        first_msg = input(
            "请一句话说明目标模型 + 客户场景：\n"
            "  示例：“Qwen3.7-Plus 德勤从 3.6-Plus 升级，纠结上 Max 还是 Plus”\n> "
        ).strip()
        if not first_msg:
            print("[ERROR] 未输入任何内容，退出。")
            return

    target_model, user_brief = parse_first_message(first_msg)

    # 构建 graph
    graph = build_graph()
    config = {"configurable": {"thread_id": f"session-{target_model}"}}

    # 启动图执行
    print(f"\n🚀 启动 Salebook Agent：目标模型={target_model}")
    if user_brief:
        print(f"   客户描述：{user_brief}")
    init_state = {"target_model": target_model}
    if user_brief:
        init_state["user_brief"] = user_brief
    result = graph.invoke(init_state, config=config)

    # 交互循环：处理 interrupt
    while hasattr(result, "__getitem__") and "__interrupt__" in result:
        interrupts = result["__interrupt__"]
        for intr in interrupts:
            info = intr.value
            question = info.get("question", "请输入：")
            print(f"\n{'-' * 50}")
            answer = input(f"{question}\n> ").strip()
            result = graph.invoke(Command(resume=answer), config=config)

    # 完成
    if isinstance(result, dict) and result.get("output_path"):
        print(f"""
{'=' * 50}
[OK] Salebook 生成完成！
文件路径: {result['output_path']}
策略类型: {result.get('strategy_type', '')}
{'=' * 50}
""")
    else:
        print("\n[OK] 完成。")


if __name__ == "__main__":
    main()
