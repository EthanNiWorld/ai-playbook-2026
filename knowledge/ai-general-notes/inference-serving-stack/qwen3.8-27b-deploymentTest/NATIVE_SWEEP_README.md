# NVFP4 原生 vLLM Sweep：TPM、TTFT、TPOT 取舍

> 最后更新: 2026-10-28  
> 领域: AI Infra / LLM Inference / Benchmark  
> 状态: Reviewed

<!-- SUMMARY_START -->
**一句话说明**: 使用原生 `vllm bench sweep serve_workload` 对单 TP2、NVFP4、FP8 KV、MTP=3 自动扫描并发，生成延迟、吞吐和 Pareto 曲线。  
**核心价值**: 用同一组数据区分原始最大 TPM、SLA 内最大 TPM，以及接近最大吞吐时的低延迟平衡点。  
**相关产品**: [NVFP4 vs FP8](TP2_NVFP4_README.md), [自动 Sweep 脚本](scripts/run_qwen38_native_sweep.py)
<!-- SUMMARY_END -->

## 1. 推荐结论

| 选择 | 并发 | 总 TPM | TTFT P50 | TPOT P50 | 适用目标 |
|---|---:|---:|---:|---:|---|
| 低 TPOT 候选 | 11 | 382,311 | 0.93s | 24.21ms | 更重视 decode 流畅度 |
| **平衡推荐** | **20** | **438,760** | **2.61s** | **31.76ms** | 接近最大吞吐，同时保留较低 TTFT |
| 激进 SLA 上限 | 25 | 440,997 | 7.08s | 34.63ms | 追求 P50/P95 内最大 TPM |
| 原始最大 TPM | 40 | 452,941 | 19.74s | 41.68ms | 只追求原始吞吐，不满足 TTFT SLA |

关键取舍：

- 并发 20→25，总 TPM 只增加约 **0.5%**，但 TTFT P50 从 **2.61s 增至 7.08s**。
- 并发 25→40，总 TPM 再增加约 **2.7%**，TTFT 和 TPOT 继续明显恶化。
- 因此日常生产优先考虑 **20**；需要更高容量且能接受 P50 接近 8s 时，再考虑 **25**。

**总 TPM 包含全部成功请求，即使 TTFT 超过 SLA；SLA 仅单独判定，不做请求剔除。**

## 2. 测试条件

- 模型：`Inferact/Qwen3.8-27B-NVFP4`
- 单实例：`tensor-parallel-size=2`
- `max-model-len=32768`
- `max-num-batched-tokens=32768`
- `max-num-seqs=32`
- FP8 KV Cache
- MTP=3
- CUDA Graph `-O2`
- 输入 8192 tokens，输出 512 tokens
- 原生 `vllm bench sweep serve_workload`
- `workload-var=max_concurrency`，共 8 个档位，每档 40 请求，warmup 4 请求

## 3. 完整结果

| 并发 | TTFT P50 | TTFT P95 | TPOT P50 | 总 TPM | 输出 TPM | MTP 接受率 | 聚合 SLA |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 0.85s | 0.86s | 8.39ms | 104,054 | 6,084 | 48.04% | 通过 |
| 6 | 0.91s | 4.97s | 16.17ms | 317,932 | 18,590 | 46.75% | 通过 |
| 11 | 0.93s | 8.73s | 24.21ms | 382,311 | 22,354 | 45.21% | 通过 |
| 16 | 1.88s | 13.22s | 29.42ms | 414,078 | 24,212 | 46.68% | 通过 |
| 20 | 2.61s | 16.51s | 31.76ms | 438,760 | 25,655 | 49.74% | 通过 |
| 25 | 7.08s | 20.62s | 34.63ms | 440,997 | 25,786 | 45.56% | 通过 |
| 30 | 13.45s | 24.38s | 38.74ms | 443,509 | 25,933 | 46.86% | P50 超标 |
| 40 | 19.74s | 39.17s | 41.68ms | **452,941** | 26,484 | 46.81% | P50/P95 超标 |

## 4. 曲线

- [TTFT 随并发变化](results/native-sweep/ttft_curve.png)
- [TPOT 随并发变化](results/native-sweep/tpot_curve.png)
- [总吞吐随并发变化](results/native-sweep/throughput_curve.png)
- [TTFT 与总吞吐权衡](results/native-sweep/latency_throughput.png)
- [Pareto 前沿](results/native-sweep/pareto/PARETO.png)

吞吐在并发 20 后进入边际递减，TPOT 则近似持续上升，这是选择生产并发上限时需要同时看两条曲线的原因。

### 4.1 `max-num-batched-tokens=40960` 对照

保持 NVFP4、TP2、FP8 KV、MTP=3 和 seed=23025 不变，仅将 prefill budget 从 32768 提至 40960，复测并发 25：

| 参数 | 总 TPM | TTFT P50 | TTFT P95 | TPOT P50 | 判断 |
|---|---:|---:|---:|---:|---|
| 32768 | **440,997** | **7.08s** | **20.62s** | 34.63ms | 当前更优 |
| 40960 | 422,791 | 10.12s | 22.80s | **31.98ms** | 总 TPM -4.1%，P50 超标 |

40960 使 TPOT 略有改善，但 prefill 阻塞和总吞吐明显恶化，因此恢复 32768。结果说明“波次对齐”只是理论候选，增大 batch 仍可能增加头阻塞，不能据此直接提高 prefill budget。

原始结果：[40960 对照 CSV](results/nvfp4-bt40960-c25-summary.csv)。

## 5. 自动执行脚本

### 文件

- [run_qwen38_native_sweep.py](scripts/run_qwen38_native_sweep.py)：自动运行 sweep、绘图、生成 `summary.csv` 和 `recommendations.json`
- [vllm_sweep_server.sh](scripts/vllm_sweep_server.sh)：保留 sweep 子进程启动日志
- [vllm_sweep_reset.sh](scripts/vllm_sweep_reset.sh)：每个档位之间清理 Prefix/MM/Encoder Cache

### 运行

先停止当前占用 GPU/端口的服务，然后执行：

```bash
python3 run_qwen38_native_sweep.py \
  --experiment-name nvfp4-tp2-mtp3-001 \
  --workload-iters 8 \
  --num-prompts 40 \
  --output-len 512
```

默认输出到：

```text
/data/benchmark-results/native-sweep/nvfp4-tp2-mtp3-001/
```

主要产物：

```text
summary.csv
recommendations.json
ttft_curve.png
tpot_curve.png
throughput_curve.png
latency_throughput.png
pareto/PARETO.png
server-8000.log
```

### 只重新生成汇总

```bash
python3 run_qwen38_native_sweep.py \
  --summary-only \
  --experiment-dir /data/benchmark-results/native-sweep/nvfp4-tp2-mtp3-001
```

### 自动推荐逻辑

脚本输出三类运行点：

1. `raw_max_tpm`：全量成功请求中的最大总 TPM，不考虑 SLA。
2. `sla_max_tpm`：P50≤8s 且 P95≤30s 的最大总 TPM。
3. `balanced_lowest_ttft_within_ratio`：达到 SLA 内最大 TPM 的 99% 以上时，选择 P50 最低的点。

可用 `--balanced-ratio 0.95` 将平衡范围放宽到 95%。

## 6. 当前结果文件

- [汇总 CSV](results/native-sweep/summary.csv)
- [推荐结果 JSON](results/native-sweep/recommendations.json)

## 7. 工程注意事项

- 原生 sweep 会自行启动和停止模型服务，运行前必须释放 GPU 和端口。
- 非交互 SSH 下需要显式设置 vLLM 的 PATH，子进程不能依赖 conda 已手工激活。
- MTP 使用点号参数形式，避免 sweep 对嵌套 JSON 的错误拆分：

```text
--speculative-config.method mtp
--speculative-config.num_speculative_tokens 3
```

- 绘图需要 `pandas` 和 `seaborn`；压测本身不依赖这两个包。
- 当前 vLLM 0.32 的 `dry-run/show-stdout` 路径存在参数解析问题，本脚本不使用它们，而是通过 wrapper 保留启动日志。
- 测试完成后，当前 ECS 已恢复为单 TP2 + NVFP4 + FP8 KV + MTP=3 服务。

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-28 | 完成原生 workload sweep 与四类图表；新增自动执行脚本、TPM 汇总和三档运行点推荐 |
