# Meta Muse 系列

> 最后更新: 2026-11-11
> 所属厂商: Meta
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: Meta 的闭源 Agent 向模型系列，官方定位「个人与专业 Agent 使用」；多模态输入（文本/图像/音频/视频）+ 文本输出、1M 上下文，配套 Meta 官方编码 Agent **Muse Code**。Ember 为当前 AA 榜「≥36 分档最便宜」模型（$0.14/task）
**当前主推**: Muse Wonder Full（旗舰，Muse Code 独占）/ Muse Wonder（API 主力）/ Muse Ember（性价比轻量）
**适用**: Agent 知识工作、Agentic 编码、SaaS 自动化流程、大批量低成本 Agent 调用
**不适用**: 开源自部署（闭权重、参数未公开）、知识密集型问答（AA-Omniscience 偏弱，Ember 拒答率 64%）
<!-- SUMMARY_END -->

> ⚠️ **信源与版本口径**：本文基于 Artificial Analysis 独立评测（2026-10-12 / 11-09 两篇文章 + 模型页，2026-11-11 查询）；Meta 官方博客（research.meta.ai）直取超时，官方一手细节待补充。AA Intelligence Index 已重校准：**v4.3（10-12 发布时）→ v5.0.1（当前）**，Wonder 52→44、Wonder Full 56→50，跨版本分数不可直接比较，本文均已标注版本。

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Muse Wonder Full** 🚩 | 旗舰（Muse Code 独占） | 1M | AA v5.0.1 = 50（#22/119）；v4.3 发布时 56；不按 token 计价、无公开 API；文本/图像/音频/视频输入 | 2026.10.12 |
| **Muse Wonder** | API 主力 | 1M | AA v5.0.1 = 44（v4.3 发布时 52）；$4/$20、缓存 $0.20；$6.95/task（v5.0.1）；四模态输入 | 2026.10.12 |
| **Muse Ember** | 性价比轻量 | 1M | AA v5.0.1 = 36（xhigh 34）；$0.10/$0.50、缓存 $0.004（96% 折扣）；$0.14/task 为 ≥36 分档最便宜；455 tok/s、3.1 min/task；文本+图像输入 | 2026.11.09 |

> 📌 **历史模型**：Muse Spark 1.3（max，AA v4.3 = 48，$1.25/$4.25、缓存 $0.15，$1.60/task）——仍可调用，但已被 Wonder 系列取代（发布间隔仅约 6 周），不建议新项目选用。
> 📌 **观察项**：Muse Spark Open——AA Endpoint Accuracy Index v1.1（2026-11-09）新增覆盖该型号，疑似 Spark 开放权重变体，规格/许可证未直取 [⚠️ 待验证]。

### Muse Wonder Full
- 模型：Muse Wonder Full（max effort）
- 公司：Meta
- 时间：2026.10.12（AA FAQ 确认）
- 尺寸：闭源专有，参数未公开（AA 模型页）
- 上下文：1M tokens；输入文本/图像/音频/视频，输出文本
- 场景：Agent 知识工作、科学推理、Agentic 编码（Muse Code 内）
- 特点：
  - AA v5.0.1 = 50（#22/119，2026-11-11 查询）；v4.3 发布时 = 56，十项评测全面超越 Spark 1.3（+8 分）
  - v4.3 口径六项评测进前三：CritPt 33%（#1）、GDP.pdf 33%（#1）、GDPval-AA v2.1 1857 Elo（#2）、AA-Briefcase 1729 Elo（#3）、AutomationBench-AA 71%（#3）、SciCode 63%（#3）；Terminal-Bench 4.0 33%→57%（+24 分，最大涨幅）
  - 幻觉率 33%→23%，为 AA ≥45 分档第二低（仅次于 Gemini 4 Argon high 15%）
  - Muse Code 内 Coding Agents Index = 68（max），与 Claude Code + Sonnet 5.5（max，68）持平
- 定价：**不按 token 计价**，仅 Muse Code 用户可用，无公开 API（AA 2026-11-11 查询仍显示 No publicly available API），无 Cost per Task 数据

### Muse Wonder
- 模型：Muse Wonder（max effort）
- 公司：Meta
- 时间：2026.10.12
- 尺寸：闭源专有，参数未公开
- 上下文：1M tokens；输入文本/图像/音频/视频，输出文本
- 场景：Meta 第一方 API 的 Agent 主力档
- 特点：
  - AA v5.0.1 = 44、$6.95/task（2026-11-09 文章口径）；v4.3 发布时 = 52、$4.52/task（10-12 文章口径）
  - v4.3 口径：TB 4.0 33%→52%、AutomationBench-AA 58%→68%；AA-Omniscience 25、幻觉率 27%（≥45 分档第三低，v4.3 时期口径）
  - 输出 token 效率改善：~54k output/task（较 Spark 1.3 的 60k 降 ~10%）；但输入用量高（7.69M/task，较 Spark +28%），输入成本占 task 成本 76%
  - Muse Code 内 Coding Agents Index = 63（max）
- 定价：$4 输入 / $20 输出 / $0.20 缓存命中（每百万 tokens）；与 Claude Opus 5.5 同价，为 Sonnet 5.5 / Gemini 4 Argon / GPT-6.1 Sol（$2/$10）的 2 倍

### Muse Ember
- 模型：Muse Ember（max / xhigh effort）
- 公司：Meta
- 时间：2026.11.09（AA 文章发布日）
- 尺寸：闭源专有，参数未公开
- 上下文：1M tokens；输入文本+图像，输出文本（注意：无音频/视频输入，与 Wonder 系不同）
- 场景：高效轻量档，大批量 Agent 调用、自动化流程
- 特点：
  - AA v5.0.1 = 36（max）/ 34（xhigh，$0.12/task）；**$0.14/task 为 ≥36 分档最便宜**：同分的 Claude Haiku 5.5（max）$0.41（约 3 倍）；较 DeepSeek V4.1 Flash 1017（33，$0.60）、GLM-5.3-Flash（28，$0.58）便宜约 4 倍
  - 与 Haiku 5.5 / GPT-6 Luna 输入输出同价，但缓存命中便宜 60%，输出 token 用量约为 Haiku 的 1/3
  - AutomationBench-AA 68.1%（与 Wonder max、GPT-6 Astra 持平）；TB 4.0 40.9%（胜 Haiku 32.8%）、FrontierCode 2.0 27.2%（负 Haiku 34.9%）、GDP.pdf 22.8%（胜 Haiku 20.8%）、AA-Briefcase 1521 Elo（负 Haiku 1574）
  - Muse Code 内 Coding Agents Index = 46（max），领先 Claude Code + Haiku 5.5（37）与 Codex + GPT-6 Luna（31）
  - 性能：455 tok/s、TTFA 4.69s、3.1 min/task（同档中位 7.6 min）
  - 知识弱但极少幻觉：AA-Omniscience 准确率 21.1%（同档最低），主因拒答 64% 的问题；幻觉率 17.4%（Haiku 的一半）
- 定价：$0.10 输入 / $0.50 输出 / $0.004 缓存命中（96% 折扣，每百万 tokens）

### Muse Spark 1.3（历史）
- AA v4.3 = 48（max）；TB 4.0 33%、AutomationBench-AA 58%、GDPval-AA v2.1 1681 Elo、AA-Briefcase 1581 Elo
- $1.25 输入 / $4.25 输出 / $0.15 缓存命中；$1.60/task；输出 ~60k/task、输入 6.03M/task
- Muse Code 内 Coding Agents Index = 54；1M 上下文
- 已被 Wonder / Wonder Full 取代（2026.10.12），不建议新项目选用

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 多模态输入 | Wonder / Wonder Full：文本+图像+音频+视频；Ember：文本+图像；输出均为文本 |
| 长上下文 | 全系 1M tokens（自 Spark 1.3 起不变） |
| Agent 知识工作 | Wonder Full 在 GDPval-AA / AA-Briefcase / CritPt / GDP.pdf 进前三（v4.3 口径） |
| Agentic 编码 | Muse Code 内 Coding Agents Index：Wonder Full 68 / Wonder 63 / Ember 46 |
| 低幻觉 | Wonder Full 23%、Ember 17.4%（AA-Omniscience 口径），适合「宁可不答不可答错」场景 |
| 推理努力档 | Ember 提供 max / xhigh；Wonder 系评测以 max 展示 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 闭权重 | Proprietary | 全系参数未公开，不可自部署（Spark Open 变体待验证） |
| Wonder Full 获取受限 | 仅 Muse Code | 无公开 API、不按 token 计价，售前不可承诺 API 获取 |
| 知识广度弱 | AA-Omniscience：Wonder Full 30 / Wonder 25 / Ember 21.1% | 低于 Opus 5.5（46）、GPT-6 Astra（43）等；Ember 拒答率 64% |
| Wonder 输入成本高 | 7.69M input/task（v4.3）；$6.95/task（v5.0.1） | 输入占 task 成本 76%，长任务场景需评估 |
| 输出模态 | 仅文本 | 无图像/音频生成能力 |

## 定价概览

| 模型 | 输入价格 | 输出价格 | 缓存价格 | 备注 |
|------|---------|---------|---------|------|
| Muse Wonder | $4/1M tokens | $20/1M tokens | $0.20/1M tokens（命中） | Meta 第一方 API + Muse Code |
| Muse Ember | $0.10/1M tokens | $0.50/1M tokens | $0.004/1M tokens（命中，96% 折扣） | 与 Haiku 5.5 / GPT-6 Luna 同输入输出价 |
| Muse Wonder Full | 不按 token 计价 | — | — | 仅 Muse Code 订阅内可用 |
| Muse Spark 1.3（历史） | $1.25/1M tokens | $4.25/1M tokens | $0.15/1M tokens（命中） | 已被 Wonder 取代 |

> 定价来源：AA 2026-10-12 文章（Wonder / Spark）+ 2026-11-09 文章与模型页（Ember），核实日期：2026-11-11。Meta 官方定价页未直取，以官方为准。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| Agent 知识工作 / 科学推理 | Wonder Full（Muse Code）/ Wonder | GDPval-AA、CritPt、GDP.pdf 前三（v4.3 口径） |
| Agentic 编码 | Wonder Full / Wonder | Muse Code 内 Index 68 / 63，对标 Claude Code + Sonnet 5.5 |
| SaaS 自动化流程 | Ember | AutomationBench-AA 68.1%，$0.14/task 成本优势显著 |
| 大批量低成本 Agent 调用 | Ember | ≥36 分档最便宜，455 tok/s 快速响应 |
| 低幻觉要求的问答辅助 | Ember / Wonder Full | 拒答换低幻觉（17.4% / 23%），适合合规敏感场景 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 开源自部署 / 私有化 | 闭权重（Spark Open 待验证） |
| 知识密集型百科问答 | AA-Omniscience 偏弱，Ember 拒答率 64% |
| 需要公开 API 的旗舰档集成 | Wonder Full 仅 Muse Code 独占 |

## 生态：Muse Code（Meta 官方编码 Agent）

Muse Code 是 Meta 官方编码 Agent 产品，Wonder Full 仅在其内可用；AA Coding Agents Index 在该 harness 内实测：

| 模型（Muse Code 内，max） | Coding Agents Index |
|------|------|
| Muse Wonder Full | 68 |
| Muse Wonder | 63 |
| Muse Spark 1.3（历史） | 54 |
| Muse Ember | 46 |

> 对照组（AA 口径）：Claude Code + Sonnet 5.5（max）68、Opus 5.5（max）66；Claude Code + Haiku 5.5（max）37；Codex + GPT-6 Luna（max）31。Muse Code 产品细节（定价/形态）未直取 [⚠️ 待补充]。

## 参考资料

- [AA：Muse Wonder and Muse Wonder Full（2026-10-12）](https://artificialanalysis.ai/articles/muse-wonder)
- [AA：Muse Ember is the cheapest model scoring 36（2026-11-09）](https://artificialanalysis.ai/articles/meta-s-muse-ember-is-the-cheapest-model-scoring-36-on-the-intelligence-index)
- [AA 模型页：Muse Wonder Full](https://artificialanalysis.ai/models/muse-wonder-full) · [Muse Ember](https://artificialanalysis.ai/models/muse-ember)（2026-11-11 查询）
- Meta 官方博客 research.meta.ai/blog/muse-ember（直取超时，未纳入本文事实来源）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-11-11 | 创建：AA 两篇文章 + 两模型页提炼（Wonder Full / Wonder / Ember / Spark 1.3 + Muse Code 生态）；标注 v4.3→v5.0.1 重校准口径；官方博客未直取、无公开论文素材故省略论文章节 |