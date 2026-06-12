"""
strategy 节点 — 调用 LLM 输出 Markdown 策略简报
================================================
输出形态：
    第 1 行: STRATEGY_TYPE: <tech_advantage|price_value|trojan_horse>
    第 2 行: ---
    之后:    完整 Markdown 简报

state 写入：
    strategy_type   — 路由用枚举
    strategy_brief  — 整段 Markdown，供 confirm 直接展示 / generate 拼 prompt
"""

import re
from langchain_openai import ChatOpenAI
from state import SalebookState
from config import get_llm_config
from prompts.strategy_prompt import STRATEGY_SYSTEM_PROMPT
from tools.web_researcher import research_enterprise


VALID_STRATEGIES = {"tech_advantage", "price_value", "trojan_horse"}

# 知名企业词典（无后缀品牌，快速命中）
_KNOWN_ENTERPRISES = {
    # 咨询四大
    "德勤", "普华永道", "毕马威", "安永", "麦肯锡", "贝恩", "波士顿",
    # 互联网/科技大厂
    "阿里巴巴", "腾讯", "字节跳动", "美团", "京东", "拼多多", "小米", "华为",
    "百度", "网易", "携程", "滴滴", "哔哩哔哩", "知乎", "微博", "新浪", "搜狐",
    "蚂蚁", "蚂蚁金服", "钉钉", "飞书", "快手", "小红书",
    # 银行与金融
    "招行", "招商银行", "平安", "平安银行", "平安保险", "中信", "兴业",
    "工商银行", "农业银行", "中国银行", "建设银行", "交通银行", "邮储银行",
    "光大银行", "民生银行", "浦发银行", "华夏银行",
    # 车企
    "理想", "蔚来", "小鹏", "比亚迪", "特斯拉", "吉利", "长城", "广汽",
    "上汽", "一汽", "东风", "奇瑞", "长安", "极氪", "问界", "小米汽车",
    # 能源与央企
    "国家电网", "南方电网", "中石油", "中石化", "中海油", "国家电力",
    "三大运营商", "中国移动", "中国联通", "中国电信",
    # 高科技制造
    "宁德时代", "立讯精密", "海康威视", "海尔", "美的", "格力", "三一重工",
}

# 通用后缀兜底（捕获「xxx银行/xxx集团/xxx科技」这类）
_ENTERPRISE_SUFFIX_RE = re.compile(
    r"([\u4e00-\u9fff]{2,8})"
    r"(银行|集团|科技|汽车|股份|证券|保险|基金|信托|资管"
    r"|电力|能源|地产|航空|铁路|物流|快递|零售|商超|医院|大学"
    r"|会计师事务所|律师事务所|咨询)"
)


def _extract_enterprise(brief: str) -> str:
    """从 brief 中识别企业名。优先词典精确匹配，其次后缀 regex。"""
    if not brief:
        return ""
    for name in _KNOWN_ENTERPRISES:
        if name in brief:
            return name
    m = _ENTERPRISE_SUFFIX_RE.search(brief)
    if m:
        return m.group(0)
    return ""


def strategy_node(state: SalebookState) -> dict:
    """基于知识库数据 + 客户上下文，LLM 输出 Markdown 策略简报"""
    print("\n🧠 策略分析中...")

    # ── 企业画像识别 + 联网搜索（首轮需搜，后续轮复用）──
    enterprise_name = (state.get("enterprise_name") or "").strip()
    enterprise_profile = (state.get("enterprise_profile") or "").strip()
    if not enterprise_profile:
        enterprise_name = _extract_enterprise(state.get("user_brief") or "")
        if enterprise_name:
            print(f"  🏢 识别到企业: {enterprise_name}，联网搜索中...")
            try:
                enterprise_profile = research_enterprise(enterprise_name)
                print(f"  ✓ 企业画像素材: {len(enterprise_profile)} 字符")
            except Exception as e:
                print(f"  ⚠️ 企业搜索失败，降级为纯 LLM 推断: {e}")
                enterprise_profile = ""

    llm_cfg = get_llm_config()
    llm = ChatOpenAI(
        model=llm_cfg["model"],
        api_key=llm_cfg["api_key"],
        base_url=llm_cfg["base_url"],
        temperature=0.3,
        max_tokens=8192,
        # 关闭 Qwen3 系列默认 thinking 模式（避免吃光 token 导致输出截断）
        # DashScope 兼容层不识别 enable_thinking 时会忽略，对 deepseek 无影响
        extra_body={"enable_thinking": False},
    )

    # 拼用户消息（以 SA/BD 自由描述为主，知识库作为上下文）
    user_msg = f"""## 目标模型
{state['target_model']}

## SA/BD 自由描述（可能极短，根据这里主动推断其他字段）
{(state.get('user_brief') or '（未提供，请基于目标模型出一份通用初稿）').strip()}

## 已知客户字段（如上轮推断/纠正过，供你参考）
- 客户当前模型: {state.get('customer_current_model') or '未明（请推断）'}
- 机会类型: {state.get('deal_type') or '未明（请推断）'}
- 核心场景: {state.get('customer_scenario') or '未明（请推断）'}
- 预算敏感度: {state.get('budget_sensitivity') or '未明（请推断 medium）'}
- 决策驱动: {state.get('decision_driver') or '未明（请推断）'}

## 我方模型知识库数据
{(state.get('model_data') or '无本地数据')[:8000]}

## 销售策略框架
{(state.get('sales_strategy') or '无')[:3000]}
"""
    if enterprise_profile:
        user_msg += f"""
## 🏢 企业画像数据（联网搜索）
企业名：{enterprise_name}

{enterprise_profile}

> 请基于以上搜索素材，在策略简报顶部输出「🏢 企业画像」块（营收/业务形态/决策驱动/AI 潜力评分）。
"""
    user_msg += "\n请按规定格式输出：首行 STRATEGY_TYPE，第二行 ---，之后是包含《🧩 当前理解》块的完整 Markdown 简报。**不要反问。**"

    messages = [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        print(f"  ⚠️ LLM 调用失败: {e}")
        return {
            "strategy_type": "unknown",
            "strategy_brief": f"# 策略分析失败\n\n{e}",
        }

    strategy_type, brief = _parse_md(raw)

    print(f"  ✓ 策略类型: {strategy_type}")
    print(f"  ✓ 简报长度: {len(brief)} 字符")

    return {
        "strategy_type": strategy_type,
        "strategy_brief": brief,
        "iterate_done": False,  # 重写后重置，避免跳过 iterate 展示
        "enterprise_name": enterprise_name,
        "enterprise_profile": enterprise_profile,
    }


def _parse_md(text: str) -> tuple[str, str]:
    """从 LLM 输出中提取 strategy_type 和 Markdown 正文。

    优先匹配首行 `STRATEGY_TYPE: xxx`；
    若 LLM 未遵守格式，再用关键词兜底匹配。
    """
    text = text.strip()
    # 去除可能的代码块包裹
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)

    # 尝试匹配首行 STRATEGY_TYPE
    m = re.match(
        r"\s*STRATEGY_TYPE\s*[:：]\s*(tech_advantage|price_value|trojan_horse)\s*\n",
        text,
        re.IGNORECASE,
    )
    if m:
        strategy_type = m.group(1).lower()
        # 去掉首行和可能的 --- 分隔行
        body = text[m.end():].lstrip()
        body = re.sub(r"^-{3,}\s*\n", "", body)
        return strategy_type, body.strip()

    # 兜底：关键词匹配
    lowered = text.lower()
    for stype in VALID_STRATEGIES:
        if stype in lowered:
            return stype, text
    if any(k in text for k in ("技术碾压", "benchmark", "数据说话")):
        return "tech_advantage", text
    if any(k in text for k in ("性价比", "更低成本", "省下")):
        return "price_value", text
    if any(k in text for k in ("田忌赛马", "先做进去", "绑定 API", "绑定API")):
        return "trojan_horse", text

    return "unknown", text
