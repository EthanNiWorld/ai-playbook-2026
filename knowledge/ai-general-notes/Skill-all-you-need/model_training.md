> 最后更新: 2026-06-23
> 领域: AI Engineering
> 状态: Published

## 一、MoE 模型端到端流程全景图

```
═══════════════════════════════════════════════════════════════════════════
                              预训练阶段
═══════════════════════════════════════════════════════════════════════════

  [1] 数据收集 ──► [2] 数据清洗 ──► [3] 数据配比 ──► [4] 分词器训练
       │               │               │               │
  多源并行抓取    分shard并行去重   代码/网页/数学    BPE/SentencePiece
                               配比决定能力分布

  [5] 架构设计 ──► [6] 小规模验证 ──► [7] 大规模预训练
       │               │               │
  Dense vs MoE      多组超参并行       DP × TP × PP × EP
  专家数/top-k/     网格搜索最优       all-to-all通信
  路由策略/辅助loss                  负载均衡

═══════════════════════════════════════════════════════════════════════════
                              后训练阶段
═══════════════════════════════════════════════════════════════════════════

  [8] SFT ──► [9] RM训练 ──► [10] RL对齐 ──► [11] 能力专项
    │            │             │               │
  高质量示例    可跳过        PPO/GRPO/DPO    代码RL/数学RL/
  指令微调                    +Anti-Hack      Agent RL

  [12] 基准评估 ──► [13] 安全测试 ──► [14] 推理优化 ──► [15] 部署
       │               │               │               │
  全benchmark    红队攻击测试    量化/投机解码    vLLM/SGLang/
  并行测试       越狱/偏见       KV-cache压缩    K8s/灰度发布
```

---

## 二、DeepSeek 招聘需求关键词提取

从 47 个职位中提炼出高频技术关键词：

| 类别 | 高频关键词 | 出现职位数 |
|------|-----------|-----------|
| **RL/对齐** | PPO、DPO、GRPO、Actor-Critic、RLHF、RLAIF、过程奖励、偏好学习 | 4+ |
| **Agent** | Agent Loop、Tool Use、MCP、Function Calling、Planning、Reasoning、Memory、Subagent、Multi-Agent | 5+ |
| **分布式训练** | DP、TP、PP、EP、all-to-all、NCCL、RDMA、RoCEv2、IB、NVLink | 4+ |
| **推理优化** | KV Cache、投机解码、量化、Flash Attention、Continuous Batching | 3+ |
| **数据工程** | 数据清洗、去重、质量评估、标注方案、数据Pipeline | 3+ |
| **系统工程** | K8s、Docker、GPU集群、异构计算、算子编译器、Profiling | 5+ |
| **模型架构** | MoE、Dense、GQA、MLA、稀疏注意力、长上下文 | 3+ |
| **Agent 产品** | Claude Code、Cursor、Vibe Coding、Prompt Engineering、Context Engineering | 4+ |

---

## 三、GLM-5.2 技术栈关键词

| 技术点 | 细节 |
|--------|------|
| **长上下文** | 1M 实测可用上下文，项目级工程接管 |
| **输出能力** | 128K max tokens |
| **Agent 协议** | MCP 原生支持 |
| **架构创新** | IndexShare（稀疏注意力共享索引器）、MTP+KVShare |
| **训练创新** | slime框架、Critic-Based PPO、Anti-Hack模块、OPD |
| **推理优化** | LayerSplit、KV-cache 三级管理 |
| **推荐场景** | 移动端真机调试、微信小程序、小游戏、长程重构 |

---

## 四、PPO vs GRPO vs DPO — 为什么 GLM-5.2 选择 PPO？

### 核心差异：轨迹压缩导致 GRPO 失效

长程编程任务（如"花 10 小时优化 CUDA kernel"）的轨迹太长，必须压缩（compaction）。一条超长轨迹变成 N 条子轨迹，不同 rollout 的 N 不同。GRPO 的组内标准化假设"每个 rollout 产生 1 个 reward"彻底崩塌。

**PPO 的优势**：单 rollout 学习，不需要等同一 prompt 的 G 个 rollout 跑完；每个子轨迹独立用 Critic 估计 token 级 advantage，长度无关；压缩友好，子轨迹就是训练单元。

**PPO 的代价**：需要额外训练 Critic 网络（≈Actor 大小），但远小于 GRPO 在长程场景下根本不可用的问题。

| 维度 | PPO | GRPO | DPO |
|------|-----|------|-----|
| **本质** | 强化学习（Actor-Critic） | 强化学习（无 Critic） | 非 RL（直接偏好优化） |
| **Advantage 来源** | Critic 网络学习 V(s) | 同一 prompt 的 G 个 rollout 组内标准化 | 不需要（直接优化偏好） |
| **额外模型** | 需要 Critic | 不需要 | 不需要 |
| **在线采样** | ✅ | ✅ | ❌ |
| **适用场景** | 长程复杂探索（编程 Agent） | 有明确 reward（数学推理） | 偏好对齐（安全/有用） |
| **代表模型** | GLM-5.2 | DeepSeek-R1 | Llama 3 |

---

## 五、SA 学习重点矩阵（按优先级排序）

### ⭐⭐⭐ 第一梯队：必须精通（占 60% 精力）

**1. 强化学习与对齐（RL & Alignment）**
```
这是 DeepSeek 招聘中最高频、最核心的要求。

核心知识点：
├─ PPO：Actor-Critic 架构，clip 机制，GAE 优势估计
├─ GRPO：组内相对优势，无 Critic 设计
├─ DPO：直接偏好优化，Bradley-Terry 模型
├─ RLHF/RLAIF：Reward Model 训练，偏好数据标注
├─ 过程奖励 vs 结果奖励
└─ GLM 的 Critic-Based PPO 选择原因（长程任务 → 压缩 → 子轨迹长度不一）
```

**2. MoE 架构与分布式训练**
```
DeepSeek 和 GLM 都是 MoE 模型，这是核心竞争力。

核心知识点：
├─ MoE 原理：专家路由、top-k 选择、辅助负载均衡 loss
├─ 4D 并行：DP × TP × PP × EP（EP 是 MoE 独有）
├─ all-to-all 通信 vs all-reduce 通信
├─ 负载不均衡问题：auxiliary loss、动态 capacity
├─ DeepSeek MoE 设计：细粒度专家、共享专家
└─ GLM IndexShare：稀疏注意力索引器共享，FLOPs 降低 2.9×
```

**3. 后训练全流程**
```
SA 需要能讲清楚从基座模型到可用模型的完整路径。

核心知识点：
├─ SFT 原理与局限：只能学示范，不能学探索
├─ RL 对齐三条路线选择（PPO/GRPO/DPO）的适用场景
├─ 编程 Agent RL：slime 框架、rollout 采样、reward 设计
├─ Anti-Hack：规则过滤 + LLM 裁判两级检测
└─ 能力专项：代码 RL / 数学 RL / 搜索 RL 的并行训练
```

---

### ⭐⭐ 第二梯队：深入理解（占 30% 精力）

**4. Agent 系统架构**
```
DeepSeek "Agent Harness 研发工程师" 职位专门讲这个。

核心知识点：
├─ Agent Loop：感知→规划→执行→观察→迭代
├─ Tool Use / Function Calling：模型如何调用外部工具
├─ MCP（Model Context Protocol）：GLM-5.2 原生支持
├─ Planning & Reasoning：COT、TOT、ReAct 等范式
├─ Memory：短期（上下文窗口）/ 长期（向量数据库）
├─ Subagent / Multi-Agent：任务分解与协作
└─ Context Engineering：Prompt 设计、上下文压缩（compaction）
```

**5. 推理优化**
```
所有模型部署都绕不开。

核心知识点：
├─ KV Cache 原理与瓶颈：显存占用 = 2 × layers × hidden_dim × seq_len
├─ GLM LayerSplit：三层 KV-cache 管理（GPU/CPU/磁盘）
├─ MLA（DeepSeek）：低秩 KV 压缩
├─ IndexShare（GLM）：稀疏注意力降低 FLOPs
├─ 投机解码：MTP、draft model 方案
├─ 量化：INT8/INT4/FP8，AWQ/GPTQ
├─ Continuous Batching：vLLM 核心机制
└─ Prefill-Decode 分离架构
```

**6. 数据工程**
```
DeepSeek 专门有"Agent 数据策略工程师"。

核心知识点：
├─ 数据清洗管线：去重（MinHash/SimHash）、质量过滤、语言检测
├─ 数据配比策略：代码/网页/数学/多语言的比例
├─ Agent 训练数据构造：规划、工具调用、多轮交互
├─ 评测数据集设计：SWE-bench、Terminal-Bench、FrontierSWE
└─ 数据与 RL 闭环：数据分析 → 数据补齐 → 训练 → 评测 → 迭代
```

---

### ⭐ 第三梯队：了解原理（占 10% 精力）

**7. 高性能网络与集群**
```
DeepSeek "超算网络研发工程师" 的核心。SA 了解原理即可。

核心知识点：
├─ RDMA / RoCEv2 / InfiniBand：GPU 间通信协议
├─ all-to-all（MoE 关键）vs all-reduce（Dense 关键）
├─ NVLink / NVSwitch：GPU 内互联
├─ 集合通信库：NCCL 的基本原理
└─ 万卡集群故障诊断与容错
```

**8. 模型架构基础**
```
核心知识点：
├─ Transformer 架构：Self-Attention、FFN、LayerNorm
├─ 注意力变体：MHA → MQA → GQA → MLA
├─ RoPE 位置编码与长上下文扩展（YaRN、NTK-aware）
├─ MoE vs Dense 的 FLOPs/参数 权衡
└─ GLM IndexShare 论文（arXiv:2603.12201）
```

---

## 六、一张图：SA 学习路线图

```
                               ┌─────────────────┐
                               │   SA 学习路线图   │
                               └────────┬────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
   ┌────▼────┐                    ┌────▼────┐                    ┌────▼────┐
   │ 第一梯队 │                    │ 第二梯队 │                    │ 第三梯队 │
   │  ⭐⭐⭐  │                    │   ⭐⭐   │                    │    ⭐    │
   │ 60%精力 │                    │ 30%精力  │                    │ 10%精力  │
   └────┬────┘                    └────┬────┘                    └────┬────┘
        │                               │                               │
   ┌────▼──────────┐          ┌────────▼──────────┐          ┌────────▼──────────┐
   │ 1. RL与对齐    │          │ 4. Agent系统架构   │          │ 7. 高性能网络      │
   │ PPO/GRPO/DPO  │          │ Agent Loop/Tool   │          │ RDMA/RoCEv2/NCCL  │
   │ RLHF/RLAIF    │          │ MCP/Planning/     │          │ all-to-all通信    │
   │ Critic/Advantage│        │ Memory/Subagent   │          │                   │
   ├────────────────┤          ├───────────────────┤          ├───────────────────┤
   │ 2. MoE架构     │          │ 5. 推理优化        │          │ 8. 模型架构基础    │
   │ EP/DP×TP×PP   │          │ KV Cache/量化     │          │ Transformer/注意力 │
   │ all-to-all     │          │ 投机解码/MLA/     │          │ RoPE/长上下文     │
   │ 负载均衡       │          │ IndexShare       │          │ IndexShare论文    │
   ├────────────────┤          ├───────────────────┤          └───────────────────┘
   │ 3. 后训练全流程 │          │ 6. 数据工程        │
   │ SFT→RM→RL     │          │ 清洗/配比/标注    │
   │ Agentic RL      │          │ 评测/闭环迭代     │
   │ Anti-Hack      │          │                   │
   └────────────────┘          └───────────────────┘
```

---

## 七、为什么是这个优先级？（招聘需求交叉验证）

| 知识点 | DeepSeek 要求 | GLM-5.2 体现 | 权重 |
|--------|:---:|:---:|:---:|
| RL/对齐（PPO/DPO/GRPO） | ✅ 核心要求 | ✅ Critic-Based PPO | ⭐⭐⭐ |
| MoE 分布式训练 | ✅ 超算/核心系统 | ✅ IndexShare/EP | ⭐⭐⭐ |
| 后训练流程 | ✅ 数据+RL闭环 | ✅ slime+OPD | ⭐⭐⭐ |
| Agent 架构 | ✅ Harness 团队 | ✅ 1M上下文+MCP | ⭐⭐ |
| 推理优化 | ✅ 深度学习研发 | ✅ LayerSplit/MTP | ⭐⭐ |
| 数据工程 | ✅ 数据策略工程师 | ✅ 编码Agent训练数据 | ⭐⭐ |
| 高性能网络 | ✅ 超算网络 | ✅ all-to-all优化 | ⭐ |
| 模型架构 | ✅ 核心系统 | ✅ IndexShare论文 | ⭐ |

---

**一句话总结**：作为 SA，**RL 对齐 + MoE 训练 + 后训练流程** 是必须能讲透的硬核知识，这是 DeepSeek 和 GLM-5.2 的共性核心；**Agent 架构 + 推理优化 + 数据工程** 是决定你能否和客户做深度技术交流的差异点；**网络/集群/底层架构** 了解原理即可，不需要深入。






Source :
Prompt with qwenpaw on 20260623
"
The user wants me to:

1. Look at the MoE model end-to-end training flow (which we've already discussed)
2. As a Solution Architect (SA), identify which knowledge points are most important to learn
3. Cross-reference with:
   - High-Flyer (幻方/DeepSeek) job postings at https://app.mokahr.com/social-recruitment/high-flyer/140576#/jobs
   - GLM-5.2 documentation at https://docs.bigmodel.cn/cn/guide/models/text/glm-5.2

Let me first open both URLs to get the job requirements and GLM-5.2 details.

好的，我同时打开两个来源，把 DeepSeek 的招聘需求、GLM-5.2 的技术文档和前面讨论的训练流程三者交叉对照，帮你梳理 SA 的学习重点。



Let me snapshot this page to see the job listings.

I've got a lot of job listings from DeepSeek. Let me now also check the GLM-5.2 documentation page. But first let me also scroll down to see more job listings from the DeepSeek page.

Let me also open the GLM-5.2 docs page.

Let me snapshot both pages. Let me also scroll the DeepSeek page to see more job listings.

Now let me also scroll down the DeepSeek job page to see more listings. I only got one job so far (Agent深度学习算法研究员). Let me scroll to see more.

Let me take a snapshot to see more job listings.

The GLM-5.2 page didn't give me much technical detail - it's more of a product page. The deepseek page also didn't give me the full job listings. Let me now scroll further down the DeepSeek job page to see more job categories. Also, let me browse the different job listings by clicking on them.

Actually, let me try a different approach. Let me click on some of the job listings to see the actual job descriptions. But first, let me scroll more to see all the available jobs.

Actually, wait - the previous snapshot of the DeepSeek page showed the page switched to the GLM page. Let me switch back to the DeepSeek page.

OK, I got the GLM-5.2 docs. Now let me switch back to the DeepSeek jobs page and get the job listings. The current page_id "default" is showing the GLM page, not the DeepSeek jobs page. Let me navigate to the DeepSeek page properly.

Let me wait a moment and then take a snapshot.

I now have a comprehensive view of the DeepSeek (High-Flyer) job listings. Let me also scroll the GLM-5.2 page to get the full technical details. Let me also get the full DeepSeek job listing. Let me now scroll the GLM page for more details.

From the DeepSeek job listings, I can see these key roles:
1. Agent深度学习算法研究员 - RL, PPO, DPO, Actor-Critic, RLHF/RLAIF
2. Agent 数据策略工程师 - Agent training data, evaluation, RL
3. Agent 全栈开发工程师 - Agent infrastructure, MCP, Tool Use, Function Calling
4. Agent Harness 研发工程师 - Model + Harness = Agent, KV Cache, Agent Loop, Tool Use, Reasoning, Planning, Skills, MCP, Memory, Subagent, Multi-Agent
5. 超算网络研发工程师 - RDMA, RoCEv2, IB, all-to-all, NVLink, GPU cluster
6. 全栈开发工程师 - Distributed systems, K8s, Agent infrastructure, data pipeline
7. 搜索算法研究员 - LLM + Search
8. 核心系统研发工程师 - HPC, RDMA, model framework, operator compiler
9. 深度学习研发工程师 - Algorithm + System, training + inference
10. 客户端研发工程师 - iOS/Android
11. 前端研发工程师 - React/Vue

Now for the GLM-5.2 page, let me scroll down to get more technical details.

Let me snapshot the GLM-5.2 page again.

Now I have a very comprehensive view of:

1. **DeepSeek (High-Flyer) job listings** - 47 positions, with the key ones I've captured:
   - Agent深度学习算法研究员: RL, PPO, DPO, Actor-Critic, RLHF/RLAIF, pre-training, fine-tuning, alignment
   - Agent 数据策略工程师: Agent training data, evaluation, RL, data labeling
   - Agent 全栈开发工程师: Agent infrastructure, MCP, Tool Use, Function Calling, RL integration
   - Agent Harness 研发工程师: Model + Harness = Agent, KV Cache, Agent Loop, Tool Use, Reasoning, Planning, Skills, MCP, Memory, Subagent, Multi-Agent
   - 超算网络研发工程师: RDMA, RoCEv2, IB, all-to-all, NVLink, GPU cluster, NCCL
   - 全栈开发工程师: 高并发, 数据处理Pipeline, Agent基础设施, 异构超算, K8s
   - 搜索算法研究员: LLM + Search
   - 核心系统研发工程师: HPC, RDMA, 算子编译器, 模型框架
   - 深度学习研发工程师: 算法+系统, 训练+推理
   - 客户端研发工程师: iOS/Android
   - 前端研发工程师: React/Vue

2. **GLM-5.2 documentation** - Key features:
   - 1M context window
   - 128K max output tokens
   - 面向长任务时代的旗舰模型
   - 项目级工程接管、长程重构执行、生产级规范压力测试
   - MCP support
   - 推荐场景：移动端真机调试、微信小程序开发、小游戏开发

Now I need to synthesize all of this into a comprehensive analysis for a Solution Architect, combining:
- The MoE training flow we discussed
- DeepSeek's job requirements
- GLM-5.2's technical features

Let me organize this as a learning roadmap for an SA.

数据收集完毕。现在结合三方面信息——训练流程、DeepSeek 招聘需求、GLM-5.2 技术栈——梳理 SA 需要掌握的知识体系。

---