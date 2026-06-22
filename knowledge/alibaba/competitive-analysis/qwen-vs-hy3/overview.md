# Qwen3.7 vs Hy3-preview 竞争分析

> 最后更新: 2026-06-22
> 状态: Published

<!-- SUMMARY_START -->
**核心差异**: Qwen3.7 系列（Max/Plus）在上下文（1M vs 256K）、深度编码（Terminal-Bench 69.7% vs 54.4%）和多模态（Plus 原生视觉）上不可替代；Hy3-preview 在性价比（价格约 1/19）和开源可部署性上碾压
**我方优势**: 1M 上下文、深度编码断层领先、多模态能力、长时 Agent（35h 自主运行）
<!-- SUMMARY_END -->

## 概览对比

| 维度 | Qwen3.7-Max | Qwen3.7-Plus | Hy3-preview |
|------|-------------|--------------|-------------|
| 厂商 | 阿里云 | 阿里云 | 腾讯混元 |
| 定位 | 旗舰 Agent "The Agent Frontier" | 多模态智能体 | 高性价比通用推理+Agent底座 |
| 上下文 | **1M** | **1M** | 256K |
| 多模态 | 纯文本¹ | **图/视频/屏幕** | 纯文本 |
| 开源 | 否 | 否 | **是** |
| 输入价格 | ¥12/M（5折 ¥6） | ¥2/M | **≈¥0.5/M** |
| 输出价格 | ¥36/M（5折 ¥18） | ¥8/M | **≈¥1.9/M** |
| 长时 Agent | **35h / 1,158 次工具调用** | GUI/CLI Agent | 495 步工作流 |

> ¹ `qwen3.7-max` 默认指针仍指向 2026-05-20 快照（纯文本），但 `qwen3.7-max-2026-06-08` 快照已支持视觉输入（图像/视频）。

## Benchmark 对比

| Benchmark | Hy3-preview | Qwen3.7-Max | Qwen3.7-Plus |
|-----------|-------------|-------------|--------------|
| SWE-bench Verified | 74.4% | **80.4%** | ~68.7%（preview） |
| Terminal-Bench 2.0 | 54.4% | **69.7%** | — |
| AIME 2026 | 89.2% | — | — |
| GPQA Diamond | 87.2% | **92.4%** | — |
| BrowseComp | **67.1%** | — | — |
| OpenRouter 工具调用 | **#1** | 未上榜 | 未上榜 |
| OpenRouter Coding | **#2** | 未上榜 | 未上榜 |

## 选型建议

| 场景 | 推荐 | 理由 |
|------|------|------|
| 个人/小团队 Agent 开发，预算敏感 | Hy3-preview | 性价比碾压，Agent 能力够用 |
| 企业级 Agentic Coding，长时自主 | Qwen3.7-Max | 编码 Benchmark 断层领先，1M 上下文 |
| 多模态 Agent（GUI/视觉/屏幕） | Qwen3.7-Plus | Hy3 无多模态能力 |
| 大型代码仓库/超长文档 | Qwen3.7-Max/Plus | 1M vs 256K 上下文差距 |
| 私有化部署/二次开发 | Hy3-preview | 开源+21B 激活，部署成本低 |

## SA 销售打法建议

### 我方优势切入点

1. **上下文鸿沟**：1M vs 256K = 4 倍差距，大型代码仓库和超长文档场景无法替代
2. **深度编码领先（Max）**：Terminal-Bench 69.7% vs 54.4%，差 15.3 个百分点，复杂重构更可靠
3. **长时 Agent（Max）**：35 小时自主运行 / 1,158 次工具调用是极端场景验证，Hy3 的 495 步无法比拟
4. **多模态（Plus）**：图/视频/屏幕输入 + 视觉编码，纯文本模型完全无法替代

### 对方薄弱环节

- 上下文仅 256K，无法处理大型代码仓库或超长文档
- 纯文本模型，无多模态能力
- 无长时自主运行验证（仅 495 步工作流 vs 35h）

### 建议话术要点

> "Hy3-preview 确实性价比高，适合个人开发者和小团队的轻量 Agent 场景。但企业级场景的核心诉求是**可靠性和能力上限**——1M 上下文处理整仓代码、35 小时无人值守编程、多模态 GUI 操作，这些 Hy3 做不到。两者不在同一赛道竞争。"

## 底层逻辑

> 这是"中等体量高效推理"vs"大体量极致能力"的经典路径之争。Hy3-preview 证明了 DeepSeek 式的"效率优先"路线可以在 OpenRouter 这类开发者市场取得商业成功；Qwen3.7 系列则在 Agent 长时自主运行和多模态这两个"hard problems"上建立了不可替代性。两者不在同一赛道竞争。

## 参考资料

- [Tencent Hunyuan Hy3-preview GitHub](https://github.com/Tencent-Hunyuan/Hy3-preview)
- [Tencent 官方新闻稿](https://www.tencent.com/en-us/articles/2202320.html)
- [HuggingFace 社区分析](https://huggingface.co/blog/imnotkitty/hy3-preview)
- [OpenRouter 霸榜分析](https://www.openai-hub.com/news/398)
- [Qwen 官方](https://qwen.ai)
- [LLM Reference 对比](https://www.llmreference.com/compare/hy3-preview/o3-pro)
- [Qwen3.7-Max Benchmark 对比](https://apidog.com/blog/qwen-3-7-vs-gpt-5-5-vs-opus-4-7/)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-22 | 补充：概览对比表 Max 多模态列加脚注（qwen3.7-max-2026-06-08 快照支持视觉输入） |
| 2026-06-11 | 初始创建：Qwen3.7-Max/Plus vs Hy3-preview 选型对比。来源：inbox/ai-knowledge-by-qoder-ai-native-agent-20260611.md |
