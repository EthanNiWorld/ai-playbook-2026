# qwen3.8-27b 思考模式测试结果（2026-08-27）

## 测试环境

| 项目 | 值 |
|------|-----|
| 模型 | `qwen3.8-27b`（Qwen3.8 系列 27B Dense 视觉语言开源模型，2026-08-17 上线） |
| 端点 | 主测 CN 专属端点；A1 关键用例三端点交叉验证（CN 专属 / 国际站 BJ / 国际站 SG） |
| SDK | OpenAI Python SDK，流式调用 |
| 测试题 | "一个水库的水位每天翻倍，50天灌满，第几天灌一半？请简要推理。"（与 a95b 同题） |
| 重复次数 | 正常用例 3 次，报错用例 1 次 |
| 脚本 | `test_qwen38_27b_thinking_switch.py`（同目录） |
| 对照组 | `qwen3.8-2.4t-a95b`（实测仅思考模式，见 `test_qwen38_a95b_thinking_switch_results_20260827.md`） |

## 核心结论

1. **思考可以关闭**：`enable_thinking=False` 完全生效——思考 0 字符，模型直接输出回复，且**三端点行为一致**（CN 专属 / 国际站 BJ / 国际站 SG）
2. **默认开启思考**：不传 `enable_thinking` 时模型默认思考（均值 357 字符）——与官方"Qwen3.8 系列混合思考模式，默认开启"口径一致
3. **`reasoning_effort=none` 同样可关**：思考 0 字符，验证官方 `none → enable_thinking=False` 映射在 27b 生效且被允许（a95b 因强制思考被拒）
4. **`thinking_budget` 有效**：budget=1024 → 思考均值 148 字符
5. **`reasoning_effort` 有效**：low → 思考均值 121 字符，方差小
6. **两参数互斥（实测同样适用 27b）**：同时设置报错 `'reasoning_effort' and 'thinking_budget' cannot be set simultaneously`
7. **`/no_think` 软开关效果不明确**：思考仍输出（均值 189 字符，与去异常后的对照组相当），未实现完全关闭；27b 有可靠的硬开关，软开关无实用价值

## 详细结果

### A. 思考开关

| 用例 | 思考长度（字符，3 轮） | 均值 | 结论 |
|------|----------------------|------|------|
| A1 `enable_thinking=False` | [0, 0, 0] | **0** | ✅ **成功关闭** |
| A2 不传 `enable_thinking` | [314, 325, 431] | 357 | 默认开启思考 |
| A3 `True` + 提示词 `/no_think` | [116, 269, 183] | 189 | 软开关未完全关闭 |
| A4 `enable_thinking=True`（对照组） | [187, 138, 1168*] | 498 | 思考正常（*含一轮异常值） |

### B. 思考长度控制

| 用例 | 思考长度（字符，3 轮） | 均值 |
|------|----------------------|------|
| B1 `thinking_budget=1024` | [153, 135, 157] | 148 |
| B2 `reasoning_effort=low` | [108, 134, 121] | 121 |

### C. 边界行为

| 用例 | 结果 | 结论 |
|------|------|------|
| C1 `reasoning_effort=none` | 思考 0 字符 | ✅ 等价关闭，映射生效且被允许 |
| C2 `thinking_budget=4096` + `reasoning_effort=low` | ❌ 报错 cannot be set simultaneously | 互斥规则同样适用 27b |

### X. A1 三端点交叉验证

| 端点 | 结果 |
|------|------|
| CN 专属（cn-beijing） | 思考 0 字符，关闭 ✅ |
| 国际站 BJ（cn-beijing） | 思考 0 字符，关闭 ✅ |
| 国际站 SG（ap-southeast-1） | 思考 0 字符，关闭 ✅ |

## Qwen3.8 系列思考模式横向对比

| 模型 | enable_thinking=False | 默认行为 | reasoning_effort=none | 实测结论 |
|------|----------------------|---------|----------------------|---------|
| qwen3.8-2.4t-a95b | ❌ 报错 restricted to True | 强制思考 | ❌ 报错 | **仅思考模式**（与官方文档"混合思考"分类不符） |
| qwen3.8-27b | ✅ 关闭 | 默认思考 | ✅ 关闭 | **混合思考模式**（与官方文档一致） |
| qwen3.8-max / flash | ✅（官方文档） | 默认思考 | ✅ 映射关闭 | 混合思考模式（官方口径） |

## 使用建议

```python
# 关闭思考：直接硬开关
extra_body={"enable_thinking": False}

# 控制思考长度（两参数二选一，同时设置会报错）
extra_body={"enable_thinking": True, "thinking_budget": 4096}
extra_body={"enable_thinking": True, "reasoning_effort": "low"}
```

> 知识库同步：`alibaba-ai-hub/maas/qwen.md`「Qwen3.8-27B」小节
