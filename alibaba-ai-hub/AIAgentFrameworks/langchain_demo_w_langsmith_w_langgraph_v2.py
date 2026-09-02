"""
LangChain + LangSmith + LangGraph 工具链组合示例 V2
=====================================================
本示例展示 LangGraph 的核心价值：构建多步骤工具链工作流

场景：股价查询 → 数据分析 → 生成投资建议

LangGraph 独特能力：
1. 状态传递 - 每个节点的结果自动传递到下一个节点
2. 条件路由 - 根据数据决定走哪条分支（如股价涨跌不同策略）
3. 循环执行 - 可以反复优化直到满足条件
4. 可视化追踪 - LangSmith 可查看完整执行链路

对比普通 LangChain：
- 普通方式：单次调用，无法处理多步骤依赖
- LangGraph：多节点协作，支持复杂业务流程
"""

import os
import json
import re
from typing import TypedDict, Literal, Annotated
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.tools import DuckDuckGoSearchRun # 需要pip install -U ddgs
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# ============================================
# 配置 LangSmith 追踪
# ============================================
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "langchain_stock_analysis_demo"

# LANGSMITH_API_KEY 从环境变量读取，不在启动日志中打印（防泄漏，兼容 pre-commit 密钥扫描）


# ============================================
# 初始化模型
# ============================================
chatLLM = ChatTongyi(model="qwen-plus", streaming=False)


# ============================================
# 定义自定义状态（展示 LangGraph 状态管理）
# ============================================
class StockAnalysisState(TypedDict):
    """
    自定义状态结构
    
    LangGraph 的强大之处：可以在节点间传递任意状态数据
    不只是 messages，还可以有 stock_data、analysis_result 等
    """
    messages: Annotated[list, add_messages]  # 消息历史（自动累加）
    stock_symbol: str                        # 股票代码
    stock_data: dict                         # 查询到的股价数据
    analysis_result: str                     # 分析结果
    recommendation: str                      # 最终投资建议
    risk_level: Literal["high", "medium", "low"]  # 风险等级


# ============================================
# 工具函数：使用 DuckDuckGo 搜索查询实时股价
# ============================================
# 初始化 DuckDuckGo 搜索工具（LangChain 官方封装）
duckduckgo_search = DuckDuckGoSearchRun()

def query_stock_price(symbol: str) -> dict:
    """
    使用 DuckDuckGo 搜索查询股票实时价格
    
    使用 LangChain Community 提供的 DuckDuckGoSearchRun 工具，
    更稳定可靠，无需 API Key。
    
    支持的股票代码：
    - 美股：BABA（阿里巴巴）、AAPL（苹果）、TSLA（特斯拉）等
    - 港股：00700（腾讯）、01810（小米）等
    
    注意：DuckDuckGo 偶尔会有访问限制，如失败会自动使用演示数据
    """
    
    # 股票代码映射
    symbol_mapping = {
        "BABA": {"name": "阿里巴巴", "search_name": "Alibaba BABA stock price today"},
        "AAPL": {"name": "苹果", "search_name": "Apple AAPL stock price today"},
        "MSFT": {"name": "微软", "search_name": "Microsoft MSFT stock price today"},
        "TSLA": {"name": "特斯拉", "search_name": "Tesla TSLA stock price today"},
        "GOOGL": {"name": "谷歌", "search_name": "Alphabet GOOGL stock price today"},
        "AMZN": {"name": "亚马逊", "search_name": "Amazon AMZN stock price today"},
        "TCEHY": {"name": "腾讯控股(ADR)", "search_name": "Tencent TCEHY stock price today"},
        "BIDU": {"name": "百度", "search_name": "Baidu BIDU stock price today"},
        "NIO": {"name": "蔚来", "search_name": "NIO stock price today"},
        "00700": {"name": "腾讯控股", "search_name": "Tencent 0700.HK stock price today"},
        "01810": {"name": "小米集团", "search_name": "Xiaomi 1810.HK stock price today"},
        "09988": {"name": "阿里健康", "search_name": "Alibaba Health 9988.HK stock price today"},
    }
    
    symbol_upper = symbol.upper().strip()
    stock_info = symbol_mapping.get(symbol_upper, {"name": symbol_upper, "search_name": f"{symbol_upper} stock price today"})
    
    try:
        # 使用 LangChain 的 DuckDuckGo 搜索工具
        query = stock_info["search_name"]
        print(f"    🔍 DuckDuckGo 搜索: {query}")
        
        # 执行搜索
        search_result = duckduckgo_search.invoke(query)
        
        # 解析价格信息
        price, change, change_percent = _parse_price_from_text(search_result)
        
        if price > 0:
            return {
                "symbol": symbol_upper,
                "name": stock_info["name"],
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "prev_close": round(price - change, 2),
                "currency": "USD",
                "data_source": "DuckDuckGo Search (实时搜索)",
                "update_time": "实时",
                "search_query": query,
                "raw_result": search_result[:300] if search_result else ""
            }
        else:
            # 如果 DuckDuckGo 没有返回价格，尝试备用方案
            raise Exception("DuckDuckGo 未返回股价数据")
            
    except Exception as e:
        error_msg = f"DuckDuckGo 获取失败: {str(e)}"
        print(f"    ❌ {error_msg}")
        raise Exception(error_msg)


def _parse_price_from_text(text: str) -> tuple:
    """
    从文本中解析股价信息
    
    Returns:
        (price, change, change_percent)
    """
    import re
    
    price = 0.0
    change = 0.0
    change_percent = 0.0
    
    if not text:
        return price, change, change_percent
    
    # 调试：打印原始文本（前500字符）
    print(f"    📝 原始搜索结果: {text[:300]}...")
    
    # 清理文本：移除常见干扰字符
    # 有些搜索结果包含 HTML 标签或特殊格式
    text_clean = re.sub(r'<[^>]+>', '', text)  # 移除 HTML 标签
    text_clean = re.sub(r'\s+', ' ', text_clean)  # 合并多个空格
    
    # 匹配价格模式 - 优先匹配明确的价格格式
    # 查找类似 "42.80" 或 "$42.80" 的价格，通常在 "stock price" 附近
    price_patterns = [
        # 最可靠：在 price 或 stock 附近的数字
        r'(?:price|stock).*?\$?([\d]{1,3}\.[\d]{2})[^\d]',
        r'\$([\d]{1,3}\.[\d]{2})[^\d]',  # $42.80
        r'(?:at|is|was)\s+\$?([\d]{1,3}\.[\d]{2})[^\d]',  # at $42.80
        r'([\d]{1,3}\.[\d]{2})\s*(?:USD|\$)',  # 42.80 USD
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                candidate_price = float(price_str)
                # 过滤不合理的价格（股价通常在 1-5000 之间）
                if 1 <= candidate_price <= 5000:
                    price = candidate_price
                    break
            except:
                continue
    
    # 匹配涨跌幅 - 查找百分比变化
    # 格式如：+1.15%、-0.5%、(1.15%)、up 1.15%
    percent_patterns = [
        r'([+-]?[\d]{1,2}\.[\d]{2})%',  # +1.15% 或 -0.50%
        r'\(([+-]?[\d]{1,2}\.[\d]{2})%\)',  # (1.15%)
        r'(?:up|down|gain|loss|rise|fall|increase|decrease)[\s:]+([\d]{1,2}\.[\d]{2})%',  # up 1.15%
    ]
    
    for pattern in percent_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            try:
                candidate_percent = float(match.group(1))
                # 过滤不合理的涨跌幅（通常在 -50% 到 +50% 之间）
                if -50 <= candidate_percent <= 50:
                    change_percent = candidate_percent
                    break
            except:
                continue
    
    # 计算涨跌额（从价格和涨跌幅计算，更可靠）
    if price > 0 and change_percent != 0:
        change = price * change_percent / 100
    
    # 调试输出
    print(f"    📊 解析结果: price=${price}, change={change:+.2f}, change_percent={change_percent:+.2f}%")
    
    return price, change, change_percent


def _get_demo_data(symbol: str, stock_info: dict, error_msg: str = "") -> dict:
    """
    获取演示数据（当 API 失败时使用）
    """
    demo_data = {
        "BABA": {"price": 85.50, "change": 2.30, "change_percent": 2.76},
        "TCEHY": {"price": 42.80, "change": -0.50, "change_percent": -1.15},
        "00700": {"price": 385.20, "change": 5.40, "change_percent": 1.42},
        "AAPL": {"price": 195.20, "change": 1.20, "change_percent": 0.62},
        "MSFT": {"price": 420.55, "change": 3.45, "change_percent": 0.83},
        "TSLA": {"price": 175.30, "change": -2.10, "change_percent": -1.18},
    }
    
    demo = demo_data.get(symbol, {"price": 100.0, "change": 0.0, "change_percent": 0.0})
    
    return {
        "symbol": symbol,
        "name": stock_info["name"],
        "price": demo["price"],
        "change": demo["change"],
        "change_percent": demo["change_percent"],
        "prev_close": round(demo["price"] - demo["change"], 2),
        "currency": "USD",
        "data_source": "演示数据（DuckDuckGo 暂时不可用）",
        "update_time": "模拟",
        "note": f"搜索错误: {error_msg}" if error_msg else "DuckDuckGo 搜索未返回有效数据"
    }


# ============================================
# LangGraph 节点 1：解析用户输入
# ============================================
def parse_input(state: StockAnalysisState):
    """
    节点1：从用户输入中提取股票代码
    
    LangGraph 价值：专门用一个节点处理输入解析，
    后续节点可以直接使用解析结果
    """
    messages = state["messages"]
    last_message = messages[-1].content
    
    # 简单提取股票代码（实际可用 NLP）
    stock_symbol = "BABA"  # 默认阿里巴巴
    if "腾讯" in last_message or "tencent" in last_message.lower():
        stock_symbol = "TCEHY"
    elif "苹果" in last_message or "apple" in last_message.lower():
        stock_symbol = "AAPL"
    elif "微软" in last_message or "microsoft" in last_message.lower():
        stock_symbol = "MSFT"
    
    print(f"\n[节点1: 输入解析] 识别到股票代码: {stock_symbol}")
    
    return {"stock_symbol": stock_symbol}


# ============================================
# LangGraph 节点 2：查询股价数据
# ============================================
def fetch_stock_data(state: StockAnalysisState):
    """
    节点2：查询股价数据
    
    LangGraph 价值：独立的查询节点，可以：
    - 单独重试（如果查询失败）
    - 缓存结果
    - 替换为不同的数据源
    """
    symbol = state["stock_symbol"]
    
    print(f"\n[节点2: 数据查询] 正在查询 {symbol} 的股价...")
    
    # 调用工具函数
    stock_data = query_stock_price(symbol)
    
    print(f"  → 当前价格: ${stock_data['price']}")
    print(f"  → 涨跌: {stock_data['change']:+.2f} ({stock_data['change_percent']:+.2f}%)")
    
    # 将数据格式化为消息，加入对话
    data_message = SystemMessage(content=f"""
股票数据 [{stock_data['name']} / {symbol}]:
- 当前价格: ${stock_data['price']}
- 涨跌额: ${stock_data['change']:+.2f}
- 涨跌幅: {stock_data['change_percent']:+.2f}%
""")
    
    return {
        "stock_data": stock_data,
        "messages": [data_message]
    }


# ============================================
# LangGraph 节点 3：分析数据
# ============================================
def analyze_data(state: StockAnalysisState):
    """
    节点3：AI 分析股价数据
    
    LangGraph 价值：可以独立调用 LLM 进行分析，
    结果保存在状态中供后续节点使用
    """
    stock_data = state["stock_data"]
    
    print(f"\n[节点3: AI分析] 正在分析 {stock_data['symbol']} 数据...")
    
    # 构建分析提示
    analysis_prompt = f"""
请分析以下股票数据，给出简短的技术分析：

股票: {stock_data['name']} ({stock_data['symbol']})
当前价格: ${stock_data['price']}
涨跌: {stock_data['change']:+.2f} ({stock_data['change_percent']:+.2f}%)

请分析：
1. 短期趋势判断
2. 风险等级（高/中/低）
3. 关键观察点

用2-3句话简要回答，回答时第一句需要热情的称呼用户为爸爸。请用中文回答。
"""
    
    # 调用 LLM
    response = chatLLM.invoke([HumanMessage(content=analysis_prompt)])
    analysis = response.content
    
    # 从分析中提取风险等级（简单规则）
    risk = "medium"
    if "高" in analysis or "high" in analysis.lower():
        risk = "high"
    elif "低" in analysis or "low" in analysis.lower():
        risk = "low"
    
    print(f"  → 风险等级: {risk}")
    print(f"  → 分析摘要: {analysis[:50]}...")
    
    return {
        "analysis_result": analysis,
        "risk_level": risk,
        "messages": [AIMessage(content=f"技术分析: {analysis}")]
    }


# ============================================
# LangGraph 节点 4：生成投资建议（条件分支）
# ============================================
def generate_recommendation(state: StockAnalysisState):
    """
    节点4：根据风险等级生成投资建议
    
    LangGraph 价值：可以根据状态中的 risk_level 
    走不同的分支，生成不同的建议策略
    """
    stock_data = state["stock_data"]
    analysis = state["analysis_result"]
    risk = state["risk_level"]
    
    print(f"\n[节点4: 投资建议] 基于{risk}风险等级生成建议...")
    
    # 根据风险等级调整策略
    if risk == "high":
        strategy = "高风险策略：建议观望，等待更明确的信号。可考虑分批建仓或设置止损点。"
    elif risk == "low":
        strategy = "低风险策略：可考虑逐步建仓，但需关注大盘走势。"
    else:
        strategy = "中等风险策略：建议小仓位试探，密切关注后续走势。"
    
    recommendation = f"""
=== 投资建议 [{stock_data['name']}] ===

【当前数据】
价格: ${stock_data['price']} | 涨跌: {stock_data['change_percent']:+.2f}%

【技术分析】
{analysis}

【操作策略】
{strategy}

【风险提示】
以上分析仅供参考，投资有风险，入市需谨慎。
"""
    
    print(f"  → 建议已生成")
    
    return {
        "recommendation": recommendation,
        "messages": [AIMessage(content=recommendation)]
    }


# ============================================
# 构建 LangGraph 工作流
# ============================================
def build_stock_analysis_graph():
    """
    构建股价分析工作流
    
    工作流图：
    
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  START  │───→│ 解析输入 │───→│ 查询数据 │───→│ AI分析  │
    └─────────┘    └─────────┘    └─────────┘    └────┬────┘
                                                       │
                                              ┌────────▼────────┐
                                              │   生成投资建议   │
                                              └────────┬────────┘
                                                       │
                                                  ┌────┴────┐
                                                  │   END   │
                                                  └─────────┘
    
    LangGraph 优势：
    - 每个节点独立，可单独测试
    - 状态自动传递，无需手动管理
    - 可在任意节点添加条件分支
    """
    
    # 创建工作流
    workflow = StateGraph(StockAnalysisState)
    
    # 添加节点
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("fetch_data", fetch_stock_data)
    workflow.add_node("analyze", analyze_data)
    workflow.add_node("recommend", generate_recommendation)
    
    # 添加边（定义执行顺序）
    workflow.add_edge(START, "parse_input")
    workflow.add_edge("parse_input", "fetch_data")
    workflow.add_edge("fetch_data", "analyze")
    workflow.add_edge("analyze", "recommend")
    workflow.add_edge("recommend", END)
    
    return workflow.compile()


# ============================================
# 主程序
# ============================================
def main():
    """主函数：演示股价分析工作流"""
    
    print("\n" + "=" * 70)
    print("LangGraph 工具链组合示例：股价查询 → 分析 → 投资建议")
    print("=" * 70)
    
    # 构建工作流
    graph = build_stock_analysis_graph()
    
    # 用户输入
    user_input = "你好，分析下腾讯的股价"
    
    print(f"\n用户输入: {user_input}")
    print("\n开始执行工作流...")
    print("-" * 70)
    
    # 执行工作流
    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)],
        "stock_symbol": "",
        "stock_data": {},
        "analysis_result": "",
        "recommendation": "",
        "risk_level": "medium"
    })
    
    print("-" * 70)
    print("\n【最终输出】")
    print(result["recommendation"])
    
    print("\n" + "=" * 70)
    print("工作流执行完成！")
    print("提示：在 LangSmith 控制台可查看完整的节点执行链路")
    print("=" * 70)


if __name__ == "__main__":
    main()
