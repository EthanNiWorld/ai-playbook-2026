# Gemini

> 最后更新: 2026-10-09
> 所属厂商: GCP
> 产品类别: MaaS

**定位**: Google 自研多模态大模型系列，原生支持文本+图像+音频+视频多模态输入输出
**适用**: 多模态理解与生成、企业知识管理、Agent 基础模型、代码生成、计算机操控
**不适用**: 需要私有化部署的场景（Gemini 仅通过 API / GCP 平台提供）
**当前主推**: **Gemini 4 Argon（2026.09.30，Gemini 4 世代首发旗舰，🌟 输出上限 1M tokens 行业首个——但首发仅 Fairwind Program 受限访问，后续 paid API 无时间表，售前不可承诺获取）**；公开可得旗舰仍为 Gemini 3.1 Pro（2026.02.19，推理与知识密度最强）；Flash 线已迭代至 **Gemini 3.8 Flash / 3.8 Flash Cyber**（[⚠️ 详情待补充]），3.5 Flash-Lite（350 tok/s 高吞吐）在售；3.6 Flash（2026.07.21）已被 3.7 Flash 取代。**Gemini 3.5 Pro 官方确认搁置（2026.09.24）**，重心转 Flash 线 + Gemini 4

## 当前主推模型

| 模型 | 定位 | 核心特点 | 推出/更新时间 |
|------|------|------|------|
| **Gemini 4 Argon** 🚩 | 新世代旗舰（**受限访问**） | 🌟 输出上限 1M tokens（行业首个）；DeepSWE 77.9% SOTA、AA 幻觉率 15% 最低；仅 Fairwind Program；标准价 $4/$20（入门 $2/$10 为 50% 限时促销） | 2026.09.30 |
| **Gemini 3.7 Flash** | 主力（workhorse，coding/agents） | 三周点更新：DeepSWE 65.3%（+16.3），入门价 $0.75/$3.75（至 2026-12-31，标准价 $1.50/$7.50），`thinking_level` 新 API | 2026.08.13 |
| **Gemini 3.1 Pro** | 公开可得旗舰（推理/知识密度最强） | 当前 Pro 级旗舰，学术推理与密集长上下文仍领先 | 2026.02.19 |
| **Gemini 3.5 Flash-Lite** | 轻量（最快最便宜） | 350 tok/s，$0.30/$2.50，多项 Agent/Coding 评测超 3 Flash，Computer Use 内置 | 2026.07.21 |
| **Gemini Omni Flash** | 原生音视频多模态 | 端到端音频/视频原生理解，实时语音交互 | 2026.05.19 |

> 📌 **专用模型**：Gemini 3.5 Flash Cyber（2026.07.21）与 **Gemini 3.8 Flash Cyber**（[⚠️ 详情待补充]）——基于 Flash 线微调的网络安全专用模型，搭配 CodeMender 代码安全 Agent，CyberGym 达前沿竞争力；因双用途风险**仅限政府与受信任伙伴**限额试点获取，不公开售卖
> 📌 **历史模型**：Gemini 3 Pro（→3.1 Pro）/ 3.1 Flash（→3.5 Flash-Lite）/ 3.5 Flash（→3.6 Flash）/ 3.6 Flash（→3.7 Flash，仅存活三周）仍可调用，但不建议新项目选用

> ⚠️ Gemini 2.5 系列（Pro/Flash/Deep Think）为 2025 年中发布，**已非最新代**。2.5 Pro 更新至 2025.06.27，2.5 Flash 更新至 2025.09.26。详见 [Google DeepMind Model Cards](https://deepmind.google/models/model-cards/)

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **原生多模态** | 文本+图像+音频+视频统一理解与生成，不需要拼接多个模型 |
| **超长上下文** | 1M+ tokens，支持整仓库代码/超长文档一次性分析 |
| **Agent 基座** | Gemini Enterprise Agent Platform 的核心引擎，ADK 2.0 默认模型 |
| **Computer Use** | 3.6 Flash / 3.5 Flash-Lite / 3.5 Flash 内置计算机操控工具（client-side built-in tool），可跨浏览器/桌面/移动端自主操作 UI；3.6 Flash OSWorld-Verified 83.0% |
| **TPU 原生优化** | 在 TPU 8t/8i 上推理效率极致优化，推理性价比领先 |
| **MCP 原生支持** | 通过 MCP 协议调用 GCP 全系服务 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 部署方式 | 仅 API / GCP 平台 | 不支持私有化下载部署 |
| API 双轨 | `google.genai` + `vertexai` 两套 API | 开发者需根据场景选择，Google 已确认将长期共存 |
| 中文能力 | 强但非母语级 | 中文场景优先考虑 Qwen / DeepSeek 作为补充 |

## Gemini 4 Argon（2026-09-30，Gemini 4 世代首发旗舰）🌟

> 来源：[Google 官方博客](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/)（2026-09-30，Kavukcuoglu 署名）、[felloai 汇总](https://felloai.com/gemini-4-argon/)（AA/Vals/LMArena 第三方数据、Fairwind 细节、Bloomberg 内部质疑报道）；2026-10-09 合并入库

**基本信息**：
- 2026-09-30 发布，**Gemini 4 世代首个模型**、Google 自 Gemini 3.1 Pro（2026-02）以来首个旗舰（7 个月旗舰空窗；3.5 Pro 确认搁置）
- **"Argon"（氩）为首个代号式命名的 Gemini**，类比 OpenAI Astra/Sol/Luna 的天体命名；官方称 Argon 为 "early post-training output"
- 发布者 Koray Kavukcuoglu（SVP Google DeepMind & Chief AI Architect，已从 OpenAI 移职）
- 定位 "our next era of frontier intelligence"：real-world software engineering、enterprise knowledge work（法律/金融）、cybersecurity defense、creative writing；"built to sustain deep reasoning across complex, long-horizon workflows"
- 规格：**输出上限 1M tokens**（上代 64K，行业最高）；上下文 1M（Artificial Analysis 口径；**Google 未发 model card，官方 API model ID 与知识截止未公布**）；文本+图像输入（AA 列表另含 video/speech 输入）

**访问受限（Fairwind Program）**：首发仅 Fairwind Program（650+ 合作伙伴：政府/国家 cyber 机构、医疗·电信·能源·金融关键基础设施运营商、核心技术平台、防御性 benchmark 学术实验室；需钓鱼抗性 MFA、禁转售）；Fairwind 伙伴与 Google 内部团队获**无 cyber 护栏版** + CodeMender 集成；后续 paid API + Google AI Ultra 订阅者（无时间表）；参与美国政府自愿 pre-release 审查——**售前不可承诺获取**。

**定价**：入门价 **$2 输入 / $10 输出 / cached $0.10（=95% off）——50% 限时促销，促销期未公布**；标准价 **$4/$20（与 Opus 5.5 同价）**。生产预算必须按标准价测算。

**技术亮点与独创性**：
1. 🌟 **首创｜1M token 单响应输出上限**（行业首个；此前行业最高 128K——Claude/GPT 系，Gemini 3.x 为 64K）+ 配套 **Long Decode Continuation** API（超长输出暂停/续传，防请求超时）——此前无同类：输出上限从未被作为主打规格突破。专为"单次轨迹完成长程任务"设计：全库代码迁移、超长法律文书、数小时连续推理
2. 📋 **跟进对齐｜无护栏版 + 可信防御者受限访问（Fairwind）**：Anthropic Project Glasswing（Mythos 5）与 OpenAI Daybreak（Astra）先行——三大前沿厂商 2026 年内全部采用"最强 cyber 能力 → 受限分阶段发布"同构模式
3. ⚙️ **工程优化**：DeepSWE v1.1 **77.9% SOTA**（Opus 5.5 74.2 / Astra 74.1 / GPT-6 Sol max 68.8 / Gemini 3.7 Flash 65.3）；Vals Index 68.9% #1/41；AA 幻觉率 **15%（AA 实测领先模型最低**：Astra 51%、GPT-6.1 Sol 54%）——代价是事实题答对率 -13pp（更多拒答）；LMArena Text Arena #1（1525 分，coding/hard prompts/指令跟随/创意写作分类均第一）
4. 🔬 **独特路线**：CoT + 行为实时监控用于失配缓解（监控发现刻意不回流训练，防模型"学会规避监控"），公开呼吁全行业保持推理透明——与 Astra"书面推理更难监控"的困境形成 alignment 监控的两条路线对照

**能力领先项**：Harvey Legal Agent **19.6% vs Opus 5.5 3.8% / Astra 5.4%**（法律工作 ~5× 领先，最大单项差距）；Vals Finance Agent v2 65.4%；AutomationBench 51.3% #1（Opus 5.5 42.5、Astra 41.4）；GraphWalks 84.2%（长上下文）；LVBench 91.7%（长视频）；Gray Swan IPI 提示注入攻击成功率 **0.7%**（Opus 5.5 1.0%、Astra 8.5%）；CWE-bench v1 68% 并列第一；IOI 编程奥赛 100%（与 Astra 并列）。

**增量解锁**：①1M 输出 → 全库级迁移/超长文书"一口气"完成（Google 内部实证：Fuchsia Zircon 内核 800K+ 行 C/C++→Rust、libgav1 32K 行 SIMD 重写后 2.7× 提速、数据中心内存优化释放 300 TiB（预计 500 TiB–1 PiB）、量子算法超已发表 baseline 40%）②最低幻觉率 → 高可信知识工作（法律/金融）③防御性 cyber 生产工具（Wiz Scan for Good 实战发现全球医院医疗软件严重漏洞——前代前沿模型均未发现）。

**⚠️ 落后项（Bloomberg 报道内部质疑部分印证）**：Terminal-Bench 4.0 57.4% vs Opus 5.5 **66.4%**；FrontierSWE v2 55.0% vs Astra **65.5%**；Code Arena: WebDev 仅 #8（前端弱）；AA Intelligence Index 53 = Astra = Fable 5.1，低于 Opus 5.5 58 / Sonnet 5.5 56。

**AA 成本实测**：入门价 $1.99/task（Astra $3.26 的 60%、Opus 5.5 $5.98）；标准价 $3.98/task；**62K output tokens/task（Astra 27K）——低价靠单价而非省 token**，入门价下仍为 GPT-6.1 Sol 的 2.7×/task。

**成本归因**：定价策略降本（限时促销）为主——AA 明确"低价来自 token 单价而非用量"（输出 token 用量为 Astra 的 2.3×），架构内禀降本无公开证据（无技术报告）。促销动机判断：在 Opus 5.5（同标准价）发布 8 天后入场，用半价期拉高第三方"成本效率"口径（AA $1.99/task、LMArena "most cost efficient model" 均依赖促销价）抢占首发心智。Google 自有 TPU 推理栈是长期单位成本优势（知识库已有结论），但本次发布无相关披露。

## Gemini 3.7 Flash（2026-08-13 发布，当前 workhorse）

> 来源：[Google Blog — Introducing Gemini 3.7 Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-3-7-flash/)、[DeepMind Model Card](https://deepmind.google/models/model-cards/gemini-3-7-flash/)；2026-08-17 合并入库

**基本信息**：
- Model ID：`gemini-3.7-flash`；官方定位 "most intelligent workhorse model yet for coding and agents"（中档主力，非旗舰）
- 距 3.6 Flash（2026.07.21）仅三周发布；上下文维持 1M 未扩展，能力提升来自后训练（RL）而非模型扩大（素材分析）
- 技术规格：1M tokens 上下文 / 最大输出 64K；输入文本+图像+音频+视频，输出文本；知识截止 2026 年

**定价（含时效）** [来源: blog.google + Google AI Studio]：

| 时段 | 输入 ($/M tokens) | 输出 ($/M tokens) | 有效期 |
|------|-------------------|-------------------|--------|
| 入门价 | $0.75 | $3.75 | 至 2026-12-31 |
| 标准价 | $1.50 | $7.50 | 2027-01-01 起 |

入门价 = 3.6 Flash 标准价的一半，同时性能更强。

**Benchmark（vs 3.6 Flash）** [来源: blog.google 官方 + miraflow.ai 分析]：

| 基准 | 测量维度 | 3.6 Flash | 3.7 Flash | 提升 |
|------|---------|-----------|-----------|------|
| DeepSWE v1.1 | 长程编码（抗污染） | 49.0% | **65.3%** | +16.3 |
| FrontierCode 1.1 Main | 意图推断编码 | 34.4% | **43.6%** | +9.2 |
| WebDev Arena Elo | 人类盲评 Web 开发 | 1538 | **1588** | +50 |
| GDP.pdf | 复杂文档理解 | 22.0% | **34.0%** | +12.0 |
| AutomationBench | 多步工作流自动化 | 17.0% | **30.4%** | +13.4 |

**关键 API 变化** [来源: Google AI for Developers 文档]：
1. **`thinking_level` 取代 `thinking_budget`**：三值枚举（low / medium / high）——low 延迟敏感（实时对话、事件响应）；medium 默认（复杂编码与 Agent 工作流）；high 极端困难任务（数学、复杂编码，延迟与 token 开销显著增加）
2. **`temperature` / `top_p` / `top_k` 已废弃**
3. **服务端 `previous_interaction_id`**：对话状态服务端保存，客户端仅发送新 turn，大幅降低多轮 Agent 会话的输入 token 开销
4. **移除 prefilled assistant turns**

**部署与生态**：已部署至 Gemini Spark（Google 个人 AI Agent，覆盖 160+ 国家）与 Antigravity（Agent-first 编码环境）

> **Why 值得关注**：三周点更新 + 入门价减半 + 性能大幅提升 = 同价位性能翻倍；`thinking_level` 三值枚举是推理控制新范式——从"猜 token 预算"到"选任务难度"，与 DeepSeek / GLM 的 `reasoning_effort` 三级化同向（见 [推理深度控制](../../ai-general-notes/reasoning-effort.md)）

## Gemini 3.6 Flash / 3.5 Flash-Lite / 3.5 Flash Cyber（2026-07-21 发布）

> 来源：[Google Blog — Introducing Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Flash Cyber](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)，Gemini API changelog 确认 3.6 Flash / 3.5 Flash-Lite 当日 GA
>
> ⚠️ 2026-08-13 起 3.6 Flash 已被 3.7 Flash 取代（仅存活三周）；3.5 Flash-Lite / 3.5 Flash Cyber 仍为现役

### 3.6 Flash：新一代 workhorse，叙事从"快"转向"高效可靠的企业 Agent 主力"

官方口径："production AI agents 需要更高 token 效率、更低时延、更可靠的表现"——核心卖点不再是峰值分数，而是**单位 Agent 任务成本**：

| 维度 | 3.6 Flash | vs 3.5 Flash |
|------|-----------|--------------|
| 输出 token 效率 | 减 17%（AA Index），DeepSWE 场景最高减 65% | 推理步骤与工具调用次数同步减少 |
| 定价 | $1.50 输入 / **$7.50 输出** /1M tokens | 输入持平，输出降价 17%（原 $9.00） |
| Coding 精度 | DeepSWE 49%（更少非预期代码编辑/执行循环） | 3.5 Flash 37% |
| ML 研究 | MLE Bench 63.9% | 3.5 Flash 49.7% |
| Computer Use | OSWorld-Verified 83.0%，内置 client-side 工具 | 3.5 Flash 78.4% |
| 知识工作 | GDPval-AA v2 1421（Hebbia/Harvey 反馈多模态文档解析/图表分析/报告起草能力突出） | 3.5 Flash 1349 |

- **安全**：携带增强版 Frontier Safety 防护（CBRN + 网络攻击滥用），抗越狱能力提升同时降低良性用途拒答率
- **可用性**：Gemini API（AI Studio / Android Studio）、Antigravity、Gemini Enterprise Agent Platform、Gemini App
- 客户背书：Figma、Harvey、Hebbia、JetBrains

> **Why 这个叙事重要**：Google 把 Flash 线从"便宜跑量"升级为"企业 Agent 主力"，token 效率成为与分数并列的一等公民指标——Agent 多轮调用下，输出 token 减 17% + 输出单价降 17% 的叠加效应对单任务成本的影响远大于 benchmark 提升。这与 StepFun Step 3.7 Flash 的"agent efficiency"路线同向，印证行业竞争焦点从智力上限转向效率前沿。

### 3.5 Flash-Lite：高吞吐 Agent 扩展层

- **速度/价格**：350 output tok/s（AA 实测，3.5 系最快），$0.30 输入 / $2.50 输出 /1M tokens
- **能力跃升**（vs 3.1 Flash-Lite）：Terminal-Bench 2.1 54% vs 31%；GDM-MRCR v2 72.2% vs 60.1%；GDPval-AA v2 1140 vs 642
- **越级表现**：多项 Agent/Coding 评测超 3 Flash（SWE-Bench Pro 54.2% vs 49.6%；OSWorld-Verified 74.0% vs 65.1%）
- **定位**：可配置 thinking level，低档跑高并发低时延任务，高档处理多步 subagent 工作负载；官方示例中与 3.6 Flash 组成 master-worker 多 Agent 编排；已开始接入 Google Search

### 3.5 Flash Cyber：安全垂直专用（限定开放）

基于 3.5 Flash 微调的网络安全模型，在 CodeMender 中以多 Agent 协作产出合并报告，CyberGym 达前沿竞争力。因双用途风险，**仅向政府与受信任伙伴限额试点**，售前场景不可承诺获取。

## 上代模型存档：Gemini 3.5 Flash（已被 3.6 Flash 取代）

> 发布 2026.05.19（Google I/O 2026），API Model ID `gemini-3.5-flash`。以下仅保留仍有参考价值的结论，详细 benchmark/定价历史数据见 [3.5 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-5-flash/) 及 Changelog 2026-06-09 版本。

- **历史意义**：首次打破"Pro=难题, Flash=跑量"二分法——Agent/Coding 负载上 Flash 首次超越自家上代 Pro（GDPval-AA 1656 vs 3.1 Pro 1314，Finance Agent v2 +14.9），奠定了 3.6 Flash "workhorse" 叙事的基础
- **关键参数**：1M 输入 / 64K 输出，$1.50/$9.00（缓存 $0.15），知识截止 2026.01
- **Computer Use 起源**：2026.06.24 率先在 3.5 Flash 上成为内置工具（此前仅独立 Gemini 2.5 computer use 模型），现已成为 Flash 线标配（3.6 Flash / 3.5 Flash-Lite 均内置）；安全机制：prompt injection 对抗训练 + 敏感操作显式确认 + 间接注入自动停止，建议配合沙箱与 human-in-the-loop
- **遗留弱点**（下方"诚实弱点"章节数据即基于 3.5 Flash 实测）：密集长上下文回忆与极难学术推理仍输 3.1 Pro

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 多模态企业知识库 | 3.7 Flash / 3.1 Pro | 3.7 Flash 复杂文档理解 GDP.pdf 34.0%（+12.0）；深度推理选 3.1 Pro |
| Agent 规模化部署 | 3.7 Flash | workhorse 定位，入门价 $0.75/$3.75（至 2026-12-31）+ AutomationBench 30.4%，单任务成本最优 |
| 高吞吐批量/subagent 扩展 | 3.5 Flash-Lite | 350 tok/s，$0.30/$2.50，适合 agentic search/文档处理高并发 |
| 复杂推理/学术难题 | 3.1 Pro | 对标 Claude Opus / GPT-5.x，HLE/ARC-AGI-2 仍领先 Flash 线 |
| 实时音视频交互 | Omni Flash | 原生端到端音频/视频理解 |
| 代码辅助 | 3.7 Flash | DeepSWE 65.3% vs 3.6 Flash 49%，FrontierCode 43.6%（+9.2） |
| Google Workspace AI | 3.1 Flash / 3.1 Pro | 内嵌于 Gmail/Docs/Sheets 的 AI 能力 |

## 平台交付方式

Gemini 通过 **Gemini Enterprise Agent Platform** 统一交付（见 [`vertex-ai.md`](../ai-platform/vertex-ai.md)）。开发者可选两种接入路径：

| 路径 | 接口 | 适用 |
|------|------|------|
| **Gemini API / AI Studio** | `google.genai` | 快速原型、单次推理、个人开发者 |
| **Agent Platform** | `vertexai`（原 Vertex AI API） | 企业级 Agent 构建、生产部署、治理优化 |
| **Gemini App / Search AI Mode** | 消费者界面 | 3.6 Flash 已上线 Gemini App，3.5 Flash-Lite 接入 Google Search（默认模型是否切换待核实） |
| **Antigravity 2.0** | 独立桌面 Agent IDE | Agent 开发者，对标 Claude Code / Cursor |

> **新产品/能力**：
> - **Antigravity 2.0**：独立桌面 Agent 开发环境，支持并行子 Agent 执行、定时任务（后台自动化）、CLI + SDK，与 AI Studio / Android / Firebase 集成。Gemini CLI 用户可迁移至 Antigravity CLI。
> - **Managed Agents**：单次 API 调用即可启动完整 Agent（推理 + 工具调用 + 代码执行），隔离 Linux 环境，跨调用持久化。
> **Gemini Spark**：个人 AI Agent，7×24 运行；3.7 Flash 发布后已部署至 Spark（覆盖 160+ 国家）与 Antigravity。

### 真实落地案例

| 客户 | 场景 |
|------|------|
| Shopify | 并行子 Agent 做全球商户增长预测 |
| Macquarie Bank | 100+ 页金融文档推理加速 onboarding |
| Salesforce Agentforce | 多子 Agent 企业任务自动化 |
| Ramp | 多模态 OCR 处理复杂发票 |
| Xero | 自主管理多周工作流（1099 税务表单） |
| Databricks | Agent 化监控与实时检索 |

### 诚实弱点

> 以下数据基于 3.5 Flash 实测（3.6 Flash 对应数据待 model card 核实），Flash 线相对 Pro 的结构性短板判断仍适用：

| 弱点 | 说明 |
|------|------|
| 128k 密集上下文回忆 | MRCR v2 · 128k 输 3.1 Pro 7.6 分，"塞满 128k 全部精准回忆"场景慎用 |
| 学术推理 | Humanity's Last Exam 输 4.2 分、ARC-AGI-2 输 5.0 分，极难学术问题选 3.1 Pro 或等待 3.5 Pro |

> 📌 **Gemini 3.5 Pro 确认搁置（更新 2026-10-09）**：原预计 2026.06 发布，多次跳票后，Kavukcuoglu 于 2026-09-24 公开确认 "took a little bit of a step back"——重心转向 Flash 线与 Gemini 4；**Gemini 4 Argon 已于 09-30 发布（见上文专章）**。售前沟通中不应承诺 3.5 Pro。另：Flash 线已迭代至 **3.8 Flash / 3.8 Flash Cyber**（[⚠️ 详情待补充]）。

## 参考资料

- [Google Blog - Gemini 3.5](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-5/)
- [Google Blog — Introducing Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Flash Cyber](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)（2026-07-21）
- [Gemini API Release Notes](https://ai.google.dev/gemini-api/docs/changelog)（3.6 Flash / 3.5 Flash-Lite GA 确认）
- [Google Blog — Introducing Gemini 3.7 Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-3-7-flash/)（2026-08-13）
- [Gemini 3.7 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-7-flash/)
- [miraflow.ai — Gemini 3.7 Flash benchmarks 分析](https://miraflow.ai/blog/gemini-3-7-flash-explained-coding-benchmarks-2026)
- [Gemini 3.6 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-6-flash/)
- [Reuters — Google updates lightweight Gemini models, but flagship still delayed](https://www.reuters.com/business/google-updates-lightweight-gemini-models-flagship-still-delayed-2026-07-21/)（3.5 Pro 跳票归因）
- [Google Blog — Introducing computer use in Gemini 3.5 Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-computer-use-gemini-3-5-flash/)
- [Gemini 3.5 Flash Model Card](https://deepmind.google/models/model-cards/gemini-3-5-flash/)
- [LLM Stats - Gemini 3.5 Flash Launch](https://llm-stats.com/blog/research/gemini-3.5-flash-launch)
- [Gemini Flash 产品页](https://deepmind.google/models/gemini/flash/)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-10-09 | 合并四模型调研素材：**新增 Gemini 4 Argon 专章**（09-30 发布，🌟 1M 输出上限行业首个 + Long Decode Continuation、Fairwind 受限访问、DeepSWE 77.9% SOTA、AA 幻觉率 15% 最低、领先/落后项与成本归因全量）；主推表加 Argon（受限标注）并调整 3.1 Pro 为"公开可得旗舰"；**补记 3.8 Flash / 3.8 Flash Cyber 已存在**（[⚠️ 详情待补充]）；3.5 Pro 从"跳票预期"改为"官方确认搁置（09-24）"；头部当前主推重写 |
| 2026-08-17 | 合并：inbox 四模型调研 - 新增 Gemini 3.7 Flash 章节（2026-08-13 发布，新 workhorse 🚩：入门价 $0.75/$3.75 至 2026-12-31 / DeepSWE 65.3% / thinking_level 三值枚举等 4 项 API 变化 / 部署 Gemini Spark+Antigravity）；主推表重排（3.7 Flash 顶替 3.6 Flash，3.6 Flash 仅存活三周移入历史标注）；适用场景与平台交付表同步 |
| 2026-07-27 | 精简：3.5 Flash 深度分析章节（~80 行）压缩为"上代模型存档"小节，保留战略意义/关键参数/Computer Use 起源，删除过时 benchmark/定价详表；诚实弱点与平台交付口径同步 |
| 2026-07-27 | 合并：2026-07-21 三模型发布官网调研 — 新增 Gemini 3.6 Flash（新 workhorse 🚩，$1.50/$7.50，token 效率 -17%）/ 3.5 Flash-Lite / 3.5 Flash Cyber 章节；主推表重排（3.5 Flash 降为上代）；3.5 Pro 跳票与 Gemini 4 预训练启动；适用场景表同步 |
| 2026-06-29 | 合并：Gemini 3.5 Flash Computer Use 官网调研 — 新增 Computer Use 内置工具章节（2026.06.24 发布，跨平台支持，安全机制），核心能力表新增 Computer Use 行，当前主推描述更新 |
| 2026-06-09 | 合并：Gemini 3.5 Flash 深度分析 — 补充 benchmark 详细对比表（vs 3.1 Pro）、定价、战略意图、Antigravity 2.0、Managed Agents、Gemini Spark、真实落地案例、诚实弱点、3.5 Pro 预期、参考资料 |
| 2026-06-09 | 修正：Gemini 3 Pro / 3.1 Pro 版本关系——3 Pro 为上代旗舰，3.1 Pro 为当前旗舰；适用场景表同步修正 |
| 2026-05-31 | 修正：Gemini 2.5→3.x 系列为最新代。新增 Gemini 3 Pro、3.5 Flash、Omni Flash、3.1 Pro/Flash。标注 Gemini 3.5 Pro 预计 2026.06 发布 |
