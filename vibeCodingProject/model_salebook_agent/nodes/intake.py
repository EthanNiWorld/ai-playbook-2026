"""
intake 节点 — 加载本地知识库数据，识别数据缺口
"""

from state import SalebookState
from tools.knowledge_reader import (
    load_model_knowledge,
    load_sales_strategy,
    load_competitive_analysis,
)
from tools.web_researcher import research_model


def intake_node(state: SalebookState) -> dict:
    """
    加载本地知识 + 识别缺口 + 联网补全。
    """
    target = state["target_model"]
    print(f"\n🔍 正在加载 {target} 的知识数据...")

    # 1. 加载本地知识
    model_data = load_model_knowledge(target)
    sales_strategy = load_sales_strategy()
    competitive = load_competitive_analysis(target)

    # 2. 识别数据缺口
    data_gaps = []
    if not model_data:
        data_gaps.append(f"本地未找到 {target} 的模型文档")
    if not competitive:
        data_gaps.append(f"本地未找到 {target} 的竞品分析")

    # 3. 如有缺口，联网搜索补全
    web_research = []
    if data_gaps:
        print(f"⚠️ 数据缺口: {data_gaps}")
        print("🌐 正在联网搜索补全...")
        web_research = research_model(target, "benchmark pricing capabilities")

    # 合并知识
    combined_data = model_data
    if competitive:
        combined_data += f"\n\n---\n## 竞品分析\n{competitive}"
    if web_research:
        web_text = "\n".join(
            f"- [{r['title']}]({r['source']}): {r['content']}"
            for r in web_research[:5]
        )
        combined_data += f"\n\n---\n## 联网搜索补充（{len(web_research)} 条）\n{web_text}"

    status = "✓ 本地知识加载完成" if model_data else "⚠️ 本地无数据，依赖联网搜索"
    if web_research:
        status += f"（+{len(web_research)} 条联网结果）"
    print(f"  {status}")

    return {
        "model_data": combined_data,
        "sales_strategy": sales_strategy,
        "web_research": web_research,
        "data_gaps": data_gaps,
    }
