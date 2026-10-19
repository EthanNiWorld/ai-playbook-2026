# 混元（腾讯 Hunyuan）模型系列

> 最后更新: 2026-10-19
> 所属厂商: 腾讯（Tencent Hunyuan）
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 腾讯混元开源 MoE 模型系列，以"生产力场景 Co-design + 极致性价比 + Apache 2.0 可自部署"为差异化主线
**当前主推**: Hy4 preview（2026-08-28，770B/49B，1M 上下文，纯文本）；上一代正式版 Hy3（2026-07-06，295B/21B，256K）
**适用**: 长程 coding / 终端任务（Hy4）、办公生产与金融建模（Hy3）、私有化部署与二次开发（两者均 Apache 2.0）
**不适用**: 多模态输入（两者均纯文本）、长程马拉松工程任务（Hy4 SWE-Marathon 31.9 落后）、办公自动化（Hy4 AutomationBench 32.1）、轻量高并发档（系列无小模型）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Hy4 preview** 🚩 | 新一代开源旗舰（preview） | 1M | 770B/49B、Gated DSA + IndexCache + iHC、模型参与自身研发闭环、Apache 2.0 | 2026-08-28 |
| **Hy3** | 上一代正式版（唯一 GA 版本） | 256K | 295B/21B、异构专家 + 快慢思考融合、Apache 2.0 | 2026-07-06 |
| Hy3-preview | 历史版本（已被 Hy3 取代） | 256K | 异构专家 + P-Penalty Loss | 2026-04-22 |

> 📌 **代际状态（2026-10-19 核实）**：Hy4 目前仅有 preview，正式版未发布——官方口径为"下一批模型近期上线"，并预告将提升性能与**多模态**能力。Hy3 仍是唯一 GA 版本，两者并行可用。

## Hy4 preview（新一代旗舰）

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
| 多模态 | **纯文本**（preview 阶段；正式版预告补多模态） |
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

### 已知限制

| 限制 | 说明 |
|---|---|
| 仍是 preview | 正式版未发布，行为与接口可能变动 |
| 纯文本 | 无图像/视频/音频输入 |
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

## 代际演进（Hy3 → Hy4）

| 维度 | Hy3 | Hy4 preview | 变化 |
|---|---|---|---|
| 总参 / 激活 | 295B / 21B | 770B / 49B | 参数 2.6×，激活 2.3× |
| 上下文 | 256K | 1M | 4× |
| 注意力 | GQA（64 查询头 / 8 KV 头） | Gated DSA + IndexCache | 稀疏注意力 + 跨层索引复用 |
| MoE | 192 专家（top-8 + 共享） | 256 专家（top-8 + 共享） | 专家容量扩容 |
| 残差 | 单流 | iHC 4 路 | 层间信息通路加宽 |
| 默认推理强度 | no_think | high（思维链） | 默认更重推理，token 消耗上升 |
| 多模态 | 纯文本 | 纯文本 | 未变化（正式版预告补） |
| DeepSWE | 28.0 | 64.3 | 2.3× |
| Terminal-Bench 2.1 | 71.7 | 85.4 | +13.7 |
| 定价（国内） | ¥1 / ¥4 | ¥6 / ¥18 | 6× / 4.5× |

> 演进逻辑：Hy3 走"小激活 + 极致性价比"，Hy4 转向"大容量 + 长上下文 + 生产力上限"，价格带整体上移，但仍是同代开源旗舰中偏低的一档。

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 长程 coding / 终端任务 | Hy4 Terminal-Bench 2.1 85.4、SWE-bench Multilingual 82.9（厂商口径） |
| 1M 上下文工程 | Hy4 支持跨文件长程开发与多轮工具调用 |
| 生产力 Co-design | CodeBuddy / WorkBuddy 真实任务数据回流，办公/游戏/金融/安全专家共建语料 |
| 开源可自部署 | 两者均 Apache 2.0；Hy4 轻量版 214GB 可异构集群推理 |
| Agent 工具调用 | Hy4 MCP-Atlas 83.7、Toolathlon 74.1；Hy3 MCP-Atlas 79.1 |
| 研发流程自我优化 | Hy4 参与自身训练方法/评测/算子优化，推理栈吞吐 +31.8%（官方自述） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 多模态 | 纯文本 | Hy4 正式版预告补多模态，当前不可用 |
| 长程马拉松 | Hy4 SWE-Marathon 31.9 | 落后 GLM-5.3（42.5）与 Kimi K3（42.0） |
| 知识型推理 | Hy4 HLE 55.4 | 落后 GLM-5.3（62.5）与 Kimi K3（59.8） |
| 办公自动化 | Hy4 AutomationBench 32.1 | 30 个模型中排第 20 |
| 独立验证 | AA 指数缺位 | 厂商口径为主，选型需自行压测 |
| 轻量档缺位 | 最小 295B/21B | 无 $0.1–0.3 级小模型，无法覆盖高并发轻任务 |
| 过度推理 | 官方自认 | 复杂任务长思考、过度自我验证，token 账单偏高 |

## 定价概览

| 模型 | 输入（/1M） | 输出（/1M） | 缓存命中（/1M） | 备注 |
|------|------------|-------------|----------------|------|
| **Hy4 preview**（国内） | ¥6 | ¥18 | ¥0.3 | 腾讯云 TokenHub |
| **Hy4 preview**（海外） | $0.834 | $2.501 | $0.042 | TokenHub + OpenRouter |
| **Hy3** | ¥1 | ¥4 | ¥0.25 | 统一固定价 |

> 定价来源：[腾讯官方新闻稿](https://www.tencent.com/tencent-releases-and-open-sources-tencent-hy4-preview/)（海外）、[DataLearner](https://www.datalearner.com/ai-models/pretrained-models/hy4-preview/analysis)（国内），核实日期 2026-10-19。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 长程 coding / 终端自动化 | Hy4 preview | Terminal-Bench 2.1 85.4、MCP-Atlas 83.7；1M 上下文跨文件 |
| 大型代码仓库 / 长文档 | Hy4 preview | 1M 上下文，Hy3 仅 256K |
| 一句话生成可玩游戏原型 | Hy4 preview | 官方演示能力，接游戏引擎多轮迭代 |
| 科研推理（物理/数学/AI 研发） | Hy4 preview | GPQA 92.3、CritPt 16.9 |
| 办公生产 / 金融建模 | Hy3 | 已有 WorkBuddy 任务成功率 72%→90%、耗时 -34% 的验证数据 |
| 私有化部署 / 二次开发 | Hy3（8×H20-3e）/ Hy4 轻量版（214GB） | 均 Apache 2.0 |
| 预算敏感 Agent 开发 | Hy3 | ¥1/¥4，输出价为同代旗舰最低档 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 多模态 Agent（GUI / 视觉 / 音视频） | 两者均纯文本 |
| 长程马拉松式工程任务 | Hy4 SWE-Marathon 31.9，落后同代开源旗舰 |
| 办公流程自动化（表单/CRM/SaaS） | Hy4 AutomationBench 32.1，明显弱于通用 Agent 模型 |
| 高并发轻量任务（摘要/抽取/分类） | 系列无小模型档，单价与时延均不占优 |
| 需要第三方背书的采购决策 | 暂无 AA 等独立指数，建议先做 shadow 压测 |

## Co-design 方法论

混元的迭代方法论（来源：[腾讯混元解决方案](https://hunyuan.tencent.com/solutions)）：

1. **以扎实模型底座为前提**：Hy3 的 295B MoE + 快慢思考；Hy4 的 770B/49B + 1M 上下文
2. **用真实应用场景构建 Eval**：从 50+ 腾讯业务团队收集反馈，专家盲测（Hy3 270 位 / Hy4 163 位）
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

[⚠️ 待补充]——Hy4 preview 暂未见公开技术报告；Hy3 的架构与训练细节以官方发布页与 GitHub README 为准。

## 参考资料

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
- [腾讯云 TokenHub](https://console.cloud.tencent.com/tokenhub/models/detail?modelId=hy4-preview)
- [AI Studio 在线体验](https://aistudio.tencent.com/)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-19 | **合并重构**：新建厂商级文档 hunyuan.md，合并原 hy3.md（Hy3 正式版）与 Hy4 preview 调研。新增 Hy4 preview 全量信息（770B/49B、1M、Gated DSA + IndexCache + iHC、MTP 10B/0.7B、$0.834/$2.501、自我改进闭环 +31.8% 吞吐、轻量版 214GB、benchmark 与制衡点），新增「代际演进」对比表与「轻量档缺位」限制；Hy3 内容完整保留。原 hy3.md 已删除 |
| 2026-07-08 | Hy3 正式版（2026-07-06 发布）全面更新：Benchmark、生产可靠性、Co-design 方法论、API 定价、业务接入。**文件重命名**：hy3-preview.md → hy3.md |
| 2026-06-11 | 初始创建：Hy3-preview 产品知识提炼 |
