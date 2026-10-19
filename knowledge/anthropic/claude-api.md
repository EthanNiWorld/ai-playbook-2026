# Anthropic Claude 模型

> 最后更新: 2026-10-19
> 所属厂商: Anthropic
> 产品类别: MaaS
> 状态: Published

> **定位**: Anthropic 旗舰模型系列，强调 Constitutional AI 安全对齐、长文本理解与高精度推理
**最高能力档**: Claude Fable 5.1（Fable 线小版本更新，$10/$50 同价；AA 指数 65.7、HLE 65.0%——2026-09 AA v4.1.1 口径）
**主力推荐**: Claude Opus 5.5（2026.09.22，$4/$20，比 Opus 5 降 20%；TB 4.0 66.4%、AA 指数 58 为当前独立榜第一）
**均衡档**: Claude Sonnet 5.5（2026.09.28，$2/$10，cache 读减半）
**轻量档**: Claude Haiku 5.5（2026.10.07，1M 上下文，Claude 系首个按上下文长度分层定价 $0.10/$0.50）
**适用**: 高精度推理、复杂长文本分析、代码生成、企业级 Agent、合规要求高场景、高并发轻量任务（Haiku 5.5）
**不适用**: 渗透测试 / exploit 生成 / 二进制漏洞扫描类请求；>100K 长上下文高并发任务（Haiku 5.5 长段溢价 5×，建议对比 GPT-6 Luna）

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Claude Fable 5.1** 🚩 | **最高能力档**（Fable 线小版本更新） | [⚠️ 待补充] | $10/$50 同价；AA 指数 65.7 / HLE 65.0%（Vellum/AA 榜单口径） | [⚠️ 待补充] |
| **Claude Opus 5.5** ⭐ | **主力推荐**（新旗舰） | [⚠️ 待补充] | $4/$20（比 Opus 5 -20%）；TB 4.0 66.4%、AA 指数 58（独立榜第一）；与 Gemini 4 Argon 标准价同价 | 2026.09.22 |
| **Claude Sonnet 5.5** | 均衡档（Sonnet 线当前主推） | [⚠️ 待补充] | $2/$10（低于 Sonnet 5 标准价 $3/$15）；cache 读减半（agentic -20%）；TB 4.0 70.6%、AA 指数 56 | 2026.09.28 |
| **Claude Haiku 5.5** | 轻量/高并发（Haiku 线当前主推） | **1M** | 首个按上下文长度分层定价：$0.10/$0.50（≤100K）；128K 输出；effort 五档；computer use / browser use beta | 2026.10.07 |

> 📌 **限制访问模型**：**Claude Mythos 5**（2026.06.09）与 Fable 5 同底座、同定价、同 API 行为，仅去除网络安全限制，**仅通过 Project Glasswing** 向美国政府网络防御者与关键基础设施提供商开放；非参与组织请用 Fable 5。详见下文专章。

> 📌 **历史模型**（仍可调用，不建议新项目选用）：**Opus 5**（2026.07.24，已被 Opus 5.5 取代）/ **Sonnet 5**（2026.06.30，已被 Sonnet 5.5 取代）/ **Fable 5**（2026.06.09，Fable 线已迭代至 5.1）/ **Haiku 4.5**（已被 Haiku 5.5 取代）/ **Opus 4.8**（2026.05.28）/ **Opus 4.7**（2026.04.16）/ **Opus 4.6** / **Sonnet 4.6**。**Opus 4.1 已废弃，2026-08-05 退役**。

### Claude Opus 5.5 与 Claude 5.5 家族刷新（2026.09-10）

> 来源：[Opus 5.5 官方公告](https://www.anthropic.com/claude-opus-5-5)（2026-09-22）、[Sonnet 5.5 官方公告](https://www.anthropic.com/claude-sonnet-5-5)（2026-09-28）；2026-10-09 合并入库

**家族代际**：Claude 5（Fable 5 / Opus 5 / Sonnet 5，2026.06-07）→ **Claude 5.5（2026.09-10，全系降价）**：Opus 5.5（09-22）→ Sonnet 5.5（09-28）→ Haiku 5.5（10-07，见下文专章）。Opus 5.5 与 OpenAI GPT-6 Sol/Luna（09-22）同日贴身发布，Opus 5.5 抢先约 90 分钟上线。

**Claude Opus 5.5**（2026-09-22）：
- 定价 **$4/$20**（比 Opus 5 的 $5/$25 降 20%；与 Gemini 4 Argon 标准价同价）
- 关键评测（第三方/竞对发布会口径）：Terminal-Bench 4.0 **66.4%**（领先 Gemini 4 Argon 57.4%）、DeepSWE v1.1 74.2%、AutomationBench 42.5%、Harvey Legal Agent 3.8%、Gray Swan IPI 攻击成功率 1.0%；AA Intelligence Index **58，当前独立榜第一**（Sonnet 5.5 56 次之）；AA 实测 $5.98/task、max effort 平均 $23.21/task（GPT-6.1 Sol 对比口径）
- 其余规格（上下文窗口、最大输出等）：[⚠️ 待补充——素材未提供]

**Claude Sonnet 5.5**（2026-09-28）：
- 定价 **$2/$10**（低于 Sonnet 5 标准价 $3/$15）；**cache 读减半（$0.20→$0.10），agentic 任务成本 -20%**
- Terminal-Bench 4.0 **70.6%**（领先 Haiku 5.5 的 39.2%——复杂 agentic coding 仍是 Sonnet/Opus 首选）；GDPval-AA v2.1 1840；AA 指数 56
- 其余规格：[⚠️ 待补充——素材未提供]

**家族级成本攻势**（同期）：Max/Team 订阅月度 API credits——Max 5x $100 / Max 20x $200 / Team 至 $500（不滚存），等于订阅费全额返还 API 额度（来源：Simon Willison 实测）。

**Fable 线补录**：**Claude Fable 5.1**——Fable 线小版本更新，$10/$50 同价；AA 指数 65.7、HLE 65.0%（2026-09 AA v4.1.1 口径，Astra 发布时领先 Astra 61.2 / Opus 5 63.1 / Fable 5 62.1；⚠️ 2026-10 最新口径下 Fable 5.1 为 53，AA 指数随新模型发布重新校准，跨时间引用需注明口径）。发布时间 [⚠️ 待补充]。

---

### Claude Opus 5（历史，2026.07.24）

- **模型 ID**：`claude-opus-5`；**1M 上下文 / 128K 输出**；定价 **$5/$25**（Fast mode $10/$50，约 2.5× 速度）；Claude Max 默认模型
- **定位**：接近 Fable 5 的前沿智能、价格腰斩、无数据留存要求（Fable 5 强制 30 天且不可 ZDR）
- **关键表现（官方仅给相对表述，未公布绝对分数）**：Frontier-Bench 超 Opus 4.8 翻倍以上且单任务成本更低；CursorBench 3.2 距 Fable 5 峰值 0.5% 内、成本一半；ARC-AGI 3 约为次优模型 3 倍；OSWorld 2.0 以约 1/3 成本超过 Fable 5
- **行为特征**：核心改进是「自我验证 + 反复迭代直到成功」——会自建工具与测试 harness 校验结果（如自写视觉流水线从图纸像素重建零件），而非单纯分数提升
- **护栏**：从「按领域封禁」改为「按任务阶段切分」（源码漏洞发现✅ / 二进制扫描、渗透、exploit 生成❌），分类器触发率较 Fable 5 低约 85%；详见 [安全护栏粒度](../ai-general-notes/safety-guardrail-granularity.md)
- **状态**：已被 **Opus 5.5**（2026.09.22，$4/$20，再降 20%）取代

---

### Claude Fable 5（历史，2026.06.09）

- **模型 ID**：`claude-fable-5`；**1M 上下文 / 128K 输出**；定价 **$10/$50**（cache write $12.50 / read $1.00）
- **定位**：Mythos-class 首个公开版本，介于 Opus 4.8 与限制级 Mythos 5 之间
- **关键基准**：SWE-Bench Pro **80.3%**（+11.1pp vs Opus 4.8 69.2%）、FrontierCode Diamond 29.3%、GDP.pdf 29.8%
- **核心能力**：长程 Agent 可连续工作数天（Stripe 用 1 天完成原本需 2 个月的 50M 行 Ruby 迁移）；主动自验证（写测试校验自己代码、用 Vision 比对设计稿、进展汇报前强制审计工具结果）；可靠派遣并行子 Agent；视觉 SOTA（截图重建 web app、仅凭原始截图通关 Pokémon FireRed）
- **代价**：约 <5% 会话因 cyber / 生物 / 蒸馏查询被自动降级到 Opus 4.8 代答——此类公开分数等于 Opus 4.8
- **状态**：Fable 线已迭代至 **Fable 5.1**（当前最高能力档，$10/$50）

---

### Claude Mythos 5（限制访问，2026.06.09）

- **模型 ID**：`claude-mythos-5`；**1M 上下文 / 128K 输出**；定价 **$10/$50**（与 Fable 5 相同）
- **定位**：Fable 5 同底座但**去除网络安全限制**；仅通过 Project Glasswing 向美国政府网络防御者与关键基础设施提供商开放，非参与组织请用 Fable 线
- **合规**：Mythos-class 流量须 30 天数据留存 + 人工访问日志 + 自动删除；不用于训练
- **关键基准（竞争情报价值）**：

| 基准 | Mythos 5 | Fable 5（降级后） | Opus 4.8 |
|------|----------|-----------------|----------|
| ExploitBench | **78.0%** | 40.0% | 40.0% |
| BioMysteryBench | **46.1%** | 40.0% | 40.0% |
| SWE-Bench Pro | **80.3%** | 80.3% | 69.2% |

> 意义：ExploitBench 78% vs 公开模型 40% 的双倍差距，说明「漏洞发现」与「武器化 exploit 开发」是两种能力，公开模型的护栏卡在后者；详见 [安全护栏粒度](../ai-general-notes/safety-guardrail-granularity.md)。

---

### Claude Opus 4.x 世系（历史：4.7 / 4.8）

| 版本 | 时间 | 定价 | 关键基准 | 一句话定位 |
|------|------|------|----------|-----------|
| **Opus 4.8** | 2026.05.28 | $5/$25（Fast $10/$50） | SWE-Bench Pro 69.2%、SWE-Bench Verified 88.6%、Terminal-Bench 2.1 74.6%、HLE w/tools 57.9%、OSWorld-Verified 83.4%、GDPval-AA 1,890 | 诚实度 4× 提升（漏报缺陷率降至 1/4）、动态工作流与 parallel subagents |
| **Opus 4.7** | 2026.04.16 | 同价 | SWE-Bench Pro 64.3%、Terminal-Bench 2.1 66.1% | 视觉能力 3×，引入 xhigh 推理档与 Task Budgets |

> 📌 **版本节奏观察**：Opus 4.8 距 4.7 仅 **42 天**，为 Anthropic 史上最短 Opus 迭代间隔（此前约 70-75 天），动因是修复 4.7 的 comment-verbosity / tool-calling 一致性、以及用诚实度提升支撑 Agent 规模化。发布策略：Opus 先行 → Sonnet 1-4 周跟进 → Haiku 跳跃式更新。

### Claude Sonnet 5（历史，2026.06.30）

- **模型 ID**：`claude-sonnet-5`；**1M 上下文 / 128K 输出**；定价 **$2/$10**（introductory，至 2026-08-31）→ **$3/$15** 标准价
- **定位**：当时最 agentic 的 Sonnet——可制定计划、用浏览器与终端工具、自主运行；性能接近 Opus 4.8 而价格更低，Free / Pro 默认模型
- **能力**：agentic search（BrowseComp）与 computer use（OSWorld-Verified）对 Sonnet 4.6 为严格改进；medium effort 成本效率显著，高 effort 可追平 Opus 4.8
- **⚠️ tokenizer 陷阱**：新 tokenizer 使同一输入映射为 **1.0–1.35× token**；官方称 introductory 定价是为迁移「大致成本中立」，转标准价后单价 +50% 叠加 token 量上浮，**实际账单涨幅高于单价涨幅**——这条认知对当前 5.5 家族同样适用
- **状态**：已被 **Sonnet 5.5**（2026.09.28，$2/$10，cache 读减半）取代

---

### Claude Haiku 5.5

> 来源：[Anthropic 官方公告](https://www.anthropic.com/claude-haiku-5-5)（2026-10-07）、[Haiku 5.5 System Card](https://www.anthropic.com/document/claude-haiku-5-5-system-card)、[Claude Platform 模型总览](https://platform.claude.com/docs/en/models/overview)、[Simon Willison 独立评测](https://simonwillison.net/2026/Oct/7/claude-haiku-5-5/)；2026-10-09 合并入库

- **模型 ID**：`claude-haiku-5-5`
- **公司**：Anthropic
- **时间**：2026 年 10 月 7 日（Claude 5.5 家族最后成员；Opus 5.5 09-22、Sonnet 5.5 09-28）
- **上下文**：**1M tokens**（Haiku 4.5 为 200K，5×），最大输出 **128K tokens**（上代 64K）
- **知识截止**：2026-06（System Card）；输入：文本 + 图像
- **定位**：官方 tagline "Our fastest, cheapest, and most capable small model yet"——高并发成本敏感任务（摘要/压缩/数据库查询/分类）、Opus/Sonnet 5.5 的编码 subagent、速度敏感场景（实时客服、browser use / computer use，Python/TS SDK 同日新增两能力 beta）
- **推理**：Adaptive thinking 强制开启（**不可禁用推理**）；**首个支持可调 effort 的 Haiku**（low/medium/high/xhigh/max，默认 medium）；Batch 半价

#### 定价（按 prompt 长度分层，Claude 系首个）

| 项（$/1M tokens） | ≤100K tokens | >100K tokens | Haiku 4.5 对照 |
|---|---|---|---|
| 输入 | $0.10 | $0.50 | $1.00 |
| 输出 | $0.50 | $2.50 | $5.00 |
| Cache 读 | $0.01 | $0.05 | $0.10 |
| Cache 写 | $0.125 | $0.625 | $1.25 |

官方口径：≤100K 档比 Haiku 4.5 便宜 90%、>100K 便宜 50%、平均 ~75%（Haiku 4.5 的 90% 请求 ≤100K）。

#### 技术亮点与独创性

1. 🔧 **组合创新｜按上下文长度分层计价**：此前 Claude 4.6 以来所有模型全窗口单一费率，Haiku 5.5 首个引入分段（竞对 GPT-6 Luna 已先 2 周引入 272K 分段，Anthropic 将其做为主打定价架构）。本质：让价格贴成本曲线（长 prompt 的 KV cache/注意力服务成本更高），并在 ≤100K 段与 GPT-6 Luna 精确同价对位
2. 📋 **跟进对齐｜effort 五档下放 Haiku 线**：Opus/Sonnet、GPT-6 Sol（六档含 none）、Gemini thinking_level 均已先行；"不可禁用推理"意味着连小模型也默认是 reasoning model（行业新共识）
3. ⚙️ **工程优化**：1M 上下文 + 128K 输出下放小模型档；⚠️ **新 tokenizer 同任务 token 量 ~1.25×**（Simon Willison 实测，官方脚注承认）——标价降 90% 中含 ~25% 隐性回补，售前测算必须按"每任务实付"而非单价

#### 能力增强（vs 前代 Haiku 4.5 / GPT-6 Luna，官方表）

| 基准 | Haiku 5.5 | Haiku 4.5 | GPT-6 Luna |
|---|---|---|---|
| GDPval-AA v2.1 | **1620** | 735 | 1437 |
| AA-Briefcase v1.1 | **1578** | 614 | 1336 |
| HLE（no tools） | **45.9%** | 10.2% | — |
| HLE（with tools） | **57.4%** | 18.7% | — |
| OSWorld 2.1 offline | **72.4%** | 15.7% | 48.9% |
| Terminal-Bench 4.0 | **39.2%** | 0.0% | 16.4% |
| FrontierCode 1.1 Main | **46.4%** | — | 42.4% |
| Chartography | **46.4%** | 6.4% | 29.1% |

> 注：vs GPT-6 Luna 的分数为 Anthropic 官方口径，引用需注明。

- **存量变强**：摘要/分类/抽取质量达上代中档水平——HubSpot CRM 套件历史最高分 92.8%；AlphaSense 生产负载 8M calls/周，质量 0.84 vs 0.76
- **增量解锁**：①computer use / browser use 高并发 subagent（OSWorld 72.4% + 全家族最快速度，Asana 延迟 -30%、Box 延迟减半）②100K 内大文档压缩/摘要（1M 窗口 + $0.10 输入）③编码 sidekick（Cognition Devin Fusion 以其为 sidekick 保持 FrontierCode 66.2）
- **官方明确边界**：Sonnet/Opus 5.5 仍是复杂 agentic coding 首选（TB 4.0：Sonnet 5.5 70.6% vs Haiku 39.2%），Haiku 只做"窄范围、此前成本 prohibitive 的任务"
- **安全**：对齐评测大幅优于 Haiku 4.5；cyber 护栏比 Haiku 4.5 严、比其他新模型略松，允许的防御性 cyber 任务范围比 Sonnet 5.5 更宽，仍阻断渗透测试

#### 成本归因

- **定价策略降本为主**：无任何架构/技术报告公开（无 MoE/稀疏注意力披露）。90% 降幅主要来自：①分层定价贴成本曲线 ②tokenizer 换代（同任务 token +~25% 部分抵消降幅）③对位 GPT-6 Luna（09-22 先发 $0.10/$0.50）的防御性卡位——保住 Claude 生态高并发负载（Claude Code subagent、MCP 调用）不被路由到 OpenAI
- 架构内禀降本：无公开证据，官方仅称"性能与效率改进"——两种可能并存，官方未公开机制

---

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **高精度推理** | Constitutional AI 安全对齐，强调输出安全性与无害性 |
| **长上下文** | Fable 5.1 / Opus 5.5 / Sonnet 5.5 / Haiku 5.5 均为 1M tokens，标准 API 价格无长上下文附加费 |
| **代码生成** | Opus 5.5 TB 4.0 66.4%、AA 指数 58（独立榜第一）；Sonnet 5.5 TB 4.0 70.6%；Fable 5.1 AA 指数 65.7 |
| **多模态** | 支持图片等多模态输入；Haiku 5.5 支持 computer use / browser use beta |
| **Agent 能力** | Claude Code 编程 Agent；全系列支持 effort 阶梯调参与 adaptive thinking；Haiku 5.5 支持 effort 五档 |
| **安全对齐** | Constitutional AI 安全对齐；护栏从「按领域封禁」下沉到「按任务阶段切分」（详见 [安全护栏粒度](../ai-general-notes/safety-guardrail-granularity.md)） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 价格 | 分档 | Fable 5.1 $10/$50；Opus 5.5 $4/$20；Sonnet 5.5 $2/$10；Haiku 5.5 $0.10/$0.50（≤100K，>100K 段 $0.50/$2.50）；详见下方定价表 |
| 网络安全护栏 | 分类器拦截 | 渗透测试 / exploit 生成 / 二进制漏洞扫描被阻断；需降低护栏需申请 CVP |
| Fable 线数据留存 | 强制 30 天 | 不可用于 ZDR；Opus / Sonnet / Haiku 线无此限制 |
| Claude tokenizer | token 量 ×1.0–1.35 | 自 Opus 4.7 起引入，Sonnet 5 起明显；测算成本不可只看单价 |
| Anthropic 访问 | 需翻墙 | 国内无法直接访问 |
| 推理延迟 | 非极致优化 | 定位高精度，非超低延迟 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 日常主力 / 性价比最优 | **Opus 5.5** | $4/$20 新旗舰，TB 4.0 66.4%、AA 指数 58 独立榜第一 |
| 极限难度任务 | Fable 5.1 | 最高能力档 $10/$50，AA 指数 65.7（09 口径） |
| 大规模 Agent / 成本敏感 | **Sonnet 5.5** | $2/$10，cache 读减半（agentic -20%），TB 4.0 70.6% |
| 高并发摘要/压缩/subagent | **Haiku 5.5** | $0.10/$0.50（≤100K），同价档智力领先 GPT-6 Luna（详见[竞品对比](../../alibaba-ai-hub/competitive-analysis/haiku-vs-luna/overview.md)） |
| 长上下文高并发（>100K） | Haiku 5.5（>100K 段）或 GPT-6 Luna | Haiku >100K 涨 5×，性价比对比见竞品分析 |
| 需降低护栏的网络安全工作 | 申请 CVP（Cyber Verification Program） | 公开模型默认阻断渗透 / exploit / 二进制漏洞扫描；CVP 提供限制更少的版本 |
| 企业级合规（不接受数据留存） | Opus 5.5 / Sonnet 5.5 / Haiku 5.5 | Fable 线强制 30 天留存且不可用于 ZDR |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 预算敏感用户 | 价格较高 |
| 超高并发低成本 | 非性价比路线 |
| 国内直接访问 | 需翻墙 |

## 定价（API）

| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) | Prompt Cache Write | Prompt Cache Read |
|------|---------------------|---------------------|-------------------|-------------------|
| **Claude Fable 5.1** | $10.00 | $50.00 | $12.50 | $0.25 |
| **Claude Mythos 5**（限制访问） | $10.00 | $50.00 | — | — |
| **Claude Opus 5.5** | **$4.00** | **$20.00** | $5.00 | $0.20 |
| **Claude Sonnet 5.5** | **$2.00** | **$10.00** | $2.50 | **$0.10**（官方口径较 $0.20 减半） |
| **Claude Haiku 5.5**（prompt ≤100K tokens） | **$0.10** | **$0.50** | $0.125 | $0.01 |
| **Claude Haiku 5.5**（prompt >100K tokens） | **$0.50** | **$2.50** | $0.625 | $0.05 |

> 来源：[Anthropic 官方定价页](https://www.anthropic.com/pricing)（cache 价格 2026-10-19 核实）；Fable 5.1 / Mythos 5 沿用 Fable 5 同价口径。

> ⚡ **Fast mode**：Opus 5.5 支持 fast mode——2.5× 速度、2× 标准定价（官方定价页，2026-10-19）。

> ⚠️ **tokenizer 成本提醒**：Claude 自 Opus 4.7 起更换 tokenizer，同一输入映射为 **1.0–1.35× token**；跨世代对比单价时不可只看标价。

> **价格对比参考**：Fable 线 / Mythos 5（$10/$50）是 Opus 5.5（$4/$20）的 2.5 倍；Sonnet 5.5 与 Opus 5.5 差 2 倍。

## 竞品对比

> 📌 **最新对比**：Claude 5.5 家族（Opus 5.5 09-22 / Sonnet 5.5 09-28 / Haiku 5.5 10-07）与 GPT-6、Gemini 4 Argon 的横向对比（含 AA 独立指数座次：Opus 5.5 58 第一）见 [Haiku 5.5 vs GPT-6 Luna 小型档竞争分析](../../alibaba-ai-hub/competitive-analysis/haiku-vs-luna/overview.md)。
>
> 历史世代（Fable 5 / Opus 4.8 时期）的跨厂商对比已随各模型迭代失效，不再维护。

## 参考资料

- [Anthropic 官方博客 — Introducing Claude Haiku 5.5](https://www.anthropic.com/claude-haiku-5-5)（2026.10.07）
- [Claude Haiku 5.5 System Card](https://www.anthropic.com/document/claude-haiku-5-5-system-card)
- [Claude Platform 模型总览](https://platform.claude.com/docs/en/models/overview)
- [Anthropic 官方博客 — Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5)（2026.09.22）
- [Anthropic 官方博客 — Introducing Claude Sonnet 5.5](https://www.anthropic.com/claude-sonnet-5-5)（2026.09.28）
- [AWS what's-new — Claude Haiku 5.5](https://aws.amazon.com/about-aws/whats-new/2026/10/claude-haiku-5-5-aws/)
- [Simon Willison — Claude Haiku 5.5 实测](https://simonwillison.net/2026/Oct/7/claude-haiku-5-5/)（tokenizer ~1.25×、订阅 credits 细节）
- [Anthropic 官方博客 — Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5)（2026.07.24）
- [Anthropic 官方博客 — Introducing Claude Sonnet 5](https://www.anthropic.com/news/claude-sonnet-5)（2026.06.30）
- [anthropics/skills 官方模型目录](https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/models.md) — 模型 ID / 上下文与输出上限 / API 破坏性变更 / 废弃时间表的权威清单
- [Anthropic 官方定价页](https://www.anthropic.com/pricing)（2026.06.14 核实）
- [Vellum AI: Fable 5 & Mythos 5 Benchmarks Explained](https://www.vellum.ai/blog/claude-fable-5-and-mythos-5-benchmarks-explained)
- [AppStackBuilder: Claude Fable 5 & Mythos 5 Launch](https://appstackbuilder.com/blog/claude-fable-5-mythos-5-launch-2026)
- [Forbes: Anthropic's Fable 5 AI Model Offers More Power At A Higher Price](https://www.forbes.com/sites/ronschmelzer/2026/06/10/anthropic-fable-5-ai-model-cost/)
- [Anthropic 官方博客 — Claude Opus 4.8](https://www.anthropic.com/news/claude-opus-4-8)
- [Claude Fable 5 官方产品页](https://www.anthropic.com/claude/fable)
- [Prompting Claude Fable 5（官方 Prompting Guide）](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- [Anthropic 官方博客 — Claude Opus 4.7](https://www.anthropic.com/news/claude-opus-4-7)
- [TechCrunch: Anthropic releases Opus 4.8 with new dynamic workflow tool](https://techcrunch.com/2026/05/28/anthropic-releases-opus-4-8-with-new-dynamic-workflow-tool/)
- [Anthropic API 文档](https://docs.anthropic.com)
- [Claude API Platform](https://console.anthropic.com)
- 定价：https://platform.claude.com/docs/zh-CN/about-claude/pricing

> ⚠️ **信源踩坑记录（2026-08-01）**：`platform.claude.com` 各页面存在持续抓取超时；其定价页的**搜索摘要**曾给出 Sonnet 5 为 $1/$5 → $1.50/$7.50，**经官方发布页逐字比对证实为错配、完全错误**。核实定价必须以 `anthropic.com/news/*` 发布页或官方定价页原文为准，**不可采信搜索摘要**。

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-19 | 校验修复（knowledge-verification-2026-10-19）：定价表 cache 价格回填（官方定价页核实）——Fable 5.1 write $12.50 / read $0.25、Opus 5.5 write $5 / read $0.20、Sonnet 5.5 write $2.50；补注 Opus 5.5 fast mode（2.5× 速度、2× 定价） |
| 2026-10-19 | 历史世代瘦身（用户确认无存量客户使用 Opus 4.x / Sonnet 4.6）：Opus 5 86→6 行、Fable 5 31→5 行、Mythos 5 27→8 行、Opus 4.7/4.8 合并为历史表、Sonnet 5 48→5 行、Sonnet 4.6 与 Haiku 4.5 小节删除；定价表只保留当前 5 款在售型号；删除 Fable 5 / Opus 4.8 时期两节跨厂商对比；核心能力/限制/适用场景表全部改为当前世代口径；保留 tokenizer ×1.0–1.35 等不随版本失效的认知 |
| 2026-10-09 | 合并 ai-native-expert 四模型调研素材：**新增 Claude 5.5 家族刷新章节**（Opus 5.5 09-22 $4/$20 / Sonnet 5.5 09-28 $2/$10 + cache 读减半 / 家族级 Max/Team API credits）与 **Haiku 5.5 专章**（1M/128K、首个按上下文长度分层定价 $0.10/$0.50、effort 五档、tokenizer ~1.25× 隐性回补、能力/安全/成本归因全量）；**补录 Fable 5.1**（$10/$50 同价，AA 65.7）；主推表刷新为 5.5 家族（Fable 5 / Opus 5 / Sonnet 5 / Haiku 4.5 移入历史标注）；定价表新增 6 行；适用场景与核心限制表同步；竞品对比新增 2026-10 更新指引 |
| 2026-08-01 | 合并 ai-native-expert 素材：**新增 Claude Opus 5（2026.07.24）**完整章节（$5/$25 同价 Opus 4.8 / Fable 5 半价、1M、无数据留存、512 cache 最小块、独立限流池、thinking disabled 仅 effort≤high、护栏从领域级下沉到任务阶段级 + OSS-Fuzz 双轴依据、CVP、两项 beta）；**新增 Claude Sonnet 5（2026.06.30）**完整章节（$2/$10 introductory→$3/$15、tokenizer ×1.0–1.35、Free/Pro 默认模型、Firefox 147 exploit 评测 0.0%、护栏同 Opus 4.7/4.8）；**版本代际校正**：“当前最强=Fable 5”改为“Fable 5 为最高能力档、Opus 5 为 coding/knowledge work SOTA”，主推表重构为 4 款并将 Opus 4.8/4.7/4.6/Sonnet 4.6 移入历史模型；**修正 Sonnet 4.6 上下文 200K→1M**、模型 ID 纠错、Haiku 4→Haiku 4.5；补记 Opus 4.1 于 2026-08-05 退役；修复核心能力表格式错误；记录定价信源踩坑（搜索摘要不可采信） |
| 2026-06-15 | 合并 ai-native-expert 素材：Fable 5 新增「days-long 自主执行」和「主动自验证（Proactive Self-Verification）」详细行为描述（来自官方 Prompting Guide）；补充并行子 Agent 委托能力 |
| 2026-06-14 | 新增 Claude Fable 5（2026.06.09）与 Claude Mythos 5 完整信息：定价 $10/$50、Mythos-class 架构、自动降级机制、SWE-Bench Pro 80.3%、关键 benchmarks；更新 Haiku 为 4.5；定价表补全 Prompt Caching；更新竞品对比 |
| 2026-06-03 | 合并 ai-native-expert 素材：新增 Agentic 基准（Online-Mind2Web 84%）、Legal Agent Benchmark、Tool calling 改进、Messages API 系统条目、42 天迭代策略分析 |
| 2026-05-31 | 更新 Opus 4.8（2026.05.28 发布），包含关键基准（SWE-Bench Pro 69.2%等）、诚实度4×提升、fast mode降价、与Gemini 3.1 Pro竞品对比 |
| 2026-05-28 | 新建文档，首次提炼 Claude Opus 4.7 系列信息 |