# Kimi K 系列模型

> 最后更新: 2026-06-29
> 所属厂商: 月之暗面（Moonshot AI）
> 产品类别: MaaS

<!-- SUMMARY_START -->
**定位**: 开源 Agent 模型系列，聚焦编码、长周期执行与多 Agent 协作
**当前主推**: Kimi K2.7-Code（编码旗舰）/ Kimi K2.6（通用旗舰）
**适用**: AI 编码助手、Agent 应用、多 Agent 系统、自动化工作流
**不适用**: 轻量级对话、纯文本生成（性价比不如 Qwen/GPT 系列）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| 🚩 **Kimi K2.7-Code** | 编码旗舰 | 256K | 基于 K2.6 的编码专精模型，推理 token 减少 30%，长程软件工程优化 | 2026-06-12 |
| **Kimi K2.6** | 通用旗舰 | 256K | 原生多模态、13 小时长周期编码、Agent Swarm（300 子 Agent） | 2026-04-20 |

> 📌 **历史模型**：Kimi K2.5（2026-01-27）仍可调用，但已被 K2.6 取代，不建议新项目选用。Kimi K2（2025-07-11）已于 2026-05-25 正式下线。

## 模型演进

### Kimi K2.7-Code（2026 年 6 月，编码旗舰）

- **架构**：开源 MoE，1T 总参 / 32B 激活参数（基于 K2.6 架构）[来源: totalum.app / OpenRouter]
- **上下文**：256K tokens
- **定位**：以编码为中心的智能体模型，专为长程软件工程任务优化 [来源: help.aliyun.com]
- **核心改进**（vs K2.6）：
  - 推理 token 用量减少约 30%（效率显著提升）[来源: MarkTechPost]
  - Kimi Code Bench v2 得分 +21.8% [来源: MarkTechPost / Instagram]
  - SWE-bench Verified 60.4%（开源模型最高）[来源: OpenRouter]
  - 擅长跨多文件重构、功能实现、长会话调试等复杂工作流 [来源: help.aliyun.com]
- **变体**：
  - `kimi/kimi-k2.7-code`（2026-06-15 百炼上线）：**仅支持思考模式**（不支持非思考模式，关闭思考会报错），temperature 固定 1.0
  - `kimi/kimi-k2.7-code-highspeed`（2026-06-18 百炼上线）：功能完全一致，速度提升 5-6 倍，输出约 180 Token/s [来源: help.aliyun.com / platform.kimi.com]
- **开源**：HuggingFace（moonshotai/Kimi-K2.7-Code），open-weight
- **场景差异 vs K2.6**：K2.7-Code 专注编码 Agent，**支持多模态视觉**（图片 + 视频理解，格式支持 png/jpeg/webp/gif/mp4 等）；K2.6 仍为通用旗舰（含视觉 + Agent Swarm）。两者均支持视觉，但 K2.7-Code 仅支持思考模式 [来源: platform.kimi.com]

### Kimi K2.6（2026 年 4 月，通用旗舰）

- **架构**：原生多模态 MoE（延续 K2.5 架构）
- **上下文**：256K tokens
- **核心突破**：
  - **长周期编码**：支持连续编码长达 13 小时，4,000+ 工具调用
  - **Agent Swarm 升级**：从 K2.5 的 100 子 Agent / 1,500 步扩展到 300 子 Agent / 4,000 协调步骤
  - **编码驱动设计（Coding-Driven Design）**：从单提示生成完整前端界面
  - **主动 Agent（Proactive Agents）**：支持 24/7 持续运行的自主 Agent
  - **Claw Groups**（研究预览）：异构多 Agent + 人类协作的新架构
  - **Skills 系统**：将 PDF/幻灯片/文档转化为可复用技能
- **百炼平台接入**：模型 ID `kimi/kimi-k2.6`，通过阿里云 DashScope API 调用
- **缓存折扣**：命中缓存按输入价格的 16.9% 计费

### Kimi K2.5（2026 年 1 月）

- **架构升级**：原生多模态 MoE（文本 + 视觉）
- **参数**：1T 总参 / 32B 激活（同 K2）
- **视觉编码器**：MoonViT
- **上下文**：256K tokens（K2 的 2 倍）
- **继续预训练**：约 15T 混合视觉与文本 tokens
- **新能力**：
  - Agent Swarm（研究预览）：最多 100 个子 Agent 并发协作
  - 原生图像/视频理解
  - 思考模式（enable_thinking）
- **API 定价**：输入 $0.60/M tokens（缓存命中 $0.10/M），输出 $3.00/M tokens
- **开源**：HuggingFace，Modified MIT License

### Kimi K2（2025 年 7 月）

- **架构**：MoE（Mixture-of-Experts）
- **总参数**：1T（万亿）
- **激活参数**：32B（每 token）
- **层数**：61 层（含 1 层 Dense）
- **专家数**：384 个，每 token 路由至 8 个 + 1 个共享专家
- **注意力**：MLA（Multi-head Latent Attention），Hidden Dim 7168，64 头
- **MoE Hidden Dim**：每专家 2048
- **激活函数**：SwiGLU
- **词表**：160K
- **上下文**：128K tokens
- **训练数据**：15.5T tokens
- **优化器**：Muon（首次在超大规模 MoE 成功应用）
- **变体**：K2-Base（基础模型）、K2-Instruct（指令微调模型）
- **开源**：HuggingFace，Modified MIT License
- **状态**：已于 2026-05-25 下线

## Benchmark 对比（K2.6 vs 主流模型）

| Benchmark | Kimi K2.6 | GPT-5.4 (xhigh) | Claude Opus 4.6 (max) | Gemini 3.1 Pro (high) | Kimi K2.5 |
|-----------|-----------|------------------|----------------------|----------------------|-----------|
| **Agent** |  |  |  |  |  |
| HLE-Full w/ tools | **54.0** | 52.1 | 53.0 | 51.4 | 50.2 |
| BrowseComp (swarm) | **86.3** | — | — | — | 78.4 |
| DeepSearchQA (f1) | **92.5** | 78.6 | 91.3 | 81.9 | 89.0 |
| Toolathlon | 50.0 | **54.6** | 47.2 | 48.8 | 27.8 |
| OSWorld-Verified | 73.1 | **75.0** | 72.7 | — | 63.3 |
| **编码** |  |  |  |  |  |
| Terminal-Bench 2.0 | 66.7 | 65.4 | 65.4 | **68.5** | 50.8 |
| SWE-Bench Pro | **58.6** | 57.7 | 53.4 | 54.2 | 50.7 |
| SWE-Bench Verified | 80.2 | — | 80.8 | **80.6** | 76.8 |
| **推理** |  |  |  |  |  |
| AIME 2026 | 96.4 | **99.2** | 96.7 | 98.3 | 95.8 |
| GPQA-Diamond | 90.5 | 92.8 | 91.3 | **94.3** | 87.6 |
| **视觉** |  |  |  |  |  |
| MathVision w/ python | 93.2 | **96.1** | 84.6 | 95.7 | 85.0 |
| V* w/ python | **96.9** | 98.4 | 86.4 | 96.9 | 86.9 |

> K2.6 在 Agent、编码（尤其 SWE-Bench Pro）和 DeepSearchQA 上达到开源 SOTA，与 GPT-5.4、Claude Opus 4.6、Gemini 3.1 Pro 等闭源旗舰模型处于同一梯队。

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 长周期编码 | 13 小时连续编码，1,000+ 工具调用，跨语言（Rust/Go/Zig/Python） |
| Agent Swarm | 300 子 Agent 并发协作，4,000 协调步骤 |
| 原生多模态 | 文本 + 图像 + 视频理解（MoonViT） |
| 思考模式 | K2.6 可开关（enable_thinking）；**K2.7-Code 仅支持思考模式**（不支持关闭，temperature 固定 1.0） |
| Tool Calling | 原生工具调用，支持 MCP 协议 |
| 编码驱动设计 | 从提示生成完整前端 + 全栈应用 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 上下文 | 256K tokens | 不如 Qwen 系列的 1M 上下文 |
| 推理/数学 | 略弱于 GPT-5.4 | AIME 96.4 vs 99.2，HMMT 92.7 vs 97.7 |
| 视觉理解 | 略弱于 Gemini 3.1 Pro | MMMU-Pro 79.4 vs 83.0 |
| 不支持 | 联网搜索 | 百炼平台暂不支持联网搜索功能 |

## 百炼平台接入

通过阿里云百炼调用 Kimi K2.6：

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    model="kimi/kimi-k2.6",
    messages=[{"role": "user", "content": "你好"}],
    extra_body={"enable_thinking": True}  # 可选：开启思考模式
)
```

**支持功能**：多轮对话、Function Calling、前缀续写、上下文缓存（隐式缓存自动开启）、结构化输出。

**不支持**：联网搜索、thinking_budget 限制思考长度；K2.7-Code 额外不支持关闭思考模式（thinking: disabled 会报错）。

**参数默认值**：K2.6 思考模式 temperature=1.0、非思考模式 temperature=0.6、top_p=0.95；K2.7-Code 仅思考模式，temperature 固定 1.0、top_p 固定 0.95，不可调整。

## 推理部署

Kimi K2 系列模型权重开源（block-fp8 格式），推荐推理引擎：

- **vLLM** — 主流开源推理引擎
- **SGLang** — 高效推理框架
- **KTransformers** — MoE 优化推理
- **TensorRT-LLM** — NVIDIA 推理加速

> 模型文件大小约 595GB，需要多卡 GPU 集群部署。

## 关键技术论文

| 论文 | 时间 | 核心贡献 |
|------|------|----------|
| Kimi K2: Open Agentic Intelligence | 2025-07 | MoE 1T 架构、Muon 优化器、Agent 能力优化 |
| Agent Swarm | 2026-02 | 多 Agent 并发协作架构 |
| WorldVQA | 2026-02 | 视觉质量评估 |

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-29 | 修正：K2.7-Code 支持多模态视觉（图片+视频），明确仅支持思考模式（不支持关闭）；模型演进调整为时间倒序（K2.7-Code → K2.6 → K2.5 → K2）[来源: platform.kimi.com] |
| 2026-06-22 | 合并：百炼上新架与外部报道 — 新增 Kimi K2.7-Code 编码旗舰（2026-06-12 发布，百炼 06-15 上架），含 Benchmark、架构、Highspeed 变体 |
| 2026-06-07 | 新建：覆盖 K2/K2.5/K2.6 全系列模型知识 |

## 参考资料

- [Kimi K2.6 技术博客](https://www.kimi.com/blog/kimi-k2-6)
- [GitHub: moonshotai/kimi-k2](https://github.com/moonshotai/kimi-k2)
- [Kimi API 平台模型列表](https://platform.kimi.ai/docs/models)
- [Kimi K2.7 Code 快速开始（官方文档）](https://platform.kimi.com/docs/guide/kimi-k2-7-code-quickstart)
- [阿里云百炼 Kimi 文档](https://help.aliyun.com/zh/model-studio/kimi-api-by-moonshot-ai)
- [ModelScope: Kimi-K2.6](https://www.modelscope.cn/models/moonshotai/Kimi-K2.6)
