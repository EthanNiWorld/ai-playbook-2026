# Gemini

> 最后更新: 2026-11-23
> 所属厂商: GCP
> 产品类别: MaaS

**定位**: Google 自研多模态大模型系列，原生支持文本+图像+音频+视频多模态输入输出
**适用**: 多模态理解与生成、企业知识管理、Agent 基础模型、代码生成、计算机操控
**不适用**: 需要私有化部署的场景（Gemini 仅通过 API / GCP 平台提供）
**当前主推**: **Gemini 4 Neon（2026.11.18 发布，AA Intelligence Index v5.0.1 xhigh = 61 总榜第 3，$3/$15，Google 七周内第四款模型）**；**Gemini 4 Carbon 🚩（2026.10.28 发布、11.10 公开 API 开放，AA v5.0 = 60，2026-11-08 曾榜首、11-09 起 Fable 5.2 接棒；标准价 $4/$20）**；Gemini 4 Argon（09.30 发布、10.13 GA，🌟 输出上限 1M tokens 行业首个）；**Gemini 4 Hydrogen（2026.11.12，workhorse，3.8 Flash 官方接棒者，$1.50/$7.50 flat）**；3.5 Flash-Lite / Omni Flash 在售。3.8 Flash / 3.1 Pro 移入历史模型。**Gemini 3.5 Pro 官方确认搁置**；Fairwind 仅覆盖无护栏 cyber 版

## 当前主推模型

| 模型 | 定位 | 核心特点 | 推出/更新时间 |
|------|------|------|------|
| **Gemini 4 Neon** | 高性能新旗舰（**公开可得**） | AA v5.0.1 xhigh = 61（总榜第 3，仅次 Fable 5.2 65 / GPT-6.2 Astra 62）；$3/$15、cached $0.15（95% 折扣）；1M ctx、文本+图像+视频+语音输入；effort 四档（low/medium/high/xhigh）；发布即公开 API + Antigravity | 2026.11.18 |
| **Gemini 4 Carbon** 🚩 | 旗舰（**公开可得**：付费 API / Ultra 订阅） | **AA Intelligence Index v5.0 = 60（2026-11-08 曾 #1，现榜首 Fable 5.2 65）**；TB 4.0 (AA) 65.2%；SEC-bench Pro 88.2%；11-10 API 开放，标准价 $4/$20；Fairwind 仅限无护栏 cyber 版 | 2026.10.28（11.10 API 开放） |
| **Gemini 4 Argon** | 世代首发旗舰（**公开可得**） | 🌟 输出上限 1M tokens（行业首个）；DeepSWE 77.9% SOTA、AA 幻觉率 15% 最低；10-13 GA [⚠️ 第三方信源]；标准价 $4/$20 | 2026.09.30（10.13 GA） |
| **Gemini 4 Hydrogen** | 当前 workhorse（coding/agents 执行档） | adapted from Carbon；AA high 51 / xhigh 54（超 Argon 50）；TB 4.1 57%（3.8 Flash 18.2%）；统一 1M 窗口 + 1M long-decode 输出；`thinking_level` 四档（默认 high）；$1.50/$7.50 flat | 2026.11.12 |
| **Gemini 3.5 Flash-Lite** | 轻量（最快最便宜） | 350 tok/s，$0.30/$2.50，多项 Agent/Coding 评测超 3 Flash，Computer Use 内置；Gemini app 免费档主力 | 2026.07.21 |
| **Gemini Omni Flash** | 原生音视频多模态 | 端到端音频/视频原生理解，实时语音交互 | 2026.05.19 |

> 📌 **专用模型**：**Gemini 3.8 Flash Cyber**（2026.09.02，当前）与 Gemini 3.5 Flash Cyber（2026.07.21）——Flash 线网络安全专用模型：CyberGym 前沿级漏洞发现、CWE-Bench 修复 pass@1 47.2%（Pareto 前沿）、内部 20 语言漏洞发现成功率 >70%；经 **Fairwind Program** 向政府/关键基础设施/软件维护者等受信防御者开放，不公开售卖。2026-11-10 起 Fairwind 亦开放 **Carbon for cyber**（无护栏版，受信防御者申请制；公开版 Carbon 已 GA 且带完整护栏）
> 📌 **历史模型**：**Gemini 3.8 Flash（2026.09.02）workhorse 已于 2026-11-12 由 4 Hydrogen 接棒（官方迁移指南），无退役日期、API 仍在售（2027-01-01 起定价 $1.50/$7.50 与 Hydrogen 同价），Gemini app 已不再列出**；**Gemini 3.1 Pro（2026.02.19）上代公开旗舰，仍可调用**；3.7 Flash（2026.08.13）仍官方 fully supported（效率优先负载）；3 Pro / 3.1 Flash / 3.5 Flash / 3.6 Flash（仅存活三周）仍可调用，不建议新项目选用。2026-12-01 起已弃用的 gemini-2.5-pro 请求自动路由至 3.8 Flash（第三方引 Google 退役表 [⚠️ 待核实]）

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

## Gemini 4 Neon（2026-11-18，Google 七周内第四款模型）

> 来源：[AA 官方分析文章](https://artificialanalysis.ai/articles/gemini-4-neon-intelligence-gain)（2026-11-18）

- **模型**：Gemini 4 Neon，Google 七周内第四款模型（Argon → Carbon → Hydrogen → Neon）
- **公司**：Google
- **时间**：2026-11-18 发布，发布即公开 API + Gemini Enterprise Agent Platform + Antigravity（Pro/Ultra）
- **Benchmark**：AA Intelligence Index v5.0.1（xhigh）= **61，总榜第 3**（仅次 Fable 5.2 65、GPT-6.2 Astra 62）；比 Carbon（high）高 1 分；Coding Agent Index 59（Antigravity CLI，Carbon 55）；GDP.pdf 33.4%（+5pt）；AA-Briefcase 1700 Elo（Presentation Quality 1771 超 Sonnet 5.5 居首）
- **定价**：$3/$15（Carbon 标准价 $4/$20 的 75 折）；cached $0.15（95% 折扣）
- **上下文**：1M tokens
- **输入模态**：文本 + 图像 + 视频 + 语音
- **推理强度**：effort 四档（low / medium / high / xhigh）

## Gemini 4 Hydrogen（2026-11-12，当前 workhorse，Gemini 4 首个公开可得模型）

> 来源：[Google 官方发布博客](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/) + [Antigravity 官方博客](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/)（均 2026-11-12，2026-11-13 全文抓取）；[Model Card](https://deepmind.google/models/model-cards/gemini-4-hydrogen/) 与[官方开发者指南](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-hydrogen)经搜索 snippet 核实（直连超时）；[AA 独立实测](https://artificialanalysis.ai/models/gemini-4-hydrogen-high/providers)；felloai/orcarouter 第三方交叉（细目已标注）。

**基本信息**：
- 2026-11-12 发布，stable 正式版（非 preview），Koray Kavukcuoglu 署名；Gemini 4 世代第三个模型（Argon 09-30 → Carbon 10-28 → Hydrogen 11-12），**首个公开可得的 Gemini 4 模型**
- 官方定位 "built for rapid execution across diverse agentic workflows"——日常编码/agent **执行档**，与 Carbon/Argon（深度长程推理）分工；可独立使用或作为多模型工作流的高效执行引擎
- **血统**：Model card 称 **"adapted from Gemini 4 Carbon"**（felloai 引 card）——旗舰衍生/蒸馏，非独立训练的小模型；解释了 AA 指数 31→51 的代际跳变
- **命名**：Gemini 4 世代延续元素代号，**Flash 品牌在 4 代退役**；Hydrogen 即事实上的 "Gemini 4 Flash"（官方从未用此名）；无 Gemini 4 Flash-Lite，轻量档仍由 3.5 Flash-Lite 承担
- Model ID：`gemini-4-hydrogen`；官方 lifecycle 页：无退役日期公布

**规格**（aistudio latest-model snippet + felloai 引 model card + 官方博客交叉）：
- **统一 1,048,576 token 窗口**：输入+思考+输出共享（3.8 Flash 为 1M 输入 / 64K 输出分离预算）——迁移陷阱源
- 输出默认上限 65,536；**background long decode 模式最高 1M**（承接 Argon 🌟 1M 输出 + Long Decode Continuation，首次下放公开档）
- 输入：文本/图像/音频/视频/PDF；输出：仅文本（不生成图像/音频）
- 知识截止：**2026-03**（Model Card snippet，与 Argon card 一致）
- **thinking_level 四档**：low / medium / **high（默认）** / **xhigh（新增）**；默认档由 3.8 Flash 的 medium 上调至 high（官方指南 snippet）；官方警告 xhigh "can cause overthinking on simpler prompts"；Gemini app 仅暴露 low/medium/high，xhigh 限 API/Antigravity（felloai）；对照 Carbon/Argon 默认 medium、上限 high

**定价**（官方博客 + [Cloud 定价页](https://cloud.google.com/model-garden/pricing) snippet）：**$1.50 输入 / $7.50 输出 per 1M tokens，全 1M 窗口 flat**（无长上下文加价）；缓存命中 $0.075（95% off），**仅隐式缓存**（≥4096 tokens 自动生效），不支持显式 cachedContents；思考 token 按输出计费；数据政策：免费档数据用于产品改进，付费档不用于改进

**可用性**（官方博客 + felloai 引官方帮助页）：Gemini API 免费+付费 / AI Studio / Android Studio / Gemini for business / Gemini app（**Plus $4.99 起可手选**；免费用户仅 Auto 路由命中时用到，多数 prompt 走 Flash-Lite）/ **Google Search 全球全用户**（官方称 Search 史上最大模型升级，query fan-out 增强）/ Antigravity（付费 Pro/Ultra）/ Sheets；已成为 Gemini Managed Agents 中 Antigravity agent 的默认模型（felloai）

**Orchestrator**（Antigravity 同日上线，官方博客）：
- **单轨迹内 Carbon↔Hydrogen 动态双向切换**：Carbon 只读探索依赖/消歧/定计划（含显式重规划触发器）→ Hydrogen 写码/改包/跑测试 → 遇阻交回 Carbon 检修计划再续跑；官方明确批评静态 model router（按首 prompt 猜难度一次性路由）在长运行 agent 上失效
- Terminal-Bench 近 Carbon 成功率、**quota -24%、速度 +19%**（主博客写 TB 4.0、Antigravity 博客写 TB 4.1，两处官方口径不一，引用需注明）
- 订阅分层：Ultra 得 Orchestrator (Carbon) + (Argon)，Pro 得 (Argon)；并行模式：Carbon 协调者 + Hydrogen worker/verifier 隔离工作区；Antigravity SDK 可显式编排多模型流水线（官方 demo：Hydrogen 做 issue 分诊/编码/UI 迭代，Carbon 做大重构/新特性/安全检查）

**技术亮点与独创性**（本次无 🌟 行业首创；首创属 Argon 1M 输出与 Carbon Gray Swan IPI 0%）：

| 亮点 | 分级 | 依据 |
|------|------|------|
| 旗舰蒸馏（adapted from Carbon）+ 继承 Gemini 4 后训练/安全栈 | ⚙️ 工程优化 | frontier→fast 蒸馏为业界成熟做法；新颖度在跳变幅度（AA +20 点） |
| Orchestrator 轨迹级动态双向切换 | 🔧 组合创新 | GPT-5 实时 router（2025）先行；新颖点在**单条长程轨迹内双向交接 + 摩擦触发回退旗舰**，并给出量化收益 |
| xhigh 第四思考档 | 📋 跟进对齐 | OpenAI reasoning_effort、Claude effort 五档先行 |
| 统一 1M 窗口 | ⚙️ 工程优化 | 非行业首创；简化预算管理，代价是长输入挤占输出 |
| 1M 输出 long decode 下放公开档 | 📋 跟进对齐（自家） | 🌟 首创属 Argon（09-30），Hydrogen 是普及化 |
| MKA benchmark（与 AA 共建） | 🔧 组合创新（评测治理） | 厂商+独立评测机构共建基准，非完全独立第三方，成绩解读需带折扣 |
| 原生并行批量 file-read/search | ⚙️ 工程优化 | 后训练使"先批量"成默认行为；合作伙伴实测 2–2.8× 提速 + token -12~23% |
| CoT 可读性 99.9%、20 万+ 审计轮次零欺骗性推理编辑 | ⚙️ 工程优化（规模化） | 延续 Argon 推理透明路线，扩到 20 万轮审计规模 |

**关键评测**：
- **AA 独立实测**：Intelligence Index high **51** / xhigh **54** vs 3.8 Flash high **31**（+20 点）；51 与 GPT-6.1 Terra 持平、超 Argon 50，低于 Carbon 60 / Sonnet 5.5 55（felloai 引 AA 2026-11-12 表）。输出速度 high ~236 tok/s、xhigh ~198 tok/s（AA，felloai/orcarouter 转述）；单任务成本 high **$1.87** / xhigh $3.16（AA providers 页直抓+交叉）；首答案 token high ~15–19s（AA 滚动窗口：14.96s 表值/18.89s FAQ 值）、xhigh ~41.1s vs 3.8 Flash ~17.1s（orcarouter 引 AA）
- **官方口径**：TB 4.1 **57% vs 3.8 Flash 18.2%**（>3×）；任务完成 **2.5× 快**（high 默认档）；捏造声明 **-5×**（缺上下文时标记而非猜测）；工具调用失败/搜索空结果自适应；合作伙伴 graph/SQL/数据密集工作流 **2–2.8× 提速 + token -12~23%**
- **领域领先项**（官方博客 + felloai 引 Google 对比表，混含厂商自跑/公开榜，不可与独立评测混比）：HLE-Diamond 58.8% 同级第一；Vals Tax Agent Bench 52.3% 总榜第一；Vals Legal Research Bench 55.8% 并列第一；AutomationBench-AA 76.1% 同级第一；MKA 53.4%；Agents' Last Exam v1.1 71.6%；SWE-sweep 13.5%（Sonnet 5.5 仅 3.1% / Terra 5.8%）；Chartography 66.6%；Vending-Bench 2 $14,549（高于 Sonnet $11,165 / Terra $9,107）；Agent Arena #5（arena.ai live）
- **安全**（官方博客）：overreach -81%、under-service -79%、失配动作/任务抄近路 -12×、越权绕过可能性 -2×、内部 agent 诚实率 96.7%、Gray Swan IPI 抗性 2.3×、HealthBench Pro 误拒 <0.4%

**⚠️ 诚实弱点**：
- Google 自家对比表 10 项中 3 项输给 Claude Sonnet 5.5：**TB 4.1 57% vs 63.9%、OSWorld-2.1 77.6% vs 83.9%、TB-Science 0.1 51.4% vs 59.9%**——终端编码/计算机操控/科学任务仍是 Sonnet 强项
- Model card：**无理由拒答率较 3.8 Flash +5.57pp**（多模态 prompt 尤甚）；image-to-text 安全 +7pp（felloai 引 card）
- **TTFT 更慢**："starts later, finishes earlier"——人盯首字的聊天界面 3.8 Flash 体感更快，agent 闭环按总时长计费则 Hydrogen 胜
- xhigh 简单 prompt 过度思考风险（官方警告）；AA 评 xhigh "very verbose"（$3.16/task vs high $1.87）
- 前沿风险评估：较 Argon 无实质能力增量，bio/cyber 低于 critical 阈值但触及 alert 阈值；完整 Safety & Security Report 待发（felloai 引 card）

**成本归因**：
- ⚠️ **token 单价并非更低而是更高**：$1.50/$7.50 = 3.8 Flash 过渡期价格（$0.75/$3.75）的 **2×**。"更便宜"成立于**单任务成本**口径
- **架构内禀降本（主因，可持续）**：AA 实测 $1.87/task（high）vs 3.8 Flash $7.77 / Argon 标准价 $9.95 / Carbon $7.76——**单价贵 2× 但单任务便宜 4.1×**；机制 = 旗舰蒸馏 + 执行纪律 → 每任务输出 token 更少 + 成功率高减少重试；无技术报告，独立实测支撑"真实成本下降"
- **定价策略（辅因）**：**价格收敛设计**——2027-01-01 起 3.8 Flash 涨至 $1.50/$7.50 与 Hydrogen 同价，"升级免费"；当前 2× 差价实为早鸟溢价。Batch/Flex 两者均 $0.75/$3.75、Priority 均 $2.70/$13.50；缓存命中价 3.8 Flash 2027-01-01 起 $0.075→$0.15，Hydrogen 保持 $0.075（orcarouter 引 Google rate card [⚠️ 官方定价页待直核]）
- **系统级降本**：Orchestrator quota -24% / 速度 +19%（官方）——路由层节省，与模型单价无关
- TPU 自研推理栈为长期单位成本优势（KB 既有结论），本次发布无新披露，不作为本次降本归因证据

**迁移陷阱（3.8 Flash → Hydrogen）**（orcarouter 分析与官方指南 snippet 交叉；官方指南页直连超时，细目以第三方转述为主）：
- **四项静默失效（返回 200，行为已变）**：① temperature/top_p/top_k 被服务端静默忽略（3.7 起已废弃，调参 prompt 悄悄回到默认分布）；② 默认思考档 medium→high（延迟与输出计费变）；③ 统一窗口挤占（900K 输入只剩 ~148K 给思考+回答，长上下文任务截断自己的答案而非报错）；④ 显式缓存不支持（仅隐式 ≥4096 tokens、95% off——折扣相同但控制权丢失）
- **两项显式报错**：⑤ minimal 思考档报错（3.8 Flash 同样报错，存量问题）；⑥ 同步输出上限 64K/hop，>64K 需 `background: true` **且** `max_output_tokens > 65536`（上限 1M − 输入），只设 background 不提 max_output_tokens 仍停 64K；max_output_tokens 现在约束 thinking+output 总和
- **官方建议**：从 high 起步，xhigh 留给 high 解不出的多步问题；硬架构/调试/科学/安全审计用 Carbon。**迁移节奏**（orcarouter 建议）：agent/终端/长程负载立即迁；聊天型/首字延迟敏感/显式缓存依赖者可等 2027-01 价格收敛；预留一周行为回归测试，勿在 12 月最后一周迁移

**售前启示（阿里云视角）**：
- Flash 档竞争口径从 $/M tokens 转向 **$/task**——Hydrogen 单价 2× 但单任务便宜 4.1×；对 Qwen Flash 档比价应引入 AA cost/task + 成功率口径，仅比单价会误判
- "旗舰蒸馏 + 执行档定价 + 轨迹级路由"组合拳把 Carbon 锁进执行生态；百炼多模型编排与缓存亲和路由资产可对位叙事
- Gemini 4 免费档 + Search 全用户 = 分发优势；差异化强调 Qwen 开源可私有化部署、中国节点合规、中文能力

## Gemini 4 Carbon（2026-10-28 发布、2026-11-10 公开 API 开放，Gemini 4 世代第二个旗舰）🌟

> 来源：[DataLearner 汇总](https://www.datalearner.com/ai-models/pretrained-models/gemini-4-carbon)（含 Google 发布表原始口径、AA/Vals 独立评测，2026-11-03 核实）；[Google 官方 GA 公告博客](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-carbon-now-available/)（2026-11-10，一手，2026-11-13 全文抓取）。

**基本信息**：
- 2026-10-28 Google DeepMind 发布，Gemini 4 世代第二个模型（Argon 之后）；面向长期自主工程、编程与网络安全防御
- **2026-11-10 公开 API 开放**（官方公告博客）：向所有付费开发者/企业开放（AI Studio / Gemini for business），入门价与 Argon 相同 $2/$10；Google AI Ultra 订阅者可在 Antigravity / Gemini app / Search AI Mode 使用。首发（10-28）曾为 Fairwind 受限，现 **Fairwind Program 仅覆盖 "Carbon for cyber" 无护栏版**（受信防御者申请制）——售前可承诺公开付费 API，无护栏版仍不可承诺
- 官方定位（11-10 博客）："our strongest model"；**Argon 仍是多数软件工程与知识工作的首选**，Carbon 面向测试智力极限的最难任务（复杂多步编码/调试、开放式科学研究），比 Argon 消耗更多 token 做彻底探索、深度推理与扩展验证循环
- 规格（第三方口径，待 Google 确认）：1M 上下文 + 最大输出 1M（Vals 评测配置）；文本+图像+音频+视频输入 → 文本；默认 high 思考档；参数量未公布；公开 API model ID [⚠️ 待补充]

**定价**：入门价 $2 输入 / $10 输出 / 缓存 $0.10（=输入价 5%）；标准价 $4/$20（缓存 $0.20）。入门价至 2026-11-30、12-01 起标准价（felloai 引 Google 定价页 [⚠️ 官方定价页待直核]）。生产预算按标准价测算。

**2026-11-10 GA 公告新增事实**（官方公告博客）：
- **榜单与成本**：CursorBench 4.0 / Perplexity WANDR / Zapier AutomationBench 均 #1，单任务成本比次优外部模型低 2×+；MKA 榜 #2 且平均单任务成本比榜首低 6×+（**MKA 为 Google 与 Artificial Analysis 共建的新基准**——非完全独立第三方，成绩解读需带此折扣）
- **安全/对齐**：agentic honesty benchmark（375 任务）通过率 92%（Argon 70%），98% 情况下拒绝填补缺失实验数据、68% 情况下标记方法学缺陷；阻断 99% 自适应红队攻击轨迹，单次尝试突破率 0.8%（Argon 3.1%）；Gray Swan 自动化网络攻击查询成功率 2.17%（Argon 9.86%）；Trajectory Labs 132 小时 / 13,000+ 请求零新型通用越狱
- **/swarm**（Antigravity 并行 agent 团队）预览：上线数日即数万 swarm；Carbon 承担架构设计/协调/审计等最深推理角色，搭配轻量模型并行隔离工作区与对抗验证器
- **科学家计划**：10,000 名科学家免费 6 个月 Argon 访问（4 周前开放申请，已 onboard 数千人），11-10 起扩展至 Carbon，每周滚动审核
- **科学推理案例**：AlphaProof Code 用 Carbon 生成数百万行 Lean 代码，数周内证明 Signal 密码协议关键安全性质（传统需专家团队数年）；CASP17 低同源蛋白家族同源检索平均提升 40×；Axiom Bio 将生产科学分析迁移至 Carbon/Argon

**独立评测与榜首**：
- **AA Intelligence Index v5.0 = 60**（2026-11-08 首页 live 值，当时 #1/76；10-28 宣布新榜首时为 59；⚠️ 2026-11-09 AA 收录 Claude Fable 5.2 = 65（v5.0.1）登顶，Carbon 退居其次）：Claude Opus 5.5 59、GPT-6 Astra 57、Gemini 4 Argon 50、Claude Fable 5.1 49。⚠️ AA 指数随新模型发布重校准，下方 Google 发布对比表保留 10-28 原始口径（59/58/57），跨时间引用需注明查询日期
- AA Coding Agent Index v2.0 = 59（Antigravity CLI）、AA-Briefcase 1609 Elo、AA-Omniscience v1.1 = 54（正确率 58%、幻觉率 11%）
- 标准价下 AA 实测 **$7.76/task**（比 Opus 5.5 max $10.04 低约 23%）、约 123K output tokens/task
- Vals Index v2.2 = 70.36%（#2/28）

**Google 发布对比表（原始口径，不同 harness/评测者不可混比）**：

| 评测 | Carbon | Argon | GPT-6 Astra | Opus 5.5 |
|------|--------|-------|-------------|----------|
| AA Index v5.0 | **59** | 50 | 57 | 58 |
| Terminal-Bench 4.0 (AA) | **65.2** | 57.1 | 59.1 | 59.6 |
| FrontierSWE 2 | 61.2 | 55.0 | **65.5** | 62.3 |
| OSWorld 2.1 offline | 81.5 | 74.7 | 80.9 | **87.2** |
| AutomationBench (Zapier) | **53.9** | 51.3 | 41.4 | 42.5 |
| GraphWalks 256K–1M BFS F1 | **96.2** | 84.2 | 71.8 | 66.8 |
| SEC-bench Pro | **88.2** | 83.4 | 85.4 | — |
| ExploitGym (10h) | **54.8** | 42.0 | 42.4 | 34.5 |

**安全能力（最大亮点）**：SEC-bench Pro 88.2%、CWE-bench v1 71.0%、ExploitGym 54.8%（10h 预算；安全评测无护栏运行）；Gray Swan 间接提示注入攻击成功率 **0.0%**（Argon 为 0.7%）；内部安全代码生成成功率超 Argon 两倍（Google 内部口径，非独立排名）。

**与 Argon 的关系**：世代内旗舰接棒——AA v5 指数 Carbon 60 vs Argon 50；Argon 的 🌟 1M 输出上限与 AA 最低幻觉率（15%）仍是差异化规格。两者均已公开可得（Argon 10-13 GA [⚠️ 第三方信源] / Carbon 11-10 API 开放）；官方口径 Argon 仍是多数软件工程与知识工作首选，Carbon 面向最难任务。注意：Hydrogen（adapted from Carbon）AA high 51 已超 Argon 50，见 Hydrogen 专章。

## Gemini 4 Argon（2026-09-30，Gemini 4 世代首发旗舰）🌟

> 来源：[Google 官方博客](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/)（2026-09-30，Kavukcuoglu 署名）、[felloai 汇总](https://felloai.com/gemini-4-argon/)（AA/Vals/LMArena 第三方数据、Fairwind 细节、Bloomberg 内部质疑报道）；2026-10-09 合并入库。GA 状态 2026-11-13 更新：[digitalapplied](https://www.digitalapplied.com/blog/gemini-4-argon-generally-available-migration) 与 [felloai Hydrogen 汇总](https://felloai.com/gemini-4-hydrogen/) 一致报 10-13 公开 GA，官方 Model Card 页发布日期 10-13，官方 11-10 Carbon 博客口径佐证。

**基本信息**：
- 2026-09-30 发布，**Gemini 4 世代首个模型**、Google 自 Gemini 3.1 Pro（2026-02）以来首个旗舰（7 个月旗舰空窗；3.5 Pro 确认搁置）
- **"Argon"（氩）为首个代号式命名的 Gemini**，类比 OpenAI Astra/Sol/Luna 的天体命名；官方称 Argon 为 "early post-training output"
- 发布者 Koray Kavukcuoglu（SVP Google DeepMind & Chief AI Architect，已从 OpenAI 移职）
- 定位 "our next era of frontier intelligence"：real-world software engineering、enterprise knowledge work（法律/金融）、cybersecurity defense、creative writing；"built to sustain deep reasoning across complex, long-horizon workflows"
- 规格：**输出上限 1M tokens**（上代 64K，行业最高）；上下文 1M（Artificial Analysis 口径）；文本+图像输入（AA 列表另含 video/speech 输入）。**Model Card 已发布**（页面发布日期 2026-10-13，原"未发 model card"口径已过时）；知识截止 2026-03（Hydrogen 素材确认与 Argon card 一致）；官方 API model ID [⚠️ 待补充]

**访问状态（2026-11-13 更新）**：首发（09-30）仅 Fairwind Program（650+ 合作伙伴：政府/国家 cyber 机构、医疗·电信·能源·金融关键基础设施运营商、核心技术平台、防御性 benchmark 学术实验室；需钓鱼抗性 MFA、禁转售），Fairwind 伙伴与 Google 内部团队获**无 cyber 护栏版** + CodeMender 集成，并参与美国政府自愿 pre-release 审查。**2026-10-13 公开 GA**（digitalapplied/felloai 第三方一致 + 官方 Model Card 页发布日期 10-13；官方 11-10 Carbon 博客 "Carbon joins Argon in our family of frontier models across our products" 佐证）[⚠️ GA 日期为第三方信源，官方 changelog 未直核]。Gemini app 中 Argon 为 Pro 档（$19.99）前沿模型，Ultra 亦含（felloai 引官方帮助页）。Fairwind 无护栏版仍面向受信防御者——**公开版售前可承诺，无护栏版仍不可承诺**。

**定价**：标准价 **$4 输入 / $20 输出 per 1M tokens（与 Opus 5.5 同价）**，cached 95% off。生产预算按标准价测算。

**技术亮点与独创性**：
1. 🌟 **首创｜1M token 单响应输出上限**（行业首个；此前行业最高 128K——Claude/GPT 系，Gemini 3.x 为 64K）+ 配套 **Long Decode Continuation** API（超长输出暂停/续传，防请求超时）——此前无同类：输出上限从未被作为主打规格突破。专为"单次轨迹完成长程任务"设计：全库代码迁移、超长法律文书、数小时连续推理
2. 📋 **跟进对齐｜无护栏版 + 可信防御者受限访问（Fairwind）**：Anthropic Project Glasswing（Mythos 5）与 OpenAI Daybreak（Astra）先行——三大前沿厂商 2026 年内全部采用"最强 cyber 能力 → 受限分阶段发布"同构模式
3. ⚙️ **工程优化**：DeepSWE v1.1 **77.9% SOTA**（Opus 5.5 74.2 / Astra 74.1 / GPT-6 Sol max 68.8 / Gemini 3.7 Flash 65.3）；Vals Index 68.9% #1/41；AA 幻觉率 **15%（AA 实测领先模型最低**：Astra 51%、GPT-6.1 Sol 54%）——代价是事实题答对率 -13pp（更多拒答）；LMArena Text Arena #1（1525 分，coding/hard prompts/指令跟随/创意写作分类均第一）
4. 🔬 **独特路线**：CoT + 行为实时监控用于失配缓解（监控发现刻意不回流训练，防模型"学会规避监控"），公开呼吁全行业保持推理透明——与 Astra"书面推理更难监控"的困境形成 alignment 监控的两条路线对照

**能力领先项**：Harvey Legal Agent **19.6% vs Opus 5.5 3.8% / Astra 5.4%**（法律工作 ~5× 领先，最大单项差距）；Vals Finance Agent v2 65.4%；AutomationBench 51.3% #1（Opus 5.5 42.5、Astra 41.4）；GraphWalks 84.2%（长上下文）；LVBench 91.7%（长视频）；Gray Swan IPI 提示注入攻击成功率 **0.7%**（Opus 5.5 1.0%、Astra 8.5%）；CWE-bench v1 68% 并列第一；IOI 编程奥赛 100%（与 Astra 并列）。

**增量解锁**：①1M 输出 → 全库级迁移/超长文书"一口气"完成（Google 内部实证：Fuchsia Zircon 内核 800K+ 行 C/C++→Rust、libgav1 32K 行 SIMD 重写后 2.7× 提速、数据中心内存优化释放 300 TiB（预计 500 TiB–1 PiB）、量子算法超已发表 baseline 40%）②最低幻觉率 → 高可信知识工作（法律/金融）③防御性 cyber 生产工具（Wiz Scan for Good 实战发现全球医院医疗软件严重漏洞——前代前沿模型均未发现）。

**⚠️ 落后项（Bloomberg 报道内部质疑部分印证）**：Terminal-Bench 4.0 57.4% vs Opus 5.5 **66.4%**；FrontierSWE v2 55.0% vs Astra **65.5%**；Code Arena: WebDev 仅 #8（前端弱）；AA Intelligence Index 53 = Astra = Fable 5.1，低于 Opus 5.5 58 / Sonnet 5.5 56（均为 2026-09-30 Argon 发布时口径）。

**AA 成本实测**：促销期 $1.99/task、标准价 $3.98/task（Astra $3.26、Opus 5.5 $5.98）；**62K output tokens/task（Astra 27K）——低价靠单价而非省 token**。

**成本归因**：低价主要来自定价策略而非架构内禀降本（无技术报告）——AA 明确"低价来自 token 单价而非用量"（输出 token 用量为 Astra 的 2.3×）；第三方成本效率口径（AA $1.99/task、LMArena "most cost efficient model"）建立在促销期价格上，标准价下需重估。Google 自有 TPU 推理栈是长期单位成本优势（知识库已有结论），但本次发布无相关披露。

**与 Hydrogen 的关系（2026-11-13 更新）**：Hydrogen（adapted from Carbon）AA high 51 已超 Argon 50，且 🌟 1M 输出经其 long decode 下放公开档——Argon 的差异化收窄至单轮深度推理与最低幻觉率；官方定位仍称 "Argon remains the ideal choice for the majority of software engineering and knowledge work"（11-10 Carbon 博客）。AA 单任务成本 Argon 标准价 $9.95 vs Hydrogen $1.87（felloai 引 AA 2026-11-12 表）。

## Gemini 3.8 Flash / 3.8 Flash Cyber（2026-09-02，workhorse 已由 4 Hydrogen 接棒，仍在售）

> 来源：[Google Blog — Introducing Gemini 3.8 Flash and 3.8 Flash Cyber](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/)（2026-09-02，官方一手）；2026-11-03 合并入库
>
> ⚠️ **2026-11-12 workhorse 已由 Gemini 4 Hydrogen 接棒**（官方开发者指南 "Recommended upgrade from Gemini 3.8 Flash and earlier Gemini 3 and 2.5 models"）；无退役日期、API 仍在售；2027-01-01 起价格升至 $1.50/$7.50 与 Hydrogen 同价；Gemini app 已不再列出。迁移陷阱见 Hydrogen 专章。以下为发布时历史记录。

**基本信息**：
- 2026-09-02 发布（3.7 后三周、六周内第三个 Flash）；官方口径 "Gemini 3.8, our best reasoning and coding model yet, at the same speed and low cost of 3.7"
- **3.8 Flash**：most intelligent workhorse model——软件工程、agentic 任务与专业领域多步推理显著提升；入门价同 3.7（$0.75/$3.75 至 2026-12-31，2027-01-01 起 $1.50/$7.50）
- **3.8 Flash Cyber**：最强网络安全模型，经 Fairwind Program 向受信防御者开放
- 训练：长程 agentic loops 递归评估与精炼底层模型 + 网络安全高要求领域严格训练，驱动共享核心能力提升（官方口径）

**关键评测**：
- HLE-Verified **54.9%**（官方）；Vals Finance Agent V2 与 Harvey's Legal Agent Benchmark 超 3.7 Flash 及其他前沿模型（官方）
- DeepSWE v1.1 **73.7%**（vs Opus 5 74.0%，第三方 tmtpost/36kr 口径；官方图为"超越大多数更大前沿模型"）；Terminal-Bench 4.0 **19.09%**（官方 tbench 榜单，mini-SWE-agent·high；Vals 独立 harness 19.70%）——旧 TB 2.1 口径的 89.4% 已停用
- Gray Swan prompt injection 鲁棒性大幅跃升（官方）；CBRN + cyber offense 防护（Frontier Safety Framework）

**核心设计 "works harder"**：复杂任务执行更多推理步骤、迭代调用工具——高档位下 token 消耗可能增加；**效率优先场景可用低 effort 档或继续用 3.7 Flash（官方 fully supported）**。API 沿用 `thinking_level` 三档枚举（替代 thinking_budget）。

**3.8 Flash Cyber 实战**：CyberGym 前沿级自主漏洞发现（超 3.5 Flash Cyber 与更大前沿模型）；内部 20 语言漏洞发现成功率 >70%；CWE-Bench（Collinear）修复 pass@1 **47.2%**（对照前沿模型 47.8%，成本显著更低）；Chrome 团队正确补丁数为更大商用模型 **2.6×**；Wiz 内部渗透测试 recall +7.5–9.7%、成本 1/2.3–1/5.2；Google Cloud VR 团队 <2 小时发现关键基础漏洞

**可用性**：Gemini API（AI Studio / Android Studio）、Gemini Enterprise、Antigravity、Stitch；消费者 Google AI Pro / Ultra（Gemini app、Search AI Mode、Sheets）

## Gemini 3.7 Flash（2026-08-13 发布；workhorse 已由 3.8 接棒，仍支持效率优先负载）

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
- **能力跃升**（vs 3.1 Flash-Lite）：GDM-MRCR v2 72.2% vs 60.1%；GDPval-AA v2 1140 vs 642（TB 旧版 2.1 相对值已按全库规则停用；双方均无 TB 4.0 数据）
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
| 多模态企业知识库 | Hydrogen / Carbon | Hydrogen MKA 53.4% / Agents' Last Exam 71.6%（官方）；深度推理与最难任务选 Carbon |
| Agent 规模化部署 | Hydrogen（效率优先可低档或 3.8 Flash） | workhorse，$1.50/$7.50 flat；AA $1.87/task vs 3.8 Flash $7.77；Orchestrator 搭配 Carbon 再省 24% quota |
| 高吞吐批量/subagent 扩展 | 3.5 Flash-Lite | 350 tok/s，$0.30/$2.50，适合 agentic search/文档处理高并发；app 免费档主力 |
| 复杂推理/学术难题 | Carbon / Argon | 公开可得旗舰（3.1 Pro 上代仍可调用）；HLE-Diamond Hydrogen 58.8% 同级第一，最难任务 Carbon |
| 实时音视频交互 | Omni Flash | 原生端到端音频/视频理解 |
| 代码辅助 | Hydrogen | TB 4.1 57%（3.8 Flash 18.2%）、AA 51/54；终端编码/计算机操控仍 Sonnet 5.5 更强（Google 自家表） |
| 前沿旗舰（公开可得） | 4 Carbon 🚩 / 4 Argon | AA v5.0 = 60（Carbon，2026-11-08 曾榜首、现 Fable 5.2 登顶，见 benchmark 统一口径）；Carbon 11-10 API 开放 / Argon 10-13 GA [⚠️ 第三方信源]；Fairwind 仅限无护栏 cyber 版 |
| Google Workspace AI | Hydrogen（Sheets） | Gemini in Sheets 已接入 Hydrogen（官方）；Gmail/Docs 历史为 3.1 系内嵌 |

## 平台交付方式

Gemini 通过 **Gemini Enterprise Agent Platform** 统一交付（见 [`vertex-ai.md`](../ai-platform/vertex-ai.md)）。开发者可选两种接入路径：

| 路径 | 接口 | 适用 |
|------|------|------|
| **Gemini API / AI Studio** | `google.genai` | 快速原型、单次推理、个人开发者 |
| **Agent Platform** | `vertexai`（原 Vertex AI API） | 企业级 Agent 构建、生产部署、治理优化 |
| **Gemini App / Search AI Mode** | 消费者界面 | App：Hydrogen 自 Plus $4.99 起可手选（免费用户仅 Auto 路由，多数 prompt 走 Flash-Lite），Pro 加 Argon、Ultra 加 Carbon；Search：2026-11-12 起 Hydrogen 全球全用户（官方称 Search 史上最大模型升级） |
| **Antigravity 2.0** | 独立桌面 Agent IDE | Agent 开发者，对标 Claude Code / Cursor |

> **新产品/能力**：
> - **Antigravity 2.0**：独立桌面 Agent 开发环境，支持并行子 Agent 执行、定时任务（后台自动化）、CLI + SDK，与 AI Studio / Android / Firebase 集成。Gemini CLI 用户可迁移至 Antigravity CLI。**Orchestrator**（2026-11-12）：单轨迹内 Carbon/Argon↔Hydrogen 动态双向切换（Ultra 得 Carbon+Argon 版、Pro 得 Argon 版）；**/swarm**（11-10 预览）：并行 agent 团队，上线数日即数万 swarm。
> - **Managed Agents**：单次 API 调用即可启动完整 Agent（推理 + 工具调用 + 代码执行），隔离 Linux 环境，跨调用持久化。2026-11-12 起其 Antigravity agent 默认模型为 Hydrogen（felloai）。
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
| 学术推理 | Humanity's Last Exam 输 4.2 分、ARC-AGI-2 输 5.0 分（3.5 Flash vs 3.1 Pro 历史数据），极难学术问题选 Carbon/Argon（3.5 Pro 已官方搁置） |

> 📌 **Gemini 3.5 Pro 确认搁置（更新 2026-11-13）**：原预计 2026.06 发布，多次跳票后，Kavukcuoglu 于 2026-09-24 公开确认 "took a little bit of a step back"——重心转向 Flash 线与 Gemini 4。售前沟通中不应承诺 3.5 Pro。**Gemini 4 世代已全面公开**：Argon 09-30 发布 / 10-13 GA [⚠️ 第三方信源]、Carbon 10-28 发布 / 11-10 API 开放、Hydrogen 11-12 接棒 workhorse（Flash 品牌在 4 代退役，3.8 Flash 仍在售无退役日期）。

## 参考资料

- [Google Blog — Introducing Gemini 4 Hydrogen](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/)（2026-11-12，官方一手）
- [Google Antigravity Blog — Gemini 4 Hydrogen and Orchestrator](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/)（2026-11-12，官方一手）
- [Google Blog — Gemini 4 Carbon is now available](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-carbon-now-available/)（2026-11-10，官方一手，Carbon GA）
- [Gemini 4 Hydrogen Model Card](https://deepmind.google/models/model-cards/gemini-4-hydrogen/)（知识截止 2026-03，snippet 核实）
- [Gemini 4 Hydrogen 官方开发者指南](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-hydrogen)（model ID / 默认 HIGH / XHIGH / 迁移指引，snippet 核实）
- [Gemini 模型版本与生命周期](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions)（Hydrogen 2026-11-12、无退役日期）
- [AA — Gemini 4 Hydrogen (high) providers](https://artificialanalysis.ai/models/gemini-4-hydrogen-high/providers)（$1.87/task 独立实测）
- [felloai — Gemini 4 Hydrogen 汇总](https://felloai.com/gemini-4-hydrogen/)（model card 转述 / AA 11-12 表 / 订阅分层 / Argon GA）
- [orcarouter — Hydrogen vs 3.8 Flash 迁移分析](https://www.orcarouter.ai/ru/blog/gemini-4-hydrogen-vs-gemini-3-8-flash)（六项迁移变更 / 价格收敛细目）
- [Google Blog — Introducing Gemini 3.8 Flash and 3.8 Flash Cyber](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/)（2026-09-02，官方一手）
- [DataLearner — Gemini 4 Carbon 评测/价格/参数汇总](https://www.datalearner.com/ai-models/pretrained-models/gemini-4-carbon)（含 Google 发布表与 AA/Vals 独立评测，2026-11-03 核实）
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
| 2026-11-23 | 校验修复（knowledge-verification-2026-11-23）：新增 Gemini 4 Neon 专章（11-18 发布，AA v5.0.1 xhigh=61 总榜第 3，$3/$15，七周内第四款）；主推表与头部同步收录 Neon；index.md / README.md mindmap 同步代号 |
| 2026-11-20 | 口径修订（全库 TB 4.0 规则）：3.8 Flash 改引官方榜单 TB 4.0；3.5 Flash-Lite / 3.1 Flash-Lite 旧版 TB 相对量停用 |
| 2026-11-20 | 校验修复：清理限时促销/免费额度等营销性信息，定价保留官方标准列表价口径 |
| 2026-11-13 | 合并：Gemini 4 Hydrogen 发布调研（inbox 20261113）——新增 Hydrogen 专章（workhorse，adapted from Carbon、AA 51/54、$1.50/$7.50 flat、统一 1M 窗口、四档思考、Orchestrator、迁移六陷阱）；**修正 Carbon/Argon 可得性：Carbon 11-10 公开 API 开放（官方一手）、Argon 10-13 GA [⚠️ 第三方信源]，Fairwind 仅限无护栏 cyber 版**；入门价至 11-30 [⚠️ 待核实]；3.8 Flash / 3.1 Pro 移出主推表入历史模型（3.8 Flash 无退役日期仍在售、2027-01-01 价格收敛）；场景/平台交付/参考资料同步 |
| 2026-11-11 | 校验修复（knowledge-verification-2026-11-11）：AA 榜首口径同步——Fable 5.2（v5.0.1）2026-11-09 收录登顶，Carbon 60 改“曾榜首”历史口径（头部/主推表/专章/场景表 4 处），指向 benchmark 全库统一口径；Changelog 折叠最早 2 条 |
| 2026-11-08 | 校验修复（knowledge-verification-2026-11-08）：AA Intelligence Index v5 刷新 Carbon 59→60（标查询日期；发布对比表保留 10-28 原始口径 59）；与 Argon 关系对比、头部/主推表同步，Argon 落后项行补口径日期 |
| 2026-11-03 | 校验修复+补研（knowledge-verification-2026-11-03）：新增 Gemini 4 Carbon 专章并切为 🚩（AA v5 = 59 新榜首，Fairwind 受限）与 3.8 Flash / Cyber 专章（官方一手）；workhorse 统一为 3.8，3.7 转为官方支持的效率优先选项（非简单取代）；头部主推/历史关系/场景同步，解除 3.7/3.8 内部不一致 |
| 2026-10-19 | 校验修复（knowledge-verification-2026-10-19）：3.8 Flash 待补充处回填定价——入门价 $0.75/$3.75 至 2026-12-31（Google 官方云定价页 snippet 核实）；详细规格待 miner 补研 |
| 2026-10-09 | 合并四模型调研素材：**新增 Gemini 4 Argon 专章**（09-30 发布，🌟 1M 输出上限行业首个 + Long Decode Continuation、Fairwind 受限访问、DeepSWE 77.9% SOTA、AA 幻觉率 15% 最低、领先/落后项与成本归因全量）；主推表加 Argon（受限标注）并调整 3.1 Pro 为"公开可得旗舰"；**补记 3.8 Flash / 3.8 Flash Cyber 已存在**（[⚠️ 详情待补充]）；3.5 Pro 从"跳票预期"改为"官方确认搁置（09-24）"；头部当前主推重写 |
| 2026-08-17 | 合并：inbox 四模型调研 - 新增 Gemini 3.7 Flash 章节（2026-08-13 发布，新 workhorse 🚩：入门价 $0.75/$3.75 至 2026-12-31 / DeepSWE 65.3% / thinking_level 三值枚举等 4 项 API 变化 / 部署 Gemini Spark+Antigravity）；主推表重排（3.7 Flash 顶替 3.6 Flash，3.6 Flash 仅存活三周移入历史标注）；适用场景与平台交付表同步 |
| 2026-07-27 | 精简：3.5 Flash 深度分析章节（~80 行）压缩为"上代模型存档"小节，保留战略意义/关键参数/Computer Use 起源，删除过时 benchmark/定价详表；诚实弱点与平台交付口径同步 |
| 2026-07-27 | 合并：2026-07-21 三模型发布官网调研 — 新增 Gemini 3.6 Flash（新 workhorse 🚩，$1.50/$7.50，token 效率 -17%）/ 3.5 Flash-Lite / 3.5 Flash Cyber 章节；主推表重排（3.5 Flash 降为上代）；3.5 Pro 跳票与 Gemini 4 预训练启动；适用场景表同步 |
| 2026-06-29 | 合并：Gemini 3.5 Flash Computer Use 官网调研 — 新增 Computer Use 内置工具章节（2026.06.24 发布，跨平台支持，安全机制），核心能力表新增 Computer Use 行，当前主推描述更新 |
| 2026-06-09 | 合并：Gemini 3.5 Flash 深度分析 — 补充 benchmark 详细对比表（vs 3.1 Pro）、定价、战略意图、Antigravity 2.0、Managed Agents、Gemini Spark、真实落地案例、诚实弱点、3.5 Pro 预期、参考资料 |

<details>
<summary>历史早期记录（2026-05 ~ 2026-06 上旬）</summary>

| 日期 | 变更内容 |
|------|----------|
| 2026-06-09 | 修正：Gemini 3 Pro / 3.1 Pro 版本关系——3 Pro 为上代旗舰，3.1 Pro 为当前旗舰；适用场景表同步修正 |
| 2026-05-31 | 修正：Gemini 2.5→3.x 系列为最新代。新增 Gemini 3 Pro、3.5 Flash、Omni Flash、3.1 Pro/Flash。标注 Gemini 3.5 Pro 预计 2026.06 发布 |

</details>
