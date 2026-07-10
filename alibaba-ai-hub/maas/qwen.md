# 通义千问 (Qwen)

> 最后更新: 2026-07-10
> 所属厂商: 阿里云
> 产品类别: MaaS

**定位**: 阿里云自研大语言模型系列，覆盖文本/代码/多模态，开源+商业双轨并行
**当前主推**: Qwen3.7-Max（旗舰 Agent）/ Qwen3.7-Plus（多模态智能体）/ Qwen3.6-Flash（轻量快速）
**适用**: 企业级AI应用开发、智能对话、代码生成、多模态理解、长时间自主 Agent
**不适用**: 需要完全私有化且无网络的极端离线场景

## 当前主推模型

> 数据来源：[百炼模型广场](https://help.aliyun.com/zh/model-studio/models)，2026-06-04 核实

| 模型 | 定位 | 上下文 | 特点 |
|------|------|--------|------|
| **Qwen3.7-Max** | 旗舰 Agent | **1M tokens** | AA Intelligence Index 56.6–57（国产 #1），35小时自主运行，0608 快照起支持视觉输入 |
| **Qwen3.7-Plus** | 多模态智能体 | **1M tokens** | 原生多模态（图/视频/屏幕）+ GUI/CLI Agent + 视觉编码，纯文本接近 Max |
| **Qwen3.6-Flash** | 轻量快速 | 256K tokens | 速度快，成本低，系列内 Flash 仍延用 3.6 代号 |

> 📌 **历史模型**：Qwen3.6-Plus、Qwen3.6-Max-Preview 仍可调用，但已分别被 Qwen3.7-Plus 和 Qwen3.7-Max 取代，不建议新项目选用。

### Qwen3.7-Max

- **模型**：Qwen3.7-Max
- **公司**：阿里云
- **时间**：2026 年 5 月 19 日（阿里云峰会上线）
- **尺寸**：未公开（MoE架构）
- **上下文**：**1M tokens**，最大输出 65,536 tokens
- **定价**：¥12 / ¥36 per 1M input/output tokens；缓存输入 ¥1.2/M（90% 折扣）；5 折活动期间 ¥6/¥18，缓存 ¥0.6/M [来源: developer.aliyun.com/article/1738425]
- **新用户**：免费赠送 100 万 Tokens 试用额度 [来源: developer.aliyun.com/article/1738425]
- **接入**：仅 API（百炼 / DashScope），兼容 OpenAI 和 Anthropic 协议
- **开源**：否，非 open-weight
- **场景**：长时间自主 Agent、Agentic Coding、数学推理、多语言任务
- **定位**："The Agent Frontier"，专为长时自主执行设计的旗舰 Agent 模型

**关键基准**（vendor-published，vs Claude Opus 4.6）：
Terminal-Bench 2.0 **69.7**（+4.3）、SWE-Pro **60.6**（+3.3）、SWE-Verified 80.4 vs 80.8（平手）、HLE **41.4**（+1.4）、GPQA Diamond **92.4**（+1.1）、HMMT 2026 **97.1%**、IMOAnswerBench **90.0%**（+14.7）、Apex **44.5**（+10.0）

**标志性事件**：35 小时自主编码运行（1,158 次工具调用），GPU 内核优化达 10× 加速比（vs Triton 参考）

**快照版本演进**：
- `qwen3.7-max-2026-05-20`：纯文本旗舰，仅支持思考模式
- `qwen3.7-max-2026-06-08`（2026-06-10 上线）：**新增视觉模态理解能力**，支持文本、图像、视频输入，1M 上下文，最大输出 64K，最大图片数 2048，最大视频数 64，支持 Function Calling 和内置工具 [来源: https://help.aliyun.com/zh/model-studio/newly-released-models]
  - 结构化输出（JSON Mode）：官方视觉模型页面标注为 "--"（不支持），但 2026-06-12 实测纯文本和视觉输入两种场景下 `response_format: {"type": "json_object"}` 均成功返回合法 JSON ⚠️ 待官方文档更新确认

### Qwen3.7-Plus

- **模型**：Qwen3.7-Plus
- **公司**：阿里云
- **时间**：Preview 版 2026-05-19/20（阿里云峰会）；stable 快照 `qwen3.7-plus-2026-05-26`，2026-06-02 全量上线 [来源: https://qwen.ai/blog?id=qwen3.7-plus]
- **尺寸**：约 35B 密集架构（preview 阶段 CSDN/网易转述，stable 版官方未公布）[⚠️ 待补充]
- **上下文**：**1M tokens**（阶梯计价 0-256K / 256K-1M）[来源: https://help.aliyun.com/zh/model-studio/model-pricing]
- **输入模态**：文本 + 单图/多图/视频 + 屏幕截图 [来源: https://qwen.ai/blog?id=qwen3.7-plus]
- **场景**：多模态智能体（GUI + CLI 闭环）、视觉编码（图→SVG/网页/前端）、视觉推理、真实世界感知
- **特点**：
  - 多模态智能体：GUI/CLI 操作 + 视觉编码 + 跨框架部署（Claude Code / OpenClaw / Qwen Code）
  - `preserve_thinking` 多轮思维保留
  - 纯文本能力官方称"整体接近 Max 级别"
  - **多模态/GUI 操作为 Qwen3.7 系列最强**
- **定价**：¥2/¥8 per 1M input/output tokens（≤256K）；¥6/¥24（256K-1M）；思考与非思考同价 [来源: https://help.aliyun.com/zh/model-studio/model-pricing]
  - Batch 调用 5 折；输入支持上下文缓存折扣（与 Batch 不可叠加）
  - 推理后付费限时 8 折（截止日期以百炼控制台为准）
- **开源**：否，API 商用闭源（仅通过百炼提供）[来源: https://www.aihub.cn/ai-model/qwen3-7-plus/]
- **Benchmark**（来源: qubrid.com 六模型对比表 + benchlm.ai）：
  - GUI Agent: ScreenSpot Pro 79.0% / AndroidWorld 81.0% / OSWorld-Verified 73.3%（BenchLM Computer Use 全球 #4，75.6 分）
  - Visual Coding: QwenVision2Code 1,772 / QwenSVG 1,588
  - 文档理解: OmniDocBench 1.5 91.4%（最高）/ OCR-Bench-V2 70.7%
  - 纯文本 Agent: Deep-Planning 62.3%（最高）/ MCP-Mark 58.7%（最高）/ MRCR-v2 128K 91.7%（最高）
  - SWE-bench Verified ~68.7%；Arena 综合 1156（preview 阶段第三方数据）[⚠️ stable 版待验证]

> ⚠️ stable 版 benchmark 与精确参数官方尚未公布，建议关注 artificialanalysis.ai / LMSYS Arena 后续复测。

**系列定位分工**：
- **Qwen3.7-Max** = 推理 + Agent 旗舰（~~纯文本~~ → 0608 快照起支持视觉输入，但视觉专项 benchmark 尚待验证；1M 全段无阶梯）
- **Qwen3.7-Plus** = 多模态智能体（视觉 + 语言 + GUI/CLI + 视觉编码，VLA 训练范式，视觉场景首选）
- **Qwen3.6-Flash** = 低成本快速档（系列内未推 3.7-Flash，Flash 仍延用 3.6 代号）

**竞争力要点**：
- vs Qwen3.6-Plus（上一代）：输出价从 ¥12 降至 ¥8（-33%），256K-1M 输出从 ¥48 降至 ¥24（-50%），能力升级同时降价
- vs Qwen3.7-Max：256K 内输入成本仅为 Max 的 1/6、输出约 1/4.5；Max 仅在 SWE-bench/复杂长链路 Agentic Coding 上明显占优；**视觉相关场景（GUI Agent / 视觉编码 / 图文文档理解）Plus 为首选**，Max-0608 视觉专项能力尚待实测
- vs 海外同档（Claude Haiku 4 / GPT-4o-mini）：价位接近，但 Plus 独有 1M 上下文 + 多模态智能体组合

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **深度推理（Max）** | AA Intelligence Index 56.6–57（国产 #1），数学/科学推理全球领先 |
| **Agentic Coding** | Terminal-Bench 2.0 69.7，SWE-Pro 60.6；35小时自主编码运行 |
| **超长上下文** | 1M tokens 上下文窗口，处理大型代码仓库和长文档 |
| **多模态智能体** | Qwen3.7-Plus 支持图/视频/屏幕输入 + GUI/CLI Agent + 视觉编码；Qwen3.7-Max（0608 快照起）支持图/视频输入，但无 GUI Agent 专项 benchmark |
| **数学能力** | HMMT 2026 97.1%、IMOAnswerBench 90.0%，竞赛数学断层领先 |
| **多语言** | WMT24++ 85.8%，覆盖 55 种语言，多语言能力领先 |
| **开源生态** | 多尺寸开源，社区活跃（3.7-Max 除外，为 API only） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 3.7-Max 开源 | 不开放 | API only，无法私有化部署或微调 |
| 3.7-Max 多模态（0520 快照） | 仅文本 | 0520 快照不支持图像输入；0608 快照已新增视觉能力 |
| 3.7-Max 输出冗长 | 97M vs 中位 24M | 实际输出成本可达同类模型的 2-4× |
| 3.6-Max 上下文 | 256K tokens | 仅为 Plus/3.7 的 1/4 |
| 3.6-Max 稳定性 | Preview 状态 | 尚未正式 GA，生产环境建议 Plus 或 3.7-Max |
| 并发限制 | 按账户等级 | 企业版更高 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 长时间自主 Agent / 数学竞赛 / 科研推理 | **3.7-Max** | 35h 自主运行，HMMT 97.1%，全球领先 |
| Agentic Coding（重度） | **3.7-Max** | Terminal-Bench 69.7 |
| Agentic Coding（性价比）/ 长文档 / 多模态 / 生产环境 | **3.7-Plus** | GA 稳定，支持图像/视频/屏幕，1M 上下文，GUI/CLI Agent |
| 高并发轻量调用 | **3.6-Flash** | 低延迟低成本 |
| 私有化部署 | 3.6 开源版 | 支持本地部署 |

### Plus vs Max 场景选型详解

#### Plus 有 benchmark 验证的视觉专项场景（Max-0608 尚无公开数据）

Max-0608 已支持视觉输入，但以下场景 Plus 有明确 benchmark 验证，Max-0608 视觉专项能力尚待实测：

| 场景 | Plus Benchmark | 说明 |
|------|---------------|------|
| GUI Agent / Computer Use | ScreenSpot Pro 79.0%（> GPT-5.4 67.4%）/ AndroidWorld 81.0% / OSWorld-Verified 73.3% | BenchLM 全球排名 #4（75.6 分） |
| Visual Coding（截图→代码） | QwenVision2Code 1,772 / QwenSVG 1,588 | Figma→React、视频→SVG |
| 图文混合文档理解 | OmniDocBench 1.5 91.4%（全场最高）/ OCR-Bench-V2 70.7%（> GPT-5.4 59.1%） | 表格/图表/公式嵌入图片 |
| 视频理解 | 原生视频输入 | Max 完全不支持 |
| 物理世界感知推理 | BabyVision 70.4% / HiPhO 84.1% | 空间关系/物理直觉 |
| 多模态知识检索 | SimpleVQA 81.7%（> GPT-5.4 69.4%）| 视觉证据 + 实时搜索 |

#### 纯文本维度 Plus 也意外领先的场景

| 场景 | Plus 得分 | 同表最强竞品 | Max 已知数据 |
|------|----------|------------|------------|
| Deep-Planning | 62.3%（最高） | Opus 4.6: 58.9% | 无公开数据 |
| Terminal-Bench 2.0-Terminus | 70.3%（最高） | DS-V4-Pro: 67.9% | Max TB 2.0: 69.7%（不同变体） |
| MCP-Mark | 58.7%（最高） | Opus 4.6: 56.7% | 无公开数据 |
| MRCR-v2 128K | 91.7%（最高） | Opus 4.6: 84.0% | 无公开数据 |

> 💡 **Why**：VLA（视觉-语言-动作）联合训练让 Plus 对空间结构、UI 层级、流程规划有更好内隐理解；Agent loop "看→想→写→做→验" 闭环训练目标强化了持续工具调用场景。

#### Max 明确占优的场景

| Benchmark | Max | Plus | 差值 |
|-----------|-----|------|------|
| Apex | 44.5% | 22.7% | +21.8 |
| HLE | 41.4% | 34.7% | +6.7 |
| HMMT 2026 | 97.1% | 92.9% | +4.2 |
| IMOAnswerBench | 90.0% | 86.0% | +4.0 |
| SWE-Pro | 60.6% | 57.6% | +3.0 |
| SWE-Verified | 80.4% | 77.7% | +2.7 |
| GPQA Diamond | 92.4% | 90.3% | +2.1 |

结论：Max 仅在极端数学推理（Apex/IMO/HMMT）和重度 SWE 编码两个维度上明确领先。

#### 推理速度对比

| 指标 | Plus | Max | 比值 |
|------|------|-----|------|
| Latency (p50) TTFT | 0.91s | 1.10s | Plus TTFT 略快 |
| Throughput (p50) | 10.0 tok/s | **47.0 tok/s** | **Max 快 4.7×** |

> 数据来源：Artificial Analysis, Alibaba Cloud Int. endpoint [来源: 用户口述] ⚠️ 待官方验证

Max 生成速度约为 Plus 的 4.7 倍（MoE 架构 + 无视觉 encoder 开销）。考虑价格差（Max 输出 ¥36 vs Plus ¥8），"吞吐量/元" 两者接近（Max 1.3 tok/s/¥ vs Plus 1.25 tok/s/¥）。

#### 选型结论

| 决策条件 | 推荐模型 |
|----------|----------|
| 需要看图/看屏/看视频 | 两者均可；**Plus** 有 GUI Agent benchmark 验证，**Max-0608** 视觉专项能力尚待实测 |
| 需要强推理 + 简单看图 | **Max-0608**（推理更强） |
| GUI 自动化 / 屏幕操作 Agent | **Plus**（ScreenSpot Pro 79.0%） |
| 截图→代码 / 视觉编码 | **Plus**（QwenVision2Code 1,772） |
| 需要从视觉输入提取 JSON | 两者均可（Max-0608 实测 JSON Mode 可用，但官方文档未更新） |
| Deep-Planning / MCP 工具链 / 128K 长程记忆 | **Plus**（benchmark 领先） |
| 极端数学推理（Apex/IMO/HLE） | **Max** |
| 需要极快生成速度（交互体验优先） | **Max**（4.7× throughput） |
| 成本敏感（同等产出） | **Plus**（输出价 1/4.5） |
| 绝大多数生产场景 | **Plus**（默认选择） |

## 接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| API 直接调用 | DashScope API，兼容OpenAI格式 | 快速集成 |
| 平台托管 | 百炼平台，可视化编排 | 企业级应用 |

## 定价（API）

| 模型 | 输入（¥/1M tokens） | 输出（¥/1M tokens） | 缓存输入 |
|------|---------------------|---------------------|----------|
| **Qwen3.7-Max** | ¥12 | ¥36 | ¥1.2 |
| Qwen3.7-Max（5折） | ¥6 | ¥18 | ¥0.6 |
| **Qwen3.7-Plus** | ¥2 | ¥8 | — |
| **Qwen3.6-Flash** | [查看定价](https://help.aliyun.com/zh/model-studio/model-pricing) | — | — |

> Qwen3.7-Max 实际成本需关注输出冗长问题：评估中生成量是中位数的 4×，建议 prompt 中显式约束输出长度。

## 竞品定价对比（参考）

| 模型 | 输入（¥/M tokens） | 输出（¥/M tokens） | 缓存 | 来源 |
|------|-------------------|-------------------|------|------|
| **Qwen3.7-Max** | ¥12 | ¥36 | ¥1.2 | developer.aliyun.com |
| DeepSeek-V4-Pro | ¥3 | ¥6 | ¥0.025 | api-docs.deepseek.com |
| GLM-5.1（智谱） | ¥6（32K以内）/ ¥8 | ¥24 | ~¥3.4（$0.475） | open.bigmodel.cn |
| GPT-5.5 | $5（≈¥36） | $30（≈¥216） | $0.50 | apidog.com (AA) |
| Claude Opus 4.7 | $6.25（≈¥45） | $25（≈¥180） | $0.50 | apidog.com (AA) |

> Qwen3.7-Max 单价高于 DeepSeek-V4-Pro（4×）和 GLM-5.1（2×），但 Agent 场景（Terminal-Bench 2.0 69.7 vs GLM-5.1 63.5）、1M 上下文（vs GLM-5.1 128K）、35h 长时执行是核心差异点。

## 参考资料

- https://artificialanalysis.ai/models/qwen3-6-max （AA独立评测，Intelligence Index #2）
- https://apidog.com/blog/qwen-3-7-vs-gpt-5-5-vs-opus-4-7/ （Qwen3.7-Max vs GPT-5.5 vs Opus 4.7 三方对比，AA Index 57 / #1）
- https://developer.aliyun.com/article/1738425 （百炼 Qwen3.7-Max RMB 定价详解）
- https://www.datalearner.com/ai-models/compare/qwen3-7-max-preview/vs/glm-5-1 （Qwen3.7 vs GLM-5.1 Benchmark 对比）
- https://artificialanalysis.ai/models/comparisons/qwen3-6-plus-vs-qwen3-max-thinking-preview
- https://hub.baai.ac.cn/view/53628 （智源社区评测文章）
- https://qwen.ai/blog?id=qwen3.6 （Qwen官方博客）
- agentic LLM参考: https://artificialanalysis.ai/models?intelligence=coding-index
- https://www.qubrid.com/blog/qwen37-plus-is-now-available-on-qubrid-ai （Qwen3.7-Plus 完整 Benchmark 六模型对比表）
- https://benchlm.ai/best/computer-use （Computer Use AI 全球排名，Plus #4 75.6 分）
- https://www.qbitai.com/2026/06/427730.html （量子位报道，11 小时自主开发 demo）
- https://help.aliyun.com/zh/model-studio/newly-released-models （模型上下架与更新，2026-06-10 qwen3.7-max-2026-06-08 条目）
- https://help.aliyun.com/zh/model-studio/vision-model/ （视觉理解模型列表，含 Max-0608 参数表）
- [通义千问官网](https://tongyi.aliyun.com)
- [百炼平台](https://bailian.console.aliyun.com)
- [Qwen GitHub](https://github.com/QwenLM)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-07-10 | 校验修复：移除 Plus "8折至 2026-07-02" 过期到期日，改为"截止日期以百炼控制台为准" |
| 2026-06-14 | 同步 HTML 选型页变更：系列定位分工更新 Max 不再是纯文本旗舰（0608 快照起支持视觉）；Plus 竞争力要点补充视觉场景首选定位 |
| 2026-06-12 | 合并：inbox 素材 — Qwen3.7-Max-2026-06-08 新增视觉能力（官方日志确认 + 视觉模型页面参数表）；修正多处"Max 仅文本"过时描述；新增快照版本演进记录；更新选型结论表（Max-0608 视觉可用但专项 benchmark 待验证）；JSON Mode 实测可用标注 |
| 2026-06-11 | 合并：inbox 选型分析素材 — 新增「Plus vs Max 场景选型详解」子章节（3 层对比 + benchmark 数据 + 推理速度 + 选型结论表）；更新 Plus Benchmark 详细数据（GUI Agent / Visual Coding / 文档理解 / 纯文本 Agent 四维度） |
| 2026-06-04 | 主推模型表更新：移除已取代的 Qwen3.6-Plus / Qwen3.6-Max-Preview，主推表仅保留百炼在售的 3 个模型（Qwen3.7-Max / Qwen3.7-Plus / Qwen3.6-Flash）；历史模型单独标注 |
| 2026-05-31 | 合并：inbox 素材 — 新增百炼 RMB 定价（¥12/¥36，5折 ¥6/¥18）、竞品定价对比表（DS-V4-Pro/GLM-5.1/GPT-5.5/Opus 4.7）、新用户 100 万 tokens 免费额度 |
| 2026-05-31 | 新增 Qwen3.7-Max（2026.05.19 发布），包含关键基准、AA Intelligence Index 56.6、35h 自主运行、定价、局限；更新模型表、能力/场景/限制/定价；标注 Qwen3.6-Max 被 3.7-Max 取代 |
| 2026-04-24 | 合并 qwen3.6.md 内容，补充 Qwen3.6-Max-Preview 详细信息和对比分析 |
| 2026-04-20 | 按_maas_template重构，对齐模板结构 |
