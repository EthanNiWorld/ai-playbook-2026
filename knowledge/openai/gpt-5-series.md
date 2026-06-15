# OpenAI GPT-5 系列模型

> 最后更新: 2026-06-15
> 所属厂商: OpenAI
> 产品类别: MaaS
> 状态: Published

**定位**: OpenAI 最新一代旗舰模型系列，统一多模态架构，支持文字/图像/音频/视频输入，强调原生电脑操控能力
**当前主推**: GPT-5.5（2026.04.23）
**适用**: 通用推理、Agentic Coding、复杂任务执行、企业级应用
**不适用**: 预算敏感型个人用户、超低延迟场景、对开源/可自托管有强需求场景

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **GPT-5.5** | 🚩 最新旗舰 | 256K–1M | 面向 Plus/Pro/Business/Enterprise 用户 | 2026.04.23 |
| **GPT-5.4** | Native Computer Use | 256K–1M | 首次具备原生电脑操控能力 | 2026.03 |
| **GPT-5.3-Codex** | 编程专项 | 256K–1M | 企业级编程优化 | 2026.02.06 |

> 📌 **历史模型**：GPT-5.3-Instant（幻觉控制）、GPT-5.3（人格/创意）、GPT-5.2、GPT-5（统一旗舰）仍可调用，但已被 GPT-5.5/5.4 取代，不建议新项目选用。

> 📌 **路线图**：GPT-5.6 已有曝光，预计 2026 年 6 月发布 [⚠️ 待验证]

### GPT-5.5

- **模型**：gpt-5.5
- **公司**：OpenAI
- **时间**：2026 年 4 月 23 日
- **尺寸**：MoE [⚠️ 具体参数未公开]
- **上下文**：256K 至 1M tokens
- **场景**：最新迭代版本，面向 Plus/Pro/Business/Enterprise 用户
- **特点**：GPT-4.5 以来首次全量从头训练（fully retrained）的基础模型，定位 agentic coding + scientific reasoning + data analysis 三位一体，强调跨领域泛化能力而非垂直场景极致深度
- **推理深度（Reasoning Effort）**：支持 5 级调节 — `xhigh` / `high` / `medium` / `low` / 默认
- **定价**：$5 / $30 per 1M input/output tokens（batch/flex 半价，priority 2.5×）；Pro 版 $30 / $180

#### Benchmark 数据（thinking depth: xhigh，除非另注）

| Benchmark | GPT-5.5 (xhigh) | GPT-5.4 | Opus 4.7 | Gemini 3.1 Pro | 说明 |
|-----------|------------------|---------|----------|----------------|------|
| Terminal-Bench 2.0 | **82.7%** | 75.1% | 69.4% | 68.5% | 领先 Opus 4.7 达 13pt，最大单 benchmark 差距 |
| SWE-Bench Pro | 58.6% | 57.7% | **64.3%** | 54.2% | 落后 Opus 4.7，但该 benchmark 存在 memorization 争议 |
| Expert-SWE（OpenAI 内部） | **73.1%** | 68.5% | — | — | 长程编程专项 |
| OSWorld-Verified | 78.7% | 75.0% | 78.0% | — | |
| MCP Atlas（工具调用） | 75.3% | 70.6% | **79.1%** | 78.2% | Opus 4.7 领先 |
| BrowseComp | 84.4% | 82.7% | 79.3% | **85.9%** | |
| FrontierMath Tier 4 | **35.4%** | 27.1% | 22.9% | 16.7% | |
| GDPval-AA（AA 排行榜） | **84.9%**（wins/ties） | 83.0% | 80.3% | 67.3% | Elo 1785，领先 Opus 4.7 (max) ~30pt |
| MRCR v2 8-needle 512K–1M | **74.0%** | 36.6% | 32.2% | — | 长上下文能力跃升 |

#### 推理深度-成本梯度（来源：Artificial Analysis, 2026-04-23）

| Effort | 智能水平 | 运行 Intelligence Index 成本 | 对标 |
|--------|----------|------------------------------|------|
| xhigh | 最高 | ~$4,800 | — |
| medium | ≈ Opus 4.7 (max) | ~$1,200（1/4 成本） | — |
| low | ≈ Opus 4.7 (non-reasoning, high) | ~$500（1/2 成本） | — |

> 数据来源：OpenAI 官方博客 2026-04-23、Artificial Analysis 2026-04-23、alexlavaee.me 分析

### GPT-5.4

- **模型**：gpt-5.4
- **公司**：OpenAI
- **时间**：2026 年 3 月
- **尺寸**：MoE [⚠️ 具体参数未公开]
- **上下文**：256K 至 1M tokens
- **场景**：通用旗舰、重度推理、企业级任务
- **特点**：首次具备 **Native Computer Use（原生电脑操控能力）**，可自动执行点击、填表、跨软件导航等操作任务

### GPT-5.3-Codex

- **模型**：gpt-5.3-codex
- **公司**：OpenAI
- **时间**：2026 年 2 月 6 日
- **尺寸**：MoE [⚠️ 具体参数未公开]
- **上下文**：256K 至 1M tokens
- **场景**：编程专项
- **特点**：专为企业级编程任务优化

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **统一多模态** | 支持文字/图像/音频/视频输入 |
| **Native Computer Use** | GPT-5.4 首次具备，可自动操控电脑 |
| **超长上下文** | 256K 至 1M tokens |
| **Expert 级推理** | GPT-5 官方定位 |
| **编程 SOTA** | GPT-5.3-Codex 编程专项优化 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 价格 | 高昂 | Plus $20/月，Pro $200/月，API 按 token 计费 |
| OpenAI 访问 | 需翻墙 | 国内无法直接访问 |
| 退役模型 | GPT-4o 等已退役 | 2026.02.13 起生效 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 通用推理（最高质量） | GPT-5.5 / GPT-5.4 | 最新最强版本 |
| 编程专项 | GPT-5.3-Codex | OpenAI 官方编程优化 |
| 复杂 Agent 任务 | GPT-5.4 | Native Computer Use 能力 |
| 企业级应用 | GPT-5 全系列 | Plus/Pro/Business/Enterprise 分层 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 预算敏感用户 | 价格较高 |
| 超低延迟场景 | 非实时优化方向 |
| 开源自托管 | OpenAI 模型闭源 |
| 国内直接访问 | 需翻墙 |

## 已退役模型

| 模型 | 退役时间 | 说明 |
|------|----------|------|
| GPT-4o | 2026.02.13 | 已退役 |
| GPT-4.1 / 4.1 mini | 2026.02.13 | 已退役 |
| o4-mini | 2026.02.13 | 已退役 |
| GPT-5 Instant / Thinking | 2026.02.13 | 已退役 |

## 参考资料

- [OpenAI 官网](https://openai.com)
- [OpenAI 官方博客 — Introducing GPT-5.5](https://openai.com/index/introducing-gpt-5-5/)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [OpenAI API 定价文档] https://developers.openai.com/api/docs/pricing?latest-pricing=standard

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-15 | 合并 ai-native-expert 素材：GPT-5.5 补充「GPT-4.5 以来首次全量从头训练」技术事实，强化 agentic coding + 通用推理定位描述 |
| 2026-06-14 | 补充 GPT-5.5 benchmark 数据（TB 2.0: 82.7%, SWE-Bench Pro: 58.6% 等），标注 thinking depth: xhigh；新增推理深度 5 级梯度说明及 AA 成本对比；补充定价信息 |
| 2026-06-04 | 主推模型表精简：仅保留 GPT-5.5/5.4/5.3-Codex 为主推，GPT-5.3/5.2/5.0 移入历史模型标注 |
| 2026-05-28 | 新建文档，首次提炼 GPT-5 系列模型系列信息 |