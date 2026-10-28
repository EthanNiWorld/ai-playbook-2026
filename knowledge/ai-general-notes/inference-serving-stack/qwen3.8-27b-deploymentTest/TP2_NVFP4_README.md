# Qwen3.8-27B FP8 vs NVFP4 单实例 TP2 对比实测

> 最后更新: 2026-10-28  
> 领域: AI Infra / LLM Inference / vLLM  
> 状态: Reviewed（仅单实例 TP2、MTP=3 场景）

<!-- SUMMARY_START -->
**一句话说明**: 在相同单实例 TP2、32K 上下文、FP8 KV Cache 和 MTP=3 配置下，对比 Qwen3.8-27B-FP8 与 Inferact/Qwen3.8-27B-NVFP4 的性能。  
**核心价值**: 量化 NVFP4 在 Blackwell sm120 上的真实收益，并明确总 TPM 包含所有成功请求，SLA 只作为独立判定。  
**相关产品**: [TP2 FP8 基线](TP2_README.md), [vLLM](../vllm.md), [推测解码](../../speculative-decoding.md)
<!-- SUMMARY_END -->

## 1. 结论

在本文测试范围内，**NVFP4 全面优于 FP8 的总 TPM，且并发越高，收益总体越明显**：

- 并发 1：总 TPM 提升 **7.6%**
- 并发 8：提升 **10.7%**
- 并发 16：提升 **15.4%**
- 并发 20：提升 **17.0%**
- 并发 24：提升 **18.4%**
- 并发 32：提升 **17.4%**

当前推荐：**单 TP2 + NVFP4 权重 + FP8 KV Cache + MTP=3**。

- **聚合 SLA 内最佳点**：NVFP4、并发 24，总 TPM **442,519**，TTFT P50 **7.08s**、P95 **19.79s**。
- **原始最大总 TPM**：NVFP4、并发 32，总 TPM **449,069**，但 P50 **13.47s**，不满足 P50≤8s。
- NVFP4 每卡模型加载显存从 FP8 的 **14.98GiB** 降至 **12.82GiB**，减少约 **14.4%**。
- TP2 KV token 容量从 **1,553,749** 增至 **1,612,913**，增加约 **3.8%**。
- NVFP4 的 GPU 峰值功耗整体更低，本轮各并发点大致低 **10%～15%**。

> 本文只评估工程性能，不代表 NVFP4 与 FP8 的业务生成质量等价。商业化采用前仍需做准确率、指令遵循和典型任务回归。

## 2. 公平对比条件

两种权重使用完全相同的部署和压测参数：

| 参数 | 统一值 |
|---|---|
| 实例数 | 1 |
| `tensor-parallel-size` | 2 |
| `max-model-len` | 32768 |
| `max-num-batched-tokens` | 32768 |
| `max-num-seqs` | 32 |
| `gpu-memory-utilization` | 0.90 |
| `kv-cache-dtype` | FP8 |
| MTP | 开启，`num_speculative_tokens=3` |
| CUDA Graph | `-O2`，未使用 `--enforce-eager` |
| 输入 / 输出 | 8192 / 512 tokens |
| 请求 seed | 23001、23008、23016、23020、23024、23032 |
| 样本数 | 并发 1 为 20；其他并发为 40 |

模型分别为：

- FP8：`Qwen/Qwen3.8-27B-FP8`
- NVFP4：`Inferact/Qwen3.8-27B-NVFP4`

NVFP4 启动日志确认使用原生 `FlashInferCutlassNvFp4LinearKernel`，不是反量化到 BF16 的回退路径。

## 3. 核心指标对比

**总 TPM 包含全部成功完成的请求，即使其 TTFT 超过 SLA；不会因延迟不达标而剔除请求。**

| 并发 | 指标 | FP8 | NVFP4 | NVFP4 相对变化 |
|---:|---|---:|---:|---:|
| 1 | 总 TPM | 95,685 | **102,921** | **+7.6%** |
| 1 | TTFT P50 | 0.98s | **0.85s** | 改善 |
| 1 | TPOT P50 | 8.95ms | **8.33ms** | -6.9% |
| 8 | 总 TPM | 308,718 | **341,672** | **+10.7%** |
| 8 | TTFT P50 | 1.05s | **0.93s** | 改善 |
| 8 | TPOT P50 | 21.33ms | **19.66ms** | -7.8% |
| 16 | 总 TPM | 355,417 | **409,980** | **+15.4%** |
| 16 | TTFT P50 | 2.97s | **1.76s** | 改善 |
| 16 | TPOT P50 | 32.90ms | **28.25ms** | -14.1% |
| 20 | 总 TPM | 374,926 | **438,504** | **+17.0%** |
| 20 | TTFT P50 | 2.50s | **2.30s** | 改善 |
| 20 | TPOT P50 | 34.87ms | **30.16ms** | -13.5% |
| 24 | 总 TPM | 373,670 | **442,519** | **+18.4%** |
| 24 | TTFT P50 | 8.84s | **7.08s** | 改善 |
| 24 | TPOT P50 | 42.99ms | **31.77ms** | -26.1% |
| 32 | 总 TPM | 382,511 | **449,069** | **+17.4%** |
| 32 | TTFT P50 | 16.89s | **13.47s** | 改善，但仍超标 |
| 32 | TPOT P50 | 40.36ms | 41.92ms | +3.9% |

所有测试点失败请求均为 0，随机冷请求的 Prefix Cache 命中率均为 0%。

## 4. SLA 与原始吞吐

| 模型 | 聚合 SLA 内最高总 TPM | 对应并发 | 原始最高总 TPM | 对应并发与限制 |
|---|---:|---:|---:|---|
| FP8 | 374,926 | 20 | 382,511 | 32，P50/P95 均超标 |
| **NVFP4** | **442,519** | **24** | **449,069** | 32，P50 超标 |

NVFP4 将聚合 SLA 内的最佳并发点从 20 推到 24，同时把该点的总 TPM 提高约 **18.0%**（442,519 / 374,926 - 1）。

并发 32 的 449,069 仍然计入原始总 TPM，但不能标记为 SLA 达标配置。

## 5. 显存、KV 容量与功耗

| 指标 | FP8 | NVFP4 | 变化 |
|---|---:|---:|---:|
| 每卡模型加载显存 | 14.98GiB | **12.82GiB** | 减少约 14.4% |
| TP2 KV tokens | 1,553,749 | **1,612,913** | 增加约 3.8% |
| 32K 估算最大并发 | 47.42 | **49.22** | 增加约 3.8% |
| GPU 峰值功耗 | 多数约 296～356W | 多数约 274～310W | 整体下降 |

NVFP4 的权重压缩减少了每卡权重占用，但 MTP、CUDA Graph、激活和混合注意力状态仍占用显存，因此 KV 容量增幅小于权重降幅。

## 6. MTP 接受率

| 并发 | FP8 MTP=3 接受率 | NVFP4 MTP=3 接受率 |
|---:|---:|---:|
| 1 | 50.05% | 45.05% |
| 8 | 49.06% | 45.34% |
| 16 | 47.14% | 46.79% |
| 20 | 46.35% | 49.12% |
| 24 | 42.84% | 48.72% |
| 32 | 48.58% | 47.70% |

NVFP4 的总性能提升不能只用接受率解释。权重计算路径、prefill/decode kernel 效率和功耗同样影响最终 TPM，因此仍需以端到端指标为准。

## 7. 当前部署配置

```bash
CUDA_VISIBLE_DEVICES=0,1 vllm serve /data/Qwen3.8-27B-NVFP4 \
  --served-model-name Qwen3.8-27B-NVFP4 \
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

当前 ECS 已保留该配置运行。可复用部署脚本：[scripts/deploy_qwen38_tp2.sh](scripts/deploy_qwen38_tp2.sh)，支持 `start/stop/restart/status/logs`，并可通过环境变量切换 FP8 权重。

## 8. 后续验证

1. 对 NVFP4 并发 16、20、24 做 500 请求 × 3 个 seed 的重复性验证。
2. 补充 NVFP4 与 FP8 的业务质量、长输出一致性和典型 Agent 工具调用回归。
3. 增加 32K 输入、2048 输出和 Poisson QPS 到达测试。
4. 在质量回归通过后，再将 NVFP4 作为商业化默认权重。

## 9. 测试产物

- [原生 Sweep 与 TPM/TTFT/TPOT 取舍](NATIVE_SWEEP_README.md)
- [NVFP4 汇总 CSV](results/tp2-nvfp4-mtp3-summary.csv)
- [NVFP4 关键启动日志](logs/tp2-nvfp4-startup.log)
- [TP2 FP8 基线文档](TP2_README.md)

ECS 原始结果目录：

```text
/data/benchmark-results/nvfp4-tp2/
/data/vllm-nvfp4-tp2-mtp3.log
```

## 参考资料

- [官方 Recipe] Qwen3.8-27B — https://recipes.vllm.ai/Qwen/Qwen3.8-27B
- [模型] Inferact/Qwen3.8-27B-NVFP4 — https://huggingface.co/Inferact/Qwen3.8-27B-NVFP4
- [模型] Qwen/Qwen3.8-27B-FP8 — https://huggingface.co/Qwen/Qwen3.8-27B-FP8

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-28 | 新建相同 TP2/32K/FP8 KV/MTP=3 条件下的 FP8 vs NVFP4 对比；NVFP4 总 TPM 提升 7.6%～18.4%，SLA 内最佳点为并发 24 |
