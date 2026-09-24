# EPD 分离（Encode-Prefill-Decode Disaggregation）

> 最后更新: 2026-09-20
> 领域: AI Infra / LLM Inference
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 多模态推理的三级分离架构——把视觉编码（ViT）从 LLM prefill 中拆出，Encoder/Prefill/Decode 三个资源池独立扩缩容，中间经 Mooncake/NIXL/ZMQ 传输 embedding
**核心价值**: 解决多模态"编码阻塞"：ViT 不吃 TP 只能横向扩、文本请求不再被图像请求堵（混合流量文本 TTFT -42.2%）、编码可用低档 GPU 池承接（同 SLO 多服务 70% 流量）；图像重负载下 TTFT 低 6-8×
**相关产品**: [SGLang](sglang.md), [vLLM](vllm.md), [Mooncake](Mooncake.md), [GLM 系列](../../zhipu/glm-series.md)
<!-- SUMMARY_END -->

## 是什么

EPD = Encode–Prefill–Decode 三级分离。多模态（VLM）请求在 LLM prefill 之前多一段**视觉编码**——图片/视频先过 ViT 生成 embedding，LLM 才能开始 prefill。EPD 把这段编码也拆成独立资源池：

```
客户端 → [Encoder 池：只载视觉权重，ViT 编码]
             ↓ vision embedding（Mooncake / NIXL / ZMQ 传输）
        [Prefill 池：language-only，拼接 embedding + 文本 token]
             ↓ KV cache（复用 PD 分离传输逻辑）
        [Decode 池：逐 token 生成]
```

- **与 PD 分离的关系**：PD 分离管"两段 LLM 计算"，EPD 在多模态场景把分离链从 2 级推到 3 级，P→D 的 KV 传输逻辑直接复用
- **代价**：embedding 跨节点传输引入网络开销——图像轻的场景可能负优化（SGLang 官方明示）

## 核心原理

### 为什么需要（四条因果链）

1. **ViT 不吃 TP（反直觉发现）**：Qwen2.5-VL-72B 实测（H20，4 图/请求），ViT 耗时 tp2=492ms / tp4=466ms / tp8=524ms——视觉模型参数小，TP 通信开销盖过计算收益。**纵向切不动，只能横向扩**（多开 encoder 实例、按图数据并行分发）
2. **计算异构阻塞**：ViT（compute-intensive 小模型）与 LLM 抢同一 GPU 互相阻塞
3. **混合流量队头阻塞**：文本请求不需要编码，却排在多模态请求的 ViT 后面干等；NVIDIA 实测 50:50 文图混合流量下，EPD 使文本请求 TTFT **-42.2%**、图像请求 **-30.8%**
4. **成本结构**：编码负载可用低档 GPU 池承接（NVIDIA 案例：2× RTX 6000D 编码 + 4× GB200 PD，同 SLO 多服务 **70%** 流量——不增加高档卡预算）

### 关键机制（SGLang 实现口径）

- **三级角色**：`--encoder-only`（只载视觉权重）/ `--language-only` prefill / decode 实例
- **图像分发**：数据并行——7 张图拆给 3 个 encoder（3/2/2），多实例负载均衡
- **传输后端**：ZMQ（默认，单机）/ Mooncake（RDMA，多机零拷贝）/ NIXL
- **Embedding 缓存**：重复图片不再重复编码（本地前缀缓存默认 4GB；Mooncake 全局 ViT embedding 缓存可跨实例共享）
- **实测**（Qwen3-VL-235B-FP8，8×H20，1080p 平均 4 图/请求）：高负载下 TTFT 低 **6-8×**、TPOT 低 **8-10×**、吞吐约 **2×**（2E1P 配置，代价为多 50% GPU）

### 收益判据（反直觉核心）

EPD 收益不取决于模型总参数，而取决于一个**比值**：

$$\text{EPD 收益} \propto \frac{\text{每请求 ViT 计算量}}{\text{LLM 每 token 有效计算量}}$$

- **分子端**（拉高有利）：图片多、分辨率高、视频输入
- **分母端**（压低有利）：小 dense、**MoE 低激活**、**量化**（LLM 量化到 NVFP4、ViT 仍 BF16，ViT 占比被动升高，colocated goodput 从 1.78× → 2.64×）
- **证据**：NVIDIA 主测 MoE 模型 122B-A10B（激活仅 10B）获 5× TTFT；dense 27B（ViT 参数占比 1.7%）colocated 反而 **0.65× 负收益**，4B（占 7.2%）则 2.62×
- **长输出稀释**：decode 主导 E2E 延迟，OSL 2048 时 E2E 收益从 20.3% 缩到 5.2%
- **边界**：43% 的 TTFT 花在 ViT 开始之前（媒体下载/预处理）——EPD 管不了这段，需前端并行媒体解码等配套（可再降 26%）

## 📄🔧 技术溯源（原创研究 vs 工程实现）

### 📄 原创研究

**Singh et al., *Efficiently Serving Large Multimodal Models Using EPD Disaggregation***（arXiv:2501.05460；**华为加拿大研究院 + 华为云 + Simon Fraser University**；v1 提交 2024-12-25，**ICML 2025 收录**，PMLR 267）

| 论文原创机制 | 工程化现状 |
|-------------|-----------|
| ① 首提 EPD 框架（encoding 与 prefill 解耦） | ✅ 全部被采用（vLLM/SGLang/Dynamo 核心架构） |
| ② IRP 请求内 patch 级并行 | ✅ SGLang 图像分发机制对应（官方博客未标注引用） |
| ③ 黑盒资源分配优化器 | ⚠️ 工程侧缺位（各家仍手动调参/向导配置） |
| ④ 动态角色切换（E/P/D 实例按负载互转） | ⚠️ 主流开源缺位（字节 AIBrix 实践笔记涉及 PD+弹性伸缩/角色切换方向，⚠️ 第三方笔记待验证）——可能的下一波工程方向 |

- 论文实验：MiniCPM-V 2.6 / InternVL2-8B/26B；15× 内存降、22× batch、TTFT -71%；相关工作引用含 Mooncake（Qin et al. 2024）等 PD 分离文献
- 学术伴生：ModServe（Qiu et al. 2025，modality/stage-aware 资源分离，vLLM 博客同列引用）

### 🔧 工程实现（时间线与论文关系）

| 时间 | 实现 | 与论文关系 |
|------|------|-----------|
| 2025 中 | NVIDIA Dynamo 最早以 vLLM 实现 EPD 式分离（vLLM 博客口径，当时文档有限） | 独立工程探索 |
| 2025.11 | vLLM native EPD（PR #25233，0.11.1 起可用，12-15 官方博客；贡献者含昇腾团队，Ascend 910B 复现验证硬件可移植性） | **明确引用 Singh et al. 与 ModServe** |
| 2026.01 | SGLang EPD（rednote hilab + 阿里云 + 蚂蚁 SCT 联合开发） | 架构对应，官方博客未标注引用 |
| 2026.02 | vLLM-Omni 全模态全分离（arXiv:2602.02204） | 扩展到 any-to-any（自身带论文） |
| 2026.09 | NVIDIA Dynamo EPD 官方选型指南（三拓扑方法论） | 产品化 |

> 💡 **溯源洞察**：EPD 论文出自**华为**（加拿大研究院+华为云），vLLM 工程主力亦含昇腾团队——华为在 EPD 上"论文+工程"双轮驱动；SGLang 侧由中国应用公司（小红书/阿里云/蚂蚁）主导落地。另：vLLM 博客自述 "ViT DP + LM TP" 混合并行为 vLLM 首创、SGLang 跟进采用——工程社区内部的"先到先得"亦需分辨。

## 关键选型维度

### 什么时候用 / 不用

| | 条件 |
|---|------|
| ✅ **用 EPD** | 多图/高分辨率/视频输入；短~中输出；**LLM 每 token 有效计算小的模型**（小 dense / MoE 低激活 / 量化——NVIDIA 原文 "fewer active parameters and lower precision"）；文图混合流量；有异构低档 GPU 池 |
| ❌ **不用 EPD** | 图像轻（传输开销>收益）；长输出（decode 主导）；大 dense 模型（ViT 占比太低，dense 27B 实测负收益）；同构 GPU 集群勿拆独立 encoder tier（NVIDIA 明示同构 disaggregated 始终不如 colocated） |

### 拓扑选择（NVIDIA 三拓扑，2026-09 官方口径）

| 拓扑 | 结构 | 适用 |
|------|------|------|
| Aggregated | E+P+D 同 worker | 图像轻、长输出、大 dense 模型 |
| Colocated encoder | encoder 与 PD 共享 GPU（分离调度不独占卡） | 同构集群默认更优 |
| Disaggregated encoder | 独立低档 GPU tier 承接编码 | 有异构硬件时（低档卡编码、高档卡专供 PD） |

## 关键认知框架

### 核心洞察 1：EPD 与 PD 同源——"计算特性不同 → 资源池分开专精"

- 多模态把分离链从 2 级推到 3 级；可推广到任何请求链路中计算特性突变的环节（如视频生成的 encoder/transformer 解耦）
- 可迁移场景：评估任何分离式架构，先画请求链路、标记各段计算特性，突变点即分离候选

### 核心洞察 2：收益判据是比值，不是总参数

- "ViT 计算 / LLM 每 token 有效计算"——MoE 化、量化、稀疏注意力都在压低分母，**EPD 是 MoE 化+量化+多模态三大趋势共振的优化，行业越演进越是标配**
- 可迁移场景：GLM-5.3-Flash（320B 总参/18B 激活 + 混合注意力）LLM 计算被压到极低，正是 EPD 受益者而非反例——智谱为它上生产级 EPD 的底层原因；评估多模态私有化方案时先算这个比值

### 核心洞察 3：数据面第二战场

- embedding 传输/缓存把 Mooncake/NIXL 的疆域从 KV 扩展到多模态中间产物；缓存从"KV 前缀"扩展到"跨实例视觉 embedding"
- 可迁移场景：多模态推理方案把"KV 数据面 + embedding 数据面"统一评估（详见 [Mooncake](Mooncake.md) 四层框架）

## 各厂商实现对照

| 厂商 | 方案要点 | 传输层 |
|------|---------|--------|
| 智谱 GLM | GLM-5.3-Flash 官方文档明确生产级 EPD：编码/预填充/解码独立调度独立扩缩容；SGLang 基座 + DeepEP + 国产芯片 | Mooncake |
| SGLang 社区 | 三级 EPD（2026.01 发布），rednote hilab（小红书）+ 阿里云 + 蚂蚁 SCT 联合开发 | ZMQ/Mooncake/NIXL |
| NVIDIA | Dynamo EPD 三拓扑（2026.09 官方选型框架）；TRT-LLM PD 分离已集成 Mooncake/NIXL；Baseten 等已采用 | NIXL |
| vLLM | vLLM EPD（2025.12 博客）→ vLLM-Omni 全分离 any-to-any（2026.02），encoder/prefill/decode 独立 GPU 池 | Mooncake 双连接器 |
| 月之暗面 | Mooncake 数据面从 KV 传输扩展到 embedding 传输与全局缓存 | Mooncake |
| 阿里云 PAI | PAI-EAS EP+PD 分离部署模板（2025.11 文档，BladeLLM 自研引擎）；阿里云工程师为 SGLang EPD 共同作者 | — |
| 华为昇腾 | vLLM-Ascend EPD 分离官方教程（多节点分布式负载均衡） | Mooncake |
| 字节跳动 | AIBrix 公开资料以 PD 分离/弹性伸缩/KV 卸载为主，未见 EPD 专项披露（截至 2026-09，待验证） | — |
| DeepSeek | 官方推荐 SGLang + Mooncake PD 分离（96×H100 指南）；多模态独立 EPD 未公开 | Mooncake |
| OpenAI/Anthropic/Google | 闭源不公开 serving 架构 | — |

> 详细产品分析见各厂商对应文档

## 最佳实践

### 可迁移场景（推荐）

- **多模态私有化部署**（图像审核/文档理解/视频分析）：按"ViT/LLM 计算比值 + 输出长度 + 流量结构"三要素决定是否上 EPD
- **异构集群降本**：低档 GPU 承接编码池，高档 GPU 专供 PD（NVIDIA 案例：+70% 流量不增加 GB200 预算）
- **文图混合 API 服务**：EPD 消除文本请求队头阻塞（文本 TTFT -42.2%）
- **售前叙事**：EPD 收益判据（比值论）+ 国产原创格局（华为论文 + 小红书/阿里云/蚂蚁工程 + 昇腾复现）

## 常见误区

| 误区 | 事实 |
|------|------|
| "模型总参数越小 EPD 收益越大" | 判据是"LLM 每 token 有效计算 vs ViT 计算"的比值；MoE（激活小）恰恰是受益者，dense 27B 才负收益 |
| "EPD 总是更快" | 图像轻场景传输开销 > 卸载收益，可能负优化（SGLang 官方明示） |
| "拆开就一定好" | 同构 GPU 集群拆独立 encoder tier 始终不如 colocated（NVIDIA 明示） |
| "EPD 能优化全部 TTFT" | 43% TTFT 在 ViT 开始前（下载/预处理），需前端并行媒体解码等配套 |
| "ViT 也可以靠 TP 扩" | 实测 tp8 比 tp2 更慢——参数小、通信开销主导，只能横向扩实例 |

## 参考资料

- [官方] SGLang EPD Disaggregation 博客（LMSYS，2026-01-12，rednote hilab/阿里云/蚂蚁联合） — https://www.lmsys.org/blog/2026-01-12-epd/ ；文档 — https://lmsysorg.mintlify.app/docs/advanced_features/epd_disaggregation
- [官方] NVIDIA: When to Use EPD Disaggregation（2026-09-09，Dynamo 三拓扑 + 全因素选型框架） — https://developer.nvidia.com/blog/when-to-use-encode-prefill-decode-disaggregation-to-accelerate-multimodal-model-serving/
- [官方] vLLM EPD 博客（2025-12-15） — https://vllm.ai/blog/2025-12-15-vllm-epd ；vLLM-Omni 论文 — https://arxiv.org/html/2602.02204v1 ；文档 — https://docs.vllm.ai/projects/vllm-omni/en/latest/design/feature/disaggregated_inference/
- [论文] EPD 概念源头（Singh et al.，华为加拿大研究院+华为云+SFU，ICML 2025） — https://arxiv.org/abs/2501.05460 （v1 2024-12-25）
- [官方] 智谱 GLM-5.3-Flash 文档（生产级 EPD 架构） — https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash
- [官方] 阿里云 PAI-EAS EP+PD 分离部署（2025-11-25） — https://help.aliyun.com/zh/pai/deployment-moe-model-based-on-expert-parallel-and-pd-separation
- [官方] vLLM-Ascend EPD 分离教程 — https://docs.vllm.ai/projects/ascend/zh-cn/main/user_guide/feature_guide/epd_disaggregation.html
- [官方] NVIDIA Dynamo 文档 — https://docs.nvidia.com/dynamo/ ；TRT-LLM Disaggregated Serving — https://nvidia.github.io/TensorRT-LLM/blogs/tech_blog/blog5_Disaggregated_Serving_in_TensorRT-LLM.html
- [媒体] Baseten × Dynamo EPD — https://www.baseten.co/blog/nvidia-dynamo-day-baseten-inference-stack/

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-09-20 | 新建文档：EPD 分离原理与机制、收益判据（ViT/LLM 有效计算比值论）、技术溯源（华为 ICML 2025 论文 vs 各厂商工程实现）、NVIDIA 三拓扑选型、厂商对照表 |
