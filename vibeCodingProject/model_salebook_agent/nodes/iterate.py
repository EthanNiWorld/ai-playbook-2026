"""
iterate 节点 — 展示 Markdown 策略简报，等待 SA/BD 反馈
======================================================

行为：
- 展示当前 strategy_brief（含 🧩 当前理解 推断块）
- SA/BD 输入：
    - 'y' / 'ok' / '生成' / 'go' → 进入 generate
    - 任何其他文本 → 视为补充/纠正信息，累加到 user_brief，回 strategy 重写

替代旧 confirm 节点的"y/n 二选一"模式，支持"先出稿、再迭代"。
"""

from langgraph.types import interrupt
from state import SalebookState


STRATEGY_LABEL = {
    "tech_advantage": "📊 技术碾压—以 benchmark 数据说话",
    "price_value": "💰 性价比—同等能力更低成本",
    "trojan_horse": "🐴 田忌赛马—先做进去等模型升级",
}

# 进入生成的关键词（SA/BD 满意时输入）
GENERATE_SIGNALS = {"y", "yes", "ok", "好", "确认", "生成", "go", "开始", "出"}


def iterate_node(state: SalebookState) -> dict:
    """展示当前简报，收集自由反馈或生成信号"""
    strategy_type = state.get("strategy_type", "")
    label = STRATEGY_LABEL.get(strategy_type, strategy_type or "未知")
    brief = state.get("strategy_brief", "（无策略简报）")

    summary = f"""
━━━ 当前策略简报（v{_brief_version(state)}）━━━

**🎯 选定路径**: {label}

{brief}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ **下一步**：
- 直接说补充/纠正信息（如 "客户其实是金融，对价格极敏感"），我会重写简报
- 或回复 `y` / `ok` / `生成` 直接进入 HTML Salebook 生成
"""
    print(summary)

    feedback = interrupt({
        "question": "继续调整还是直接生成？",
        "field": "iterate_feedback",
        "summary": summary,
    })

    feedback_str = feedback.strip() if isinstance(feedback, str) else str(feedback)

    # 满意 → 进 generate
    if feedback_str.lower() in GENERATE_SIGNALS:
        return {"iterate_done": True}

    # 否则把反馈累加到 user_brief，回 strategy
    prev_brief = (state.get("user_brief") or "").strip()
    if prev_brief:
        new_brief = f"{prev_brief}\n\n[追加补充] {feedback_str}"
    else:
        new_brief = feedback_str

    return {
        "user_brief": new_brief,
        "iterate_done": False,
    }


def _brief_version(state: SalebookState) -> int:
    """简单数一下迭代轮次（user_brief 里 [追加补充] 的次数 + 1）"""
    brief = state.get("user_brief") or ""
    return brief.count("[追加补充]") + 1
