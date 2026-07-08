# Model Salebook Agent — 设计规格

## Context

BD/SA 在推广百炼平台模型（Qwen3.7-Max/Plus、Wan2.7、DeepSeek 等）时，需要针对不同客户场景制定差异化销售策略。本 Agent 用第一性原理思维引导用户梳理客户情况，自动判断应走「技术碾压」「性价比」还是「田忌赛马」路线，最终输出定制化 HTML Salebook。

## 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| Agent 框架 | **LangGraph** | 结构化流水线 + HITL interrupt 原生支持 |
| LLM | Qwen3.7-Plus (DashScope) | 1M 上下文、成本低、OpenAI 兼容协议 |
| 本地知识 | 直读 knowledge/ markdown | 文件量小无需 RAG |
| 联网搜索 | DuckDuckGo（免费兜底） | 本地缺口自动补全 |
| Web UI | Gradio ChatInterface | 多轮 Chat + 文件下载 |
| HTML 输出 | 两阶段（LLM→JSON→Python 渲染） | 质量稳定、设计一致 |

## 工作流（LangGraph 状态图）

```
START → intake → interview ⇄ (多轮对话,不限轮次) → strategy → confirm → generate → review → END
              ↓                                          ↓                              ↓
        (加载本地知识                              (策略摘要+内容大纲                (不满意则
         + 识别缺口                                用户确认后再生成)                重新 generate)
         + 联网补全)
```

## 状态 Schema (`state.py`)

```python
class SalebookState(TypedDict, total=False):
    target_model: str               # 目标模型名（如 "Qwen3.7-Max", "Wan2.7"）
    # 对话收集
    customer_current_model: str     # 客户当前用的模型
    deal_type: str                  # "upsell" | "winback" | "new"
    customer_scenario: str          # 核心场景
    budget_sensitivity: str         # "high" | "medium" | "low"
    decision_driver: str            # "tech" | "business" | "mixed"
    interview_complete: bool
    chat_history: list              # 对话历史 [{"role", "content"}]
    # 策略结果
    strategy_type: str              # "tech_advantage" | "price_value" | "trojan_horse"
    strategy_rationale: str
    key_selling_points: list
    competitive_comparison: dict
    recommended_scenarios: list
    talking_points: list
    # 知识数据
    model_data: str                 # 本地 knowledge/ 模型文档原文
    sales_strategy: str             # 销售策略原文
    web_research: list              # 联网搜索结果 [{source, content, date}]
    data_gaps: list                 # 本地知识缺口描述
    # 生成输出
    salebook_json: dict             # LLM 生成的结构化内容 JSON
    html_content: str               # 渲染后的 HTML
    output_path: str                # 输出文件路径
    # 审核
    review_feedback: str            # 用户修改意见（空=通过）
```

## 节点设计

### intake (`nodes/intake.py`)
- 读取本地 `alibaba-ai-hub/maas/` 按模型名模糊匹配
- 加载 `notes/maas_sales_advice_ethan_2026.md` 销售策略
- 识别数据缺口 → 联网搜索 DuckDuckGo 补全

## interview (`nodes/interview.py`)
- **LLM 驱动的自由对话引导**（v1.2 改造）
- 像销售顾问聊天，自然语言问答，**非表单**
- 每轮调用 LLM，输入：system prompt + 已收集字段摘要 + 完整对话历史 + 用户最新输入
- LLM 输出严格 JSON：`{reply, extracted: {字段更新}, complete: bool}`
- **智能字段提取**：BD/SA 一句话可能透露多个字段（如"客户用 GPT-4o，预算紧，技术团队主导"→自动提取 3 个字段）
- **何时结束**：5 个核心维度齐了 → LLM 主动 complete=true；BD/SA 说"够了/done"→ 强制结束
- 5 个核心维度：customer_current_model / deal_type / customer_scenario / budget_sensitivity / decision_driver
- 对话历史保存在 `state.chat_history`（最多保留 40 条防止 token 过长）

### strategy (`nodes/strategy.py`)
- 注入完整知识 + 客户上下文 → LLM 输出策略 JSON
- 三条路径：tech_advantage / price_value / trojan_horse
- 田忌赛马逻辑：先用子场景优势做进去 → 等 3.8/4.0 升级

### generate (`nodes/generate.py`)
- 阶段1: LLM 生成结构化 JSON（hero/positioning/vs_competitors/scenarios/pricing/talking_points）
- 阶段2: `templates/components.py` 渲染为 HTML（暗色主题、卡片式布局）

### confirm (`nodes/confirm.py`) — 新增
- 在 generate 之前，展示：
  - 策略分析摘要（策略类型 + 原因 + 核心卖点）
  - Salebook 大纲（计划包含哪些章节 + 主要数据点）
- `interrupt()` 等待用户确认：
  - 'y' → 进入 generate
  - 修改意见 → 调整策略后重新生成大纲

### review (`nodes/review.py`)
- HTML 生成后，`interrupt()` 等待用户最终确认
- 输入 'y' → 结束；输入修改意见 → 重新 generate

## 知识获取策略

**本地优先 → 联网补全**

| 触发条件 | 搜索目标 |
|----------|----------|
| 竞品模型不在本地知识库 | 竞品 benchmark + 定价 |
| 本地数据超过 30 天 | 最新 benchmark |
| 场景无本地数据 | 场景 benchmark 对比 |
| 定价信息缺失 | 官方 pricing |

## 目录结构

```
model_salebook_agent/
├── main.py              # 终端入口
├── web.py               # Gradio Web UI (localhost:7860)
├── graph.py             # LangGraph 状态图
├── state.py             # 状态 Schema
├── config.py            # 配置管理（环境变量、路径动态推导）
├── nodes/
│   ├── intake.py        # 知识加载 + 联网补全
│   ├── interview.py     # 5问引导（interrupt）
│   ├── strategy.py      # 策略决策引擎
│   ├── generate.py      # HTML 两阶段生成
│   └── review.py        # 用户审核确认
├── tools/
│   ├── knowledge_reader.py  # 本地知识库读取
│   └── web_researcher.py    # DuckDuckGo 联网搜索
├── templates/
│   └── components.py    # HTML 组件渲染器（暗色主题 CSS）
├── prompts/
│   ├── interview_prompt.py
│   ├── strategy_prompt.py
│   └── generation_prompt.py
├── output/              # 生成的 HTML（.gitignore）
├── .venv/               # Python 虚拟环境
├── requirements.txt
├── .gitignore
├── SPEC.md              # ← 本文件
└── README.md
```

## 环境变量

| 变量 | 必须 | 默认值 | 说明 |
|------|------|--------|------|
| `DASHSCOPE_API_KEY_INTL` | 是 | — | DashScope 国际站 API Key |
| `DASHSCOPE_BASE_URL` | 否 | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | API 端点 |
| `SALEBOOK_MODEL` | 否 | `qwen3.7-plus` | 底层 LLM |
| `TAVILY_API_KEY` | 否 | — | 高质量搜索（不配则用 DuckDuckGo） |
| `KNOWLEDGE_BASE_PATH` | 否 | 自动推导 | knowledge/ 目录路径 |

## 运行方式

```bash
cd vibeCodingProject/model_salebook_agent
source .venv/bin/activate
export DASHSCOPE_API_KEY_INTL="sk-xxx"

# 终端模式
python main.py --model "Qwen3.7-Plus"

# Web 模式
python web.py   # → http://localhost:7860
```

## 支持的模型

本地有知识文档的（直接读取）：
- Qwen3.7-Max / Qwen3.7-Plus / Qwen3.6-Flash
- Wan2.7（视频生成）
- HappyHorse

本地无文档的（自动联网搜索）：
- 任意模型名（GPT-5.5、Claude Opus 4.8、DeepSeek-V4-Pro 等）

## HTML 设计系统

复用 `alibaba-ai-hub/maas/qwen3.7-max-salebook.html` 的视觉规范：
- 背景: `#0F1419`
- 卡片: `#1A1F2E`，圆角 16px
- 强调: 橙色渐变 `#FF6A00 → #EE0979`
- 字体: `-apple-system, PingFang SC`

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 框架 | LangGraph（非 Deep Agents） | 工作流结构化，HITL 原生支持，不需要子Agent |
| HTML 生成 | 两阶段（JSON→渲染） | LLM 直出 HTML 不稳定 |
| 联网搜索 | DuckDuckGo 免费方案 | 无需额外 API Key，零配置可用 |
| 知识匹配 | 文件名关键词模糊匹配 | 文件量小，无需向量检索 |
| 路径推导 | `Path(__file__).parent.parent.parent` | 不硬编码绝对路径 |
| LLM 调用模式 | strategy/generate 无状态；interview 累积对话历史 | strategy/generate 单次足够；interview 需上下文连贯 |
| 交互风格 | **自由对话式（chat）**，非表单 | BD/SA 反对强制问卷，需自然引导 |

## Token 管理策略

### 各节点调用情况

| 节点 | 输入 tokens | 说明 |
|------|------------|------|
| strategy | ~7,200 | model_data 全量注入，无状态 |
| generate | ~5,200 | model_data 截断到 8000 chars，无状态 |
| interview | ~2-15K（累积） | system + 已收集摘要 + chat_history（最多 40 条） |

### interview 历史控制（v1.2 起累积）

1. **结构化存储**：提取到的字段存 state 字段，不重复存 chat_history
2. **滑动窗口**：chat_history 注入 LLM 时只取最近 40 条（约 ~10K tokens）
3. **温度低 (0.4)**：减少 LLM 跑题导致的多轮发散
4. 远低于 1M 上限，正常使用 20+ 轮也无压力

## Changelog

| 日期 | 变更 |
|------|------|
| 2026-06-12 | **interview 改为 LLM 驱动的自由对话**（chat 式而非表单/问卷）；新增 chat_history 状态；prompt 重写为销售顾问角色；UI 优化（消息气泡+示例+新建会话按钮） |
| 2026-06-12 | interview 改为不限轮次（可追问）；新增 confirm 节点（生成前确认策略+大纲） |
| 2026-06-12 | 初始版本：LangGraph 5 节点状态图 + Gradio 双入口 + DuckDuckGo 联网 |
