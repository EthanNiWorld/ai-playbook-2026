# Harness（AI Agent 缰绳）

> 最后更新: 2026-06-09
> 领域: AI Engineering
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: Harness 是 Agent 的约束+治理层，定义 Agent 能做什么、不能做什么、何时需要人工介入；同时也覆盖调用层可靠性工程（多账号路由、限流熔断、连接池）
**核心价值**: 模型是同质化 commodity，Harness 是真正的差异化竞争护城河；Harness Engineering 已成行业正式工程方法论（Anthropic/OpenAI/Hashimoto 共同验证）；Model-Harness 协同演进是下一层竞争前沿
**相关产品**: [HiClaw/龙虾家族](../../alibaba-ai-hub/ai-application/claw-family.md), [JVS Crew](../../alibaba-ai-hub/ai-application/jvs-crew.md)
<!-- SUMMARY_END -->

## 是什么

**Harness** 是骑马时的"缰绳+鞍具"——它不是马（模型），但没有它，马（模型）跑不受控。

在 AI Agent 语境里，Harness 是围绕模型构建的治理层，包括：
- **工具权限边界**：Agent 能调用哪些工具、不能调哪些
- **业务规则约束**：什么情况下必须停止、必须转人工
- **人工介入点（Human-in-the-loop）**：关键决策节点强制人工确认
- **监控与审计**：每步行动的可观测性、日志、回滚能力
- **安全凭证隔离**：Agent 执行节点不接触真实 API Key

### 公式演进：Agent = Model + Harness

| 时间 | 事件 | 贡献 |
|------|------|------|
| 2025-11 | **Anthropic** 发布《Effective harnesses for long-running agents》，首次在官方资料中将 Agent Harness 作为核心概念 | 概念起点，行业头部厂商背书 |
| 2026-02 | **Mitchell Hashimoto**（HashiCorp 联合创始人）在《My AI Adoption Journey》中正式倡导 **Harness Engineering**——Agent 犯错时应优化 Harness（运行环境），而非仅修改 Prompt | 概念升级为工程方法论 |
| 2026-02 | **OpenAI** 发布《Harness engineering: leveraging Codex in an agent-first world》，三工程师通过 Harness 生成百万行代码 | 规模化实证验证 |
| 2026-03 | **LangChain**（Vivek Trivedy）发布《The Anatomy of an Agent Harness》，明确提炼 `Agent = Model + Harness` 公式并系统化阐述 Harness 构成组件 | 公式正式定义并广泛传播 |
| 2026-05 | **DeepSeek** 在官方 JD 中直接使用 Model + Harness = Agent 公式，设立专职 Harness 团队 | 公式被模型厂商内化为产品战略 |

> 传播链路：Anthropic 概念起点（2025-11）→ Hashimoto/OpenAI 方法论升级（2026-02）→ LangChain 公式定义（2026-03）→ DeepSeek 战略化（2026-05）——半年内完成从「行业概念」到「厂商战略」的全链路传导。

## 核心原理

### 为什么 Harness 是企业战略级资产

**第一性原理推导**：

1. 大模型正在快速同质化（Claude / GPT / Qwen 能力差距收窄）
2. 但行业 Harness 是非标的——每个行业的业务流程、合规要求、风险边界完全不同
3. 构建行业 Harness 需要**深度的领域业务理解**（不是工程问题，是业务知识问题）
4. 因此：**谁先把行业 Harness 做深，谁就有护城河**

> 公司 A 和公司 B 用同一个模型，接不同的 Harness，出来的产品能力天差地别。Harness 是能力放大器，也是风险防护盾。

### Harness 的构成维度

| 维度 | 含义 | 工程实现 |
|------|------|---------|
| **工具边界** | Agent 可以调用什么，不可以调用什么 | 工具白名单、参数校验 |
| **业务规则** | 什么条件下执行什么操作 | 规则引擎、Prompt 约束 |
| **人工介入点** | 哪些步骤必须人确认才能继续 | HITL（Human-in-the-Loop）设计 |
| **凭证隔离** | Agent 不直接持有生产凭证 | Vault 机制、令牌代理 |
| **审计追踪** | 每步行动都可追溯、可回滚 | 不可变日志、操作快照 |
| **退出条件** | 硬性终止：超时、最大步数、异常 | 守卫条件（Guard Rails） |

## 关键选型维度

| 维度 | 轻量 Harness | 企业级 Harness | 怎么选 |
|------|------------|--------------|--------|
| 适用场景 | 个人/开发者工具 | 政企/金融/医疗等高合规行业 | 风险等级和合规要求 |
| 人工介入 | 无/最小 | 关键节点强制审批 | 是否有不可逆操作 |
| 凭证管理 | 环境变量 | Vault/密钥管理服务 | 生产环境必须隔离 |
| 审计要求 | 无 | 不可变日志+全链路追踪 | 监管/合规要求 |
| 典型产品 | QwenPaw、百炼龙虾 | JVS Crew、Claude Managed Agents | 参见产品文档 |

## 各厂商实现对照

| Harness 能力 | 阿里云 JVS Crew | Anthropic Claude Managed Agents | 开源方案 |
|-------------|---------------|---------------------------------|---------|
| 工具权限控制 | RBAC + Skill 审核 | 工具白名单 | LangGraph 条件边 |
| 凭证隔离 | RBAC + 无影沙箱 | Vault 机制（更彻底） | 需自建 |
| 人工介入 | 全链路追踪+可回滚 | 未明确支持 | HITL 框架 |
| 审计日志 | 全链路追踪 | 只读持久化（不可变，更强） | 需自建 |
| 企业 SSO | 支持 AAD | 暂不支持（2026-04公测） | 需自建 |
| 网络隔离 | VPC 内网支持 | 纯公网 SaaS | 自托管 |

## 最佳实践

### 行业 Harness 构建路径

1. **业务流程梳理**：把行业核心业务流程文档化——这是 Harness 的"输入材料"
2. **风险边界定义**：明确哪些操作绝对不能自动执行（资金操作、删除操作等）
3. **分层权限设计**：只读操作 > 写操作 > 删除操作，分三级权限，从最小权限开始开放
4. **HITL 节点设计**：每个关键决策点，预设人工确认触发条件
5. **审计先行**：在实现功能前先把审计日志基础设施搭好

### Harness vs Prompt 的区别

很多人把"更好的 Prompt"当 Harness——这是最常见的误解：

| 对比项 | Prompt | Harness |
|--------|--------|---------|
| 约束层级 | 软约束（模型可能忽略） | 硬约束（代码层面强制执行） |
| 覆盖范围 | 模型行为 | 系统整体行为（含工具、权限、审计） |
| 可审计性 | 无 | 有（每步可追溯） |
| 可靠性 | 依赖模型遵从 | 不依赖模型遵从 |

## 常见误区

| 误区 | 事实 |
|------|------|
| "把规则写进 Prompt 就是 Harness" | Prompt 是软约束，Harness 是系统层面的硬约束，两者不可替代 |
| "Harness 通用化就能复用" | Harness 越通用越没价值，行业特异性才是护城河所在 |
| "强模型不需要 Harness" | 模型越强越需要 Harness——能力越大，失控的后果越严重 |

## Model-Harness 协同演进：各厂商策略对比

Harness 的战略价值不仅在于治理层设计，更在于 **Model 与 Harness 能否联合设计**。各厂商策略差异显著：

| 厂商 | Model-Harness 关系 | 特点 |
|------|-------------------|------|
| **Anthropic** | 深度协同（Claude Code 与 Claude 模型联合设计） | 模型团队和产品团队紧密耦合 |
| **OpenAI** | 协同（Codex 与 GPT 系列联合优化） | Codex CLI 开源，产品层分离 |
| **第三方 Harness**（如 DeepSeek-TUI） | 纯接入（只能用 API，无法影响模型） | 只能在模型之上做工程 |
| **DeepSeek**（2026-05 起） | 明确追求深度协同，Harness 团队可反向影响模型训练方向 | 模型和产品联合设计 |

**核心洞察**：当模型能力趋同时（V4 ≈ Claude ≈ GPT），竞争壁垒从「谁模型强」转移到「谁的 Harness 好」——评估任何 AI Agent 产品，要看 Harness 质量（工具权限设计、上下文管理策略、HITL 机制、错误恢复能力），而非仅看所用模型。同一模型接不同 Harness，产品体验可差一个数量级。

## 调用层 Harness：容量与限流治理

除了权限与审计，Harness 还覆盖「调用层可靠性」：如何在云厂商 RPM/TPM 限流下保证吞吐与稳定性。这是 Agent 产品从 demo 到生产的必经之路。

### 多账号扩限流模式及其隐性拖点

**现象**：云厂商 MaaS 平台（百炼、Bedrock、Vertex AI）的限流颗粒度是**账号（UID）**，不是 API Key。同一账号下创建 N 个 Key 不会扩额，但 N 个独立账号可以获得 N 倍额度。

**为什么云厂商按 UID 限流（第一性原理）**：
1. **计费锰点**：UID 是云平台最小计费单元，限流 = 计费 = 额度 = 欠费控制，天然绑定
2. **防绕过**：若按 API Key 限流，单账号创建大量 RAM 用户即可无限扩展，限流实质上失效
3. **平台惯例**：所有云产品的配额管理都以账号为最小隔离域

**架构茂**：

```
业务应用 / Agent
        │
        ▼
  账号调度层（Harness）
  ├─ 账号池（N 个独立 UID）
  ├─ 加权轮询／最少负载调度
  ├─ 429 检测 → 账号熔断 60-70s
  ├─ 独立 httpx 连接池 + client 复用
  └─ 降级策略（备用模型 / Batch API）
```

### 客户端拥塞拐点（隐性瓶颈）

**反直觉发现**：多账号方案的真正瓶颈往往不是云厂商限流，而是客户端拥塞拐点。

**典型表现**（以某推理模型压测为例，思考模式平均延迟 7-12s）：

| 并发 | 60s 窗口 TPM | 429 限流 | 客户端错误 | 现象 |
|----:|------------:|--------:|----------:|------|
| 80 | 173K | 0 | 0 | 客户端未饱和 |
| **200** | **876K** | 0 | 25 | ✅ 单账号甜点 |
| 500 | 217K | 1,449 | 5,486 | ❌ 客户端自我攻击 |

**为什么高并发反而低 TPM**：
- 超过服务端 RPM 软限后，429 雪崩触发重试风暴
- 客户端 socket / TLS / CPU 资源被重试请求挤占
- 有效请求与重试请求互相坍陆→ 吞吐反向崩塌（**自我 DDoS 效应**）

**正确姿势**：
1. 先找到单账号的客户端甜点（本例 200 并发）
2. N 账号场景把总并发控制在 N × 单账号甜点（本例 250×2=500）
3. 必须复用 HTTP client + 调大 httpx 连接池（max_connections ≥ 600）+ 各账号独立 client 实例
4. 触发 429 立即熔断换账号，不要 sleep 后重试同账号

**实测验证（同 500 总并发）**：

| 指标 | 单账号 500 并发 | 双账号 250×2 | 倍数 |
|------|---------------:|-----------:|----:|
| 429 限流 | 1,449 | **0** | 完全消除 |
| 60s 窗口 TPM | 217K | **1,840K** | ×8.5 |
| 平均延迟 | 12.0s | 9.3s | ⬇️ 22% |

### 云厂商限流文档与实测差异

**发现**：云厂商发布的 RPM/TPM 数字往往是「理论上限」，实测会打折扣。以某思考模型为例：
- 文档：RPM = 15,000
- 实测：成功 RPM ~300-500，到达服务端 RPM ~1,500（含 429）——实际软限可能仅为文档值的 1/30

**原因推测**：
- 思考模型算力消耗高，服务端可能设置了比文档更严的软限制
- 账号等级、地域、突发流量保护都会叠加打折
- 文档公布值可能是「申请提额后可达上限」，默认额度远低于此

**推荐做法**：生产部署前必须用与生产场景一致的负载（模型+并发+消息长度）跑一次端到端压测，把限流真值测出来再做容量规划。

### 判断框架：什么时候该上多账号

| 场景 | 首选方案 | 原因 |
|------|---------|------|
| 偶尔超额 | 官方提额 | 运维成本最低 |
| 稳定高并发 | 多账号池化 | 提额存在上限，多账号可线性扩展 |
| 离线批处理 | Batch API | 不受实时限流，成本更低 |
| 超高吞吐+低延迟 | 自托管 GPU 集群 | 多账号运维成本超过自建 |

**三者起手成本对比**（模型存在多个文档额度环境下）：官方提额 ≪ 多账号池化 ≪ 自建 GPU 集群。

## 参考资料

- 来源于 2026-04-23 龙虾家族产品分析沟通（HiClaw 分享观点：Harness 是企业战略级资产）
- [JVS Crew 安全文档](https://help.aliyun.com/zh/document_detail/3029896.html)
- [Pluto Security：Claude Managed Agents 安全分析](https://pluto.security/blog/securing-claude-managed-agents/)
- 2026-05-22 多账号 TPM 压测实践（参考实现脚本）
- [百炼限流文档](https://www.alibabacloud.com/help/en/model-studio/rate-limit)
- [Anthropic《Effective harnesses for long-running agents》](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)（2025-11）
- [Mitchell Hashimoto《My AI Adoption Journey》](https://mitchellh.com/writing/my-ai-adoption-journey)（2026-02）
- [OpenAI《Harness engineering: leveraging Codex in an agent-first world》](https://openai.com/index/harness-engineering-leveraging-codex/)（2026-02）
- [LangChain《The Anatomy of an Agent Harness》](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness)（2026-03）
- [36氪：DeepSeek 智能体产品要来了](https://eu.36kr.com/en/p/3818407956366208)
- [Verdent AI：DeepSeek's Coding Plan: V4, Harness Team, and 2026 Roadmap](https://www.verdent.ai/zh-CN/guides/deepseek-coding-plan-2026)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-04-23 | 初始创建（修复原错误内容——原文是 RAG 模板复制残留），基于龙虾家族对话洞察：Harness 是企业战略级资产、Harness vs Prompt 区别 |
| 2026-05-22 | 新增「调用层 Harness：容量与限流治理」主章节：多账号扩限流模式、客户端拥塞拐点（200 并发甜点 vs 500 并发自我 DDoS）、云厂商限流文档与实测差异、多账号 vs 提额 vs 自托管决策框架。来源：某推理模型双 UID 压测实践（8.5× TPM 提升、零限流验证） |
| 2026-06-09 | 新增：公式演进（Anthropic→Hashimoto→OpenAI→LangChain→DeepSeek 传播史）、Model-Harness 协同演进厂商对比（含 DeepSeek Harness 团队战略视角）。来源：inbox/ai-knowledge-by-qoder-ai-native-agent-20260609.md（36氪、Verdent AI、Anthropic、Hashimoto、OpenAI、LangChain 原文交叉验证） |
