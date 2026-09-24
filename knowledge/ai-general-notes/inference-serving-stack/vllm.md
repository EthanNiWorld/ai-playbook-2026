# vLLM

> 最后更新: 2026-09-20
> 领域: AI Infra / LLM Inference
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 生态覆盖最广的开源 LLM 推理与服务引擎——以 PagedAttention 页式 KV cache 管理起家，把模型权重变成高并发、OpenAI 兼容的 API 服务
**核心价值**: 解决推理"放得下、跑得快"：PagedAttention 将 KV cache 显存浪费压到近零，continuous batching 让吞吐提升一个数量级；全模型/全硬件后端覆盖使其成为事实标准之一
**相关产品**: [SGLang](sglang.md), [Mooncake](Mooncake.md), [EPD 分离](epd-disaggregation.md), [推测解码](../speculative-decoding.md)
<!-- SUMMARY_END -->

## 是什么

vLLM 是 UC Berkeley Sky Computing Lab（Ion Stoica 团队）于 2023 年发布的开源 LLM 推理/服务引擎（serving engine）。它位于"模型权重"与"线上流量"之间，负责显存管理、批处理调度、多卡并行与 API 服务化——没有这一层，模型只能 `model.generate()` 单条串行跑，吞吐差一个数量级以上。

一句话理解三层职责：

- **显存管理**：KV cache 放哪、怎么省（PagedAttention）
- **调度**：哪些请求一起算、什么时候算（continuous batching / chunked prefill）
- **服务化**：OpenAI 兼容 API、流式输出、多 LoRA、量化部署

## 核心原理

### PagedAttention（招牌创新，SOSP'23 论文）

传统方案按"最大可能长度"为每个请求预分配连续 KV cache 显存，60%–80% 被内部碎片浪费。PagedAttention 借鉴操作系统虚拟内存思想：

- KV cache 切成固定大小的"页"（block）：逻辑上连续、物理上可离散存放
- 按需分配、引用计数共享（beam search / 多候选可共享前缀页）
- 显存浪费压到近零（论文口径 <4%）→ 同等显存塞下更多并发请求 → 吞吐数量级提升

### 调度与执行栈

| 机制 | 作用 |
|------|------|
| Continuous batching（迭代级调度） | 请求粒度进出批次，不等整批结束，GPU 不空转 |
| Chunked prefill | 长 prompt 切块与 decode 混合调度，防 prefill 头阻塞 |
| Automatic Prefix Caching (APC) | 跨请求复用共享前缀 KV（对标 SGLang RadixAttention） |
| TP / PP / EP 并行 | 多卡张量/流水/专家并行 |
| 量化 + CUDA Graph + 投机解码 | FP8/INT8、消除 kernel 启动开销、加速 decode |

### 数据面集成（PD 分离时代）

vLLM v1 提供 KV Connector 插件体系，把跨节点 KV cache 传输/存储交给专业数据面组件，而非自研传输层：

- **Mooncake**：2024.12 官方支持 Transfer Engine 做 disaggregated prefill；2025.12 Transfer Engine 直接集成进 vLLM v1 KV Connector；2026.05 官方 blog 推介 Mooncake Store 做跨实例 KV 共享；vLLM-Ascend 用 Mooncake Store 做分布式 KV 池（2025.09）；vLLM-Omni 提供 MooncakeStoreConnector 与 MooncakeTransferEngineConnector（2026.02）
- **NVIDIA NIXL**：PD 分离传输后端之一（NIXL 亦反向兼容 Mooncake Transfer Engine 为插件，2025.05）
- **LMCache**：KV 分级缓存，2025.04 起支持 Mooncake Store 为 remote connector
- **原生 EPD**：多模态编码器分离实现 2025.11 合并（PR #25233，0.11.1 起可用），vLLM-Omni 扩展至全模态全分离——详见 [EPD 分离](epd-disaggregation.md)

详见 [Mooncake](Mooncake.md)。

### 生态与治理

- **硬件覆盖最广**：NVIDIA / AMD / Intel Gaudi / Google TPU / AWS Neuron / 昇腾（vllm-ascend 插件）/ CPU，芯片厂商 Day 0 适配 vLLM 已成标配（含国产芯片）
- **产业背书**：Red Hat 于 2024.11 宣布收购 vLLM 核心贡献方 Neural Magic，vLLM 成为其 AI 推理产品线基座

## 关键选型维度（vLLM vs SGLang）

| 维度 | vLLM | SGLang | 怎么选 |
|------|------|--------|--------|
| 生态/硬件广度 | ⭐ 最全（多云、多芯片默认适配） | 聚焦 NVIDIA + 部分国产芯 | 异构硬件、多云交付 → vLLM |
| 超大 MoE 生产部署 | 支持，公开标杆案例较少 | ⭐ 事实标准（DeepSeek/Kimi/GLM 旗舰、万卡 RL rollout） | 1T 级 MoE + 大 EP → SGLang |
| 前缀密集负载（多轮/Agent/共享 system prompt） | APC 可用 | ⭐ RadixAttention + HiCache 多级缓存更成熟 | 高前缀重叠率 → 优先 SGLang |
| 结构化生成 | 支持（guided decoding） | ⭐ 原生 DSL + 约束解码优化 | 重约束输出 → SGLang |
| 上手/托管 | 文档全、云厂商托管最多 | 文档全，偏工程 | 快速 PoC → vLLM |

> 2026 年多方基准共识：**两者谁快取决于 workload 前缀重叠率（prefix overlap ratio）**，无绝对优劣 [来源：Spheron / atomic.chat 对比基准]。

## 关键认知框架

### 核心洞察 1：推理引擎的壁垒是"显存管理 + 调度"，不是"能跑模型"

- LLM 推理成本大头 = KV cache 占显存 + decode 阶段访存带宽受限；PagedAttention 解决"放得下"，continuous batching 解决"不空转"
- 可迁移场景：评估任何推理引擎先问两个数——KV cache 显存利用率、调度器空转率

### 核心洞察 2：计算面引擎正在与数据面解耦

- PD 分离后 KV cache 需要跨节点流动，vLLM 选择用 KV Connector 插件体系开放这一层（Mooncake / NIXL / LMCache），而非自研传输层
- 可迁移场景：售前方案按"引擎 + 数据面 + 存储池"三层分别选型（见 [Mooncake](Mooncake.md) 的四层框架）

### 核心洞察 3：生态广度是 vLLM 的护城河

- "什么模型什么卡都能跑"使其成为异构环境的兜底选项；Red Hat 收购 Neural Magic 后企业级支持商业化
- 可迁移场景：客户硬件环境不确定/异构时，vLLM 是风险最低的默认答案

## 常见误区

| 误区 | 事实 |
|------|------|
| "vLLM 一定比 SGLang 快（或慢）" | 取决于 workload 前缀重叠率；两者机制已趋同（vLLM 有 APC，SGLang 底层也用 paged kernel） |
| "PagedAttention 与 RadixAttention 互斥" | 同一问题（KV cache 管理）的两个切面：请求内显存利用率 vs 跨请求前缀复用；现代引擎两者兼备 |
| "vLLM 支持 PD 分离 = 自带高速传输层" | PD 分离的 KV 传输依赖外部数据面（Mooncake / NIXL），引擎只提供 Connector 接口 |
| "vLLM 是研究项目，不能上生产" | Red Hat 企业化背书、云厂商广泛托管，是生产级事实标准之一 |

## 参考资料

- [官方文档] vLLM Documentation — https://docs.vllm.ai/
- [论文] Efficient Memory Management for Large Language Model Serving with PagedAttention（SOSP 2023）
- [官方] vLLM Blog：Mooncake Store 跨实例 KV 共享（2026-05-07，经 Mooncake 官方 updates 转引）
- [官方] vLLM-Ascend PD 分离（Mooncake，单节点）教程 — https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/features/pd_disaggregation_mooncake_single_node.html
- [媒体] Red Hat 宣布收购 Neural Magic（2024-11）
- [对比基准] vLLM vs SGLang 2026（prefix overlap 决定论） — https://www.spheron.network/blog/vllm-vs-sglang-2026/ ；https://atomic.chat/blog/llm-updates/sglang-vs-vllm ；https://inferenceengineering.tech/learn/vllm-vs-sglang-vs-tensorrt-llm/

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-09-20 | 新建文档：vLLM 定位、PagedAttention、调度栈、数据面集成与 vLLM vs SGLang 选型维度 |
| 2026-09-20 | 联动：EPD 分离独立成文（epd-disaggregation.md）——数据面集成补原生 EPD（PR #25233）条目，相关产品新增交叉引用 |
