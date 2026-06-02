# 知识库全局索引

> 本文件是知识库的全局索引，Skill 必读。
> 最后更新：2026-06-03

## 🔍 快速查找

按关键词或问题快速定位文档：

| 我想找… | 文档 |
|---------|------|
| Qwen 定价 / 模型对比 / benchmark | [Qwen](alibaba-cloud/maas/qwen.md) |
| Qwen3.7-Plus / 3.7 系列 | [Qwen](alibaba-cloud/maas/qwen.md#qwen37-plus) |
| Qwen3.7-Max / 旗舰模型 | [Qwen](alibaba-cloud/maas/qwen.md#qwen37-max) |
| 万相 / Wan / 视频生成 / 图生视频 | [万相](alibaba-cloud/maas/wan.md) |
| HappyHorse / 快乐小马 / 图像生成 | [HappyHorse](alibaba-cloud/maas/happyhorse.md) |
| 百炼平台 / 多账号 / TPM 扩量 / 限流 | [百炼平台](alibaba-cloud/maas/overview.md) |
| Qoder / AI 编程 / Copilot | [Qoder](alibaba-cloud/ai-coding/qoder.md) |
| QoderWork / 桌面助手 / 本地 Agent | [QoderWork](alibaba-cloud/ai-application/qoder-work.md) |
| MuleRun / 骡子快跑 / 云端 Agent | [MuleRun](alibaba-cloud/ai-application/mulerun.md) |
| MuleRun vs QoderWork 对比 | [MuleRun](alibaba-cloud/ai-application/mulerun.md#与-qoderwork-的深度对比分析) |
| GPU 选型 / A100 / H100 / H20 | [GPU 产品线选型](alibaba-cloud/ai-infra/gpu-product-line.md) ⭐ |
| 灵骏 / 智算集群 / EFLOPS | [灵骏](alibaba-cloud/ai-infra/lingjun.md) |
| Agent 定义 / Harness / 治理层 | [Agent](ai-general-notes/agent-def.md) ⭐ / [Harness](ai-general-notes/harness.md) ⭐ |
| Prompt 工程 / 防幻觉 | [Prompt Engineering](ai-general-notes/prompt-engineering.md) ⭐ |
| Claude / Opus 4.8 / Sonnet / Haiku | [Claude API](anthropic/maas/claude-api.md) |
| Claude Code / 竞品对比 | [Claude Code](anthropic/ai-coding/claude-code.md) / [Qoder vs Kiro](alibaba-cloud/competitive-analysis/qoder-vs-kiro/overview.md) |
| Gemini / Google / Imagen | [Gemini](gcp/maas/gemini.md) / [Imagen](gcp/maas/imagen.md) |
| Kiro / Spec-driven coding | [Kiro](aws/ai-coding/kiro.md) |
| DeepSeek / R1 / V4 / 开源 | [DeepSeek](deepseek/general_intro.md) ⭐ |
| MiniMax / M3 / 海螺 AI | [M 系列](minimax/minimax-series.md) |
| GLM / 智谱 / 长程任务 | [GLM 系列](zhipu/glm-series.md) |
| GPT-5 / ChatGPT / OpenAI | [GPT-5 系列](openai/gpt-5-series.md) |
| 企业自建推理 / Higress / AI 网关 | [企业自建 AI 推理平台](solutions/enterprise-ai-platform/overview.md) ⭐ |
| 数据出境 / 数据主权 / CN 版 | [MuleRun](alibaba-cloud/ai-application/mulerun.md#mulerun全球版与骡子快跑中国版的关系) / [QoderWork](alibaba-cloud/ai-application/qoder-work.md) |

## 道：AI 领域知识（跨厂商）

### AI General Notes

**🛠️ 技术概念类**（适合关键选型维度）：
- [Agent](ai-general-notes/agent-def.md) ⭐ — for循环本质、Model+Harness框架、Agent平台战略拐点、OpenAI三大优先级
- [Harness](ai-general-notes/harness.md) ⭐ — 企业战略级资产、约束治理层、Harness vs Prompt区别、调用层容量与限流治理（多账号扩 TPM、客户端拥塞拐点）
- [Prompt Engineering](ai-general-notes/prompt-engineering.md) ⭐ — 防幻觉四层机制、第一性原理、博弈论应用
- [RAG](ai-general-notes/rag.md) — 待填充
- [Fine-tuning](ai-general-notes/fine-tuning.md) — 待填充

**💡 概念洞察类**（适合关键认知框架）：
- [AI能力边界与迭代部署](ai-general-notes/ai-capability-and-deployment.md) ⭐ — 锯齿状能力边界、迭代部署哲学、Personal AGI终局
- [模型自我进化](ai-general-notes/agent-self-evolution.md) ⭐ — 模型自驱动训练、打破人工瓶颈、100+轮自主迭代带来30%效果提升

## 点：单产品知识

### 阿里云
- MaaS: [百炼平台](alibaba-cloud/maas/overview.md) — UID 级限流、多账号扩 TPM（8.5× 实测）、deepseek-v4-flash 压测 | [Qwen](alibaba-cloud/maas/qwen.md) — 3.7-Max/3.7-Plus/3.6、定价、benchmark | [万相](alibaba-cloud/maas/wan.md) — 视频生成、首尾帧 | [HappyHorse](alibaba-cloud/maas/happyhorse.md) — 图像生成
- AI Coding: [Qoder](alibaba-cloud/ai-coding/qoder.md) — IDE 插件、AI 编程
- AI App: [QoderWork](alibaba-cloud/ai-application/qoder-work.md) — 桌面 Agent、本地 | [MuleRun](alibaba-cloud/ai-application/mulerun.md) — 云端 Agent、Always-On | [龙虾家族](alibaba-cloud/ai-application/claw-family.md) | [JVS Crew](alibaba-cloud/ai-application/jvs-crew.md)
- AI Platform: [PAI](alibaba-cloud/ai-platform/pai.md) — 训练平台
- AI Infra: [ECS GPU](alibaba-cloud/ai-infra/ecs-gpu.md) | [灵骏](alibaba-cloud/ai-infra/lingjun.md) — 智算集群 | [GPU 产品线选型](alibaba-cloud/ai-infra/gpu-product-line.md) ⭐ — A100/H100/H20 选型决策树

### AWS
- MaaS: [Bedrock](aws/maas/overview.md) | [Claude](aws/maas/claude.md) | [Titan](aws/maas/titan.md)
- AI Coding: [Q Developer](aws/ai-coding/q-developer.md) | [Kiro](aws/ai-coding/kiro.md) — Spec-driven、需求驱动编码
- AI App: [Q Business](aws/ai-application/q-business.md) — 企业搜索、知识库
- AI Platform: [SageMaker](aws/ai-platform/sagemaker.md) — 训练/部署平台
- AI Infra: [EC2 GPU](aws/ai-infra/ec2-gpu.md) | [Trainium](aws/ai-infra/trainium.md) — 训练芯片 | [Inferentia](aws/ai-infra/inferentia.md) — 推理芯片

### GCP
- MaaS: [Gemini Enterprise Agent Platform](gcp/maas/overview.md) | [Gemini](gcp/maas/gemini.md) — 2.5 Pro/Flash | [Imagen](gcp/maas/imagen.md) — 图像生成
- AI Coding: [Gemini Code Assist](gcp/ai-coding/gemini-code-assist.md)
- AI App: [Gemini for Workspace](gcp/ai-application/gemini-workspace.md) — Docs/Sheets/Gmail 集成
- AI Platform: [Vertex AI → Agent Platform](gcp/ai-platform/vertex-ai.md) — 训练/部署/Agent
- AI Infra: [TPU](gcp/ai-infra/tpu.md) — Google 自研 AI 芯片

### Anthropic
- MaaS: [Claude API](anthropic/maas/claude-api.md) — Opus 4.8（SWE-Bench Pro 69.2%）/ Sonnet 4.6 / Haiku 4
- AI Coding: [Claude Code](anthropic/ai-coding/claude-code.md) — 终端 AI 编程
- AI App: [Claude Teams](anthropic/ai-application/claude-teams.md) | [Claude Managed Agents](anthropic/ai-application/claude-managed-agents.md) — 托管 Agent

### MiniMax
- 公司分析: [MiniMax 公司分析报告](minimax/general_intro.md) — 2026.01 港股 IPO（00100.HK）、海螺 AI / Talkie 全球化、MiniMax-M1/M2/M2.7 开源混合注意力，**M2.7 自我进化（模型自驱动训练）能力**
- 模型系列: [M 系列](minimax/minimax-series.md) — M1/M2/M2.7/M3（**M3 已正式发布**，MSA 稀疏注意力、原生多模态、前沿 Coding/Agent）
- Agent: [Agent Team](minimax/agent-team.md) — Leader–Worker–Verifier 对抗制衡多Agent协作系统，Team Engine 状态机驱动

### 智谱 AI（Zhipu）
- 公司分析: [智谱 AI 公司分析报告](zhipu/general_intro.md) — 2026.01 港股 IPO（02513.HK，全球大模型第一股）、GLM-5 编程开源 SOTA、MaaS ARR 17 亿元
- 模型系列: [GLM 系列](zhipu/glm-series.md) — GLM-4/4.5/4.6/5/5.1，**GLM-5.1 主推 8 小时级长程任务**

### DeepSeek（深度求索）
- 公司分析: [DeepSeek 公司分析报告](deepseek/general_intro.md) ⭐ — MLA+MoE 架构创新、R1 纯 RL 推理、V4 开源 SOTA、557万美元训练成本、"DeepSeek 时刻"
- 模型系列: [V 系列](deepseek/deepseek-v-series.md) — V1/V2/V3/V3.2/V4 | [R 系列](deepseek/deepseek-r-series.md) — R1/R1-0528/R2

### OpenAI
- 公司分析: [OpenAI 公司分析报告](openai/general_intro.md) — GPT-5 系列、ChatGPT、Native Computer Use
- 模型系列: [GPT-5 系列](openai/gpt-5-series.md) — GPT-5/5.2/5.3/5.4/5.5

## 线：对比分析（阿里云视角）

- [阿里云 vs AWS](alibaba-cloud/competitive-analysis/alibaba-vs-aws/overview.md) — 云厂商全面对比
- [阿里云 vs 火山引擎](alibaba-cloud/competitive-analysis/alibaba-vs-volcengine/overview.md) — MaaS 定价、生态对比
- [Qoder vs Kiro](alibaba-cloud/competitive-analysis/qoder-vs-kiro/overview.md) — AI Coding 工具对比
- [Qoder vs Trae](alibaba-cloud/competitive-analysis/qoder-vs-trae/overview.md) ⭐ — 企业级 vs 个人开发者定位差异

## 体：行业解决方案

- [IPC 智能安防](solutions/vertical-ipc/overview.md) — 视频监控、AI 质检
- [短剧出海](solutions/vertical-short-drama/overview.md) — 视频翻译、本地化
- [商业地产](solutions/commercial-real-estate/overview.md) — AI 质检、合同审查、知识库、智能客服、Qoder 提效
- [企业自建 AI 推理平台](solutions/enterprise-ai-platform/overview.md) ⭐ — Higress AI 网关 + 灵骏 GPU + 百炼 Fallback；含 AWS 迁移案例
- [跨国企业 MNC](solutions/mnc/overview.md) — 全球化部署
- [出海方案](solutions/going-global/overview.md) — 合规、数据主权

## 模板参考

- [AI 通用笔记模板](ai-general-notes/_template.md)
- [MaaS 产品模板](_maas_template.md)
- [产品模板](_product_template.md)
- [对比分析模板](alibaba-cloud/competitive-analysis/_template.md)
- [内部产品对比模板](_internal-comparison_template.md)
- [解决方案模板](solutions/_template.md)
