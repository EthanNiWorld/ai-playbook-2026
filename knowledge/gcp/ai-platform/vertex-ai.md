# Gemini Enterprise Agent Platform（原 Vertex AI）

> 最后更新: 2026-05-31
> 所属厂商: GCP
> 产品类别: AI Platform
> 状态: Published

<!-- SUMMARY_START -->
**定位**: Google Cloud 的统一 AI 平台，2026.04 Google Cloud Next '26 上正式取代 Vertex AI 品牌，成为 Gemini Enterprise 三大组件之一（Agent Platform + Enterprise App + Agent Marketplace），所有模型训练、部署、Agent 构建能力均通过此平台交付
**适用**: 企业级 Agent 规模化构建与治理、多 Agent 协作、长运行 Agent 生产部署、AI 安全合规
**不适用**: 简单单次 API 调用（用 Gemini API / AI Studio 即可）、非 GCP 生态的纯开源自建
**竞品**: Azure AI Foundry、火山方舟、AWS Bedrock + SageMaker
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

Google Cloud 在 2026 年 4 月宣布 **Vertex AI 品牌死亡**，所有服务被折叠进 **Gemini Enterprise Agent Platform**。官方表述："all Vertex AI services and roadmap evolutions will be delivered exclusively through the Agent Platform, rather than as a standalone service."

品牌合并原因：客户反复问"我还要买 Vertex 吗？"——品牌分裂拖累了销售。Gemini Enterprise 现在是产品名，Agent Platform 是开发者界面，Enterprise App 是知识工作者界面。

### 底层架构：四层 Agent Platform

Agent Platform 按 **Build → Scale → Govern → Optimize** 四层组织：

| 层 | 核心产品 | 能力 |
|---|---|---|
| **Build** | ADK 2.0、Agent Studio、Agent Garden、Agents CLI | 三种编排模式：Graph-based workflows（确定性 DAG）、Collaborative agents（多 Agent 协作）、Dynamic workflows（代码级循环/分支）。ADK 支持 Python/Go/TypeScript 的 Skill 系统 |
| **Scale** | Agent Runtime（GA）、Agent Sessions、Memory Bank、Agent Sandbox | 亚秒级冷启动、最长 7 天自主运行、BYOC 自定义容器、3000 Agent/项目、Memory Profiles 用户级精准召回 |
| **Govern** | Agent Registry、Gateway、Identity、Model Armor、Anomaly Detection | Agent 注册表、网关、身份管理、异常检测、安全合规仪表盘 |
| **Optimize** | Agent Simulation、Evaluation、Observability、Optimizer | 合成用户压测 → 多轮自动评分 → DAG 可视化 Trace → 自动聚类失败并建议修改 System Instruction |

### ADK 2.0（Agent Development Kit）

2026 年新增三种编排模式，月均超 6 万亿 tokens 流经 ADK Agent：

| 模式 | 说明 | 适用场景 |
|---|---|---|
| **Graph-based** | 确定性 DAG 工作流，显式控制路由和执行顺序 | 审批流程、多步骤合规任务 |
| **Collaborative agents** | Coordinator + 多 Sub-agent，原生多 Agent 协作 | 跨部门复杂任务 |
| **Dynamic workflows** | 代码级逻辑控制（循环、条件分支、迭代决策） | 需要自适应决策的任务 |

### Agent 优化四件套（全网第一家）

| 工具 | 做什么 | 状态 |
|---|---|---|
| **Agent Simulation** | 用合成用户 + 虚拟化工具压测 Agent，自动评分 | Preview |
| **Agent Evaluation** | 多轮自动评分，评对话逻辑而非单次回复 | GA |
| **Agent Observability** | 执行 DAG 可视化 + 全链路 Trace | Public Preview |
| **Agent Optimizer** | 自动聚类失败 → 建议修改 System Instruction | GA |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| API 不统一 | `google.genai` 与 `vertexai` 两套 API 将长期共存 | 开发者困惑，但 Google 已确认"indefinitely" |
| 品牌重学成本 | Vertex AI → Gemini Enterprise 迁移 | 文档和旧教程中的 Vertex AI 引用需逐步更新 |
| 平台复杂度 | 表面面积大：ADK、Agent Studio、Runtime、Memory Bank、Sessions、Sandbox、Simulation、Evaluation、Observability、Optimizer 等 20+ 组件 | 开发者教育需要时间追赶 |

## 适用边界分析

### ✅ 适用场景

| 场景 | 说明 | 典型客户/案例 |
|------|------|--------------|
| 企业级 Agent 规模化 | 需要 Registry、Gateway、Identity 治理的大规模 Agent 部署 | Comcast、L'Oréal、Macquarie Bank、PayPal |
| 长运行 Agent | 7 天自主运行 + Memory Bank 持久记忆 | 自动化运维、持续监控 |
| 多 Agent 协作 | 需要 Coordinator + Sub-agent 的复杂任务 | 跨系统数据整合 |
| 安全合规 Agent | Model Armor + Anomaly Detection + 合规仪表盘 | 金融、医疗 |
| Data + AI 融合 | Knowledge Catalog 聚合全企业数据 + BigQuery 分析 | 企业知识库、BI 智能化 |

### ❌ 不适用场景

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 简单单次推理 | 平台 overhead 太大 | Gemini API / AI Studio |
| 非 GCP 生态 | 深度绑定 GCP 基础设施 | Azure AI Foundry / AWS Bedrock |

## 竞品快速对照

| 维度 | Gemini Enterprise Agent Platform | Azure AI Foundry | 火山方舟 |
|------|---|---|---|
| Agent 框架 | ADK 2.0（三种编排） | Semantic Kernel / AutoGen | 豆包 Agent 开发 |
| 治理层 | Govern 四件套（最完整） | Responsible AI 工具 | 基础 |
| 优化闭环 | Simulation+Evaluation+Observability+Optimizer | Prompt Flow 评估 | 基础监控 |
| 自研芯片 | TPU 8t/8i 双芯 | 无 | 无 |
| 低代码 | Agent Studio | Copilot Studio | Agent 开发平台 |
| 数据+AI | BigQuery + Knowledge Catalog + Iceberg 联邦 | Fabric + Cosmos DB | 数据中台 |

## 参考资料

- [Google Cloud Next '26 Recap (TWIML)](https://twimlai.com/articles/google-cloud-next-26-recap)
- [Vertex AI Agent Builder 2026 Guide (UI Bakery)](https://uibakery.io/blog/vertex-ai-agent-builder)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-05-31 | 重写：Vertex AI→Gemini Enterprise Agent Platform 品牌迁移、四层架构、ADK 2.0、Agent 优化四件套 |
