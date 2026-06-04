# 通义千问 (Qwen)

> 最后更新: 2026-06-04
> 所属厂商: 阿里云
> 产品类别: MaaS

**定位**: 阿里云自研大语言模型系列，覆盖文本/代码/多模态，开源+商业双轨并行
**当前主推**: Qwen3.7-Max（旗舰 Agent）/ Qwen3.7-Plus（多模态智能体）/ Qwen3.6-Flash（轻量快速）
**适用**: 企业级AI应用开发、智能对话、代码生成、多模态理解、长时间自主 Agent
**不适用**: 需要完全私有化且无网络的极端离线场景

## 当前主推模型

> 数据来源：[百炼模型广场](https://help.aliyun.com/zh/model-studio/models)，2026-06-04 核实

| 模型 | 定位 | 上下文 | 特点 |
|------|------|--------|------|
| **Qwen3.7-Max** | 旗舰 Agent | **1M tokens** | AA Intelligence Index 56.6–57（国产 #1），35小时自主运行，"The Agent Frontier" |
| **Qwen3.7-Plus** | 多模态智能体 | **1M tokens** | 原生多模态（图/视频/屏幕）+ GUI/CLI Agent + 视觉编码，纯文本接近 Max |
| **Qwen3.6-Flash** | 轻量快速 | 256K tokens | 速度快，成本低，系列内 Flash 仍延用 3.6 代号 |

> 📌 **历史模型**：Qwen3.6-Plus、Qwen3.6-Max-Preview 仍可调用，但已分别被 Qwen3.7-Plus 和 Qwen3.7-Max 取代，不建议新项目选用。

### Qwen3.7-Max

- **模型**：Qwen3.7-Max
- **公司**：阿里云
- **时间**：2026 年 5 月 19 日（阿里云峰会上线）
- **尺寸**：未公开（MoE架构）
- **上下文**：**1M tokens**，最大输出 65,536 tokens
- **定价**：¥12 / ¥36 per 1M input/output tokens；缓存输入 ¥1.2/M（90% 折扣）；5 折活动期间 ¥6/¥18，缓存 ¥0.6/M [来源: developer.aliyun.com/article/1738425]
- **新用户**：免费赠送 100 万 Tokens 试用额度 [来源: developer.aliyun.com/article/1738425]
- **接入**：仅 API（百炼 / DashScope），兼容 OpenAI 和 Anthropic 协议
- **开源**：否，非 open-weight
- **场景**：长时间自主 Agent、Agentic Coding、数学推理、多语言任务
- **定位**："The Agent Frontier"，专为长时自主执行设计的旗舰 Agent 模型

**关键基准**（vendor-published，vs Claude Opus 4.6）：
Terminal-Bench 2.0 **69.7**（+4.3）、SWE-Pro **60.6**（+3.3）、SWE-Verified 80.4 vs 80.8（平手）、HLE **41.4**（+1.4）、GPQA Diamond **92.4**（+1.1）、HMMT 2026 **97.1%**、IMOAnswerBench **90.0%**（+14.7）、Apex **44.5**（+10.0）

**标志性事件**：35 小时自主编码运行（1,158 次工具调用），GPU 内核优化达 10× 加速比（vs Triton 参考）

### Qwen3.7-Plus

- **模型**：Qwen3.7-Plus
- **公司**：阿里云
- **时间**：Preview 版 2026-05-19/20（阿里云峰会）；stable 快照 `qwen3.7-plus-2026-05-26`，2026-06-02 全量上线 [来源: https://qwen.ai/blog?id=qwen3.7-plus]
- **尺寸**：约 35B 密集架构（preview 阶段 CSDN/网易转述，stable 版官方未公布）[⚠️ 待补充]
- **上下文**：**1M tokens**（阶梯计价 0-256K / 256K-1M）[来源: https://help.aliyun.com/zh/model-studio/model-pricing]
- **输入模态**：文本 + 单图/多图/视频 + 屏幕截图 [来源: https://qwen.ai/blog?id=qwen3.7-plus]
- **场景**：多模态智能体（GUI + CLI 闭环）、视觉编码（图→SVG/网页/前端）、视觉推理、真实世界感知
- **特点**：
  - 多模态智能体：GUI/CLI 操作 + 视觉编码 + 跨框架部署（Claude Code / OpenClaw / Qwen Code）
  - `preserve_thinking` 多轮思维保留
  - 纯文本能力官方称"整体接近 Max 级别"
  - **多模态/GUI 操作为 Qwen3.7 系列最强**
- **定价**：¥2/¥8 per 1M input/output tokens（≤256K）；¥6/¥24（256K-1M）；思考与非思考同价 [来源: https://help.aliyun.com/zh/model-studio/model-pricing]
  - Batch 调用 5 折；输入支持上下文缓存折扣（与 Batch 不可叠加）
  - 推理后付费限时 8 折至 2026-07-02
- **开源**：否，API 商用闭源（仅通过百炼提供）[来源: https://www.aihub.cn/ai-model/qwen3-7-plus/]
- **Benchmark**：SWE-bench Verified ~68.7%；Arena 综合 1156（均为 preview 阶段第三方数据）[⚠️ stable 版待验证]

> ⚠️ stable 版 benchmark 与精确参数官方尚未公布，建议关注 artificialanalysis.ai / LMSYS Arena 后续复测。

**系列定位分工**：
- **Qwen3.7-Max** = 文本 / Agentic Coding 旗舰（1M 全段无阶梯）
- **Qwen3.7-Plus** = 多模态智能体（视觉 + 语言 + GUI/CLI + 视觉编码）
- **Qwen3.6-Flash** = 低成本快速档（系列内未推 3.7-Flash，Flash 仍延用 3.6 代号）

**竞争力要点**：
- vs Qwen3.6-Plus（上一代）：输出价从 ¥12 降至 ¥8（-33%），256K-1M 输出从 ¥48 降至 ¥24（-50%），能力升级同时降价
- vs Qwen3.7-Max：256K 内输入成本仅为 Max 的 1/6、输出约 1/4.5；Max 仅在 SWE-bench/复杂长链路 Agentic Coding 上明显占优
- vs 海外同档（Claude Haiku 4 / GPT-4o-mini）：价位接近，但 Plus 独有 1M 上下文 + 多模态智能体组合

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **深度推理（Max）** | AA Intelligence Index 56.6–57（国产 #1），数学/科学推理全球领先 |
| **Agentic Coding** | Terminal-Bench 2.0 69.7，SWE-Pro 60.6；35小时自主编码运行 |
| **超长上下文** | 1M tokens 上下文窗口，处理大型代码仓库和长文档 |
| **多模态智能体（Plus）** | Qwen3.7-Plus 支持图/视频/屏幕输入 + GUI/CLI Agent + 视觉编码；Qwen3.7-Max 仅文本 |
| **数学能力** | HMMT 2026 97.1%、IMOAnswerBench 90.0%，竞赛数学断层领先 |
| **多语言** | WMT24++ 85.8%，覆盖 55 种语言，多语言能力领先 |
| **开源生态** | 多尺寸开源，社区活跃（3.7-Max 除外，为 API only） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 3.7-Max 开源 | 不开放 | API only，无法私有化部署或微调 |
| 3.7-Max 多模态 | 仅文本 | 不支持图像输入（Plus-Preview 支持） |
| 3.7-Max 输出冗长 | 97M vs 中位 24M | 实际输出成本可达同类模型的 2-4× |
| 3.6-Max 上下文 | 256K tokens | 仅为 Plus/3.7 的 1/4 |
| 3.6-Max 稳定性 | Preview 状态 | 尚未正式 GA，生产环境建议 Plus 或 3.7-Max |
| 并发限制 | 按账户等级 | 企业版更高 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 长时间自主 Agent / 数学竞赛 / 科研推理 | **3.7-Max** | 35h 自主运行，HMMT 97.1%，全球领先 |
| Agentic Coding（重度） | **3.7-Max** | Terminal-Bench 69.7 |
| Agentic Coding（性价比）/ 长文档 / 多模态 / 生产环境 | **3.7-Plus** | GA 稳定，支持图像/视频/屏幕，1M 上下文，GUI/CLI Agent |
| 高并发轻量调用 | **3.6-Flash** | 低延迟低成本 |
| 私有化部署 | 3.6 开源版 | 支持本地部署 |

## 接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| API 直接调用 | DashScope API，兼容OpenAI格式 | 快速集成 |
| 平台托管 | 百炼平台，可视化编排 | 企业级应用 |

## 定价（API）

| 模型 | 输入（¥/1M tokens） | 输出（¥/1M tokens） | 缓存输入 |
|------|---------------------|---------------------|----------|
| **Qwen3.7-Max** | ¥12 | ¥36 | ¥1.2 |
| Qwen3.7-Max（5折） | ¥6 | ¥18 | ¥0.6 |
| **Qwen3.7-Plus** | ¥2 | ¥8 | — |
| **Qwen3.6-Flash** | [查看定价](https://help.aliyun.com/zh/model-studio/model-pricing) | — | — |

> Qwen3.7-Max 实际成本需关注输出冗长问题：评估中生成量是中位数的 4×，建议 prompt 中显式约束输出长度。

## 竞品定价对比（参考）

| 模型 | 输入（¥/M tokens） | 输出（¥/M tokens） | 缓存 | 来源 |
|------|-------------------|-------------------|------|------|
| **Qwen3.7-Max** | ¥12 | ¥36 | ¥1.2 | developer.aliyun.com |
| DeepSeek-V4-Pro | ¥3 | ¥6 | ¥0.025 | api-docs.deepseek.com |
| GLM-5.1（智谱） | ¥6（32K以内）/ ¥8 | ¥24 | ~¥3.4（$0.475） | open.bigmodel.cn |
| GPT-5.5 | $5（≈¥36） | $30（≈¥216） | $0.50 | apidog.com (AA) |
| Claude Opus 4.7 | $6.25（≈¥45） | $25（≈¥180） | $0.50 | apidog.com (AA) |

> Qwen3.7-Max 单价高于 DeepSeek-V4-Pro（4×）和 GLM-5.1（2×），但 Agent 场景（Terminal-Bench 2.0 69.7 vs GLM-5.1 63.5）、1M 上下文（vs GLM-5.1 128K）、35h 长时执行是核心差异点。

## 参考资料

- https://artificialanalysis.ai/models/qwen3-6-max （AA独立评测，Intelligence Index #2）
- https://apidog.com/blog/qwen-3-7-vs-gpt-5-5-vs-opus-4-7/ （Qwen3.7-Max vs GPT-5.5 vs Opus 4.7 三方对比，AA Index 57 / #1）
- https://developer.aliyun.com/article/1738425 （百炼 Qwen3.7-Max RMB 定价详解）
- https://www.datalearner.com/ai-models/compare/qwen3-7-max-preview/vs/glm-5-1 （Qwen3.7 vs GLM-5.1 Benchmark 对比）
- https://artificialanalysis.ai/models/comparisons/qwen3-6-plus-vs-qwen3-max-thinking-preview
- https://hub.baai.ac.cn/view/53628 （智源社区评测文章）
- https://qwen.ai/blog?id=qwen3.6 （Qwen官方博客）
- agentic LLM参考: https://artificialanalysis.ai/models?intelligence=coding-index
- [通义千问官网](https://tongyi.aliyun.com)
- [百炼平台](https://bailian.console.aliyun.com)
- [Qwen GitHub](https://github.com/QwenLM)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-06-04 | 主推模型表更新：移除已取代的 Qwen3.6-Plus / Qwen3.6-Max-Preview，主推表仅保留百炼在售的 3 个模型（Qwen3.7-Max / Qwen3.7-Plus / Qwen3.6-Flash）；历史模型单独标注 |
| 2026-05-31 | 合并：inbox 素材 — 新增百炼 RMB 定价（¥12/¥36，5折 ¥6/¥18）、竞品定价对比表（DS-V4-Pro/GLM-5.1/GPT-5.5/Opus 4.7）、新用户 100 万 tokens 免费额度 |
| 2026-05-31 | 新增 Qwen3.7-Max（2026.05.19 发布），包含关键基准、AA Intelligence Index 56.6、35h 自主运行、定价、局限；更新模型表、能力/场景/限制/定价；标注 Qwen3.6-Max 被 3.7-Max 取代 |
| 2026-04-24 | 合并 qwen3.6.md 内容，补充 Qwen3.6-Max-Preview 详细信息和对比分析 |
| 2026-04-20 | 按_maas_template重构，对齐模板结构 |
