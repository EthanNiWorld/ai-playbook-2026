# Qoder

> 最后更新: 2026-07-01
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: AI Coding
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 智能体编程平台（Agentic Coding Platform），面向真实软件开发场景，10倍研发提效。提供 Teams 和 Enterprise 两个组织版本  
**适用**: 研发团队、企业组织，需要统一 AI 编程工具链、沉淀团队知识、集中管控  
**不适用**: 仅需简单代码补全的个人用户（可用社区免费版）  
**竞品**: Kiro (AWS), Cursor, GitHub Copilot, Trae (ByteDance)  
**常搭配**: 百炼平台（MaaS）、阿里云开发者生态  
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

面向真实软件的智能体编程平台，支持全球 SOTA 及亚太 SOTA 模型智能调度，实现从辅助编程到完全自主编程的全谱系开发体验。

### 4 大核心模式

| 模式 | 功能 | 场景 |
|------|------|------|
| **NEXT** | 智能代码补全与行间建议预测 | 日常编码提效 |
| **Agentic Chat** | 对话式智能体协同，自动理解意图、拆解任务 | 规划、编码与交付协同 |
| **Quest** | 自主智能体，端到端独立完成任务 | 复杂、长周期开发任务 |
| **RepoWiki** | 团队知识引擎，从代码和对话中沉淀知识 | 代码库文档化与架构理解 |

### 产品形态

| 形态 | 说明 |
|------|------|
| Qoder IDE | 原生 AI IDE 开发环境 |
| JetBrains 插件 | 适配 IntelliJ IDEA 等 JetBrains 全系 IDE |
| Qoder CLI | 终端原生工作形态 |
| QoderWork | 桌面 Agent、本地智能助手 |
| QoderWake | 后台智能任务执行 |
| Cloud Agents | 云端自主智能体 |
| Qoder Mobile | 移动端 AI 编程 |

### Qoder CLI 技术栈演进

Qoder CLI 最初使用 **Go** 语言开发，后因不满足快速迭代需求，整体重构为 **TypeScript**。投入 7 人、30 天完成重写二十万行代码。 可以作为qoder本身的案例case。 

**为什么从 Go 切换到 TypeScript？**

| 维度 | Go | TypeScript | 切换原因 |
|------|-----|-----------|----------|
| AI 工具链生态 | pkg.go.dev AI 库较少 | npm AI/LLM SDK 丰富（OpenAI、Anthropic、MCP 官方 SDK 均为 TS 优先） | TS 生态与 AI Coding 工具天然亲和 |
| 流式交互架构 | goroutine 强于高并发，但流式 UI 渲染需更多胶水 | async/await + ReadableStream 原生适配流式 LLM 输出 + 终端渲染 | AI CLI 核心是流式交互，TS 更自然 |
| IDE 生态亲和度 | 与 VSCode/LSP 生态距离较远 | VSCode 本身为 TS/Electron，LSP、tree-sitter TS binding 为一等公民 | Qoder 需深度集成 IDE 能力 |
| MCP 协议支持 | 需自行适配 | Anthropic MCP 官方 SDK 为 TS 优先 | Qoder 深度依赖 MCP 生态 |
| 终端 UI 框架 | cobra + bubbletea，生态较小 | Ink（React for CLI）、oclif、@inquirer 等，迭代快 | 复杂终端交互开发效率更高 |
| 团队与招聘 | Go 开发者池较小 | TS/全栈工程师池大，前端可无缝参与 CLI 开发 | 扩大可参与开发的团队范围 |
| 代码复用 | CLI 与 IDE 插件（TS）需各写一套 | CLI 与 IDE 插件共享核心逻辑（模型调用、MCP 集成） | 消除跨形态重复开发 |

> **总结**：Go 的优势在高并发后端服务；Qoder CLI 本质是“AI 交互前端”（流式 UI + IDE 集成 + MCP 协议），这些是 TypeScript 的主场。

### 核心能力特性

- 全球 SOTA + 亚太 SOTA 模型智能调度，兼顾性能与成本
- 特训智能体大模型，对话次数提升 4 倍
- 工程知识引擎系统（记忆 + 全量实时代码检索）
- MCP 生态集成，灵活拓展功能

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 席位 Credits（仅 Teams） | 3,000/席位/月 | 固定额度，不可席位间共享，月末清零 |
| Enterprise 席位 | 不带 Credits | 纯靠组织共享资源包 |
| 共享资源包有效期 | 3 个月 | 到期清零，不可转让 |
| 购买渠道 | 阿里云国际云市场 | 兑换码模式，购买后不可退款 |

## 计费模式

### 设计逻辑（Why Credits）

Qoder 采用 Credit 计量制而非纯席位订阅，背后逻辑：
1. AI 编程“消费量”在开发者间差异巨大（轻度补全 vs 重度 Agent），按量计费覆盖更广场景
2. Credits 机制将不同模型的消耗统一度量，简化多模型定价复杂度
3. Teams 版设计为“人头费 + 按需补充”双层结构，反映企业采购典型诉求

### Teams 版方案

| 项目 | 详情 |
|------|------|
| 席位价格 | $40/席位/月 |
| 席位额度 | 3,000 Credits/席位/月（固定，不可共享，月末清零） |
| 组织共享资源包 | $40/2,000 Credits（组织内全员共享，有效期 3 个月） |
| 消耗优先级 | 席位额度 → 组织共享资源包 |
| 企业功能 | 集中计费、管理员控制台、SSO、域限制、RBAC |

### Enterprise 版方案

| 项目 | 详情 |
|------|------|
| 席位价格 | $20/席位/月 |
| 席位额度 | **不带任何 Credits**，纯靠组织共享资源包 |
| 组织共享资源包 | $40/2,000 Credits（同 Teams） |
| 消耗优先级 | 组织共享资源包 |
| 购买渠道 | 官网直接购买 或 阿里云云市场兑换码（Credits 有效期 24 个月） |

**Enterprise 比 Teams 多的独有能力：**

| 类别 | 能力 | 说明 |
|------|------|------|
| 组织架构 | 群组（Groups） | 按部门/团队分组，分组权限和计费独立管理 |
| 计费管理 | 成员分组计费 | 不同组设不同额度，精细化成本管控 |
| AI 可信治理 | 模型路由策略 + 内容安全策略 | 限制可用模型范围、设置内容安全过滤规则 |
| 能力分发 | Plugin/Skill 统一下发 + Marketplace | 强制推送插件到所有成员，企业私有插件市场 |
| 知识引擎 | 个人知识库 15G（Teams 10G） | 更大的个人知识存储空间 |
| 安全合规 | 操作审计 | 完整操作日志审计 |
| 开放性 | 更丰富的 API 接口 | 企业级集成能力（Teams 仅基础 API） |

> **Teams 与 Enterprise 版本独立隔离，不支持相互切换/升降级。** 选择前需充分评估。 `[来源: 用户口述]` `[⚠️ 待官方验证]`

### 席位管理规则（通用）

- 最少 2 个席位起购
- 增购席位按当前周期剩余天数**按比例计费**
- 减少席位：空闲席位可随时减配，差额按比例退还
- 两种角色：管理员（Admin，计费角色，全部管理权限）、成员（Member，计费角色，使用权限）

### 购买渠道（以云市场为准）

| 产品 | 云市场链接 |
|------|------------|
| Teams 席位 | https://marketplace.alibabacloud.com/products/201076001/sgcmgj00036615.html |
| 组织共享资源包 | https://marketplace.alibabacloud.com/products/201076001/sgcmgj00036655.html |

### 开通流程

1. 注册 qoder.com 账号，创建组织并获取组织 ID
2. 前往云市场下单（填写组织 ID）
3. 收到兑换码后在 Qoder 后台激活 — [Redemption Guide](https://docs.qoder.com/zh/account/teams/about-redeem)

## 适用边界分析

### ✅ 适用场景

| 场景 | 说明 | 典型客户 |
|------|------|----------|
| 团队统一 AI 编程工具 | 集中管理、知识沉淀、新人快速上手 | 中大型研发团队 |
| 复杂任务自动化 | Quest 自主智能体端到端完成 | 技术领导者 |
| 跨区域企业部署 | SSO + 域限制 + 集中计费 | 跨国/跨地域组织 |

### ❌ 不适用场景

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 仅需基础补全的个人用户 | 社区版已满足，无需付费 | 社区版（免费） |
| 需要企业级治理能力但已选 Teams | Teams/Enterprise 不可相互切换 | 初始选择时充分评估 |

## 安全与合规

| 安全能力 | 说明 |
|----------|------|
| 数据加密 | 传输与存储全程加密，代码数据不用于模型训练 |
| 数据隐私模式 | 管理员可统一设置团队隐私策略 |
| SSO & RBAC | 支持 SAML 2.0 / OIDC 单点登录，基于角色的访问权限控制 |
| 基础设施 | 阿里云全球基础设施，通过 ISO 27001 / SOC 2 等认证 |
| 隐私政策 | https://qoder.com/privacy-policy |

## 竞品快速对照

| 维度 | Qoder | Kiro (AWS) | Cursor |
|------|-------|-----------|--------|
| 定位 | 智能体编程平台 | Spec-driven AI IDE | AI Code Editor |
| 模型策略 | 全球+亚太 SOTA 智能调度 | Claude 单模型 | 多模型可选 |
| 团队功能 | Teams版/Enterprise版 SSO/RBAC/集中计费 | [⚠️ 待验证] | Teams版 |
| 知识引擎 | RepoWiki + Memory | Steering [⚠️ 待验证] | - |

## 参考资料

- 官网: https://qoder.com
- 文档: https://docs.qoder.com
- 价格说明: https://docs.qoder.com/zh/account/pricing
- Teams 价格: https://docs.qoder.com/zh/account/teams/teams-pricing
- 计费调整公告: https://docs.qoder.com/zh/events/pricing-adjustment-notice
- 兑换码说明: https://docs.qoder.com/zh/account/teams/about-redeem
- 企业版: https://qoder.com/zh/enterprise

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-04-20 | 初始创建（Draft） |
| 2026-05-26 | 合并：inbox/ai-knowledge-by-qoder-ai-native-agent-20260526.md - 完善产品定位、4大核心模式、计费模式、安全合规、竞品对照 |
| 2026-06-08 | 增量：用户口述 - 新增 Qoder CLI 技术栈演进（Go → TypeScript，7人30天）及切换原因分析 |
| 2026-07-01 | 合并：inbox/ai-knowledge-by-qoder-ai-native-agent-20260701.md - 新增 Enterprise 版本能力与计费模型、产品形态补全、席位管理规则；修正“企业版待发布”为已发布；移除消耗优先级中的“个人资源包”（Teams/Enterprise 成员不可购买） |