# kimi-k3.1-pro 双协议面（Responses / Anthropic Messages）接入实测

> 测试时间：2026-11-19
> 脚本：[test_kimi_k31_protocol_support.py](test_kimi_k31_protocol_support.py)
> 节点：国际站新加坡 `llm-ablnum2bgfvl34hs.ap-southeast-1`、国际站北京 `llm-kvw0aiysjfv4g6fh.cn-beijing`
> 模型 ID：`kimi-k3.1-pro`（MaaS 专属端点无厂商前缀）

## 结论

**两条协议面均可用（两节点全部 HTTP 200）。** 但二者都是百炼网关的"兼容实现"，不是模型厂商私有原生协议，行为差异见下方"注意事项"。

| 协议面 | 端点 | SG | 北京 |
|--------|------|----|------|
| OpenAI 兼容 Responses | `POST {host}/compatible-mode/v1/responses` | ✅ | ✅ |
| Anthropic 兼容 Messages | `POST {host}/apps/anthropic/v1/messages` | ✅ | ✅ |
| 对照 Chat Completions | `POST {host}/compatible-mode/v1/chat/completions` | ✅ | ✅ |

## 用例明细

| 用例 | 结果 | 关键证据 |
|------|------|----------|
| A. Responses 非流式（`input` + `max_output_tokens=1024`） | 200 / `status=completed` | `output` 含 `reasoning` + `message` 两类 item；`usage` 带 `input_tokens_details.cached_tokens`、`output_tokens_details.reasoning_tokens` |
| A'. 同一请求 `max_output_tokens=128` | 200 / `status=incomplete` | 128 token 被思考耗尽，无 message 文本 → 该模型思考占额，预算必须放大 |
| B. Anthropic Messages 非流式 | 200 / `stop_reason=end_turn` | `content` = [`thinking`, `text`]，`usage` 含 `cache_creation_input_tokens` / `cache_read_input_tokens` |
| D. Anthropic 流式 | 200 | 事件序：`ping → message_start → content_block_start → content_block_delta…` |
| E. Anthropic `thinking={"type":"disabled"}` | 200 但**仍返回 thinking block** | 参数被接受、语义未生效 |
| E2. 对照 `enable_thinking=false`（Chat Completions） | 200 | `reasoning_len=0`，关闭生效 |
| F. Responses 流式 | 200 | 事件序：`response.created → response.in_progress → response.output_item.added → response.content_part.added → response.reasoning_text.delta → response.reasoning_text.done → response.content_part.done → response.output_item.done → response.output_text.delta → response.output_text.done → response.completed` |

## 接入要点

1. **认证**：Anthropic 面支持 `x-api-key` 或 `Authorization: Bearer` 两种头，必须带 `anthropic-version`（实测 `2023-06-01` 可用）。
2. **端点路径**：Anthropic 面 SDK 的 `base_url` 填 `.../apps/anthropic`，SDK 自动拼 `/v1/messages`；直连 HTTP 要写全 `.../apps/anthropic/v1/messages`。
3. **思考占额**：kimi-k3.1-pro 默认开启思考，`max_tokens` / `max_output_tokens` 同时覆盖思考与回答，实测 128 档会直接 `incomplete`。生产建议 ≥1024，或用 `output_config.effort`（Anthropic 面支持 max/high/medium/low，默认 max）降档。
4. **思考关闭能力两侧不一致**：Chat Completions 的 `enable_thinking=false` 生效；Anthropic 面的 `thinking.type=disabled` 被接受但思考仍发生。若客户要求严格关闭思考，应引导走 Chat Completions 面。
5. **限流**：SG workspace 端点配额紧，本脚本单节点连发 6 次即触发多次 429，脚本已内置 8s/16s/24s 退避。
