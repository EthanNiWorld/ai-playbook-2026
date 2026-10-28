# Qwen3.8-27B 单实例 TP2 部署与性能实测

> 最后更新: 2026-10-28  
> 领域: AI Infra / LLM Inference / vLLM  
> 状态: Reviewed（仅单实例 TP2 场景）

<!-- SUMMARY_START -->
**一句话说明**: 在双 RTX PRO 5000 72GB Blackwell 上，以单个 `--tensor-parallel-size 2` vLLM 实例部署 Qwen3.8-27B-FP8，独立测量并发、TPM、Prefix Cache、MTP 和 KV dtype，并完成 NVFP4 原生 kernel 启动与容量验证。  
**核心价值**: 为明确选择 TP2 的场景提供不掺杂其他拓扑数据的调优基线，区分原始最大 TPM、聚合 SLA 内 TPM 和单请求有效 TPM。  
**相关产品**: [vLLM](../vllm.md), [推测解码](../../speculative-decoding.md), [Qwen](../../../../alibaba-ai-hub/maas/qwen.md)
<!-- SUMMARY_END -->

## 1. 范围与结论

本文所有结果均来自**一个 TP2 vLLM 实例**，两张 GPU 通过 `--tensor-parallel-size 2` 共同服务同一模型。不包含双 TP1 或其他副本拓扑的数据。

### 当前推荐运行点

| 项目 | 推荐值 |
|---|---|
| 模型 | Qwen3.8-27B-FP8 |
| 实例数 | 1 |
| `tensor-parallel-size` | 2 |
| `max-num-seqs` | 32 |
| `max-num-batched-tokens` | 32768 |
| `max-model-len` | 32768 |
| KV Cache | FP8 |
| MTP | 开启，`num_speculative_tokens=3` |
| CUDA Graph | 开启，`-O2` |
| `--enforce-eager` | 不开启 |

### 核心结论

- **随机冷请求、MTP 关闭、8K/128**：聚合 SLA 内最佳为并发 8，总 TPM **388,224**；原始 TPM 在并发 32～48 进入约 **45.5 万**的平台期，但延迟已超标。
- **随机冷请求、MTP=3、8K/512**：聚合 SLA 内最高测试点为并发 20，总 TPM **374,926**；原始最高测试点为并发 32，总 TPM **382,511**，但 P50/P95 均失败。
- **单请求 TTFT≤8s 有效 TPM**：MTP 关闭、8K/128 时并发 8 最高，为 **373,665**；MTP=3、8K/512 时并发 8 最高，为 **254,691**。
- **Prefix Cache**：共享前缀、并发 16 时命中率 **66.00%**，总 TPM **869,219**，TTFT P50 **0.92s**；该结果代表前缀复用负载，不能与随机冷请求混用。
- **MTP 默认固定为 3**：相对关闭 MTP，并发 1/8/16 的总 TPM 分别提高约 **59.2%/27.7%/16.5%**；后续不再把 MTP=2 作为调优变量。
- **KV dtype**：FP8 在本轮 TP2 测试中只带来约 3%～4% 的吞吐优势，但 KV token 容量从 **1,312,085** 提升至 **2,313,178**，约 **1.76 倍**，对长上下文容量更重要。
- **NVFP4 启动与容量验证**：已确认原生 `FlashInferCutlassNvFp4LinearKernel`；每卡模型加载显存由 FP8 的 **14.98GiB** 降至 **12.82GiB**，相同 MTP=3、FP8 KV 等配置下，TP2 KV 逻辑容量由 **1,553,749** 提至 **1,612,913 tokens**（+3.81%）。当前只证明启动路径与容量收益，不代表吞吐、质量或能效已通过验收。

## 2. 测试条件

### 2.1 硬件与软件

| 项目 | 配置 |
|---|---|
| ECS | `ecs.gn9gc-2x.16xlarge`，64 vCPU / 约 371GiB 内存 |
| GPU | 2×NVIDIA RTX PRO 5000 72GB Blackwell，sm120 |
| GPU 互联 | PHB，经 PCIe Host Bridge；未见 NVLink |
| Python / PyTorch | 3.12.16 / 2.13.0+cu130 |
| vLLM / Transformers | 0.32.0 / 5.19.0 |
| Driver | 580.126.09 |
| 模型 | `/data/Qwen3.8-27B-FP8` |
| 服务入口 | `http://127.0.0.1:8000`，单实例，无 Nginx 副本分发 |

### 2.2 压测口径

- 客户端位于 ECS 本机，使用 OpenAI Chat Completions 流式接口。
- 并发扫描采用闭环 `max-concurrency`，随机 Prompt 使用不同 seed，避免 Prefix Cache 污染。
- 每轮记录 TTFT、TPOT、E2EL、输入/输出/总 TPM、TTFT≤8s 有效 TPM、缓存命中率、MTP 接受率、preemption 和 GPU 采样。
- 输入/输出 TPM 按每轮实际 token 数除以实际耗时计算。
- 缓存命中率按 TP2 实例的 `prefix_cache_hits_total / prefix_cache_queries_total` 增量计算。
- **总 TPM 统计所有成功完成的请求，不因 TTFT 超过 SLA 而剔除**；有效 TPM 仅作为额外的辅助指标，统计单请求 TTFT≤8s 的 token。聚合 SLA 单独判断 P50≤8s、P95≤30s。
- 全程保持 CUDA Graph `-O2`，未使用 `--enforce-eager`。

### 2.3 当前限制

- 主要覆盖 8K 输入、128/512 输出，未完成 32K 长上下文和业务质量回归。
- MTP 与 KV A/B 每组为 20～40 请求，属于首轮工程筛选，需要更大样本复测。
- `max-num-batched-tokens=32768` 是本文统一基线，不代表已完成 TP2 下该参数的全局最优搜索。
- NVFP4 目前仅完成原生 kernel 启动、权重显存和 KV 容量对照；尚未完成同负载吞吐、业务质量与稳态平均功耗 A/B。
- 服务为临时进程，未配置 systemd 自动恢复，也未开放公网。

## 3. 单 TP2 部署方案

```bash
CUDA_VISIBLE_DEVICES=0,1 vllm serve /data/Qwen3.8-27B-FP8 \
  --served-model-name Qwen3.8-27B-FP8 \
  --host 127.0.0.1 --port 8000 \
  --tensor-parallel-size 2 \
  --max-model-len 32768 \
  --max-num-batched-tokens 32768 \
  --max-num-seqs 32 \
  --gpu-memory-utilization 0.90 \
  --kv-cache-dtype fp8 \
  --reasoning-parser qwen3 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}' \
  -O2
```

### 3.1 NVFP4 启动验证与 TP2 KV 容量

对照组保持 TP2、`max-model-len=32768`、FP8 KV、MTP=3 和 batch 参数一致，仅改变权重精度。NVFP4 已确认使用原生 `FlashInferCutlassNvFp4LinearKernel`。

| 指标 | FP8 权重 + FP8 KV | NVFP4 权重 + FP8 KV | 变化 |
|---|---:|---:|---:|
| 每卡模型加载显存 | 14.98GiB | 12.82GiB | **节约 2.16GiB/卡** |
| TP2 KV 逻辑容量 | 1,553,749 tokens | 1,612,913 tokens | **+59,164（+3.81%）** |
| 全部按 32K 估算的逻辑请求容量 | 47.42 | 49.22 | 整数槽位约 47 → 49 |

> 本表的 FP8 KV 容量来自 MTP=3 对照配置，不能与第 7 节 MTP 关闭时的 2,313,178 tokens 直接比较。

**TP2 KV 容量的含义**：vLLM 在权重、MTP、CUDA Graph 和其他运行时对象分配完成后，利用剩余显存为 KV Cache 预留的逻辑 token 槽位总数。它不是当前已使用量，也不是每请求容量；两张卡虽然分片存储 KV，但该数值已经表示 TP2 实例的逻辑容量，不应再乘以 2。

全部请求达到 32K 时，可用下式做容量记账：

\[
C_{32K}=\min\left(\text{max-num-seqs},\left\lfloor\frac{\text{KV tokens}}{32768}\right\rfloor\right)
\]

当前 `max-num-seqs=32` 时，两种权重精度都先受调度上限约束，满 32K 请求并发上限均为 32；NVFP4 的收益是更多 KV 余量，而不是立即把并发从 32 提高到 49。若 `max-num-seqs=16`，满 32K 时逻辑占用为 524,288 tokens，约占 NVFP4 KV 容量的 32.5%。

需要避免三种误读：

1. `max-num-batched-tokens` 是单次调度迭代的 token 预算，不是总 KV 容量上限。
2. 预留但未使用的 KV 槽位不会被 Attention 扫描，不会仅因池子更大就拖慢 decode；TPOT 取决于真实上下文长度、活跃请求、KV 读取与调度。
3. “KV 使用率保持 60%～80%”不是通用最优规则。应结合 preemption、waiting、TTFT/TPOT、Goodput 和 Prefix Cache 价值判断，不能仅按使用率降载。

**功耗口径**：初步观察到 NVFP4 峰值功耗较 FP8 低约 10%～15%，但峰值功耗不等于平均能耗。是否省电必须在相同负载和 SLA 下比较稳态平均功耗与吞吐，使用 `每 token 能耗 ∝ 平均功耗 / token/s` 判定；在完成该 A/B 前不宣称节能 10%～15%。

## 4. 并发与 TPM 扫描

配置：单 TP2、MTP 关闭、FP8 KV、bt=32768，8K 输入、128 输出，每档 80 个随机冷请求。

| 并发 | TTFT P50 | TTFT P95 | TPOT P50 | 总 TPM | TTFT≤8s 有效总 TPM | 聚合 SLA |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 0.97s | 0.98s | 15.61ms | 170,142 | 170,142 | 通过 |
| 4 | 4.01s | 4.01s | 17.63ms | 321,620 | 321,620 | 通过 |
| 8 | 7.88s | 8.00s | 19.34ms | **388,224** | **373,665** | 通过 |
| 12 | 11.09s | 11.82s | 25.62ms | 416,353 | 72,862 | P50 超标 |
| 16 | 13.72s | 15.81s | 37.20ms | 435,637 | 27,227 | P50 超标 |
| 20 | 14.09s | 19.81s | 66.01ms | 444,978 | 38,936 | P50 超标 |
| 24 | 14.45s | 23.83s | 88.73ms | 444,648 | 83,372 | P50 超标 |
| 32 | 16.00s | 31.68s | 130.63ms | 455,162 | 22,758 | P50/P95 超标 |
| 48 | 27.44s | 50.63s | 178.45ms | **455,682** | 5,696 | P50/P95 超标 |
| 64 | 42.72s | 66.82s | 178.41ms | 455,408 | 5,692 | P50/P95 超标 |

### 边际递减判断

- 并发 32、48、64 的总 TPM 分别为 455,162、455,682、455,408，已经进入平台期。
- 从并发 32 提至 48，原始 TPM 仅增加约 0.1%，但 P50 从 16.00s 增至 27.44s。
- 聚合 SLA 下应选择并发 8，而不是追求并发 48 的原始最大值。
- 若按单请求 TTFT≤8s 过滤，并发 8 同样是有效 TPM 最佳点。

## 5. Prefix Cache A/B

配置：单 TP2、MTP 关闭、FP8 KV，约 4.2K 输入、128 输出。共享前缀组使用 8 个 4096-token 前缀和 128-token 后缀。

| 场景 | 并发 | TTFT P50 | TTFT P95 | 总 TPM | 有效总 TPM | 缓存命中率 |
|---|---:|---:|---:|---:|---:|---:|
| 随机冷请求 | 8 | 4.00s | 4.02s | 337,244 | 337,244 | 0% |
| 8 个共享前缀 | 8 | **0.42s** | 1.62s | **591,917** | 591,917 | **66.00%** |
| 8 个共享前缀 | 16 | **0.92s** | 4.45s | **869,219** | 869,219 | **66.00%** |

同并发 8 下，共享前缀使总 TPM 提高约 **75.5%**，TTFT P50 降低约 **89.6%**。单 TP2 只有一个引擎和一份本地 Prefix Cache，因此本文不涉及多实例缓存亲和路由。

## 6. MTP 关闭与 MTP=3 A/B

配置：单 TP2、FP8 KV、bt=32768，8K 输入、512 输出；同一并发使用相同 seed。并发 1 每组 20 请求，其他并发每组 40 请求。

| 并发 | MTP | TTFT P50 | TTFT P95 | TPOT P50 | 总 TPM | 有效总 TPM | 接受率 | 聚合 SLA |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 关闭 | 0.97s | 0.97s | 15.21ms | 60,111 | 60,111 | - | 通过 |
| 1 | **3** | 0.98s | 0.99s | **8.95ms** | **95,685** | **95,685** | 50.05% | 通过 |
| 8 | 关闭 | 7.87s | 8.02s | 18.63ms | 241,671 | 169,169 | - | 通过 |
| 8 | **3** | **1.05s** | 8.55s | 21.33ms | **308,718** | **254,691** | 49.06% | 通过 |
| 16 | 关闭 | 12.48s | 16.01s | 21.21ms | 305,139 | 53,400 | - | P50 超标 |
| 16 | 3 | 2.97s | 16.53s | 32.90ms | 355,417 | 222,137 | 47.14% | 通过 |
| 20 | 3 | **2.50s** | **20.57s** | 34.87ms | **374,926** | 196,836 | 46.35% | 通过 |
| 24 | 3 | 8.84s | 24.76s | 42.99ms | 373,670 | 158,813 | 42.84% | P50 超标 |
| 32 | 3 | 16.89s | 33.09s | 40.36ms | **382,511** | 86,066 | 48.58% | P50/P95 超标 |

### MTP 选择

- MTP=3 相对关闭，在并发 1/8/16 的总 TPM 分别提高约 **59.2%/27.7%/16.5%**。
- 并发 1 的收益最高；并发提高后收益收窄，因此仍需按真实并发和输出长度复测。
- 后续统一选择 **MTP=3**，不再把 MTP=2 作为调优变量；历史原始数据仅用于归档。

## 7. KV Cache dtype A/B

配置：单 TP2、MTP 关闭、8K 输入、512 输出。

| 并发 | KV dtype | TTFT P50 | TTFT P95 | 总 TPM | TP2 KV tokens | 32K 估算最大并发 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | FP8 | 0.97s | 0.97s | 60,111 | **2,313,178** | **70.59** |
| 1 | BF16 | 0.95s | 0.96s | 57,942 | 1,312,085 | 40.04 |
| 8 | FP8 | 7.87s | 8.02s | 241,671 | **2,313,178** | **70.59** |
| 8 | BF16 | 7.75s | 7.91s | 233,627 | 1,312,085 | 40.04 |
| 16 | FP8 | 12.48s | 16.01s | 305,139 | **2,313,178** | **70.59** |
| 16 | BF16 | 12.47s | 15.77s | 293,871 | 1,312,085 | 40.04 |

FP8 KV 在三个并发点的吞吐优势约 **3.4%～3.8%**，远小于其对 KV 容量的提升。对于本文 TP2 负载，FP8 的核心价值主要是长上下文容量和避免 KV 成为后续并发瓶颈，而不是立即获得数十个百分点的吞吐。

## 8. TP2 场景下的调优优先级

| 优先级 | 因素 | 本文证据与建议 |
|---|---|---|
| 1 | 并发与准入控制 | MTP 关闭时并发 8 后 P50 超标；原始 TPM 在 32 后进入平台期。必须限制入口，而非只提高 `max-num-seqs` |
| 2 | MTP 与输出长度 | MTP=3 显著提升 decode 和 TPM；2/3 的差异随并发变化，需按真实输出长度复测 |
| 3 | Prefix Cache 命中率 | 共享前缀使同并发总 TPM 提高 75.5%，是 Agent/多轮场景的首要 TTFT 杠杆之一 |
| 4 | Prefill 调度 | 本文统一 bt=32768，尚需继续对比 16384 等档位，不应直接认定为全局最优 |
| 5 | KV dtype 与容量 | FP8 吞吐提升约 3%～4%，但 KV 容量约 1.76 倍；长上下文下优先级上升 |

CUDA Graph 保持 `-O2` 作为基线。`--enforce-eager` 会关闭 CUDA Graph，不是提高吞吐的必要条件。

## 9. 后续实验

1. 对 MTP=3 的并发 8、16、20 做 500 请求 × 3 个 seed 的重复性验证。
2. 在 TP2 下对比 `max-num-batched-tokens=16384/32768`。
3. 增加 32K 输入、2048 输出和 Poisson QPS 到达测试。
4. 对 FP8 KV 与 MTP=3 同时开启的组合做业务质量回归。
5. 在相同负载、并发和 SLA 下对比 FP8/NVFP4 的吞吐、业务质量、稳态平均功耗和每百万 token 能耗。
6. 最后再调整 CUDA Graph capture sizes，避免在前期引入过多变量。

## 10. 测试产物

仓库内文件：

- [NVFP4 vs FP8 同参数对比文档](TP2_NVFP4_README.md)
- [部署与压测日志目录](logs/README.md)：最终启动日志、MTP/KV 变体记录和压测摘要
- [TP2 并发扫描 CSV](results/tp2-concurrency-8k-o128-summary.csv)
- [TP2 Prefix Cache A/B CSV](results/tp2-cache-ab-summary.csv)
- [TP2 MTP 与 KV dtype A/B CSV](results/tp2-mtp-kv-ab-summary.csv)
- [矩阵压测脚本](../../../../vibeCodingProject/llm_api_perf_benchmark/qwen38_vllm_matrix.py)

ECS 原始结果目录：

```text
/data/benchmark-results/tp2-concurrency-8k-o128/
/data/benchmark-results/tp2-cache-ab/
/data/benchmark-results/tp2-mtp-ab/
```

## 参考资料

- [官方 Recipe] Qwen3.8-27B — https://recipes.vllm.ai/Qwen/Qwen3.8-27B
- [官方文档] vLLM Optimization and Tuning — https://docs.vllm.ai/en/latest/configuration/optimization/
- [官方文档] vLLM Bench Serve — https://docs.vllm.ai/en/latest/cli/bench/serve/

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-28 | 新建纯单实例 TP2 实测文档：并发/TPM、有效 TPM、Prefix Cache、MTP 关闭/MTP=3、KV dtype；当前推荐 TP2 + FP8 KV + MTP=3 |
| 2026-10-28 | 新增 NVFP4 原生 kernel 启动验证、权重显存与 TP2 KV 逻辑容量对照；澄清 KV 容量、调度上限和峰值功耗/能效口径 |
