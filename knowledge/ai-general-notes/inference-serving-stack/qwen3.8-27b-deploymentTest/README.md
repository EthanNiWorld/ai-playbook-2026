# Qwen3.8-27B 双卡 Blackwell 部署与性能实测

> 最后更新: 2026-10-28  
> 领域: AI Infra / LLM Inference / vLLM  
> 状态: Reviewed（阶段性实测，持续迭代）

<!-- SUMMARY_START -->
**一句话说明**: 在阿里云 ECS 双 RTX PRO 5000 72GB Blackwell 上部署 Qwen3.8-27B-FP8，对比双 TP1 与 TP2、并发上限和 prefill batch，并建立面向商业化 Goodput 的调优框架。  
**核心价值**: 用真实数据区分“单流最快”“高并发 SLA 最优”和“峰值吞吐最高”，避免把某一负载下的最优参数误当成通用答案。  
**相关产品**: [vLLM](../vllm.md), [推测解码](../../speculative-decoding.md), [Qwen](../../../../alibaba-ai-hub/maas/qwen.md)
<!-- SUMMARY_END -->

## 1. 结论速览

### 当前实测结论

- **单流/低并发优先 TP2**：8K 输入、并发 1 时，TP2 的 TTFT P50 为 **0.96s**，单流输出吞吐约 **45 tok/s**。
- **高并发 SLA 优先双 TP1 + MTP=3**：8K/512 输出、并发 16 时，总 TPM 从 MTP 关闭的 **295,750** 提升至 **394,576**，TTFT P50 为 **2.73s**。
- **原始 TPM 与 SLA 最佳点不同**：8K/128、MTP 关闭时，原始最大总 TPM 为 **611,115**（并发 48，SLA 失败）；聚合 P50/P95 均达标时最高为 **580,264**（并发 20）。
- **单请求有效 TPM 另有一个最佳点**：按每请求 TTFT≤8s 过滤，并发 12 的有效总 TPM 最高，为 **512,621**；并发 20 虽原始 TPM 更高，有效 TPM 降至 340,906。
- **Prefix Cache 是商业化核心变量**：4.2K 输入、并发 12 时，共享前缀使命中率达到 **58.66%**，总 TPM 从 **411,975** 提至 **597,042**，TTFT P50 从 **3.84s** 降至 **0.49s**。
- **FP8 KV 在高并发下显著优于 BF16 KV**：MTP 关闭、8K/512、并发 16 时，FP8 KV 总 TPM 高 **35.6%**，每实例 KV token 容量约为 BF16 的 **1.75 倍**。
- **Prefill batch 不是越大越好**：`max-num-batched-tokens=16384` 优于本次测过的 8192 和 32768。
- **27B 不必须 TP2**：FP8 权重实际单卡加载约 28.42GiB，72GB 单卡可完整运行 TP1；是否使用 TP2 取决于负载和 SLA，而不是模型名称。
- **当前配置证明了达标能力，但尚不能宣称生产 SLA 已稳定通过**：不同轮次仍可能出现明显波动，商业化前需用真实负载进行多轮、长时间验证。

### 当前推荐运行点

| 项目 | 推荐值 |
|---|---|
| 模型 | Qwen3.8-27B-FP8 |
| 拓扑 | 两个 TP1 独立实例 |
| 负载均衡 | Nginx `least_conn` |
| 每实例 `max-num-seqs` | 16 |
| 整机入口初始并发上限 | 16；短输出可继续扫描 20，长输出先保守控制在 16 |
| `max-num-batched-tokens` | 16384 |
| `max-model-len` | 32768 |
| KV Cache | FP8 |
| CUDA Graph | 开启，`-O2`，不要使用 `--enforce-eager` 作为吞吐开关 |
| MTP | 开启，`num_speculative_tokens=3` |

> `max-num-seqs` 是**每个 vLLM 实例**的调度上限，不等于整机入口并发上限。两个 TP1 实例理论合计为 32，但本次 SLA 导向下入口先限制为 16。

## 2. 测试目标

初始目标：

- TTFT P50 ≤ 8s
- TTFT P95 ≤ 30s
- 在满足延迟目标的前提下，提高整机有效吞吐，探索商业化部署的主要影响因素

商业化评估不能只看峰值 tokens/s，应同时看：

1. **TTFT**：排队、tokenize、prefix cache、prefill 和首包网络耗时。
2. **TPOT/ITL**：decode 阶段单 token 延迟，决定长输出体验。
3. **Output token throughput**：整机生成吞吐。
4. **Goodput**：单位时间内满足 SLA 的请求或 token 数量。
5. **成本**：单位有效 token 的 ECS 小时成本，而不是单位原始 token 的理论最低成本。

## 3. 测试条件

### 3.1 硬件与系统

| 项目 | 实测配置 |
|---|---|
| ECS 规格 | `ecs.gn9gc-2x.16xlarge` |
| CPU / 内存 | 64 vCPU / 约 371GiB 可用内存 |
| GPU | 2×NVIDIA RTX PRO 5000 72GB Blackwell |
| Compute Capability | sm120，即 `(12, 0)` |
| 单卡显存 | 73415MiB |
| 单卡功耗上限 | 350W |
| GPU 互联 | PHB，经 PCIe Host Bridge；未见 NVLink |
| MIG | 关闭 |
| 操作系统 | Alibaba Cloud Linux 3.2104 U13 |
| 数据盘 | `/data`，测试开始时约 438GiB 可用 |

> ECS 初始描述中的“L20N”以实例内 `torch`/`nvidia-smi` 实测为准：本机实际识别为 RTX PRO 5000 72GB Blackwell。

### 3.2 软件栈

| 组件 | 版本 |
|---|---|
| Python | 3.12.16 |
| PyTorch | 2.13.0+cu130 |
| vLLM | 0.32.0 |
| Transformers | 5.19.0 |
| NVIDIA Driver | 580.126.09 |
| Nginx | 1.24.0 |

### 3.3 模型与精度

- 模型目录：`/data/Qwen3.8-27B-FP8`
- 权重占用：约 28.75GiB；vLLM 日志中的模型加载显存约 28.42GiB
- KV Cache：FP8
- vLLM 自动选择 `CutlassFp8BlockScaledMMKernel`
- Blackwell 上自动禁用该架构不适用的 DeepGemm 路径，回退 CUTLASS
- 本次未使用 NVFP4 权重，避免在首轮部署中同时引入新的精度变量

## 4. 压测方法与数据有效性

### 4.1 基本口径

| 项目 | 口径 |
|---|---|
| 客户端位置 | ECS 本机回环地址，排除公网网络波动 |
| 压测工具 | `vllm bench serve` |
| API | OpenAI Chat Completions，流式 |
| 主要负载 | 输入 8192 tokens，输出 128 tokens |
| 请求到达 | 默认 `request-rate=inf`，通过 `max-concurrency` 做闭环并发控制 |
| TTFT | 请求发出至首个流式 token 到达 |
| 结果统计 | TTFT/TPOT/E2EL 的 P50/P95/P99、请求吞吐、输出 token 吞吐 |
| 预热 | 每轮正式测试前 2～8 个 warm-up 请求 |

新一轮矩阵压测统一增加以下指标：

- 输入 TPM = `total_input_tokens / (duration_seconds / 60)`
- 输出 TPM = `total_output_tokens / (duration_seconds / 60)`
- 总 TPM = 输入 TPM + 输出 TPM；**所有成功完成的请求均计入，即使 TTFT 超过 SLA**
- 有效 TPM：仅作为额外辅助指标，统计 TTFT≤8s 的请求对应的输入/输出 token；同时保留 P50/P95 聚合 SLA 判定
- Prefix Cache 命中率 = 两台实例的 `prefix_cache_hits_total` 增量之和 / `prefix_cache_queries_total` 增量之和
- 每轮同步记录 preemption、KV 使用率，以及 GPU 利用率、显存、功耗、温度和时钟采样

### 4.2 Prefix Cache 污染处理

早期多轮测试均使用 `vllm bench serve` 默认 `seed=0`，同一服务会重复利用相同随机 Prompt；在 Prefix Cache 开启时，后续测试可能命中前面测试的缓存，不能用于冷请求拓扑对比。

后续有效测试采用：

- 每轮使用不同 `--seed`
- 将“随机冷请求”和“共享前缀缓存命中”分开评估
- 不采用早期重复 seed 产生的异常低 TTFT 作为结论

### 4.3 当前限制

- 主要结果集中在 8K 输入、128/512 输出，不代表 32K/128K 输入或 2K+ 输出的表现。
- 闭环并发压测不等于真实 Poisson 到达流量，商业化前需补充开放环路 QPS 压测。
- 多数实验为 80～200 请求；最终候选点应至少 500 请求并独立重复 3 轮。
- 已完成首轮 MTP 关闭/MTP=3、KV Cache dtype 和 Prefix Cache A/B；尚未完成 32K 长上下文、CUDA Graph capture sizes 和业务质量回归。
- 本轮服务以临时进程运行，未配置 systemd 自动恢复，也未开放公网。

## 5. 部署方案

### 5.1 拓扑对比

```text
方案 A：双 TP1（高并发候选）
                         ┌─ GPU0: vLLM TP1 :8000
Client → Nginx least_conn ┤
                         └─ GPU1: vLLM TP1 :8001

方案 B：单 TP2（单流/低并发候选）
Client → vLLM :8000 → GPU0 + GPU1，层内 TP 通信
```

### 5.2 最终保留方案：双 TP1

两个实例使用相同模型和参数，仅修改 `CUDA_VISIBLE_DEVICES` 与端口：

```bash
CUDA_VISIBLE_DEVICES=0 vllm serve /data/Qwen3.8-27B-FP8 \
  --served-model-name Qwen3.8-27B-FP8 \
  --host 127.0.0.1 --port 8000 \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --max-num-batched-tokens 16384 \
  --max-num-seqs 16 \
  --gpu-memory-utilization 0.90 \
  --kv-cache-dtype fp8 \
  --reasoning-parser qwen3 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}' \
  -O2
```

第二实例设置 `CUDA_VISIBLE_DEVICES=1`、`--port 8001`。Nginx 仅监听 `127.0.0.1:8080`，使用 `least_conn` 并关闭流式代理缓冲。

仓库中的配置：[qwen38-vllm-nginx.conf](../../../../vibeCodingProject/llm_api_perf_benchmark/qwen38-vllm-nginx.conf)。

## 6. 有效实测结果

### 6.1 拓扑与并发

以下均为 8K 输入、128 输出；每轮使用独立 seed 或首次冷服务测试。

| 拓扑 | 整机并发 | 样本 | TTFT P50 | TTFT P95 | 输出吞吐 | 判断 |
|---|---:|---:|---:|---:|---:|---|
| TP2，bt=32768 | 1 | 20 | **0.96s** | 0.97s | 44.96 tok/s | 单流最优 |
| TP2，bt=32768 | 8 | 80 | 7.84s | 7.96s | 100.63 tok/s | 接近 P50 上限 |
| TP2，bt=32768 | 16 | 80 | 12.03s | 14.91s | 112.87 tok/s | P50 超标 |
| 双 TP1，bt=16384 | 16 | 80 | 6.91s | 13.79s | 131.02 tok/s | 达标 |
| 双 TP1，bt=16384 | 20 | 120 | 8.82s | 19.47s | 123.36 tok/s | P50 超标 |
| 双 TP1，bt=16384 | 24 | 120 | 9.01s | 21.50s | 133.89 tok/s | P50 超标 |

> `bt` 指每个实例的 `max-num-batched-tokens`。不同行使用不同随机 seed，适合观察趋势，不应把小幅差异当成精确百分比收益。

### 6.2 Prefill batch 单变量对比

拓扑固定为双 TP1，8K 输入、128 输出、整机并发 16：

| `max-num-batched-tokens` | 样本 | TTFT P50 | TTFT P95 | 输出吞吐 | 结论 |
|---:|---:|---:|---:|---:|---|
| 8192 | 80 | 12.45s | 20.51s | 84.49 tok/s | 过小的调度预算降低效率 |
| **16384** | 80 | **6.91s** | **13.79s** | **131.02 tok/s** | 当前最佳 |
| 32768 | 80 | 13.26s | 18.06s | 117.02 tok/s | 大批量 prefill 加重阻塞 |

### 6.3 最终配置重复性检查

双 TP1、bt=16384、8K 输入、128 输出、整机并发 16：

| 轮次 | 样本 | TTFT P50 | TTFT P95 | TTFT P99 | 输出吞吐 |
|---|---:|---:|---:|---:|---:|
| seed=516 | 200 | 14.65s | 21.16s | 21.19s | 82.78 tok/s |
| seed=616 | 80 | 5.93s | 11.52s | 12.05s | 138.17 tok/s |
| seed=716 | 200 | 6.89s | 16.62s | 18.73s | 120.07 tok/s |

最终一轮健康检查结果：两个 vLLM 实例和 Nginx 均正常，失败请求为 0，日志未发现 preemption、OOM 或 Traceback。

**解读**：目标在最佳复测中满足，但不同轮次存在明显波动。商业化报告应同时披露最优值、波动范围和重复性，不能只保留最好的一轮。

### 6.4 并发扫描：TPM、有效 TPM 与边际递减

配置：双 TP1、MTP 关闭、FP8 KV、bt=16384，8K 输入、128 输出，每档 80 个随机冷请求。

| 并发 | TTFT P50 | TTFT P95 | TPOT P50 | 总 TPM | TTFT≤8s 有效总 TPM | 缓存命中率 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.34s | 1.35s | 25.82ms | 108,719 | 108,719 | 0% |
| 4 | 5.23s | 5.26s | 28.60ms | 226,553 | 226,553 | 0% |
| 8 | 10.02s | 10.55s | 33.23ms | 282,498 | 105,937 | 0% |
| 12 | 6.17s | 7.90s | 40.56ms | 512,621 | **512,621** | 0% |
| 16 | 6.51s | 10.68s | 61.94ms | 558,127 | **418,593** | 0% |
| 20 | 7.46s | 14.28s | 74.21ms | **580,264** | 340,906 | 0% |
| 24 | 8.12s | 16.17s | 85.81ms | 580,657 | 261,294 | 0% |
| 32 | 9.75s | 21.45s | 121.57ms | 610,045 | 213,515 | 0% |
| 48 | 19.83s | 37.33s | 135.77ms | **611,115** | 45,833 | 0% |
| 64 | 30.34s | 47.15s | 135.77ms | 599,058 | 44,929 | 0% |

三种“最佳”必须分开：

- **原始最大 TPM**：并发 48 为 611,115，但与并发 32 的 610,045 几乎相同，延迟已经明显恶化。
- **聚合 SLA 内最大 TPM**：并发 20 为 580,264，P50/P95 均达标；并发 24 的 P50 超过 8s。
- **单请求 TTFT≤8s 的有效 TPM**：并发 12 最高，为 512,621；生产若重视单请求体验和余量，12 比 20 更稳健。

并发 8 的 GPU 平均利用率约 47%，并发 12～48 约 89%～91%。这解释了为什么从 8 到 12 会出现明显的吞吐跃升，而 32 以后原始 TPM 基本进入平台期。

### 6.5 Prefix Cache A/B

配置：双 TP1、MTP 关闭、FP8 KV，约 4.2K 输入、128 输出。共享前缀组使用 8 个 4096-token 前缀和 128-token 后缀。

| 场景 | 并发 | TTFT P50 | TTFT P95 | 总 TPM | 有效总 TPM | 缓存命中率 |
|---|---:|---:|---:|---:|---:|---:|
| 随机冷请求 | 12 | 3.84s | 3.87s | 411,975 | 411,975 | 0% |
| 8 个共享前缀 | 12 | **0.49s** | 3.29s | **597,042** | 597,042 | **58.66%** |
| 8 个共享前缀 | 20 | **0.97s** | 4.28s | **822,449** | 822,449 | **58.67%** |

同并发 12 下，共享前缀使总 TPM 提高约 **44.9%**，TTFT P50 降低约 **87.3%**。共享前缀、并发 20 的 822,449 也是本轮所有实验中的最高观测总 TPM，但它代表**前缀复用负载**，不能与随机冷请求的最大 TPM 直接混用。

当前 Nginx 使用 `least_conn`，不保证相同前缀始终路由到同一实例。商业化可继续测试 cache-affinity/sticky routing，但需要同时评估负载不均和单实例热点。

### 6.6 MTP 关闭与 MTP=3 A/B

配置：双 TP1、FP8 KV、bt=16384，8K 输入、512 输出；同一并发使用相同 seed。并发 1 每组 20 请求，并发 8/16 每组 40 请求。

| 并发 | MTP | TTFT P50 | TTFT P95 | TPOT P50 | 总 TPM | MTP 接受率 | 聚合 SLA |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 关闭 | 1.34s | 1.35s | 25.84ms | 36,126 | - | 通过 |
| 1 | **3** | 1.35s | 1.36s | **13.31ms** | **62,042** | 52.69% | 通过 |
| 8 | 关闭 | 5.28s | 5.33s | 28.55ms | 211,386 | - | 通过 |
| 8 | **3** | **4.58s** | 10.46s | 19.93ms | **255,643** | 47.40% | 通过 |
| 16 | 关闭 | 6.98s | 10.75s | 34.75ms | 295,750 | - | 通过 |
| 16 | **3** | **2.73s** | 16.60s | 26.25ms | **394,576** | 52.35% | 通过 |
| 20 | 3 | 10.01s | 22.74s | 28.92ms | 342,863 | 47.23% | P50 超标 |
| 24 | 3 | 7.06s | 35.01s | 33.12ms | 374,437 | 46.00% | P95 超标 |
| 32 | 3 | 14.49s | 22.56s | 35.57ms | **466,289** | 50.00% | P50 超标 |

结论：

- MTP=3 相对 MTP 关闭，在并发 1/8/16 的总 TPM 分别提高约 **71.7%/20.9%/33.4%**。
- 后续统一以 MTP=3 为默认，不再把 MTP=2 作为调优变量；历史原始数据仅用于归档。
- 接受率不是唯一目标，还需同时观察 TTFT、TPOT、总吞吐和有效 TPM。
- MTP=3 的最佳 SLA 点仍为并发 16；并发 32 的 466,289 是原始 TPM，不满足 P50 目标。
- 本轮为初步 A/B，生产启用前仍需更大样本、真实输出长度分布和业务质量回归。

### 6.7 KV Cache dtype A/B

配置：双 TP1、MTP 关闭、8K 输入、512 输出，FP8 KV vs BF16 KV。

| 并发 | KV dtype | TTFT P50 | TTFT P95 | 总 TPM | 每实例 KV tokens | 32K 估算最大并发 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | FP8 | 1.34s | 1.35s | 36,126 | 815,559 | 24.89 |
| 1 | BF16 | 1.32s | 1.33s | 35,594 | 464,896 | 14.19 |
| 16 | **FP8** | **6.98s** | **10.75s** | **295,750** | **815,559** | **24.89** |
| 16 | BF16 | 12.52s | 19.87s | 218,120 | 464,896 | 14.19 |

单流吞吐差异约 1.5%，但并发 16 时 FP8 KV 总 TPM 比 BF16 高约 **35.6%**。每实例 KV token 容量比约 **1.75 倍**，并非理想化的完整 2 倍，原因是混合注意力状态、块对齐和其他显存开销也参与分配。

## 7. 商业化调优 Top5 影响因素

### Top 1：并发与准入控制——`max-num-seqs`、网关并发、到达 QPS

**影响程度：最高，且直接决定尾延迟。**

并发增加通常先提高 GPU 利用率和吞吐，随后进入边际递减：新增并发带来的吞吐收益变小，但排队、prefill 阻塞和 decode 干扰继续增加，TTFT/TPOT 快速恶化。

本次 8K/128 扫描已出现完整拐点：总 TPM 从并发 20 的 580,264 到并发 24 的 580,657 几乎零增长，到并发 48 也仅为 611,115；但 P50 从 7.46s 升至 8.12s、19.83s。与此同时，单请求 TTFT≤8s 的有效 TPM 在并发 12 已达到最高值 512,621，之后持续下降。

商业部署需要同时控制两层：

- vLLM 实例层：`max-num-seqs`
- 网关层：整机最大 in-flight 请求数、到达 QPS、排队和拒绝策略

只调整 `max-num-seqs` 而不限制入口，会把队列从引擎内部转移到网关，不能真正消除尾延迟。

### Top 2：拓扑——TP2 还是多个 TP1 副本

**影响程度：最高，决定单流与并发两条性能曲线。**

- TP2：两张卡共同完成一次计算，单流 prefill/decode 更快，但承担 NCCL/PCIe 通信。
- 双 TP1：每张卡独立服务，避免层内通信，增加调度与负载均衡自由度，通常更适合多请求并发。
- 本机实测：TP2 单流最好，双 TP1 高并发 SLA 更好。

**纠正“27B 必须 TP2”**：本模型 FP8 权重约 29GiB，单卡 72GB 足以运行；TP2 是性能选择，不是显存可行性要求。

### Top 3：Prefill 调度——`max-num-batched-tokens` 与 Chunked Prefill

**影响程度：高，尤其是长输入和混合 prefill/decode 负载。**

- 较小 budget：单次 prefill 更细，可能改善部分 ITL，但调度开销和分块次数增加。
- 较大 budget：提高单批 prefill 能力，但可能让一批长 prompt 阻塞其他请求。
- 本机 8K 输入下，16384 明显优于 8192/32768，说明最佳点必须与输入长度联合测试。

商业化不能脱离输入长度分布设置该参数；2K、8K、32K 负载可能对应不同最佳值。

### Top 4：KV Cache 与显存策略——dtype、容量、Prefix Cache

**影响程度：条件性高；长上下文、高并发、前缀复用场景下可升至 Top 1～2。**

FP8 KV Cache 相对 BF16 可减少 KV 存储和读取带宽，为更多并发或更长上下文释放空间。本次 A/B 已验证：单流差异仅约 1.5%，但并发 16 时 FP8 KV 总 TPM 高 35.6%，每实例 KV token 容量约为 BF16 的 1.75 倍。

需要区分两个机制：

- **KV dtype**：影响每请求 KV 成本、显存带宽、可承载并发和可能的精度。
- **Prefix Cache**：影响共享前缀请求的重复 prefill；本次共享前缀 A/B 在并发 12 下使总 TPM 提高 44.9%，TTFT P50 降低 87.3%。

后续仍需补充更长上下文、业务质量回归，以及 cache-affinity 与 `least_conn` 的路由策略对比。

### Top 5：Decode 加速——MTP 与 `num_speculative_tokens`

**影响程度：对 TPOT/长输出成本可能很高，对 TTFT 不是直接优化项。**

MTP 通过一次主模型验证接受多个 draft token，潜在收益取决于接受率、speculative tokens、输出长度、并发，以及额外计算和显存开销。

本次 8K/512 A/B 结果：

- 并发 1：MTP=3 总 TPM 比关闭高 71.7%。
- 并发 8：MTP=3 总 TPM 比关闭高 20.9%，本轮 TTFT 也更好。
- 并发 16：MTP=3 总 TPM 比关闭高 33.4%，本轮 P50 也更低。
- 本轮接受率约 46%～64%，接受率需与 TTFT、TPOT 和 Goodput 联合判断。

因此当前选择 MTP=3，但不能外推为所有负载的固定答案。高并发下仍可能出现额外计算、调度波动和尾延迟，必须结合 Goodput 判断。

每轮同时读取：

- `vllm:spec_decode_num_accepted_tokens_total`
- `vllm:spec_decode_num_draft_tokens_total`
- 接受率 = accepted / draft

## 8. CUDA Graph 为什么暂不列入 Top5

CUDA Graph 是重要基线优化，本次保持 `-O2`，启动日志显示 `FULL_AND_PIECEWISE`，默认 capture sizes 为 `[1, 2, 4, 8, 16, 24, 32]`。

但 capture sizes 主要影响：

- 是否覆盖实际运行 batch，减少 graph 外执行
- 启动时的 capture 时间和显存
- 不必要的大 batch graph 带来的额外成本

在当前每实例 `max-num-seqs=16` 的配置下，24/32 对稳态运行可能不是必需项；精简 capture sizes 更可能首先改善启动和显存，而不是自动带来数量级吞吐提升。应在并发、拓扑和 prefill 调度确定后，再做单变量验证。

## 9. 下一轮实验矩阵

### Phase A：确定并发膝点

固定双 TP1、bt=16384、FP8 KV，分别测：

- 输入：2K / 8K / 32K
- 输出：512，另补 2048 检验长输出
- 整机并发：1 / 2 / 4 / 8 / 12 / 16 / 20 / 24 / 32 / 48 / 64
- 每轮至少 200 请求；候选点 500 请求 × 3 个独立 seed
- 同步采集 TTFT、TPOT、E2EL、输出吞吐、waiting/running、KV 使用率、preemption、GPU 利用率

同时增加固定 QPS 的 Poisson 到达测试，避免只测闭环并发。

### Phase B：MTP A/B（已完成首轮，待扩大样本）

已完成 MTP 关闭与 MTP=3 的 8K/512 初步对比，后续统一以 3 为默认，在真实负载上重复：

| 组别 | MTP | `num_speculative_tokens` |
|---|---|---:|
| A0 | 关闭 | - |
| A1 | 开启 | 3 |

每组至少覆盖并发 1、8、16，输出长度 512/2048。只有接受率、TPOT 和 Goodput 同时改善时才启用。

```bash
--speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

### Phase C：KV Cache 与 Prefix Cache（已完成首轮，待长上下文与质量回归）

- KV dtype：FP8 vs BF16
- 输入：8K vs 32K
- 并发：16 vs 更高容量点
- 记录：可承载并发、KV 使用率、preemption、吞吐、业务精度回归
- Prefix Cache：随机冷请求 vs 共享长前缀请求，分别报告命中率和 TTFT

### Phase D：CUDA Graph capture sizes

在前三项确定后，对比默认列表与实际 batch 对齐的列表，观察稳态性能、启动时间和显存，不优先做全排列实验。

## 10. 如何判断“最佳并发”与边际递减

不要预设 64 或 128 是最佳点，应按负载实测：

1. 并发逐级增加，绘制 output tok/s、TTFT P50/P95、TPOT P50/P95 三条曲线。
2. 当吞吐连续两个档位增长明显放缓，或 TTFT/TPOT 开始快速上升时，标记为候选膝点。
3. 以 SLA 过滤无效吞吐：

\[
Goodput_{SLA}=\frac{\text{满足单请求延迟门槛的请求数}}{\text{测试时长}}
\]

4. 选择 Goodput 最大且 P50/P95 均有余量的点，而非原始吞吐最大的点。
5. 生产入口保留余量，并通过准入控制防止请求无限排队。

成本评估可统一为：

\[
Cost_{\text{有效百万token}}=
\frac{\text{ECS 小时价格}}{\text{有效 token/s}\times 3600 / 10^6}
\]

这里的“有效 token”必须来自满足延迟和质量门槛的请求。

## 11. 常见误区

| 误区 | 事实 |
|---|---|
| 27B 模型必须 TP2 | 本机 FP8 权重约 29GiB，72GB 单卡 TP1 可运行；TP2 是性能选择 |
| `max-num-seqs` 越大，吞吐越高 | 超过膝点后，吞吐增长放缓，TTFT/TPOT 和排队显著恶化 |
| `max-num-seqs=16` 就是整机并发 16 | 它是每实例限制；双 TP1 理论合计 32，入口还需独立限流 |
| prefill batch 越大越好 | 本机 16384 优于 8192/32768，最佳值随输入长度和并发变化 |
| FP8 KV 会让吞吐翻倍 | 它降低 KV 容量和带宽成本，但只有 KV 成为瓶颈时才可能显著转化为吞吐 |
| MTP 主要降低 TTFT | MTP 主要优化 decode/TPOT；TTFT 主要受排队和 prefill 影响 |
| MTP=3 是所有负载下的固定最优 | 当前统一默认 3，但仍需按真实负载验证 TTFT、TPOT 和 Goodput |
| CUDA Graph capture sizes 越全越好 | 多余尺寸增加启动和显存成本，需与实际 batch 对齐 |
| 吞吐压测必须开启 `--enforce-eager` | 该参数会关闭 CUDA Graph，通常降低稳态 decode 性能；主要用于排障、快速启动或解决 capture OOM，吞吐测试默认保持 `-O2` |
| 固定 seed 的多轮压测可直接横向比较 | Prefix Cache 开启时会复用旧 prompt，应使用不同 seed 或明确测缓存命中场景 |
| 峰值吞吐最高就是商业化最佳 | 应选择 SLA 约束下 Goodput 和单位有效 token 成本最佳 |

## 12. 测试产物

仓库内汇总与复用脚本：

- [单实例 TP2 专项实测文档](TP2_README.md)：仅包含 `--tensor-parallel-size 2` 的并发、缓存、MTP 与 KV dtype 数据
- [FP8 vs NVFP4 同参数对比](TP2_NVFP4_README.md)：单 TP2 + FP8 KV + MTP=3 的核心指标对比
- [原生 Sweep 与取舍分析](NATIVE_SWEEP_README.md)：自动并发扫描、四类曲线与三档运行点推荐
- [部署与压测日志目录](logs/README.md)：启动日志、变体参数、压测摘要与 Nginx 配置
- [并发扫描汇总 CSV](results/concurrency-8k-o128-summary.csv)
- [Prefix Cache A/B 汇总 CSV](results/cache-ab-summary.csv)
- [MTP 与 KV dtype A/B 汇总 CSV](results/mtp-kv-ab-summary.csv)
- [矩阵压测脚本](../../../../vibeCodingProject/llm_api_perf_benchmark/qwen38_vllm_matrix.py)：自动采集 TTFT/TPOT、输入/输出/总 TPM、TTFT≤8s 有效 TPM、缓存命中率、MTP 接受率、preemption 和 GPU 采样
- [TP2 部署脚本](scripts/deploy_qwen38_tp2.sh)：默认 NVFP4 + FP8 KV + MTP=3，支持启动、停止、重启、状态和日志查看

ECS 上的主要文件：

```text
/data/vllm-fp8-tp1-gpu0.log
/data/vllm-fp8-tp1-gpu1.log
/data/vllm-fp8-tp2.log
/data/benchmark-results/
/data/vllm-nginx.conf
```

主要最终结果文件：

```text
fp8-final-2tp1-bt16384-8k-c16-s516.json
fp8-final-2tp1-bt16384-8k-c16-s616.json
fp8-final-2tp1-bt16384-8k-c16-s716.json
```

## 参考资料

- [官方 Recipe] Qwen3.8-27B — https://recipes.vllm.ai/Qwen/Qwen3.8-27B
- [官方文档] vLLM Optimization and Tuning — https://docs.vllm.ai/en/latest/configuration/optimization/
- [官方文档] vLLM Bench Serve — https://docs.vllm.ai/en/latest/cli/bench/serve/
- [官方模型] Qwen3.8-27B-FP8 — https://huggingface.co/Qwen/Qwen3.8-27B-FP8

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-28 | 新建双卡 FP8 部署实测报告：测试条件、双 TP1/TP2 对比、prefill 调优、重复性波动、商业化 Top5 与后续实验矩阵 |
| 2026-10-28 | 完成并发 1～64、TPM/有效 TPM、Prefix Cache、MTP 关闭/MTP=3、KV dtype 首轮矩阵；当前推荐双 TP1 + FP8 KV + MTP=3 |
