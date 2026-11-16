# qwen4-max / qwen4-max-preview 上架与可调用性实测（2026-11-16）

## 结论

**Qwen4-Max 正式版（Model ID: `qwen4-max`）已上架百炼，支持按量计费，CN / 国际站新加坡 / 国际站北京三端点实测全部调通。**

另有一个独立的预览版 `qwen4-max-preview`（2026-11-11 上线，预览期至 11-25 24:00 后下线），仅 Token Plan 套餐可调用，与正式版是两个不同模型条目。

- 正式版文档：https://help.aliyun.com/zh/model-studio/qwen4-max
- 预览版文档：https://help.aliyun.com/zh/model-studio/qwen4-max-preview
- 口语名 `qwen4.0-max` 无效（新加坡端点 404 model_not_found）

## 实测矩阵（test_qwen4_max_preview.py，按量计费密钥）

| 端点 | qwen4-max | qwen4-max-preview | qwen4.0-max |
| --- | --- | --- | --- |
| CN 常规端点（CN_TEST） | ✅ 成功 | 403 access_denied | 403 access_denied |
| 国际站新加坡（INTL_SG_TEST） | ✅ 成功 | 403 access_denied | 404 model_not_found |
| 国际站北京（INTL_BJ_TEST） | ✅ 成功 | 403 access_denied | 403 access_denied |
| Token Plan 端点（普通密钥） | 404 | 404 | 404 |

- 三端点成功调用均返回正常回答，usage 含 `reasoning_tokens`（默认开启思考，本次传 `reasoning_effort=low`）
- preview 的 403 与"仅 Token Plan、需 sk-sp- 套餐专用 Key + 专属 Base URL"官方口径一致；Token Plan Key 与按量 Key 完全隔离不可混用

## 正式版规格（官方文档）

| 项 | 值 |
| --- | --- |
| 部署节点 | 北京（中国内地）、新加坡（国际）、法兰克福/弗吉尼亚/东京/港（全球） |
| 上下文 | 1M token |
| 最大输出 | 非思考 131,072；思考+回答总预算 262,144 |
| 思考模式 | 默认开启（enable_thinking=true），reasoning_effort: low / high（默认）/ xhigh |
| 多模态 | 文本 + 图片 + 视频输入，文本输出 |
| 工具 | Function Calling（含并行）、联网搜索、前缀补全、思维链摘要与加密 |
| 结构化输出 | JSON Object / JSON Schema |
| 缓存 | 显式 + 隐式缓存均支持 |
| 批量推理 | 仅北京节点支持 |
| API 兼容 | OpenAI Chat Completions / Responses、Anthropic Messages、DashScope |

注意：preview 与正式版规格不同（preview 最大输出 393,216、reasoning_effort 为 low/medium/xhigh）；正式版为 low/high/xhigh，medium 映射到 high。

## 定价（国际站 USD 列表价，每百万 token，2026-11-16 抓取）

来源：https://www.alibabacloud.com/help/en/model-studio/model-pricing

| Region | 输入 | 输出 | 缓存写(5m) | 缓存写(1h) | 缓存读 |
| --- | --- | --- | --- | --- | --- |
| Singapore（主口径） | $1.5 | $4.5 | $1.875 | $3 | $0.075 |
| China (Beijing) | $1.413 | $4.24 | $1.767 | $2.827 | $0.071 |

- 北京节点另有 Batch 价：Batch File $0.707/$2.12，Batch Chat $1.413/$4.24
- 对比上代 qwen3.8-max（SG $2/$6）：qwen4-max 输入降 25%、输出降 25%

## 迁移注意（官方口径，自 qwen4 代起）

- `max_tokens` 与 `max_completion_tokens` 等价，均限制**思考+回答总量**；沿用旧模型"仅为回答预留"的上限会导致输出提前截断
- 多轮对话 `preserve_thinking` 默认开启，历史 assistant 消息须通过 `reasoning_content` 字段完整回传思考内容