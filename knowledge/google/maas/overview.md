# Gemini Enterprise Agent Platform — MaaS & Agent 服务

> 最后更新: 2026-05-31
> 所属厂商: GCP
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: GCP 的统一 MaaS 与 Agent 平台入口。2026.04 Google Cloud Next '26 上，Vertex AI 品牌正式退役，Model Garden 等所有模型服务折叠进 Gemini Enterprise Agent Platform。平台支持 Gemini 自研模型 + 第三方模型（Claude、Llama 等），通过 Model Garden 统一访问
**适用**: 企业级 Agent 构建、模型选型与部署、多模态应用开发
**不适用**: 仅需单次 API 推理（直接用 Gemini API / AI Studio）
**竞品**: Azure AI Foundry、火山方舟 MaaS、AWS Bedrock
<!-- SUMMARY_END -->

## 平台架构

### Gemini Enterprise 三大组件

| 组件 | 说明 |
|---|---|
| **Agent Platform** | 开发者界面：ADK 2.0、Agent Studio、Model Garden、Agent Runtime、Govern/Optimize 工具链 |
| **Enterprise App** | 知识工作者界面：无代码 AI 助手，由原 Agentspace 演变而来 |
| **Agent Marketplace** | 合作伙伴 Agent 市场：Adobe、Salesforce、ServiceNow、Workday 等预构建 Agent |

### Model Garden（模型花园）

已整合进 Agent Platform 的 Build 层，提供：

| 模型来源 | 代表模型 |
|---|---|
| **Google 自研** | Gemini 2.5 Flash / Pro / Ultra、Imagen（文生图）、Chirp（语音） |
| **第三方** | Claude Opus/Sonnet（Anthropic）、Llama（Meta）、开源模型 |
| **开源** | 通过 HuggingFace 等渠道接入 |

### Agentic Data Cloud

Agent 的上下文引擎：

| 组件 | 能力 |
|---|---|
| **Knowledge Catalog** | 聚合企业全数据资产（Salesforce/SAP/ServiceNow/Workday），混合语义+词法+Rerank 搜索，保留源数据 ACL 权限 |
| **BigQuery** | Fluid scaling 降低自动扩缩成本 34%，与 Gemini 深度集成 |
| **Iceberg REST Catalog** | 双向联邦：与 Databricks Unity、Snowflake Polaris、AWS Glue 互通 |

## 关键特性

- **MCP everywhere**：每个 GCP 服务都有 MCP 端点，Agent 可通过标准协议调用任何 GCP 服务
- **A2A 协议**：Agent-to-Agent 通讯标准，50+ 合作伙伴已加入
- **BYO-MCP**：自带 MCP Server 接入 Agent Platform
- **跨云开放**：Spanner Omni 可离线运行、Iceberg 联邦跨云、Claude 等第三方模型在 Model Garden 原生可用

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-05-31 | 重写：Vertex AI→Gemini Enterprise Agent Platform 品牌迁移、Model Garden 整合、Agentic Data Cloud、MCP/A2A 协议支持 |
