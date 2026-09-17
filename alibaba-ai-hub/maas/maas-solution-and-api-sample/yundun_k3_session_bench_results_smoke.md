# yundun-key（AI DeepSign）kimi-k3 会话式负载基准结果

- 时间: 2026-09-11 12:34
- 端点: https://api-aideepsign.cn-hangzhou.aliyuncs.com/v1/messages
- 负载: 到达率 0.5→0.5/s （10s 爬坡 + 30s 稳态），会话 2（完成 1/中断 0）
- 请求: 成功 3 | 限流 0 | 其他错误 0 | 有效时长 19s
- tokens: 输入 6.2k + 输出 1.6k + 缓存读 1.5k + 缓存写 0.0k = 配额口径 0.01M
- 缓存模式: explicit（预检决定，可用 --cache-mode 覆盖）

## TPM 结论
- 峰值 60s 窗口 TPM: **9k**（≈0.01M）
- 未触发限流；受 token 预算/时长约束，下限结论: TPM ≥ 9k

## 缓存命中率
- 总体: **19.9%**（cache_read 1.5k / 计费输入基数 7.7k）
- 首轮（system 初始化）: 0.0%（2 请求）
- 第 2 轮起（前缀复用）: 68.9%（1 请求）

| 轮次 | 请求数 | 命中率 | 平均输入 tokens |
|---|---|---|---|
| 1 | 2 | 0.0% | 2.7k |
| 2 | 1 | 68.9% | 2.2k |

## TTFT（流式首 token）
- 任意首 token（含 thinking）: n=3 | P50 **1064ms** | P90 1071ms | P95 1071ms | max 1071ms
- 正文首 token（text_delta）: n=3 | P50 **10475ms** | P90 26786ms | P95 26786ms | max 26786ms
- 首轮（初始上下文 ~28k） 任意首 token: P50 1071ms | P95 1071ms
- 后续轮（增量输入） 任意首 token: P50 709ms | P95 709ms

## 60s 窗口曲线

| 窗口 | t(s) | 成功req | TPM | 缓存% | 429 | TTFT P50(ms) |
|---|---|---|---|---|---|---|
| 1 | 0-60 | 3 | 9k | 20% | 0 | 1064 |
