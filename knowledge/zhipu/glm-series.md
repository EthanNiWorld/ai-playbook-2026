# 智谱 GLM 系列模型

> 最后更新: 2026-08-17
> 所属厂商: 智谱 AI（Zhipu AI）
> 产品类别: MaaS
> 状态: Published

**定位**: 智谱自研 GLM 系列大模型，清华 KEG 实验室背景，强调中国本土化、合规部署与 ARC（Agent/Reasoning/Coding）能力体系
**当前主推**: GLM-5.3（2026.08.14 发布，同基座后训练 Scaling，API 即将上线 / Coding Plan 已全量）+ GLM-5.2（2026.06 上线并开源，Solid 1M 上下文，专为长程任务而生）
**适用**: 企业合规部署、政企客户、本地化推理、中文编程、长程任务、1M 项目级上下文
**不适用**: 多模态场景（纯文本模型）、需要极致低价的开源场景（DeepSeek 更具价格优势）

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| 🚩 **GLM-5.3** | 最新旗舰（同基座后训练 Scaling） | 1M | 与 GLM-5.2 同基座（~743B MoE）；Terminal-Bench 3.0 28.3 开源第一，CyberGym 84.5%；始终思考模式（low/high/max）；API 即将上线，Coding Plan 已全量，宣布两周后开放权重 | 2026.08.14 |
| **GLM-5.2** | 长程任务旗舰（在售） | 1M | Solid 1M 无损上下文，长程任务开源 SOTA，AA 综合榜 51 分前三，MIT 开源 | 2026.06 |

> 📌 **历史模型**：GLM-5.1（2026.04.07，200K，8 小时级长程任务，SWE-Bench Pro 58.4，MIT 开源，华为昇腾训练）、GLM-5（2026.02.11，128K+，SWE-bench Verified 开源 SOTA）仍可调用，但已被 GLM-5.2/5.3 取代，不建议新项目选用；GLM-4 / GLM-4.5 / GLM-4.6 / GLM-4.7 详见下方各小节。

### GLM-5.3

- **模型**：GLM-5.3
- **公司**：智谱 AI
- **时间**：2026 年 8 月 14 日 [来源: zhipuai.cn/zh/research/162]
- **架构**：总参数 ~743B MoE，与 GLM-5.2 共享同一基座（GLM-5/5.1/5.2/5.3 四代同基座）
- **上下文**：1M tokens，最大输出 128K
- **思考模式**：始终启用思考（不支持禁用），支持 low / high / max 三级
- **可用性**：API 即将上线；Coding Plan 已全量上线 GLM-5.3
- **开源**：官方宣布将在发布两周后开放权重（完成安全评估与加固后）[来源: z.ai/blog/glm-5.3] ⚠️ 截至入库尚未兑现，待验证
- **核心理念**："基座模型没变，但通过极致的后训练 Scaling 大大提高了模型的智能上界" [来源: docs.bigmodel.cn]

#### GLM-5.3 基准分数（vs GLM-5.2）

[来源: 智谱官方技术博客 z.ai/blog/glm-5.3 + zhipuai.cn/zh/research/162]

| 基准 | GLM-5.2 | GLM-5.3 | 提升 | 备注 |
|------|---------|---------|------|------|
| Terminal-Bench 3.0 | 4.6 | **28.3** | +515% | 开源第一 |
| DeepSWE v1.1 | 46.2 | **66.9** | +45% | — |
| Agents' Last Exam (CLI) | 23.8 | **28.5** | +20% | 开源第一 |
| Z.ai Code Bench (max) | 23.4% | **34.5%** | +47% | 内部基准，接近 Fable 5 (39.5%) |
| Z.ai Code Bench (high) | — | **31.4%** | — | 超 Opus 4.8 (29.5%)，且 token 效率更高 |
| CyberGym | 77.2% | **84.5%** | +7.3 | 超越 Mythos 5 (83.8%) 和 GPT-5.6 (83.6%) |
| ExploitBench | 24.4% | **54.4%** | +123% | 仍低于 Mythos 5 (78.0%) |
| ExploitGym (2h/6h) | 29/39 | **105/130** | +261%/+233% | — |
| GDPval-AA v2 | — | **1769** | — | 44 种职业知识工作 |

> ⚠️ Terminal-Bench 3.0 与 2.x 为不同版本，分数不可直接对比（GLM-5.3 的 TB 3.0 = 28.3 与其他模型 TB 2.1 分数不同尺度）。

#### 涌现的网络安全能力 [来源: zhipuai.cn/zh/research/162]

- 在漏洞利用链上展现跨阶段推理能力，官方称为训练中未预期到的涌现行为
- 联合清华、南开及多家安全团队发现 **2,436 个漏洞**（含 1,097 个中高危），覆盖 269 个项目
- 最长潜伏漏洞达**约 45 年**（DNS 协议级漏洞，影响全球 90%+ 主流 DNS 系统）
- 参考 Zerodium 等市场报价，这些漏洞经济价值约 3,000 万元
- 建立 Z.ai 安全漏洞披露台账（https://cvd.z.ai/），启动"开源的盾"计划

#### 后训练 Scaling 技术路线

- **任务环境规模化**：从编程题扩展到接近真实专家工作的完整流程（如 ML infra 优化任务：模型独立发现瓶颈→实施优化→验证结果）
- **自动化环境合成流水线**：研究 Agent 从真实工作收集模式 → 转化为长程任务环境 → 评审 Agent 验证可解性 → 验证器自动生成 RL 奖励信号
- **SAO + 上下文压缩**：延续 GLM-5.2 引入的策略，使能力增益在长程任务中持续体现
- **IndexShare + Slime 框架**：支撑同一基座上的高效 RL 推进

> **Why 同基座路线值得关注**：GLM-5/5.1/5.2/5.3 四代共享同一基座、每次升级仅改后训练——5.2→5.3 单代 Terminal-Bench 3.0 提升 +515%，大于多数厂商跨代提升，证明后训练 Scaling 远未见顶。

### GLM-5.2

- **模型**：glm-5.2
- **公司**：智谱 AI
- **时间**：2026 年 6 月（6.13 宣布全面开放，6.16 上线 OpenRouter）
- **架构**：744B 总参数 MoE，256 experts，每 token 激活 8 个（有效计算约 40B），与 GLM-5/5.1 同架构
- **许可证**：MIT（权重完全开放，可商用，HuggingFace: zai-org/GLM-5.2）
- **上下文**：Solid 1M 无损上下文——官方强调非单纯扩窗，花数月扩展 1M Coding Agent 训练环境（大规模实现/自动化研究/性能优化），实测长上下文表现有时超过 Opus
- **场景**：长程任务（Long Horizon Task）、项目级 Coding、大型重构工程、知识工作者长链路任务
- **特点**：
  1. **长程任务开源 SOTA**：FrontierSWE 仅低 Claude Opus 4.8 约 1%，超 GPT-5.5 和 Opus 4.7；官方 demo 单次长程任务处理 88 万+ tokens 交付多端应用
  2. **Infra 协同设计**：IndexShare（每 4 层稀疏注意力复用同一 indexer，1M 下单 token FLOPs 降 2.9 倍）；MTP 层优化使投机解码接受长度最多提升 20%；Day 0 适配华为昇腾/平头哥/摩尔线程/寒武纪等国产算力平台
  3. **effort level（思考档位）**：可在能力/速度/成本间平衡
  4. **RL 训练路线切换**：长程 Agentic RL 阶段从 GRPO 切换回 critic-based PPO（自研 Slime 框架支撑），详见 [RL 算法选型](../ai-general-notes/rl-algorithm-selection-grpo-vs-ppo.md)
- **官方承认短板**：SWE-Marathon（超长周期自主工程）低于 Opus 4.8 约 13%

#### GLM-5.2 基准分数

| 基准 | 表现 | 说明 |
|------|------|------|
| Artificial Analysis 综合榜 | 51 分 | 与 Anthropic、OpenAI 同列前三，开源 SOTA |
| Code Arena（前端盲测） | 全球可用模型第一 | 百万用户参与盲测 |
| FrontierSWE | 低 Opus 4.8 约 1% | 超 GPT-5.5 和 Opus 4.7，开源最高 |
| SWE-Marathon | 低 Opus 4.8 约 13% | 官方承认待提升 |
| Terminal-Bench 2.1 | 低 Opus 4.8 约 4% | 较 GLM-5.1 提升 17.5% |
| MCP-Atlas（工具使用） | 低 Opus 4.8 约 0.8% | — |

> 来源：[智谱官方博客](https://www.zhipuai.cn/zh/research/161)、[GLM-5.2 技术博客](https://z.ai/blog/glm-5.2)

### GLM-5.1

- **模型**：glm-5.1
- **公司**：智谱 AI
- **时间**：2026 年 4 月 7 日（正式公告），3 月 27 日面向 Coding Plan 用户开放
- **架构**：MoE（Mixture-of-Experts），总参数 744B，256 experts，每 token 激活 8 experts（约 40-44B 激活参数）
- **训练数据**：28.5T tokens
- **训练硬件**：100,000 块华为昇腾 Ascend 910B（完全无 NVIDIA GPU）
- **许可证**：MIT（开源权重，可商用）
- **上下文**：200K tokens，最大输出 128K tokens（约 131,072）
- **模态**：纯文本输入/输出（不支持图像/视频/音频）
- **场景**：Agentic Engineering（工程代理）、长程 Coding Agent、Autonomous Agent
- **特点**：
  1. **8 小时级长程任务**：全球唯一达到 8 小时级持续工作的开源模型，可在单次任务中完成规划、执行、测试、修复、交付完整闭环。技术原理：Progressive Alignment（渐进对齐）纯后训练优化 + 阶梯型策略切换能力（在优化路径碰壁时主动识别瓶颈、切换到结构性不同的方案）。详见 [长程任务](../ai-general-notes/long-horizon-task.md)
  2. **SWE-Bench Pro 58.4**：发布时全球第一，超越 GPT-5.4、Claude Opus 4.6 和 Gemini 3.1 Pro（后被 Claude Opus 4.8 的 69.2 超越，但仍略高于 GPT-5.5 的 58.6）
  3. **工程交付能力**：8 小时从零构建 Linux 桌面系统（1200+ 步骤），655 轮迭代将向量数据库 QPS 提升 6.9 倍，KernelBench Level 3 优化 3.6 倍几何平均加速比
  4. **与 GLM-5 关系**：同架构，纯后训练优化（progressive alignment），编程评分从 35.4 提升至 45.3（+28%）

#### GLM-5.1 基准分数

| 基准 | 分数 | 说明 |
|------|------|------|
| SWE-Bench Pro | 58.4% | 发布时全球第一，目前被 Claude Opus 4.8 (69.2) 超越 |
| SWE-Bench Verified | 77.8% | 接近 Claude Opus 4.6 (80.8%) 和 GPT-5.2 (80.0%) |
| Terminal-Bench 2.0 | 63.5% | 命令行操作与系统管理 |
| NL2Repo | 42.7% | 从零构建完整代码仓库 |
| Coding Score | 45.3 | 达 Claude Opus 4.6 (47.9) 的 94.6% |
| AIME 2026 | 95.3% | 数学竞赛推理 |
| GPQA Diamond | 86.0% | 研究生级科学推理（GLM-5 数据，5.1 未独立公布） |
| 三大代码基准综合 | 全球第三 | 仅次于 Claude Opus 4.6 和 GPT-5.4；国产第一、开源第一 |

> 来源：[智谱官方文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.1)、[智谱研究文档](https://www.zhipuai.cn/zh/research/157)、[WaveSpeed AI 对比](https://wavespeed.ai/blog/posts/glm-5-1-vs-claude-gpt-gemini-deepseek-llm-comparison/)、[Lushbinary](https://lushbinary.com/blog/glm-5-1-benchmarks-breakdown-swe-bench-pro-nl2repo-cybergym/)

#### GLM-5.1 定价

**中国站（智谱开放平台，元/百万 tokens）**：

| 分段 | 输入 | 输出 | 缓存命中 |
|------|------|------|----------|
| 0-32K | 6 元 | 24 元 | 0.6 元 |
| 32K+ | 8 元 | 28 元 | 0.6 元 |

**国际站（美元/百万 tokens）**：

| 渠道 | 输入 | 输出 |
|------|------|------|
| Z.AI 官方 / OpenRouter | $0.98 | $3.08 |
| FriendliAI / Requesty | $1.40 | $4.40 |

> 来源：[智谱定价页](https://bigmodel.cn/pricing)、[OpenRouter](https://openrouter.ai/z-ai/glm-5.1)、[PricePerToken](https://pricepertoken.com/pricing-page/model/z-ai-glm-5.1)

#### GLM-5.1 vs 同期旗舰对比（2026 年 6 月）

| 维度 | GLM-5.1 | Claude Opus 4.8 | GPT-5.5 | Qwen3.7-Max |
|------|---------|-----------------|---------|-------------|
| 发布时间 | 2026.04.07 | 2026.05.28 | 2026.05 | 2026.05.20 |
| SWE-Bench Pro | 58.4 | **69.2** | 58.6 | N/A |
| SWE-Bench Verified | 77.8 | **88.6** | 82.6 | N/A |
| Terminal-Bench | 63.5 (v2.0) | 74.6 (v2.1) | **78.2** (v2.1) | 69.7 (v2.0) |
| HLE | N/A | **57.9** | 52.2 | 41.4 |
| 上下文 | 200K | 200K | **1M** | **1M** |
| 多模态 | ❌ | ✅ | ✅ | ❌ (Max版) |
| 开源 | ✅ MIT | ❌ | ❌ | ❌ |
| 输入价格 $/M | $0.98 | $5.00 | $5.00 | $2.50 |
| 输出价格 $/M | $3.08 | $25.00 | $30.00 | $7.50 |

> GLM-5.1 的核心优势不在绝对分数而在**性价比 + 开源 + 长程任务 + 华为昇腾合规**的组合。

> 来源：[Vellum AI - Claude Opus 4.8 Benchmarks](https://www.vellum.ai/blog/claude-opus-4-8-benchmarks-explained)（引用 Anthropic System Card 8.1.A）、[AI Tools Recap - Qwen3.7-Max](https://aitoolsrecap.com/Blog/qwen-3-7-max-review-benchmarks-2026)

### GLM-5

- **模型**：glm-5
- **公司**：智谱 AI
- **时间**：2026 年 2 月 11 日
- **架构**：MoE，总参数 744B，与 GLM-5.1 共用基础架构
- **上下文**：128K+ tokens
- **场景**：Agentic Coding、企业级推理、复杂任务
- **特点**：
  1. **编程开源 SOTA**：SWE-bench Verified、Terminal-Bench 2.0 等榜单达开源 SOTA，比肩 Claude Opus 4.5
  2. **ARC 能力体系**：Agent / Reasoning / Coding 三大能力体系完整
  3. **清华 KEG 血统**：源自清华大学知识工程实验室，学术与技术双重背书
  4. **首次集成 DeepSeek Sparse Attention**：在维持长文本效果无损的同时提升 Token Efficiency

### GLM-4 系列

- **模型**：GLM-4 / GLM-4-Plus / GLM-4-Air / GLM-4-Flash
- **公司**：智谱 AI
- **时间**：2024 年
- **上下文**：128K+ tokens
- **场景**：通用推理、企业应用
- **特点**：分层模型矩阵，旗舰/性价比/极速全覆盖

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **编程 SOTA** | GLM-5.3 Terminal-Bench 3.0 28.3（开源第一）、DeepSWE 66.9；GLM-5.2 AA 综合榜 51 前三、Code Arena 全球第一 |
| **长程任务** | 全球唯一开源 8 小时级持续工作，自主规划→执行→测试→修复→交付完整闭环 |
| **本地化部署** | 2025 年本地化部署收入 5.34 亿元，同比 +102.3%，是核心商业模式 |
| **政企合规** | 央企、政务、金融、能源等高合规要求行业渗透率高 |
| **华为昇腾训练** | 100,000 块 Ascend 910B 训练，完全脱离 NVIDIA 依赖，中国 AI 自主可控里程碑 |
| **安全攻防（GLM-5.3 涌现）** | CyberGym 84.5% 超越 Mythos 5 / GPT-5.6，发现 2,436 个真实漏洞（含 45 年潜伏 DNS 漏洞） |
| **开源 MIT 协议** | GLM-5.2 / GLM-5.1 权重完全开放，支持商业部署（GLM-5.3 宣布两周后跟进） |
| **中文优化** | 清华大学 KEG 实验室背景，中文理解能力强 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 纯文本 | 不支持图像/视频/音频 | 多模态需使用 GLM-5V-Turbo / GLM-4.6V 等独立产品线 |
| 上下文窗口 | GLM-5.2 已达 1M | GLM-5.1 及之前为 200K；GLM-5.2 实现 Solid 1M 无损上下文 |
| 绝对编程能力 | GLM-5.1 落后 Claude Opus 4.8 约 10 个百分点 | SWE-Bench Pro 58.4 vs 69.2（GLM-5.3 未公布该基准） |
| 国际化 | 主要面向中国市场 | 海外生态和竞争力相对较弱 |
| 性价比 | 非极致低价 | DeepSeek V4 价格更低（$0.27/$1.10），定位不同 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 企业合规部署 | GLM-5.1 / GLM-5 | 本地化部署 + 华为昇腾适配，合规无忧 |
| 政企客户 | GLM-5.1 / GLM-4 全系列 | 高合规要求行业首选 |
| 长程编程任务 | GLM-5.3（Coding Plan）/ GLM-5.2 | GLM-5.3 TB 3.0 28.3 开源第一；GLM-5.2 单次任务 88 万+ tokens 交付 |
| 项目级 1M 上下文 | GLM-5.3 / GLM-5.2 | 完整工程放进同一条推理链路 |
| 安全攻防 / 漏洞研究 | GLM-5.3 | CyberGym 84.5%，真实漏洞挖掘能力验证（2,436 个） |
| 中文编程 | GLM-5.3 / GLM-5.2 | 主流编程基准开源 SOTA |
| 开源 + 商业可用 | GLM-5.2 / GLM-5.1 | MIT 协议，可自部署（GLM-5.3 宣布两周后开放） |
| 中等推理任务 | GLM-4-Air / Flash | 性价比分层 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 极致低价 | DeepSeek V4 价格更低（$0.27/$1.10 vs $0.98/$3.08） |
| 多模态需求 | GLM-5.1 纯文本，需使用 GLM-5V-Turbo 等 |
| 绝对最强编程 | Claude Opus 4.8 在 SWE-Bench Pro 上领先 10.8 个百分点 |
| 超长周期自主工程（SWE-Marathon 类） | GLM-5.2 低于 Claude Opus 4.8 约 13%（官方承认） |
| 全球市场 | 国际化能力相对弱，海外生态不如 Claude/GPT |

## 关键技术论文

| 论文 | 核心观点 | 影响 |
|------|----------|------|
| GLM 论文系列 | 自研 GLM 架构，中英双语优化 | 奠定国产大模型技术基础 |

## 参考资料

- [智谱 GLM-5.3 官方研究博客](https://www.zhipuai.cn/zh/research/162)（2026-08-14）
- [GLM-5.3 官方技术博客](https://z.ai/blog/glm-5.3)
- [GLM-5.3 官方文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3)
- [Z.ai 安全漏洞披露台账](https://cvd.z.ai/)
- [智谱 AI 官网](https://www.zhipuai.cn)
- [智谱 MaaS 平台](https://open.bigmodel.cn)
- [智谱官方博客 - GLM-5.2 上线并开源](https://www.zhipuai.cn/zh/research/161)
- [GLM-5.2 官方文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.2)
- [GLM-5.2 官方技术博客](https://z.ai/blog/glm-5.2)
- [GLM-5.2 ModelScope 模型卡](https://modelscope.cn/models/ZhipuAI/GLM-5.2)
- [GLM-5.1 官方文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.1)
- [智谱新品发布公告](https://docs.bigmodel.cn/cn/update/new-releases)
- [GLM-5.1 GitHub](https://github.com/zai-org/GLM-5)
- [GLM-5.1 Hugging Face](https://huggingface.co/zai-org/GLM-5.1)
- [WaveSpeed AI - GLM-5.1 vs Claude/GPT/Gemini 对比](https://wavespeed.ai/blog/posts/glm-5-1-vs-claude-gpt-gemini-deepseek-llm-comparison/)
- [Vellum AI - Claude Opus 4.8 Benchmarks](https://www.vellum.ai/blog/claude-opus-4-8-benchmarks-explained)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-08-17 | 合并：inbox 四模型调研 - 新增 GLM-5.3 小节（2026-08-14 发布：同基座后训练 Scaling、TB 3.0 28.3 开源第一、DeepSWE 66.9、网络安全涌现能力 2,436 漏洞、后训练技术路线）；主推切换 GLM-5.3 🚩（API 即将上线 / Coding Plan 已全量 / 两周后开放权重待验证），GLM-5.1 移入历史标注；核心能力表新增安全攻防行；适用场景表同步 |
| 2026-07-30 | 合并：inbox 2026-07-30 素材 - 新增 GLM-5.2 小节（1M 上下文、基准分数、IndexShare/MTP、RL 路线切换），主推切换为 GLM-5.2，修正上下文限制与适用场景表述，交叉链接 rl-algorithm-selection-grpo-vs-ppo.md |
| 2026-06-15 | GLM-5.1 长程任务特点补充技术原理摘要（Progressive Alignment + 阶梯型策略切换），新增智谱研究文档参考链接，交叉链接 [long-horizon-task.md](../ai-general-notes/long-horizon-task.md) |
| 2026-06-03 | 全面更新 GLM-5.1：修正发布时间为 2026.04.07（正式公告）；补充架构参数（744B MoE, 256 experts）；新增全部基准分数（SWE-Bench Pro/Verified、Terminal-Bench 2.0、NL2Repo、Coding Score、AIME 2026）；新增中国站/国际站定价；新增与 Claude Opus 4.8 / GPT-5.5 / Qwen3.7-Max 对比表；补充华为昇腾训练、MIT 协议、纯文本限制等关键信息；更新适用/不适用场景 |
| 2026-05-28 | 新建文档，首次提炼 GLM 系列模型系列信息 |
| 2026-05-28 | 更新主推模型为 GLM-5.1（2026.03.27），新增 GLM-5.1 详情节（8 小时级长程任务、SWE-Bench Pro 全球第一） |