"""
LangChain + LangSmith + LangGraph 集成示例
==========================================
本示例展示如何将 LangGraph 的工作流集成到 LangChain 应用中，
同时使用 LangSmith 进行调用追踪和监控。

主要组件：
- LangChain: 大模型调用和工具集成
- LangSmith: 调用链路追踪和监控
- LangGraph: 构建复杂的 agent 工作流
"""

import os
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from typing import Literal

# ============================================
# 配置 LangSmith 追踪
# ============================================
# 确保环境变量中已设置 LANGSMITH_API_KEY
# export LANGSMITH_API_KEY="your-api-key"

os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "langchain_langgraph_demo"

# LANGSMITH_API_KEY 从环境变量读取，不在启动日志中打印（防泄漏，兼容 pre-commit 密钥扫描）


# ============================================
# 初始化通义千问模型
# ============================================
chatLLM = ChatTongyi(
    model="qwen-plus",
    streaming=False,
)


# ============================================
# 定义 LangGraph 节点函数
# ============================================

def call_model(state: MessagesState):
    """
    LangGraph 节点：调用 LLM 生成回复
    
    Args:
        state: 包含消息历史的状态对象
        
    Returns:
        包含 AI 回复的消息更新
    """
    # 从状态中获取消息历史
    messages = state["messages"]
    
    # 调用通义千问模型
    response = chatLLM.invoke(messages)
    
    # 返回更新后的消息列表
    return {"messages": [response]}


def should_continue(state: MessagesState) -> Literal["continue", "end"]:
    """
    LangGraph 条件边：决定工作流是否继续
    
    可以根据实际需求添加逻辑，例如：
    - 检查是否需要调用工具
    - 检查对话轮数是否超过限制
    - 检查是否达到终止条件
    
    Args:
        state: 当前状态
        
    Returns:
        "continue" 继续执行 或 "end" 结束工作流
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # 示例：如果最后一条消息包含特定关键词，结束对话
    if isinstance(last_message, AIMessage):
        content = last_message.content.lower()
        if "再见" in content or "goodbye" in content:
            return "end"
    
    # 默认继续（这里简化为直接结束，实际可扩展）
    return "end"


# ============================================
# 构建 LangGraph 工作流
# ============================================

def build_graph():
    """
    构建 LangGraph 工作流
    
    工作流结构：
    START -> call_model -> END
    
    可扩展为更复杂的结构，例如：
    START -> call_model -> [工具调用] -> call_model -> END
    """
    # 创建状态图
    workflow = StateGraph(MessagesState)
    
    # 添加节点
    workflow.add_node("call_model", call_model)
    
    # 添加边
    workflow.add_edge(START, "call_model")
    
    # 添加条件边（可选）
    # workflow.add_conditional_edges(
    #     "call_model",
    #     should_continue,
    #     {
    #         "continue": "call_model",  # 继续调用模型
    #         "end": END                 # 结束工作流
    #     }
    # )
    
    # 直接连接到结束
    workflow.add_edge("call_model", END)
    
    # 编译图
    return workflow.compile()


# ============================================
# 主程序：运行集成示例
# ============================================

def main():
    """主函数：演示 LangChain + LangSmith + LangGraph 集成"""
    
    print("\n" + "=" * 60)
    print("LangChain + LangSmith + LangGraph 集成示例")
    print("=" * 60)
    
    # 构建工作流
    graph = build_graph()
    
    # 准备输入消息
    messages = [
        SystemMessage(content="You are a helpful assistant"),
        HumanMessage(content="你好，分析下腾讯的股价")
    ]
    
    print(f"\n用户输入: {messages[-1].content}")
    print("\n正在调用 LangGraph 工作流...")
    
    # 执行工作流
    # LangSmith 会自动追踪这次调用
    result = graph.invoke({"messages": messages})
    
    # 获取最终回复
    final_messages = result["messages"]
    ai_response = final_messages[-1].content
    
    print(f"\nAI 回复:\n{ai_response}")
    print("\n" + "=" * 60)
    print("调用完成！请在 LangSmith 控制台查看追踪详情")
    print("=" * 60)


# ============================================
# 进阶：带工具调用的 LangGraph 工作流
# ============================================

def build_graph_with_tools():
    """
    构建支持工具调用的复杂工作流
    
    工作流结构：
    START -> call_model -> [判断是否需要工具] 
          -> [需要] -> call_tool -> call_model -> END
          -> [不需要] -> END
    """
    from datetime import datetime
    
    # 定义工具函数
    def get_current_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 工具注册
    tools = {
        "get_current_time": get_current_time
    }
    
    def call_model_with_tools(state: MessagesState):
        """带工具调用的模型节点"""
        messages = state["messages"]
        
        # 绑定工具到模型
        llm_with_tools = chatLLM.bind(
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "description": "获取当前时间",
                        "parameters": {}
                    }
                }
            ]
        )
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    def call_tool(state: MessagesState):
        """工具执行节点"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 检查是否有工具调用请求
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            tool_call = last_message.tool_calls[0]
            tool_name = tool_call["name"]
            
            if tool_name in tools:
                result = tools[tool_name]()
                return {"messages": [{"role": "tool", "content": result, "tool_call_id": tool_call["id"]}]}
        
        return {"messages": []}
    
    # 构建图
    workflow = StateGraph(MessagesState)
    workflow.add_node("call_model", call_model_with_tools)
    workflow.add_node("call_tool", call_tool)
    
    workflow.add_edge(START, "call_model")
    
    # 条件边：判断是否需要调用工具
    def route_tools(state: MessagesState):
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "call_tool"
        return END
    
    workflow.add_conditional_edges("call_model", route_tools, {
        "call_tool": "call_tool",
        END: END
    })
    workflow.add_edge("call_tool", "call_model")
    
    return workflow.compile()


def demo_with_tools():
    """演示带工具调用的工作流"""
    print("\n" + "=" * 60)
    print("带工具调用的 LangGraph 示例")
    print("=" * 60)
    
    graph = build_graph_with_tools()
    
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="现在几点了？")
    ]
    
    print(f"\n用户输入: {messages[-1].content}")
    
    result = graph.invoke({"messages": messages})
    
    final_response = result["messages"][-1].content
    print(f"\nAI 回复: {final_response}")
    print("=" * 60)


if __name__ == "__main__":
    # 运行基础示例
    main()
    
    # 运行带工具调用的示例（取消注释）
    # demo_with_tools()
