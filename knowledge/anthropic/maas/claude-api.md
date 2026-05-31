# Anthropic Claude 模型

> 最后更新: 2026-05-28
> 所属厂商: Anthropic
> 产品类别: MaaS
> 状态: Published

**定位**: Anthropic 旗舰模型系列，强调 Constitutional AI 安全对齐、长文本理解与高精度推理
**当前主推**: Claude Opus 4.8（2026.05.28，**1M 上下文**）
**适用**: 高精度推理、复杂长文本分析、代码生成、企业级 Agent、合规要求高场景
**不适用**: 预算敏感场景、超高并发低成本推理

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Claude Opus 4.8** | 旗舰 | **1M** | SWE-Bench Pro 69.2%，诚实度4×提升，动态工作流，effort控制 | 2026.05.28 |
| **Claude Opus 4.7** | 前旗舰 | **1M** | 视觉能力3×提升，编程显著跃升，xhigh 推理等级，128K 最大输出 | 2026.04.16 |
| **Claude Sonnet 4.6** | 均衡旗舰 | 200K | 性价比旗舰，编程/推理均衡 | 2026.03 |
| **Claude Haiku 4** | 轻量极速 | 200K | 极速响应，编程能力显著提升 | 2026.04 |

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

#### 编程基准对比

| 基准 | Opus 4.8 | Opus 4.7 | GPT-5.5 | Gemini 3.1 Pro |
|------|----------|----------|---------|----------------|
| SWE-Bench Pro | **69.2%** | 64.3% | 58.6% | 54.2% |
| SWE-Bench Verified | **88.6%** | 87.6% | — | 80.6% |
| Terminal-Bench 2.1 | **74.6%** | 66.1% | 78.2% | 70.3% |
| HLE（带工具） | **57.9%** | 54.7% | 52.2% | 51.4% |
| OSWorld-Verified | **83.4%** | 82.8% | 78.7% | 76.2% |
| GDPval-AA | **1,890** | 1,753 | 1,769 | 1,314 |

> 注：Terminal-Bench 对测试 harness 敏感。GPT-5.5 在 OpenAI 自有 Codex CLI 上得分 83.4%，但在公共 Terminus-2 harness 上为 78.2%。Opus 4.8 在同条件 Terminus-2 下 74.6%，对比 Gemini 3.1 Pro 的 70.3%。

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
| **多模态** | Opus 4.7 视觉能力提升 3 倍 |
| **Agent 能力** | Claude Code 编程 Agent，支持动态工作流（parallel subagents）、effort 调参 |

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
| 最高精度推理 | Opus 4.7 | xhigh 推理等级，视觉3×提升 |
| 均衡性价比 | Sonnet 4.6 | 编程/推理均衡 |
| 极速响应 | Haiku 4 | 编程能力显著提升，极速 |
| 企业级 Agent | Opus 4.7 / Sonnet 4.6 | Task Budgets 支持 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 预算敏感用户 | 价格较高 |
| 超高并发低成本 | 非性价比路线 |
| 国内直接访问 | 需翻墙 |

## 定价（API）

| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) |
|------|---------------------|---------------------|
| **Claude Opus 4.8** | $5.00 | $25.00 |
| **Claude Opus 4.8 Fast** | $10.00 | $50.00 |
| **Claude Sonnet 4.6** | $3.00 | $15.00 |
| **Claude Haiku 4** | $0.80 | $4.00 |

## 竞品对比（vs Gemini 3.1 Pro）

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

- [Anthropic 官方新闻](https://www.anthropic.com/news/claude-opus-4-7)
- [Anthropic API 文档](https://docs.anthropic.com)
- [Claude API Platform](https://console.anthropic.com)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-05-31 | 更新 Opus 4.8（2026.05.28 发布），包含关键基准（SWE-Bench Pro 69.2%等）、诚实度4×提升、fast mode降价、与Gemini 3.1 Pro竞品对比 |
| 2026-05-28 | 新建文档，首次提炼 Claude Opus 4.7 系列信息 |