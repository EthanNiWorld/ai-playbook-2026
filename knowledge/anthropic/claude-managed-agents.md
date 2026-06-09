# Claude Managed Agents

> 最后更新: 2026-04-23
> 所属厂商: Anthropic
> 产品类别: AI App
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 云端全托管 AI Agent 平台（2026-04-08 公测），推理与执行解耦架构，仅支持 Claude API，不支持 AWS Bedrock/GCP Vertex AI/私有化
**适用**: 需要顶级模型能力、gVisor 级沙箱安全、不可变审计日志、纯公网 SaaS 的 AI Agent 场景
**不适用**: 需要内网部署、企业 SSO/RBAC、IM 集成（钉钉/企微/飞书）、私有化部署的中国企业场景
**竞品**: JVS Crew（阿里云）、Copilot Studio（Microsoft）
**常搭配**: Claude API（claude-opus-4.8 / sonnet-4.6 / haiku-4）
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

Anthropic 推出的云端全托管 AI Agent 平台，核心架构为推理与执行解耦，支持多触发模式，以 gVisor 沙箱和 Vault 凭证隔离为安全核心。

### 底层原理

**架构四大模块**：推理层（Claude 模型）、执行层（gVisor 沙箱）、凭证层（Vault 机制）、审计层（只读持久化日志）

**关键设计原则**：
- Agent 执行环境为 **disposable**（一次性运行时），执行完毕即销毁
- 凭证不入沙箱：API Key 通过 Vault 机制隔离，Agent 执行节点不接触真实密钥
- 审计日志为只读持久化（不可变），无法篡改

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 模型锁定 | 仅 Claude API | 不支持 AWS Bedrock、GCP Vertex AI、私有化部署 |
| SSO/RBAC | **不支持** | 无角色权限控制，无 per-agent 权限范围 |
| 内网支持 | **不支持** | 纯公网 SaaS，无 VPC 穿透 |
| 状态 | 公测（2026-04-08） | 企业功能（SSO/RBAC 等）可能在路线图中 |

## 功能特性

| 维度 | 详情 |
|------|------|
| **架构** | 推理与执行解耦，四大模块 |
| **模型** | 仅 Claude 系列（claude-opus-4.8 / sonnet-4.6 / haiku-4） |
| **触发** | 多种触发模式（API 调用、定时、事件等） |
| **调试** | 控制台 + SDK + CLI |
| **监控** | 会话日志 |

## 安全与审计

| 维度 | 详情 |
|------|------|
| **沙箱** | gVisor 隔离引擎，disposable 一次性运行时 |
| **凭证** | Vault 机制，凭证不入沙箱，隔离最彻底 |
| **网络** | JWT 代理 + TLS 检查 + DNS 禁用 + limited 模式 |
| **审计** | 只读持久化事件日志（不可变，无法篡改） |
| **SSO** | **不支持**（无 RBAC，无 per-agent 权限） |
| **内网** | 不支持（纯公网 SaaS） |

## 计费模式

| 维度 | 详情 |
|------|------|
| **Token** | 标准 Claude API 费率（claude-opus-4.5 等） |
| **Session** | $0.08/Session 小时（仅 Running 时计费） |
| **额外** | 网页搜索 $10/千次 |
| **预充值** | 不需要 |

## 竞品快速对照

与 JVS Crew（阿里云）客观对比：

| 对比项 | 优势方 | 说明 |
|------|:---:|------|
| **模型能力** | Claude Managed Agents | Claude 系列行业第一梯队 |
| **企业身份集成（SSO/RBAC）** | JVS Crew | Claude 当前无 SSO/RBAC |
| **内网/VPC 支持** | JVS Crew | Claude 纯公网 SaaS |
| **沙箱技术透明度** | Claude Managed Agents | gVisor 实现更透明 |
| **凭证隔离** | Claude Managed Agents | Vault 机制更彻底 |
| **不可变审计日志** | Claude Managed Agents | 默认只读持久化日志 |
| **多渠道 IM 集成** | JVS Crew | JVS 支持钉钉/企微/飞书 |
| **计费模式** | 持平 | 都是按需后付费 |

> ⚠️ Claude Managed Agents 2026-04-08 刚发布公测，SSO/RBAC 等企业功能可能在路线图中，当前对比不代表最终能力。

## 参考资料

- [Verdent AI：Claude Managed Agents 定价](https://www.verdent.ai/guides/claude-managed-agents-pricing)
- [Pluto Security：Claude Managed Agents 安全分析](https://pluto.security/blog/securing-claude-managed-agents/)（明确指出无 RBAC/per-agent 权限）
- [ToolIn：Claude Managed Agents 功能介绍](https://toolin.ai/blog/claude-managed-agents)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-04-23 | 初始创建，基于 Claude Managed Agents vs JVS Crew 对比分析（2026-04-23） |
