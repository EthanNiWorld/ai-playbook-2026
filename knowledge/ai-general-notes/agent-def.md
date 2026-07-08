# Agent

> 最后更新: 2026-04-23
> 领域: AI Engineering
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 让 LLM 具备自主规划、使用工具、完成复杂任务的能力；本质是一个不确定性受控的 for 循环
**核心价值**: 从"对话助手"升级为"自主执行助手"——模型从被动回答变为主动感知、规划、行动；模型从产品本身转变为产品的一部分，厚软件层成为新壁垒
**相关产品**: [HiClaw/龙虾家族](../../alibaba-ai-hub/ai-application/claw-family.md), [JVS Crew](../../alibaba-ai-hub/ai-application/jvs-crew.md), [Claude Managed Agents](../anthropic/claude-managed-agents.md), [OpenAI Codex](https://openai.com/codex)
<!-- SUMMARY_END -->

## 是什么

Agent 是一个围绕 LLM 构建的自主执行系统，能够感知环境、调用工具、做出决策，并持续循环直到任务完成。

**最精准的底层比喻**：Agent 本质是一个 **for 循环**。

```
while not done:
    感知（Perception） → 思考（Reasoning） → 行动（Action） → 观察（Observation）
```

但这个循环有三个关键的"不确定性"让它远比普通 for 循环复杂：
1. **思考不是确定性的**：相同输入，LLM 可能给出不同的行动计划
2. **退出条件不固定**：循环何时结束，由模型判断，不是硬编码的
3. **行动有副作用**：调用 API、写数据库、发邮件——每一步都可能不可逆

## 核心原理

### Agent = Model + 产品化 Harness

```
Agent = Model（大脑）+ Harness（缰绳+鞍具）
```

- **Model**：提供理解和生成能力，是推理引擎
- **Harness**：提供约束、工具权限、人工介入点、监控机制——决定 Agent 能做什么、不能做什么

> 模型是 commodity（越来越同质化），真正的差异化在 Harness 的设计质量。相同的模型，接不同的 Harness，出来的产品能力天差地别。

### Agent 平台战略拐点（2026-04 更新）

**行业趋势**：模型从"产品本身"转变为"产品的一部分"

- **过去**：模型上面只有一层很薄的软件
- **现在**：一层很厚的软件层，包括 skill、连接器、计算机操作、上下文管理、记忆
- **比喻**：有了大脑（模型），现在在造身体。两者都很难，必须协同设计

**OpenAI 三大优先级**（2026-04）：
1. **构建极致的 Agent 平台**（第一优先级）
2. **将 Agent 应用到所有 computer work**：从软件工程扩展到法律、金融、写作、表格、PPT等垂直行业
3. **Personal AGI**：每人一个代表自己的 AI，拥有用户上下文，能主动行动

**战略逻辑**：
- 单模型能力已触及用户交互瓶颈
- Agent 平台可构建生态壁垒，开发者能构建自己的 Agent
- 小公司能获得以前不可能的收入规模，释放新一波创业浪潮

### 感知-推理-行动-观察循环

| 阶段 | 含义 | 工程关键点 |
|------|------|-----------|
| **感知** | 接收输入（用户指令、工具返回、环境状态） | 上下文窗口管理、信息压缩 |
| **推理** | 模型决策下一步行动 | Prompt 设计、思维链（CoT）、工具选择 |
| **行动** | 调用工具/API/写数据 | 权限控制、幂等性、失败重试 |
| **观察** | 将行动结果反馈回上下文 | 结果解析、错误信号注入 |

## 关键选型维度

| 维度 | 单 Agent | 多 Agent（Manager-Worker） | 怎么选 |
|------|---------|--------------------------|--------|
| 任务复杂度 | 线性、单一目标 | 可拆解的并行子任务 | 任务能否并行拆解是核心判断 |
| 错误传播 | 单点失败即终止 | Worker 失败不影响全局 | 高可靠需求用多 Agent |
| 工程复杂度 | 低 | 高（协调开销大） | 简单任务不要过度设计 |
| 典型产品 | Claude Managed Agents | HiClaw（Manager-Worker） | 参见产品文档 |

## 各厂商实现对照

| 能力 | 阿里云 | Anthropic | OpenAI | 开源 |
|------|--------|-----------|--------|------|
| 托管 Agent 平台 | [JVS Crew](../../alibaba-ai-hub/ai-application/jvs-crew.md)、百炼龙虾 | [Claude Managed Agents](../anthropic/claude-managed-agents.md) | Codex Agent 平台 | OpenClaw、LangGraph |
| 多 Agent 框架 | [HiClaw](../../alibaba-ai-hub/ai-application/claw-family.md)（Manager-Worker） | 无内置框架 | 规划中 | CrewAI、AutoGen |
| Agent 执行环境 | 无影 AgentBay（沙箱） | gVisor disposable 运行时 | 统一 Agent 基础设施 | Docker 自托管 |
| 企业 SSO/RBAC | JVS Crew（含 AAD） | 暂不支持（2026-04公测版） | 支持 | 需自建 |
| 编程 Agent | Qoder | Claude Code | Codex | Continue、Aider |
| 垂直行业扩展 | 进行中 | 进行中 | 法律/金融/写作等 | - |

## 最佳实践

### 老代码 AI 改造三步法

当用 AI Agent 改造存量代码仓库时，推荐：

1. **先还原**：让 AI 读老代码，产出 SPEC（接口约定、业务逻辑文档）——建立基准线
2. **再设计**：明确改什么、不改什么——防止 AI 生成代码时丢失隐含约定
3. **后生成**：基于 SPEC 生成新代码，保证新旧代码能融合

> 本质是"理解 → 规划 → 执行"的标准工程流程，跳过理解直接生成是最大的陷阱。

### Agent 工程化要点

- **退出条件显式化**：不要依赖模型自判断"任务完成"，要有硬性终止条件（最大步数、超时）
- **工具幂等性**：能重试的操作必须幂等，不可逆操作需要人工确认门
- **上下文压缩**：长循环中上下文会膨胀，需要摘要/截断策略
- **可观测性优先**：每一步的感知-行动-观察都要有日志，否则调试极难

## 常见误区

| 误区 | 事实 |
|------|------|
| "Agent 就是高级 Prompt" | Agent 是系统工程，不是 Prompt 技巧，核心难点在循环控制和工具调用 |
| "模型越强，Agent 越好" | Harness 质量决定上限，差的 Harness 会让强模型也"跑偏" |
| "用多 Agent 更高级" | 单 Agent 能解决的问题，加多 Agent 只会增加复杂度和 debug 难度 |
| "Agent 一定能自动完成复杂任务" | 长任务中错误会累积，关键步骤必须设置人工介入点 |

## 参考资料

- 来源于 2026-04-23 龙虾家族产品分析沟通（HiClaw 分享观点部分）
- [OpenClaw 开源项目](https://github.com/agentscope-ai/HiClaw)
- [无影 AgentBay 产品页](https://www.aliyun.com/product/agentbay)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-04-24 | 新增：Agent平台战略拐点、OpenAI三大优先级、各厂商Agent平台对照扩展（来源：OpenAI创始人访谈） |
| 2026-04-23 | 初始填充，基于龙虾家族对话中的第一性原理洞察：Agent for循环本质、Agent=Model+Harness、老代码三步法 |
