# 推理深度控制（reasoning_effort / thinking_budget）

> 最后更新: 2026-08-17
> 领域: AI Engineering / LLM
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: reasoning_effort / thinking_level 是 2026 年推理模型的标配能力，四家主流已收敛到**三级离散档位**范式，在"思考质量 vs 成本延迟"的 Pareto 前沿上提供动态调节点
**核心价值**: Agent 场景下，Harness 应根据当前步骤难度动态选择 thinking depth——规划用 high，工具调用用 medium，格式转换用 low
**相关产品**: [Qwen](../../alibaba-ai-hub/maas/qwen.md), [Claude API](../anthropic/claude-api.md), [GPT-5 系列](../openai/gpt-5-series.md), [DeepSeek V 系列](../deepseek/deepseek-v-series.md), [GLM 系列](../zhipu/glm-series.md), [Gemini](../google/maas/gemini.md)
<!-- SUMMARY_END -->

## 是什么

推理深度控制（thinking depth control）是大模型提供的一种机制，允许调用方动态调整模型在回答前的"思考量"。核心目标是在推理质量和成本/延迟之间找到最佳平衡点。

2026 年，这一能力已成为所有主流推理模型的**标配**——没有 reasoning_effort 控制的推理模型被视为不完整。

## 核心原理

### 核心矛盾

深度思考的推理模型，output token 暴增 → **成本和延迟飙升**。但绝大多数日常查询根本不需要"想 5 分钟"。reasoning_effort 参数让用户/系统可以按需调节思考深度。

### 三层权衡逻辑

1. **经济性** — 思考 token 也是钱。简单查询触发 2000 token 思考链是纯浪费。`minimal` 模式让简单任务"不思考直出"，成本可降 5-10 倍
2. **延迟敏感** — Agent 场景中一个 loop 可能调用模型 50+ 次，每次都深度思考会让 18h 任务变成 72h
3. **质量-速度 Pareto 前沿** — 简单分类/提取任务中，思考越多反而越容易"想偏"（overthinking degradation）

## 各厂商实现对照

| 厂商/模型 | 参数名 | 可选值 | 默认 | 备注 |
|-----------|--------|--------|------|------|
| **Gemini 3.7 Flash** (2026.08) | `thinking_level` | **low / medium / high** | medium | ⭐ **取代旧版 `thinking_budget` 数值型**；`temperature`/`top_p`/`top_k` 同步废弃 [来源: blog.google 2026-08-13] |
| **DeepSeek V4-Pro GA** (2026.08) | `reasoning_effort` | **low / high / max** | high | V4-Pro + V4-Flash 统一三级；V4-Flash-0731 同步支持 [来源: api-docs.deepseek.com] |
| **GLM-5.3** (2026.08) | `reasoning_effort` | **low / high / max** | max | 始终启用思考，不支持禁用；`thinking.type` 必须为 `enabled` [来源: docs.bigmodel.cn] |
| **Qwen3.8-Max** (2026.08) | `reasoning_effort` | 多级（具体档位待确认） | — | 开源版同步支持；`preserve_thinking` 可跨轮保留推理上下文 [来源: qwen.ai/blog] |
| Doubao-Seed-2.1 Pro | `reasoning_effort` | minimal / low / medium / high | high | minimal = 不思考（四级，含"不思考"档） |
| OpenAI o-系列 / GPT-5.5 | `reasoning_effort` | low / medium / high | medium | 最早引入此概念 |
| Claude Opus 5 / Fable 5 | `budget_tokens`（extended thinking） | 数值型（1024~128K） | — | 仍保持连续数值控制，是少数未切换到离散档位的厂商 |
| ~~Gemini 3.1~~ (旧版) | ~~`thinking_config.thinking_budget`~~ | ~~数值型（0~24576）~~ | ~~自动~~ | **已被 3.7 Flash 的 `thinking_level` 取代** |
| ~~DeepSeek-V4 Preview~~ (旧版) | ~~`thinking` on/off + `max_thinking_tokens`~~ | ~~开关 + 数值~~ | ~~默认开启~~ | **已被 GA 版三级 `reasoning_effort` 取代** |
| ~~Qwen3.7 系列~~ (旧版) | ~~`enable_thinking` + `thinking_budget`~~ | ~~开关 + 数值~~ | ~~开启~~ | **已被 3.8 系列 `reasoning_effort` 取代** |

## 设计哲学差异

- **离散档位**（OpenAI / DeepSeek / GLM / Gemini 3.7 / Qwen3.8）：对开发者更友好，不需要调参，"选一个档就行"——适合 Agent 框架快速集成
- **连续数值**（Anthropic Claude 系列）：给高级用户精细控制权，适合研究/极致优化场景

### 2026-08 趋势：三级离散已成事实标准

> ⭐ **2026 年 8 月是关键拐点**：Gemini 3.7 Flash 从数值型 `thinking_budget` 切换到三值 `thinking_level`，标志着行业从"连续数值 → 离散档位"的范式转变基本完成。

截至 2026-08-17，四家主流厂商在**同一个月内**全部收敛到三级离散档位：

| 厂商 | 模型 | 三档位 | 发布时间 |
|------|------|--------|----------|
| Google | Gemini 3.7 Flash | low / medium / high | 2026-08-13 |
| DeepSeek | V4-Pro GA / V4-Flash GA | low / high / max | 2026-08-13 / 07-31 |
| 智谱 | GLM-5.3 | low / high / max | 2026-08-14 |
| 阿里云 | Qwen3.8-Max | `reasoning_effort` 多级 | 2026-08-12 |

**为什么收敛到三级而非二级或五级**：
- 二级（on/off）太粗——Agent 场景中"中等复杂"任务占比最大，需要中间档
- 五级及以上（如 Doubao 四级）增加选择负担，开发者实测难以区分相邻档位差异
- 三级恰好对应 Agent 工作流的三种典型模式：快速路由（low）/ 日常执行（medium/high）/ 极端难题（max/high）

**Gemini 3.7 Flash 的附加变化**（值得关注的 API 设计趋势）：
1. `temperature` / `top_p` / `top_k` **已废弃**——推理模型正在接管采样参数的控制权
2. **Server-side `previous_interaction_id`**：服务端保存对话状态，客户端仅发送新 turn，大幅降低多轮 Agent 会话的输入 token 开销 [来源: Google AI for Developers 文档]

## 关键认知框架

### 核心洞察 1：thinking depth 应由 Harness 动态控制

- **洞察内容**：Agent 场景中，不是所有步骤都需要同等深度的思考。Harness（而非用户）应根据当前步骤的任务类型动态选择 reasoning_effort
- **为什么重要**：固定 high 模式导致 Agent 整体执行时间膨胀 3-4 倍，且不必要地增加 overthinking 风险
- **可迁移场景**：任何多步 Agent 系统（Coding Agent / RPA / 数据分析 pipeline）

### 核心洞察 2：overthinking degradation 真实存在

- **洞察内容**：简单任务用 deep thinking 反而比 shallow thinking 效果更差——模型容易"想偏"或过度分析
- **为什么重要**：这颠覆了"思考越多越好"的直觉，要求系统设计中主动抑制不必要的推理
- **可迁移场景**：分类器、路由器、格式转换器等确定性任务

## 最佳实践

### Agent 场景 thinking depth 推荐

| 任务类型 | 推荐 thinking depth | 说明 |
|---------|-------------------|------|
| 任务规划/架构设计 | high | 需要深度推理和全局视野 |
| 代码生成/Bug修复 | high 或 medium | 平衡质量与速度 |
| 工具调用决策 | medium | Agent loop 中频繁调用，控制延迟 |
| 格式转换/信息提取 | low 或 minimal | 简单任务无需深度思考 |
| 简单分类/路由 | minimal | 不思考直出，成本最低 |

## 常见误区

| 误区 | 事实 |
|------|------|
| 思考越多效果越好 | 简单任务中 deep thinking 会导致 overthinking degradation，效果反而下降 |
| reasoning_effort 只影响速度 | 它同时影响质量和成本，是一个三维 trade-off |
| 所有任务应该用同一个 thinking depth | Agent 场景应根据步骤类型动态调整，固定 high 会膨胀 3-4 倍执行时间 |

## 参考资料

- [火山方舟模型文档 - Doubao-Seed-2.1 Pro reasoning_effort](https://www.volcengine.com/docs/82379/2549861)
- [Gemini 3.7 Flash 官方博客](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-3-7-flash/) — `thinking_level` 取代 `thinking_budget`，2026-08-13
- [DeepSeek API Changelog](https://api-docs.deepseek.com/updates/) — V4-Pro GA / V4-Flash GA 三级 `reasoning_effort`，2026-08-13 / 07-31
- [GLM-5.3 官方文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3) — `reasoning_effort` low/high/max，始终启用思考
- [Qwen3.8-Max 官方博客](https://qwen.ai/blog?id=qwen3.8) — `reasoning_effort` + `preserve_thinking`
- 各厂商官方 API 文档（OpenAI / Anthropic）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-08-17 | 补充 Gemini 3.7 Flash `thinking_level` 三值范式（取代旧版 `thinking_budget`）；新增"三级离散已成事实标准"趋势分析（四家同月收敛）；DeepSeek V4 GA / GLM-5.3 / Qwen3.8 实现更新；旧版条目划线标注取代关系；`temperature` 废弃 + `previous_interaction_id` 服务端状态补充 |
| 2026-06-26 | 初始创建：从 inbox 概念洞察提炼，含各家实现对比、设计哲学差异、Agent 最佳实践 |
