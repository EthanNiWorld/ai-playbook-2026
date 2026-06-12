# 知识库全局索引

> 本文件是知识库的全局索引，Skill 必读。
> 最后更新：2026-06-12

## 目录

- [🔍 快速查找](#-快速查找)
- [道：AI 领域知识（跨厂商）](#道ai-领域知识跨厂商)
- [点：单产品知识](#点单产品知识)
  - 云厂商：[阿里云](#阿里云) · [Google](#google)
  - 海外模型厂商：[Anthropic](#anthropic) · [OpenAI](#openai) · [Microsoft AI (MAI)](#microsoft-ai-mai)
  - 中国模型厂商：[DeepSeek](#deepseek深度求索) · [MiniMax](#minimax) · [智谱 AI](#智谱-aizhipu) · [月之暗面](#月之暗面moonshot-ai) · [腾讯混元](#腾讯混元tencent-hunyuan)
- [线：对比分析（阿里云视角）](#线对比分析阿里云视角)
- [体：行业解决方案](#体行业解决方案)
- [模板参考](#模板参考)

---

## 🔍 快速查找

按关键词或问题快速定位文档（⭐ 表示高频文档）：

| 我想找… | 文档 |
|---------|------|
| Qwen / 通义千问 / 3.7-Plus / 3.7-Max / 旗舰 | [Qwen](knowledge/alibaba/maas/qwen.md) |
| 万相 / Wan / 视频生成 / 图生视频 | [万相](knowledge/alibaba/maas/wan.md) |
| HappyHorse / 快乐小马 / 图像生成 | [HappyHorse](knowledge/alibaba/maas/happyhorse.md) |
| 百炼平台 / 多账号 / TPM 扩量 / 限流 | [百炼平台](knowledge/alibaba/maas/overview.md) |
| Qoder / AI 编程 / IDE 插件 | [Qoder](knowledge/alibaba/ai-coding/qoder.md) |
| QoderWork / 桌面助手 / 本地 Agent | [QoderWork](knowledge/alibaba/ai-application/qoder-work.md) |
| MuleRun / 骡子快跑 / 云端 Agent / vs QoderWork | [MuleRun](knowledge/alibaba/ai-application/mulerun.md) |
| GPU 选型 / A100 / H100 / H20 | [GPU 选型决策树](knowledge/alibaba/ai-infra/gpu-product-line.md) ⭐ |
| 灵骏 / 智算集群 / EFLOPS | 待补充 |
| Agent 定义 / Harness / 治理层 | [Agent](knowledge/ai-general-notes/agent-def.md) ⭐ · [Harness](knowledge/ai-general-notes/harness.md) ⭐ |
| Agent 框架 / LangChain / LangGraph / Deep Agents | [Agent 框架](knowledge/ai-general-notes/agent-frameworks.md) |
| AI 记忆 / Memory / Dreaming | [AI Agent 记忆](knowledge/ai-general-notes/agent-memory.md) ⭐ |
| AI 公司增长 / ARR / 飞轮 | [AI 增长飞轮](knowledge/ai-general-notes/ai-company-growth-flywheel.md) ⭐ |
| Prompt 工程 / 防幻觉 | [Prompt Engineering](knowledge/ai-general-notes/prompt-engineering.md) ⭐ |
| Claude / Opus 4.8 / Sonnet / Haiku | [Claude API](knowledge/anthropic/claude-api.md) |
| Claude Code / 竞品 | [Claude Code](knowledge/anthropic/claude-code.md) |
| Gemini / Google | [Gemini](knowledge/google/maas/gemini.md) |
| GPT-5 / ChatGPT / OpenAI / Codex | [GPT-5 系列](knowledge/openai/gpt-5-series.md) · [Codex](knowledge/openai/codex.md) |
| MAI / 微软自研 / Copilot 模型 | [MAI 模型家族](knowledge/microsoft/mai-models.md) |
| DeepSeek / R1 / V4 / 开源 | [DeepSeek](knowledge/deepseek/general_intro.md) ⭐ |
| Hy3-preview / 腾讯混元 / Hunyuan | [Hy3-preview](knowledge/tencent/hy3-preview.md) |
| Qwen vs Hy3 / 混元竞争分析 | [Qwen3.7 vs Hy3-preview](knowledge/alibaba/competitive-analysis/qwen-vs-hy3/overview.md) |
| MiniMax / M3 / 海螺 AI | [M 系列](knowledge/minimax/minimax-series.md) |
| Kimi / 月之暗面 / Moonshot / K2.6 | [Kimi K 系列](knowledge/moonshot/kimi-k-series.md) |
| GLM / 智谱 / 长程任务 | [GLM 系列](knowledge/zhipu/glm-series.md) |
| 企业自建推理 / Higress / AI 网关 | [企业自建 AI 推理平台](knowledge/solutions/enterprise-ai-platform/overview.md) ⭐ |
| 数据出境 / 数据主权 / CN 版 | [MuleRun](knowledge/alibaba/ai-application/mulerun.md#mulerun全球版与骡子快跑中国版的关系) · [QoderWork](knowledge/alibaba/ai-application/qoder-work.md) |

---

## 道：AI 领域知识（跨厂商）

### 技术概念类（关键选型维度）

- [Agent](knowledge/ai-general-notes/agent-def.md) ⭐ — for 循环本质、Model+Harness 框架、Agent 平台战略拐点、OpenAI 三大优先级
- [Harness](knowledge/ai-general-notes/harness.md) ⭐ — 企业战略级资产、约束治理层、Harness vs Prompt 区别、调用层容量与限流治理、Agent=Model+Harness 公式演进史、Model-Harness 协同演进厂商对比
- [Agent 框架](knowledge/ai-general-notes/agent-frameworks.md) — LangChain / LangGraph / Deep Agents 三层递进架构、选型决策树、与闭源 Deep Agent 产品关系
- [Prompt Engineering](knowledge/ai-general-notes/prompt-engineering.md) ⭐ — 防幻觉四层机制、第一性原理、博弈论应用

### 概念洞察类（关键认知框架）

- [AI 能力边界与迭代部署](knowledge/ai-general-notes/ai-capability-and-deployment.md) ⭐ — 锯齿状能力边界、迭代部署哲学、Personal AGI 终局
- [模型自我进化](knowledge/ai-general-notes/agent-self-evolution.md) ⭐ — 模型自驱动训练、打破人工瓶颈、100+ 轮自主迭代带来 30% 效果提升
- [AI Agent 记忆系统](knowledge/ai-general-notes/agent-memory.md) ⭐ — ChatGPT Dreaming V3、人脑记忆工程同构、个性化护城河
- [AI 公司增长飞轮](knowledge/ai-general-notes/ai-company-growth-flywheel.md) ⭐ — Killer App × 企业信任 × 消费制收入，Anthropic 17 个月 47 倍

---

## 点：单产品知识

> 分组顺序：**云厂商**（阿里云 / Google）→ **海外模型厂商** → **中国模型厂商**。

### 阿里云

**MaaS**
- [百炼平台](knowledge/alibaba/maas/overview.md) — UID 级限流、多账号扩 TPM（8.5× 实测）、deepseek-v4-flash 压测
- [Qwen](knowledge/alibaba/maas/qwen.md) — 3.7-Max / 3.7-Plus / 3.6、定价、benchmark
- [万相](knowledge/alibaba/maas/wan.md) — 视频生成、首尾帧
- [HappyHorse](knowledge/alibaba/maas/happyhorse.md) — 图像生成

**AI Coding**
- [Qoder](knowledge/alibaba/ai-coding/qoder.md) — IDE 插件、AI 编程

**AI App**
- [QoderWork](knowledge/alibaba/ai-application/qoder-work.md) — 桌面 Agent、本地
- [MuleRun](knowledge/alibaba/ai-application/mulerun.md) — 云端 Agent、Always-On
- [龙虾家族](knowledge/alibaba/ai-application/claw-family.md)
- [JVS Crew](knowledge/alibaba/ai-application/jvs-crew.md)

**AI Infra**
- [GPU 产品线选型](knowledge/alibaba/ai-infra/gpu-product-line.md) ⭐ — A100/H100/H20 选型决策树

### Google

**MaaS**
- [Gemini Enterprise Agent Platform](knowledge/google/maas/overview.md)
- [Gemini](knowledge/google/maas/gemini.md) — 3.1 Pro（当前旗舰） / 3.5 Flash（Agent/Coding 性价比率先，含 benchmark 对比）

**AI Platform**
- [Vertex AI → Agent Platform](knowledge/google/ai-platform/vertex-ai.md) — 训练/部署/Agent

### Anthropic

- 公司分析: [Anthropic 公司分析](knowledge/anthropic/general_intro.md) — PBC 治理、Scaling Laws 团队、Claude 家族、ARR $2B+（2026.04）
- MaaS: [Claude API](knowledge/anthropic/claude-api.md) — Opus 4.8（SWE-Bench Pro 69.2%）/ Sonnet 4.6 / Haiku 4
- AI Coding: [Claude Code](knowledge/anthropic/claude-code.md) — 终端 AI 编程
- AI App: [Claude Cowork](knowledge/anthropic/claude-cowork.md) — 桌面通用知识工作 Agent · [Claude Managed Agents](knowledge/anthropic/claude-managed-agents.md)

### OpenAI

- 公司分析: [OpenAI 公司分析](knowledge/openai/general_intro.md) — GPT-5 系列、ChatGPT、Native Computer Use
- 模型系列: [GPT-5 系列](knowledge/openai/gpt-5-series.md) — GPT-5 / 5.2 / 5.3 / 5.4 / 5.5
- AI Coding: [Codex](knowledge/openai/codex.md) — 多形态 AI 编程 Agent 平台（CLI/IDE/Web/桌面），多 Agent 编排

### Microsoft AI (MAI)

- 模型家族: [MAI 模型家族](knowledge/microsoft/mai-models.md) — Build 2026 首发 7 款自研模型：🚩 MAI-Thinking-1（推理旗舰，35B 激活/~1T 总参，AIME 2026 94.5%）/ MAI-Code-1-Flash（5B 激活，GitHub Copilot 原生集成）/ Image-2.5 / Transcribe-1.5 / Voice-2

### DeepSeek（深度求索）

- 公司分析: [DeepSeek 公司分析](knowledge/deepseek/general_intro.md) ⭐ — MLA+MoE 架构创新、R1 纯 RL 推理、V4 开源 SOTA、557 万美元训练成本、"DeepSeek 时刻"、**Harness 团队组建（2026-05，对标 Claude Code）**
- 模型系列:
  - [V 系列](knowledge/deepseek/deepseek-v-series.md) — V1 / V2 / V3 / V3.2 / V4
  - [R 系列](knowledge/deepseek/deepseek-r-series.md) — R1 / R1-0528 / R2

### MiniMax

- 公司分析: [MiniMax 公司分析](knowledge/minimax/general_intro.md) — 2026.01 港股 IPO（00100.HK）、海螺 AI / Talkie 全球化、M1/M2/M2.7 开源混合注意力，**M2.7 自我进化（模型自驱动训练）**
- 模型系列: [M 系列](knowledge/minimax/minimax-series.md) — M1 / M2 / M2.7 / M3（**M3 已开源权重**，MSA 稀疏注意力、原生多模态）
- Agent: [Agent Team](knowledge/minimax/agent-team.md) — Leader–Worker–Verifier 对抗制衡多 Agent 协作系统

### 智谱 AI（Zhipu）

- 公司分析: [智谱 AI 公司分析](knowledge/zhipu/general_intro.md) — 2026.01 港股 IPO（02513.HK，全球大模型第一股）、GLM-5 编程开源 SOTA、MaaS ARR 17 亿元
- 模型系列: [GLM 系列](knowledge/zhipu/glm-series.md) — GLM-4 / 4.5 / 4.6 / 5 / 5.1，**GLM-5.1 主推 8 小时级长程任务**

### 月之暗面（Moonshot AI）

- 公司分析: [月之暗面公司分析](knowledge/moonshot/general_intro.md) — 2023 成立、估值 >$200 亿、累计融资超 376 亿元、ARR >$2 亿
- 模型系列: [Kimi K 系列](knowledge/moonshot/kimi-k-series.md) — K2 / K2.5 / K2.6，**K2.6 Agent Swarm（300 子 Agent）、13 小时长周期编码**

### 腾讯混元（Tencent Hunyuan）

- 模型: [Hy3-preview](knowledge/tencent/hy3-preview.md) — 295B MoE/21B 激活，OpenRouter 工具调用 #1，SWE-bench 74.4%，开源可自部署，价格碾压

---

## 线：对比分析（阿里云视角）

- [Qoder vs Trae](knowledge/alibaba/competitive-analysis/qoder-vs-trae/overview.md) ⭐ — 企业级 vs 个人开发者定位差异
- [Qwen3.7 vs Hy3-preview](knowledge/alibaba/competitive-analysis/qwen-vs-hy3/overview.md) — 1M上下文+深度编码+多模态 vs 性价比+开源部署，SA 打法建议

---

## 体：行业解决方案

- [IPC 智能安防](knowledge/solutions/vertical-ipc/overview.md) — 视频监控、AI 质检
- [短剧出海](knowledge/solutions/vertical-short-drama/overview.md) — Qwen3.7-Plus 原生 VL 视频理解 + 16 语言内容生成 + OpenSearch SEO，30 天 156 万条
- [商业地产](knowledge/solutions/commercial-real-estate/overview.md) — AI 质检、合同审查、知识库、智能客服、Qoder 提效
- [企业自建 AI 推理平台](knowledge/solutions/enterprise-ai-platform/overview.md) ⭐ — Higress AI 网关 + 灵骏 GPU + 百炼 Fallback；含 AWS 迁移案例

---

## 模板参考

- [AI 通用笔记模板](knowledge/ai-general-notes/_template.md)
- [MaaS 产品模板](knowledge/_maas_template.md)
- [产品模板](knowledge/_product_template.md)
- [对比分析模板](knowledge/alibaba/competitive-analysis/_template.md)
- [内部产品对比模板](knowledge/_internal-comparison_template.md)
- [解决方案模板](knowledge/solutions/_template.md)
