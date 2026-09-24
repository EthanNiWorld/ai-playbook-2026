# SGLang

> 最后更新: 2026-09-20
> 领域: AI Infra / LLM Inference
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 超大 MoE 生产部署事实标准的开源 LLM 推理引擎——RadixAttention 前缀复用 + PD/EPD 分离 + 大 EP 并行，DeepSeek / Kimi / GLM 旗舰的官方首选部署栈
**核心价值**: 解决"别重复算"与"拆得开"：基数树跨请求 KV 复用 + 多级缓存 + 与 Mooncake 深度耦合的分离式架构，在 Agent/多轮/长上下文高前缀重叠负载下吞吐领先
**相关产品**: [vLLM](vllm.md), [Mooncake](Mooncake.md), [EPD 分离](epd-disaggregation.md), [GLM 系列](../../zhipu/glm-series.md), [推测解码](../speculative-decoding.md)
<!-- SUMMARY_END -->

## 是什么

SGLang 是 LMSYS Org（UC Berkeley 系，Chatbot Arena / Vicuna 团队）2024 年发布的开源 LLM 推理引擎，论文获 NeurIPS'24 收录（"SGLang: Efficient Execution of Structured Language Model Programs"）。与 vLLM 同宗同源但起点不同：SGLang 最初是"结构化 LM 程序"的执行引擎（自带前端 DSL），其后端调度系统（RadixAttention）独立演进为通用 serving 引擎。

## 核心原理

### RadixAttention（招牌创新）

- 用**基数树（Radix Tree）**组织所有请求的 KV cache：共享前缀（system prompt、多轮历史、few-shot 示例）只算一次、存一份，后续请求自动命中复用
- 配合 cache-aware 调度（前缀相似的请求路由到同一节点），多轮对话/Agent 场景缓存命中率与吞吐显著优于纯页式管理
- 树节点按 LRU 驱逐；底层 kernel 同样是分页实现（与 vLLM 趋同）

### 生产级机制栈

| 机制 | 作用 |
|------|------|
| HiCache 多级缓存 | RadixAttention 从 GPU 显存扩展到 host DRAM → 远端存储（2025.09 官方集成 Mooncake Store） |
| PD 分离 | prefill/decode 拆池独立扩缩容；传输后端官方支持 **Mooncake 与 NVIDIA NIXL** 双选项（2025.04 起） |
| EPD 分离 | 多模态场景再拆出 Encoder（ViT）池，Mooncake RDMA 零拷贝传 embedding（2025.12）；Encoder Global Cache Manager 跨实例共享 ViT embedding（2026.02）；图像重负载实测 TTFT 低 6-8×，详见 [EPD 分离](epd-disaggregation.md) |
| DP attention + DeepEP | 大 EP 并行下的注意力数据并行与 MoE all-to-all 通信，DeepSeek/Kimi 级 MoE 标配 |
| 结构化生成 | 正则/JSON 约束解码（FSM 压缩跳转），吞吐优于通用方案 |
| Model Gateway（原 Router） | PD 分离下的请求路由、负载均衡、容错 |

### 生产采用（为什么它是超大 MoE 事实标准）

- **DeepSeek 官方推荐**部署引擎；Mooncake 团队支持 SGLang 发布 DeepSeek PD 分离 96×H100 部署指南（2025.05）
- **Kimi K2**：128×H200 PD 分离 + 大 EP，prefill 224k / decode 288k tokens/s（2025.07）；RL 权重经 Mooncake RDMA P2P 广播，1T 参数 53s→7.2s（2026.04）
- **GLM 旗舰**：GLM-5.3 生产栈 = SGLang 基座自研引擎 + EPD 分离 + DeepEP + Mooncake Transfer + 10 万张国产芯片（智谱 2026-09 RSI 长文披露）；GLM-5.3-Flash Day 0 国产芯片适配（壁仞）基于 SGLang；社区亦有 SGLang PD + Mooncake 部署 GLM-5.1（744B MoE）实践（issue #23020）
- **RL rollout**：veRL / slime / Miles 等训练框架默认推理后端

## 关键选型维度（SGLang vs vLLM）

| 维度 | SGLang | vLLM | 怎么选 |
|------|--------|------|--------|
| 超大 MoE + 大 EP 生产部署 | ⭐ 事实标准 | 支持，公开标杆案例较少 | 1T 级 MoE 私有化 → SGLang |
| 前缀密集负载（Agent/多轮/共享前缀） | ⭐ RadixAttention + HiCache | APC 可用 | 高前缀重叠率 → SGLang |
| 分离式架构（PD/EPD） | ⭐ 与 Mooncake 集成最深（四条线） | KV Connector 插件体系 | 重度分离式架构 → SGLang |
| 生态/硬件广度 | 聚焦 NVIDIA + 部分国产芯（壁仞/昇腾已验证） | ⭐ 最全 | 异构多云 → vLLM |
| RL 训练配套（rollout/权重广播） | ⭐ 训练框架默认后端 | 支持 | RL 场景 → SGLang |

## 关键认知框架

### 核心洞察 1：前缀复用是 Agent 时代的吞吐杠杆

- Agent/多轮对话的上下文天然高前缀重叠（system prompt + 历史 + 工具返回逐轮累积），RadixAttention 把"重复算前缀"变成"查树命中"
- 可迁移场景：评估 Agent 产品推理成本时，缓存命中率是第一变量（呼应缓存亲和路由实践）

### 核心洞察 2：超大 MoE 部署是系统工程，引擎只是冰山一角

- 1T 级 MoE serving = 引擎（SGLang）+ EP 通信（DeepEP）+ KV 传输（Mooncake）+ 调度（Gateway）+ 芯片适配的联合工程；GLM-5.3 的 GIL 案例（DeepEP C++ 调用未释放 GIL，卡住同进程 Mooncake Transfer 线程）说明瓶颈常藏在组件接缝处
- 可迁移场景：售前讲旗舰模型私有化部署，必须按全栈清单逐项核问，不能只说"支持 SGLang"

### 核心洞察 3：引擎与数据面共生演进

- SGLang 是 Mooncake 集成最深的引擎（PD / EPD / HiCache / 权重广播四条线），两者形成"计算面 + 数据面"事实搭档
- 可迁移场景：选型时把引擎与其数据面生态打包评估，而非孤立对比引擎

## 常见误区

| 误区 | 事实 |
|------|------|
| "SGLang 只是个 prompt 编程 DSL" | 前端 DSL 是其起源，今天的 SGLang 是完整生产级 serving 引擎 |
| "RadixAttention 在所有负载下都优于 PagedAttention" | 优势集中在前缀重叠率高的负载；低重叠场景两者相当，且机制已趋同 |
| "PD 分离开箱即用" | 需配传输后端（Mooncake / NIXL）+ 路由（Gateway）+ RDMA 网络规划 |
| "SGLang 只适配 NVIDIA" | GLM-5.3-Flash 已验证国产芯片 Day 0 适配（壁仞等），昇腾亦有支持 |

## 参考资料

- [官方文档] SGLang Documentation — https://docs.sglang.ai/
- [官方文档] PD Disaggregation（Mooncake / NIXL 双后端） — https://docs.sglang.ai/advanced_features/pd_disaggregation.html
- [论文] SGLang: Efficient Execution of Structured Language Model Programs（NeurIPS 2024）
- [官方] Mooncake × SGLang Integration — https://kvcache-ai.github.io/Mooncake/getting_started/examples/sglang-integration/index.html
- [媒体/官方] 智谱 GLM-5.3 RSI 长文（InfoQ，2026-09-18） — https://www.infoq.cn/news/O1uIfJx3CF5SZz3ayuaI
- [官方] 壁仞 Day0 适配 GLM-5.3-Flash（基于 SGLang，2026-09-07） — https://www.birentech.com/news/egy64w6zdtrkwy3pxr7hxpo4/
- [社区] SGLang issue #23020（SGLang PD + Mooncake 部署 GLM-5.1） — https://github.com/sgl-project/sglang/issues/23020

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-09-20 | 新建文档：SGLang 定位、RadixAttention、PD/EPD 分离机制栈、超大 MoE 生产采用与选型维度 |
| 2026-09-20 | 联动：EPD 分离独立成文（epd-disaggregation.md）——机制栈 EPD 行补实测数字（TTFT 6-8×）与链接，相关产品新增交叉引用 |
