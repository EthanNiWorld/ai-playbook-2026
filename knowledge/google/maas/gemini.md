# Gemini

> 最后更新: 2026-07-27
> 所属厂商: GCP
> 产品类别: MaaS

**定位**: Google 自研多模态大模型系列，原生支持文本+图像+音频+视频多模态输入输出
**适用**: 多模态理解与生成、企业知识管理、Agent 基础模型、代码生成、计算机操控
**不适用**: 需要私有化部署的场景（Gemini 仅通过 API / GCP 平台提供）
**当前主推**: Gemini 3.x 系列。Pro 线旗舰为 Gemini 3.1 Pro（2026.02.19，推理与知识密度最强）；Flash 线主力已迭代至 **Gemini 3.6 Flash（2026.07.21 GA，官方定位 "workhorse"：coding/知识工作/多模态全面提升 + 输出 token 减 17%，输出降价至 $7.50/M）**，同期发布 3.5 Flash-Lite（350 tok/s 高吞吐）与 3.5 Flash Cyber（安全专用，限定开放）。Gemini 3.5 Pro 多次跳票，仍在合作伙伴测试中；Gemini 4 预训练已启动

## 当前主推模型

| 模型 | 定位 | 核心特点 | 推出/更新时间 |
|------|------|------|------|
| **Gemini 3.6 Flash** 🚩 | 主力（workhorse，Agent/企业知识工作） | coding/知识工作/多模态全面超越 3.5 Flash，输出 token 减 17%，Computer Use 内置 | 2026.07.21 |
| **Gemini 3.1 Pro** | 旗舰（推理/知识密度最强） | 当前 Pro 级旗舰，学术推理与密集长上下文仍领先 | 2026.02.19 |
| **Gemini 3.5 Flash-Lite** | 轻量（最快最便宜） | 350 tok/s，$0.30/$2.50，多项 Agent/Coding 评测超 3 Flash，Computer Use 内置 | 2026.07.21 |
| **Gemini Omni Flash** | 原生音视频多模态 | 端到端音频/视频原生理解，实时语音交互 | 2026.05.19 |
| **Gemini 3.5 Flash** | 上代 Flash 主力 | I/O 2026 首发，已被 3.6 Flash 取代 | 2026.05.19 |

> 📌 **专用模型**：Gemini 3.5 Flash Cyber（2026.07.21）——基于 3.5 Flash 微调的网络安全专用模型，搭配 CodeMender 代码安全 Agent，CyberGym 达前沿竞争力；因双用途风险**仅限政府与受信任伙伴**通过 CodeMender 限额试点获取，不公开售卖
> 📌 **历史模型**：Gemini 3 Pro / 3.1 Flash / 3.5 Flash 仍可调用，但已分别被 3.1 Pro / 3.5 Flash-Lite / 3.6 Flash 取代，不建议新项目选用

> ⚠️ Gemini 2.5 系列（Pro/Flash/Deep Think）为 2025 年中发布，**已非最新代**。2.5 Pro 更新至 2025.06.27，2.5 Flash 更新至 2025.09.26。详见 [Google DeepMind Model Cards](https://deepmind.google/models/model-cards/)

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **原生多模态** | 文本+图像+音频+视频统一理解与生成，不需要拼接多个模型 |
| **超长上下文** | 1M+ tokens，支持整仓库代码/超长文档一次性分析 |
| **Agent 基座** | Gemini Enterprise Agent Platform 的核心引擎，ADK 2.0 默认模型 |
| **Computer Use** | 3.6 Flash / 3.5 Flash-Lite / 3.5 Flash 内置计算机操控工具（client-side built-in tool），可跨浏览器/桌面/移动端自主操作 UI；3.6 Flash OSWorld-Verified 83.0% |
| **TPU 原生优化** | 在 TPU 8t/8i 上推理效率极致优化，推理性价比领先 |
| **MCP 原生支持** | 通过 MCP 协议调用 GCP 全系服务 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 部署方式 | 仅 API / GCP 平台 | 不支持私有化下载部署 |
| API 双轨 | `google.genai` + `vertexai` 两套 API | 开发者需根据场景选择，Google 已确认将长期共存 |
| 中文能力 | 强但非母语级 | 中文场景优先考虑 Qwen / DeepSeek 作为补充 |

## Gemini 3.6 Flash / 3.5 Flash-Lite / 3.5 Flash Cyber（2026-07-21 发布）

> 来源：[Google Blog — Introducing Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Flash Cyber](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)，Gemini API changelog 确认 3.6 Flash / 3.5 Flash-Lite 当日 GA

### 3.6 Flash：新一代 workhorse，叙事从"快"转向"高效可靠的企业 Agent 主力"

官方口径："production AI agents 需要更高 token 效率、更低时延、更可靠的表现"——核心卖点不再是峰值分数，而是**单位 Agent 任务成本**：

| 维度 | 3.6 Flash | vs 3.5 Flash |
|------|-----------|--------------|
| 输出 token 效率 | 减 17%（AA Index），DeepSWE 场景最高减 65% | 推理步骤与工具调用次数同步减少 |
| 定价 | $1.50 输入 / **$7.50 输出** /1M tokens | 输入持平，输出降价 17%（原 $9.00） |
| Coding 精度 | DeepSWE 49%（更少非预期代码编辑/执行循环） | 3.5 Flash 37% |
| ML 研究 | MLE Bench 63.9% | 3.5 Flash 49.7% |
| Computer Use | OSWorld-Verified 83.0%，内置 client-side 工具 | 3.5 Flash 78.4% |
| 知识工作 | GDPval-AA v2 1421（Hebbia/Harvey 反馈多模态文档解析/图表分析/报告起草能力突出） | 3.5 Flash 1349 |

- **安全**：携带增强版 Frontier Safety 防护（CBRN + 网络攻击滥用），抗越狱能力提升同时降低良性用途拒答率
- **可用性**：Gemini API（AI Studio / Android Studio）、Antigravity、Gemini Enterprise Agent Platform、Gemini App
- 客户背书：Figma、Harvey、Hebbia、JetBrains

> **Why 这个叙事重要**：Google 把 Flash 线从"便宜跑量"升级为"企业 Agent 主力"，token 效率成为与分数并列的一等公民指标——Agent 多轮调用下，输出 token 减 17% + 输出单价降 17% 的叠加效应对单任务成本的影响远大于 benchmark 提升。这与 StepFun Step 3.7 Flash 的"agent efficiency"路线同向，印证行业竞争焦点从智力上限转向效率前沿。

### 3.5 Flash-Lite：高吞吐 Agent 扩展层

- **速度/价格**：350 output tok/s（AA 实测，3.5 系最快），$0.30 输入 / $2.50 输出 /1M tokens
- **能力跃升**（vs 3.1 Flash-Lite）：Terminal-Bench 2.1 54% vs 31%；GDM-MRCR v2 72.2% vs 60.1%；GDPval-AA v2 1140 vs 642
- **越级表现**：多项 Agent/Coding 评测超 3 Flash（SWE-Bench Pro 54.2% vs 49.6%；OSWorld-Verified 74.0% vs 65.1%）
- **定位**：可配置 thinking level，低档跑高并发低时延任务，高档处理多步 subagent 工作负载；官方示例中与 3.6 Flash 组成 master-worker 多 Agent 编排；已开始接入 Google Search

### 3.5 Flash Cyber：安全垂直专用（限定开放）

基于 3.5 Flash 微调的网络安全模型，在 CodeMender 中以多 Agent 协作产出合并报告，CyberGym 达前沿竞争力。因双用途风险，**仅向政府与受信任伙伴限额试点**，售前场景不可承诺获取。

## 上代模型存档：Gemini 3.5 Flash（已被 3.6 Flash 取代）

> 发布 2026.05.19（Google I/O 2026），API Model ID `gemini-3.5-flash`。以下仅保留仍有参考价值的结论，详细 benchmark/定价历史数据见 [3.5 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-5-flash/) 及 Changelog 2026-06-09 版本。

- **历史意义**：首次打破"Pro=难题, Flash=跑量"二分法——Agent/Coding 负载上 Flash 首次超越自家上代 Pro（GDPval-AA 1656 vs 3.1 Pro 1314，Finance Agent v2 +14.9），奠定了 3.6 Flash "workhorse" 叙事的基础
- **关键参数**：1M 输入 / 64K 输出，$1.50/$9.00（缓存 $0.15），知识截止 2026.01
- **Computer Use 起源**：2026.06.24 率先在 3.5 Flash 上成为内置工具（此前仅独立 Gemini 2.5 computer use 模型），现已成为 Flash 线标配（3.6 Flash / 3.5 Flash-Lite 均内置）；安全机制：prompt injection 对抗训练 + 敏感操作显式确认 + 间接注入自动停止，建议配合沙箱与 human-in-the-loop
- **遗留弱点**（下方"诚实弱点"章节数据即基于 3.5 Flash 实测）：密集长上下文回忆与极难学术推理仍输 3.1 Pro

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 多模态企业知识库 | 3.6 Flash / 3.1 Pro | 3.6 Flash 多模态文档解析/图表分析获 Hebbia/Harvey 背书；深度推理选 3.1 Pro |
| Agent 规模化部署 | 3.6 Flash | workhorse 定位，token 效率减 17% + 输出降价，单任务成本最优 |
| 高吞吐批量/subagent 扩展 | 3.5 Flash-Lite | 350 tok/s，$0.30/$2.50，适合 agentic search/文档处理高并发 |
| 复杂推理/学术难题 | 3.1 Pro | 对标 Claude Opus / GPT-5.x，HLE/ARC-AGI-2 仍领先 Flash 线 |
| 实时音视频交互 | Omni Flash | 原生端到端音频/视频理解 |
| 代码辅助 | 3.6 Flash | DeepSWE 49% vs 3.5 Flash 37%，更少非预期编辑 |
| Google Workspace AI | 3.1 Flash / 3.1 Pro | 内嵌于 Gmail/Docs/Sheets 的 AI 能力 |

## 平台交付方式

Gemini 通过 **Gemini Enterprise Agent Platform** 统一交付（见 [`vertex-ai.md`](../ai-platform/vertex-ai.md)）。开发者可选两种接入路径：

| 路径 | 接口 | 适用 |
|------|------|------|
| **Gemini API / AI Studio** | `google.genai` | 快速原型、单次推理、个人开发者 |
| **Agent Platform** | `vertexai`（原 Vertex AI API） | 企业级 Agent 构建、生产部署、治理优化 |
| **Gemini App / Search AI Mode** | 消费者界面 | 3.6 Flash 已上线 Gemini App，3.5 Flash-Lite 接入 Google Search（默认模型是否切换待核实） |
| **Antigravity 2.0** | 独立桌面 Agent IDE | Agent 开发者，对标 Claude Code / Cursor |

> **新产品/能力**：
> - **Antigravity 2.0**：独立桌面 Agent 开发环境，支持并行子 Agent 执行、定时任务（后台自动化）、CLI + SDK，与 AI Studio / Android / Firebase 集成。Gemini CLI 用户可迁移至 Antigravity CLI。
> - **Managed Agents**：单次 API 调用即可启动完整 Agent（推理 + 工具调用 + 代码执行），隔离 Linux 环境，跨调用持久化。
> - **Gemini Spark**：基于 3.5 Flash 的个人 AI Agent，7×24 运行。

### 真实落地案例

| 客户 | 场景 |
|------|------|
| Shopify | 并行子 Agent 做全球商户增长预测 |
| Macquarie Bank | 100+ 页金融文档推理加速 onboarding |
| Salesforce Agentforce | 多子 Agent 企业任务自动化 |
| Ramp | 多模态 OCR 处理复杂发票 |
| Xero | 自主管理多周工作流（1099 税务表单） |
| Databricks | Agent 化监控与实时检索 |

### 诚实弱点

> 以下数据基于 3.5 Flash 实测（3.6 Flash 对应数据待 model card 核实），Flash 线相对 Pro 的结构性短板判断仍适用：

| 弱点 | 说明 |
|------|------|
| 128k 密集上下文回忆 | MRCR v2 · 128k 输 3.1 Pro 7.6 分，"塞满 128k 全部精准回忆"场景慎用 |
| 学术推理 | Humanity's Last Exam 输 4.2 分、ARC-AGI-2 输 5.0 分，极难学术问题选 3.1 Pro 或等待 3.5 Pro |

> 📌 **Gemini 3.5 Pro 预期（更新 2026-07-27）**：原预计 2026.06 发布，**已多次跳票**。官方 7/21 口径："正在与合作伙伴测试，准备好后尽快广泛提供"。Reuters 报道延迟原因是未达内部目标（尤其 coding）。同时官方确认 **Gemini 4 预训练已启动**（"最雄心勃勃的一次 pre-training run"）。售前沟通中不应承诺 3.5 Pro 时间表。

## 参考资料

- [Google Blog - Gemini 3.5](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-5/)
- [Google Blog — Introducing Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Flash Cyber](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)（2026-07-21）
- [Gemini API Release Notes](https://ai.google.dev/gemini-api/docs/changelog)（3.6 Flash / 3.5 Flash-Lite GA 确认）
- [Gemini 3.6 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-6-flash/)
- [Reuters — Google updates lightweight Gemini models, but flagship still delayed](https://www.reuters.com/business/google-updates-lightweight-gemini-models-flagship-still-delayed-2026-07-21/)（3.5 Pro 跳票归因）
- [Google Blog — Introducing computer use in Gemini 3.5 Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-computer-use-gemini-3-5-flash/)
- [Gemini 3.5 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-5-flash/)
- [LLM Stats - Gemini 3.5 Flash Launch](https://llm-stats.com/blog/research/gemini-3.5-flash-launch)
- [Gemini Flash 产品页](https://deepmind.google/models/gemini/flash/)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-07-27 | 精简：3.5 Flash 深度分析章节（~80 行）压缩为"上代模型存档"小节，保留战略意义/关键参数/Computer Use 起源，删除过时 benchmark/定价详表；诚实弱点与平台交付口径同步 |
| 2026-07-27 | 合并：2026-07-21 三模型发布官网调研 — 新增 Gemini 3.6 Flash（新 workhorse 🚩，$1.50/$7.50，token 效率 -17%）/ 3.5 Flash-Lite / 3.5 Flash Cyber 章节；主推表重排（3.5 Flash 降为上代）；3.5 Pro 跳票与 Gemini 4 预训练启动；适用场景表同步 |
| 2026-06-29 | 合并：Gemini 3.5 Flash Computer Use 官网调研 — 新增 Computer Use 内置工具章节（2026.06.24 发布，跨平台支持，安全机制），核心能力表新增 Computer Use 行，当前主推描述更新 |
| 2026-06-09 | 合并：Gemini 3.5 Flash 深度分析 — 补充 benchmark 详细对比表（vs 3.1 Pro）、定价、战略意图、Antigravity 2.0、Managed Agents、Gemini Spark、真实落地案例、诚实弱点、3.5 Pro 预期、参考资料 |
| 2026-06-09 | 修正：Gemini 3 Pro / 3.1 Pro 版本关系——3 Pro 为上代旗舰，3.1 Pro 为当前旗舰；适用场景表同步修正 |
| 2026-05-31 | 修正：Gemini 2.5→3.x 系列为最新代。新增 Gemini 3 Pro、3.5 Flash、Omni Flash、3.1 Pro/Flash。标注 Gemini 3.5 Pro 预计 2026.06 发布 |
