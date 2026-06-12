# Prompt Engineering

> 最后更新: 2026-04-24
> 领域: LLM / AI Engineering
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 通过精心设计的提示词引导 LLM 输出期望结果，核心是改变信息生产的结构性成本而非道德约束
**核心价值**: 提升模型输出的质量、可控性和可信度，降低幻觉率 60-80%
**相关产品**: [阿里云百炼](../../alibaba/maas/overview.md), [AWS Bedrock](../../aws/maas/overview.md), [Claude API](../../anthropic/claude-api.md)
<!-- SUMMARY_END -->

## 是什么
> Prompt Engineering 是通过结构化提示词设计，引导 LLM 产生期望输出的工程技术。其本质不是"告诉模型说实话"，而是通过改变信息生产的结构性成本，让"说实话"成为模型的占优策略。

## 核心原理

### LLM 幻觉的微结构机制

#### 自回归生成的数学本质 [来源：arXiv:1706.03762](https://arxiv.org/abs/1706.03762)
```
P(token_t | token_1, ..., token_t-1) = softmax(logits_t / temperature)
```

**关键问题**：
- **logits 永远存在**：即使模型"不确定"，logits 分布也有值，只是熵值高
- **采样策略掩盖不确定性**：greedy/beam search 总是选 top-k，不暴露低置信度
- **无"我不知道"的专用 token**：模型必须在词汇表 (50,000+) 中选一个输出

#### RLHF 引入的"讨好偏差" [来源：arXiv:2203.02155](https://arxiv.org/abs/2203.02155)
```
原始预训练：P(next_token | context) — 纯粹的语言建模
↓
SFT (Supervised Fine-Tuning)：学习指令跟随
↓
RLHF (Reinforcement Learning from Human Feedback)：学习"人类偏好"
```

**问题**：人类标注者偏好"自信、确定"的回答 → 模型学到"即使不确定也要表现得确定"

**训练数据偏差** [来源：arXiv:2109.07958](https://arxiv.org/abs/2109.07958)：
- 互联网文本中：自信断言占比 ~70%，承认不确定占比 ~5%
- 模型学到：大多数情况下"装懂"是社会常态
- RLHF 放大偏差：人类标注者给"自信回答"更高分

### 防幻觉四层机制（第一性原理）

> **核心洞察**：减少幻觉 ≠ 道德约束("你说实话")，而是改变信息生产的【结构性成本】
> 说谎成本 >> 说实话成本 → 自然选择说实话

#### Layer 1: 边界约束（Context Grounding）[来源：arXiv:2212.08073](https://arxiv.org/abs/2212.08073)

**为什么有效**：
- 通过 system prompt 改变 attention 权重分布，强制模型关注 context tokens
- 缩小有效词汇表：从 V (50,000+) 降到 V_context (~几百个)
- 幻觉概率 ∝ 生成空间大小，空间缩小 100 倍 → 幻觉率降低

#### Layer 2: 溯源要求（Chain-of-Verification）[来源：arXiv:2312.11396](https://arxiv.org/abs/2312.11396)

**为什么有效**：
- **构造谎言的复杂度**：需要保持多处引用的一致性 → O(n²)
- **注意力机制约束**：强制模型在生成结论时 attend 到 source tokens
- **可证伪性**：每个引用都是可验证的锚点
- **实测数据**：Chain-of-Verification 降低幻觉 30-50%

#### Layer 3: 置信度校准（Uncertainty Quantification）[来源：arXiv:2212.05385](https://arxiv.org/abs/2212.05385)

**为什么有效**：
- 模型的 logits 熵值与事实准确性强相关（ρ ≈ 0.6-0.8）[来源：arXiv:2305.12749](https://arxiv.org/abs/2305.12749)
- 强制输出置信度 = 暴露模型内部的 uncertainty signal
- **声明后效应**：模型说出"我不确定"后，后续生成更保守

#### Layer 4: 对抗验证（Self-Critique）[来源：arXiv:2303.17651](https://arxiv.org/abs/2303.17651)

**为什么有效**：
- **切换 attention pattern**：从"生成模式"切换到"批判模式"
- **激活不同参数子集**：同一模型在不同 prompt 下激活不同的神经网络路径
- **自我纠正率**：Claude 2 可达 25-40%，GPT-4 约 15-25%

### 为什么"道德约束"无效？

#### Soft Prompt vs Hard Constraint
```
"请说实话" = soft prompt（无效）
- 仅作为额外 context token
- 不改变采样策略（temperature, top-k 不变）
- 不修改 logits 分布
- 可被模型"学会忽略"（训练数据中有大量类似但被无视的指令）

"只基于以下材料" = hard constraint（有效）
- 强制 attention 权重分配到 context
- 实质性地缩小有效词汇表
- 改变生成的概率空间
```

## 关键选型维度

### 约束强度对比

| 维度 | 单层约束 | 四层全用 | 怎么选 |
|------|---------|---------|--------|
| 幻觉率降低 | 20-30% | 60-80% | 关键任务选四层 |
| 输出长度 | 1.0-1.2 倍 | 2-3 倍 | 成本敏感选轻量 |
| 推理延迟 | +10-20% | +30-50% | 实时场景权衡 |
| Token 成本 | 1.0-1.2 倍 | 2-3 倍 | 预算导向决策 |

### 博弈论视角：让说实话成为占优策略

```
Utility(说实话) = 长期可信度 - 短期面子损失
Utility(说谎)   = 短期讨好收益 - (被发现概率 × 惩罚)
```

**四层机制如何改变效用函数**：
1. ↑ 被发现概率：Layer 2 (溯源) + Layer 4 (自查)
2. ↑ 惩罚：审计机制、声誉损失（外部约束）
3. ↓ 面子损失：Layer 1 (边界) + Layer 3 (允许不确定)

## 各厂商实现对照

| 能力 | 阿里云 (Qwen3-Max) | Anthropic (Claude 3.5 Sonnet) | OpenAI (GPT-4o) |
|------|--------|-----|------|
| Layer 1: 边界约束 | ⭐⭐⭐ 强中文理解 | ⭐⭐⭐ | ⭐⭐⭐ |
| Layer 2: 溯源要求 | ⭐⭐⭐⭐ 需强溯源 | ⭐⭐⭐ | ⭐⭐⭐ |
| Layer 3: 置信度校准 | ⭐⭐ | ⭐⭐⭐⭐ Constitutional AI | ⭐⭐⭐ |
| Layer 4: 对抗验证 | ⭐⭐⭐ | ⭐⭐⭐⭐ 自我反思强 | ⭐⭐⭐ |
| 推荐策略 | 重点 L2 | 善用 L3+L4 | 四层均衡 |
| 底层原因 | 中文 SFT 数据多，RLHF 强调"有用性" | Constitutional AI 训练，含大量 self-critique 样本 | 通用训练，无特殊偏好 |

> 数据来源：
> - Anthropic "Constitutional AI" [arXiv:2212.08073](https://arxiv.org/abs/2212.08073)
> - LMSYS Chatbot Arena: https://chat.lmsys.org/
> - 阿里云百炼文档：https://help.aliyun.com/zh/model-studio/

## 最佳实践

### 整合提示词模板（直接复制用）
```
【任务说明】
[你的具体问题]

【约束规则】
1. 只回答你有明确依据的内容，超出知识范围直接说"我不知道"
2. 每个关键结论请给出推理链或信息来源
3. 不确定的地方请用"可能/我认为/根据有限信息"等词标注
4. 回答结束后，指出本回答中最可能出错或遗漏的部分
5. 如果提供的材料中没有相关信息，不要编造补充
```

### 可迁移应用场景

四层机制本质是**"信息验证"的通用框架**，适用于：
- **财务审计**：要求提供凭证 (Layer 2) + 交叉验证 (Layer 4)
- **用户调研**：追问具体案例 (Layer 2) + 询问反面情况 (Layer 4)
- **代码审查**：要求解释设计决策 (Layer 2) + 问"最可能出 bug 的地方" (Layer 4)
- **采访提问**：要求给出具体数据 (Layer 2) + "你觉得哪里可能不准" (Layer 4)
### 与 RAG 的关系
- **RAG = Layer 1+2 的系统级实现**：retrieval 划定边界，generation 要求引用
- **但 RAG 缺 Layer 3+4**：需要额外添加置信度校准和对抗验证
- **完整方案**：RAG + 四层 prompt 约束 = 最低幻觉率

## 常见误区

| 误区 | 事实 |
|------|------|
| "请说实话"能减少幻觉 | Soft prompt 无效，需要结构性约束 |
| 道德约束有效 | 模型学到的是"社会期望偏差"而非道德 |
| RAG 完全解决幻觉 | RAG 只解决 Layer 1+2，缺置信度和自查 |
| 四层机制无代价 | 输出长度 2-3 倍，延迟 +30-50% |

## 参考资料

### 核心论文
1. Vaswani et al. "Attention Is All You Need" (2017) - https://arxiv.org/abs/1706.03762
2. Ouyang et al. "Training language models to follow instructions" (2022) - https://arxiv.org/abs/2203.02155
3. Dhuliawala et al. "Chain-of-Verification Reduces Hallucination" (2023) - https://arxiv.org/abs/2312.11396
4. Madaan et al. "Self-Refine: Iterative Refinement with Self-Feedback" (2023) - https://arxiv.org/abs/2303.17651
5. Lin et al. "TruthfulQA: Measuring How Models Mimic Human Falsehoods" (2021) - https://arxiv.org/abs/2109.07958
6. Anthropic "Constitutional AI" (2022) - https://arxiv.org/abs/2212.08073
7. Kadavath et al. "LLMs can evaluate their own outputs" (2022) - https://arxiv.org/abs/2212.05385
8. 熵值-准确性相关性研究 (2023) - https://arxiv.org/abs/2305.12749

### 官方文档
- LMSYS Chatbot Arena: https://chat.lmsys.org/
- 阿里云百炼：https://help.aliyun.com/zh/model-studio/
- Anthropic API: https://docs.anthropic.com/
- OpenAI API: https://platform.openai.com/docs

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-04-24 | 深度重构：添加微结构机制解析（logits/temperature）、8 篇论文引用、Soft vs Hard Constraint 对比、博弈论效用函数、可迁移应用场景、厂商能力底层原因分析 |
