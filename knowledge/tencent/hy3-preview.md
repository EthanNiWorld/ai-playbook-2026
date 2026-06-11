# Hy3-preview（腾讯混元）

> 最后更新: 2026-06-11
> 所属厂商: 腾讯（Tencent Hunyuan）
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 腾讯混元系列旗舰推理模型，高性价比通用推理 + Agent 底座，295B MoE 仅 21B 激活，开源可自部署
**当前主推**: Hy3-preview
**适用**: 个人/小团队 Agent 开发、预算敏感场景、私有化部署/二次开发
**不适用**: 多模态 Agent（纯文本模型）、超长上下文场景（256K vs 竞品 1M）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Hy3-preview** | 🚩 高性价比通用推理+Agent底座 | 256K tokens | 异构专家设计 + P-Penalty Loss + 开源 | 2026-04-22 |

### Hy3-preview

- **模型**：Hy3-preview
- **公司**：腾讯混元（Tencent Hunyuan）
- **时间**：2026 年 4 月 22 日
- **尺寸**：295B（MoE），激活参数 21B
- **上下文**：256K tokens
- **开源**：是（Tencent Hunyuan Community License）
- **多模态**：纯文本
- **场景**：Agent 开发、编码辅助、工具调用、私有化部署
- **特点**：
  1. **异构专家尺寸设计 + P-Penalty Loss 路由优化**：推理效率提升 40%
  2. **OpenRouter 工具调用 #1、Coding #2**
  3. **性价比碾压**：输入 ~$0.07/1M tokens（≈¥0.5/M），输出 ~$0.26/1M tokens（≈¥1.9/M）
  4. **开源可自部署**：295B MoE 仅 21B 激活，消费级硬件可跑（量化后）
  5. **长时 Agent**：495 步工作流

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **Agent/工具调用** | OpenRouter 工具调用排名 #1 |
| **编码能力** | SWE-bench Verified 74.4%，OpenRouter Coding #2 |
| **数学推理** | AIME 2026 89.2%，GPQA Diamond 87.2% |
| **浏览/信息检索** | BrowseComp 67.1% |
| **性价比** | 输出价格约 Qwen3.7-Max 的 1/19，约 Qwen3.7-Plus 的 1/4 |
| **开源部署** | 21B 激活参数，量化后消费级硬件可运行 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 上下文 | 256K tokens | 竞品普遍 1M（如 Qwen3.7-Max/Plus） |
| 多模态 | 纯文本 | 无图/视频/屏幕输入能力 |
| 长时 Agent | 495 步工作流 | 无超长时自主运行验证（竞品如 Qwen3.7-Max 支持 35h） |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 个人/小团队 Agent 开发 | Hy3-preview | 性价比碾压，Agent 能力够用 |
| 私有化部署/二次开发 | Hy3-preview | 开源 + 21B 激活，部署成本低 |
| 预算敏感的编码辅助 | Hy3-preview | SWE-bench 74.4%，足够大多数编码场景 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 多模态 Agent（GUI/视觉/屏幕） | 纯文本模型，无多模态能力 |
| 大型代码仓库/超长文档 | 256K 上下文，竞品 1M |

## 市场表现

- 连续三周登顶 OpenRouter 周榜（2026.04.27-05.11）
- Token 调用量达上一代 Hy2 的 10 倍
- 代码与智能体场景增幅超 16.5 倍
- 结束限免后仍保持榜首 → 开发者愿意付费
- 2026-06-11 OpenRouter 周 Token 量 3.3T，排名 #2（仅次于 DeepSeek V4 Flash）

### 为什么在 OpenRouter 调用量高

1. **价格碾压**：输出价格约 Qwen3.7-Max 的 1/19，约 Qwen3.7-Plus 的 1/4。OpenRouter 用户以个人开发者和小团队为主，价格极度敏感
2. **能力"够用"**：SWE-bench 74.4% 超过大量竞品，工具调用 #1，证明 Agent 实战可用
3. **开源可自部署**：295B MoE 仅 21B 激活，消费级硬件可跑（量化后）
4. **限免策略正确**：两周限免建立使用惯性，结束后留存率高

## 关键技术论文

[⚠️ 待补充]

## 参考资料

- [Tencent Hunyuan Hy3-preview GitHub](https://github.com/Tencent-Hunyuan/Hy3-preview)（官方 GitHub）
- [Tencent 官方新闻稿](https://www.tencent.com/en-us/articles/2202320.html)
- [HuggingFace 社区分析](https://huggingface.co/blog/imnotkitty/hy3-preview)
- [OpenRouter 霸榜分析](https://www.openai-hub.com/news/398)
- [LLM Reference - 定价与 Benchmark 对比](https://www.llmreference.com/compare/hy3-preview/o3-pro)
- [SWE-bench 74.4% 分析](https://businessanalytics.substack.com/p/tencent-open-sources-hy3-at-744)
- [API 定价与 Specs](https://developer.puter.com/ai/tencent/hy3-preview/)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-11 | 初始创建：Hy3-preview 产品知识提炼。来源：inbox/ai-knowledge-by-qoder-ai-native-agent-20260611.md |
