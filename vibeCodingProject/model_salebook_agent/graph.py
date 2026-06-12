"""
LangGraph 状态图定义（先出稿、再迭代）
======================================
START → intake → strategy → iterate ⇄ strategy
                              ↓ iterate_done
                              generate → review → END
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import SalebookState
from nodes.intake import intake_node
from nodes.strategy import strategy_node
from nodes.iterate import iterate_node
from nodes.generate import generate_node
from nodes.review import review_node


def should_proceed_after_iterate(state: SalebookState) -> str:
    """SA/BD 满意 → generate；否则回 strategy 重写"""
    if state.get("iterate_done"):
        return "generate"
    return "strategy"


def should_regenerate(state: SalebookState) -> str:
    """review 节点：用户接受最终 HTML 否？"""
    if state.get("review_feedback"):
        return "generate"  # 有修改意见，重新生成
    return END


def build_graph():
    """构建并编译 LangGraph 状态图"""
    builder = StateGraph(SalebookState)

    builder.add_node("intake", intake_node)
    builder.add_node("strategy", strategy_node)
    builder.add_node("iterate", iterate_node)
    builder.add_node("generate", generate_node)
    builder.add_node("review", review_node)

    # 主流程：intake → strategy → iterate
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "strategy")
    builder.add_edge("strategy", "iterate")

    # iterate 路由：满意进 generate，否则回 strategy
    builder.add_conditional_edges(
        "iterate",
        should_proceed_after_iterate,
        {"strategy": "strategy", "generate": "generate"},
    )

    # generate → review → END / 重新生成
    builder.add_edge("generate", "review")
    builder.add_conditional_edges(
        "review",
        should_regenerate,
        {"generate": "generate", END: END},
    )

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph
