# MiniMax M 系列模型

> 最后更新: 2026-06-15
> 所属厂商: MiniMax（稀宇科技）
> 产品类别: MaaS
> 状态: Published

**定位**: MiniMax 自研文本/推理大模型系列，从 abab 架构演进至 M 系列（MoE 架构），强调开源、长上下文与 Agent 能力
**当前主推**: M3（2026.06.01）
**适用**: Agentic Coding、长上下文任务、专业办公、软件工程、ML 工程
**不适用**: 超低延迟实时对话、纯中文日常闲聊

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **MiniMax-M3** | 🚩 旗舰 | 1M tokens | MSA 稀疏注意力、原生多模态、前沿 Coding/Agent | 2026.06.01 |
| **MiniMax-M2.7** | 次旗舰 | 100 万 tokens | 自我进化能力、Benchmark 追平 GPT-5.3-Codex，性价比极高 | 2026.03.18 |

> 📌 **历史模型**：MiniMax-M2（2025.11，Agent/代码专项）和 MiniMax-M1（2025.08，开源标杆）仍可调用，但已被 M3/M2.7 取代，不建议新项目选用。

### MiniMax-M3

- **模型**：MiniMax-M3
- **公司**：MiniMax
- **时间**：2026 年 6 月 1 日 [来源: ai-knowledge-by-qoder-ai-native-agent-20260601.md]
- **架构**：MoE + MSA（MiniMax Sparse Attention） [来源: minimaxi.com/blog/minimax-m3]
- **上下文**：1M tokens [来源: minimaxi.com/blog/minimax-m3]
- **多模态**：原生多模态（图片 + 视频输入 + Computer Use） [来源: minimaxi.com/blog/minimax-m3]
- **开源**：已开源权重，官方定位为"业内首款同时集齐百万上下文、前沿代码能力、原生多模态三合一的开源权重重大模型" [来源: 用户口述 + MiniMax 官方宣传图] ⚠️ 待官方验证
- **场景**：Agentic Coding、长程 Agent 任务、论文复现、CUDA 算子优化、自主训模型
- **特点**：
  1. **MSA 稀疏注意力**：100 万上下文下每 token 计算量仅为上代 1/20，Prefill 加速 9.7x，Decode 加速 15.6x，比 Flash-Sparse-Attention/flash-moba 快 4 倍以上 [来源: minimaxi.com/blog/minimax-m3]；技术原理详见 [MSA 论文解读](msa-sparse-attention.md)（arXiv:2606.13392）
  2. **前沿 Coding/Agent**：SWE-Bench Pro 59.0%（> GPT-5.5, > Gemini 3.1 Pro，低于 Opus 4.8 的 69.2% [来源：ai-native-expert 2026-06-02]）、Terminal Bench 2.1 66.0%、MCP Atlas 74.2%、Claw-Eval 全模型 #1 [来源: minimaxi.com/blog/minimax-m3]
  3. **原生多模态**：OmniDocBench 超过 Gemini 3.1 Pro、SVG-Bench 超过 Opus 4.8 [来源: minimaxi.com/blog/minimax-m3]
  4. **长程自主能力**：自主运行 12h 复现 ICLR 获奖论文（18 次 commit + 23 张图表）、24h CUDA 算子优化（9.4x 加速）、12h 自主训模型（PostTrainBench 0.37） [来源: minimaxi.com/blog/minimax-m3]
  5. **定价（分两档）**：≤512K 输入 ¥4.2/M 输出 ¥16.8/M；512K–1M 输入 ¥8.4/M 输出 ¥33.6/M [来源: finance.sina.com.cn]
  6. **Token Plan**：Plus ¥49/月（6 亿 token）、Max ¥119/月（18 亿）、Ultra ¥469/月（55 亿），约 Claude 订阅 15 倍用量 [来源: minimaxi.com/blog/minimax-m3]
  7. **支持 thinking / non-thinking 两种模式**，共享定价 [来源: minimaxi.com/blog/minimax-m3]

### MiniMax-M2.7

- **模型**：MiniMax-M2.7
- **公司**：MiniMax
- **时间**：2026 年 3 月 18 日
- **尺寸**：MoE，总参 2300 亿 / 激活 100 亿（激活率 ~4.3%）
- **上下文**：100 万 tokens，最大输出 16,384 tokens
- **多模态输入**：文本 + 图片 + 音频
- **场景**：Agentic Coding、长上下文分析、专业办公、软件工程
- **特点**：
  1. **自我进化能力**：模型深度参与自身迭代，自主构建 Agent Harness、更新 Memory、驱动强化学习，100+ 轮自主迭代带来 30% 效果提升
  2. **Benchmark 追平 GPT-5.3-Codex**：SWE-Pro 56.22%、GDPval-AA ELO 1495（开源最高）
  3. **性价比极高**：$1 / $5 per 1M tokens，约为 Claude Opus 4.6 的 1/15

### MiniMax-M2

- **模型**：MiniMax-M2
- **公司**：MiniMax
- **时间**：2025 年下半年（2025.11）
- **尺寸**：MoE [⚠️ 待验证具体参数]
- **上下文**：100K+ tokens
- **场景**：Agent 与代码场景
- **特点**：强化工具调用能力，延续开源策略

### MiniMax-M1

- **模型**：MiniMax-M1
- **公司**：MiniMax
- **时间**：2025 年中
- **尺寸**：MoE [⚠️ 待验证具体参数]
- **上下文**：128K+ tokens
- **场景**：推理、开源部署
- **特点**：全球首个开源、大规模混合注意力（Hybrid Attention）推理模型，登顶 Artificial Analysis 开源榜单

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **Agentic Coding（M3）** | SWE-Bench Pro 59.0%（> GPT-5.5, > Gemini 3.1 Pro）、Terminal Bench 2.1 66.0% [来源: minimaxi.com/blog/minimax-m3] |
| **Agentic Coding（M2.7）** | SWE-Pro 56.22%，追平 GPT-5.3-Codex；可完成端到端完整项目交付、Bug 定位 |
| **MSA 稀疏注意力（M3）** | 1M 上下文计算量降为上代 1/20，Prefill 9.7x / Decode 15.6x 加速 [来源: minimaxi.com/blog/minimax-m3] |
| **原生多模态（M3）** | 图片 + 视频输入 + Computer Use；OmniDocBench > Gemini 3.1 Pro [来源: minimaxi.com/blog/minimax-m3] |
| **长程自主运行（M3）** | 12h 论文复现、24h CUDA 优化（9.4x 加速）、PostTrainBench 0.37 [来源: minimaxi.com/blog/minimax-m3] |
| **MCP 工具调用（M3）** | MCP Atlas 74.2% [来源: minimaxi.com/blog/minimax-m3] |
| **自我进化** | 模型自主驱动自身训练迭代，100+ 轮迭代效果提升 30% |
| **长上下文** | 100 万 token 上下文，NIAH (1M) 准确率 96.8% |
| **ML 工程** | MLE Bench Lite 66.6% 得牌率，仅次于 Opus-4.6 和 GPT-5.4 |
| **Agent Teams** | 支持原生多智能体协作，稳定的角色身份锚定 |
| **专业办公** | Word/Excel/PPT 复杂编辑、金融年报分析、营收预测建模 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 开源版本 | M1/M2/M3 已开源，M2.7 闭源 | M3 官方确认为开源权重模型 [来源: 用户口述] ⚠️ 待官方验证 |
| 最大输出 | 16,384 tokens | 单次回复长度受限 |
| 厂商背景 | MiniMax 非阿里云产品 | 需通过 MiniMax 开放平台调用，非百炼 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| Agentic Coding（重度） | M3 | SWE-Bench Pro 59.0%，Terminal Bench 2.1 66.0% |
| 长程自主任务 | M3 | 12h 论文复现、24h CUDA 优化、自主训模型 |
| 多模态 Agent（Computer Use） | M3 | 原生图片/视频输入 + 桌面操作 |
| 整仓库代码审查 | M3 / M2.7 | 100 万 token 上下文支持完整代码库分析 |
| 开源部署 / 研究 | M1 | Artificial Analysis 开源榜登顶 |
| 工具调用 / Agent | M2 | 强化函数调用能力 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 超低延迟实时对话 | 非实时优化方向 |
| 纯中文日常闲聊 | 非核心优化场景 |

## 定价

| 模型 | 输入 | 输出 | 上下文分档 |
|------|------|------|------------|
| **MiniMax-M3** | ¥4.2/M tokens | ¥16.8/M tokens | ≤512K [来源: finance.sina.com.cn] |
| **MiniMax-M3** | ¥8.4/M tokens | ¥33.6/M tokens | 512K–1M [来源: finance.sina.com.cn] |
| **MiniMax-M2.7** | $1.00/M tokens | $5.00/M tokens | — |
| Claude Opus 4.8 | $5.00/M tokens | $25.00/M tokens | — |
| GPT-5.5 | $7.50/M tokens | $22.50/M tokens | — |

> M3 有限时 7 天 5 折活动。支持 thinking / non-thinking 两种模式，共享定价。[来源: minimaxi.com/blog/minimax-m3]
> M3（¥4.2）价格约为 Claude Opus 4.8（$5 ≈ ¥36）的 **约 1/8**，M2.7 时代相对 Opus 4.6 为 1/15。
> M3 国际定价：MiniMax 官方平台 M3-Priority 永久5折价 $0.45/$1.80（≤512K），512K–1M 区间 $0.90/$3.60 [来源: api.minimax.chat]；OpenRouter 标准 M3 当前临时5折至 $0.30/$1.20（原价 $0.60/$2.40）[来源: openrouter.ai/minimax/minimax-m3，2026-06-14 核实]。

## 市场表现

- M2.7 在 OpenRouter 平台上的调用量一度超过 Claude Opus 4.6，是目前用量增长最快的模型之一
- 2026 年 2 月 M2 系列每百万 Token 推理算力成本较 2025 年 12 月下降超过 **50%**
- 日均 token 消耗量增长超 6 倍，其中 Coding Plan 增长超 10 倍
- M3 发布当日（2026.06.01）MiniMax（00100.HK）早盘涨超 7% 后转跌，收盘跌超 15%，报 708 港元 [来源: finance.sina.com.cn]
- 用户反馈：M3 速度更快、上下文能力不错，但 Token 消耗更快、变相涨价 [来源: finance.sina.com.cn]
- 公司 2025 年营收约 7904 万美元（同比 +159%），年内亏损 18.7 亿美元 [来源: finance.sina.com.cn]

### OpenRouter 排名表现（2026-06-11）

| 排名 | 模型 | 周 Token 量 | 增长 |
|------|------|-------------|------|
| #1 | DeepSeek V4 Flash | 4.07T | 41% |
| #2 | Hy3-preview | 3.3T | 12% |
| #3 | **MiniMax M3** | **2.89T** | **>999%** |

[来源: openrouter.ai/rankings, 2026-06-11]

### M3 高调用量的驱动因素

1. **"三合一"独占生态位**：1M 上下文 + 前沿编码（SWE-Bench Pro 59.0%）+ 原生多模态 + 开源权重，这个组合在开源模型里无竞品
2. **从 M2.5 继承的"默认前端模型"地位**：开发者的分层路由策略（80% 日常用 MiniMax，20% 深推用 Opus），成本下降 17x [来源: workos.com/blog/minimax-m25-most-popular-model-openrouter]
3. **MSA 稀疏注意力**：1M 上下文计算量仅为上代 1/20，实际推理成本远低于纸面价格
4. **OpenClaw 生态绑定**：M3 在 OpenClaw Agent 框架使用量 #1 [来源: openrouter.ai/collections/openclaw]
5. **Token Plan 消费级定价**：Plus ¥49/月 6 亿 token ≈ Claude 订阅 15 倍用量，包月用户天然多调用

> 💡 **洞察**：OpenRouter 调用量排行的本质不是"谁最便宜"，而是"谁在开发者的默认工作流里"。Token 消耗量排行 ≠ 价格排行——驱动 token 量的是"工作流复杂度 × 用户基盘惯性 × 生态绑定"，不是单价。能承载复杂 Agent 管道的模型每次消耗巨大，总量反而更高。

## 参考资料

- [MiniMax M3 官方博客](https://www.minimaxi.com/blog/minimax-m3)
- [MiniMax 投资者材料 PDF](https://ir-upload.realxen.net/iis/0100/uploads/iis/2026/11985588-0.PDF)
- [MiniMax 投资者材料 PDF](https://ir-upload.realxen.net/iis/0100/uploads/iis/2026/12116753-0.PDF)
- [MiniMax 开放平台](https://platform.minimaxi.com)
- Artificial Analysis 开源榜单
- [新浪科技：MiniMax 新模型报道](https://finance.sina.com.cn/tech/roll/2026-06-01/doc-inhzwyqq3940096.shtml)
- [OpenRouter 实时排名](https://openrouter.ai/rankings)
- [M3 OpenRouter 页面](https://openrouter.ai/minimax/minimax-m3)
- [WorkOS: M2.5 霸榜分析（分层路由策略）](https://workos.com/blog/minimax-m25-most-popular-model-openrouter)
- [OpenClaw 使用排名](https://openrouter.ai/collections/openclaw)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-15 | M3 MSA 描述补充论文来源 arXiv:2606.13392，新增 [MSA 技术解读](msa-sparse-attention.md) 交叉链接 |
| 2026-06-14 | 新增 M3 国际定价信息：M3-Priority 永久5折价 $0.45/$1.80（MiniMax 官方平台）、OpenRouter 标准 M3 临时5折 $0.30/$1.20 |
| 2026-06-11 | 合并：inbox/ai-knowledge-by-qoder-ai-native-agent-20260611.md - M3 OpenRouter 排名 #3（2.89T/周，>999% 增长）、高调用量 5 大驱动因素、Token 消耗量驱动力洞察 |
| 2026-06-08 | 更新：M3 开源状态从"计划 10 天内开源"修正为"已确认开源权重" [来源: 用户口述 + MiniMax 官方宣传图] |
| 2026-06-04 | 主推模型表精简：仅保留 M3（旗舰）+ M2.7（次旗舰）为主推，M2/M1 移入历史模型标注 |
| 2026-06-01 | 合并：ai-knowledge-by-qoder-ai-native-agent-20260601.md - M3 从"即将"升级为正式发布，新增 M3 详细参数、Benchmark、定价、MSA 稀疏注意力、Token Plan、市场反应 |
| 2026-05-28 | 新建文档，首次提炼 M 系列模型系列信息 |