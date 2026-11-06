# 混元（腾讯 Hunyuan）模型系列

> 最后更新: 2026-11-06
> 所属厂商: 腾讯（Tencent Hunyuan）
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 腾讯混元旗舰 MoE 系列，以"生产力场景 Co-design + 加量不加价的性价比"为主线；preview 阶段 Apache 2.0 开源，正式版权重尚未放出
**当前主推**: Hy4（2026-11-04 正式版，首次视觉理解 + Computer Use，1M 上下文）；上一代正式版 Hy3（2026-07-06，295B/21B，256K）；Hy4 preview 已降为历史版本
**适用**: 带图分析 / 复杂图表与文档、长文档与跨文件长程 Agent（Hy4）、办公协作与金融研究（WorkBuddy 83.18、金融众测开源第一）、专业软件操作（Blender / CAD）
**不适用**: 私有化部署与自部署（正式版权重未放出，仅 API）、高并发轻量档（Hy4 Flash 未发布）、跨模型横比 benchmark（口径不可比）、构造型前沿数学（Hy-FrontierMath T5 仅 13.0）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Hy4** 🚩 | 现役旗舰（正式版） | 1M | 首次视觉理解 + Computer Use、Co-design 全场景、等价同价 | 2026-11-04 |
| **Hy3** | 上一代正式版（轻量性价比档） | 256K | 295B/21B、异构专家 + 快慢思考融合、Apache 2.0 | 2026-07-06 |
| Hy4 preview | 历史版本（已被正式版取代） | 1M | 770B/49B、Gated DSA + IndexCache + iHC、Apache 2.0 已开源 | 2026-08-28 |
| Hy3-preview | 历史版本（已被 Hy3 取代） | 256K | 异构专家 + P-Penalty Loss | 2026-04-22 |

> 📌 **代际状态（2026-11-06 核实）**：Hy4 正式版已于 2026-11-04 发布并在腾讯云 TokenHub / OpenRouter 上线，**但模型权重与 system card 仍在"计划开源"状态**，当前只能 API 调用。Hy4 Flash 官方称计划近期发布，届时才补上轻量档。

## Hy4（正式版）

### 基本信息

| 项 | 值 |
|---|---|
| 发布时间 | 2026-11-04（距 Hy4 preview 2026-08-28 约 68 天） |
| 参数 | 官方发布稿未单列；腾讯系渠道沿用 preview 的 770B 总参 / 49B 激活 |
| 上下文 | 1M（TokenHub 侧最大输入 960K / 最大输出 64K） |
| 新增模态 | **视觉理解（首次）**：细粒度图像处理、复杂图表分析、多模态数学推理 |
| 新增能力 | **Computer Use（首次）**：命令行 + 图形界面双通道 |
| 权重状态 | ⚠️ **尚未放出**：官方称"计划开源模型权重"、system card"近期发布"；Agent Arena 标注 Currently proprietary |
| 获取渠道 | 腾讯云 TokenHub（OpenAI 兼容）、OpenRouter / Hermes / OpenCode、WorkBuddy / CodeBuddy、元宝、ima、企业微信"大圆" |
| 后续规划 | Hy4 Flash（主打性价比，近期发布）；QQ、王者荣耀、和平精英、微信读书、腾讯新闻陆续接入 |

> ⚠️ **一个高频误读**：11-04 发生的是"发新模型 + 上 API"，**不是放权重**。preview 阶段 Apache 2.0 已开源，正式版权重仍在"计划"状态；传播口径里的"开源模型第一"属能力定位与市场分类，不是法律意义上的授权状态。

### 两项"第一次"

| 能力 | 官方口径 |
|---|---|
| 视觉理解 | 视觉 + 推理 + 工具调用融合；官方演示：28 亿像素航拍图中定位约 2 米大小屋顶构件、重组 900 片拼图还原莫奈画作 |
| Computer Use | 命令行与 GUI 结合操作；针对 Blender / CAD 等专业软件专项训练；与腾讯云 Agent Runtime 共建沙箱，部署数百款应用供反复执行验证 |

### 生产力场景（官方数据）

| 场景 | 表现 |
|---|---|
| 办公协作（WorkBuddy） | 平均效果 **83.18** 分、任务通过率 **96.15%**；12 个场景中 9 个中国内地第一 |
| 金融分析 | 213 位专家（153 位外部）、579 个真实任务众测：Hy4 **3.04** > DeepSeek-V4.1-Flash-1017 2.97 > Kimi K3.1 Pro 2.68 = GLM-5.3 2.68；外部 iRaB 综合 61.63，较 preview +12.03 |
| 前端 / 游戏 | 相对 preview：GameDev **+19.1%**、GameLogic **+9.8%**；深度适配 UE / Unity / Godot，开始覆盖多人联机 |
| 科研 | TenureTrail（7 学科、123 项可执行任务）居开源首位；699 万细胞小鼠胚胎 3D 重建 1.5 小时无人干预；与北大数学团队找到 Méndez–Pinto–Villarreal 猜想反例并完成 Lean 形式化验证 |

### Benchmark（正式版 vs preview）

官方 Bench 附录为图片且未提供 HTML 表，下列为逐项转录值。**不可跨模型横比**——harness、推理档位、裁判模型各不相同，且相当比例任务集为内部自建。

| 分组 | Benchmark | preview | Hy4 | 变化 |
|---|---|---|---|---|
| Agentic Coding | DeepSWE v1.1 | 64.3 | **74.9** | +10.6 |
| Agentic Coding | SWE-Marathon v1.1 * | 31.9 | **43.8** | +11.9 |
| Agentic Coding | Terminal-Bench 4.0 | 26.3 | **44.4** | +18.1 |
| Agentic Coding | Hy-CompanyBench 2.0（internal） | 62.4 | **78.8** | +16.4 |
| Working Agent | APEX-Agents v1.1（pass@1） | 53.9 | **75.2** | +21.3 |
| Working Agent | Agents' First Exam-IF（internal） | 50.5 | **79.9** | +29.4 |
| STEM | Hy-FrontierMath T5（internal）* | 7.8 | **13.0** | +5.2 |
| AI4Research | Foundation Model Bench（internal）* | 13.6 | **28.1** | +14.5 |

首次开测（preview 列为空，属新增评测面而非能力从 0 起跳）：OSWorld 2.1 **78.9**、MMMU-Pro **78.6**、BuddyVQA Atlas 81.0（带工具）/ 55.6（不带）、FrontierCode 2.0 31.0、Agents' Last Exam 41.0、ZeroBench-main pass@5 55.4。

- 竞品列版本：GLM-5.3、DeepSeek-V4.1-Flash-1017、Kimi K3.1 Pro、GPT-6.1 Sol、Claude Opus 5.5。
- `*` = 发布时首次评测 / 腾讯自测；官方另注明 **preview 列分数可能因 harness、裁判模型与反作弊机制更新而与 8-28 公布值不一致**，故"提升 xx%"须先确认两端同口径。
- 旧基准（SWE-bench Multilingual 82.9、Terminal-Bench 2.1 85.4、MCP-Atlas 83.7 等）仍为 **preview 口径**；正式版换用 TB 4.0 等新基准，两者不可混用或拼接。⚠️ 尤其不要拿 preview 的 Terminal-Bench 2.1 85.4 对比正式版的 TB 4.0 44.4——基准难度与 harness 均已更换，只会得出反向结论。

### 可靠性与安全边界

- **幻觉**：官方自建测试中幻觉率 12.95% → **7.2%**（英文稿口径），猜测导致的错误率 23.1% → **5.6%**；中文渠道另有 15.76% → 5.45% 口径，官方未统一，引用时须注明来源渠道。
- **网络安全**：训练只纳入 PoC 生成、漏洞修复等防守性数据，剔除利用 / 逆向 / 渗透等攻击性内容；玄武与科恩实验室审计未发现突出进攻性风险。
- **生物安全**：Hy-BioExperimentBench **30.4/100**，开放式实验设计能力与前沿模型差距明显。
- **官方自认差距**：在前沿数学、长程开发、模型迭代、视觉问答等高难度内测集上，与顶尖闭源模型仍有较大差距。

### RSI（递归自我改进）

- 结合 **Hyra 2.0** 研发框架优化同架构小模型的预训练基础设施，自动训练出的 Jev 在多项评测中优于官方版本。
- 同步开源单细胞表征模型 **HyCell** 与物理场模型 **HyPDE**（这两个是开源资产，与 Hy4 权重无关）。
- 第三方 Agent Arena（11-04）：总榜 #14、8.5K+ 会话、净提升 +4.7%、进入 Pareto 前沿，任务成本 $0.55/task，并注明"权重放出后"才与 Kimi K3.1 Pro 并列为开源第一。

## Hy4 preview（历史版本，2026-08-28）

> 以下保留 preview 阶段的架构与评测口径，供追溯与自部署选型参考；正式版沿用架构但官方未重申全部规格。

### 基本信息

| 项 | 值 |
|---|---|
| 发布时间 | 2026-08-28（距 Hy3 正式版 7-06 仅 53 天） |
| 总参数 / 激活 | 770B / 49B |
| 层数 / 隐藏维度 | 78 层（第 1 层标准 FFN，余 77 层 MoE）/ 6144 |
| MoE 结构 | 256 路由专家 + 1 共享专家，每 token 激活 top-8 + 共享 |
| 注意力 | Gated DeepSeek Sparse Attention（Gated DSA）+ IndexCache 跨层复用稀疏索引 |
| 残差 | iHC（identity Hyper-Connections），残差流 4 路 |
| MTP | 原生 1 层，10B 总参 / 0.7B 激活，支持投机解码 |
| 上下文 / 词表 | 1M tokens / 120832 |
| 多模态 | **纯文本**（preview 阶段；正式版已补视觉理解） |
| 开源 | Apache 2.0，BF16 + FP8 权重（HF / ModelScope / GitCode / CNB） |
| 推理强度 | 默认 `high`（深度思维链）；可传 `reasoning_effort: no_think` 直接回答 |
| 获取渠道 | 开源权重 / 腾讯云 TokenHub / OpenRouter / WorkBuddy、CodeBuddy、元宝、ima |

### 技术亮点与独创性

| 分级 | 亮点 | 判断依据 |
|------|------|----------|
| 🌟 **首创**（官方宣称，待第三方复现） | **模型参与自身研发流程的早期 RSI 闭环**：首次参与自身训练方法、数据策略、评测框架与底层算子的自动化优化（提出方案 → 跑实验 → 按结果迭代，代码/日志/反馈进入下一轮）；并**自主分析自身推理系统瓶颈**，完成算子融合与通信优化多轮迭代，端到端吞吐相对基线 **+31.8%** | OpenAI GPT-6 Astra 披露的是"前代模型监督新一代训练"（模型作为监督信号）；Hy4 是**模型作为研发执行者改写自身训练/推理栈并给出量化收益**。公开材料中尚无其他厂商披露同等颗粒度的闭环证据。⚠️ 厂商自述，未见独立审计 |
| 🔧 组合创新 | Gated DSA + IndexCache + iHC 三件套 | 官方明示"受到 DeepSeek 和 GLM 的启发"：稀疏注意力加门控、IndexCache 做跨层稀疏索引复用、iHC 扩成 4 路残差通路。属已有技术的新组合 |
| ⚙️ 工程优化 | 770B/49B + 1M + MTP；首发即有 vLLM/SGLang 官方镜像、FP8 变体、微调指南、AngelSlim 压缩工具链 | 工程可用性对齐开源头部 |
| ⚙️ 工程优化 | **轻量版（2026-09-01）**：权重从约 1.5TB 压到 **214GB**；与 prima.cpp 验证异构联合推理（单卡 4090 笔记本 + 四卡 A4000 服务器，合计 80GB 显存 + 64GB 内存，跨局域网调度 MoE 层） | 大幅降低自部署门槛 |
| 📋 跟进对齐 | 生产力 Co-design + 163 位专家 × 203 真实工程任务盲测 | 沿用 Hy3 方法论；**内部闭集，任务集与评分细则未公开，不可外部复现** |

### 能力表现与制衡点

| Benchmark | Hy4 preview | Hy3 | 同代参照 |
|---|---|---|---|
| SWE-bench Multilingual | **82.9** | 75.8 | GLM-5.3 81.3、Kimi K3 80.8、DeepSeek-V4-Pro 77.3 |
| SWE-bench Pro (Public) | **65.7** | 57.9 | DeepSeek-V4-Pro 55.4 |
| DeepSWE v1.1 | **64.3** | 28.0（2.3×） | GLM-5.3 68.96、Kimi K3 68.51（**落后**） |
| Terminal-Bench 2.1 | **85.4** | 71.7 | DeepSeek-V4-Pro 72.1 |
| MCP-Atlas | **83.7** | 79.1 | Kimi K3 82.3、DeepSeek-V4-Pro 74.2 |
| Toolathlon-Verified | **74.1** | 56.8 | — |
| SWE-Marathon | 31.9 | — | GLM-5.3 42.5、Kimi K3 42.0（**明显落后**） |
| GPQA Diamond | 92.3 | 90.4 | Kimi K3 91.92 |
| HLE（工具 / 无工具） | 55.4 / 43.4 | 53.2 / 37.0 | GLM-5.3 62.5、Kimi K3 59.8（**落后**） |
| AutomationBench | 32.1（第 20/30） | — | **办公自动化短板** |
| CyberGym | 78.4 | — | 安全类中游 |

- **存量变强**：DeepSWE 翻倍级提升（28.0 → 64.3）、Terminal-Bench 71.7 → 85.4，长程开发的调试与验证能力是主要受益面。
- **增量解锁**：1M 上下文下的跨文件长程开发；一句话生成可玩游戏原型并接引擎多轮迭代；科研场景（AI 研发、分子动力学、凝聚态物理、基础数学）。
- **专家盲测**：163 位内部专家 × 203 任务，Hy4 preview 2.99/4 vs GLM-5.3 2.92（胜 46.8% / 平 12.8% / 负 40.4%）、Kimi K3 2.94（胜 51.2% / 平 7.9% / 负 40.9%）——领先幅度接近，非压倒性。
- ⚠️ **制衡点**：单点仓库修复领先，但**长程马拉松（31.9 vs 42.5）与知识型推理（HLE 55.4 vs 62.5）反而落后**；办公自动化（32.1）偏弱；纯文本。全部数字为厂商口径，**截至 2026-10-19 未见 Artificial Analysis 稳定收录**（OpenRouter 对比页标 Not available）。

### 成本归因

- **架构内禀降本**：49B 激活承担 770B 容量；Gated DSA + IndexCache 降低长上下文注意力成本；MTP 投机解码提升吞吐——三者叠加让 1M 上下文在工程上可支付。
- **定价策略降本**：海外 $0.834/$2.501（缓存 $0.042），约为 GLM-5.2（$1.4/$4.4）的 60%/57%，是 Kimi K3（¥20/¥100）的零头。典型"低于已验证在位者、让早期用户承担未验证风险"的定价。
- ⚠️ **未公开项**：训练成本与算力规模均未披露，无法判断是效率红利还是份额补贴。官方自认"复杂任务长思考、过度自我验证"，agent 场景实际 token 账单可能抵消单价优势。

### 已知限制（preview 阶段）

| 限制 | 说明 |
|---|---|
| 已被取代 | 2026-11-04 正式版发布后不再作为主推，行为与接口可能变动 |
| 纯文本 | 无图像/视频/音频输入（正式版已补视觉） |
| 独立评测缺位 | benchmark 全为厂商口径，第三方榜单未收录 |
| 过度推理 | 复杂任务长思考、过度自我验证，token 消耗偏高 |
| 部署门槛 | BF16 约 1.5TB；轻量版 214GB 仍需多卡或异构集群 |

## Hy3（上一代正式版）

### 基本信息

- **模型**：Hy3（2026-07-06 正式发布，取代 2026-04-22 的 Hy3-preview）
- **尺寸**：295B（MoE），激活参数 21B，MTP 层 3.8B
- **架构**：80 层主网络、192 个路由专家（每层激活 8 个 + 1 个常驻共享专家）、64 GQA 查询头 + 8 KV 头、隐藏维度 4096
- **上下文**：256K tokens
- **开源**：Apache 2.0，BF16 + FP8 权重均开放
- **多模态**：纯文本
- **思考模式**：`reasoning_effort` 在 no_think / low / high 之间切换（默认 no_think）
- **场景**：Agent 开发、编码辅助、工具调用、办公生产、金融建模、前端设计、游戏制作、私有化部署
- **价格**：输入 ¥1 / 输出 ¥4 / 缓存命中 ¥0.25（每百万 tokens）

### 核心升级（vs Hy3-preview）

1. **后训练数据质量与多样性提升 + RL 算力规模扩大**：以较小尺寸首次比肩国内外 2～5 倍参数规模的旗舰模型
2. **Co-design 方法论**：以扎实模型底座为前提，用真实应用场景构建 Eval、以数据回流反哺训练，借助大模型泛化性把单产品沉淀的能力迁移到其他产品
3. **270 位专家盲测**：Hy3 均分 2.67/4，优于 GLM-5.1（2.51/4），前端/数据与存储/CI-CD 优势显著
4. **生产级稳定性**：工具调用错误恢复能力大幅提升，跨脚手架（CodeBuddy/Cline/KiloCode）SWE-bench Verified 标准差 ≤4%
5. **幻觉率大幅下降**：12.5% → 5.4%，常识错误率 25.4% → 12.7%
6. **多轮对话能力增强**：多轮问题率 17.4% → 7.9%，MRCR 42.9% → 75.1%
7. **Apache 2.0 协议**（preview 为 Tencent Hunyuan Community License）

### 核心能力（Benchmark）

| 能力 | 指标 | 来源 |
|------|------|------|
| 编码（SWE-bench Verified） | 78.0%（高推理强度 + 工具） | [DataLearner](https://www.datalearner.com/ai-models/pretrained-models/tencent-hy3) |
| 编码（SWE-bench Multilingual） | 75.8% | 同上 |
| 编码（SWE-bench Pro） | 57.9% | 同上 |
| 编码（DeepSWE） | 28.0% | 同上 |
| 数学推理（IMO-AnswerBench） | 90.0% | 同上 |
| 科学推理（GPQA Diamond） | 90.4%（高推理强度） | 同上 |
| 高难度推理（HLE） | 37.0（无工具）/ 53.2（工具） | 同上 |
| 浏览/信息检索（BrowseComp） | 84.2%（联网 + 工具） | 同上 |
| Agent 工具调用（MCP-Atlas） | 79.1% | 同上 |
| Agent 工具调用（TerminalBench 2.1） | 71.7% | 同上 |
| Agent 工具调用（Tool Decathlon） | 48.5% | 同上 |
| 长上下文（AA-LCR） | 73.4% | 同上 |
| 开源部署 | 21B 激活参数，Apache 2.0 免费商用 | [GitHub](https://github.com/Tencent-Hunyuan/Hy3) |

### 生产可靠性（vs preview）

| 指标 | preview | Hy3 正式版 | 说明 |
|------|---------|-----------|------|
| 幻觉率 | 12.5% | 5.4% | 基于真实产品内部评测 |
| 常识错误率 | 25.4% | 12.7% | 细粒度数据清洗 + 训练约束 |
| 多轮问题率 | 17.4% | 7.9% | 指代消解 / 省略还原 / 多轮约束继承 |
| MRCR（长对话理解） | 42.9% | 75.1% | 长程交互中复杂意图保持 |
| 跨脚手架标准差 | — | ≤4% | SWE-bench Verified 在 CodeBuddy/Cline/KiloCode 上 |

## 代际演进（Hy3 → Hy4 preview → Hy4）

| 维度 | Hy3 | Hy4 preview | Hy4（正式版） |
|---|---|---|---|
| 总参 / 激活 | 295B / 21B | 770B / 49B | 官方未单列，渠道沿用 770B / 49B |
| 上下文 | 256K | 1M | 1M（输入 960K / 输出 64K） |
| 注意力 | GQA（64 查询头 / 8 KV 头） | Gated DSA + IndexCache | 官方未重申，沿用 preview 架构 |
| 多模态 | 纯文本 | 纯文本 | **首次支持图像输入** |
| 电脑操作 | 无 | 无 | **首次支持 Computer Use** |
| 默认推理强度 | no_think | high（思维链） | high（思维链） |
| 研发闭环 | 无 | 参与推理栈优化，吞吐 +31.8% | Hyra 2.0 + Jev / HyCell / HyPDE |
| 权重开放 | Apache 2.0 | Apache 2.0（已开源） | ⚠️ 未放出，官方称"计划开源" |
| 定价（国内） | ¥1 / ¥4 | ¥6 / ¥18 | ¥6 / ¥18（加量不加价） |
| 主评测 | TB 2.1 71.7 / DeepSWE 28.0 | TB 2.1 85.4 / DeepSWE 64.3 | 见上方 Benchmark 节（更换基准，不可拼接） |

> 演进逻辑：Hy3 走"小激活 + 极致性价比"，Hy4 转向"大容量 + 长上下文 + 生产力上限"，价格带整体上移；正式版在价格不变的前提下补上视觉与 Computer Use，但把"权重开放"从既成事实退回为计划项。

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 视觉理解 + 工具调用 | Hy4 首次支持图像输入，可做细粒度图像处理、复杂图表分析与多模态数学推理（具体分数见上方 Benchmark 节） |
| Computer Use | 命令行 + GUI 双通道，针对 Blender / CAD 等专业软件专项训练 |
| 长程 coding / 终端任务 | 1M 上下文支撑跨文件长程开发与多轮工具调用，DeepSWE / SWE-Marathon 均为 10 分以上量级提升 |
| 生产力 Co-design | CodeBuddy / WorkBuddy 真实任务数据回流，办公 / 游戏 / 金融 / 安全专家共建语料 |
| Agent 工具调用 | APEX-Agents 等工作型 Agent 基准为量级提升；Hy3 仍可作轻量工具调用档 |
| 研发流程自我优化 | Hy4 结合 Hyra 2.0 优化同架构小模型预训练，产出 Jev 与 HyCell / HyPDE |
| 开源可自部署（仅 Hy3 / Hy4 preview） | Apache 2.0；preview 轻量版 214GB 可异构集群推理 |

### 核心限制

| 限制项 | 说明 |
|--------|------|
| **权重未放出** | Hy4 正式版目前只有 API，不能自部署、无许可证可查；可自部署的旗舰仍是 Hy4 preview |
| 构造型数学弱 | Hy-FrontierMath T5 仅 13.0，与前沿闭源模型差一个量级 |
| 高难度知识推理 | HLE 类指标仍落后 GLM / Kimi 一档（正式版未单独披露 HLE 新值，preview 口径 55.4） |
| 办公自动化专项 | AutomationBench（preview）仅 32.1；正式版改用 WorkBuddy 内部评测，两者不可直比 |
| 独立验证缺位 | 无 Artificial Analysis 等第三方指数，官方 Bench 附录又存在多套 harness 与脚注，选型须自行压测 |
| 轻量档缺位 | 最小仍为 295B/21B，Hy4 Flash 未发布；高并发轻任务无对应价位 |
| 幻觉口径不统一 | 12.95%→7.2% 与 15.76%→5.45% 两个官方渠道口径并存，对外引用须注明来源 |
| 过度推理 | 默认 high 推理强度，复杂任务长思考、过度自我验证，token 账单偏高 |

## 定价概览

| 模型 | 输入（/1M） | 输出（/1M） | 缓存命中（/1M） | 备注 |
|------|------------|-------------|----------------|------|
| **Hy4**（国内刊例） | ¥6 | ¥18 | ¥0.3 | 腾讯云 TokenHub，与 preview 同价 |
| **Hy4**（海外刊例） | ≈$0.90 | ≈$2.70 | ≈$0.045 | 官方英文稿 approx 口径 |
| **Hy4 preview**（国内 / 海外） | ¥6 / $0.834 | ¥18 / $2.501 | ¥0.3 / $0.042 | 已被正式版取代，仅历史参考 |
| **Hy3** | ¥1 | ¥4 | ¥0.25 | 统一固定价，系列最低价档 |

> 定价来源：[Hy4 官方英文新闻稿](https://www.tencent.com/tencent-launches-hy4-joining-the-ranks-of-the-worlds-leading-open-source-ai-models/)（海外刊例）+ 官方中文发布页（国内），核实日期 2026-11-06。⚠️ 第三方平台上实际挂价可能低于刊例（OpenRouter 当前显示 $0.417 / $1.251，与官方同期折扣同步），对外报价前必须回查官方页当期值。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 带图分析（图表 / 文档 / 多图） | Hy4 | 首次视觉能力，图表解读与细粒度定位是主场景 |
| 专业软件操作（Blender / CAD 类） | Hy4 | Computer Use + 专业软件专项训练 |
| 长文档 / 跨文件长程 coding | Hy4 | 1M 上下文（输入 960K），Hy3 仅 256K |
| 办公协作与金融研究 | Hy4 | WorkBuddy 83.18、金融众测开源第一，且有外部 iRaB 交叉 |
| 游戏 / 前端原型 | Hy4 | GameDev +19.1%、GameLogic +9.8%，已适配 UE / Unity / Godot |
| 私有化部署 / 预算敏感 | Hy3 | Apache 2.0、¥1/¥4，系列唯一低价档 |
| 旗舰能力自部署 | Hy4 preview | 正式版权重未放，preview 是当前唯一可下载的 Hy4 系架构 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 需要自部署 Hy4 正式版 | 权重与 system card 尚未放出，许可证未知 |
| 高并发轻量任务（摘要/抽取/分类） | 无小模型档，Hy4 Flash 未发布，单价与时延均不占优 |
| 构造型前沿数学 / 定理发现 | Hy-FrontierMath T5 13.0，仅适用流程型科研辅助 |
| 跨模型榜单横比选型 | 官方 Bench 附录存在多种 harness 与内部自建任务集，分数不可跨模型直比 |
| 需要第三方背书的采购决策 | 暂无 AA 等独立指数，建议先做 shadow 压测 |

## Co-design 方法论

混元的迭代方法论（来源：[腾讯混元解决方案](https://hunyuan.tencent.com/solutions)）：

1. **以扎实模型底座为前提**：Hy3 的 295B MoE + 快慢思考；Hy4 的 770B/49B + 1M 上下文
2. **用真实应用场景构建 Eval**：从 50+ 腾讯业务团队收集反馈，专家盲测（Hy3 270 位 / Hy4 preview 163 位 / Hy4 正式版金融众测 213 位）
3. **以数据回流反哺训练**：WorkBuddy / 元宝 / ima / Marvis 等产品的真实日志与反馈用于 SFT + RL
4. **借助大模型泛化性迁移能力**：单产品沉淀的能力（意图理解、工具调用）迁移到其他产品

> 本质是**模型-产品协同进化**：模型能力提升 → 产品体验改善 → 更多用户 → 更多真实数据 → 模型继续提升。Hy4 进一步把这个闭环向内延伸——让模型参与训练方法、评测框架与推理栈的优化。

## 市场表现（Hy3）

- Preview 上线以来日均 token 消耗量增长 **20 倍**
- 连续三周登顶 OpenRouter 周榜（2026.04.27–05.11）
- Token 调用量达上一代 Hy2 的 10 倍
- 代码与智能体场景增幅超 16.5 倍
- 2026-06-11 OpenRouter 周 Token 量 3.3T，排名 #2（仅次于 DeepSeek V4 Flash）
- WorkBuddy 上自主选择 Hy3 的用户数增长 **6 倍**
- 已接入 WorkBuddy/CodeBuddy、元宝、Marvis、ima 等多个腾讯业务

### 为什么市场认可度高

1. **价格碾压**：输出价远低于同级别旗舰，OpenRouter 用户以个人开发者和小团队为主，价格极度敏感
2. **能力"够用"且持续进步**：SWE-bench Verified 从 preview 的 74.4% 提升到 78.0%
3. **开源可自部署**：295B MoE 仅 21B 激活，Apache 2.0 免费商用
4. **Co-design 飞轮**：腾讯多元产品矩阵提供真实反馈 → 模型优化 → 反哺所有产品
5. **限免策略**：两周限免建立使用惯性，结束后留存率高

## 关键技术论文

[⚠️ 待补充]——Hy4 正式版的模型权重与 system card 均未放出（官方称近期发布），暂无技术报告；preview 阶段亦无公开技术报告；Hy3 的架构与训练细节以官方发布页与 GitHub README 为准。

## 参考资料

- [Hy4 官方发布页](https://hunyuan.tencent.com/research/hy4)（2026-11-04，视觉 / Computer Use / 定价 / Bench 附录；JS 渲染，正文经搜索快照与英文稿交叉）
- [Hy4 官方英文新闻稿](https://www.tencent.com/tencent-launches-hy4-joining-the-ranks-of-the-worlds-leading-open-source-ai-models/)（海外定价、权重"计划开源"、安全边界与场景数据）
- [OpenRouter: tencent/hy4](https://openrouter.ai/tencent/hy4)（第三方平台挂价与上下文）
- [Hy4 正式版 Bench 附录逐项转录与口径拆解](https://www.cnblogs.com/foxcharon/p/23557908)（第三方；含星号/† 脚注、harness 分配与开源口径对比）
- [腾讯云开发者社区：Hy4 正式版解读](https://developer.cloud.tencent.com/article/2776227)（场景细节与接入方式，腾讯系转载）
- [腾讯官方新闻稿 — Hy4 preview 发布并开源](https://www.tencent.com/tencent-releases-and-open-sources-tencent-hy4-preview/)（2026-08-28，含海外定价与自我改进闭环披露）
- [Hy4-preview GitHub README](https://github.com/Tencent-Hunyuan/Hy4-preview/blob/main/README_CN.md)（完整架构规格、部署方案、Apache 2.0）
- [HuggingFace: tencent/Hy4-preview](https://huggingface.co/tencent/Hy4-preview) · [ModelScope](https://modelscope.cn/models/Tencent-Hunyuan/Hy4-preview)
- [DataLearner — Hy4 preview 评测与定价](https://www.datalearner.com/ai-models/pretrained-models/hy4-preview/analysis)
- [Hy3 官方发布页](https://hy.tencent.com/research/hy3)（官方博客）
- [腾讯混元解决方案](https://hunyuan.tencent.com/solutions)（Co-design 方法论）
- [Tencent Hunyuan Hy3 GitHub](https://github.com/Tencent-Hunyuan/Hy3)（Apache 2.0）
- [HuggingFace: tencent/Hy3](https://huggingface.co/tencent/Hy3) · [ModelScope](https://modelscope.cn/models/Tencent-Hunyuan/Hy3)
- [新浪财经：Hy3 正式发布报道](https://finance.sina.com.cn/stock/relnews/hk/2026-07-06/doc-inifwfpy8675405.shtml)
- [DataLearner: Hy3 评测与定价](https://www.datalearner.com/ai-models/pretrained-models/tencent-hy3)
- [新京报：Hy3 API 定价](https://www.bjnews.com.cn/detail/1783323355129516.html)
- [腾讯云 TokenHub](https://console.cloud.tencent.com/tokenhub/models/detail?modelId=hy4)
- [AI Studio 在线体验](https://aistudio.tencent.com/)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-11-06 | **Hy4 正式版增量升级**：主推切至 Hy4（11-04 GA，首次视觉 + Computer Use），新增正式版专章；preview 降为历史版本；补入权重仍在"计划开源"状态、定价与 Bench 口径差异；信源以官方英文稿与 Bench 附录第三方转录交叉 |
| 2026-07-08 | Hy3 正式版（2026-07-06 发布）全面更新：Benchmark、生产可靠性、Co-design 方法论、API 定价、业务接入。**文件重命名**：hy3-preview.md → hy3.md |
| 2026-06-11 | 初始创建：Hy3-preview 产品知识提炼 |
