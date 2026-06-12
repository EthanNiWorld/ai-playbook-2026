# Model Salebook Agent

基于 LangGraph 的模型销售指导文档生成 Agent。通过对话引导 BD/SA 梳理客户情况，自动判断应走「技术碾压」「性价比」还是「田忌赛马」路线，最终输出定制化 HTML Salebook。

## 工作流

```
输入模型名 → 加载知识(本地+联网) → 多轮引导问答(不限轮次) → 策略决策 → 确认大纲 → 生成HTML → 确认/修改
```

**三条策略路径**：
- `tech_advantage` — Benchmark 碾压，数据说话
- `price_value` — 性价比切入，同等能力更低成本
- `trojan_horse` — 田忌赛马，先做进去等模型升级

## 支持的模型

可为百炼平台上任何模型生成 Salebook：
- Qwen3.7-Max / Qwen3.7-Plus / Qwen3.6-Flash
- Wan2.7（视频生成）
- DeepSeek-V4-Flash/Pro
- 其他（本地无数据时自动联网搜索补全）

## 快速开始

```bash
cd vibeCodingProject/model_salebook_agent

# 1. 创建并激活虚拟环境（macOS Homebrew Python 必需）
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（在 ~/.zshrc 里添加后 source，或当前 shell 临时 export）
export DASHSCOPE_API_KEY_INTL="sk-xxx"

# 4a. 终端模式
python main.py --model "Qwen3.7-Plus"

# 4b. Web 模式
python web.py
# 浏览器打开 http://localhost:7860
```

> ⚠️ **踩坑提醒**：macOS Homebrew Python 受 PEP 668 保护，直接 `pip3 install` 会报 `externally-managed-environment` 错误。必须先 `source .venv/bin/activate` 进入虚拟环境。
>
> 不想每次激活？直接用 `.venv/bin/python web.py` 也可以。

## 环境变量

| 变量 | 必须 | 默认值 | 说明 |
|------|------|--------|------|
| `DASHSCOPE_API_KEY_INTL` | 是 | — | DashScope 国际站 API Key |
| `DASHSCOPE_BASE_URL` | 否 | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | API 端点 |
| `SALEBOOK_MODEL` | 否 | `qwen3.7-plus` | 底层 LLM 模型 |
| `TAVILY_API_KEY` | 否 | — | 联网搜索（不配则用 DuckDuckGo 免费方案） |

## 项目结构

```
model_salebook_agent/
├── main.py              # 终端入口
├── web.py               # Gradio Web UI
├── graph.py             # LangGraph 状态图
├── state.py             # 状态 Schema
├── config.py            # 配置管理
├── nodes/               # 图节点（intake/interview/strategy/generate/review）
├── tools/               # 工具（知识库读取 + 联网搜索）
├── templates/           # HTML 组件渲染器
├── prompts/             # 各节点 System Prompt
└── output/              # 生成的 HTML 文件
```

## 技术栈

- **Agent 框架**: LangGraph（状态图 + interrupt HITL）
- **LLM**: Qwen3.7-Plus via DashScope（OpenAI 兼容协议）
- **知识来源**: 本地 knowledge/ 优先 + DuckDuckGo 联网兜底
- **Web UI**: Gradio ChatInterface
- **HTML 输出**: 两阶段（LLM→JSON→Python 渲染）
