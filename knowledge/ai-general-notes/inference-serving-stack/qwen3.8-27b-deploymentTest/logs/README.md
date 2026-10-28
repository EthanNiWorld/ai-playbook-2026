# 部署与压测日志说明

> 归档日期: 2026-10-28

## 文件清单

| 文件 | 内容 |
|---|---|
| `tp2-final-startup.log` | 单 TP2 + FP8 权重 + FP8 KV + MTP=3 的完整启动日志；内部通信 IP 已脱敏 |
| `tp2-nvfp4-startup.log` | 单 TP2 + NVFP4 权重 + FP8 KV + MTP=3 的原生 NVFP4 kernel、显存与 KV 容量记录 |
| `tp2-startup-variants.log` | TP2 下 MTP 0/2/3 与 BF16 KV 的关键启动参数、kernel、显存和 KV 容量记录 |
| `tp2-benchmark-summaries.log` | TP2 并发、MTP、KV 压测的运行摘要 |
| `tp1-startup-variants.log` | 历史双 TP1 实验中 prefill batch、MTP、KV dtype 变体的关键启动记录 |
| `nginx.conf` | 双 TP1 历史实验使用的本机 `least_conn` 配置；当前单 TP2 不使用该入口 |

## 未归档内容

- 模型权重、ModelScope/Hugging Face 下载临时文件
- vLLM compile cache、FlashInfer autotune cache
- 重复的大段请求访问日志和模型下载进度
- 原始 enriched JSON：继续保留在 ECS，仓库中的 `../results/` 已保存对应汇总 CSV

## ECS 原始位置

```text
/data/vllm-*.log
/data/benchmark-results/tp2-concurrency-8k-o128/
/data/benchmark-results/tp2-cache-ab/
/data/benchmark-results/tp2-mtp-ab/
```

这些日志仅用于工程复盘。压测结论以 `../TP2_README.md`、`../README.md` 和汇总 CSV 为准。原始日志和 CSV 中的 MTP=2 记录仅作为历史实验归档；后续部署与调优统一默认 MTP=3，不再将 2 作为独立测试场景。
