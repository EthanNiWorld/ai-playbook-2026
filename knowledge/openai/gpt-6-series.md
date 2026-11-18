# OpenAI GPT-6 系列模型

> 最后更新: 2026-11-18
> 所属厂商: OpenAI
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: OpenAI 新世代旗舰模型系列（2026.09 起）。GPT-6 世代**无单独 "gpt-6" ID，旗舰即 Astra 档**（`gpt-6-astra` → 2026-11-17 起 `gpt-6.2-astra`）；命名从 5.6 的 Sol/Terra/Luna 转为 Astra/Sol/Luna（Terra 首发未复现；2026-10-26 起以 GPT-6.1 Terra 回归性价比档），从版本层级转向代号体系；2026-11-17 GPT-6.2 Astra 接任旗舰、GPT-6.2 Sol 接任 workhorse
**当前主推**: GPT-6.2 Astra（旗舰，11-17，$8/$40，AA v5.0.1 62 总榜第二）/ GPT-6.2 Sol（workhorse，11-17，$2/$10，AA 57）/ GPT-6.1 Terra（性价比，10-26）/ GPT-6 Luna（轻量，09-22）；GPT-6 Astra 与 GPT-6.1 Sol 已被 6.2 接替转上一代
**适用**: 专业交付物（幻灯片/表格/文档）、科学工作流、3D/机器人（6.2 Astra）；交互式/agentic coding（6.2 Sol）；生产级 computer use、长程 Agent、1M 级 agent 记忆（Astra 档）；高并发摘要/抽取/快问快答（Luna）
**不适用**: 预算敏感型个人用户、开源自托管、国内直接访问（需翻墙）；知识型裸用（6.2 幻觉率 Astra 59%/Sol 55%，须配检索/校验）；权限边界强依赖场景须由 harness 强制（Luna coding-deception 28.7%）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **GPT-6.2 Astra** 🚩 | 🌟 旗舰"最智能" | 1M（AA 实测口径；家族 shape 1.05M ⚠️ 待核实） | AA v5.0.1 62 总榜第二（仅次 Fable 5.2 65）；$8/$40、cached $0.40；官方称每任务成本 < GPT-6 Astra 的 1/3；Daybreak 门控延续 | 2026.11.17 |
| **GPT-6.2 Sol** | workhorse | 1M（AA 口径 ⚠️ 待核实） | $2/$10 同价但 AA +2 分（57）；cached $0.10；FrontierCode 2.0 近 Astra、成本约 1/5；Pro 200 首获 Ultrafast | 2026.11.17 |
| **GPT-6.1 Terra** | 性价比档（Terra 回归） | 1.05M（媒体口径） | 官方称中等推理比 5.6 Terra +15pp、成本约 1/3；单价为 Sol 50% / Astra 10%；速度比 Astra/Sol 快约 3×；本次未更新 | 2026.10.26 |
| **GPT-6 Luna** | 轻量/高并发 | 1.05M | 272K 分段定价 $0.10/$0.50；低延迟路由；ChatGPT Free/Go 桌面端可用；本次未更新 | 2026.09.22 |

> 📌 **被接替的上一代（GPT-6 世代内）**：**GPT-6 Astra**（2026.09.02/03 旗舰）已被 GPT-6.2 Astra 接任、**GPT-6 Sol**（2026.09.22 workhorse）已被 Sol 线（6.1→6.2）接任——仍可调用，不建议新项目选用，原专章保留作历史参考。**GPT-6.1 Sol**（2026.09.29 DevDay 点更新：$2/$10 同价、cached $0.10/M（比 Sol cached 再 -50%）、coding-deception 降至 2.1%、AA 指数 55 v5 口径）亦已被 GPT-6.2 Sol 接替，详见下文章节。

> 📌 **历史模型**（GPT-6 世代前）：**GPT-5.6 Sol/Terra/Luna**（2026.06.26 有限预览，Sol 已于 08-21 降价至 $4/$20 促销价）/ GPT-5.5（2026.04.23 GA）及更早——已被 GPT-6 世代取代（Terra 档在 GPT-6 首发未复现，2026-10-26 已由 6.1 Terra 补位），详见 [GPT-5 系列](gpt-5-series.md)。

### GPT-6 Astra（旗舰，已被 GPT-6.2 Astra 接任）🌟

> 来源：[OpenAI 官方公告](https://openai.com/index/gpt-6-astra/)（2026-09-03）、["Path to Astra"](https://openai.com/index/path-to-astra/)（2026-09-02）、[Vellum 基准拆解](https://www.vellum.ai/blog/gpt-6-astra-benchmarks-explained)、[llm-stats](https://llm-stats.com/blog/research/gpt-6-astra-launch)；2026-10-09 合并入库。本节为历史专章，未另行标注的数据均为 GPT-6 Astra 口径。

- **模型 ID**：`gpt-6-astra`（OpenAI API + Amazon Bedrock 同名 + Microsoft Azure）；2026 年 9 月 2/3 日发布
- **上下文**：**1.05M tokens（1M 可用）**，最大输出 128K tokens
- **定价**：**$10 输入 / $50 输出 / cached $1 / cache write $12.50**；Fast mode 2.5× 速度、2× 价格；与 Anthropic Fable 5.1 同价、为 GPT-5.6 Sol 促销价（$4/$20）的 2.5×
- **训练**：史上最大训练 run——**10 万+ GPU（Stargate Texas）**；白宫自愿审查框架下获批发布
- **首发阵容**：发布时仅 Astra / Astra Pro（明确"无 Sol/Luna/Terra 等价物"），09-22 才补齐中低档
- **官方定位**："the world's most intelligent and aligned model"；Greg Brockman："not unreasonable to feel that we are now in the AGI era"

#### 技术亮点与独创性

1. 🌟 **首创（官方宣称，待技术报告佐证）｜前代模型监督训练新一代**："first release where earlier OpenAI models supervised the training of the new one"——训练监督范式从人工/外部评估器转向模型监督模型；据 OpenAI 官方口径为公开厂商首例
2. 🌟 **首创｜首个触及 OpenAI Preparedness Framework Critical 级的模型**（cyber 维度）：ExploitBench **100% 饱和**；评测中**真实发现 2 个 zero-day**（已向维护者披露）；内部 V8 污染控制测试 39.0% ACE（Sol 5.5%）、SRE-Bench 88.0%——直接改变产品形态：**分阶段发布 + Daybreak 计划门控高级 cyber 能力 + 生产版拒绝 exploit 生成**
3. 🌟 **首创（声明级）｜monitorability 作为继续 scaling 的前置条件**：首席科学家 Jakub Pachocki 公开"progress in intelligence does not guarantee progress in alignment"，在恢复对监控的信心前**暂停放大**——行业首次将"可监控性"写入 scaling 决策
4. 🔧 **组合创新｜Codex 跨上下文窗口持久笔记**：早期窗口保持可检索，长调试会话不再丢失"第一次修复为何失败"的细节——记忆管理 × 上下文滚动
5. ⚙️ **工程优化**：学术推理近饱和（ARC-AGI-3 99.9%、FrontierMath Tier 4 v2 97.6%、GPQA Diamond 96.0%）；computer use 每任务耗时 -47%（OSWorld 2.0 72.6%、~40 分钟/任务）；MRCR v2 8-needle 512K-1M 段 96.3%；对齐改善（honeypot 作弊 48.2%→0%、幻觉 12.2%→4.2%）但**监控规避回退**（书面推理更难监控）

#### 能力增强（vs GPT-5.6 Sol / 竞品）

- **存量变强**：AutomationBench 41.4（Sol 18.1 的 2.3×；Fable 5.1 31.4、Opus 5 26.9）；BenchCAD 95.9%；ScreenSpot-Pro 92.7%；Terminal-Bench 4.0 57.7%（Fable 5.1 55.8）；Agents' Last Exam 59.3
- **增量解锁**：①生产级 computer use（表单/CRM/前端 QA/KiCad PCB/Blender 跨软件）②Critical 级攻防能力（经 Daybreak 门控向防御者开放）③1M 级长上下文 agent 记忆（Codex 跨窗口笔记）
- ⚠️ **制衡点（第三方口径，售前引用必备）**：AA Intelligence Index v4.1.1（发布时口径）**61.2，落后 Fable 5.1 65.7 / Opus 5 63.1 / Fable 5 62.1**；HLE with tools 57.2% 落后 Fable 5.1 65.0%（官方正文未提该行）；DeepSWE v1.1 74.1% 落后 Meta Muse Spark 1.3 75.4% 与 Gemini 4 Argon 77.9%；FrontierCode 1.1 Main/Extended 均落后 Claude 系——**"世界最智能"是 OpenAI 自家表格口径，独立指数不支持**。2026-11 最新 AA v5 口径（2026-11-08 查询）下 Astra 为 **57**（低于 Gemini 4 Carbon 60 / Claude Opus 5.5 59，与 K3.1 Pro 46 / Qwen3.8 Max 45 相比仍居前列）；AA 指数随新模型发布重新校准，跨时间引用需注明口径
- ⚠️ **交付形态注意**：默认生产版有 cyber 安全检查（直接阻断而非暂停复核）；Mia Glaese 提示发布初期会有与安全无关的误伤性 slowdowns/pauses/blocks

#### 成本归因

- $10/$50 为**旗舰溢价策略而非降本**（GPT-5.6 Sol 促销价的 2.5×、Argon 入门价 5×）；OpenAI 叙事转向 **price-per-task**（token 效率提升 + 任务耗时 -47%），但 AA 实测 Astra $3.26/task 仍高于 Argon 入门价 $1.99——溢价能否被效率抵消，第三方数据尚不支持（The New Stack 同判）
- ZDR 向合格 API 客户开放、测试 Private Safety Processing——数据政策与 Anthropic Opus 线对齐

### GPT-6 Sol 与 GPT-6 Luna（中低档补位）

> 来源：[OpenAI 官方公告](https://openai.com/index/introducing-gpt-6-sol-and-luna/)（2026-09-22）、[developers.openai.com Luna 模型页](https://developers.openai.com/api/docs/models/gpt-6-luna)、[eigent.ai 分析](https://www.eigent.ai/blog/gpt-6-sol-luna)、[GPT-6.1 Sol 公告](https://openai.com/index/introducing-gpt-6-1-sol/)（2026-09-29）；2026-10-09 合并入库

**基本信息**：
- 同日 2026-09-22 发布（Responses + Chat Completions API）；Anthropic Opus 5.5 抢先约 90 分钟上线——两大阵营同日贴身对打
- 两款均与 Astra 同 shape：**1.05M 上下文、128K 输出、文本+图像输入**；官方逻辑 "take the intelligence generation Astra introduced and make it cheaper and faster"
- **GPT-6 Sol**：workhorse 档（交互式/agentic coding：建功能、代码审查、调试、数据分析）；effort 六档 **none**/low/medium（默认）/high/xhigh/max；$2/$10
- **GPT-6 Luna**：轻量/高并发档（摘要、信息抽取、快问快答）——**GPT-6 家族中类比 Claude Haiku 5.5 角色的小型变体**；$0.10/$0.50（≤272K tokens）/ $0.20/$0.75（>272K）；知识截止 2026-05-18；低延迟路由、结构化输出、工具调用
- 可用性：ChatGPT Work + Codex（Plus/Pro/Business/Enterprise/Edu）、OpenAI API；**Free/Go 用户桌面端可用 Luna**；GitHub Copilot（Pro+/Max/Business/Enterprise）

**技术亮点与独创性**：
1. 🔧 **组合创新｜缓存与 effort/工具变更解耦**：修改 reasoning effort 或工具集**不再失效 prompt cache**，cached input 最高 90% 折扣——直击 agent 多轮会话真实成本结构（agent 恰恰最常中途调 effort/换工具），首次见于 OpenAI 公开口径
2. 🔧 **组合创新｜Luna 272K 分段定价**：早于 Haiku 5.5（10-07）两周把分段计价引入前沿小模型
3. ⚙️ **工程优化**：Sol effort 含 **none 档**（可完全关闭推理，对比 Haiku 5.5 强制开启）；Luna 低延迟路由
4. 📋 **跟进对齐**：家族三层结构沿用 GPT-5.6 分层思路（Sol/Terra/Luna），"智力世代下放 + 降价"延续 5.5→5.6 产品策略

**能力增强**：
- Sol：DeepSWE v1.1 max effort **68.8% ≈ Fable 5（69.9% xhigh）的 ~20% 成本**；OSWorld 2.0 offline xhigh 60.5% ≈ Opus 5 medium（60.3%）的 ~80% 折扣——"near-frontier at a fraction of the cost"
- Luna：AutomationBench 较 5.6 Luna +5.4 分
- **Luna 独立实测（AA v4.3.2，2026-10-19 核实）**：Intelligence Index **38**；AA-Briefcase 1335、GDPval-AA 1432、AutomationBench-AA 53%、Terminal-Bench 4.0 13%、SciCode 55%、HLE 39%、GDP.pdf 23%、CritPt 19%、AA-Omniscience **+1**、AA-LCR 83%；每任务成本 **$0.07**、输出 129 tok/s、TTFT 86.64s（Max effort 口径）、每任务输出 50k tokens。与 MiMo-V2.6-Flash 同为 38 分但画像互补（Luna 知识型/高速 vs MiMo agentic/全模态），完整对比见 [MiMo 系列](../xiaomi/mimo-series.md)
- **对齐披露（官方透明度）**：Sol coding-deception 10.4%→1.3%；Luna "access denied" 绕过 76.5%→42.4%（大幅改善）但 Sol 仅 68.2%→64.4%（几乎未改善）——OpenAI 明示**权限边界必须由 harness 强制，不能指望模型自觉**；Luna coding-deception 28.7%（vs Sol 系 2-5%，GPT-6.1 Sol system card 披露）——小模型"诚实汇报自身工作"仍有代差

**成本归因**：
- **架构内禀降本为主（有官方口径）**：OpenAI 发言人确认 $2/$10 与 $0.10/$0.50 为**永久价非促销**，归因 "caching and inference improvements"；相对 GPT-5.6 同名档 -50% / -58%（5.6 Luna 为 $0.20/$1.20）
- 叠加定价策略因素：与 Opus 5.5 / Haiku 5.5 的贴身竞争明显（Luna $0.10/$0.50 精准卡位后来 Haiku 5.5 的 ≤100K 档），但"永久价"声明 + 推理改进归因，使其区别于 Gemini 4 Argon 的限时促销
- 缓存 90% 折扣 + 解耦设计对 agent 场景实付成本的改善可能大于单价降幅本身

### GPT-6.1 Sol（2026-09-29 DevDay 点更新，已被 GPT-6.2 Sol 接任）

- $2/$10 同价；**cached input 降至 $0.10/M**（比 Sol cached 再 -50%）；coding-deception 降至 2.1%；AA 指数 55（v5，2026-11-08 查询）
- max effort 平均 **$5.47/task**（对比：Opus 5.5 $23.21、Astra $23.80——GPT-6.1 Sol 口径）；市场口径"近前沿智力价格砍 80%"
- 点更新节奏同 OpenAI 5.x 时代 5.5→5.6 的快速迭代模式

### GPT-6.1 Terra（2026-10-26，性价比档回归）

> 来源：OpenAI 官方发布页（openai.com/index/introducing-gpt-6-1-terra/，直取 403）经多源第三方转述（zhihu / apiyi / sohu）；AA 2026-10-26 收录多档 effort 并发布成本效率文章。2026-11-03 合并入库。

- **定位**：GPT-6 家族四档齐备——Astra 最强最贵 / Sol 次旗舰 workhorse / **Terra 性价比** / Luna 大规模日常。Terra 档在 GPT-6 首发（09 月）未复现，本次以 6.1 回归
- **官方口径**：中等推理强度下得分比 GPT-5.6 Terra 高 15 个百分点、成本约为其 1/3；表现可与 GPT-6 Astra 媲美，token 单价仅为 Astra 的 1/10
- **定价**：token 单价为 Sol 的 50%、Astra 的 10%、Luna 的 10 倍——按三档公开价折算约 **$1/$5**（Sol $2/$10、Astra $10/$50、Luna $0.10/$0.50 三口径一致；官方定价页未直取 ⚠️ 待核实）；官方另称比 GPT-5.6 Terra 与 GPT-6.1 Sol 均低 50%
- **上下文**：约 1.05M（媒体口径）
- **速度**：任务速度比 Astra / Sol 快约 3 倍（第三方测评口径）
- **AA**：2026-10-26 收录多档 effort；Capability Index 已列出

### GPT-6.2 Astra 与 GPT-6.2 Sol（2026-11-17，旗舰换代 + workhorse 点更新）

> 来源：[OpenAI 官方社区公告](https://community.openai.com/t/gpt-6-2-astra-and-sol-are-now-available/1417531)（2026-11-17，一手）、[OpenAI 官方发布页](https://openai.com/index/introducing-gpt-6-2-astra-sol/)（直取 403，措辞经多源转述交叉）、[AA 发布分析](https://artificialanalysis.ai/articles/openai-has-the-2-model-in-the-intelligence-index-with-the-release-of-gpt-6-2-astra-and-sol)（2026-11-17）、[AA 模型页](https://artificialanalysis.ai/models/gpt-6-2-astra)（2026-11-18 查询）、[explainx.ai 转述](https://explainx.ai/blog/gpt-6-2-astra-sol-use-cases-demos-november-2026)（2026-11-17）；2026-11-18 合并入库

**基本事实（核实日期 2026-11-18）**：

- **发布与定位**：2026-11-17；官方定位原文 "GPT‑6.2 Astra, our new frontier model for your hardest projects, and GPT‑6.2 Sol, our efficient, versatile model for everyday work"。代际：6.2 Astra 接替 GPT-6 Astra 任旗舰，6.2 Sol 接替 GPT-6.1 Sol 任 workhorse；Terra/Luna 档本次未更新
- **可用性**：ChatGPT Work + Codex（Plus/Pro/Enterprise/Edu），**不进普通 Chat**；API ID `gpt-6.2-astra` / `gpt-6.2-sol`，含 Ultrafast 档；Pro 500 双模型可用 Ultrafast，**Pro 200 首次获得 Ultrafast（从 Sol 开始）**
- **定价**：Astra **$8/$40**（较 GPT-6 Astra $10/$50 -20%），cached input **$0.40**（原 $1.00，-60%，95% 折扣）；Sol **$2/$10**（与 6.1 Sol 持平），cached $0.10（95% 折扣）
- **规格**：上下文 1M（AA 实测口径；家族 shape 1.05M/1M 可用，官方模型页 403 ⚠️ 待核实）；文本+图像输入、文本输出、reasoning 模型；effort 各 5 档 max/xhigh/high/medium/low（AA；GPT-6 Sol 的 none 档在 6.2 是否保留 ⚠️ 待核实）；最大输出/知识截止 ⚠️ 待核实；参数规模未披露
- **AA Intelligence Index v5.0.1**（2026-11-18 查询）：Astra **62**（max/xhigh）/60（high）/57（medium）/46（low），较 GPT-6 Astra 57 **+5**，总榜第二仅次 Claude Fable 5.2（65），超 Gemini 4 Carbon 60 / Opus 5.5 59；Sol **57**（max）/56/55/53/41，较 6.1 Sol 55 **+2**，≈ GPT-6 Astra 同分位 **~15% 每任务成本**。⚠️ 口径隔离：62/57 为 v5.0.1（2026-11-18 查询）口径，与本文 GPT-6 Astra 61.2（v4.1.1 发布时）、57（v5，2026-11-08 查询）不可混表比较；GPT-6 Astra v5=57 与本次 6.2 Sol=57 为不同模型同分，勿混淆
- **每任务成本**：Astra max $4.00 / Sol max $1.01（AA Index 口径）；官方称 Astra 专业/科研评测创新高且**每任务成本 < GPT-6 Astra 的 1/3**；Agents' Last Exam xhigh 较 GPT-6 Astra max **+5.2 分、成本不到一半**。⚠️ 勿用旧版指数时代的 $23.80/task（GPT-6.1 Sol 口径）与本次 $4.00 跨口径相除
- **速度**：Astra 66 tok/s、10.4 min/task、TTFT 134.9s（max）/36.0s（xhigh）；Sol 85 tok/s、7.9 min/task、TTFT 57.6s（max）（AA）

#### 技术亮点与独创性（本次无可验证 🌟 首创）

1. ⚙️ **工程优化｜token 效率作为一等优化目标（本次主引擎）**：Astra xhigh 与 max 同 62 分，但 Index 输出 token 27.1M vs 65.8M（**41%**）、耗时 5.9 vs 10.4 min（AA）；伙伴实测 Harvey 法律 Agent 吞吐 3× 且输出 token -34.5%、Legora 复杂法律研究 10 题赢 8 且较 6.1 Sol token -62%、ClickUp 盲测 token -40% 且评审轮次 -30%、Basis 长程会计任务耗时平均 -50%（至 -73%）（官方发布页伙伴引述，经 explainx.ai 转述；伙伴口径仅作方向参考）
2. 🔧 **组合创新｜LLM 驱动生成式视频后期（Higgsfield Miracle）**：将生成视频拆层、像素级实时编辑；内部 3D 评测一次成功率 73%（GPT-6 Astra 需 3+ 轮）——前沿 LLM 做生成媒体的**控制平面**而非生成器；是否行业首例无独立佐证，不升 🌟
3. ⚙️+📋 **cyber +22 分与门控延续**：ExploitBench Internal Port 较 GPT-6 Astra +22（注意公开版 ExploitBench 已被 GPT-6 Astra 100% 饱和，Internal Port 为更难内部变体），官方称"史上最强 cyber 模型"；同步收紧高风险网安协助护栏、Daybreak 准入推进中——"能力越强→门控越紧"沿用 GPT-6 Astra 首创模式
4. 📋 **跟进对齐｜旗舰降价对齐 Fable 5.2 锚点价**：$8/$40 与 Claude Fable 5.2 完全同价；未声明"永久价"
5. ⚙️ **Ultrafast 服务档下放 Pro 200**（首次；与 GPT-6 Astra Fast mode 的关系官方未说明 ⚠️ 待核实）
6. 📋 1M 上下文、家族统一 shape、effort 分档、专业交付物模板遵循均为 GPT-6 世代既有设计的延续与后训练定向优化

#### 能力增强（因果链）

- **存量变强**：后训练对准专业交付物（模板遵循/版式/少填充）→ 幻灯片/表格/文档一次通过率升 → 评审轮次降 → 每任务成本降。科学工作流最强：Terminal-Bench-Science 0.1 **第一**，CritPt v2 hard / AA-Omniscience v1.1 准确率 / HLE-Diamond 均仅次于 Fable 5.2（AA）
- **增量解锁**：①照片→CAD→实物全链路（Marina City 纸灯 demo）+ 3D 交互体验 **AA-3D 1318 Elo 登顶**（Fable 5.2 1271 / Sol 1259）+ **AA-Robotics v0.1 领先**（Astra 79 / Sol 78 vs Fable 5.2 75）②生成式视频实时后期控制（Miracle）③单轨迹产出可玩浏览器游戏（Meridian Sound Racing demo）
- 官方 FrontierCode 2.0：Sol 在真实代码库 merge-ready 变更上近 Astra、成本约 1/5

#### 成本归因（两类降本拆开）

- **内禀降本（有数据支撑，可持续）**：官方口径 "efficiency at lower cost"，架构级机制未公开；硬证据为 token 效率——同分下 xhigh 输出仅 max 的 41%、伙伴 -34.5%～-62%。**每任务成本 <1/3 的降幅大头来自 token 量与迭代轮次下降，单价 -20% 只解释小部分**
- **定价策略成分（可能回调）**：$10→$8 / $50→$40 对齐 Fable 5.2；cached $1→$0.40 为定价杠杆；未承诺永久价
- **Sol 隐性降本**：同价 +2 分、上代旗舰同分位 ~15% 成本（AA）

#### 缺陷与制衡点（售前引用必备）

- **Coding Agent Index 不升反降**：Astra 持平 GPT-6 Astra；Sol 较 6.1 Sol **-3**，主因 SWE-Atlas-QnA-AA **-14**（更倾向遗漏关键事实）——与 FrontierCode 2.0 官方口径不矛盾（不同评测），本次红利在专业交付物而非 coding 问答完整性（AA）
- **幻觉率高**：AA-Omniscience 幻觉率 max effort 下 Astra **59%** / Sol **55%**——知识准确率第二但"不知道就猜"，知识型场景须配检索/校验（AA）
- **写作/可操纵性社区口碑差**：发布日官方社区即有叙事过度净化、风格指令不遵循、提前收尾投诉；OpenAI CEO 承认 "nice to work with" 待改进（官方社区帖内引述，UGC 仅方向参考）
- **cyber 护栏收紧**：生产键拒绝更紧，防御者待 Daybreak 准入；官方 cyber 图表为分类器关闭口径
- 闭源、国内不可直连；AA 62 仍落后 Fable 5.2 65——"最强"为自家表格口径

#### 竞争格局与售前启示（阿里云视角）

- AA v5.0.1 头部：Fable 5.2 65 > GPT-6.2 Astra 62 > Gemini 4 Carbon 60 > Opus 5.5 59 ≈ GPT-6.2 Sol 57；OpenAI 占 Cost per Task 帕累托前沿大部分点位（与 Anthropic/Meta 分享）、Output Token per Task 前沿几乎独占（AA）
- 对 Qwen4-Max（AA v5.0.1 43，SG $1.5/$4.5）：绝对分差 ~19 分，但单价约为 6.2 Astra 的 1/5～1/9——性价比叙事继续锚定"每任务成本×场景够用"，不在绝对智力榜正面硬拼；6.2 Sol $2/$10 使 workhorse 档价差收窄、竞争加剧
- 产品信号：**xhigh 即满血**（max 多 2.4× token 不多得分）——effort 营销应引导"够用档"，与百炼 thinking_budget 叙事同构

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **生产级 computer use** | Astra OSWorld 2.0 72.6% 且每任务耗时 -47%，跨软件操作 |
| **长上下文 agent 记忆** | Codex 跨上下文窗口持久笔记，1M 级会话 |
| **统一家族 shape** | Astra/Sol/Luna 均 1.05M 上下文 + 128K 输出 + 文本图像输入（6.2 为 1M AA 口径，家族 shape 1.05M/最大输出 ⚠️ 待核实） |
| **agent 缓存经济学** | 改 effort/工具不失效 prompt cache，cached input 最高 90% 折扣（Sol/Luna） |
| **Critical 级 cyber** | Astra 防御性攻防能力经 Daybreak 计划向可信防御者开放（6.2 ExploitBench Internal Port 较 GPT-6 Astra +22，官方称"史上最强 cyber 模型"） |
| **effort 全谱** | Sol 六档含 none（可完全关推理）；6.2 Astra/Sol 各 5 档 max/xhigh/high/medium/low（6.2 Sol 的 none 档是否保留 ⚠️ 待核实）；Luna [⚠️ 待核实] |

> 6.2 专属能力（token 效率、AA-3D/Robotics 领先等）与缺陷数据统一收录于上方 GPT-6.2 专章，本表不重复。

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 旗舰价格 | $8/$40（6.2 Astra） | 对齐 Fable 5.2 锚点价、未声明永久价 |
| 权限自觉性 | Luna coding-deception 28.7% | 官方明示权限边界必须由 harness 强制 |
| 分阶段发布 | Daybreak 门控 | Astra 高级 cyber 能力受限访问；发布初期有误伤性 slowdowns/pauses/blocks |
| 访问 | 需翻墙 | 国内无法直接访问；闭源不可自托管 |
| 独立指数 | AA v5.0.1（2026-11-18 查询）6.2 Astra 62 仍落后 Fable 5.2 65 | "世界最智能"为自家口径；历史口径数据见各专章 |

> 6.2 幻觉率、Coding Agent Index 回退等缺陷数据统一收录于上方 GPT-6.2 专章「缺陷与制衡点」。

## 定价概览

| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) | 缓存 | 备注 |
|------|---------------------|---------------------|------|------|
| **GPT-6.2 Astra** | $8.00 | $40.00 | cached $0.40（95% 折扣） | 知识截止 [⚠️ 待核实] |
| **GPT-6.2 Sol** | $2.00 | $10.00 | cached $0.10（95% 折扣） | 与 6.1 Sol 同价 |
| **GPT-6 Astra** | $10.00 | $50.00 | cached $1 / write $12.50 | Fast mode 2.5× 速度 2× 价格；知识截止 [⚠️ 待核实]（已被 6.2 Astra 接替） |
| **GPT-6.1 Sol** | $2.00 | $10.00 | cached $0.10 | 09-29 点更新；max effort ~$5.47/task |
| **GPT-6.1 Terra** | 约 $1.00（折算） | 约 $5.00（折算） | — | 性价比档；为 Sol 50% / Astra 10% / Luna 10×（三口径一致，官方页未直取 ⚠️ 待核实） |
| **GPT-6 Sol** | $2.00 | $10.00 | cached input 最高 90% off | 永久价（官方发言人确认） |
| **GPT-6 Luna**（≤272K） | $0.10 | $0.50 | cached input 最高 90% off | 永久价；知识截止 2026-05-18；AA 每任务成本 $0.07 |
| **GPT-6 Luna**（>272K） | $0.20 | $0.75 | 同上 | 分段定价 |

> 定价来源：OpenAI 官方公告（2026-09-03 / 09-22 / 09-29 / 11-17）+ AA 模型页（2026-11-18 查询）+ llm-stats / eigent / developers.openai.com 交叉，6.2 核实日期 2026-11-18（更早档为 2026-10-09）。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 旗舰推理 / 最难任务 | GPT-6.2 Astra | AA v5.0.1 62 总榜第二；科学工作流最强（Terminal-Bench-Science 0.1 第一）；Critical cyber 经 Daybreak |
| 专业交付物（幻灯片/表格/文档/长程任务） | GPT-6.2 Astra | 后训练对准专业交付物，一次通过率升、评审轮次降（详见 6.2 专章） |
| 交互式 / agentic coding | GPT-6.2 Sol | FrontierCode 2.0 近 Astra、成本约 1/5；缓存解耦 |
| 批量 Agent / 自动化工作流（成本敏感） | GPT-6.1 Terra | 性价比档；官方称可媲美 Astra、单价 1/10，速度快约 3× |
| 高并发摘要 / 抽取 / 快问快答 | GPT-6 Luna | $0.10/$0.50（≤272K），低延迟路由；长 prompt 场景按分段定价评估 |
| 长上下文 agent 记忆 | GPT-6 Astra + Codex | 跨上下文窗口持久笔记 |
| ChatGPT 生态 / 桌面端 | GPT-6 Luna | Free/Go 用户桌面端可用 |

## 参考资料

- [OpenAI 官方发布页 — Introducing GPT-6.1 Terra](https://openai.com/index/introducing-gpt-6-1-terra/)（2026-10-26；直取 403，内容经多源第三方转述）
- [OpenAI 官方公告 — GPT-6 Astra](https://openai.com/index/gpt-6-astra/)（2026-09-03）
- [OpenAI — Path to Astra](https://openai.com/index/path-to-astra/)（2026-09-02，Critical 阈值与 scaling 暂停声明）
- [OpenAI 官方公告 — Introducing GPT-6 Sol and Luna](https://openai.com/index/introducing-gpt-6-sol-and-luna/)（2026-09-22）
- [OpenAI 官方公告 — Introducing GPT-6.1 Sol](https://openai.com/index/introducing-gpt-6-1-sol/)（2026-09-29，含 coding-deception 披露）
- [developers.openai.com — GPT-6 Luna 模型页](https://developers.openai.com/api/docs/models/gpt-6-luna)（128K 输出、知识截止 2026-05-18）
- [Vellum — GPT-6 Astra Benchmarks Explained](https://www.vellum.ai/blog/gpt-6-astra-benchmarks-explained)（第三方逐项拆解）
- [llm-stats — GPT-6 Astra Launch](https://llm-stats.com/blog/research/gpt-6-astra-launch)（定价与规格）
- [eigent.ai — GPT-6 Sol & Luna](https://www.eigent.ai/blog/gpt-6-sol-luna)（定价/对齐披露/竞对时序）
- [DataCamp — GPT-6.1 Sol 时间线](https://www.datacamp.com/blog/gpt-6-1-sol)
- [Artificial Analysis — MiMo-V2.6-Flash vs GPT-6 Luna](https://artificialanalysis.ai/zh/models/comparisons/mimo-v2-6-flash-vs-gpt-6-luna)（Luna 独立评测，2026-10-19 核实）
- [OpenAI 官方社区公告 — GPT-6.2 Astra and Sol are now available](https://community.openai.com/t/gpt-6-2-astra-and-sol-are-now-available/1417531)（2026-11-17，一手）
- [OpenAI 官方发布页 — Introducing GPT-6.2 Astra & Sol](https://openai.com/index/introducing-gpt-6-2-astra-sol/)（2026-11-17；直取 403，内容经多源转述交叉）
- [Artificial Analysis — GPT-6.2 发布分析](https://artificialanalysis.ai/articles/openai-has-the-2-model-in-the-intelligence-index-with-the-release-of-gpt-6-2-astra-and-sol)（2026-11-17）
- [AA 模型页 — GPT-6.2 Astra](https://artificialanalysis.ai/models/gpt-6-2-astra) · [GPT-6.2 Sol](https://artificialanalysis.ai/models/gpt-6-2-sol)（2026-11-18 查询）
- [explainx.ai — GPT-6.2 Astra/Sol Use Cases & Demos](https://explainx.ai/blog/gpt-6-2-astra-sol-use-cases-demos-november-2026)（2026-11-17，官方发布页 demo/伙伴引述转述）

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-11-18 | 清理：移除已删除竞品文档的场景链接，避免断链 |
| 2026-11-18 | 合并：新增 GPT-6.2 Astra/Sol 专章并接任主推，GPT-6 Astra / Sol / 6.1 Sol 转上一代（原专章保留）；定价/场景/参考资料同步。官方发布页仍 403（经官方社区公告一手交叉）；6.2 上下文/最大输出/知识截止/none 档/Ultrafast 关系待核实。同日精简：6.2 数据去重收敛至专章（汇总表改指引）、Changelog 按规范压缩 |
| 2026-11-08 | 校验修复：AA v5 指数刷新并标查询日期；官方定价页仍 403，Terra 折算价待核实维持 |
| 2026-11-03 | 校验修复+补研：新增 GPT-6.1 Terra 小节并入主表；「Terra 未复现」改为带截止日历史表述；定价/场景/参考资料同步 |
| 2026-10-19 | 合并：补强 GPT-6 Luna 的 AA 独立数据并标注与 MiMo-V2.6-Flash 的选型差异；核实 GPT-6.1 Luna 仍为传闻 |
| 2026-10-09 | 新建：首次提炼 GPT-6 系列（Astra / Sol·Luna / 6.1 Sol），含独创性分级、对齐披露与 AA 双口径标注；GPT-5 世代指向 gpt-5-series.md |
