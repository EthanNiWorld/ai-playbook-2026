# OSWorld-Verified 单步代理测试（方案 B）

这是一个轻量级的 **OSWorld-Verified 代理能力代理测试**项目，放在 `vibeCodingProject/` 下作为独立子项目。

## 定位

- **不是**完整的 OSWorld-Verified Harness（那需要真实桌面环境，成本高、耗时长）。
- **是**方案 B 的实现：给定任务描述 + 单张 GUI 截图，让模型预测下一步操作，用于快速对比不同模型的 GUI/Computer Use 能力。
- 适合在 **100 RMB 以内、1 小时内**快速摸底 `qwen3.7-plus`、`qwen3.7-max-2026-06-08` 等模型的 GUI 能力差距。

## 项目结构

```
osworld_verified_proxy/
├── README.md                  # 本文件
├── requirements.txt           # Python 依赖
├── config.py                  # 配置（模型、API、路径）
├── prepare_data.py            # 生成/准备测试样本（含合成截图 + 外部真实截图）
├── run_eval.py                # 对单个模型跑单步 action prediction
├── compare_results.py         # 对比两个模型的结果
├── generate_report.py         # 生成 HTML 评测报告
├── data/
│   ├── tasks.json             # 任务清单（任务描述 + 截图路径 + 期望动作）
│   └── images/                # 截图目录
└── results/
    └── {model_name}.json      # 每个模型的原始输出结果
    └── report.html            # HTML 汇总报告
```

## 快速开始

### 1. 安装依赖

```bash
cd vibeCodingProject/osworld_verified_proxy
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

> macOS 用户注意：按项目规范，使用 `pip3` 而非 `pip`。

### 2. 设置环境变量

```bash
# 请先设置环境变量（将 YOUR_API_KEY 替换为你的真实 API Key）
export DASHSCOPE_API_KEY=YOUR_API_KEY

# 可选：如果使用非默认 endpoint
export DASHSCOPE_BASE_URL="https://your-workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
```

### 3. 生成测试数据

```bash
python3 prepare_data.py
```

默认会生成 12 个合成 GUI 截图，覆盖基础场景 + 高难度场景（弹窗遮挡、错误提示、滚动、通知横幅），以及一个外部真实截图 `cnipa_login_captcha.png`（如果已放入 `data/images/`）。

### 4. 运行评测

```bash
# 测试 qwen3.7-plus
python3 run_eval.py --model qwen3.7-plus

# 测试 qwen3.7-max-2026-06-08
python3 run_eval.py --model qwen3.7-max-2026-06-08

# 扩展到 100 个样本时，可用并发加速（注意 DashScope 速率限制）
python3 run_eval.py --model qwen3.7-plus --workers 5
```

### 5. 对比结果

```bash
python3 compare_results.py \
  --model_a results/qwen3.7-plus.json \
  --model_b results/qwen3.7-max-2026-06-08.json
```

### 6. 生成 HTML 报告

```bash
python3 generate_report.py
```

报告会输出到 `results/report.html`，包含模型概览、逐任务结果、测试结论。

## 已测试模型

| 模型 | 视觉支持 | 13 任务结果 | 成本 | 备注 |
|------|----------|-------------|------|------|
| `qwen3.7-plus` | ✅ | 13/13 | ¥0.05 | 原生多模态，成本低 |
| `qwen3.7-max-2026-06-08` | ✅ | 13/13 | ¥0.26 | 0608 快照起支持视觉 |
| `qwen3.7-max`（无日期） | ❌ | 0/13 | ¥0 | 当前别名指向纯文本版本，不支持图片输入 |

## 测试任务清单

### 基础场景（8 个）
- `login_form`：登录表单
- `file_manager`：文件管理器
- `settings_dark_mode`：设置页开关
- `browser_search`：浏览器搜索
- `spreadsheet_sum`：电子表格
- `calendar_event`：日历新建事件
- `email_compose`：邮件撰写
- `ide_run`：IDE 运行脚本

### 高难度场景（4 个）
- `popup_blocking`：弹窗遮挡目标
- `error_message`：错误提示状态
- `scroll_needed`：目标在可视区域下方，需要滚动
- `notification_banner`：底部通知横幅

### 真实场景（1 个）
- `cnipa_login_captcha`：专利局登录页滑块验证码

## 如何接入真实 OSWorld 截图

官方 OSWorld-Verified 数据只提供任务元数据（snapshot + instruction + config），不直接附带初始截图。如果你想用真实 OSWorld 任务：

1. 在真实 OSWorld 环境中捕获每个任务的**初始状态截图**；
2. 将截图放到 `data/images/`；
3. 在 `data/tasks.json` 中添加对应条目，字段如下：

```json
{
  "id": "task-001",
  "instruction": "Open the Documents folder.",
  "image": "data/images/real_task_001.png",
  "domain": "file_manager",
  "expected_action": {
    "action": "double_click",
    "target": "Documents folder icon"
  }
}
```

## 成本预估

当前 13 个任务：

- `qwen3.7-plus`：约 ¥0.05
- `qwen3.7-max-2026-06-08`：约 ¥0.26
- `qwen3.7-max`：¥0（不支持视觉，直接报错）

扩展到 100 个真实 OSWorld 样本：

- `qwen3.7-plus`：约 ¥5–20
- `qwen3.7-max-2026-06-08`：约 ¥30–80（若仍处 5 折期则更低）

## 已知局限

1. **单步预测 ≠ 完整任务成功率**：只测模型能否给出合理的下一步，不验证后续执行是否正确。
2. **合成截图 ≠ 真实桌面**：demo 数据是合成的，仅用于快速跑通流程；真实结论需替换为 OSWorld 实际截图。
3. **无官方 Verified 子集元数据自动下载**：当前 demo 不依赖官方元数据，如需可扩展 `prepare_data.py` 拉取官方 `evaluation_examples`。
4. **`qwen3.7-max` 无视觉能力**：不带日期后缀的 `qwen3.7-max` 当前不接受 `image_url`，无法用于本测试。

## 输出示例

`run_eval.py` 会在控制台打印每个任务预测的动作，并写入 `results/{model}.json`：

```json
{
  "model": "qwen3.7-plus",
  "total_cost_usd": 0.01,
  "tasks": [
    {
      "id": "login_form",
      "instruction": "Log in with username 'user' and password 'pass'.",
      "predicted": {
        "action": "click",
        "target": "username input field",
        "coords": [500, 408],
        "reasoning": "Need to focus the username field first."
      }
    }
  ]
}
```
