# 推理深度控制（reasoning_effort / thinking_budget）

> 最后更新: 2026-06-26
> 领域: AI Engineering / LLM
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: reasoning_effort / thinking_budget 是 2026 年推理模型的标配能力，在"思考质量 vs 成本延迟"的 Pareto 前沿上提供动态调节点
**核心价值**: Agent 场景下，Harness 应根据当前步骤难度动态选择 thinking depth——规划用 high，工具调用用 medium，格式转换用 minimal
**相关产品**: [Qwen](../../alibaba-ai-hub/maas/qwen.md), [Claude API](../anthropic/claude-api.md), [GPT-5 系列](../openai/gpt-5-series.md), [Doubao-Seed-2.1](../bytedance/doubao-seed-2.1.md)
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
| Doubao-Seed-2.1 Pro | `reasoning_effort` | minimal / low / medium / high | high | minimal = 不思考 |
| OpenAI o-系列 / GPT-5.5 | `reasoning_effort` | low / medium / high | medium | 最早引入此概念 |
| Claude Opus 4.7 | `budget_tokens`（extended thinking） | 数值型（1024~128K） | — | 更精细的 token 级控制 |
| DeepSeek-V4 | `thinking` on/off + `max_thinking_tokens` | 开关 + 数值 | 默认开启 | 混合模式 |
| Qwen3.7 系列 | `enable_thinking` + `thinking_budget` | 开关 + 数值 | 开启 | 类似 DeepSeek |
| Gemini 3.1 | `thinking_config.thinking_budget` | 数值型（0~24576） | 自动 | 0 = 不思考 |

### 设计哲学差异

- **离散档位**（字节/OpenAI）：对开发者更友好，不需要调参，"选一个档就行"——适合 Agent 框架快速集成
- **连续数值**（Anthropic/Google）：给高级用户精细控制权，适合研究/极致优化场景
- 最终趋势是**两者融合**——提供语义化档位作为快捷方式，同时暴露底层数值接口

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
- 各厂商官方 API 文档（OpenAI / Anthropic / Google / DeepSeek / Qwen）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-06-26 | 初始创建：从 inbox 概念洞察提炼，含各家实现对比、设计哲学差异、Agent 最佳实践 |
