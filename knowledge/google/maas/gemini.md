# Gemini

> 最后更新: 2026-06-29
> 所属厂商: GCP
> 产品类别: MaaS

**定位**: Google 自研多模态大模型系列，原生支持文本+图像+音频+视频多模态输入输出
**适用**: 多模态理解与生成、企业知识管理、Agent 基础模型、代码生成、计算机操控
**不适用**: 需要私有化部署的场景（Gemini 仅通过 API / GCP 平台提供）
**当前主推**: Gemini 3.x 系列，当前旗舰 Gemini 3.1 Pro（2026.02.19 发布，推理与知识密度最强），I/O 2026 发布 Gemini 3.5 Flash（Flash 速度 + 超越 3.1 Pro 的 Agent/Coding，4x 推理速度，**6/24 新增 Computer Use 内置工具**）、Gemini Omni Flash（原生音视频），Gemini 3.5 Pro 预计 2026.06 发布

## 当前主推模型

| 模型 | 定位 | 核心特点 | 推出/更新时间 |
|------|------|------|------|
| **Gemini 3.1 Pro** | 旗舰（推理/知识密度最强） | 当前 Pro 级旗舰，学术推理与密集长上下文仍领先；Agent/Coding 已被 3.5 Flash 超越 | 2026.02.19 |
| **Gemini 3.5 Flash** | 轻量（高速低成本） | I/O 2026 首发，Flash 速度 + Pro 级 Agent/Coding benchmark，4x 速度 | 2026.05.19 |
| **Gemini Omni Flash** | 原生音视频多模态 | 端到端音频/视频原生理解，实时语音交互 | 2026.05.19 |
| **Gemini 3 Pro** | 上代旗舰 | 已被 3.1 Pro 超越 | 2026.01 |
| **Gemini 3.1 Flash** | 上代轻量 | 均衡性价比，适合批量推理 | 2026 Q1 |

> 📌 **历史模型**：Gemini 3 Pro / 3.1 Flash 仍可调用，但已分别被 3.1 Pro / 3.5 Flash 超越，不建议新项目选用

> ⚠️ Gemini 2.5 系列（Pro/Flash/Deep Think）为 2025 年中发布，**已非最新代**。2.5 Pro 更新至 2025.06.27，2.5 Flash 更新至 2025.09.26。详见 [Google DeepMind Model Cards](https://deepmind.google/models/model-cards/)

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **原生多模态** | 文本+图像+音频+视频统一理解与生成，不需要拼接多个模型 |
| **超长上下文** | 1M+ tokens，支持整仓库代码/超长文档一次性分析 |
| **Agent 基座** | Gemini Enterprise Agent Platform 的核心引擎，ADK 2.0 默认模型 |
| **Computer Use** | 3.5 Flash 内置计算机操控工具（2026.06.24），可跨浏览器/桌面/移动端自主操作 UI |
| **TPU 原生优化** | 在 TPU 8t/8i 上推理效率极致优化，推理性价比领先 |
| **MCP 原生支持** | 通过 MCP 协议调用 GCP 全系服务 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 部署方式 | 仅 API / GCP 平台 | 不支持私有化下载部署 |
| API 双轨 | `google.genai` + `vertexai` 两套 API | 开发者需根据场景选择，Google 已确认将长期共存 |
| 中文能力 | 强但非母语级 | 中文场景优先考虑 Qwen / DeepSeek 作为补充 |

## Gemini 3.5 Flash 深度分析

> 发布日期：2026.05.19（Google I/O 2026），GA 即日可用
> 定位：Flash 速度 + Pro 级 Agent/Coding 能力
> API Model ID：`gemini-3.5-flash`（GA，无 preview 后缀），内部版本 3.5-flash-05-2026

### 关键参数

| 参数 | 值 |
|------|------|
| 上下文窗口 | 1,048,576 输入 / 65,536 输出 tokens |
| 模态 | 文本+图像+音频+视频输入，文本输出 |
| Dynamic Thinking | 默认开启 |
| 知识截止 | 2026 年 1 月 |
| 推理速度 | 4x 于同级别前沿模型（Artificial Analysis 右上象限） |

### Benchmark 对比：Gemini 3.5 Flash vs Gemini 3.1 Pro（Google 自报）

**3.5 Flash 领先的 Coding & Agent 基准：**

| Benchmark | 3.5 Flash | 3.1 Pro | 差值 |
|-----------|-----------|---------|------|
| Terminal-Bench 2.1 | 76.2% | 70.3% | +5.9 |
| MCP Atlas | 83.6% | 78.2% | +5.4 |
| Finance Agent v2 | 57.9% | 43.0% | **+14.9**（最大单项差距） |
| GDPval-AA (Elo) | 1656 | 1314 | +342 |
| Toolathlon | 56.5% | 49.4% | +7.1 |
| SWE-Bench Pro (Public) | 55.1% | 54.2% | +0.9 |
| OSWorld-Verified | 78.4% | 76.2% | +2.2 |
| CharXiv Reasoning | 84.2% | 83.3% | +0.9 |
| MMMU-Pro | 83.6% | 80.5% | +3.1 |
| Blueprint-Bench 2 | 33.6% | 26.5% | +7.1 |

**3.1 Pro 仍领先的领域：**

| Benchmark | 3.5 Flash | 3.1 Pro | 差值 |
|-----------|-----------|---------|------|
| Humanity's Last Exam | 40.2% | 44.4% | -4.2 |
| ARC-AGI-2 | 72.1% | 77.1% | -5.0 |
| MRCR v2 · 128k | 77.3% | 84.9% | **-7.6**（密集长上下文回忆） |
| MRCR v2 · 1M | 26.6% | 26.3% | +0.3（几乎持平） |

### 定价

| 项目 | 3.5 Flash | 3.1 Pro | 对比 |
|------|-----------|---------|------|
| 输入（/1M tokens） | $1.50 | $2.50 | -40% |
| 输出（/1M tokens） | $9.00 | $15.00 | -40% |
| 缓存输入（/1M tokens） | $0.15（90% off） | — | — |
| 非全球区域输入 | $1.65 | — | — |
| 非全球区域输出 | $9.90 | — | — |

> 定价策略分析：比 3.1 Pro 便宜 40%，加 90% 缓存折扣。Agent 场景特征（多轮调用、系统提示复用）使有效价格远低于标价。直接对标 Claude Sonnet 4.6 和 GPT-5.5 的 Agent 份额。

### 战略意图

Google 将前沿能力线压到 Flash 层级，打破"Pro=难题, Flash=跑量"的二分法。在 Agent/Coding 工作负载上，Flash 首次超越自家上代 Pro。

- **Pro** 优化参数量 & 知识密度 → 学术推理占优
- **3.5 Flash** 优化工具调用链路 & 长程规划 → Agent 场景占优
- Finance Agent v2 的 +14.9 分暴涨是最强证据

### Computer Use 能力（2026.06.24 新增）

> 来源：[Google Blog — Introducing computer use in Gemini 3.5 Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-computer-use-gemini-3-5-flash/)

**功能更新，非新模型发布**——底层仍为 5 月 19 日 Google I/O 2026 发布的 Gemini 3.5 Flash。

| 维度 | 说明 |
|------|------|
| **能力** | Computer Use 成为 3.5 Flash 的内置工具（built-in tool），开发者可构建能"看、推理、行动"的 Agent |
| **跨平台** | 支持浏览器、桌面、移动端三种环境 |
| **前序** | 此前仅作为独立 Gemini 2.5 computer use 模型提供，现已原生集成到 Gemini Flash 主线 |
| **交付方式** | Gemini API + Gemini Enterprise Agent Platform |
| **OSWorld-Verified** | 78.4%（已在 benchmark 表中列出），接近 GPT-5.5 的 78.7% |

**安全机制**：
- 针对 prompt injection 风险进行定向对抗训练
- 两个可选企业级安全防护系统：敏感/不可逆操作需显式用户确认；检测到间接 prompt injection 时自动停止任务
- 建议结合安全沙箱、human-in-the-loop 验证和严格访问控制使用

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 多模态企业知识库 | 3.1 Pro | 图文音视统一理解，配合 Knowledge Catalog |
| Agent 规模化部署 | 3.5 Flash | 高吞吐、低延迟、Pro 级 benchmark，适合多 Agent 并发 |
| 复杂推理/编程 | 3.1 Pro | 对标 Claude Opus / GPT-5.x |
| 实时音视频交互 | Omni Flash | 原生端到端音频/视频理解 |
| 代码辅助 | 3.5 Flash | Flash 速度 + 超越 3.1 Pro 的 Agentic Coding |
| Google Workspace AI | 3.1 Flash / 3.1 Pro | 内嵌于 Gmail/Docs/Sheets 的 AI 能力 |

## 平台交付方式

Gemini 通过 **Gemini Enterprise Agent Platform** 统一交付（见 [`vertex-ai.md`](../ai-platform/vertex-ai.md)）。开发者可选两种接入路径：

| 路径 | 接口 | 适用 |
|------|------|------|
| **Gemini API / AI Studio** | `google.genai` | 快速原型、单次推理、个人开发者 |
| **Agent Platform** | `vertexai`（原 Vertex AI API） | 企业级 Agent 构建、生产部署、治理优化 |
| **Gemini App / Search AI Mode** | 消费者界面 | 默认模型（3.5 Flash），终端用户直接使用 |
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

| 弱点 | 说明 |
|------|------|
| 128k 密集上下文回忆 | MRCR v2 · 128k 输 3.1 Pro 7.6 分，"塞满 128k 全部精准回忆"场景慎用 |
| 学术推理 | Humanity's Last Exam 输 4.2 分、ARC-AGI-2 输 5.0 分，极难学术问题选 3.1 Pro 或等待 3.5 Pro |

> 📌 **Gemini 3.5 Pro 预期**：Google 确认 3.5 Pro 已在内部使用，预计 2026 年 6 月发布。

## 参考资料

- [Google Blog - Gemini 3.5](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-5/)
- [Google Blog — Introducing computer use in Gemini 3.5 Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-computer-use-gemini-3-5-flash/)
- [Gemini 3.5 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-5-flash/)
- [LLM Stats - Gemini 3.5 Flash Launch](https://llm-stats.com/blog/research/gemini-3.5-flash-launch)
- [Gemini Flash 产品页](https://deepmind.google/models/gemini/flash/)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-06-29 | 合并：Gemini 3.5 Flash Computer Use 官网调研 — 新增 Computer Use 内置工具章节（2026.06.24 发布，跨平台支持，安全机制），核心能力表新增 Computer Use 行，当前主推描述更新 |
| 2026-06-09 | 合并：Gemini 3.5 Flash 深度分析 — 补充 benchmark 详细对比表（vs 3.1 Pro）、定价、战略意图、Antigravity 2.0、Managed Agents、Gemini Spark、真实落地案例、诚实弱点、3.5 Pro 预期、参考资料 |
| 2026-06-09 | 修正：Gemini 3 Pro / 3.1 Pro 版本关系——3 Pro 为上代旗舰，3.1 Pro 为当前旗舰；适用场景表同步修正 |
| 2026-05-31 | 修正：Gemini 2.5→3.x 系列为最新代。新增 Gemini 3 Pro、3.5 Flash、Omni Flash、3.1 Pro/Flash。标注 Gemini 3.5 Pro 预计 2026.06 发布 |
