"""
review 节点 — 用户审核确认，通过 interrupt 等待反馈
"""

from langgraph.types import interrupt
from state import SalebookState


def review_node(state: SalebookState) -> dict:
    """展示摘要，等待用户确认或修改意见"""
    # 展示生成摘要
    summary = f"""
━━━ Salebook 生成完成 ━━━
📄 文件: {state.get('output_path', '未知')}
🎯 策略: {state.get('strategy_type', '')}
📋 卖点: {', '.join(state.get('key_selling_points', [])[:3])}
"""
    print(summary)

    # interrupt 等待用户确认
    feedback = interrupt({
        "question": "是否满意？输入 'y' 确认，或输入修改意见重新生成：",
        "field": "review_feedback",
        "summary": summary,
    })

    feedback_str = feedback.strip() if isinstance(feedback, str) else str(feedback)

    if feedback_str.lower() in ("y", "yes", "ok", "确认", "好", "满意"):
        return {"review_feedback": ""}
    else:
        return {"review_feedback": feedback_str}
