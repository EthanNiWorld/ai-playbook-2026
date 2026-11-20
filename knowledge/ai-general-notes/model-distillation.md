# 模型蒸馏：把大模型的"智商"装进小模型

> 最后更新: 2026-11-20
> 领域: AI Engineering / LLM
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 蒸馏 = teacher 产出信号、student 学习——按"信号载体"（文本样本 vs logit 分布）与"生成方向"（teacher 生成 vs student 生成 teacher 纠正）区分三条路线，LLM 时代主流是 CoT 数据蒸馏
**核心价值**: 给出三条路线（SFT 数据蒸馏 / logit KD / on-policy 蒸馏）选型框架，附 DeepSeek-R1 800k 样本工程案例、数据配比实践、以及一个真实蒸馏 API 请求样本的解读标尺
**相关产品**: [DeepSeek R 系列](../deepseek/deepseek-r-series.md), [Kimi K 系列](../moonshot/kimi-k-series.md), [RL 算法选型](rl-algorithm-selection-grpo-vs-ppo.md), [推理力度](reasoning-effort.md), [推测解码](speculative-decoding.md), [视频模型数据策略](video-model-data-strategy.md)
<!-- SUMMARY_END -->

## 是什么

用一个强模型（teacher）把能力迁移给小模型（student）。与参数压缩三兄弟的边界：

- **蒸馏**：迁移的是能力/行为，teacher 可与 student 完全不同架构、不同参数量
- **量化**：同一模型权重低精度化（`fp16`→`int8`），不换模型
- **剪枝**：同一模型删结构，不换模型

与推测解码的区别：推测解码是**运行时借用**（小模型当 draft、大模型验证，各权重原封不动）；蒸馏是**训练时迁移**（能力真正长进 student 权重里，训练完成后 teacher 可以离场）。

注意领域反例：视频生成赛道存在"[不蒸馏原则](video-model-data-strategy.md)"（Seedance 2.0 案例）——当领域内不存在可蒸馏的强 teacher 时，自建高质量数据管线是唯一路径。蒸馏的前提是**存在明确更强的 teacher**。

## 核心原理：三条路线

### 路线 1：数据蒸馏（SFT on teacher outputs）——当前主流

teacher 生成高质量样本（重点：带完整推理链 CoT 的样本），拿去 SFT 微调 student。student 学的是"怎么想"，不仅是"答案"。

关键环节：

- **拒绝采样**：同一 prompt 多次采样（`temperature` `0.7`–`1.0`），只保留答案正确、格式合规的样本
- **格式化输出**：强制 `\boxed{}` 等可机读格式，便于自动抽取答案 + 验证 + 过滤
- **数据配比**：见下文专节

### 路线 2：Logit 蒸馏（经典 KD）——理论正统，工程少用于 LLM

student 直接拟合 teacher 的输出概率分布，软标签损失 + 硬标签 CE 加权：

\[\mathcal{L} = \alpha \cdot T^2 \cdot \mathrm{KL}(p^{T}_{teacher} \,\|\, p^{T}_{student}) + (1-\alpha) \cdot \mathrm{CE}(y)\]

软标签携带"类间相似度"信息（teacher 认为错误选项也有概率质量），信号密度高于 one-hot。但要求 teacher 与 student **同词表、同步前向**——跨架构（不同 tokenizer）几乎不可用，且大规模 KD 的算力开销往往不如直接造数据，故被路线 1 取代。小模型/同源模型场景仍有用武之地。

### 路线 3：On-policy 蒸馏——反转生成方向（新路线）

离线 SFT 蒸馏的两个经典失效模式：

- **知识截断**：student 没学到的知识，teacher 数据补不上（学了也答不对）
- **分布偏移**：student 生成偏离 teacher 数据分布时，离线数据帮不上忙

On-policy 蒸馏的反转：**student 自己生成，teacher 打分**——student 输出的每个 token 位置上，用 teacher 的 logit 对 student 的梯度做 KL 加权，teacher 当"实时教练"边生成边纠正。GKD（Tulu 3 采用）是同思路的学术版本。

### 三路线对比

| 维度 | 数据蒸馏（SFT） | Logit KD | On-policy 蒸馏 |
|------|----------------|-----------|----------------|
| 信号载体 | 文本样本 | logit 概率分布 | student 生成 + teacher 逐 token 评分 |
| 生成方向 | teacher 生成 | 双方前向 | student 生成 |
| 跨词表/架构 | 可行 | 基本不可行 | 可行 |
| 工程成本 | 低（API 调用即可造数） | 高（同步前向、同词表） | 高（teacher 高频前向介入训练） |
| LLM 时代地位 | 主流 | 经典遗留、小模型场景 | 兴起（2025 起） |

## R1 蒸馏案例（工程化标杆）

DeepSeek-R1（`arXiv:2501.12948`，2025-01）的 CoT 数据蒸馏是路线 1 的大规模落地样本：

- **teacher**：DeepSeek-R1（经完整 RL 训练后的推理模型）
- **数据规模**：约 `800k` 样本 = ~`600k` 推理数据 + ~`200k` 非推理通用数据（约 75/25 配比）
- **student**：Qwen `1.5B`/`7B`/`14B`/`32B` 与 Llama `8B`/`70B`
- **训练方式**：直接 SFT 单阶段，蒸馏后的 student 不再跑 RL

论文关键实验结论：

1. **蒸馏 > 小模型直接 RL**：把 R1 的推理模式蒸馏进强 student 的收益，超过在 student 上直接跑大规模 RL——小模型自身 rollout 出高质量长推理的成本太高
2. **蒸馏可再叠 RL 抬上限**：蒸馏是起点不是终点，后续再跑 RL 还能继续涨（R1 自身的训练顺序即此设计）
3. **teacher 上限 = 蒸馏天花板**：先有 R1（RL 后的 teacher），才有值得蒸馏的信号源

## 数据配比实践

- **配比经验**：推理数据 60%–70% + 通用指令/代码/多轮对话 30%–40%，防止能力窄化与幻觉放大——纯推理数据会把小模型练成"做题机器"
- **student 容量门槛**：长 CoT 蒸馏建议模型 ≥ `7B`；`1.5B` 级别易被超长思维链撑爆有效容量
- **评测防偏科**：不能只测被蒸馏的 benchmark（AIME/GPQA），要同时测通用能力保持度（MMLU、IFEval 等），防止"只会做题"
- **teacher 质量前置**：蒸馏的上限是 teacher 的生成质量，teacher 本身要先 RL/对齐到位

## 真实请求样本：蒸馏管线的 API 长什么样

以下为用户提供的真实 API 请求（`2026-11-20`，teacher 为 Kimi K3.1 Pro）：

```json
{
  "model": "kimi-k3.1-pro",
  "messages": [
    {
      "role": "user",
      "content": "You are given a difficult question. Your task is to solve the problem.\nThe question is written in such a way that it solely requires you to find the final answer. Make sure to follow the additional formatting instructions if they are provided in the question.\nPut the final answer you find within \\boxed{}.\n\nFor integers $k\\ge 3$ and real $\\theta$, define $v(k,\\theta)$ to be the maximum possible number of vertices of a connected $k$-regular graph whose second largest eigenvalue (of its adjacency matrix) is at most $\\theta$. Compute the ordered triple $(v(4,\\sqrt2),\\,v(5,\\sqrt2),\\,v(5,\\sqrt5-1))$ and return it as a comma-separated list in \\boxed{}, e.g., \\boxed{(1,1,1)}."
    }
  ],
  "temperature": 1,
  "reasoning_effort": "max"
}
```

**识别标尺**——五个特征同时出现，即高度疑似"造训练/评测数据"的模板化 prompt 而非自然提问：

1. **模板化措辞**："You are given a difficult question..." 批量生成管线的固定模板句式
2. **强制机读格式**：`\boxed{}` 便于自动抽取答案、比对标准答案、过滤错误样本（拒绝采样的前置设计）
3. **`temperature: 1`**：采样多样化，服务拒绝采样所需的多样本
4. **`reasoning_effort: max`**：产出长 CoT，蒸馏的信号载体（详见[推理力度](reasoning-effort.md)）
5. **题目本身是高难度数学题**（谱图理论，`k`-正则图第二大特征值上界，属 Alon–Boppana 界 / Ramanujan 图领域）：构造高难度推理数据的典型题源

**无法仅凭请求区分的两种用途**：造 SFT 训练数据（蒸馏/合成数据管线）与跑 benchmark 评测（统模板 + 统温度统计准确率）在请求形态上同构，须看请求归属的管线。判别要点：训练管线会对同一题多采样（不同 seed）+ 有答案过滤/去重/清洗环节；评测管线对每题恰好一轮（或固定 k 轮）。

## 关键认知框架

### 核心洞察 1：蒸馏迁移的是"推理模式"，不是知识
- student 从 teacher 长思维链里学的是解题的思考方式；teacher 没展现出来的知识，student 无论如何都拿不到（知识截断的根源）
- 为什么重要：解释了为什么蒸馏后仍需通用数据配比与后续 RL——蒸馏不是能力注入的黑魔法
- 可迁移场景：任何"专家示范 + 学徒模仿"场景（领域小模型、分类器蒸馏、师带徒 SOP 沉淀）都遵循同一约束：**示范里没有的能力，学徒学不会**

### 核心洞察 2：蒸馏是"训练时的推测解码经济学"
- 推测解码：推理时用小模型换大模型的计算；蒸馏：训练时用一次性 teacher 开销换永久的小模型部署成本
- 两者共同点：**用强模型的可验证输出换算力**；区别是一个不改变权重、一个改变
- 可迁移场景：判断"要不要常驻大模型"的架构决策——低频高价值场景用运行时借用（推测解码/API），高频规模化场景用训练时迁移（蒸馏/自训小模型）

## 最佳实践

### 可迁移场景（推荐）

- **领域小模型定制**：用旗舰模型批量生成本领域 QA/CoT 数据 + 拒绝采样过滤 + SFT 到 `7B` 级开源底座，成本远低于自训大模型
- **非 ML 场景**：组织知识沉淀同构——专家产出结构化范例（带"为什么这么做"的推理链），新人学习的是决策模式而非结论

## 常见误区

| 误区 | 事实 |
|------|------|
| 蒸馏 = 压缩参数量 | 蒸馏迁移能力/行为，参数压缩是量化与剪枝的职责 |
| Logit KD 是当前主流 | LLM 时代受同词表约束，主流是文本数据蒸馏（路线 1） |
| 蒸馏完就不用 RL 了 | R1 验证蒸馏后可再叠 RL 继续抬上限；蒸馏是起点 |
| 小模型蒸什么都能学会 | 存在容量天花板：长 CoT 蒸馏建议 ≥ `7B`，且上限锁死在 teacher 生成质量 |
| 模板化 boxed prompt 一定是造训练数据 | 与评测请求同构，须看管线归属（多采样+过滤 → 训练；每题一轮 → 评测） |

## 论文溯源与工程实现对照

| 来源 | 性质 | 贡献 |
|------|------|------|
| Hinton et al.《Distilling the Knowledge in a Neural Networks》（`arXiv:1503.02531`，2015） | 原创研究 | logit KD 开山，软标签 + 温度缩放 |
| DeepSeek-R1（`arXiv:2501.12948`，2025-01） | 工程化 | CoT 数据蒸馏大规模落地标杆，`800k` 样本 |
| Tulu 3 / GKD（AI2，`arXiv:2411.15124`，2024-11） | 学术 | on-policy 方向（GKD）用于 `8B` 模型的系统验证 |
| Thinking Machines《On-Policy Distillation》（2025-10） | 原创研究 + 工程 | 反转生成方向，命名"on-policy distillation"，给出两大失效模式 |

> 工程化吸收状态：路线 1 已被全行业吸收；路线 3 处于头部实验室实践、开源框架尚未标准化（关注点）。

## 参考资料

- [学术论文] Hinton, Vinyals, Dean - Distilling the Knowledge in a Neural Network - https://arxiv.org/abs/1503.02531
- [学术论文] DeepSeek-AI - DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning - https://arxiv.org/abs/2501.12948
- [学术论文] AI2 - Tulu 3: Pushing Frontiers in Open Language Model Post-Training（GKD） - https://arxiv.org/abs/2411.15124
- [官方文档] Thinking Machines - On-Policy Distillation - https://thinkingmachines.ai/blog/on-policy-distillation/
- [用户样本] 2026-11-20 用户提供 kimi-k3.1-pro 数学蒸馏请求原文（本页"真实请求样本"节全量收录）

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-11-20 | 初始创建：三条蒸馏路线对比、R1 案例与数据配比实践、论文溯源对照；收录用户提供的 kimi-k3.1-pro 蒸馏请求真实样本及训练/评测同构判别要点 |
