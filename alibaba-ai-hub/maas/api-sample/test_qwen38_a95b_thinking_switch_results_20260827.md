# qwen3.8-2.4t-a95b 思考模式与思考长度控制测试结果（2026-08-27）

## 测试环境

| 项目 | 值 |
|------|-----|
| 模型 | `qwen3.8-2.4t-a95b`（百炼托管开源版） |
| 端点 | 百炼专属端点（cn-beijing，compatible-mode/v1） |
| SDK | OpenAI Python SDK，流式调用 |
| 测试题 | "一个水库的水位每天翻倍，50天灌满，第几天灌一半？请简要推理。" |
| 重复次数 | 正常用例 3 次，报错用例 1 次 |
| 脚本 | `test_qwen38_a95b_thinking_switch.py`（同目录） |

## 核心结论

1. **思考无法关闭**：`enable_thinking` 仅接受 `True`，传 `False` 直接报错 `invalid_parameter_error: The value of the enable_thinking parameter is restricted to True.`（专属端点与公共端点均验证）
2. **`/no_think` 提示词软开关无效**：思考照常输出，甚至因提示词变长思考更多
3. **`thinking_budget` 有效**：Token 硬上限，粒度精确，budget=1 时思考仅 2~4 字符
4. **`reasoning_effort` 有效**：档位软引导，low → medium → high 思考长度呈单调梯度
5. **两参数互斥（实测确认）**：同时设置报错 `'reasoning_effort' and 'thinking_budget' cannot be set simultaneously`——闭源版 qwen3.8-max/flash 的互斥规则**同样适用于 a95b**
6. **`reasoning_effort=none` 被拒**：报错信息同 `enable_thinking=False`，从侧面印证官方映射规则（none → enable_thinking=False）在 a95b 生效，且因强制思考而不可用

## 详细结果

### A. 思考开关

| 用例 | 结果 | 结论 |
|------|------|------|
| A1 `enable_thinking=False` | ❌ 报错 restricted to True | API 硬开关被服务端拒绝 |
| A2 `True` + 提示词 `/no_think` | 思考 [282, 315, 431] 字符，均值 343 | 软开关无效（比对照组还长） |
| A3 `True`（对照组） | 思考 [140, 242, 143] 字符，均值 175 | 基线，思考正常输出 |

### B. 思考长度控制

| 用例 | 思考长度（字符，3 轮） | 均值 | vs 基线 |
|------|----------------------|------|---------|
| B1a `thinking_budget=1` | [4, 2, 2] | 3 | **-98%**，近似关闭 |
| B1b `thinking_budget=1024` | [107, 87, 105] | 100 | -43% |
| B2a `reasoning_effort=low` | [100, 107, 111] | 106 | -40%，方差极小 |
| B2b `reasoning_effort=medium` | [143, 163, 95] | 134 | -23% |
| B2c `reasoning_effort=high` | [357, 274, 287] | 306 | +75% |

### C. 边界行为

| 用例 | 结果 | 结论 |
|------|------|------|
| C1 `reasoning_effort=none` | ❌ 报错（同 enable_thinking=False 的 restricted to True） | 官方映射 none→enable_thinking=False 在 a95b 生效，因强制思考被拒 |
| C2 `thinking_budget=4096` + `reasoning_effort=low` | ❌ 报错 cannot be set simultaneously | **互斥规则同样适用 a95b**（与闭源版 max/flash 一致） |

## 使用建议

```python
# 推荐：thinking_budget——官方 API 参考明确支持 Qwen3.8 系列，硬上限精确可控
extra_body={"enable_thinking": True, "thinking_budget": 4096}

# 可选：reasoning_effort——实测有效但官方支持列表未明文 a95b，软引导档位
extra_body={"enable_thinking": True, "reasoning_effort": "low"}

# 禁止：两者同时设置（a95b 实测报错）
# 禁止：enable_thinking=False / reasoning_effort=none（a95b 强制思考）
```

## 官方文档对照

- [深度思考模型的用法](https://help.aliyun.com/zh/model-studio/deep-thinking)：将 a95b 归类"混合思考模式"，与实测不符（实际仅思考模式）
- [DashScope API 参考](https://help.aliyun.com/zh/model-studio/qwen-api-via-dashscope)：`reasoning_effort` 支持列表仅明文 qwen3.8-max/flash；互斥规则写明适用 max/flash，**实测 a95b 同样互斥**

> 知识库同步：`alibaba-ai-hub/maas/qwen.md`「Qwen3.8-2.4T-A95B 开源版」小节
