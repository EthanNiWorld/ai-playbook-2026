# Kimi K 系列模型

> 最后更新: 2026-07-17
> 所属厂商: 月之暗面（Moonshot AI）
> 产品类别: MaaS

<!-- SUMMARY_START -->
**定位**: 开源 Agent 模型系列，聚焦长程编码、端到端知识工作与多 Agent 协作
**当前主推**: Kimi K3（旗舰，2.8T / 1M 上下文）/ Kimi K2.7-Code（编码专精）/ Kimi K2.6（长程 Agent）
**适用**: AI 编码助手、Agent 应用、多 Agent 系统、自动化工作流、超长上下文知识工作
**不适用**: 轻量级对话、纯文本生成（性价比不如 Qwen/GPT 系列）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| 🚩 **Kimi K3** | 旗舰 | 1M | 2.8T MoE（896 专家/激活 16）、KDA 线性注意力、原生多模态、始终 max 思考 | 2026-07-17 |
| **Kimi K2.7-Code** | 编码专精 | 256K | 基于 K2.6 的编码专精模型，推理 token 减少 30%，长程软件工程优化 | 2026-06-12 |
| **Kimi K2.6** | 长程 Agent | 256K | 原生多模态、13 小时长周期编码、Agent Swarm（300 子 Agent），价位低于 K3 | 2026-04-20 |

> 📌 **产品分层**：K3 为高端旗舰（始终 max 思考、旗舰定价 $3/$15）；K2.7-Code 守 IDE 快速编码循环；K2.6 守低价长程 Agent。K3 发布不取代 K2.7-Code / K2.6，三者按场景分流。
> 📌 **历史模型**：Kimi K2.5（2026-01-27）仍可调用，但已被 K2.6 取代，不建议新项目选用。Kimi K2（2025-07-11）已于 2026-05-25 正式下线。

## 模型演进

### Kimi K3（2026 年 7 月，旗舰）

- **架构**：2.8T MoE，896 专家 / 每 token 激活 16（稀疏度 1.8%），Stable LatentMoE 框架 [来源: platform.kimi.com]
- **注意力创新**：KDA（Kimi Delta Attention）混合线性注意力 + Attention Residuals（AttnRes）[来源: platform.kimi.com]
  - KDA：将长上下文历史压缩为紧凑记忆状态，新 token 只关注 Delta 变化；百万 token 场景解码提速 6.3 倍
  - AttnRes：注意力跨层残差连接，训练效率 +25%，额外成本 <2%
  - 整体扩展效率 vs K2 提升约 2.5 倍
- **上下文**：1M（1,048,576 tokens）
- **多模态**：原生文本 + 图像 + 视频；Moonshot 官方 API 视觉输入仅支持 base64 / `ms://` 文件 ID（不支持公网图片 URL）
- **思考模式**：始终开启，`reasoning_effort` 当前仅 `max` 档；temperature=1.0 / top_p=0.95 固定
- **输出**：max_completion_tokens 默认 131,072，最大 1,048,576
- **量化**：MXFP4 权重 + MXFP8 激活（SFT 阶段起量化感知训练）
- **开源**：全球首个 2.8T 级开源模型（官方宣传口径称"3 万亿级别"，精确值为 2.8T），权重 2026-07-27 前发布，Modified MIT
- **部署**：官方建议 64 加速器超级节点，个人/小团队本地不可跑
- **API**：模型 ID `kimi-k3`；`https://api.moonshot.cn/v1`（国内）/ `https://api.moonshot.ai/v1`（国际）
- **定价**：缓存命中 $0.30 / 输入 $3.00 / 输出 $15.00（每 M tokens）；Mooncake 分离式推理架构下编程任务缓存命中率 >90%
- **限制**：始终思考无法关闭（轻量任务成本高）；联网搜索工具更新中，近期不建议生产使用
- **百炼接入**：模型 ID `kimi/kimi-k3`（仅华北2/北京地域 Key）；MaaS 专属端点上为 `kimi-k3`（无前缀）。实测（2026-08-24，三个 MaaS 端点：北京 workspace×2 + 新加坡节点，结论一致）：图片输入 base64 与公网 URL 均可用；**视频输入不支持**（报 400 "Video inputs are not supported by this model"，字符串/嵌套格式/含 fps 均被拒），同端点 qwen3.8-max / qwen-vl-max 及 **kimi-k2.6 / kimi-k2.7-code 视频均正常** → 系百炼 kimi-k3 部署专属限制（非 kimi 系列整体问题），客户需 kimi + 视频理解时引导用 kimi-k2.6 / kimi-k2.7-code。测试脚本：`alibaba-ai-hub/maas/api-sample/test_kimi_k3_multimodal.py`

### Kimi K2.7-Code（2026 年 6 月，编码专精）

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

### Kimi K2.6（2026 年 4 月，长程 Agent）

- **架构**：原生多模态 MoE（延续 K2.5 架构）
- **上下文**：256K tokens
- **核心突破**：
  - **长周期编码**：支持连续编码长达 13 小时，4,000+ 工具调用
  - **Agent Swarm 升级**：从 K2.5 的 100 子 Agent / 1,500 步扩展到 300 子 Agent / 4,000 协调步骤
  - **编码驱动设计（Coding-Driven Design）**：从单提示生成完整前端界面
  - **主动 Agent（Proactive Agents）**：支持 24/7 持续运行的自主 Agent
  - **Claw Groups**（研究预览）：异构多 Agent + 人类协作的新架构
  - **Skills 系统**：将 PDF/幻灯片/文档转化为可复用技能
- **百炼平台接入**：模型 ID `kimi/kimi-k2.6`（标准端点）/ `kimi-k2.6`（MaaS 专属端点），通过阿里云 DashScope API 调用
- **百炼视频实测**（2026-08-24）：视频输入可用，嵌套格式 `{"video_url": {"url": ...}}`（含 fps 参数）与 qwen 风格字符串格式均通过；需 kimi + 视频理解时首选 k2.6（kimi-k3 视频不可用）
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

## Benchmark 对比

### Kimi K3（2026-07-17 发布）

| Benchmark | Kimi K3 | 对比参照 | 来源 |
|-----------|---------|----------|------|
| Terminal-Bench v2.1（独立复测） | **85.0%**，总榜第 6（前 5 均为 GPT-5.6 变体），**非 OpenAI 模型第 1** | Claude Opus 4.8 (max) 84.6%、Claude Fable 5 84.6%、GPT-5.5 (xhigh) 84.3%；榜首 GPT-5.6 Sol (xhigh) 89.5%；K2.6 为 65.9% | Artificial Analysis |
| Terminal-Bench 2.1（官方口径） | 88.3 | ⚠️ 与独立复测存在口径差，对外引用建议用独立数据 | kimi.com/blog/kimi-k3 |
| GDPval-AA v2（Elo，独立评测） | **1668**，全球第 3 | Claude Fable 5 1750、GPT-5.6 Sol (max) 1743；Claude Sonnet 5 (max) 1607；K2.6 为 1191 | Artificial Analysis |
| Intelligence Index（综合） | 57，第 3 | 与 Opus 4.8 / GPT-5.5 同档，落后 GPT-5.6 一档 | Artificial Analysis |
| Frontend Code Arena（Elo） | **1679，#1** | Claude Fable 5 1631；K2.6 由第 18 名跃升 17 位 | arena.ai |
| FrontierSWE（方案规划型） | 81.2 | Claude Fable 5 86.6 / GPT-5.6 Sol 71.3 | 官方技术博客 |
| DeepSWE（精准执行型） | 67.3 | mini-SWE-agent harness | 官方技术博客 |

> K3 代际跃升最大维度：Terminal-Bench +19.1pt、GDPval +477 Elo（均 vs K2.6）。SWE-bench Verified / LiveCodeBench / Tau2 / AIME 官方称"开源领先"，具体分数待 2026-07-27 技术报告 [⚠️ 待补充]。

### Kimi K2.6 vs 主流模型

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
| 超长上下文 | K3 支持 1M tokens（1,048,576）；K2.x 为 256K |
| 长周期编码 | 13 小时连续编码，1,000+ 工具调用，跨语言（Rust/Go/Zig/Python） |
| Agent Swarm | 300 子 Agent 并发协作，4,000 协调步骤 |
| 原生多模态 | 文本 + 图像 + 视频理解（MoonViT） |
| 思考模式 | K2.6 可开关（enable_thinking）；**K2.7-Code 仅支持思考模式**（不支持关闭，temperature 固定 1.0） |
| Tool Calling | 原生工具调用，支持 MCP 协议 |
| 编码驱动设计 | 从提示生成完整前端 + 全栈应用 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 上下文 | K2.x 为 256K tokens | K3 已达 1M；K2.x 不如 Qwen 系列的 1M 上下文 |
| K3 思考模式 | 无法关闭 | 始终 max 档，轻量任务成本高 |
| K3 联网搜索 | 更新中 | 近期不建议用于生产流程 |
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
|------|---------|
| 2026-08-24 | 实测补全：K3 百炼 MaaS 端点多模态实测（北京 workspace×2 + 新加坡节点三端点交叉验证）——k3 图片 base64/URL 均可用、视频不支持（400 报错）；同端点 kimi-k2.6 / kimi-k2.7-code 视频正常，确认系 k3 专属限制；补全 K3/K2.6 百炼接入信息；新增测试脚本 test_kimi_k3_multimodal.py |
| 2026-07-17 | 合并：inbox K3 调研素材 — 新增 Kimi K3 章节（2.8T/1M/KDA/AttnRes），主推更新为 K3，新增 K3 Benchmark 表（AA 独立评测与官方口径分列），K2.6 定位调整为长程 Agent，K2.7-Code 调整为编码专精 |
| 2026-06-29 | 修正：K2.7-Code 支持多模态视觉（图片+视频），明确仅支持思考模式（不支持关闭）；模型演进调整为时间倒序（K2.7-Code → K2.6 → K2.5 → K2）[来源: platform.kimi.com] |
| 2026-06-22 | 合并：百炼上新架与外部报道 — 新增 Kimi K2.7-Code 编码旗舰（2026-06-12 发布，百炼 06-15 上架），含 Benchmark、架构、Highspeed 变体 |
| 2026-06-07 | 新建：覆盖 K2/K2.5/K2.6 全系列模型知识 |

## 参考资料

- [Kimi K3 Quickstart（官方文档）](https://platform.kimi.com/docs/guide/kimi-k3-quickstart)
- [Kimi K3 技术博客](https://www.kimi.com/blog/kimi-k3)
- [Kimi K2.6 技术博客](https://www.kimi.com/blog/kimi-k2-6)
- [GitHub: moonshotai/kimi-k2](https://github.com/moonshotai/kimi-k2)
- [Kimi API 平台模型列表](https://platform.kimi.ai/docs/models)
- [Kimi K2.7 Code 快速开始（官方文档）](https://platform.kimi.com/docs/guide/kimi-k2-7-code-quickstart)
- [阿里云百炼 Kimi 文档](https://help.aliyun.com/zh/model-studio/kimi-api-by-moonshot-ai)
- [ModelScope: Kimi-K2.6](https://www.modelscope.cn/models/moonshotai/Kimi-K2.6)
