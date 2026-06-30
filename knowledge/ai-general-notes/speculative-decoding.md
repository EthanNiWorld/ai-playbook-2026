# 推测解码（Speculative Decoding）

> 最后更新: 2026-06-30
> 领域: AI Infra / LLM Inference
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: LLM 推理加速主流范式——轻量草稿模型快速"猜"多个 token，目标大模型一次性并行验证，保持输出分布不变的同时显著减少前向计算次数
**核心价值**: 在不降低模型质量的前提下，将推理吞吐提升 50%+（生产环境），单用户生成速度提升 57%–85%
**相关产品**: [DeepSeek DSpark](../deepseek/general_intro.md), DFlash (z-lab.ai), Eagle3
<!-- SUMMARY_END -->

## 是什么

推测解码（Speculative Decoding）是加速大模型自回归生成的核心技术。标准自回归生成是严格串行的——每个 token 依赖上一个 token，每生成一个都要跑一次完整前向计算，GPU 大量时间在等内存搬运 KV-Cache 而非做计算。

推测解码的解法是 **draft-and-verify（草稿-验证）** 循环：

1. **草稿阶段**：用一个轻量快速的草稿模型（draft model）快速生成多个候选 token
2. **验证阶段**：目标大模型一次性并行验证所有候选 token
3. **接受/拒绝**：验证通过的 token 直接接受，失败后从第一个不匹配处重新生成

关键性质：**正确实现的推测解码保持目标模型的输出分布完全不变**——不是近似，是数学上等价。加速的是效率，不牺牲质量。

## 核心原理

### 自回归生成的瓶颈

标准自回归生成中，每个 token 的生成需要一次完整的目标模型前向传播：

$$L_{\text{AR}} = n \cdot T_{\text{forward}}$$

其中 $n$ 是输出 token 数，$T_{\text{forward}}$ 是单次前向延迟。GPU 的并行计算能力被浪费在串行依赖上。

### 推测解码的加速公式

推测解码的平均每 token 延迟为：

$$L = \frac{T_{\text{draft}} + T_{\text{verify}}}{\tau}$$

其中 $\tau \in [1, \gamma+1]$ 是每个周期的期望接受 token 数（含 bonus token），$\gamma$ 是草稿长度。加速比 $\eta = L_{\text{target}} / L$。

加速来自两个方向：
- **提高接受长度 $\tau$**：草稿模型越准，一次验证通过的 token 越多
- **降低草稿开销 $T_{\text{draft}}$**：草稿模型越快，"猜"的成本越低

### 三种主流草稿方法对比

| 方法 | 草稿方式 | 代表实现 | 优势 | 短板 |
|------|---------|---------|------|------|
| **自回归草稿** | 串行逐 token 生成 | Eagle3 | 依赖建模好，草稿质量高 | 草稿本身也串行，越猜越慢，加速上限 ~2-3× |
| **扩散并行草稿** | 块级扩散模型一次前向并行出所有 token | DFlash (z-lab.ai) | 极致并行速度，5 层扩散 > Eagle3 加速 | 后续 token 容易 suffix decay（后缀跑偏） |
| **半自回归草稿** | 并行骨干 + 轻量顺序头 + 置信度调度 | **DSpark** (DeepSeek) | 草稿质量高 + 系统级负载感知调度 | 需训练专用 draft 模块、校准、serving 集成 |

### DSpark 的两个核心创新

**1. 半自回归生成（Semi-Autoregressive Generation）**

DSpark 用并行骨干（parallel backbone）快速生成整块 token 表示，再在上面接极轻量的顺序头注入局部依赖信息：
- **Markov Head**：只看前一个 token，最轻量
- **RNN Head**：可携带更多前缀历史

这解决了并行草稿的核心痛点——suffix decay（后续 token 和前文脱节）。论文数据：**2 层 DSpark 已超过 5 层 DFlash 的接受长度**。

**2. 置信度调度验证（Confidence-Scheduled Verification）**

传统推测解码盲目验证所有草稿 token，高并发下浪费目标模型算力。DSpark 增加置信度头（confidence head），预测每个草稿 token 的"存活概率"，结合硬件负载动态决定验证前缀长度：
- 轻负载：多验证几个 token
- 重负载：激进剪枝，只验证高置信度前缀

这是**模型侧（confidence head）和系统侧（hardware-aware scheduler）的联合优化**，从纯模型优化走向模型+系统协同。

### 工程部署要点

- **目标模型零侵入**：目标模型权重完全冻结，无需修改 checkpoint。草稿模型作为"外挂模块"附加
- **草稿模型极轻量**：参数量仅占目标模型的几个百分点（共享 embedding 和 LM head）
- **草稿模型 1:1 绑定**：每个目标模型需训练专用草稿模型，不能跨模型复用
- **serving 框架需支持**：推理引擎需实现 speculative decoding 协议（如 SGLang 已集成 DFlash）

## 关键认知框架

### 核心洞察 1：推理效率竞争正在从"模型侧"走向"模型+系统联合优化"

- 早期推测解码只关注"草稿猜得准不准"（模型侧），DSpark 的置信度调度代表了"验证得智不智能"（系统侧）的进化方向
- 这意味着推理加速不再只是算法问题，而是 serving 架构问题——调度器、负载感知、硬件特性都成为优化维度
- **可迁移场景**：任何需要高并发低延迟的 AI 服务（API 平台、Agent 长链路、实时对话）

### 核心洞察 2："架构效率 > 暴力堆算力"的哲学从训练侧延伸到了推理侧

- DeepSeek 的叙事线：V2/V3 用 MLA+MoE 降低训练成本 → V4 用混合注意力降低长上下文计算成本 → DSpark 用推测解码降低推理服务成本
- 这暗示模型公司的竞争力正在从"谁训得大"转向"谁服务得便宜"
- **可迁移场景**：评估模型厂商时，不只看 benchmark，还要看推理效率和单位 token 成本

### 核心洞察 3：推测解码使 Agent 长链路在经济上更可行

- Agent 每次工具调用的 I/O 都追加到上下文，链路越长推理成本越高
- 推理加速 50%+ 意味着同等硬件预算下 Agent 可以跑更长的链路
- **可迁移场景**：AI Coding Agent、多 Agent 协作、复杂 RAG pipeline

## 各厂商实现对照

| 方法 | 开发方 | 状态 | 适用模型 | 开源 |
|------|--------|------|---------|------|
| DSpark | DeepSeek + 北京大学 | 已发布 | V4-Flash / V4-Pro（已在 API 上线）；离线验证 Qwen3 / Gemma4 | MIT，DeepSpec 代码库 |
| DFlash | z-lab.ai | 已发布 | Qwen3 / LLaMA-3.1 | MIT，DeepSpec 代码库 |
| Eagle3 | 微软 | 已发布 | 通用 | 开源 |
| MTP | DeepSeek（V4 内置） | 已发布 | V4 系列 | 内置 |

> 详细产品分析见 [DeepSeek 公司分析](../deepseek/general_intro.md)

## 最佳实践

### 可迁移场景（推荐）

- **API 服务降本**：同等 GPU 集群多服务 50%+ 用户，直接改善利润率
- **Agent 长链路加速**：减少端到端延迟，改善用户体验
- **本地部署提效**：单卡可服务更多并发请求
- **推理时间扩展（Inference-time scaling）**：更低的每 token 成本使得 reasoning effort 高模式在经济上更可行

## 常见误区

| 误区 | 事实 |
|------|------|
| "推测解码会降低模型质量" | 正确实现的推测解码保持目标模型输出分布完全不变（数学等价） |
| "需要修改目标模型 checkpoint" | 目标模型权重完全冻结，草稿模型是外挂模块 |
| "DSpark 让所有模型快 4-6 倍" | 661%/406% 等极端数字出现在严格 SLA 下基线已近极限时；常规生产合理预期：吞吐 +51%–52%，单用户快 57%–85% |
| "草稿模型可以跨模型复用" | 草稿模型需针对每个目标模型单独训练，1:1 绑定 |
| "推测解码 = 模型压缩/量化" | 完全不同的技术路线，推测解码不改变模型参数，而是减少前向计算次数 |

## 参考资料

- [论文] DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation (DeepSeek + Peking University, 2026-06-27)
- [论文] DFlash: Block Diffusion for Flash Speculative Decoding — https://arxiv.org/html/2602.06036v1
- [模型卡] DeepSeek-V4-Flash-DSpark / DeepSeek-V4-Pro-DSpark (HuggingFace, MIT 许可)
- [代码] DeepSpec GitHub 仓库（推测解码训练评估代码库，含 DSpark / DFlash / Eagle3）
- [分析] DeepSeek DSpark Explained — https://kingy.ai/blog/deepseek-dspark-speculative-decoding/
- [报道] DeepSeek Releases DSpark — https://www.marktechpost.com/2026/06/27/deepseek-releases-dspark/
- [报道] Faster AI, lower costs: DSpark eases inference bottlenecks — https://www.scmp.com/tech/big-tech/article/3358647/
- [讨论] Reddit r/unsloth — https://www.reddit.com/r/unsloth/comments/1ugv32u/

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-30 | 新建文档：推测解码技术通识 + DSpark/DFlash/Eagle3 方法对比，基于 ai-native-expert 深度解析 |
