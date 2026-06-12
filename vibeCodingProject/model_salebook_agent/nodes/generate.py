"""
generate 节点 — 两阶段生成 HTML Salebook
阶段1: LLM 生成结构化 JSON
阶段2: Python 渲染为 HTML
"""

import json
import re
from datetime import datetime
from langchain_openai import ChatOpenAI
from state import SalebookState
from config import get_llm_config, get_output_path
from prompts.generation_prompt import GENERATION_SYSTEM_PROMPT
from templates.components import render_salebook_html


def generate_node(state: SalebookState) -> dict:
    """生成 HTML Salebook"""
    print("\n📝 生成 Salebook 中...")

    # 阶段 1: LLM 生成结构化内容 JSON
    llm_cfg = get_llm_config()
    llm = ChatOpenAI(
        model=llm_cfg["model"],
        api_key=llm_cfg["api_key"],
        base_url=llm_cfg["base_url"],
        temperature=0.5,
        max_tokens=8192,
    )

    user_msg = f"""## 目标模型: {state['target_model']}

## 策略类型: {state.get('strategy_type', '')}

## 策略简报（依据此生成）
{state.get('strategy_brief', '')}

## 客户情况
- 竞品: {state.get('customer_current_model', '未知')}
- 机会: {state.get('deal_type', '')}
- 场景: {state.get('customer_scenario', '')}
- 预算敏感度: {state.get('budget_sensitivity', '')}

## 模型知识库数据
{(state.get('model_data') or '')[:8000]}

{f"## 用户修改意见（请据此调整）：{state.get('review_feedback', '')}" if state.get('review_feedback') else ""}

请生成 Salebook 内容 JSON。
"""

    messages = [
        {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    response = llm.invoke(messages)
    salebook_json = _parse_json(response.content)

    if not salebook_json:
        print("  ⚠️ JSON 解析失败，使用默认结构")
        salebook_json = _fallback_json(state)
    # 阶段 2: 渲染 HTML
    html_content = render_salebook_html(salebook_json)

    # 保存文件
    model_slug = state["target_model"].lower().replace(" ", "-").replace(".", "")
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{model_slug}_salebook_{date_str}.html"
    output_file = get_output_path() / filename
    output_file.write_text(html_content, encoding="utf-8")

    print(f"  ✓ HTML 已生成: {output_file}")

    return {
        "salebook_json": salebook_json,
        "html_content": html_content,
        "output_path": str(output_file),
    }


def _parse_json(text: str) -> dict | None:
    """解析 LLM 输出的 JSON"""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None


def _fallback_json(state: SalebookState) -> dict:
    """解析失败时的回退 JSON"""
    return {
        "hero": {
            "model_name": state["target_model"],
            "tagline": "AI Model Salebook",
            "stats": [],
        },
        "positioning": state.get("strategy_rationale", ""),
        "vs_previous": {"title": "vs 上一代", "points": []},
        "vs_competitors": {"title": "vs 竞品", "competitor_name": "", "rows": []},
        "architecture_advantages": [],
        "scenarios": [],
        "pricing": {
            "our_model": {"name": state["target_model"], "input_price": "—", "output_price": "—"},
            "competitors": [],
            "savings_highlight": "",
        },
        "talking_points": [
            {"question": p, "answer": ""}
            for p in state.get("talking_points", [])
        ],
        "cta": {
            "title": "立即接入",
            "primary_link": "https://bailian.console.alibabacloud.com",
            "primary_text": "开通百炼 →",
        },
    }
