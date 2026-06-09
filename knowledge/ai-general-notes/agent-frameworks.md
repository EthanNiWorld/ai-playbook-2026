# Agent 框架（LangChain 生态）

> 最后更新: 2026-06-09
> 领域: AI Engineering
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: LangChain 生态提供三层递进的 Agent 开发架构——LangChain（构建工具包）→ LangGraph（运行时控制层）→ Deep Agents（高阶 Harness），对应从原型到生产到深度任务的复杂度阶梯
**核心价值**: 理解三层架构的差异和选型边界，避免过度工程或能力不足；Deep Agents 的设计哲学直接源自 Claude Code，是开源世界对闭源 Deep Agent 产品的通用化抽象
**相关产品**: [Harness](harness.md), [Agent 定义](agent-def.md), [Claude Code](../anthropic/ai-coding/claude-code.md), [Qoder](../alibaba-cloud/ai-coding/qoder.md)
<!-- SUMMARY_END -->

## 是什么

Agent 框架是帮助开发者构建 AI Agent 的软件工具链。LangChain Inc. 是目前最主流的 Agent 框架提供商，其产品矩阵构成**三层递进架构**：

| 产品 | 定位 | 核心抽象 | 解决的问题 |
|------|------|---------|-----------|
| **LangChain** | Agent 构建工具包（Building Blocks） | Model + Tools + Agent Loop | 快速搭建原型 Agent |
| **LangGraph** | Agent 运行时/控制层（Runtime） | State + Nodes + Edges（有向图） | 生产环境可靠、可控、可恢复 |
| **Deep Agents** | Agent Harness（高阶脚手架） | Planning + Sub-agents + FileSystem + Memory | 处理长时间、多步骤、开放式复杂任务 |

**层级关系：LangChain → LangGraph → Deep Agents（由底向上，逐层叠加）**

```
┌──────────────────────────────────────────────────────┐
│  Deep Agents  （Harness：规划 + 子Agent + 文件系统）    │
├──────────────────────────────────────────────────────┤
│  LangGraph    （Runtime：状态 + 图 + 持久化 + 人机协同） │
├──────────────────────────────────────────────────────┤
│  LangChain    （Building Blocks：模型 + 工具 + Agent循环）│
└──────────────────────────────────────────────────────┘
```

> 三者不是竞品，而是同一团队面向不同复杂度层级的递进方案。

## 核心原理

### LangChain —— 降低门槛（Building Blocks 层）

- **背景**：2023 年 LLM Agent 兴起，核心问题是"怎么把 LLM 和工具连起来"
- **方案**：标准化接口（Model I/O、Tool Calling、Chain），5 行代码跑一个 Agent
- **v1 现状**：`create_agent` 是标准入口，底层已构建在 LangGraph 之上
- **设计权衡**：追求易用性，牺牲控制粒度。适合简单场景，复杂流程控制力不从心

### LangGraph —— 生产级控制（Runtime 层）

- **背景**：原型 Agent 上生产时，需要持久化状态、精确流程控制、人机协同审批、断点续跑
- **方案**：用**有向图**建模 Agent 工作流
  - **Nodes** = 处理步骤（Agent 函数）
  - **Edges** = 流转条件（路由逻辑）
  - **State** = 共享状态（跨节点传递）
- **设计思想**：从 Petri Net / 状态机演化，天然适合表达多阶段、有分支、需恢复的复杂流程
- **关键能力**：持久化/checkpoint、流式输出、Human-in-the-Loop、节点级重试和调试
- 来源：[Building LangGraph from first principles](https://www.langchain.com/blog/building-langgraph)

### Deep Agents —— 深度任务开箱即用（Harness 层）

- **背景**：Harrison Chase（LangChain CEO）明确表示灵感来自 **Claude Code** 和 **Deep Research** 类产品
- **核心洞察**：浅层 Agent（LLM + 工具循环）无法处理复杂任务；真正"深"的 Agent 共享四个特征：

| 要素 | 说明 | Claude Code 中的实现 |
|------|------|---------------------|
| **详细系统提示词** | 长 prompt + 工具使用指南 + few-shot 示例 | recreated system prompt（数千 token） |
| **规划工具** | Todo List，本质是 no-op，但让 Agent 保持任务轨道 | TodoWrite 工具 |
| **子 Agent 机制** | 拆分任务，每个子 Agent 专注深挖一个子目标 | Task 工具（spawn sub-agent） |
| **文件系统** | Agent 的"外部记忆"，存储中间结果和笔记 | 文件读写、代码编辑 |

- **方案**：将上述四要素抽象为通用开源框架，可构建任意领域的深度 Agent
- 来源：[Deep Agents 官方博客](https://www.langchain.com/blog/deep-agents)、[Deep Agents 产品页](https://www.langchain.com/deep-agents)

### 与闭源 Deep Agent 产品的关系

Deep Agents 框架直接受 Claude Code 启发。**Claude Code、Qoder 本质上都是 Deep Agent 的闭源实现**——都有规划工具、子 Agent、文件系统访问、复杂系统提示词。

| 对比维度 | Claude Code / Qoder | Deep Agents 框架 |
|---------|--------------------|--------------------|
| 开源/闭源 | 闭源垂直产品 | 开源通用框架 |
| 专注领域 | AI 编程 | 任意领域可定制 |
| 模型绑定 | 绑定特定模型（Claude / Qwen） | 模型无关 |
| Harness 成熟度 | 高度打磨（产品级） | 社区驱动（快速迭代） |

## 关键选型维度

| 维度 | LangChain | LangGraph | Deep Agents | 怎么选 |
|------|-----------|-----------|-------------|--------|
| 任务复杂度 | 单轮工具调用 | 多阶段有状态流程 | 开放式长周期任务 | 按任务深度递增 |
| 典型场景 | 客服问答、CRM 查询 | 退款审批、事件响应 | 市场研究、跨文件编程 | 见下方决策树 |
| 流程控制 | 简单循环 | 显式图（分支/重试/HITL） | 自主规划 + 子 Agent 委托 | 越复杂越需要上层 |
| 上手成本 | 最低 | 中（需设计状态图） | 最低（开箱即用）但理解成本中 | 先原型再升级 |
| 调试粒度 | 粗 | 节点级精确调试 | 子 Agent 级 | 需要精确排错选 LangGraph |

### 选型决策树

```
你的任务是什么？
│
├─ 简单工具调用（问答、CRM 查询、单轮对话）
│  → LangChain
│
├─ 多阶段流程 + 需要审批/重试/断点恢复/精确调试
│  → LangGraph
│
└─ 开放式深度任务（研究、编程、报告生成、多 Agent 协同）
   → Deep Agents
```

### 常见错误

- **过早跳到 LangGraph**：如果应用只是"工具调用聊天机器人"，LangChain 就够了。LangGraph 增加了工作流设计开销
- **对简单任务用 Deep Agents**：Deep Agents 适合真正复杂、开放的任务。对确定性窄流程是杀鸡用牛刀
- **不理解底层就用 Deep Agents**：不理解 tools 和 state 概念，会误用框架

## 最佳实践

### 推荐学习路径

1. **LangChain 基础**：Model、Messages、Tools、Agent Loop、Middleware
2. **LangGraph 概念**：State、Nodes、Edges、Persistence、Memory、Streaming
3. **Deep Agents 高阶**：Planning、Sub-agents、FileSystems、Skills、Memory

### 推荐工程路径

1. 用 LangChain **快速验证**想法
2. 热路径/生产工作流**迁移到 LangGraph**（获得控制和可靠性）
3. 仅在**真正复杂的开放任务**上使用 Deep Agents

### 可迁移场景

- **企业 Agent 平台建设**：用三层架构思维设计内部 Agent 平台——简单场景用轻量 SDK，复杂流程用工作流引擎，研究型任务用 Harness 框架
- **Agent 产品评估**：评估任何 Agent 产品时，看它在三层架构中处于哪一层——能看出产品的真实能力边界

## 常见误区

| 误区 | 事实 |
|------|------|
| "LangChain、LangGraph、Deep Agents 是三个竞品" | 同一团队的三层递进产品，互相叠加而非替代 |
| "越复杂越好，直接用 Deep Agents" | 过度工程是真实成本，简单任务用 LangChain 更高效 |
| "Deep Agents = Claude Code 开源版" | Deep Agents 是从 Claude Code 抽象的通用框架，Claude Code 是高度打磨的垂直产品，成熟度不同 |
| "Agent 框架不重要，模型才重要" | 同一模型接不同 Harness/框架，产品体验可差一个数量级（参见 [Harness](harness.md)） |

## 为什么是三层（商业逻辑）

LangChain 三层架构背后是经典的**开源漏斗 + 平台锁定**商业飞轮：

| 层级 | 产品 | 商业角色 |
|------|------|---------|
| 入口 | LangChain（开源工具包） | 吸引开发者进入生态 |
| 绑定 | LangGraph（生产运行时） | 开发者上生产时深度绑定 |
| 变现 | LangSmith（可观测性平台） | 监控、调试、评估的付费产品 |
| 锁定 | Deep Agents（高阶 Harness） | 锁定复杂场景，强化生态依赖 |

同时这也是 Agent 工程自然演化的缩影：2023 年单轮工具调用 → 2024-2025 年有状态工作流 → 2025-2026 年自主规划 + 多 Agent 协同。

## 参考资料

- [LangChain 官方博客 - Deep Agents](https://www.langchain.com/blog/deep-agents)（2025-07，Harrison Chase）
- [LangChain 官方博客 - Building LangGraph from first principles](https://www.langchain.com/blog/building-langgraph)
- [Deep Agents 产品页](https://www.langchain.com/deep-agents)
- [Deep Agents 官方文档](https://docs.langchain.com/oss/python/deepagents/overview)
- [State of Agent Engineering 2026](https://www.langchain.com/state-of-agent-engineering)
- [Deep Agents v0.6 发布](https://www.langchain.com/blog/deep-agents-0-6)
- [LinkedIn: LangChain vs LangGraph vs Deep Agents](https://www.linkedin.com/pulse/langchain-vs-langgraph-deepagents-rachit-lohani-byibc)（独立对比分析）

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-09 | 初始创建：LangChain / LangGraph / Deep Agents 三层递进架构、选型决策树、与闭源 Deep Agent 产品（Claude Code / Qoder）的关系、商业飞轮分析。来源：inbox/ai-knowledge-by-qoder-ai-native-agent-20260609.md |
