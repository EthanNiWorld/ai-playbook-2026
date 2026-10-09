# 主流 Agent 框架调研：LangChain / LangGraph、LlamaIndex、AutoGen、CrewAI

> 最后更新: 2026-10-09
> 领域: AI Engineering / Agent Frameworks
> 状态: Published
> 调研方式: 联网核实（官方博客 / arXiv / GitHub / 官方新闻稿），非仅凭知识库

<!-- SUMMARY_START -->
**一句话说明**: 五个主流 Agent 框架分别押注五种不同的第一性抽象——LangChain（组合式链）、LangGraph（低层状态图）、LlamaIndex（数据框架）、AutoGen（多智能体对话）、CrewAI（角色扮演团队），各自的诞生时间与创始人背景精确对应了行业认知的三个阶段
**核心价值**: 框架选型的本质是抽象选型；理解每个框架"为什么长成这样"，比记住 API 更能指导选型与预判其演进方向
**相关产品**: [Agent 框架（LangChain 生态三层架构）](../../knowledge/ai-general-notes/agent-frameworks.md), [LangGraph 工具链 Demo V2](langchain_demo_w_langsmith_w_langgraph_v2.py)
<!-- SUMMARY_END -->

## 核心事实总览

| 框架 | 首次发布 | 创始团队 / 所属 | 出身背景 | 核心抽象 | 一句话理念 |
|------|---------|----------------|---------|---------|-----------|
| **LangChain** | 2022 年 10 月 | Harrison Chase（单人 side project） | Robust Intelligence 的 ML 工程师 | Chain（链式组合） | 用可组合的标准件把 LLM 嵌入应用 |
| **LlamaIndex** | 2022 年 11 月（原名 GPT Index） | Jerry Liu + Simon Suo（均前 Uber ML 工程师） | 周末项目起家 | Index（索引结构） | LLM 应用的数据框架：让模型用好私有数据 |
| **AutoGen** | 2023 年 8 月 | 微软研究院（Chi Wang、Qingyun Wu 等） | 学术研究（arXiv 论文） | Conversable Agent（可对话代理） | 用多智能体对话编程替代静态 pipeline |
| **CrewAI** | 2023 年 11 月 | João Moura（巴西裔工程师） | 独立开发者开源项目 | Crew（角色团队） | 用人类组织的角色分工心智模型编排 Agent |
| **LangGraph** | 2024 年 1 月 | LangChain Inc.（Harrison Chase 团队） | 商业公司的自我纠偏 | State Graph（状态有向图） | 只做可靠底层原语，不做高层预设 |

> 来源：[LangChain About](https://www.langchain.com/about) · [Wikipedia: LangChain](https://en.wikipedia.org/wiki/LangChain) · [LlamaIndex Turns 1 官方博客](https://www.llamaindex.ai/blog/llamaindex-turns-1-f69dcdd45fe3) · [arXiv:2308.08155](https://arxiv.org/abs/2308.08155) · [crewAI GitHub](https://github.com/crewaiinc/crewai) · [Deep Agents vs LangChain vs LangGraph（LangChain 官方博客）](https://www.langchain.com/blog/deep-agents-vs-langchain-vs-langgraph)

## 时间线：框架代际 = 行业认知阶段

```
2022-10  LangChain 发布          ┐ ChatGPT 发布（2022-11-30）前夜
2022-11  GPT Index (LlamaIndex)  ┘ 「LLM + 数据怎么接进应用」阶段
─────────────────────────────────────────────────────────────
2023-08  AutoGen 发布            ┐ GPT-4 / Function Calling 之后
2023-11  CrewAI 发布             ┘ 「多 Agent 协作怎么做」阶段
─────────────────────────────────────────────────────────────
2024-01  LangGraph 发布          「Agent 上生产的可靠性与可控性」阶段
─────────────────────────────────────────────────────────────
2025-03  OpenAI 采纳 MCP         ┐ A2A 协议发布（04）/ 捐赠 Linux Foundation（06）
2025-07  Deep Agents 发布        ┘ 「Agent 怎么变深 + 怎么互联」阶段
```

**代际洞察**：每个框架的发布时间点，恰好是行业对其前一代问题的回答。2022 年的核心问题是"LLM 怎么嵌入应用"（LangChain/LlamaIndex）；2023 年的核心问题变成"单个 Agent 不够，怎么让多个 Agent 协作"（AutoGen/CrewAI）；2024 年的核心问题又变成"原型跑通了，怎么在生产环境可控、可恢复、可审计"（LangGraph）；2025 年的核心问题则是"Agent 怎么变深、怎么互联"——在长周期开放式任务上真正完成工作，并与工具及其他 Agent 标准化通信，详见下节。

### 延伸：2025 年的核心问题——「Agent 变深 + 互联」

2024 年的图编排解决了"流程可控"，但骨架里跑的仍是单层 LLM 循环——任务一长，失败模式从"流程走错"（LangGraph 已解决）变成"上下文崩坏"（新瓶颈）：中间产物淹没上下文、注意力稀释、Agent 丢失先前工作状态。2025 年行业给出三层答案：

| 层 | 答案 | 关键时间点 | 说明 |
|----|------|-----------|------|
| 产品形态层 | **Harness / Deep Agents** | 2025-07 开源（LangChain） | 四要素：详细系统提示词 + 规划工具 + 子 Agent + 文件系统外部记忆；灵感直接来自 Claude Code / Deep Research，范式详解见 [agent-frameworks.md](../../knowledge/ai-general-notes/agent-frameworks.md) |
| 机制层 | **Context Engineering 取代 Prompt Engineering** | 术语 2025 年中经 Karpathy 带火；Anthropic 官方博客 2025-09 | 长任务失败的微观机制是上下文管理失败；解法三件套：压缩（compaction）、结构化笔记、子 Agent 上下文隔离。来源：[Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| 生态层 | **协议标准化** | MCP：OpenAI 2025-03 官方采纳、Google 2025-04 跟进；A2A：Google 2025-04 发布、2025-06-23 捐赠 Linux Foundation | MCP（Anthropic 2024-11 开源）一年内成为工具接入事实标准，终结框架各自定义接口的 N×M 集成碎片化；A2A 补齐 Agent 间互操作（100+ 厂商支持）。来源：[Wikipedia: MCP](https://en.wikipedia.org/wiki/Model_Context_Protocol)、[Google Developers Blog](https://developers.googleblog.com/en/google-cloud-donates-a2a-to-linux-foundation/) |

**能力侧前提**：METR 实测模型任务完成时间线约每 7 个月翻倍（[长程任务](../../knowledge/ai-general-notes/long-horizon-task.md)）——模型能力追上长任务需求，Harness 层投资才有回报；模型与框架是相互追赶的关系，2024 年框架跑在模型前面，2025 年模型追了上来。

**2026 年走向**：问题继续演进为"怎么可靠地运营深 Agent"——Agent Engineering 成学科（评估 / 可观测 / 回归测试）、Harness 成企业战略资产（[Harness](../../knowledge/ai-general-notes/harness.md)）、模型自我进化（[模型自我进化](../../knowledge/ai-general-notes/agent-self-evolution.md)）。

## 逐框架详解

### 1. LangChain —— LLM 应用的"标准工具箱"（2022-10）

**发布时间**：2022 年 10 月。GitHub 仓库创建于 2022-10-17，v0.0.1 同期发布至 PyPI。来源：[Wikipedia](https://en.wikipedia.org/wiki/LangChain)、[LangChain About](https://www.langchain.com/about)（"LangChain started as Harrison Chase's side project in late 2022"）。

**创始团队**：Harrison Chase 一人以 side project 起家，当时他正任职于机器学习安全公司 Robust Intelligence（2019.10–2023.01，见其 [LinkedIn](https://www.linkedin.com/in/harrison-chase-961287118)）。2023 年初公司化为 LangChain Inc.，Chase 任 CEO 至今。

**核心设计理念**：**组合性（composability）**。Chase 观察到当时所有 LLM 应用都在重复拼装同样的零件——提示词模板、模型调用、输出解析、少量工具——于是把这些零件标准化为统一接口，用"链"（Chain）串联：`Prompt → LLM → Output Parser` 可以像 Unix 管道一样自由组合。2023 年 Function Calling 出现后，重心从 Chain 转向 Agent（模型 + 工具循环）；v0.1（2024-01）稳定 API；v1.0（2025 年起）进一步收敛为标准 Agent 抽象（`create_agent`），底层完全构建在 LangGraph 之上。

**之所以然**：发布于 ChatGPT 前 6 周——彼时行业对 LLM 的想象还停留在"高级文本处理管道"，所以第一性抽象是"链"而非"Agent"。Chase 本人并非研究员，而是应用层工程师，这决定了 LangChain 的产品直觉：先让开发者 5 行代码跑通，抽象深度让位于上手速度。这个选择后来带来双刃剑效应：LangChain 以最快速度成为事实标准（GitHub 星标长期第一），但早期版本因封装过深、抽象泄漏广受批评——这正是 LangGraph 诞生的直接原因。

### 2. LangGraph —— 生产级 Agent 的"低层运行时"（2024-01）

**发布时间**：2024 年 1 月，与 LangChain v0.1 同期发布。来源：[LangChain 官方博客](https://www.langchain.com/blog/deep-agents-vs-langchain-vs-langgraph)（"we introduced LangGraph in January 2024"）。

**创始团队**：LangChain Inc. 同一团队（Harrison Chase 主导）。

**核心设计理念**：**低层编排（low-level orchestration）**。官方定位刻意强调"very low-level"（[docs.langchain.com](https://docs.langchain.com/oss/python/langgraph/overview)）：不替开发者预设任何高层抽象，只提供四个可靠原语——**State**（跨步骤共享状态）、**Nodes**（计算步骤）、**Edges**（含条件路由）、**Durable Execution**（持久化 checkpoint，进程崩溃可断点续跑），外加 Human-in-the-Loop 中断与流式输出。来源：[LangGraph 官网](https://www.langchain.com/langgraph)、[GitHub](https://github.com/langchain-ai/langgraph)。

**之所以然**：这是 LangChain 团队对自身早期批评的系统性纠偏。Chain 抽象天然只能表达线性流程，无法表达 Agent 生产的三大刚需——循环（重试直到成功）、分支（按结果路由）、恢复（状态持久化）；而有向图是表达这三者的数学最小完备结构。更关键的架构决策是"低层"定位：不做高层预设，反而让所有高层框架（LangChain v1 的 Agent 抽象、Deep Agents、大量第三方编排层）都构建在其上——底层运行时成了生态的承重墙。商业上则形成"开源 LangGraph 吸引生产用户 → LangSmith 可观测性 + LangGraph Platform 部署变现"的漏斗。

### 3. LlamaIndex —— LLM 的"数据框架"（2022-11，原名 GPT Index）

**发布时间**：2022 年 11 月，以 **GPT Index** 名义发布（Jerry Liu：["During November of 2022, I created my first commit and first tweet on GPT Index"](https://www.linkedin.com/posts/jerry-liu-64390071_during-november-of-2022-i-created-my-first-activity-7129947165392601088-1rDr)）。官方周年博客同样记载 "November 2022: Launched GPT Tree Index"（[LlamaIndex Turns 1](https://www.llamaindex.ai/blog/llamaindex-turns-1-f69dcdd45fe3)）。2023 年上半年更名 LlamaIndex，Jerry Liu 明确说明是为规避 GPT 商标风险而"preemptively renamed"（[X/Twitter](https://x.com/jerryjliu0/status/1650673187896844288)）。

**创始团队**：Jerry Liu（前 Uber 机器学习工程师）在一个周末写出原型、把私有数据喂给 GPT-3；与联合创始人 Simon Suo（同样前 Uber）于 2023 年正式成立公司。来源：[startupintros: LlamaIndex](https://startupintros.com/orgs/llamaindex)、[ai.engineer 人物页](https://ai.engineer/speakers/jerry-liu)。

**核心设计理念**：**数据框架（Data Framework）**。官方自我定位即 "LlamaIndex is a data framework for LLM applications"——LLM 的知识被参数化训练数据锁死（parametric knowledge），要用私有/最新数据就必须有一套完整管线：**Data Connectors**（摄取各类数据源）→ **Indexes**（多种索引结构）→ **Retrievers** → **Query Engines**。核心抽象是 Index 而非 Chain 或 Agent。

**之所以然**：起点决定气质。LlamaIndex 的前身 GPT Tree Index 是一个非常具体的工程解——2022 年 11 月上下文窗口只有 4K，长文档塞不进去，树状索引（叶子节点存文本块、父节点存子节点摘要）让"先查摘要再钻取细节"成为可能。当 RAG 范式确立后，这个"垂直纵深做数据接入与检索"的基因，使 LlamaIndex 与 LangChain 形成清晰分野：**LangChain 是通用编排层（什么都能拼），LlamaIndex 是数据纵深层（把接入-索引-检索这条链做到最全）**。两者在 RAG 场景中大量互相引用对方组件，是互补而非纯竞品。

**长上下文之问（2026 追问）**：窗口从 4K 涨到 1M、未来 2M/5M，"塞不下"的问题消失了，数据框架层还成立吗？三分答案：

- **被吃掉的**：语料 < 窗口的小场景确实死了——"chat with a PDF" 类应用直接全文入窗，不再需要索引，RAG 市场底座被削掉一层
- **仍成立的**：语料 >> 窗口的企业场景。四条约束不随窗口增长：①语料无界（企业级 10⁹~10¹¹ tokens，对 1M~5M 窗口仍有 10³~10⁵ 倍差距）②经济（按前沿模型输入列表价 ~$3/M tokens 计，每查询塞 1M ≈ $3、检索 20K ≈ $0.06，50 倍差距；日调用万次即 $30K vs $600；prompt caching 只缓解重复前缀，救不了首次 prefill）③注意力质量（[NoLiMa](https://arxiv.org/abs/2502.05167)、RULER 实测"有效上下文"远小于标称，性能保持基线 85% 的有效长度普遍仅 32K 级）④生产刚需（增量新鲜度、按用户 ACL、溯源审计、缓存复用）
- **在变形的**：检索的实现从预计算 embedding 向量库部分转向 agentic search（Anthropic 官方：代码场景 grep 式检索优于预计算 RAG）；LlamaIndex 自己就是注脚——官方定位已从 RAG 框架改为 [agentic work 的文档基础设施](https://www.llamaindex.ai/blog/llamaindex-is-more-than-a-rag-framework)（解析/抽取，LlamaParse），[Jerry Liu："In 2025 we're moving beyond RAG to Agentic Document Workflows"](https://x.com/jerryjliu0/status/1877512801717203324)。数据基因（把非结构化语料变成模型可用的结构）持久，变的是"检索"那一步的形态

> 第一性收束：检索的本质是**预算约束下的信息选择**。窗口变大只是把"物理不可能"降级为"不经济"；要终结选择问题，需要 token 免费、注意力完美、语料有限三条同时成立——分别违反经济、实证与物理。实践已投票：拥有 1M 窗口模型的 Anthropic，其旗舰 Agent（Claude Code）恰恰构建在"不塞满上下文"之上（grep 检索 + 压缩 + 子 Agent 隔离）。

### 4. AutoGen —— 微软的"多智能体对话"范式（2023-08）

**发布时间**：2023 年 8 月开源，同月发布论文 [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation（arXiv:2308.08155）](https://arxiv.org/abs/2308.08155)，该论文已成为多 Agent 领域最高被引文献之一（被引 5000+）。

**创始团队**：微软研究院出品。核心人物：**Chi Wang**（微软 Principal Researcher，AutoGen 创造者，此前因微软轻量级 AutoML 库 FLAML 为人所知）与论文第一作者 **Qingyun Wu**（宾州州立大学助理教授，与微软长期合作研究）。来源：[Microsoft Research 出版页](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/)、[播客访谈介绍](https://www.youtube.com/watch?v=RLwyXRVvlNk)。

**核心设计理念**：**多智能体对话框架（Multi-Agent Conversation Framework）** + **对话编程（Conversation Programming）**。论点：LLM 的本质能力是对话，那么"让多个可对话代理（Conversable Agent）通过多轮对话协商分工"，比单一 monolithic agent 或预编程静态 pipeline 更能应对开放任务。任何实体——LLM、工具、人类——都实现统一对话接口；`UserProxyAgent` 可以执行代码并把结果回传给 `AssistantAgent`，形成"生成-执行-反馈"闭环。来源：[AutoGen 0.2 文档](https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat/)。

**之所以然与后续分裂**：AutoGen 是五者中唯一的纯研究院基因项目——先有范式论文、再有工程实现，这带来学术影响力（对话编程成为公认范式之一）也带来工程债。其演进路径剧烈：
- **v0.2**（2023-08）：AgentChat 高层 API，双 Agent 范式（Assistant + UserProxy）流行一时
- **v0.4**（2024 末）：向事件驱动、Actor 模型完全重构（[迁移指南](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/migration-guide.html)），大量 API 不兼容
- **AG2 分叉**（2024 末）：部分原 AutoGen 团队成员基于 v0.2 代码库独立分叉出 [AG2](https://github.com/ag2ai/ag2)，社区从此分裂（[Split 解析](https://blckalpaca.at/en/knowledge-base/ai-agents/ai-agent-frameworks-comparison/autogen-vs-ag2)）
- **Microsoft Agent Framework**（2025-10-01 公开预览）：微软官宣 AutoGen 与 Semantic Kernel 收敛为统一框架，AutoGen/SK 进入维护模式（[官方公告 Discussion #7066](https://github.com/microsoft/autogen/discussions/7066)、[Microsoft Learn](https://learn.microsoft.com/en-us/agent-framework/overview/)、[技术细节博客](https://devblogs.microsoft.com/agent-framework/semantic-kernel-and-autogen-part-2/)）

研究院项目的宿命在此体现得淋漓尽致：AutoGen 的价值最终被微软"战略收编"——不再作为独立开源框架竞争，而是成为 Azure 生态企业 Agent 平台的组成部分。对使用者的含义：**新项目不应再基于维护模式的 AutoGen v0.2/v0.4，要么迁移 Microsoft Agent Framework（绑定 Azure 路线），要么选社区延续的 AG2，要么换栈**。

### 5. CrewAI —— "角色扮演"多 Agent 编排（2023-11）

**发布时间**：2023 年 11 月开源发布（首个版本介绍文章见于 [noze.it, 2023-11-14](https://www.noze.it/en/insights/crewai-open-source/)）。

**创始团队**：**João Moura**（创始人兼 CEO，巴西裔资深工程师/技术教育者，亦是 DeepLearning.AI《Multi AI Agent Systems with crewAI》课程讲师，见[课程页](https://www.deeplearning.ai/courses/multi-ai-agent-systems-with-crewai)）。2024 年 10 月公司 CrewAI Inc. 宣布累计 $18M 融资：Series A 由 Insight Partners 领投，inception 轮由 boldstart ventures 领投。来源：[官方新闻稿（GlobeNewswire, 2024-10-22）](https://www.insightpartners.com/ideas/crewai-launches-multi-agentic-platform-to-deliver-on-the-promise-of-generative-ai-for-enterprise/)、[Moura 本人的 LinkedIn 公告](https://www.linkedin.com/posts/joaomdmoura_excited-to-announce-that-crewai-raised-18-activity-7254492114829332480-agi7)。

**核心设计理念**：**角色扮演（role-playing）**。GitHub 官方 tagline 即 "Framework for orchestrating **role-playing**, autonomous AI agents"（[crewAIInc/crewAI](https://github.com/crewaiinc/crewai)）。核心隐喻是一支人类团队：
- **Agent** = 带 `Role`（角色）、`Goal`（目标）、`Backstory`（背景故事）的成员——用叙事化人设约束 LLM 行为边界
- **Task** = 指派给某角色的具体任务，带预期产出描述
- **Crew** = 团队容器，定义 `Process` 编排模式：`sequential`（顺序流水线）或 `hierarchical`（层级制，由 manager agent 分派与验收）

**之所以然**：CrewAI 发布时 AutoGen 已是最热的多 Agent 框架，João Moura 的切入点不是"更强的能力"而是"更低的心智门槛"：AutoGen 自由度高但需要研究者思维去设计对话协议，行为难预测；CrewAI 反其道行之——**约定优于配置（convention over configuration）**，把多 Agent 协作映射到所有人都懂的组织行为学模型（团队、分工、经理），牺牲协议自由度换取可预测性与上手速度。这让 CrewAI 在 2024 年上半年迅速成为"非研究背景开发者做多 Agent"的默认选择，也让其公司化变现路径（企业平台版）异常顺畅。代价是：深度定制工作流时层级/顺序两种 Process 模式表达力不足，复杂生产场景常被引导向 LangGraph 类低层框架。

## 设计哲学对比：五种第一性抽象

| 维度 | LangChain | LangGraph | LlamaIndex | AutoGen | CrewAI |
|------|-----------|-----------|------------|---------|--------|
| 第一性抽象 | Chain（组合） | State Graph（控制） | Index（数据） | Conversation（协商） | Crew（组织） |
| 回答的问题 | 零件怎么拼 | 流程怎么控 | 数据怎么进 | 协作怎么谈 | 团队怎么带 |
| 控制流位置 | 框架预设 | **开发者显式定义** | 数据结构隐含 | Agent 对话涌现 | Process 模板二选一 |
| 易用性 vs 控制力 | 易用优先 | 控制力优先 | 易用优先 | 控制力优先（难） | 易用优先 |
| 出身基因 | 应用工程师 | 商业纠偏 | 数据工程师 | 学术研究院 | 独立开发者/教育者 |
| 商业模式 | LangSmith/Platform SaaS | 同左（生态承重墙） | LlamaCloud | 收编入 Azure | 企业平台版 |

**关键判断**：这五家不是同一赛道的五辆赛车，而是**不同楼层的五套建筑方案**——LangGraph 是地基（runtime），LangChain/CrewAI 是框架层（应用结构），LlamaIndex 是管线层（数据），AutoGen 是一种已被验证但也已被收编的范式（对话协商）。实际生产系统往往是组合使用，例如 LangChain/LlamaIndex 做构件 + LangGraph 做编排。

## 常见误区

| 误区 | 事实 |
|------|------|
| "五者是竞品，选一个就得放弃其他" | 抽象层级不同：LangGraph（runtime）与 LangChain/LlamaIndex（构件）天然互补；本仓库 Demo 即为 LangChain 构件 + LangGraph 编排的组合 |
| "AutoGen 是微软的现任主力框架" | 2025-10 起 AutoGen 与 Semantic Kernel 均进入维护模式，主线已收敛为 Microsoft Agent Framework；社区延续在 AG2 |
| "CrewAI 比 AutoGen 出现晚 = 更先进" | 晚出但押注的是不同维度（易用性），不是技术代差；两者控制流理念相反（模板化 vs 涌现式） |
| "LlamaIndex 是 LangChain 的 RAG 子模块" | 独立公司独立框架，仅聚焦数据纵深；与 LangChain 在 RAG 场景互为组件引用 |
| "发布越早的框架越成熟可依赖" | AutoGen（早于 CrewAI/LangGraph）反而经历分叉+维护模式；成熟度要看维护活跃度与公司战略地位，不看年龄 |
| "上下文窗口到 1M+，索引/RAG 就没用了" | 检索的本质是预算约束下的信息选择：语料无界、token 非零成本、有效上下文 << 标称（NoLiMa/RULER 实测）三条约束不随窗口消失；被吃掉的只是语料 < 窗口的小场景，见 LlamaIndex 节"长上下文之问" |

## 选型速查

```
你的需求是什么？
│
├─ 只要把私有数据接给 LLM（RAG 为主）
│  → LlamaIndex（数据纵深最全），复杂编排在 LangGraph 上加
│
├─ 单 Agent + 工具调用，快速原型
│  → LangChain（v1 标准抽象，底层即 LangGraph）
│
├─ 多阶段流程，需要审批/重试/断点恢复/精确调试（生产）
│  → LangGraph（唯一把控制力完全交给开发者的主流选择）
│
├─ 多 Agent 协作，团队希望低门槛、行为可预测
│  → CrewAI（角色隐喻 + Process 模板）
│
├─ 研究型对话协商范式 / 已在微软技术栈内
│  → Microsoft Agent Framework（原 AutoGen 路线的官方延续）；
│     脱离微软栈则考虑 AG2 或迁栈
│
└─ 长周期开放式深度任务
   → Deep Agents（构建于 LangGraph 之上，见 agent-frameworks.md）
```

## 参考资料

- [LangChain About：Harrison Chase side project 起家](https://www.langchain.com/about)
- [Wikipedia: LangChain（2022-10 发布）](https://en.wikipedia.org/wiki/LangChain)
- [Harrison Chase LinkedIn（Robust Intelligence → LangChain CEO）](https://www.linkedin.com/in/harrison-chase-961287118)
- [LangChain 官方博客：Deep Agents vs LangChain vs LangGraph（LangGraph 2024-01 引入）](https://www.langchain.com/blog/deep-agents-vs-langchain-vs-langgraph)
- [LangGraph 官网与文档](https://www.langchain.com/langgraph) · [docs.langchain.com/oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LlamaIndex 官方博客：LlamaIndex Turns 1](https://www.llamaindex.ai/blog/llamaindex-turns-1-f69dcdd45fe3)
- [Jerry Liu LinkedIn：2022 年 11 月首个 commit](https://www.linkedin.com/posts/jerry-liu-64390071_during-november-of-2022-i-created-my-first-activity-7129947165392601088-1rDr) · [更名推文](https://x.com/jerryjliu0/status/1650673187896844288)
- [arXiv:2308.08155 AutoGen 论文](https://arxiv.org/abs/2308.08155) · [Microsoft Research 出版页](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/)
- [AutoGen → Microsoft Agent Framework 官方公告（Discussion #7066）](https://github.com/microsoft/autogen/discussions/7066) · [Microsoft Agent Framework Overview](https://learn.microsoft.com/en-us/agent-framework/overview/)
- [AutoGen vs AG2 分叉解析](https://blckalpaca.at/en/knowledge-base/ai-agents/ai-agent-frameworks-comparison/autogen-vs-ag2) · [AG2 GitHub](https://github.com/ag2ai/ag2)
- [crewAI GitHub](https://github.com/crewaiinc/crewai) · [CrewAI $18M 融资官方新闻稿（2024-10-22）](https://www.insightpartners.com/ideas/crewai-launches-multi-agentic-platform-to-deliver-on-the-promise-of-generative-ai-for-enterprise/)
- [noze.it：CrewAI 2023-11 首发介绍](https://www.noze.it/en/insights/crewai-open-source/)
- [DeepLearning.AI：Multi AI Agent Systems with crewAI（João Moura）](https://www.deeplearning.ai/courses/multi-ai-agent-systems-with-crewai)
- [LangChain 官方博客：Deep Agents（2025-07，Harrison Chase）](https://www.langchain.com/blog/deep-agents)
- [Anthropic：Effective context engineering for AI agents（2025-09）](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Wikipedia: Model Context Protocol（OpenAI 2025-03 采纳、Google 2025-04 跟进）](https://en.wikipedia.org/wiki/Model_Context_Protocol)
- [Google Developers Blog: A2A 捐赠 Linux Foundation（2025-06-23）](https://developers.googleblog.com/en/google-cloud-donates-a2a-to-linux-foundation/) · [Linux Foundation 新闻稿](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [NoLiMa: Long-Context Evaluation Beyond Literal Matching（Adobe Research，arXiv:2502.05167）](https://arxiv.org/abs/2502.05167) · [RULER（NVIDIA，arXiv:2404.06654）](https://arxiv.org/abs/2404.06654) — 有效上下文远小于标称的实证
- [RAG or Long-Context LLMs? An Empirical Study（arXiv:2407.16833）](https://arxiv.org/abs/2407.16833) — 长上下文效果略优但成本高一个量级，混合方案以接近 RAG 的成本逼近 LC 效果
- [LlamaIndex 官方博客：More than a RAG Framework（2026-03）](https://www.llamaindex.ai/blog/llamaindex-is-more-than-a-rag-framework) · [Jerry Liu X：Agentic Document Workflows（2025-01）](https://x.com/jerryjliu0/status/1877512801717203324) — LlamaIndex 自身转型注脚

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-08 | 初始创建：五大框架（LangChain / LangGraph / LlamaIndex / AutoGen / CrewAI）核心设计理念、创始团队、发布时间调研；代际时间线洞察；AutoGen→AG2→Microsoft Agent Framework 演进链；五抽象对比与选型速查。所有关键事实经联网核实 |
| 2026-10-09 | 时间线延伸至 2025：新增「Agent 变深 + 互联」阶段及延伸小节（产品形态层 Deep Agents / 机制层 Context Engineering / 生态层 MCP-A2A 三层答案）；代际洞察段同步扩展，附 2026 走向；关键时间点（OpenAI 采纳 MCP 2025-03、A2A 捐赠 2025-06、Anthropic 博客 2025-09）经联网核实 |
| 2026-10-09 | LlamaIndex 节新增「长上下文之问」：1M+ 窗口下数据框架层逻辑的三分答案（小场景被吃掉 / 企业场景四约束仍成立 / 检索形态转向 agentic search），含 LlamaIndex 官方转型注脚与 NoLiMa/RULER 实证；常见误区表新增对应条目；第一性收束：检索 = 预算约束下的信息选择 |
