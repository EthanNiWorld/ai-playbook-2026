# RL 算法选型：GRPO vs critic-based PPO

> 最后更新: 2026-07-30
> 领域: AI Engineering
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: RL 算法选择 = f(rollout 成本, 任务时程)——rollout 便宜 + 短时程用 GRPO，rollout 昂贵 + 长时程必须回归学习型价值函数（critic-based PPO）
**核心价值**: 以 GLM-5.2 长程 Agentic RL 从 GRPO 切换回 critic-based PPO 为开源可验证样本，给出后训练 RL 算法的任务相关选型框架
**相关产品**: [GLM 系列](../zhipu/glm-series.md), [DeepSeek](../deepseek/general_intro.md), [长程任务](long-horizon-task.md)
<!-- SUMMARY_END -->

## 是什么

GLM-5.2 技术报告披露的一个关键训练变化：**在长程 Agentic RL 阶段，从 GRPO 切换回 critic-based PPO**；而 Reasoning RL（短任务推理）阶段仍延续 GRPO + IcePop（缓解训推不匹配）路线。

表述纠偏：这不是"GLM-5.2 全面放弃 GRPO"，被否定的只是 GRPO 在长程智能体任务上的适用性。

**GRPO 的由来**（DeepSeek 2024 提出）：PPO 需要 critic（价值网络）估计每个状态的价值来算逐步 advantage，但对巨型 LLM 而言 critic 本身就是又一个巨型网络，训练贵、难收敛、易与 policy 互相拖垮。GRPO 的核心交易：**砍掉 critic，用"同 prompt 采样一组回答（GLM-5.1 为 32 条）、组内平均奖励作 baseline"替代价值估计**——本质是"用额外采样换掉一个网络"。短任务 rollout 秒级、成本低，这笔交易极划算，故两年间成为开源社区默认答案。

## 核心原理

长程任务上，GRPO 的三个设计前提全部失效：

### 1. "组内可比"不成立（技术报告点名的直接原因）

长程智能体轨迹要经过上下文压缩，压缩后的子轨迹长短不一、起点状态各异——"同一 prompt 下的 N 条平行样本"这个概念本身消失，组内比较无从谈起。

### 2. 采样成本结构反转

短任务 rollout 是秒级；长程 rollout 是数小时的完整工程轨迹（GLM-5.2 官方 demo 单任务消耗 88 万+ tokens）。为一个训练信号跑 32 条数小时轨迹不可接受——**critic 再贵，也比 32 倍超长 rollout 便宜**，"用采样换 critic"的算术彻底倒挂。

### 3. 信用分配粒度不够

GRPO 只有序列级相对 advantage，一个终局奖励均匀涂抹到几千步的每个 token；critic 能为每个中间状态给出不同的价值估计，把稀疏终局奖励**有区别地**分配到各步骤。附带问题：长程任务成败方差大，一组样本全成或全败时组内 advantage 归零，整组算力白烧。

### 更深一层：Bitter Lesson 的回归

行业讨论指出，前沿闭源实验室可能从未在 agentic RL 上全面采用 GRPO——可学习的价值函数随算力增长而变强，组采样 baseline 有手工设计的天花板。GRPO 的两年流行，某种程度是开源社区"短任务 benchmark 时代"的局部最优。

### 配套工程（GLM-5.2 案例）

- 自研 Slime 框架打通训练/推理，支撑大规模 Agentic RL 和 OPD（并行蒸馏专家模型约两天完成）
- 针对 coding 奖励作弊引入两阶段拦截机制

## 关键选型维度

| 维度 | GRPO 及变体 | critic-based PPO | 怎么选 |
|------|------------|------------------|--------|
| rollout 成本 | 低（秒级、几千 token） | 高也可承受 | rollout 变贵 → PPO |
| 任务时程 | 短（单轮数学/代码） | 长（小时级 agent 轨迹） | 时程变长 → PPO |
| 信用分配 | 序列级，粗粒度 | 逐状态，细粒度 | 需定位中间步骤好坏 → PPO |
| 工程复杂度 | 低（无 critic） | 高（需训练稳定的价值网络 + 配套框架） | 团队 infra 能力弱 → GRPO |
| 组内可比性 | 要求同 prompt 平行样本 | 无此要求 | 轨迹经压缩/异构 → PPO |

> GRPO 并未过时：DeepSeek 训练领域专家模型至今仍用 GRPO；学术界仍在持续产出 GRPO 变体。

## 常见误区

| 误区 | 事实 |
|------|------|
| GLM-5.2 全面放弃了 GRPO | 仅长程 Agentic RL 阶段切换，Reasoning RL 仍用 GRPO + IcePop |
| GRPO 过时了 | 短任务上仍是最优解之一，被暴露的只是长程任务上的适用边界 |
| PPO 的 critic 太贵不可行 | 长程场景下 critic 成本远低于 32 倍超长 rollout，成本算术已反转 |
| 算法选型有全局最优解 | RL 算法选择是任务相关的：f(rollout 成本, 任务时程) |

## 参考资料

- [官方文档] 智谱官方博客 - GLM-5.2 上线并开源（Slime 框架、Agentic RL、长程任务定位）- https://www.zhipuai.cn/zh/research/161
- [官方文档] GLM-5.2 官方技术博客 - https://z.ai/blog/glm-5.2
- [技术分析] 知乎 - GLM-5.2 为何在 Long-Horizon Agentic RL 上从 GRPO 回归 critic - https://zhuanlan.zhihu.com/p/2058332844288636661 [⚠️ 待验证]
- [技术分析] 知乎 - critic 逐步 advantage 分配机制 - https://zhuanlan.zhihu.com/p/2060119179777332073 [⚠️ 待验证]
- [媒体报道] CSDN - GLM-5.2 放弃 GRPO 引发强化学习算法选择新思考（组大小 32、子轨迹压缩、两阶段拦截）- https://blog.csdn.net/techforward/article/details/162174979 [⚠️ 待验证]

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-07-30 | 初始创建：从 inbox 概念洞察提炼，含 GRPO 三前提失效分析、选型维度表、GLM-5.2 开源可验证样本 |
