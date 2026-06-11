# JVS Crew

> 最后更新: 2026-04-23
> 所属厂商: 阿里云
> 产品类别: AI App
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 企业级 AI 数字助理构建与托管平台，基于无影云电脑体系，对标 Claude Managed Agents，差异化在内网+SSO+可审计+按 Session 执行计费
**适用**: 需要内网部署、企业 SSO（含 AAD）、合规审计、IM 集成（钉钉/企微/飞书）的企业 AI Agent 场景
**不适用**: 无 SSO/内网需求的轻量个人 Agent 场景、需要顶级模型能力优先于合规的场景
**竞品**: Claude Managed Agents（Anthropic）
**常搭配**: 百炼大模型、无影 AgentBay、钉钉/企微/飞书
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

中国企业市场的 Claude Managed Agents 替代方案：不拼模型能力，拼企业级合规和采购体验。

### 四大差异化优势

1. **内网/VPC**：切中企业对数据不出域的核心合规要求，支持 VPC 体系（需配置穿透/白名单）
2. **SSO（含 AAD）**：无影体系已有成熟 AD/AD FS/Azure AD SSO 能力，是企业采购的"门票"
3. **可审计**：全链路追踪（执行轨迹+资源调用），支持操作日志回溯、人工介入/回滚
4. **只为 Session 执行收费**：不跑不收钱，算力+Token 透明拆分计费

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 模型能力 | 依赖百炼模型体系 | 与 Claude 系列模型能力有差距 |
| 内网配置 | 需手动配置穿透/白名单 | 非开箱即用 |
| 公网 SaaS | 不支持（需 VPC） | 纯公网场景不如 Claude Managed Agents 简单 |

## 功能特性

| 维度 | JVS Crew |
|------|------|
| **架构** | 零代码角色设定+模型选择+技能参数 |
| **模型** | 百炼多模型体系（qwen3.7-plus 等） |
| **触发** | IM（钉钉/企微/飞书）、API、SDK |
| **调试** | 在线对话调试 + 全局运营看板 |
| **监控** | 全链路监控 + 运营指标看板 |

## 安全与审计

| 维度 | JVS Crew |
|------|------|
| **沙箱** | 会话级+资源级隔离（无影沙箱） |
| **凭证** | RBAC + Skill 全流程安全审核 |
| **网络** | 纵深防护+内容过滤+URL 拦截 |
| **审计** | 全链路追踪（执行轨迹+资源调用） |
| **SSO** | 支持钉钉/企微/飞书接入 + AD/AD FS/Azure AD |
| **内网** | 支持（VPC 体系，需配置穿透/白名单） |

## 计费模式

| 维度 | 详情 |
|------|------|
| **模式** | 纯后付费，按 Agent 请求消耗 |
| **Session** | 按小时结算，月末出账（仅 Running 时计费） |
| **Token** | 百炼模型标准费率 |
| **预充值** | 不需要 |
| **数据存储** | 邀测期免费 |

## 竞品快速对照

与 Claude Managed Agents 客观对比：

| 对比项 | 优势方 | 说明 |
|------|:---:|------|
| **模型能力** | Claude Managed Agents | Claude 系列行业第一梯队 |
| **企业身份集成（SSO/RBAC）** | JVS Crew | Claude 无 SSO/RBAC |
| **内网/VPC 支持** | JVS Crew | Claude 纯公网 SaaS |
| **沙箱技术透明度** | Claude Managed Agents | gVisor 实现更透明 |
| **凭证隔离** | Claude Managed Agents | Vault 机制更彻底 |
| **不可变审计日志** | Claude Managed Agents | 默认只读持久化日志 |
| **多渠道 IM 集成** | JVS Crew | IM+API+SDK 更灵活 |
| **计费模式** | 持平 | 都是按需后付费 |

> ⚠️ Claude Managed Agents 2026-04-08 刚发布公测，SSO/RBAC 等企业功能可能在路线图中，当前状态不代表最终能力。

## 参考资料

- [阿里云 JVS Crew 文档](https://help.aliyun.com/zh/document_detail/3029840.html)
- [JVS Crew 功能特性](https://help.aliyun.com/zh/document_detail/3029896.html)
- [JVS Crew 计费概述](https://help.aliyun.com/zh/document_detail/3029880.html)
- [无影 AgentBay 安全白皮书](https://help.aliyun.com/zh/agentbay/agentbay-security-white-paper)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-04-23 | 初始创建，基于 Claude Managed Agents vs JVS Crew 对比分析（2026-04-23） |
| 2026-06-09 | 修正：模型引用从 qwen3.6-plus 更新为 qwen3.7-plus |
