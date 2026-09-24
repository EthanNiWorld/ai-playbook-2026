# Mooncake（KVCache 中心的数据面基础设施）

> 最后更新: 2026-09-20
> 领域: AI Infra / LLM Inference
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 月之暗面为 Kimi 打造的 KVCache 中心分离式 serving 架构及其开源数据面组件（Transfer Engine / Mooncake Store）——PD 分离时代 KV cache 的"高速传输 + 分布式存储"层，不是推理引擎
**核心价值**: 把 KV cache 从"单卡显存里的临时状态"变成"集群内可流动、可共享的数据资产"：RDMA 零拷贝传输 + 闲置 CPU/DRAM/SSD 构建分布式 KV 池，真实流量下助 Kimi 多承载 75% 请求
**相关产品**: [vLLM](vllm.md), [SGLang](sglang.md), [EPD 分离](epd-disaggregation.md), [Kimi K 系列](../../moonshot/kimi-k-series.md), [GLM 系列](../../zhipu/glm-series.md)
<!-- SUMMARY_END -->

## 是什么

Mooncake 是 Moonshot AI（月之暗面）Kimi 的生产 serving 平台架构，论文获 **FAST'25 最佳论文**（2025.02，与清华 MADSys 合作）。⚠️ 关键定位：Mooncake **不是推理引擎**——它不含模型执行能力，开源的是"以 KVCache 为中心的数据面"：传输层（Transfer Engine）+ 存储层（Mooncake Store）。它与 vLLM/SGLang 是**互补分层**关系：引擎管计算，Mooncake 管 KV cache 的搬运与存放。2026.02 加入 PyTorch Ecosystem。

## 核心原理

### KVCache 中心的分离式架构

1. **PD 分离**：prefill（算力密集）与 decode（访存密集）拆成独立集群，各自扩缩容、互不阻塞
2. **分布式 KVCache 池**：利用 GPU 集群中闲置的 CPU/DRAM/SSD 构建分级 KV 池，跨实例共享
3. **KVCache 中心调度器**：以 KV cache 的位置/热度为中心调度请求，平衡吞吐与时延 SLO；过载时预测式早拒，避免把算力浪费在注定超 SLO 的请求上
4. 效果（论文口径）：长上下文模拟场景吞吐最高 **+525%**；真实流量下 Kimi 多承载 **75%** 请求

### 开源组件

| 组件 | 开源时间 | 职责 |
|------|---------|------|
| Transfer Engine | 2024.11 | RDMA 零拷贝传输库：多网卡带宽聚合、NVLink、TCP fallback；跨节点搬 KV / embedding / 权重 |
| Mooncake Store | 2025.03 | 基于 Transfer Engine 的分布式 KVCache 池（跨实例共享、GPU→DRAM→SSD 分级） |
| checkpoint-engine（P2P Store） | 2025.09 | 万卡训练权重秒级分发（Kimi-K2 1T 参数 ~20s） |
| 其他 | — | Conductor（调度）、TENT（Transfer Engine NEXT）、EP/PG 设计文档 |

### 与推理引擎的集成时间线（官方 updates）

| 时间 | 事件 |
|------|------|
| 2024.12 | vLLM 官方支持 Transfer Engine 做 disaggregated prefill + KV transfer |
| 2025.04 | SGLang 官方支持 Transfer Engine 作为 PD 分离传输后端；LMCache 支持 Mooncake Store 为 remote connector |
| 2025.05 | NIXL 支持 Transfer Engine 为后端插件；SGLang × Mooncake 发布 DeepSeek 96×H100 PD 分离部署指南 |
| 2025.07 | Kimi K2 128×H200 PD 分离 + 大 EP：prefill 224k / decode 288k tokens/s |
| 2025.09 | SGLang HiCache 接 Mooncake Store 分级存储；vLLM-Ascend 接入；checkpoint-engine 开源 |
| 2025.12 | Transfer Engine 进 vLLM v1 KV Connector 与 TensorRT-LLM；SGLang EPD 分离用其 RDMA 零拷贝传多模态 embedding |
| 2026.02 | 加入 PyTorch Ecosystem；SGLang Encoder Global Cache Manager（全局 ViT embedding 缓存） |
| 2026.04 | SGLang RDMA P2P 权重传输：Kimi-K2 1T 参数 53s→7.2s |
| 2026.05 | vLLM 官方 blog 推介 Mooncake Store |
| 2026.08 | 渗透 RL 训练数据面：Miles（rollout 数据传输后端）、Speculators（hidden state 经 RDMA 在 vLLM worker 与训练器间传输） |

### 案例：GLM-5.3 生产栈中的 Mooncake Transfer

智谱 2026-09-17/18 RSI 长文披露：GLM-5.3 驱动的 Infra Agent 在 10 万卡集群优化中发现——DeepEP v2.1 的 `intranode_dispatch`/`intranode_combine` 两处 C++ 调用未显式释放 GIL，导致同进程内负责 **Mooncake Transfer** 的 Python 线程拿不到 GIL，KV Transfer 调度被推迟、与后续计算的 overlap 被压缩；释放 GIL 后 Prefill+KV Transfer 吞吐大幅提升（端到端 3 倍优化的一部分）。由此确认 GLM-5.3 生产推理栈 = SGLang 基座引擎 + EPD 分离 + DeepEP + **Mooncake Transfer** + 10 万张国产芯片。

## 关键认知框架

### 核心洞察 1：PD 分离催生了独立的"KV 数据面"

- 分离后 KV cache 必须跨节点流动（1M 上下文单请求 KV 达 GB 级），引擎自带通信库不擅长异构大规模搬运 → 专门的传输/存储层成为刚需
- 类比：NCCL/RDMA 之于分布式训练；gRPC 之于微服务化
- 可迁移场景：任何 PD/EPD 分离方案必问"KV 传输层用什么"——目前主流答案是 Mooncake 或 NVIDIA NIXL

### 核心洞察 2：LLM 推理栈四层解耦框架

| 层 | 职责 | 代表 |
|---|------|------|
| 网关调度层 | 路由、负载均衡、SLO 控制、prefix 亲和 | SGLang Model Gateway、vLLM router、Mooncake Conductor |
| 计算面（引擎） | 模型执行、batching、并行 | vLLM、SGLang、TensorRT-LLM |
| KV 数据面（传输） | 跨节点 KV cache 零拷贝搬运 | **Mooncake Transfer**、NVIDIA NIXL |
| KV 存储面（分级池） | GPU→DRAM→SSD 分级缓存、跨实例共享 | Mooncake Store、LMCache、FlexKV（腾讯/NVIDIA） |

- 可迁移场景：评估任何推理方案按四层拆解，一眼看清架构完整度；售前讲国产芯片/EPD 分离/长上下文成本时，数据面是必备叙事组件

### 核心洞察 3：掌握 KV 数据面 = 解锁上层玩法

- 多级缓存、跨实例前缀共享、RL rollout 数据复用（权重广播、hidden state 传输）都建立在数据面之上；Mooncake 已从 serving 渗透进训练侧
- 多模态 embedding 传输与缓存是数据面第二战场：SGLang EPD 用 Mooncake RDMA 零拷贝传 ViT embedding、全局 embedding 缓存跨实例共享，疆域从 KV 扩展到多模态中间产物（详见 [EPD 分离](epd-disaggregation.md)）
- 可迁移场景：判断一家 infra 厂商的技术纵深，看它是否掌握数据面而非只做引擎封装

## 常见误区

| 误区 | 事实 |
|------|------|
| "Mooncake 是一个新的推理引擎" | 它是数据面基础设施（传输 + KV 存储），不含模型执行，须搭配 vLLM/SGLang 等引擎 |
| "做 PD 分离就必须用 Mooncake" | SGLang/vLLM 的 PD 传输也支持 NVIDIA NIXL；Mooncake 是主流选项而非唯一 |
| "KV cache 只是显存里的临时数据，不值得专门系统" | PD 分离后它是要跨节点流动的资产；长上下文单请求 KV 达 GB 级，传输与共享直接决定成本 |
| "Mooncake 只服务 Kimi" | 已开源并被 vLLM/SGLang/TRT-LLM/LMCache/腾讯 FlexKV 等广泛集成，GLM-5.3 生产栈亦在用 |

## 参考资料

- [官方文档] Mooncake Documentation — https://kvcache-ai.github.io/Mooncake/ ；GitHub — https://github.com/kvcache-ai/Mooncake
- [论文] Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving（FAST'25 Best Paper） — https://arxiv.org/pdf/2407.00079 ；ACM — https://dl.acm.org/doi/10.1145/3773772
- [官方] Mooncake Joins PyTorch Ecosystem（2026-02-12） — https://pytorch.org/blog/mooncake-joins-pytorch-ecosystem/
- [媒体/官方] 智谱 GLM-5.3 RSI 长文（InfoQ，2026-09-18） — https://www.infoq.cn/news/O1uIfJx3CF5SZz3ayuaI ；新浪科技转载 — https://news.sina.cn/ai/2026-09-18/detail-inisfpqz3367455.d.html
- [官方文档] GLM-5.3-Flash EPD 架构 — https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-09-20 | 新建文档：Mooncake 定位（数据面非引擎）、KVCache 中心架构、开源组件、引擎集成时间线、GLM-5.3 案例与四层解耦框架 |
| 2026-09-20 | 联动：EPD 分离独立成文（epd-disaggregation.md）——核心洞察 3 补"embedding 传输/缓存是数据面第二战场"，相关产品新增交叉引用 |
