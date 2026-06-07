# MAI 模型家族

> 最后更新: 2026-06-07
> 所属厂商: Microsoft AI (MAI)
> 产品类别: AI 模型（推理 / 编码 / 图像 / 语音 / 转录）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 微软自研多模态模型家族，2026 年 Build 大会首发 7 款模型，覆盖推理、编码、图像、语音、转录全品类
**当前主推**: 🚩 MAI-Thinking-1（推理旗舰）、MAI-Code-1-Flash（高效编码）
**适用**: 企业级推理与编码辅助、GitHub Copilot 集成、Microsoft Foundry 部署
**不适用**: 通用对话（MAI-Thinking-1 侧重推理/编码，非通用 chatbot）；当前仅私有预览，尚未全面开放 API
**竞品**: Claude Opus 4.6 / Sonnet 4.6（Anthropic）、GPT 5.4（OpenAI）、Gemini 2.5 Pro（Google）
**常搭配**: GitHub Copilot、VS Code、Microsoft Foundry、Azure
<!-- SUMMARY_END -->

> ⚠️ 素材截止：2026-06-07。模型版本/定价/可用性等可能已有更新，使用前请验证。

## 当前主推模型

| 模型 | 定位 | 激活参数 / 总参数 | 上下文 | 核心特点 | 推出时间 |
|------|------|-------------------|--------|----------|----------|
| 🚩 MAI-Thinking-1 | 推理旗舰 | 35B / ~1T（Sparse MoE） | 256K | AIME 2026 94.5%、SWE-Bench Pro 与 Opus 4.6 持平 | 2026-06-02 |
| MAI-Code-1-Flash | 高效编码 | 5B / 137B（MoE） | [⚠️ 待补充] | Token 消耗减少 60%、已集成 GitHub Copilot/VS Code | 2026-06-02 |
| MAI-Image-2.5 (+Flash) | 图像生成/编辑 | [⚠️ 待补充] | — | Arena 评分超 Nano Banana Pro | 2026-06-02 |
| MAI Transcribe-1.5 | 转录 SOTA | [⚠️ 待补充] | — | 43 语言、5 倍速度、领域术语支持 | 2026-06-02 |
| MAI-Voice-2 (+Flash) | 语音合成 | [⚠️ 待补充] | — | 15 语言、小样本声音适配 | 2026-06-02 |

### MAI-Thinking-1
- 模型：MAI-Thinking-1
- 公司：Microsoft AI（Superintelligence team）
- 时间：2026 年 6 月（Build 2026 发布）
- 架构：Sparse Mixture of Experts（MoE）
- 尺寸：35B 激活参数 / ~1T 总参数
- 上下文：256K tokens
- 场景：推理、编程、数学、企业级 Agent
- 特点：
  - AIME 2025 97.0%、AIME 2026 94.5%
  - SWE-Bench Pro 与 Claude Opus 4.6 持平（toe-to-toe）
  - Surge 专业评测员盲测 1,276 任务偏好优于 Sonnet 4.6
  - 未使用第三方模型蒸馏，从零训练
  - 支持函数调用（function calling）、开发者指令、Chat Completions API
- 训练数据：商业许可数据，排除 AI 生成内容；含自有爬虫（~1.2T 页爬取，过滤后 794B 页）+ Common Crawl（过滤后 24.2B 页）；过滤含 UT1 黑名单（成人/盗版域名）和内容级去重
- 训练规模：30T tokens，8192 GB200 GPU
- 可用性：Microsoft Foundry 私有预览

### MAI-Code-1-Flash
- 模型：MAI-Code-1-Flash
- 公司：Microsoft AI
- 时间：2026 年 6 月（Build 2026 发布）
- 架构：Mixture of Experts（MoE）
- 尺寸：5B 激活参数 / 137B 总参数
- 上下文：[⚠️ 待补充]
- 场景：轻量级编码辅助、代码补全、Agentic coding
- 特点：
  - 推理高效，对标 Haiku 级别但更便宜
  - 微软对抗性编程基准 85.8%
  - 复杂任务 Token 消耗减少 60%
  - 已集成至 GitHub Copilot（Free/Student/Pro/Pro+/Max 所有层级）+ VS Code
  - 未使用第三方模型蒸馏
- 可用性：GitHub Copilot 滚动上线中（VS Code 优先）

### MAI-Image-2.5 (+ Flash)
- 模型：MAI-Image-2.5 / MAI-Image-2.5-Flash
- 公司：Microsoft AI
- 时间：2026 年 6 月
- 尺寸：[⚠️ 待补充]
- 场景：文生图、图像编辑
- 特点：Arena 评分超过 Nano Banana Pro；Flash 变体为超高效版本
- 可用性：[⚠️ 待补充]

### MAI Transcribe-1.5
- 模型：MAI Transcribe-1.5
- 公司：Microsoft AI
- 时间：2026 年 6 月
- 尺寸：[⚠️ 待补充]
- 场景：语音转文本、多语言转录
- 特点：SOTA 精度、5 倍速度（vs 竞品）、43 语言、领域特定术语支持
- 可用性：[⚠️ 待补充]

### MAI-Voice-2 (+ Flash)
- 模型：MAI-Voice-2 / MAI-Voice-2-Flash
- 公司：Microsoft AI
- 时间：2026 年 6 月（Flash 变体 coming soon）
- 尺寸：[⚠️ 待补充]
- 场景：语音合成、多语言 TTS
- 特点：15 语言、小样本声音适配、内置滥用防护；Flash 变体为低成本超高效版本
- 可用性：[⚠️ 待补充]

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 高级数学推理 | AIME 2026 94.5%、AIME 2025 97.0% |
| 软件工程 | SWE-Bench Pro 与 Claude Opus 4.6 持平；训练环境为确定性可执行环境，用真实测试套件评分 |
| 高效编码 | MAI-Code-1-Flash 5B 激活参数，Token 消耗减少 60% |
| 多模态覆盖 | 图像生成（Image-2.5）、语音合成（Voice-2）、转录（Transcribe-1.5）|
| 企业级集成 | GitHub Copilot / VS Code 原生集成（Code-1-Flash）|
| 长上下文 | MAI-Thinking-1 支持 256K tokens |
| 函数调用 | MAI-Thinking-1 支持 function calling 和开发者指令 |
| Chat Completions API 兼容 | 便于现有工作负载迁移 |
| 企业安全合规 | Microsoft Foundry 企业级安全 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 私有预览 | MAI-Thinking-1 仅 Microsoft Foundry 私有预览 | 公开预览时间待定 |
| 编码模型可用范围 | MAI-Code-1-Flash 目前仅限 GitHub Copilot + VS Code | 滚动上线中 |
| 多模态模型详情 | Image-2.5 / Voice-2 / Transcribe-1.5 参数/定价未公开 | [⚠️ 待补充] |
| 训练数据性质 | 虽强调"商业许可"，实际含 Common Crawl 和公开网络爬取 | 见"常见误解" |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 企业级推理与数学 | MAI-Thinking-1 | AIME 2026 94.5%，256K 上下文 |
| 日常编码辅助 / 代码补全 | MAI-Code-1-Flash | 已集成 GitHub Copilot，Token 消耗低 |
| Agentic 软件工程 | MAI-Thinking-1 | SWE-Bench Pro 与 Opus 4.6 持平 |
| 图像生成与编辑 | MAI-Image-2.5 | Arena 评分超 Nano Banana Pro |
| 多语言转录 | MAI Transcribe-1.5 | 43 语言、5 倍速度 |
| 多语言语音合成 | MAI-Voice-2 | 15 语言、小样本适配 |
| 企业特定场景微调 | Frontier Tuning | 客户自有工作流数据 RL 微调，模型权重归客户 |

### ❌ 不适用

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 通用对话（当前阶段） | MAI-Thinking-1 侧重推理/编码，私有预览中 | GPT 5.4 / Claude Sonnet 4.6 |
| 非 VS Code 编码环境 | MAI-Code-1-Flash 目前仅 VS Code + Copilot | Claude Code / Qoder（多 IDE 支持） |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| "MAI 使用商业许可的独特数据训练" | 训练数据包含 Common Crawl（24.2B 页）和自有爬虫（794B 页），本质仍是公开网络爬取。"商业许可"指排除 AI 生成内容、过滤成人/盗版域名（UT1 黑名单）、内容级去重，与 OpenAI/Anthropic 做法无本质区别 |
| "盲测优于 Sonnet 4.6 适用于整个 MAI 家族" | 仅 MAI-Thinking-1 在 Surge 1,276 任务盲测中优于 Sonnet 4.6；MAI-Code-1-Flash 对标的是 Haiku 级别 |
| "MAI-Thinking-1 是 35B 参数模型" | 35B 是 MoE 的激活参数，总参数约 1T。Simon Willison 在博文中犯了此错误并做了更正致歉 |

## 关键配置与最佳实践

### 战略背景

1. **摆脱 OpenAI 依赖**：微软长期依赖 OpenAI 提供 GPT 系列模型用于 Copilot 等产品，带来成本不可控、差异化受限、战略被动三大风险。MAI 家族标志着从"分销商"向"自研者"的关键转型。

2. **MoE + 低激活参数 = 成本驱动**：GitHub Copilot 面对海量日活代码补全请求，5B 激活参数（Code-1-Flash）意味着推理成本可比 dense 70B+ 模型压缩一个数量级，配合 60% Token 消耗减少，Copilot Free/Student 层级才具备商业可行性。

3. **Frontier Tuning 是真正的护城河**：
   - 用客户自有真实工作流数据做 RL 微调
   - 微软 Excel 专用模型达到 GPT 5.4 水平但效率高 10 倍
   - 客户拥有微调后的模型权重
   - 微软有 Office 365 + GitHub + Azure 三大生态的真实工作流数据，OpenAI 和 Anthropic 都不具备

4. **自研芯片协同**：微软自研 Maia 200 加速器已实现 1.4 倍效率提升，模型与芯片协同设计确保长期自主性。

5. **Mayo Clinic 合作**：Build 2026 同时宣布与 Mayo Clinic 合作开发医疗领域前沿 AI 模型，结合 Mayo 临床数据与微软基础模型能力，模型归 Mayo Clinic 所有。

6. **第三方分发**：MAI 模型已在 OpenRouter、Fireworks 和 Baseten 上线，开发者可自行调整模型权重。

### 踩坑记录

| 问题 | 原因 | 解决方案 | 记录日期 |
|------|------|----------|----------|
| MoE 参数混淆 | 激活参数 ≠ 总参数，35B 激活 / ~1T 总量 | 引用时明确区分"激活参数"与"总参数" | 2026-06-07 |

## 竞品快速对照

| 维度 | MAI-Thinking-1 | Claude Opus 4.6 | GPT 5.4 |
|------|----------------|-----------------|---------|
| 架构 | Sparse MoE 35B 激活 / ~1T 总参 | [⚠️ 待补充] | [⚠️ 待补充] |
| AIME 2026 | 94.5% | — | — |
| SWE-Bench Pro | 与 Opus 4.6 持平 | 持平 | — |
| 盲测 vs Sonnet 4.6 | 偏好优于 | — | — |
| 上下文 | 256K | [⚠️ 待补充] | [⚠️ 待补充] |
| 可用性 | Foundry 私有预览 | 已公开 | 已公开 |

| 维度 | MAI-Code-1-Flash | Claude Haiku 4 |
|------|------------------|----------------|
| 定位 | 高效编码（5B 激活 / 137B 总参） | 轻量通用 |
| Token 效率 | 复杂任务减少 60% | — |
| 集成 | GitHub Copilot / VS Code 原生 | API 调用 |

## 参考资料

- [Introducing MAI-Thinking-1（官方博客）](https://microsoft.ai/news/introducing-mai-thinking-1/)
- [Building a hill-climbing machine: Launching seven new MAI models](https://microsoft.ai/news/building-a-hillclimbing-machine-launching-seven-new-mai-models/)
- [MAI-Thinking-1 Model Page](https://microsoft.ai/models/mai-thinking-1/)
- [MAI-Thinking-1 技术报告 (PDF)](https://microsoft.ai/wp-content/uploads/2026/06/main_20260602_2.pdf)
- [MAI-Code-1-Flash GitHub Blog](https://github.blog/changelog/2026-06-02-mai-code-1-flash-is-now-available-for-github-copilot/)
- [Simon Willison: Microsoft's new MAI models](https://simonwillison.net/2026/Jun/2/microsofts-new-models/)
- [Latent Space: MAI-Thinking-1 and MAI Family models](https://www.latent.space/p/ainews-microsoft-build-mai-thinking)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-06-07 | 创建：基于 Build 2026 公告及 Simon Willison 报道，新建 MAI 模型家族文档（7 款模型全景 + benchmark + 战略分析） |
