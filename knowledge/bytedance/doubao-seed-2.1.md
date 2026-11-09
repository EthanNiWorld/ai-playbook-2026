# Doubao-Seed-2.1

> 最后更新: 2026-11-10
> 所属厂商: 字节跳动 / ByteDance Seed
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 面向 Coding 和 Agent 时代的生产级大模型系列，2026-06-23 火山引擎 FORCE 大会发布
**适用**: Agentic Coding、长链路 Agent 自主执行、多模态理解、GUI Agent
**不适用**: 需要超长上下文（>1M）的场景（260628 旧版为 >256K）
**竞品**: Qwen3.8-Max、GPT-5.5、Claude Opus 4.7、Gemini 3.1 Pro
**常搭配**: TRAE IDE、豆包办公模式、火山方舟 API
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

Doubao-Seed-2.1 是字节跳动面向 Coding + Agent 场景打造的新一代大模型系列，提供 Pro（旗舰）和 Turbo（轻量）两个版本，在 Agent 端到端交付能力上进入全球第一梯队。

### 底层原理（通俗版）

- **MoE 架构**（参数规模未公开），在有限窗口内做深——优化 Agent 长时间迭代、多步工具调用
- **原生多模态**：文本 + 图像 + 视频输入，支持视觉理解驱动的 Agent 任务
- **深度思考模型**：支持 `reasoning_effort` 参数（minimal/low/medium/high），控制推理深度
- **设计取舍**：首发版选择 256K 上下文 + 深度 Agent 能力；0915 新版起升级 1M，转向深度与广度兼顾

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 上下文窗口 | 260628：256K；0915 / Evolving：**1M** | 0915 起不再是限制；仅 260628 旧版无法一次性加载大型 monorepo |
| 架构参数 | 未公开 | MoE 架构，具体总参数量和激活参数量未知 |
| 生态绑定 | 火山方舟 | API 仅在火山方舟上线，第三方集成便利性待观察 |

## 当前主推模型

| 模型 | 定位 | 上下文 | 输入价 | 输出价 | 特点 |
|------|------|--------|--------|--------|------|
| 🚩 **Doubao-Seed-2.1 Pro（0915）** | 旗舰·当前主推 | **1M** | ¥6/M | ¥30/M | 2026-09-15 全量：Agent 可靠性 / 多模态 Coding / 3D 理解增强 |
| **Doubao-Seed-2.1 Pro（260628）** | 旗舰·首发版 | 256K | ¥6/M | ¥30/M | 本文 benchmark 口径版本 |
| **Doubao-Seed-Evolving** | 快速迭代（官方"Seed 最新 Coding&Agent 模型"） | 1M | ¥6/M | ¥30/M | 持续更新，聚焦 Coding & Agent |
| **Doubao-Seed-2.1 Turbo** | 轻量 | 256K | ¥3/M | ¥15/M | 低成本低延迟，效果比肩 Pro |

> 来源：[火山引擎定价](https://www.volcengine.com/product/doubao)；[火山方舟模型文档](https://www.volcengine.com/docs/82379/2549861)

### 关键基准（vendor-published）

> ⚠️ 以下 benchmark 均为 **260628 首发版**口径；0915 新版与 Evolving 官方未发布完整 benchmark。

**Coding**：

| Benchmark | Pro | 对标竞品 |
|-----------|:---:|---------|
| Terminal Bench 2.1 | **71.0** | GPT-5.5: 73.8, Claude Opus 4.7: 71.7, Gemini 3.1 Pro: 70.7 |
| SWE-bench Pro | **57.5** | GPT-5.5: 58.6, Claude Opus 4.7: 64.3, Gemini 3.1 Pro: 54.2 |
| NL2Repo-Bench | 表现良好 | 自然语言→仓库级代码改动 |
| Code Arena Frontend | #8 (1539 Elo) | 前端开发 |

> 来源：[Seed 官方博客](https://seed.bytedance.com/zh/blog/seed2-1-officially-released-advancing-ai-productivity)；用户提供的 Benchmark 截图

**Agent**：

| Benchmark | Pro | 说明 |
|-----------|:---:|------|
| GDPval | 参评模型最高分 | 衡量真实工作任务的经济价值 |
| Agents' Last Exam (ALE) | 第一梯队 | 新 benchmark，各模型难以定向刷分 |
| MobileWorld | 最高分 | 手机端 GUI Agent |
| OSWorld | 保持竞争力 | 桌面端 Agent，平均步数减 16% |
| 众测 vs Claude Opus 4.6 | 胜率 59.1% | 真实代码仓库工程任务 |

> 来源：[Seed 官方博客](https://seed.bytedance.com/zh/blog/seed2-1-officially-released-advancing-ai-productivity)

**多模态与推理**：

- CharXiv-RQ / MeasureBench：SOTA（复杂文档理解、图表读取）
- MMLongBench-128K：突出（长上下文）
- TVBench / TOMATO：业界高分（视频理解）
- SciCode / FrontierScience-Olympiad：良好（科研推理）

### Doubao-Seed-2.1-Pro 0915 新版（2026-09-15 全量上线）

- **时间**：2026-09-15/16 官宣，API 已在火山方舟**全量上线**；豆包工作内已同步升级
- **升级聚焦**：
  1. **Agent 任务可靠性**增强
  2. **多模态 Coding**（"看图写代码"）
  3. **3D 理解**
- **效率**：Token 效率优化，**图像推理成本降约三成**
- **上下文**：**256K → 1M**（最大输入 1024K、最大回答/思维链 256K）✅ 火山方舟官方模型列表确证（2026-11-10 核实）
- **定价**：Pro ¥6/¥30、Turbo ¥3/¥15 未变（火山引擎产品页口径一致）
- **来源**：功能升级为 ℹ️ 第三方媒体多源一致（21世纪经济报道 / 财联社 / 我的钢铁网，2026-09-16）；上下文规格 ✅ [火山方舟模型列表](https://www.volcengine.com/docs/ark/model-list) 一手确证；0915 版完整 benchmark 官方未发布，本文 Coding/Agent 分数仍为 260628 口径 [⚠️ 待补充]

### Doubao-Seed-Evolving（2026-06-23 上线）

- **模型**：doubao-seed-evolving，火山方舟官方标注"**Seed 最新 Coding&Agent 模型**"（快速迭代通道，持续更新）
- **时间**：2026-06-23 上线（与 2.1 系列同批 FORCE 大会时间窗）
- **定位**：Coding / Agent 场景；能力标签与 0915 Pro 一致（深度思考 / 多模态理解 / GUI 任务处理 / 工具调用 / 结构化输出）
- **上下文**：**1M**（最大输入 1024K、最大回答/思维链 256K）
- **限流**：RPM 500 / TPM 1,000,000（与 Pro 相同）
- **定价**：¥6/¥30（输入/输出，每百万 tokens）
- **来源**：✅ [火山方舟模型列表](https://www.volcengine.com/docs/ark/model-list)（2026-11-10 核实，一手确证）；架构、benchmark 官方未发布 [⚠️ 待补充]

## 适用边界分析

### ✅ 适用场景

| 场景 | 说明 | 典型客户/案例 |
|------|------|--------------|
| 从零搭建新项目 | NL2Repo 能力突出，端到端工程交付 | 创业团队 / 快速原型 |
| 长链路 Agent 自主执行 | GDPval 最高分，18h 连续运行芯片设计 | 自动化运维 / DevOps |
| 多模态开发（看截图写代码） | 原生视觉输入，无需额外多模态模型 | 前端开发 / UI→Code |
| GUI Agent（手机+桌面） | MobileWorld 最高分，OSWorld 竞争力 | RPA / 自动化测试 |
| 成本敏感的生产场景 | Turbo ¥3/¥15，价格极具竞争力 | 高并发企业调用 |

### ❌ 不适用场景

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 重度 Bug 修复（SWE-Pro 类） | SWE-Pro 57.5（260628 口径），落后 Claude Opus 4.7 约 7 分 | Claude Opus 4.7 / Qwen3.8-Max |
| 超长文档处理（>1M tokens） | 0915 / Evolving 上限 1M；260628 旧版仅 256K | Gemini 3.1 Pro（2M） |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| SWE-Pro 低 = Coding 能力弱 | SWE-Pro 只测"修复已有代码 Bug"，Doubao 在端到端工程交付（NL2Repo）和 Agent 规划（GDPval）上更强 |
| 上下文仍是 256K | 仅 260628 首发版为 256K；0915 新版与 Evolving 已升级 1M（火山方舟官方模型列表确证） |
| 价格低 = 能力差 | 价格约为 Claude Opus 4.7 的 1/18，但在 Agent 端到端交付上与 Claude 接近 |

## 关键配置与最佳实践

### reasoning_effort 参数

| 任务类型 | 推荐值 | 说明 |
|---------|--------|------|
| 任务规划/架构设计 | high | 深度思考，复杂决策 |
| 代码生成/Bug修复 | high 或 medium | 平衡质量与速度 |
| 工具调用决策 | medium | Agent loop 中频繁调用，控制延迟 |
| 格式转换/提取 | low 或 minimal | 简单任务无需深度思考 |
| 简单分类/路由 | minimal | 不思考直出，成本最低 |

### 踩坑记录

| 问题 | 原因 | 解决方案 | 记录日期 |
|------|------|----------|----------|

## 竞品快速对照

| 维度 | Doubao-Seed-2.1 Pro（260628） | Qwen3.8-Max | Claude Opus 4.7 |
|------|:---:|:---:|:---:|
| TB 2.1 | 71.0 | **86.6** | 71.7 |
| SWE-Pro | 57.5 | **67.7** | 64.3 |
| 上下文 | 256K（0915 起 1M） | 1M | 200K |
| 输入价 | ¥6/M | ¥12/M | ~¥45/M |
| 输出价 | ¥30/M | ¥36/M | ~¥180/M |
| 视觉输入 | ✅ 原生 | ✅ 文本+图像（实测） | ✅ |
| Agent 规划 | GDPval 最高分 | — | — |

## 参考资料

- [ByteDance Seed 官方博客 - Seed2.1 正式发布](https://seed.bytedance.com/zh/blog/seed2-1-officially-released-advancing-ai-productivity)
- [火山方舟模型文档](https://www.volcengine.com/docs/82379/2549861)
- [火山方舟模型列表](https://www.volcengine.com/docs/ark/model-list)
- [火山引擎产品定价](https://www.volcengine.com/product/doubao)
- [IT之家报道](https://www.ithome.com/0/967/314.htm)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-11-10 | 竞品口径升级：竞品快速对照表、SUMMARY 竞品行与不适用场景替代方案中的 Qwen3.7-Max 替换为 Qwen3.8-Max（TB 2.1 86.6 / SWE-Pro 67.7，Qwen 官方博客；定价 ¥12/¥36 与 3.7 同价经百炼定价页 2026-11-10 核实；视觉为 API 实测口径）；Claude Opus 4.7 列保留未核实 |
| 2026-11-10 | 时效修复：0915 新版与 Evolving 上下文升级 1M 获火山方舟官方模型列表一手确证（最大输入 1024K、思维链 256K）；Evolving 补"Seed 最新 Coding&Agent 模型"官方定位与限流规格；主推模型表拆分 Pro 260628/0915 双版本并收录 Evolving；benchmark 统一标注 260628 口径；删除 256K 限制衍生的不适用场景与误解条目 |
| 2026-09-17 | 合并：knowledge-verification-2026-09-17 报告 — 新增「Doubao-Seed-2.1-Pro 0915 新版」小节（2026-09-15/16 火山方舟全量上线：多模态 Coding 看图写代码 / 3D 理解 / Agent 可靠性 / 图像推理成本降约三成，ℹ️ 第三方媒体多源口径待官方文档确证）+「Doubao-Seed-Evolving」条目（¥6/¥30，2026-06-23 上线，火山产品页收录）；定价 ¥6/¥30、¥3/¥15 未变复核一致 |
