# 知识库全局索引

> 本文件是知识库的全局索引，Skill 必读。
> 最后更新：2026-06-04

## 🔍 快速查找

按关键词或问题快速定位文档：

| 我想找… | 文档 |
|---------|------|
| Qwen 定价 / 模型对比 / benchmark | [Qwen](knowledge/alibaba-cloud/maas/qwen.md) |
| Qwen3.7-Plus / 3.7 系列 | [Qwen](knowledge/alibaba-cloud/maas/qwen.md#qwen37-plus) |
| Qwen3.7-Max / 旗舰模型 | [Qwen](knowledge/alibaba-cloud/maas/qwen.md#qwen37-max) |
| 万相 / Wan / 视频生成 / 图生视频 | [万相](knowledge/alibaba-cloud/maas/wan.md) |
| HappyHorse / 快乐小马 / 图像生成 | [HappyHorse](knowledge/alibaba-cloud/maas/happyhorse.md) |
| 百炼平台 / 多账号 / TPM 扩量 / 限流 | [百炼平台](knowledge/alibaba-cloud/maas/overview.md) |
| Qoder / AI 编程 / Copilot | [Qoder](knowledge/alibaba-cloud/ai-coding/qoder.md) |
| QoderWork / 桌面助手 / 本地 Agent | [QoderWork](knowledge/alibaba-cloud/ai-application/qoder-work.md) |
| MuleRun / 骡子快跑 / 云端 Agent | [MuleRun](knowledge/alibaba-cloud/ai-application/mulerun.md) |
| MuleRun vs QoderWork 对比 | [MuleRun](knowledge/alibaba-cloud/ai-application/mulerun.md#与-qoderwork-的深度对比分析) |
| GPU 选型 / A100 / H100 / H20 | [GPU 产品线选型](knowledge/alibaba-cloud/ai-infra/gpu-product-line.md) ⭐ |
| 灵骏 / 智算集群 / EFLOPS | [灵骏](knowledge/alibaba-cloud/ai-infra/lingjun.md) |
| Agent 定义 / Harness / 治理层 | [Agent](knowledge/ai-general-notes/agent-def.md) ⭐ / [Harness](knowledge/ai-general-notes/harness.md) ⭐ |
| Prompt 工程 / 防幻觉 | [Prompt Engineering](knowledge/ai-general-notes/prompt-engineering.md) ⭐ |
| Claude / Opus 4.8 / Sonnet / Haiku | [Claude API](knowledge/anthropic/maas/claude-api.md) |
| Claude Code / 竞品对比 | [Claude Code](knowledge/anthropic/ai-coding/claude-code.md) / [Qoder vs Kiro](knowledge/alibaba-cloud/competitive-analysis/qoder-vs-kiro/overview.md) |
| Gemini / Google / Imagen | [Gemini](knowledge/gcp/maas/gemini.md) / [Imagen](knowledge/gcp/maas/imagen.md) |
| Kiro / Spec-driven coding | [Kiro](knowledge/aws/ai-coding/kiro.md) |
| DeepSeek / R1 / V4 / 开源 | [DeepSeek](knowledge/deepseek/general_intro.md) ⭐ |
| MiniMax / M3 / 海螺 AI | [M 系列](knowledge/minimax/minimax-series.md) |
| GLM / 智谱 / 长程任务 | [GLM 系列](knowledge/zhipu/glm-series.md) |
| GPT-5 / ChatGPT / OpenAI | [GPT-5 系列](knowledge/openai/gpt-5-series.md) |
| 企业自建推理 / Higress / AI 网关 | [企业自建 AI 推理平台](knowledge/solutions/enterprise-ai-platform/overview.md) ⭐ |
| 数据出境 / 数据主权 / CN 版 | [MuleRun](knowledge/alibaba-cloud/ai-application/mulerun.md#mulerun全球版与骡子快跑中国版的关系) / [QoderWork](knowledge/alibaba-cloud/ai-application/qoder-work.md) |

## 道：AI 领域知识（跨厂商）

### AI General Notes

**🛠️ 技术概念类**（适合关键选型维度）：
- [Agent](knowledge/ai-general-notes/agent-def.md) ⭐ — for循环本质、Model+Harness框架、Agent平台战略拐点、OpenAI三大优先级
- [Harness](knowledge/ai-general-notes/harness.md) ⭐ — 企业战略级资产、约束治理层、Harness vs Prompt区别、调用层容量与限流治理（多账号扩 TPM、客户端拥塞拐点）
- [Prompt Engineering](knowledge/ai-general-notes/prompt-engineering.md) ⭐ — 防幻觉四层机制、第一性原理、博弈论应用
- [RAG](knowledge/ai-general-notes/rag.md) — 待填充
- [Fine-tuning](knowledge/ai-general-notes/fine-tuning.md) — 待填充

**💡 概念洞察类**（适合关键认知框架）：
- [AI能力边界与迭代部署](knowledge/ai-general-notes/ai-capability-and-deployment.md) ⭐ — 锯齿状能力边界、迭代部署哲学、Personal AGI终局
- [模型自我进化](knowledge/ai-general-notes/agent-self-evolution.md) ⭐ — 模型自驱动训练、打破人工瓶颈、100+轮自主迭代带来30%效果提升

## 点：单产品知识

### 阿里云
- MaaS: [百炼平台](knowledge/alibaba-cloud/maas/overview.md) — UID 级限流、多账号扩 TPM（8.5× 实测）、deepseek-v4-flash 压测 | [Qwen](knowledge/alibaba-cloud/maas/qwen.md) — 3.7-Max/3.7-Plus/3.6、定价、benchmark | [万相](knowledge/alibaba-cloud/maas/wan.md) — 视频生成、首尾帧 | [HappyHorse](knowledge/alibaba-cloud/maas/happyhorse.md) — 图像生成
- AI Coding: [Qoder](knowledge/alibaba-cloud/ai-coding/qoder.md) — IDE 插件、AI 编程
- AI App: [QoderWork](knowledge/alibaba-cloud/ai-application/qoder-work.md) — 桌面 Agent、本地 | [MuleRun](knowledge/alibaba-cloud/ai-application/mulerun.md) — 云端 Agent、Always-On | [龙虾家族](knowledge/alibaba-cloud/ai-application/claw-family.md) | [JVS Crew](knowledge/alibaba-cloud/ai-application/jvs-crew.md)
- AI Platform: [PAI](knowledge/alibaba-cloud/ai-platform/pai.md) — 训练平台
- AI Infra: [ECS GPU](knowledge/alibaba-cloud/ai-infra/ecs-gpu.md) | [灵骏](knowledge/alibaba-cloud/ai-infra/lingjun.md) — 智算集群 | [GPU 产品线选型](knowledge/alibaba-cloud/ai-infra/gpu-product-line.md) ⭐ — A100/H100/H20 选型决策树

### AWS
- MaaS: [Bedrock](knowledge/aws/maas/overview.md) | [Claude](knowledge/aws/maas/claude.md) | [Titan](knowledge/aws/maas/titan.md)
- AI Coding: [Q Developer](knowledge/aws/ai-coding/q-developer.md) | [Kiro](knowledge/aws/ai-coding/kiro.md) — Spec-driven、需求驱动编码
- AI App: [Q Business](knowledge/aws/ai-application/q-business.md) — 企业搜索、知识库
- AI Platform: [SageMaker](knowledge/aws/ai-platform/sagemaker.md) — 训练/部署平台
- AI Infra: [EC2 GPU](knowledge/aws/ai-infra/ec2-gpu.md) | [Trainium](knowledge/aws/ai-infra/trainium.md) — 训练芯片 | [Inferentia](knowledge/aws/ai-infra/inferentia.md) — 推理芯片

### GCP
- MaaS: [Gemini Enterprise Agent Platform](knowledge/gcp/maas/overview.md) | [Gemini](knowledge/gcp/maas/gemini.md) — 2.5 Pro/Flash | [Imagen](knowledge/gcp/maas/imagen.md) — 图像生成
- AI Coding: [Gemini Code Assist](knowledge/gcp/ai-coding/gemini-code-assist.md)
- AI App: [Gemini for Workspace](knowledge/gcp/ai-application/gemini-workspace.md) — Docs/Sheets/Gmail 集成
- AI Platform: [Vertex AI → Agent Platform](knowledge/gcp/ai-platform/vertex-ai.md) — 训练/部署/Agent
- AI Infra: [TPU](knowledge/gcp/ai-infra/tpu.md) — Google 自研 AI 芯片

### Anthropic
- 公司分析: [Anthropic 公司分析报告](knowledge/anthropic/general_intro.md) — PBC 治理结构、Scaling Laws 团队、Claude 模型家族、ARR $2B+（2026.04）
- MaaS: [Claude API](knowledge/anthropic/maas/claude-api.md) — Opus 4.8（SWE-Bench Pro 69.2%）/ Sonnet 4.6 / Haiku 4
- AI Coding: [Claude Code](knowledge/anthropic/ai-coding/claude-code.md) — 终端 AI 编程
- AI App: [Claude Teams](knowledge/anthropic/ai-application/claude-teams.md) | [Claude Managed Agents](knowledge/anthropic/ai-application/claude-managed-agents.md) — 托管 Agent

### MiniMax
- 公司分析: [MiniMax 公司分析报告](knowledge/minimax/general_intro.md) — 2026.01 港股 IPO（00100.HK）、海螺 AI / Talkie 全球化、MiniMax-M1/M2/M2.7 开源混合注意力，**M2.7 自我进化（模型自驱动训练）能力**
- 模型系列: [M 系列](knowledge/minimax/minimax-series.md) — M1/M2/M2.7/M3（**M3 已正式发布**，MSA 稀疏注意力、原生多模态、前沿 Coding/Agent）
- Agent: [Agent Team](knowledge/minimax/agent-team.md) — Leader–Worker–Verifier 对抗制衡多Agent协作系统，Team Engine 状态机驱动

### 智谱 AI（Zhipu）
- 公司分析: [智谱 AI 公司分析报告](knowledge/zhipu/general_intro.md) — 2026.01 港股 IPO（02513.HK，全球大模型第一股）、GLM-5 编程开源 SOTA、MaaS ARR 17 亿元
- 模型系列: [GLM 系列](knowledge/zhipu/glm-series.md) — GLM-4/4.5/4.6/5/5.1，**GLM-5.1 主推 8 小时级长程任务**

### DeepSeek（深度求索）
- 公司分析: [DeepSeek 公司分析报告](knowledge/deepseek/general_intro.md) ⭐ — MLA+MoE 架构创新、R1 纯 RL 推理、V4 开源 SOTA、557万美元训练成本、"DeepSeek 时刻"
- 模型系列: [V 系列](knowledge/deepseek/deepseek-v-series.md) — V1/V2/V3/V3.2/V4 | [R 系列](knowledge/deepseek/deepseek-r-series.md) — R1/R1-0528/R2

### OpenAI
- 公司分析: [OpenAI 公司分析报告](knowledge/openai/general_intro.md) — GPT-5 系列、ChatGPT、Native Computer Use
- 模型系列: [GPT-5 系列](knowledge/openai/gpt-5-series.md) — GPT-5/5.2/5.3/5.4/5.5

## 线：对比分析（阿里云视角）

- [阿里云 vs AWS](knowledge/alibaba-cloud/competitive-analysis/alibaba-vs-aws/overview.md) — 云厂商全面对比
- [阿里云 vs 火山引擎](knowledge/alibaba-cloud/competitive-analysis/alibaba-vs-volcengine/overview.md) — MaaS 定价、生态对比
- [Qoder vs Kiro](knowledge/alibaba-cloud/competitive-analysis/qoder-vs-kiro/overview.md) — AI Coding 工具对比
- [Qoder vs Trae](knowledge/alibaba-cloud/competitive-analysis/qoder-vs-trae/overview.md) ⭐ — 企业级 vs 个人开发者定位差异

## 体：行业解决方案

- [IPC 智能安防](knowledge/solutions/vertical-ipc/overview.md) — 视频监控、AI 质检
- [短剧出海](knowledge/solutions/vertical-short-drama/overview.md) — 视频翻译、本地化
- [商业地产](knowledge/solutions/commercial-real-estate/overview.md) — AI 质检、合同审查、知识库、智能客服、Qoder 提效
- [企业自建 AI 推理平台](knowledge/solutions/enterprise-ai-platform/overview.md) ⭐ — Higress AI 网关 + 灵骏 GPU + 百炼 Fallback；含 AWS 迁移案例
- [跨国企业 MNC](knowledge/solutions/mnc/overview.md) — 全球化部署
- [出海方案](knowledge/solutions/going-global/overview.md) — 合规、数据主权

## 模板参考

- [AI 通用笔记模板](knowledge/ai-general-notes/_template.md)
- [MaaS 产品模板](knowledge/_maas_template.md)
- [产品模板](knowledge/_product_template.md)
- [对比分析模板](knowledge/alibaba-cloud/competitive-analysis/_template.md)
- [内部产品对比模板](knowledge/_internal-comparison_template.md)
- [解决方案模板](knowledge/solutions/_template.md)
