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

## 最大输出边界与注意点实测（test_qwen4_max_output_limits.py + temp_file/probe_qwen4_max_upper.py，新加坡端点）

### 输出上限

| 模式 | 文档上限 | 实测结论 |
| --- | --- | --- |
| 非思考（enable_thinking=False） | 131,072 | 参数无请求期校验，上限为生成期硬帽（未真实生成到顶验证，避免高额费用） |
| 思考（默认） | 262,144（思考+回答共享） | 同上 |

**关键发现：max_tokens 无请求期上限校验**——传 131,073 / 262,145 / 393,216 甚至 1,000,000 均被静默接受并正常返回，不报 400。越界值不会报错，只会按模型实际上限截断，**不能依赖 API 报错发现配置错误**。

### 共享预算截断实证（迁移最大坑）

| 用例 | 结果 |
| --- | --- |
| 思考开启 + max_tokens=64 | finish_reason=**length**，completion=64 全部为 reasoning_tokens，**正文为空字符串** |
| 非思考 + max_tokens=64（对照） | finish_reason=stop，29 token 完整回答 |
| xhigh + max_tokens=200 + 算术题 | 思考自适应压缩至 137 token，正文 58 token，finish_reason=stop（紧预算下思考会压缩而非必然截断，但不可依赖） |

即：qwen3.8 代"max_tokens 只限正文"的经验完全失效，小预算 + 思考开启 = 正文静默消失。流式消费端必须读 finish_reason，否则无法感知截断。

### 参数行为

- `reasoning_effort` 与 `thinking_budget` **互斥**：同设返回 400 `invalid_parameter_error`（"cannot be set simultaneously"）
- `reasoning_effort` low / medium / xhigh 均被接受；同一问题 reasoning_tokens 实测 low=20~26、medium=96、xhigh=262，档位确实影响思考长度（medium 按文档映射到 high）
- 多轮历史 assistant **不带** reasoning_content（默认 preserve_thinking=true）实测**不报错**、正常回答；显式 preserve_thinking=False 也正常。官方"须完整回传"是质量建议而非硬校验，但纯文本历史的 Agent 建议显式关闭以符合协议语义

### 成本注意点

- 思考 token 计入输出计费（SG $4.5/1M）：xhigh 档同一简单问题输出 token 约为 low 档 5 倍，高频场景默认 high 档需评估成本，轻量任务建议显式传 low
- 输出预算建议：思考模式按"思考+回答"共同预留（如 32K 起步），非思考模式可按纯回答预留