"""
状态定义 — LangGraph 全局共享状态 Schema
"""

from typing import TypedDict, Optional


class SalebookState(TypedDict, total=False):
    """贯穿所有节点的共享状态"""

    # ─── 输入 ───
    target_model: str  # 用户指定的模型名（如 "Qwen3.7-Max", "Wan2.7"）
    user_brief: str  # SA/BD 累积输入的自由文本（首条剩余 + 后续 iterate 反馈）

    # ─── LLM 推断/收集的客户字段（全部可选，strategy 阶段推断填充）───
    customer_current_model: str  # 客户目前用什么模型
    deal_type: str  # "upsell" | "winback" | "new"
    customer_scenario: str  # 核心业务场景
    budget_sensitivity: str  # "high" | "medium" | "low"
    decision_driver: str  # "tech" | "business" | "mixed"
    chat_history: list  # 保留：供历史调试/追溯

    # ─── 企业画像（首轮识别+联网搜索后缓存，避免重复调用）───
    enterprise_name: str  # 从 user_brief 识别到的企业名（未识别为空）
    enterprise_profile: str  # 联网搜索拼接的企业画像原材料

    # ─── 策略分析结果 ───
    strategy_type: str  # "tech_advantage" | "price_value" | "trojan_horse"
    strategy_brief: str  # 策略简报整段 Markdown（供 iterate 展示、generate 拼 prompt）
    iterate_done: bool  # iterate 节点送出生成信号，为 True 进 generate
    # 以下为旧字段兼容（MD 输出后不再填充，保留以免老代码路径 KeyError）
    strategy_rationale: str  # 废弃：合并到 strategy_brief
    key_selling_points: list  # 废弃
    competitive_comparison: dict  # 废弃
    recommended_scenarios: list  # 废弃
    talking_points: list  # 废弃

    # ─── 知识数据 ───
    model_data: str  # 从本地 knowledge/ 加载的模型文档原文
    sales_strategy: str  # 销售策略原文
    web_research: list  # 联网搜索结果 [{source, content, date}]
    data_gaps: list  # 本地知识缺口描述

    # ─── 生成输出 ───
    salebook_json: dict  # LLM 生成的结构化内容 JSON
    html_content: str  # 渲染后的 HTML
    output_path: str  # 输出文件路径

    # ─── 审核 ───
    review_feedback: str  # 用户修改意见（空=通过）
