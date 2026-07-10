# ReAct（Reasoning and Acting）范式

> 最后更新: 2026-07-10
> 领域: AI Engineering / LLM Agent
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: ReAct 是让 LLM 交替进行"推理"（Thought）和"行动"（Action）的范式，确立了 "LLM Agent = 推理 + 工具 + 循环" 的基本骨架，是所有后续 Agent 框架的共同祖先。
**核心价值**: 将 CoT 推理与外部工具使用**交织**产生协同效应——推理指导行动方向，行动为推理提供真实信息，1+1>2。记忆系统是 ReAct 走向生产级 Agent 的最大瓶颈。
**相关产品**: [Agent 定义](agent-def.md), [Agent 框架](agent-frameworks.md), [Agent 记忆系统](agent-memory.md)
<!-- SUMMARY_END -->

## 是什么

ReAct 是一种让 LLM 交替进行"推理"和"行动"的范式——模型不是一次性给出答案，而是在 **Thought（思考）** 和 **Action（行动）** 之间反复循环，每一步行动的 **Observation（观察结果）** 反馈回模型，指导下一步推理。

**核心创新**：将 Chain-of-Thought（CoT）推理与外部工具使用**交织**在一起，产生协同效应（Synergy）。

- **推理帮助行动**：推理轨迹帮助模型归纳、追踪、更新行动计划，处理异常情况
- **行动帮助推理**：行动让模型与外部信息源（知识库、API、环境）交互，获取额外信息来补充推理

> 大白话：ReAct 就像一个人解决问题——先想想怎么办，然后去做，看看结果怎样，再想想下一步怎么办，如此反复。但它有个致命缺陷：记性不好，做得越多忘得越快，因为"脑容量"（上下文窗口）是有限的。

## 核心原理

### 论文信息

| 项目 | 内容 |
|------|------|
| 标题 | ReAct: Synergizing Reasoning and Acting in Language Models |
| 作者 | Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao |
| 机构 | Princeton University + Google Research |
| 首次提交 | 2022-10-06（arXiv:2210.03629v1） |
| 正式发表 | ICLR 2023（Oral），v3 camera ready 2023-03-10 |
| 项目主页 | https://react-lm.github.io/ |
| 代码仓库 | https://github.com/ysymyth/ReAct |

### 典型推理循环

```
Question: 爱因斯坦出生的城市现在属于哪个国家？

Thought 1: 我需要先查爱因斯坦出生在哪座城市
Action 1: Search["Einstein birthplace"]
Observation 1: Albert Einstein was born in Ulm, in the Kingdom of Württemberg.

Thought 2: 乌尔姆在当时的德意志帝国，确认它现在属于哪个国家
Action 2: Search["Ulm current country"]
Observation 2: Ulm is a city in Baden-Württemberg, Germany.

Thought 3: 乌尔姆现在仍然在德国，可以回答了
Final Answer: 爱因斯坦出生的城市乌尔姆现在属于德国。
```

### ReAct Prompting 标准模板

来自 LangChain 内置的 ZERO_SHOT_REACT_DESCRIPTION Agent：

```
Answer the following questions as best you can. You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!
Question: {input}
Thought: {agent_scratchpad}
```

### 与 CoT / Act 的区别

| 维度 | CoT（纯推理） | Act（纯行动） | ReAct（推理+行动） |
|------|-------------|-------------|-------------------|
| 推理方式 | 内部链式思考 → 直接回答 | 无思考，直接调用工具 | 交替思考+行动 |
| 外部信息 | ❌ 不使用 | ✅ 使用 | ✅ 使用 |
| 幻觉风险 | 高（纯靠模型知识） | 低（基于真实数据） | 低（数据+推理验证） |
| 可解释性 | 中 | 低 | 高（推理+行动轨迹全可见） |
| 适应性 | 低（无法纠错） | 中（工具失败时无规划） | 高（可根据观察调整策略） |

**论文实验结果**：
- **HotpotQA**（多跳问答）：ReAct 显著优于纯 CoT，减少幻觉和错误传播
- **Fever**（事实验证）：ReAct 通过 Wikipedia API 交互克服幻觉
- **ALFWorld**（交互决策）：ReAct 以绝对成功率 34% 超越模仿学习+强化学习基线
- **WebShop**（网页购物）：ReAct 以 10% 绝对成功率超越基线，仅需 1-2 个 in-context 示例

### 与 Function Calling / Tool Use 的关系

| 维度 | ReAct（Prompting 驱动） | Function Calling（微调驱动） |
|------|----------------------|---------------------------|
| 触发方式 | prompt 指导模型输出 Thought/Action 文本 | 模型微调后自动识别并输出结构化 JSON |
| 推理过程 | 显式（Thought 可见） | 隐式（模型内部决策） |
| 灵活性 | 高（可自定义推理流程） | 低（由模型厂商定义） |
| 效率 | 低（每步一次 LLM 调用） | 高（一次可输出多个工具调用） |
| 可解释性 | 高 | 低 |

两者不是互斥而是互补——现代 Agent 通常用 Function Calling 实现工具调用层，用 ReAct 思想指导推理架构。

## 关键认知框架

### 洞察 1：ReAct 是 LLM Agent 的"最小可行范式"

- **洞察内容**：ReAct 确立了 "LLM Agent = 推理 + 工具 + 循环" 的基本范式，所有后续框架都是在这个骨架上叠加能力。就像 TCP/IP 之于互联网。
- **为什么重要**：理解 ReAct 就理解了所有 Agent 框架的底层逻辑。无论 LangGraph 的状态图、Plan-and-Execute 的规划器、还是 Claude Code 的 Deep Agent，本质上都是在 ReAct 循环上增加层。
- **可迁移场景**：任何需要 LLM 与外部环境交互的任务——问答、数据分析、编程、自动化工作流、游戏 AI。

### 洞察 2：Memory 是 ReAct 的"最后一公里"

- **洞察内容**：ReAct 解决了"如何思考+如何行动"，但没有解决"如何记住"。Agent 的 for 循环质量取决于每次迭代时模型能获得多少有效上下文。
- **为什么重要**：没有好的记忆系统——10 步之后上下文就满了，工具返回的大量原始数据挤占思考空间，跨对话无法积累经验。这正是现代 Agent 框架重点突破的方向。
- **可迁移场景**：所有需要长链推理、跨会话经验积累的 Agent 应用。

### 洞察 3：效率 vs 灵活性 vs 全局性的三角权衡

- **洞察内容**：ReAct 之后涌现的变体（ReWOO / Plan-and-Execute / LLMCompiler）本质是在三个维度间做权衡。
- **为什么重要**：没有银弹，只有针对具体场景的最优解——开放式任务选 ReAct（动态适应），结构化任务选 ReWOO/P&E（高效），需要并行选 LLMCompiler。
- **可迁移场景**：Agent 架构选型、系统设计中的 trade-off 决策。

### 洞察 4：底层灵感来自人类认知与控制论

- **洞察内容**：ReAct 模拟了人类解决复杂问题时在"内心独白"和"外部交互"之间反复切换的认知模式。从控制论角度看，它将 LLM 从开环系统（输入→一路生成到底）变为闭环系统（每步输出被环境校验，偏差能被纠正）。
- **为什么重要**：这解释了为什么 ReAct 有效——闭环控制是工程系统的基本原理，将其应用于 LLM 生成过程是自然的演进。
- **可迁移场景**：任何需要将反馈控制引入生成式 AI 系统的场景。

## 各厂商实现对照

### 采用 ReAct 的主流框架/产品

| 框架/产品 | 与 ReAct 的关系 |
|-----------|---------------|
| LangChain | 内置 ZERO_SHOT_REACT_DESCRIPTION Agent |
| LangGraph | 在 ReAct 上引入状态图，解决循环控制 |
| LlamaIndex | 预配置 ReAct Agent 模块 |
| AutoGPT / BabyAGI | ReAct 循环扩展为自主任务执行 |
| Claude Code / Qoder | Deep Agent——ReAct + 规划 + 子Agent + 文件系统 |
| OpenAI Codex | Agent 平台使用 ReAct 式 reasoning + tool use |
| Reflexion | ReAct + 反思，Agent 从错误中学习 |
| IBM watsonx | 支持 ReAct agent 构建 |

### 在现代 Agent 架构中的层次位置

```
┌─────────────────────────────────────────────────────────────┐
│  生产级 Deep Agent（Claude Code / Qoder / Deep Agents）      │
│  = ReAct + 规划 + 子Agent + 文件系统 + Memory                │
├─────────────────────────────────────────────────────────────┤
│  增强型 Agent（Plan-and-Execute / ReWOO / LLMCompiler）      │
│  = ReAct + 全局规划 + 并行执行                                │
├─────────────────────────────────────────────────────────────┤
│  基础 ReAct Agent                                            │
│  = LLM + Thought-Action-Observation 循环 + 工具              │
├─────────────────────────────────────────────────────────────┤
│  Function Calling / Tool Use（模型原生工具调用能力）           │
├─────────────────────────────────────────────────────────────┤
│  Chain-of-Thought（纯推理）                                  │
└─────────────────────────────────────────────────────────────┘
```

> 详细产品分析见各厂商对应文档

## ReAct 与 Memory 的关系

### 原始 ReAct 的"记忆"

ReAct 的"记忆"就是 **agent_scratchpad**——上下文窗口中累积的 Thought/Action/Observation 文本。**工作记忆 = 上下文窗口**，没有长期记忆、没有跨对话记忆、没有学习能力。

### ReAct 的记忆问题

| 问题 | 描述 |
|------|------|
| 上下文膨胀 | Observation 返回大量文本，快速占满窗口 |
| 信息丢失 | 窗口满后截断，早期关键信息可能丢弃 |
| 无持久记忆 | 对话结束一切消失 |
| 无学习能力 | 无法从过去成功/失败中提取经验 |

### 现代 Agent 的记忆扩展

| 记忆类型 | 机制 | 实现示例 |
|---------|------|---------|
| 工作记忆 | 上下文窗口 + Scratchpad | ReAct 原始设计 |
| 短期记忆 | 对话内摘要/压缩 | LangChain ConversationSummaryMemory |
| 长期记忆 | 向量数据库 + 检索 | Mem0、VectorStoreRetrieverMemory |
| 跨对话记忆 | 用户画像 + 偏好存储 | ChatGPT Memory Dreaming V3 |
| 元记忆 | Agent 自主管理记忆 | Reflexion self-reflection |

LangChain 在 2026 年提出 "Context Engineering for Agents"，核心是用 Scratchpad 机制主动管理上下文——不是被动堆积 Observation，而是主动选择、压缩、摘要。

## 局限性与后续演进

### ReAct 的局限性

| 局限性 | 描述 |
|--------|------|
| 效率低 | 每次工具调用都需一次完整 LLM 调用，高延迟+高成本+高 token |
| 缺乏全局规划 | 每次只规划下一步而非整个任务，可能走死胡同或选次优路径 |
| 上下文膨胀 | Thought/Action/Observation 循环累积，工具返回数据占满上下文 |
| 错误累积 | 长链循环中小错误逐步放大，无内建回溯机制 |

### 后续演进

| 演进方案 | 核心改进 | 解决什么 |
|---------|---------|---------|
| ReWOO（Reasoning Without Observation） | 一次性生成完整计划，用变量引用（#E1, #E2） | 效率（减少 LLM 调用） |
| Plan-and-Execute | 分离 Planner 和 Executor，先规划完整步骤再执行 | 全局规划 + 效率 |
| LLMCompiler | 计划表达为 DAG，支持并行执行（3.6× 加速） | 延迟 |
| Reflexion | 加入"反思"步骤，从失败中学习 | 错误累积 |
| Deep Agents | 叠加规划工具、子Agent、文件系统、Memory | 长任务+深度任务 |

**ReWOO vs ReAct**：ReWOO Token 消耗低、可并行，但计划是静态的、鲁棒性差；ReAct 动态适应性强但效率低。选择取决于任务是开放式（选 ReAct）还是结构化（选 ReWOO）。

## 常见误区

| 误区 | 事实 |
|------|------|
| ReAct 和 Function Calling 是互斥的 | 两者互补——现代 Agent 用 FC 做工具调用层，用 ReAct 思想指导推理架构 |
| ReAct 就是 LangChain 的 ReAct Agent | ReAct 是通用范式，LangChain 只是其中一个实现 |
| ReAct 已经过时，被 Plan-and-Execute 取代 | ReAct 是基础骨架，P&E 是在其上叠加全局规划能力，并非替代 |
| ReAct Agent 不需要 Memory | Memory 恰恰是 ReAct 走向生产级的最大瓶颈，没有好的记忆系统 Agent 走不远 |

## 最佳实践

### 可迁移场景

- **开放式探索任务**（研究调查、复杂问答）→ 选 ReAct，动态适应能力强
- **结构化批处理任务**（数据清洗、报告生成）→ 选 ReWOO / Plan-and-Execute，效率高
- **需要并行的任务**（多源数据查询）→ 选 LLMCompiler，DAG 并行执行
- **需要经验积累的任务**（反复试错型）→ ReAct + Reflexion 反思机制
- **长链深度任务**（编程、复杂工作流）→ Deep Agent = ReAct + 规划 + 子Agent + Memory

## 参考资料

- [arXiv:2210.03629 - ReAct 原始论文](https://arxiv.org/abs/2210.03629)
- [react-lm.github.io - 项目主页](https://react-lm.github.io/)
- [ICLR 2023 Session](https://iclr.cc/virtual/2023/session/14954)
- [IBM - What is a ReAct Agent?](https://www.ibm.com/think/topics/react-agent)
- [LangChain - Plan-and-Execute Agents](https://www.langchain.com/blog/planning-agents)
- [SPR - Comparing ReAct and ReWOO](https://spr.com/comparing-react-and-rewoo-two-frameworks-for-building-ai-agents-in-generative-ai/)
- [LangChain - Context Engineering for Agents](https://www.langchain.com/blog/context-engineering-for-agents)
- [Mem0 - Working Memory for AI Agents](https://mem0.ai/blog/working-memory-for-ai-agents)
- [Dev.to - ReAct vs Plan-and-Execute](https://dev.to/jamesli/react-vs-plan-and-execute-a-practical-comparison-of-llm-agent-patterns-4gh9)
- [Reddit r/LangChain - Tool Calling vs ReAct](https://www.reddit.com/r/LangChain/comments/1mozucx/tool_calling_agent_vs_react_agent/)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-07-10 | 创建：从 inbox/ai-knowledge-by-qoder-ai-native-agent-20260710.md 提炼 ReAct 概念洞察 |
