# 知识库全局索引

> 本文件是知识库的全局索引，Skill 必读。
> 最后更新：2026-08-01

## 目录

- [🔍 快速查找](#-快速查找)
- [道：AI 领域知识（跨厂商）](#道ai-领域知识跨厂商)
- [点：单产品知识](#点单产品知识)
  - 云厂商：[阿里云](#阿里云) · [Google](#google)
  - 海外模型厂商：[Anthropic](#anthropic) · [OpenAI](#openai) · [Microsoft AI (MAI)](#microsoft-ai-mai)
  - 中国模型厂商：[DeepSeek](#deepseek深度求索) · [MiniMax](#minimax) · [智谱 AI](#智谱-aizhipu) · [月之暗面](#月之暗面moonshot-ai) · [腾讯混元](#腾讯混元tencent-hunyuan) · [阶跃星辰](#阶跃星辰stepfun)
- [线：对比分析（阿里云视角）](#线对比分析阿里云视角)
- [体：行业解决方案](#体行业解决方案)
- [模板参考](#模板参考)

---

## 🔍 快速查找

按关键词或问题快速定位文档（⭐ 表示高频文档）：

| 我想找… | 文档 |
|---------|------|
| Qwen / 通义千问 / 3.7-Plus / 3.7-Max / 旗舰 | [Qwen](alibaba-ai-hub/maas/qwen.md) |
| 万相 / Wan / 视频生成 / 图生视频 | [万相](alibaba-ai-hub/maas/wan.md) |
| CosyVoice / 语音合成 / TTS / 声音复刻 | [CosyVoice](alibaba-ai-hub/maas/cosyvoice.md) |
| FunASR / 语音识别 / ASR / 说话人分离 | [FunASR](alibaba-ai-hub/maas/funasr.md) |
| HappyHorse / 快乐小马 / 图像生成 | [HappyHorse](alibaba-ai-hub/maas/happyhorse.md) |
| Fun-Music / 音乐生成 / AI 作曲 / 歌词生成歌曲 | [Fun-Music](alibaba-ai-hub/maas/fun-music.md) |
| 百炼平台 / 多账号 / TPM 扩量 / 限流 | [百炼平台](alibaba-ai-hub/maas/overview.md) |
| 百炼安全 / SOC 2 / CMaaS / 数据主权 / 隔离 | [百炼安全合规](alibaba-ai-hub/maas/model_studio_security-compliance_cn.md) |
| 百炼权限 / RAM / 工作空间 / API Key 配置 | [百炼权限指南](alibaba-ai-hub/maas/model_studio_config/model-studio-workspace-permission-guide.md) |
| Salebook / ROI 计算器 / 售前工具 | [sales-tools/](alibaba-ai-hub/maas/sales-tools/) |
| Qoder / AI 编程 / IDE 插件 | [Qoder](alibaba-ai-hub/ai-coding/qoder.md) |
| Qoder 架构 / Harness 逆向 / 执行日志分析 | [Qoder IDE 架构逆向分析](alibaba-ai-hub/ai-coding/qoder_survey_20260622.md) |
| QoderWork / 桌面助手 / 本地 Agent | [QoderWork](alibaba-ai-hub/ai-application/qoder-work.md) |
| 万镜一刻 / WonderClip / AI视频创作 / 短剧 | [万镜一刻](alibaba-ai-hub/ai-application/wonderclip万镜一刻.md) |
| MuleRun / 骡子快跑 / 云端 Agent / vs QoderWork | [MuleRun](alibaba-ai-hub/ai-application/mulerun.md) |
| GPU 选型 / A100 / H100 / H20 | [GPU 选型决策树](alibaba-ai-hub/ai-infra/gpu-product-line.md) ⭐ |
| 灵骏 / 智算集群 / EFLOPS | 待补充 |
| Agent 定义 / Harness / 治理层 | [Agent](knowledge/ai-general-notes/agent-def.md) ⭐ · [Harness](knowledge/ai-general-notes/harness.md) ⭐ |
| ReAct / 推理+行动 / Thought-Action-Observation | [ReAct 范式](knowledge/ai-general-notes/Memory-ReAct.md) ⭐ |
| Agent 框架 / LangChain / LangGraph / Deep Agents | [Agent 框架](knowledge/ai-general-notes/agent-frameworks.md) |
| AI 记忆 / Memory / Dreaming | [AI Agent 记忆](knowledge/ai-general-notes/agent-memory.md) ⭐ |
| AI 公司增长 / ARR / 飞轮 | [AI 增长飞轮](knowledge/ai-general-notes/ai-company-growth-flywheel.md) ⭐ |
| Prompt 工程 / 防幻觉 | [Prompt Engineering](knowledge/ai-general-notes/prompt-engineering.md) ⭐ |
| SWE-bench / Terminal-Bench / OSWorld / HLE / Agent 评测 | [AI Agent Benchmark](knowledge/ai-general-notes/benchmark-coding-agentic.md) ⭐ |
| 长程任务 / Long Horizon / METR / 8 小时 / 策略切换 | [长程任务](knowledge/ai-general-notes/long-horizon-task.md) ⭐ |
| 前沿模型路线 / 选型框架 / Fable 5 vs Qwen vs GPT | [前沿模型定位](knowledge/ai-general-notes/frontier-model-positioning.md) |
| 推测解码 / Speculative Decoding / DSpark / 推理加速 | [推测解码](knowledge/ai-general-notes/speculative-decoding.md) ⭐ |
| 安全护栏 / 分类器拦截 / 降级兜底 / 护栏粒度 / CVP | [安全护栏粒度](knowledge/ai-general-notes/safety-guardrail-granularity.md) ⭐ |
| MSA / 稀疏注意力 / MiniMax 架构 | [MSA 稀疏注意力](knowledge/minimax/msa-sparse-attention.md) |
| Claude / Opus 5 / Sonnet 5 / Fable 5 / Haiku | [Claude API](knowledge/anthropic/claude-api.md) |
| Claude Code / 竞品 | [Claude Code](knowledge/anthropic/claude-code.md) |
| Gemini / Google / Computer Use | [Gemini](knowledge/google/maas/gemini.md) |
| GPT-5 / GPT-5.6 / ChatGPT / OpenAI / Codex | [GPT-5 系列](knowledge/openai/gpt-5-series.md) · [Codex](knowledge/openai/codex.md) |
| MAI / 微软自研 / Copilot 模型 | [MAI 模型家族](knowledge/microsoft/mai-models.md) |
| DeepSeek / R1 / V4 / 开源 | [DeepSeek](knowledge/deepseek/general_intro.md) ⭐ |
| Hy3 / 腾讯混元 / Hunyuan | [Hy3](knowledge/tencent/hy3.md) |
| StepFun / 阶跃星辰 / Step 3.7 Flash / AI+终端 | [StepFun](knowledge/stepfun/general_intro.md) · [Step 3 系列](knowledge/stepfun/step-3-series.md) |
| Qwen vs Hy3 / 混元竞争分析 | [Qwen3.7 vs Hy3](alibaba-ai-hub/competitive-analysis/qwen-vs-hy3/overview.md) |
| Qwen vs Doubao / 豆包竞争分析 | [Qwen3.7-Max vs Doubao-Seed-2.1 Pro](alibaba-ai-hub/competitive-analysis/qwen-vs-doubao/overview.md) |
| MiniMax / M3 / 海螺 AI | [M 系列](knowledge/minimax/minimax-series.md) |
| Kimi / 月之暗面 / Moonshot / K3 | [Kimi K 系列](knowledge/moonshot/kimi-k-series.md) |
| GLM / 智谱 / GLM-5.2 / 1M 上下文 / 长程任务 | [GLM 系列](knowledge/zhipu/glm-series.md) · [长程任务](knowledge/ai-general-notes/long-horizon-task.md) |
| Seedance / 字节视频生成 / AI 短剧 / 火山方舟 | [Seedance 系列](knowledge/bytedance/seedance-series.md) |
| GRPO / PPO / critic / RL 算法选型 / Agentic RL | [RL 算法选型](knowledge/ai-general-notes/rl-algorithm-selection-grpo-vs-ppo.md) |
| 视频模型数据策略 / 不蒸馏 / 数据质量密度 | [视频模型数据策略](knowledge/ai-general-notes/video-model-data-strategy.md) |
| 矿山安全 / AI 监控 / 矿山 Demo | [矿山安全 AI 监控 Demo](alibaba-ai-hub/ai-industry-solutions/mining-safety-ai-demo.html) |
| 企业自建推理 / Higress / AI 网关 | [企业自建 AI 推理平台](alibaba-ai-hub/ai-industry-solutions/enterprise-ai-platform/overview.md) ⭐ |
| 数据出境 / 数据主权 / CN 版 | [MuleRun](alibaba-ai-hub/ai-application/mulerun.md#mulerun全球版与骡子快跑中国版的关系) · [QoderWork](alibaba-ai-hub/ai-application/qoder-work.md) |

---

## 道：AI 领域知识（跨厂商）

### 技术概念类（关键选型维度）

- [Agent](knowledge/ai-general-notes/agent-def.md) ⭐ — for 循环本质、Model+Harness 框架、Agent 平台战略拐点、OpenAI 三大优先级
- [Harness](knowledge/ai-general-notes/harness.md) ⭐ — 企业战略级资产、约束治理层、Harness vs Prompt 区别、调用层容量与限流治理、Agent=Model+Harness 公式演进史、Model-Harness 协同演进厂商对比
- [Agent 框架](knowledge/ai-general-notes/agent-frameworks.md) — LangChain / LangGraph / Deep Agents 三层递进架构、选型决策树、与闭源 Deep Agent 产品关系
- [Prompt Engineering](knowledge/ai-general-notes/prompt-engineering.md) ⭐ — 防幻觉四层机制、第一性原理、博弈论应用
- [推理深度控制](knowledge/ai-general-notes/reasoning-effort.md) — reasoning_effort / thinking_budget 已成推理模型标配，Agent 场景动态调节策略
- [AI Agent Benchmark](knowledge/ai-general-notes/benchmark-coding-agentic.md) ⭐ — 三维度评估框架：操作执行力（SWE-bench Pro / Terminal-Bench / OSWorld）+ 学术推理力（HLE）+ 知识工作力（GDPval-AA）

### 概念洞察类（关键认知框架）

- [AI 能力边界与迭代部署](knowledge/ai-general-notes/ai-capability-and-deployment.md) ⭐ — 锯齿状能力边界、迭代部署哲学、Personal AGI 终局
- [模型自我进化](knowledge/ai-general-notes/agent-self-evolution.md) ⭐ — 模型自驱动训练、打破人工瓶颈、100+ 轮自主迭代带来 30% 效果提升
- [长程任务](knowledge/ai-general-notes/long-horizon-task.md) ⭐ — METR 任务完成时间线、阶梯型策略切换、GLM-5.1 8 小时级 / Fable 5 天级 / K2.6 13 小时
- [前沿模型定位](knowledge/ai-general-notes/frontier-model-positioning.md) — 三正交轴选型框架（时间尺度 × 模态融合 × 泛化广度）
- [推测解码](knowledge/ai-general-notes/speculative-decoding.md) ⭐ — draft-and-verify 范式、DSpark/DFlash/Eagle3 方法对比、模型+系统联合优化趋势
- [视频模型数据策略](knowledge/ai-general-notes/video-model-data-strategy.md) — 数据质量密度决定生成模型上限、不蒸馏的必然性、UNet→DiT scaling 切换（Seedance 2.0 样本）
- [RL 算法选型：GRPO vs PPO](knowledge/ai-general-notes/rl-algorithm-selection-grpo-vs-ppo.md) — f(rollout 成本, 任务时程) 选型框架、长程 Agentic RL 重新拥抱 critic（GLM-5.2 样本）
- [AI Agent 记忆系统](knowledge/ai-general-notes/agent-memory.md) ⭐ — ChatGPT Dreaming V3、人脑记忆工程同构、个性化护城河
- [ReAct 范式](knowledge/ai-general-notes/Memory-ReAct.md) ⭐ — Reasoning and Acting 范式、Thought-Action-Observation 循环、Memory 是最后一公里
- [AI 公司增长飞轮](knowledge/ai-general-notes/ai-company-growth-flywheel.md) ⭐ — Killer App × 企业信任 × 消费制收入，Anthropic 17 个月 47 倍
- [安全护栏粒度](knowledge/ai-general-notes/safety-guardrail-granularity.md) ⭐ — 从「按领域封禁」到「按危害环节封禁」；危险能力是通用智能的副产物，护栏强度应是实测危害能力的函数（Opus 5 / Sonnet 5 样本）

---

## 点：单产品知识

> 分组顺序：**云厂商**（阿里云 / Google）→ **海外模型厂商** → **中国模型厂商**。

### 🟧 阿里云（核心阵地，30 篇深度文档）

> **从底层算力到上层应用，覆盖 MaaS / AI Coding / AI App / AI Infra / 竞品对比全链路。**

**MaaS（模型即服务）**
- [百炼平台](alibaba-ai-hub/maas/overview.md) — UID 级限流、多账号扩 TPM（8.5× 实测）、deepseek-v4-flash 压测
- [百炼安全合规](alibaba-ai-hub/maas/model_studio_security-compliance_cn.md) — 算力隔离、SOC 2、ISO 42001、CMaaS、Geo-fencing、SLA
- [Qwen](alibaba-ai-hub/maas/qwen.md) — 3.7-Max（编码旗舰）/ 3.7-Plus（性价比）/ 3.6（轻量），1M 上下文
- [万相](alibaba-ai-hub/maas/wan.md) — 视频生成旗舰、首尾帧控制
- [CosyVoice](alibaba-ai-hub/maas/cosyvoice.md) — TTS 主推引擎，声音复刻+声音设计+指令控制，将替代 Qwen-TTS
- [FunASR](alibaba-ai-hub/maas/funasr.md) — ASR 主推引擎，六大能力一站式语音识别，将替代 Qwen3-ASR
- [HappyHorse](alibaba-ai-hub/maas/happyhorse.md) — 图像生成
- [Fun-Music](alibaba-ai-hub/maas/fun-music.md) — AI 音乐生成，歌词到歌曲端到端，fun-music-v1 实测
- [Qwen Demo](alibaba-ai-hub/maas/qwen-demo-20260420.md) · [Wan Demo](alibaba-ai-hub/maas/wan-demo-20260420.md) — 产品演示素材
- [百炼 API 销售指南](alibaba-ai-hub/maas/ModelStudio-api-sales-guide-20260720.md) — 售前话术、模型选型、客户问答
- [百炼权限配置指南](alibaba-ai-hub/maas/model_studio_config/model-studio-workspace-permission-guide.md) — RAM 子账号、工作空间、API Key 全流程截图
- [Wan 费用估算](alibaba-ai-hub/maas/wan_PPL_estimation_20260629.md) — 万相 PPL 费用测算

**售前工具（Sales Tools）**
- [Qwen3.7-Max Salebook](alibaba-ai-hub/maas/sales-tools/qwen3.7-max-salebook.html) · [Qwen3.7-Plus Salebook](alibaba-ai-hub/maas/sales-tools/qwen3.7-plus-salesbook.html) · [三模型联合 Salebook](alibaba-ai-hub/maas/sales-tools/qwen3.7-max-glm-kimi-salebook.html)
- [DeepSeek-V4 TPM ROI 计算器](alibaba-ai-hub/maas/sales-tools/deepseek-v4-tpm-vs-modelstudio-roi.html) · [GLM-5.2 TPM ROI 计算器](alibaba-ai-hub/maas/sales-tools/glm5.2-tpm-vs-modelstudio-roi.html)

**AI Coding**
- [Qoder](alibaba-ai-hub/ai-coding/qoder.md) — 企业级 AI Coding IDE 插件
- [Qoder IDE 架构逆向分析](alibaba-ai-hub/ai-coding/qoder_survey_20260622.md) — 基于执行日志逆向 Agent=Model+Harness 五子系统架构
- [Qoder Credits 省钱指南](alibaba-ai-hub/ai-coding/qoder-credits-saving-tips.png) — 额度优化实战

**AI App**
- [万镜一刻](alibaba-ai-hub/ai-application/wonderclip万镜一刻.md) — 全链路AI视频创作平台，短漫剧+营销，HappyHorse+Wan，$18–$12,000/月
- [QoderWork](alibaba-ai-hub/ai-application/qoder-work.md) — 桌面 Agent、本地
- [MuleRun](alibaba-ai-hub/ai-application/mulerun.md) — 云端 Agent、Always-On
- [龙虾家族](alibaba-ai-hub/ai-application/claw-family.md)
- [JVS Crew](alibaba-ai-hub/ai-application/jvs-crew.md)

**AI Infra（GPU 算力）**
- [GPU 产品线选型](alibaba-ai-hub/ai-infra/gpu-product-line.md) ⭐ — A100/H100/H20 选型决策树

**竞品对比（阿里云视角）**
- [Qoder vs Trae](alibaba-ai-hub/competitive-analysis/qoder-vs-trae/overview.md) — 企业级 vs 个人开发者定位差异
- [Qwen3.7 vs Hy3](alibaba-ai-hub/competitive-analysis/qwen-vs-hy3/overview.md) — 1M上下文+深度编码+多模态 vs 性价比+开源部署
- [Qwen vs Doubao](alibaba-ai-hub/competitive-analysis/qwen-vs-doubao/overview.md) — Coding benchmark 双领先 + 1M 上下文优势

### Google

**MaaS**
- [Gemini Enterprise Agent Platform](knowledge/google/maas/overview.md)
- [Gemini](knowledge/google/maas/gemini.md) — 3.1 Pro（Pro 线旗舰）/ **3.6 Flash（7/21 GA，新 workhorse：token 效率 -17% + 输出降价，OSWorld 83.0%）** / 3.5 Flash-Lite（350 tok/s）；3.5 Pro 跳票，Gemini 4 预训练已启动

**AI Platform**
- [Vertex AI → Agent Platform](knowledge/google/ai-platform/vertex-ai.md) — 训练/部署/Agent

### Anthropic

- 公司分析: [Anthropic 公司分析](knowledge/anthropic/general_intro.md) — PBC 治理、Scaling Laws 团队、Claude 家族、ARR $2B+（2026.04）
- MaaS: [Claude API](knowledge/anthropic/claude-api.md) — 🚩 Fable 5（最高能力档 $10/$50）/ **⭐ Opus 5（2026.07.24，coding·knowledge work SOTA，$5/$25 = Fable 5 半价、无数据留存）** / **Sonnet 5（2026.06.30，$2/$10 → 09-01 起 $3/$15）** / Haiku 4.5
- AI Coding: [Claude Code](knowledge/anthropic/claude-code.md) — 终端 AI 编程
- AI App: [Claude Cowork](knowledge/anthropic/claude-cowork.md) — 桌面通用知识工作 Agent · [Claude Managed Agents](knowledge/anthropic/claude-managed-agents.md)

### OpenAI

- 公司分析: [OpenAI 公司分析](knowledge/openai/general_intro.md) — GPT-5 系列、ChatGPT、Native Computer Use
- 模型系列: [GPT-5 系列](knowledge/openai/gpt-5-series.md) — GPT-5 / 5.2 / 5.3 / 5.4 / 5.5 / **5.6（Sol/Terra/Luna，有限预览）**
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
- 技术论文: [MSA 稀疏注意力](knowledge/minimax/msa-sparse-attention.md) — 块级稀疏注意力架构（arXiv:2606.13392）、Kernel 设计、选择粒度 × 硬件对齐
- Agent: [Agent Team](knowledge/minimax/agent-team.md) — Leader–Worker–Verifier 对抗制衡多 Agent 协作系统

### 智谱 AI（Zhipu）

- 公司分析: [智谱 AI 公司分析](knowledge/zhipu/general_intro.md) — 2026.01 港股 IPO（02513.HK，全球大模型第一股）、GLM-5 编程开源 SOTA、MaaS ARR 17 亿元
- 模型系列: [GLM 系列](knowledge/zhipu/glm-series.md) — GLM-4 / 4.5 / 4.6 / 5 / 5.1 / 5.2，**GLM-5.2 主推 Solid 1M 上下文 + 长程任务开源 SOTA，AA 综合榜前三**

### 月之暗面（Moonshot AI）

- 公司分析: [月之暗面公司分析](knowledge/moonshot/general_intro.md) — 2023 成立、估值 ~$315 亿（投前）、累计融资超 376 亿元、ARR >$3 亿
- 模型系列: [Kimi K 系列](knowledge/moonshot/kimi-k-series.md) — K2 / K2.5 / K2.6 / K3，**K3 2.8T / 1M 上下文，Terminal-Bench 非 OpenAI 模型第 1**

### 字节跳动

- 模型系列: [Doubao-Seed-2.1](knowledge/bytedance/doubao-seed-2.1.md) — Pro（旗舰）/ Turbo（轻量），Coding+Agent 时代生产级模型，GDPval 最高分
- 视频生成: [Seedance 系列](knowledge/bytedance/seedance-series.md) — 2.5（旗舰，30s 直出 + 50 全模态参考）/ 2.0（原生 4K），全球市占率第二仅次 Veo

### 腾讯混元（Tencent Hunyuan）

- 模型: [Hy3](knowledge/tencent/hy3.md) — 295B MoE/21B 激活，OpenRouter 工具调用 #1，SWE-bench 74.4%，开源可自部署，价格碾压

### 阶跃星辰（StepFun）

- 公司分析: [StepFun 公司分析](knowledge/stepfun/general_intro.md) — 2026.01 B+轮超 50 亿人民币（印奇任董事长），"AI+终端"战略：手机装机 4200 万台 + 吉利 AgentOS 座舱，终端 Agent 大脑供应商定位
- 模型系列: [Step 3 系列](knowledge/stepfun/step-3-series.md) — Step 3 / 3.5 Flash / **3.7 Flash（当前主推，198B MoE/11B 激活、256K、原生图像+视频、Advisor Mode 1/9 成本达 Opus 97% coding）**

---

## 线：对比分析（阿里云视角）

- [Qoder vs Trae](alibaba-ai-hub/competitive-analysis/qoder-vs-trae/overview.md) ⭐ — 企业级 vs 个人开发者定位差异
- [Qwen3.7 vs Hy3](alibaba-ai-hub/competitive-analysis/qwen-vs-hy3/overview.md) — 1M上下文+深度编码+多模态 vs 性价比+开源部署，SA 打法建议
- [Qwen vs Doubao](alibaba-ai-hub/competitive-analysis/qwen-vs-doubao/overview.md) — Coding benchmark 双领先（TB 2.1 +3.5, SWE-Pro +3.1）+ 1M 上下文 vs Agent 规划更强，SA 打法建议

---

## 体：行业解决方案

- [IPC 智能安防](alibaba-ai-hub/ai-industry-solutions/vertical-ipc/overview.md) — 视频监控、AI 质检
- [短剧出海](alibaba-ai-hub/ai-industry-solutions/vertical-short-drama/overview.md) — Qwen3.7-Plus 原生 VL 视频理解 + 16 语言内容生成 + OpenSearch SEO，30 天 156 万条
- [商业地产](alibaba-ai-hub/ai-industry-solutions/commercial-real-estate/overview.md) — AI 质检、合同审查、知识库、智能客服、Qoder 提效
- [企业自建 AI 推理平台](alibaba-ai-hub/ai-industry-solutions/enterprise-ai-platform/overview.md) ⭐ — Higress AI 网关 + 灵骏 GPU + 百炼 Fallback；含 AWS 迁移案例
- [矿山安全 AI 监控 Demo](alibaba-ai-hub/ai-industry-solutions/mining-safety-ai-demo.html) — 矿山安全场景 HTML 动态 Demo（含 MP4 录屏）

---

## 模板参考

- [AI 通用笔记模板](knowledge/ai-general-notes/_template.md)
- [MaaS 产品模板](knowledge/_maas_template.md)
- [产品模板](knowledge/_product_template.md)
- [对比分析模板](alibaba-ai-hub/competitive-analysis/_template.md)
- [内部产品对比模板](knowledge/_internal-comparison_template.md)
- [解决方案模板](alibaba-ai-hub/ai-industry-solutions/_template.md)
