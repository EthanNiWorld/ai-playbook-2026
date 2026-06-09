# 阿里云"龙虾家族" AI Agent 产品全景

> 最后更新: 2026-05-27
> 所属厂商: 阿里云
> 产品类别: AI App
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 阿里云围绕 OpenClaw（开源 AI Agent 网关）构建的五款产品矩阵，覆盖从轻量个人 Agent 到企业多 Agent 协作、再到云端托管全栈
**适用**: 企业级 AI Agent 构建、多 Agent 协作、数据库 AI 操作、Agent 云端执行环境
**不适用**: 纯模型推理（无 Agent 编排需求）、对 OpenClaw 无依赖的自研 Agent 框架
**竞品**: Claude Managed Agents（Anthropic）、Copilot Studio（Microsoft）
**常搭配**: 百炼大模型（qwen3.7-plus / DeepSeek-V4）、无影 AgentBay、钉钉/飞书
<!-- SUMMARY_END -->

## 产品清单

| 产品 | 定位 | 层级 | 发布时间 | 性质 | 开发团队 |
|------|------|------|:---:|:---:|------|
| **HiClaw** | 多 Agent 协作框架 | 应用层 | 2026-02 | 开源 Apache 2.0 | 阿里 Higress 团队 |
| **QwenPaw**（原 CoPaw） | 轻量个人 Agent | 应用层 | 2026-02 | 开源 | 阿里 AgentScope 团队 |
| **百炼龙虾** | 云端 OpenClaw 托管 | 应用层（SaaS+） | ~2026 初 | 云服务（Coding Plan 附赠） | 阿里百炼团队 |
| **PolarClaw** | 企业级通用 AI 助理（数据库深度优化） | 应用层（PaaS） | 2025 | 云服务 | 阿里 PolarDB 团队 |
| **无影 AgentBay** | Agent 云基础设施 | 基础设施层 | 2025-07 | 云服务 | 阿里无影团队 |

## 与 OpenClaw 的关系

| 产品 | 与 OpenClaw 的关系 |
|------|------|
| **HiClaw** | 基于 OpenClaw 构建的架构升级分支（Team 版），由 Higress 团队开发 |
| **QwenPaw** | **不基于 OpenClaw 代码**，基于 AgentScope Runtime 自研，架构类似 OpenClaw |
| **百炼龙虾** | OpenClaw 原版云端官方托管，1:1 兼容 |
| **PolarClaw** | 基于 OpenClaw 构建的企业级 PaaS，兼容社区 Skills |
| **无影 AgentBay** | **无关**，是 Agent 执行基础设施（不是 Agent 应用） |

## 产品原理解析

### HiClaw

**一句话定位**：OpenClaw 的架构升级分支，开源多智能体协作系统，主打 Manager-Worker 两层多 Agent 架构

| 维度 | OpenClaw | HiClaw |
|------|:---:|:---:|
| 架构 | 单进程 | 分布式容器底座 |
| 智能体模式 | 单 Agent | Manager-Worker 两层多 Agent |
| 安全 | 手动管理凭证 | 零凭证架构，Agent 不接触真实 API Key |
| 监控 | 无内置 | 内置心跳监控 |

**核心能力**：多 Agent 并行任务拆解执行、企业级安全（消费级令牌隔离）、零配置移动端接入

### QwenPaw（原 CoPaw）

**一句话定位**：150MB 超低内存轻量 Agent，基于 AgentScope Runtime，与 HiClaw 搭配使用

**关键特征**：
- 不基于 OpenClaw 代码（常见误解），基于 AgentScope 框架
- 超低内存（150MB），无需 Node.js
- 内置心跳监控，支持自动重启
- 数据本地存储，隐私可控

### 百炼龙虾

**一句话定位**：OpenClaw 原版的云端官方托管，1:1 兼容 OpenClaw Skills 生态

**特征**：含 Coding Plan Pro 订阅方案中，故障自愈托管，无需自运维；支持钉钉/飞书接入

### PolarClaw

**一句话定位**：通用 AI 助理平台 + PolarDB 数据库深度优化的 PaaS 服务

**常见误解**：PolarClaw 不只是数据库工具，而是通用 AI 助理平台，在数据库场景上有独特深度优化：
- **通用能力**（继承 OpenClaw）：办公自动化、邮件、日程、文件处理，多渠道接入
- **数据库增强**（差异化）：PolarDB 深度集成，AI 直接操作数据库（智能查询、SQL 生成、性能调优、Supabase 管理）

**SLA**：99.99%（全托管）；安全：VM 级隔离

### 无影 AgentBay

**一句话定位**：Agent 的"云电脑"执行环境，提供安全沙箱隔离的多种 Agent 运行时

**关键定位区分**：
- HiClaw/PolarClaw/百炼龙虾 = **Agent 应用层**（做什么事的 Agent）
- 无影 AgentBay = **Agent 基础设施层**（Agent 在哪里运行）

**运行时类型**：浏览器、云电脑、代码空间、云手机  
**定价**：免费起步，¥189/月起  
**SLA**：99.97%；安全：沙箱隔离+黑白名单+AD/AD FS/Azure AD SSO

## 综合对比

| 维度 | HiClaw | QwenPaw | 百炼龙虾 | PolarClaw | 无影 AgentBay |
|------|:---:|:---:|:---:|:---:|:---:|
| **核心优势** | Manager-Worker 多 Agent 协作 | 150MB 超低内存，无需 Node.js | 一键部署+故障自愈 | 通用 Skills + PolarDB 深度集成 | 多模态沙箱隔离 |
| **定价** | 免费+ECS 费用 | 免费+部署资源费 | 含 Coding Plan Pro | 含 PolarDB 中 | 免费+¥189/月起 |
| **运维** | 客户自运维 | 客户自部署+内置心跳 | 阿里云托管+故障自愈 | 阿里云全托管 | 阿里云全托管 |
| **SLA** | 无 | 无 | 未公开 | 99.99% | 99.97% |
| **安全** | 零凭证架构 | 数据本地存储 | 风险检测+密钥鉴权 | VM 级隔离 | 沙箱+黑白名单 |
| **SSO/AD** | 不支持 | 钉钉/飞书/QQ（通讯通道） | 钉钉/飞书 | 钉钉/飞书 | AD/AD FS/Azure AD |

## 适用场景

### ✅ 适用场景

| 场景 | 推荐产品 | 说明 |
|------|----------|------|
| 想体验 OpenClaw 原版 | 百炼龙虾 | 云端托管，1:1 兼容 |
| 多 Agent 协作、企业级安全 | HiClaw | Manager-Worker 架构，零凭证安全 |
| 数据库 AI 化操作 | PolarClaw | PolarDB 深度集成 |
| 超低内存、轻量场景 | QwenPaw | 与 HiClaw 搭配降低内存占用 |
| 为 Agent 提供云端执行环境 | 无影 AgentBay | 沙箱隔离运行时 |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| HiClaw 是 CoPaw（QwenPaw）的企业版 | 两者是并列关系，HiClaw 基于 OpenClaw，QwenPaw 基于 AgentScope |
| QwenPaw 基于 OpenClaw 代码 | QwenPaw 基于 AgentScope Runtime，不基于 OpenClaw |
| PolarClaw 只是数据库工具 | PolarClaw 是通用 AI 助理 + 数据库深度优化 |
| "QwenClaw" 是独立产品 | QwenClaw 不是官方产品名，是社区俗称 |
| HiClaw 是火山引擎产品 | HiClaw 是阿里 Higress 团队开源项目 |

## 底座模型选型建议

龙虾家族默认搭配百炼 qwen3.7-plus，但在**多 Agent 协作 / 复杂 Agentic Coding** 场景下，DeepSeek-V4 是值得评估的另一个选项。

### DeepSeek V4 作为底座的依据

DeepSeek 官方发布页明确点名 OpenClaw 集成：

> *"DeepSeek-V4 is seamlessly integrated with leading AI agents like Claude Code, **OpenClaw** & OpenCode."*  
> — https://api-docs.deepseek.com/news/news260424

这意味着 V4 在设计阶段就以 OpenClaw 为集成目标，并非事后适配。

### V4 vs V3.2：龙虾场景下的关键差异

| 能力项 | V3.2 | V4-Pro | 对龙虾场景的意义 |
|------|:---:|:---:|------|
| 跨 user turn 推理保留 | ✘ 新 user message 清空 | ✔ 含工具调用场景保留 | HiClaw Manager-Worker 多轮调度不丢失状态 |
| 工具调用格式 | JSON-in-string | `\|DSML\|` + XML schema | OpenClaw Skills function call 解析错误率下降 |
| 1M 上下文 FLOPs | 100% 基准 | 27% | 长 Agent 链路推理成本下降 |
| KV Cache | 100% 基准 | 10% | 多 Agent 并发记忆压力减小 |
| Agentic Coding（SWE Verified）| 未专项标注 | 80.6（近 Opus 4.6-Max 80.8）| PolarClaw SQL 生成 / 代码调优任务准确率提升 |

### 各产品底座选型建议

| 龙虾产品 | 场景特征 | 底座选型建议 |
|------|------|------|
| **HiClaw**（Manager-Worker 多 Agent）| 多轮任务拆解 + 跨并发 worker 调度，跨 turn 推理要求高 | 优先 V4；V3.2 仅适合单轮任务 |
| **百炼龙虾**（OpenClaw 原版托管）| 官方金标准集成路径 | V4 官方点名 OpenClaw，默认选 V4 |
| **PolarClaw**（数据库 + 通用 AI 助理）| SQL 生成 / 调优是 Agentic Coding 子集 | V4-Pro（SWE Verified 80.6，内部 R&D Coding 67% > Sonnet 4.5 的 47%）|
| **QwenPaw**（150MB 超轻量）| 个人设备低资源场景 | 与底座模型解耦，调用远端 API；V4-Flash 更经济 |
| **无影 AgentBay**（基础设施层）| 仅提供运行环境 | 与底座模型选型无关 |

### 未解决问题

- **百炼上架状态**：DeepSeek-V4 是否已在百炼平台上架、可否作为龙虾家族底座切换 — 待查 [⚠️ 待验证]
- **Function call 格式兼容性**：OpenClaw Skills 默认 JSON 格式与 V4 DSML XML 格式的适配层实现 — 待查 [⚠️ 待验证]
- **许可与计费路径**：V4 在龙虾产品中是合同内额度调用还是需要额外计费 — 待查 [⚠️ 待验证]

## 参考资料

- [阿里云 HiClaw 文档](https://help.aliyun.com/zh/model-studio/hiclaw)
- [GitHub HiClaw Issue #52](https://github.com/agentscope-ai/HiClaw/issues/52)（HiClaw vs CoPaw 关系核实）
- [InfoQ：QwenPaw 基于 AgentScope](https://www.infoq.cn/article/Z8OmAd2YjFBlxaA0yfij)
- [新浪财经：QwenPaw 改名来源](https://finance.sina.com.cn/tech/digi/2026-04-12/doc-inhufzfw3074234.shtml)
- [阿里云百炼龙虾文档](https://help.aliyun.com/zh/model-studio/model-studio-claw)
- [PolarClaw 文档](https://help.aliyun.com/zh/polardb/polardb-for-mysql/polarclaw/)
- [无影 AgentBay 产品页](https://www.aliyun.com/product/agentbay)
- [无影 AgentBay 安全白皮书](https://help.aliyun.com/zh/agentbay/agentbay-security-white-paper)
- [DeepSeek-V4 官方发布页](https://api-docs.deepseek.com/news/news260424) — V4 与 OpenClaw 集成说明
- [HuggingFace DeepSeek-V4 技术分析](https://huggingface.co/blog/deepseekv4) — V3.2 跨 turn 推理缺陷与 V4 修复

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-04-23 | 初始创建，基于 龙虾家族产品分析对话记录（2026-04-23） |
| 2026-05-27 | 合并 ai-native-expert 沉淀：新增「底座模型选型建议」章节，含 DeepSeek V4 vs V3.2 在龙虾场景下的关键差异与各产品选型推荐 |
| 2026-06-09 | 修正：常搭配底座模型从 qwen3.6-plus 更新为 qwen3.7-plus |
