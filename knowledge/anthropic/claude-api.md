# Anthropic Claude 模型

> 最后更新: 2026-06-15
> 所属厂商: Anthropic
> 产品类别: MaaS
> 状态: Published

> **定位**: Anthropic 旗舰模型系列，强调 Constitutional AI 安全对齐、长文本理解与高精度推理
**当前最强**: Claude Fable 5（2026.06.09，Mythos-class 首个公开模型，**1M 上下文**）
**前旗舰**: Claude Opus 4.8（2026.05.28）
**适用**: 高精度推理、复杂长文本分析、代码生成、企业级 Agent、合规要求高场景
**不适用**: 预算敏感场景、超高并发低成本推理、涉及网络安全/生物化学敏感查询

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Claude Fable 5** | **Mythos-class 旗舰** | **1M** | SWE-Bench Pro 80.3%，Stripe 50M行Ruby迁移1天完成，敏感查询自动降级至Opus 4.8 | 2026.06.09 |
| **Claude Opus 4.8** | 前旗舰 | **1M** | SWE-Bench Pro 69.2%，诚实度4×提升，动态工作流，effort控制 | 2026.05.28 |
| **Claude Opus 4.7** | 次前旗舰 | **1M** | 视觉能力3×提升，编程显著跃升，xhigh 推理等级，128K 最大输出 | 2026.04.16 |
| **Claude Sonnet 4.6** | 均衡旗舰 | 200K | 性价比旗舰，编程/推理均衡 | 2026.03 |
| **Claude Haiku 4.5** | 轻量极速 | 200K | 极速响应，最具性价比 | 2026 |

### Claude Fable 5

- **模型 ID**：claude-fable-5
- **公司**：Anthropic
- **时间**：2026 年 6 月 9 日
- **上下文**：**1M tokens**，最大输出 128K tokens
- **定价**：$10/$50 per 1M input/output tokens（Prompt Caching Write $12.50/MTok，Read $1/MTok）
- **定位**：Mythos-class 首个公开版本，介于 Opus 4.8 和限制级 Mythos 5 之间
- **核心升级**：
  1. **编程能力大幅领先**：SWE-Bench Pro 80.3%（+11.1pp vs Opus 4.8 69.2%），FrontierCode Diamond split 29.3%（远超 Opus 4.8 的 13.4% 和 GPT-5.5 的 5.7%）
  2. **长程 Agent 突破（days-long 自主执行）**：在 Agent Harness（Claude Code / Claude Managed Agents）中可连续工作数天，官方 Prompting Guide 明确「autonomous runs can extend for hours」；Stripe 用 1 天完成原本 50M 行 Ruby codebase 需 2 个月才能完成的迁移；Slay the Spire 持久记忆测试下表现提升 3× vs Opus 4.8
  3. **主动自验证（Proactive Self-Verification）**：自动编写测试代码校验自己写的代码；用 Vision 比对产出物与原始设计稿；长任务中按固定间隔主动自检；进展汇报前强制审计工具结果，消除虚构进度报告
  4. **并行子 Agent 委托**：比上代显著更可靠地派遣和维持多个并行子 Agent，可信赖地管理长时间运行的子 Agent 通信
  5. **视觉能力 SOTA**：可从截图重建 web app 源码；完整通关 Pokémon FireRed 仅凭原始游戏截图（无地图辅助）；GDP.pdf（视觉文档推理）29.8% 领跑竞品
  6. **内置降级保护**：涉及**网络安全、生物化学、模型蒸馏**的查询自动由 Opus 4.8 代答，发生频率 <5% 会话。这意味着约 1/20 的会话实际运行的不是 Fable 5
  7. **知识工作领先**：Hebbia Finance Benchmark SOTA，IMC 交易分析评测全面领先；GDP.pdf 29.8% > GPT-5.5 24.9% > Opus 4.8 22.5%
  8. **Token 效率更高**：同等任务下 token 消耗优于前代模型
- **可用渠道**：Claude API（claude-fable-5）、Amazon Bedrock；订阅计划（Pro/Max/Team/Enterprise）含免费期至 2026.06.22，之后需用 usage credits
- **注意**：订阅用户免费使用窗口 2026.06.22 截止，之后回归前须等容量扩充

#### Fable 5 编程基准对比

| 基准 | Fable 5 | Opus 4.8 | GPT-5.5 | Gemini 3.1 Pro |
|------|---------|----------|---------|----------------|
| SWE-Bench Pro | **80.3%** | 69.2% | 58.6% | 54.2% |
| FrontierCode Diamond | **29.3%** | 13.4% | 5.7% | — |
| GDP.pdf（视觉）| **29.8%** | 22.5% | 24.9% | 16.7% |
| BioMysteryBench（fallback至Opus 4.8）| 40.0% | 40.0% | — | — |
| ExploitBench（fallback至Opus 4.8）| 40.0% | 40.0% | 34.0% | — |

> 注：Fable 5 在网络安全/生物查询上降级至 Opus 4.8 作答，因此其公开分数等于 Opus 4.8 的分数；Mythos 5（无限制版）在这些领域远超前者。

---

### Claude Mythos 5

- **模型 ID**：claude-mythos-5
- **公司**：Anthropic
- **时间**：2026 年 6 月 9 日（限制访问）
- **上下文**：**1M tokens**，最大输出 128K tokens
- **定价**：$10/$50 per 1M input/output tokens（与 Fable 5 相同）
- **定位**：Fable 5 同底座模型，**去除了网络安全限制**；目前仅通过 Project Glasswing 向美国政府网络防御者和关键基础设施提供商开放
- **核心能力（对比 Fable 5/Opus 4.8）**：
  1. **网络安全无上限**：ExploitBench 78.0%，约为 Opus 4.8（40.0%）的 2 倍，远超 GPT-5.5（34.0%）
  2. **生物科学研究**：BioMysteryBench 46.1% > Opus 4.8（40.0%）> Mythos Preview（29.6%）；蛋白质设计加速约 10×，14 个靶点中 9 个获强候选；某 E. coli 蛋白质新机制假设已被另一实验室独立证实
  3. **独立科研能力**：138 物种单细胞数据训练的基因组学模型，性能超过 Science 期刊论文发表的模型，且参数量仅为其 1/100
- **访问限制**：仅 Project Glasswing 合作伙伴；另有独立生物安全研究轨道（保留网络安全限制，仅开放生物化学限制）计划向特定研究人员开放
- **合规要求**：所有 Mythos-class 流量须 30 天数据留存，人工访问日志，自动删除；不用于训练

#### Mythos 5 关键基准

| 基准 | Mythos 5 | Fable 5（降级后） | Opus 4.8 | Mythos Preview |
|------|----------|-----------------|----------|----------------|
| ExploitBench | **78.0%** | 40.0% | 40.0% | 69.0% |
| BioMysteryBench | **46.1%** | 40.0% | 40.0% | 29.6% |
| SWE-Bench Pro | **80.3%** | **80.3%** | 69.2% | 77.8% |

> 来源：[Anthropic June 9, 2026 发布公告](https://www.anthropic.com/news)；[Vellum AI 基准分析](https://www.vellum.ai/blog/claude-fable-5-and-mythos-5-benchmarks-explained)

---

### Claude Opus 4.8

- **模型**：claude-opus-4-8
- **公司**：Anthropic
- **时间**：2026 年 5 月 28 日
- **上下文**：**1M tokens**，最大输出 128K tokens
- **定价**：$5/$25 per 1M input/output tokens（与 Opus 4.7 持平）
- **场景**：最高精度推理、复杂长文本分析、代码生成、企业级 Agent
- **核心升级**：
  1. **编程能力全面提升**：SWE-Bench Pro 69.2%（+4.9pp vs 4.7），SWE-Bench Verified 88.6%（+1.0pp），Terminal-Bench 74.6%（+8.5pp）
  2. **诚实度 4 倍提升**：模型漏报代码缺陷的概率降至原来的 1/4，不再假装无 bug，被社区视为比 benchmark 数字更重要的体验升级
  3. **知识工作突破**：GDPval-AA 1,890 分，领先 GPT-5.5（1,769）和 Gemini 3.1 Pro（1,314）
  4. **动态工作流**：Claude Code 新增 parallel subagents，单次会话可并行调度数百个子 Agent
  5. **effort 控制**：用户可调节 default / extra / max 三档推理深度，更高的 effort 等级可进一步改善质量
  6. **Fast mode 降价 3 倍**：$10/$50 per 1M tokens，速度 2.5×，仅为旧版 fast mode 的 1/3 价格
  7. **对齐水平达 Mythos 级**：首次在公开可用模型中达到 Mythos Preview 级别的对齐指标，Anthropic 预计数周内推 Mythos 级正式模型
  8. **Agentic 判断领先**：Online-Mind2Web（浏览器 Agent 基准）84%，超越 4.7 和 GPT-5.5
  9. **Tool calling 更高效**：用更少步骤完成相同任务；修复 4.7 的 comment-verbosity 过高和 tool-calling 一致性问题
  10. **法律 Agent 突破**：Legal Agent Benchmark 历史最高分，首个 all-pass 标准突破 10%
  11. **Messages API 系统条目**：开发者可在 messages 数组中插入 system entries，运行时更新指令而不破坏 prompt cache

#### 编程基准对比

| 基准 | Opus 4.8 | Opus 4.7 | GPT-5.5 | Gemini 3.1 Pro |
|------|----------|----------|---------|----------------|
| SWE-Bench Pro | **69.2%** | 64.3% | 58.6% | 54.2% |
| SWE-Bench Verified | **88.6%** | 87.6% | — | 80.6% |
| Terminal-Bench 2.1 | **74.6%** | 66.1% | 78.2% | 70.3% |
| HLE（带工具） | **57.9%** | 54.7% | 52.2% | 51.4% |
| OSWorld-Verified | **83.4%** | 82.8% | 78.7% | 76.2% |
| GDPval-AA | **1,890** | 1,753 | 1,769 | 1,314 |
| Online-Mind2Web | **84%** | — | <84% | — |

> 注：Terminal-Bench 对测试 harness 敏感。GPT-5.5 在 OpenAI 自有 Codex CLI 上得分 83.4%，但在公共 Terminus-2 harness 上为 78.2%。Opus 4.8 在同条件 Terminus-2 下 74.6%，对比 Gemini 3.1 Pro 的 70.3%。

#### 42 天快速迭代与版本策略

距上代 Opus 4.7（2026-04-16）仅 **42 天**，为 Anthropic 历史上最短 Opus 迭代间隔（此前约 70-75 天）。

**迭代动因**：
1. **修复 4.7 短板**：社区反馈 comment-verbosity 过高、tool-calling 不一致
2. **诚实性是 Agent 规模化前提**：4× 诚实性提升解锁大规模 Agent 部署
3. **竞争节奏加快**：GPT-5.5、Gemini 3.5 Pro/Flash 同期活跃
4. **为 Mythos 铺路**：在 Mythos 大规模开放前稳住旗舰位置

**版本发布策略**：Opus 先行 → Sonnet 1-4 周跟进 → Haiku 跳跃式更新（非每版本都跟）。

### Claude Opus 4.7

- **模型**：claude-opus-4-7
- **公司**：Anthropic
- **时间**：2026 年 4 月 16 日
- **上下文**：**1M tokens**，最大输出 128K tokens
- **场景**：最高精度推理、复杂长文本分析、代码生成、企业级 Agent
- **特点**：
  1. **视觉能力提升 3 倍**：多模态理解能力大幅增强
  2. **编程能力显著跃升**：编码 benchmark 领先 Opus 4.6
  3. **xhigh 推理等级**：高级推理能力
  4. **Task Budgets**：新增任务预算管理功能

### Claude Sonnet 4.6

- **模型**：claude-sonnet-4-6-20250514
- **公司**：Anthropic
- **时间**：2026 年 3 月
- **上下文**：200K tokens
- **场景**：均衡推理、性价比旗舰
- **特点**：编程/推理能力均衡，性价比优于 Opus

### Claude Haiku 4

- **模型**：claude-haiku-4-20250514
- **公司**：Anthropic
- **时间**：2026 年 4 月
- **上下文**：200K tokens
- **场景**：极速响应、代码补全
- **特点**：编程能力显著提升，保持 Haiku 系列极速优势

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **高精度推理** | Constitutional AI 安全对齐，强调输出安全性与无害性 |
| **长上下文** | 1M tokens（无长上下文附加费） | 标准 API 价格，无额外费用 |
| **代码生成** | Opus 4.8 SWE-Bench Pro 69.2%，Verified 88.6%，编程能力断层领先 |
| **多模态** | Opus 4.8 继承并增强视觉能力，支持图片、视频等多模态输入 |
| **Agent 能力** | Claude Code 编程 Agent，支持动态工作流（parallel subagents）、effort 调参、Online-Mind2Web 84%（浏览器 Agent 基准 SOTA） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 价格 | 高昂 | Opus $5/$25（不变），Sonnet $3/$15（per 1M tokens）；Fast mode $10/$50 |
| Anthropic 访问 | 需翻墙 | 国内无法直接访问 |
| 推理延迟 | 非极致优化 | 定位高精度，非超低延迟 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 最高精度推理 | Opus 4.8 | SWE-Bench Pro 69.2%，effort 控制，编程+推理 SOTA |
| 均衡性价比 | Sonnet 4.6 | 编程/推理均衡 |
| 极速响应 | Haiku 4 | 编程能力显著提升，极速 |
| 企业级 Agent | Opus 4.8 / Sonnet 4.6 | Dynamic Workflows、Task Budgets、Agentic 判断 84% |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 预算敏感用户 | 价格较高 |
| 超高并发低成本 | 非性价比路线 |
| 国内直接访问 | 需翻墙 |

## 定价（API）

| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) | Prompt Cache Write | Prompt Cache Read |
|------|---------------------|---------------------|-------------------|-------------------|
| **Claude Fable 5** | $10.00 | $50.00 | $12.50 | $1.00 |
| **Claude Mythos 5** | $10.00 | $50.00 | — | — |
| **Claude Opus 4.8** | $5.00 | $25.00 | $6.25 | $0.50 |
| **Claude Opus 4.8 Fast** | $10.00 | $50.00 | — | — |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | $3.75 | $0.30 |
| **Claude Haiku 4.5** | $1.00 | $5.00 | $1.25 | $0.10 |

> 来源：[Anthropic 官方定价页](https://www.anthropic.com/pricing)（2026.06.14 核实）

> **价格对比参考**：Fable 5/Mythos 5 是 Opus 4.8 的 **2 倍**；不到早期 Mythos Preview 的 **一半**；早期 Opus 4.1 原价 $15/$75，Fable 5 的性价比已有质的飞跃。

## 竞品对比

### Fable 5 vs 全家桶（2026.06.09）

| 维度 | Fable 5 | Opus 4.8 | GPT-5.5 | Gemini 3.1 Pro |
|------|---------|----------|---------|----------------|
| SWE-Bench Pro | **80.3%** | 69.2% | 58.6% | 54.2% |
| FrontierCode Diamond | **29.3%** | 13.4% | 5.7% | — |
| GDP.pdf（视觉） | **29.8%** | 22.5% | 24.9% | 16.7% |
| 定价（输入/输出） | $10/$50 | $5/$25 | — | — |

### Opus 4.8 vs Gemini 3.1 Pro

Opus 4.8 发布后，Anthropic 与 Google 在 AI Coding 核心基准上的差距进一步拉大：

| 维度 | Opus 4.8 | Gemini 3.1 Pro | 差距 |
|------|----------|----------------|------|
| SWE-Bench Pro | **69.2%** | 54.2% | +15.0pp |
| SWE-Bench Verified | **88.6%** | 80.6% | +8.0pp |
| Terminal-Bench 2.1 | **74.6%** | 70.3% | +4.3pp |
| HLE（带工具） | **57.9%** | 51.4% | +6.5pp |
| OSWorld-Verified | **83.4%** | 76.2% | +7.2pp |
| GDPval-AA | **1,890** | 1,314 | +576 分 |

**例外**：Finance Agent v2 上 Gemini 3.5 Flash（57.9%）领先 Opus 4.8（53.9%），说明 Google 在小模型+垂直金融场景有独特优势。

**核心判断**：Opus 4.8 的发布使 Google 在 AI Coding 领域追赶 Anthropic 的窗口期进一步延长。仅凭 Gemini 3.1 系列不足以弥合差距，需要 AlphaCode 产品化或 Gemini 3.x 后续重大迭代才有望缩小结构性差距。

## 参考资料

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
## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-15 | 合并 ai-native-expert 素材：Fable 5 新增「days-long 自主执行」和「主动自验证（Proactive Self-Verification）」详细行为描述（来自官方 Prompting Guide）；补充并行子 Agent 委托能力 |
| 2026-06-14 | 新增 Claude Fable 5（2026.06.09）与 Claude Mythos 5 完整信息：定价 $10/$50、Mythos-class 架构、自动降级机制、SWE-Bench Pro 80.3%、关键 benchmarks；更新 Haiku 为 4.5；定价表补全 Prompt Caching；更新竞品对比 |
| 2026-06-03 | 合并 ai-native-expert 素材：新增 Agentic 基准（Online-Mind2Web 84%）、Legal Agent Benchmark、Tool calling 改进、Messages API 系统条目、42 天迭代策略分析 |
| 2026-05-31 | 更新 Opus 4.8（2026.05.28 发布），包含关键基准（SWE-Bench Pro 69.2%等）、诚实度4×提升、fast mode降价、与Gemini 3.1 Pro竞品对比 |
| 2026-05-28 | 新建文档，首次提炼 Claude Opus 4.7 系列信息 |