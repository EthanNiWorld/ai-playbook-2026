# Kimi K 系列模型

> 最后更新: 2026-11-08
> 所属厂商: 月之暗面（Moonshot AI）
> 产品类别: MaaS

<!-- SUMMARY_START -->
**定位**: 开源 Agent 模型系列，聚焦长程编码、端到端知识工作与多 Agent 协作
**当前主推**: Kimi K3.1 Pro（2026-10-24 后训练旗舰，$2/$10，权重已按期开放）/ Kimi K3（旗舰，2.8T / 1M 上下文，权重已开放）/ Kimi K2.7-Code（编码专精）/ Kimi K2.6（长程 Agent）
**适用**: AI 编码助手、Agent 应用、多 Agent 系统、自动化工作流、超长上下文知识工作
**不适用**: 轻量级对话、纯文本生成（性价比不如 Qwen/GPT 系列）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| 🚩 **Kimi K3.1 Pro** | 当前旗舰（K3 后训练版） | 1M | 沿用 K3 架构（2.8T MoE），长程编码/知识工作强化；$2/$10（低于 K3）；思考 low/high/max；权重 2026-11-04 前按期开放（官方/百炼口径 3T 级 open-weight） | 2026-10-24 |
| **Kimi K3** | 旗舰（权重已开放） | 1M | 2.8T MoE（896 专家/激活 16）、KDA 线性注意力、原生多模态、始终 max 思考 | 2026-07-17 |
| **Kimi K2.7-Code** | 编码专精 | 256K | 基于 K2.6 的编码专精模型，推理 token 减少 30%，长程软件工程优化 | 2026-06-12 |
| **Kimi K2.6** | 长程 Agent | 256K | 原生多模态、13 小时长周期编码、Agent Swarm（300 子 Agent），价位低于 K3 | 2026-04-20 |

> 📌 **产品分层**：K3.1 Pro 为当前旗舰（K3 后训练版，定价 $2/$10 低于 K3 的 $3/$15）；K3 为高端旗舰（始终 max 思考、权重已开放、可自部署评估）；K2.7-Code 守 IDE 快速编码循环；K2.6 守低价长程 Agent。K3.1 Pro 发布不取代 K2.7-Code / K2.6，按场景分流。
> 📌 **历史模型**：Kimi K2.5（2026-01-27）仍可调用，但已被 K2.6 取代，不建议新项目选用。Kimi K2（2025-07-11）已于 2026-05-25 正式下线。

## 模型演进

### Kimi K3.1 Pro（2026 年 10 月，当前旗舰）

- **发布**：2026-10-24（官网研究索引口径；10-23 UTC 网页 / Kimi Work / Kimi Code / API 已开放）；官方 API ID `kimi-k3.1-pro`，高速版 `kimi-k3.1-pro-highspeed`
- **与 K3 关系**：K3 后训练版本——主要增加强化学习算力，改进长上下文推理、沙箱、任务调度与环境质量检查；**官方未公布架构变化**，沿用 K3 规格（2.8T 总参 / 104B 激活 MoE；AA 登记同为 2.8T）[来源: kimi.com/en/blog/kimi-k3-1-pro + datalearner 汇总]
  - ⚠️ **参数量双口径**：官方博客与百炼上新页宣传口径为 **"3T-class / 3T-parameter"**（与 K3 当年"3 万亿级"宣传同款），精确值沿用 K3 架构 **2.8T**；对外引用按场景选口径，勿混用
- **上下文 / 输出**：1M（1,048,576）；max_completion_tokens 默认 131,072、最大可设 1,048,576（受总上下文预算限制）
- **多模态**：文本 + 图片 + 视频输入 → 文本输出；3D 成果通过生成并执行 Blender / CAD / 游戏引擎代码完成，非原生 3D 模态
- **思考**：始终开启，推理强度 low / high / max（默认 max）；支持工具调用与结构化输出
- **定价**（官方，datalearner 转述）：标准版 $2 输入 / $10 输出（¥13/¥68）；缓存读取 $0.20（¥1.30）；缓存写入 5 分钟 $2（¥13）/ 1 小时 $4（¥26）；高速版 $4/$20（¥26/¥136），官方称同等智能、速度约 2–3×，缓存读取同价。人民币与美元为两区域实际标价而非汇率换算
- **开放权重**：官方承诺 **2026-11-04 前发布完整权重**，**百炼上新页 2026-11-05 条目已描述为 "3T-parameter open-weight model"**（官方博客口径 "3T-class open-weight"）——按承诺时间窗判定已按期开放；HF 仓库确切发布日与许可证本轮未直查 [⚠️ 待确认]（Kimi K3 License 为上一代参考）；**Artificial Analysis 当前仍标 Proprietary，疑为收录滞后**。需立即自部署的团队可同步评估已开放权重的 K3（2.8T / Modified MIT）
- **评测**：官方与 AA 独立双口径数据（TB 4.0、HLE、GDPval 等）统一收录于下方「Benchmark 对比」节，此处不重复

### Kimi K3（2026 年 7 月，旗舰）

- **架构**：2.8T MoE，896 专家 / 每 token 激活 16（稀疏度 1.8%），Stable LatentMoE 框架 [来源: platform.kimi.com]
- **注意力创新**：KDA（Kimi Delta Attention）混合线性注意力 + Attention Residuals（AttnRes）[来源: platform.kimi.com]
  - KDA：将长上下文历史压缩为紧凑记忆状态，新 token 只关注 Delta 变化；百万 token 场景解码提速 6.3 倍
  - AttnRes：注意力跨层残差连接，训练效率 +25%，额外成本 <2%
  - 整体扩展效率 vs K2 提升约 2.5 倍
- **上下文**：1M（1,048,576 tokens）
- **多模态**：Moonshot 官方托管 API 支持 文本 + 图像 + 视频（视频经 files API 上传，`video_url` + `ms://<file-id>`，官方 Quickstart 有完整示例）；**开源权重（HF checkpoint）官方口径 Modality 仅 Text + Image，不支持视频输入**（GitHub README Model Summary 表格明示；vLLM day-0 多模态预处理亦为 image-only；2026-09-07 代码级验证：HF 仓库 `kimi_k3_processor.py` 仅识别 `image_url`/`image`，非 image 类型直接 raise ValueError，`media_utils.py` 的 `MediaInput=ImageInput` 无视频解码依赖，`encoding_k3.py` 无 video 逻辑）。官方 API 视觉输入仅支持 base64 / `ms://` 文件 ID（不支持公网图片 URL）
- **开源权重视频"残留痕迹"**：`preprocessor_config.json` 保留完整视频参数（`sample_fps=8.0`、`in_patch_limit_video`、`temporal_merge_kernel_size`、`timestamp_mode`，对应内部 `MoonViTMediaProcessorConfig` 完整版）但开源代码不读取；`config.json` vision tower 预留 4 帧时序位置编码（`init_pos_emb_time=4`、`merge_type=sd2_tpool` 时序池化、pos_embed 借鉴 InternVideo）——架构留了口子但官方 processor 未提供视频路径
- **思考模式**：始终开启，`reasoning_effort` 当前仅 `max` 档；temperature=1.0 / top_p=0.95 固定
- **输出**：max_completion_tokens 默认 131,072，最大 1,048,576
- **量化**：MXFP4 权重 + MXFP8 激活（SFT 阶段起量化感知训练）
- **开源**：全球首个 2.8T 级开源模型（官方宣传口径称"3 万亿级别"，精确值为 2.8T），权重 2026-07-27 前发布，Modified MIT
- **部署**：官方建议 64 加速器超级节点，个人/小团队本地不可跑
- **API**：模型 ID `kimi-k3`；`https://api.moonshot.cn/v1`（国内）/ `https://api.moonshot.ai/v1`（国际）
- **定价**：缓存命中 $0.30 / 输入 $3.00 / 输出 $15.00（每 M tokens）；Mooncake 分离式推理架构下编程任务缓存命中率 >90%
- **限制**：始终思考无法关闭（轻量任务成本高）；联网搜索工具更新中，近期不建议生产使用

### Kimi K2.7-Code（2026 年 6 月，编码专精）

- **架构**：开源 MoE，1T 总参 / 32B 激活参数（基于 K2.6 架构）[来源: totalum.app / OpenRouter]
- **上下文**：256K tokens
- **定位**：以编码为中心的智能体模型，专为长程软件工程任务优化 [来源: help.aliyun.com]
- **核心改进**（vs K2.6）：
  - 推理 token 用量减少约 30%（效率显著提升）[来源: MarkTechPost]
  - Kimi Code Bench v2 得分 +21.8% [来源: MarkTechPost / Instagram]
  - SWE-bench Verified 60.4%（开源模型最高）[来源: OpenRouter]
  - 擅长跨多文件重构、功能实现、长会话调试等复杂工作流 [来源: help.aliyun.com]
- **变体**：
  - `kimi/kimi-k2.7-code`（2026-06-15 百炼上线）：**仅支持思考模式**（不支持非思考模式，关闭思考会报错），temperature 固定 1.0
  - `kimi/kimi-k2.7-code-highspeed`（2026-06-18 百炼上线）：功能完全一致，速度提升 5-6 倍，输出约 180 Token/s [来源: help.aliyun.com / platform.kimi.com]
- **开源**：HuggingFace（moonshotai/Kimi-K2.7-Code），open-weight
- **场景差异 vs K2.6**：K2.7-Code 专注编码 Agent，**支持多模态视觉**（图片 + 视频理解，格式支持 png/jpeg/webp/gif/mp4 等）；K2.6 仍为通用旗舰（含视觉 + Agent Swarm）。两者均支持视觉，但 K2.7-Code 仅支持思考模式 [来源: platform.kimi.com]

### Kimi K2.6（2026 年 4 月，长程 Agent）

- **架构**：原生多模态 MoE（延续 K2.5 架构）
- **上下文**：256K tokens
- **核心突破**：
  - **长周期编码**：支持连续编码长达 13 小时，4,000+ 工具调用
  - **Agent Swarm 升级**：从 K2.5 的 100 子 Agent / 1,500 步扩展到 300 子 Agent / 4,000 协调步骤
  - **编码驱动设计（Coding-Driven Design）**：从单提示生成完整前端界面
  - **主动 Agent（Proactive Agents）**：支持 24/7 持续运行的自主 Agent
  - **Claw Groups**（研究预览）：异构多 Agent + 人类协作的新架构
  - **Skills 系统**：将 PDF/幻灯片/文档转化为可复用技能
- **缓存折扣**：命中缓存按输入价格的 16.9% 计费

### Kimi K2.5（2026 年 1 月）

- **架构升级**：原生多模态 MoE（文本 + 视觉）
- **参数**：1T 总参 / 32B 激活（同 K2）
- **视觉编码器**：MoonViT
- **上下文**：256K tokens（K2 的 2 倍）
- **继续预训练**：约 15T 混合视觉与文本 tokens
- **新能力**：
  - Agent Swarm（研究预览）：最多 100 个子 Agent 并发协作
  - 原生图像/视频理解
  - 思考模式（enable_thinking）
- **API 定价**：输入 $0.60/M tokens（缓存命中 $0.10/M），输出 $3.00/M tokens
- **开源**：HuggingFace，Modified MIT License

### Kimi K2（2025 年 7 月）

- **架构**：MoE（Mixture-of-Experts）
- **总参数**：1T（万亿）
- **激活参数**：32B（每 token）
- **层数**：61 层（含 1 层 Dense）
- **专家数**：384 个，每 token 路由至 8 个 + 1 个共享专家
- **注意力**：MLA（Multi-head Latent Attention），Hidden Dim 7168，64 头
- **MoE Hidden Dim**：每专家 2048
- **激活函数**：SwiGLU
- **词表**：160K
- **上下文**：128K tokens
- **训练数据**：15.5T tokens
- **优化器**：Muon（首次在超大规模 MoE 成功应用）
- **变体**：K2-Base（基础模型）、K2-Instruct（指令微调模型）
- **开源**：HuggingFace，Modified MIT License
- **状态**：已于 2026-05-25 下线

## Benchmark 对比

### Kimi K3.1 Pro（2026-10-24 发布）

| Benchmark | Kimi K3.1 Pro | 对比参照 | 来源 |
|-----------|---------------|----------|------|
| Terminal-Bench 4.0（Claude Code; max） | **65.7%** | Claude Opus 5.5 66.4%、GPT-6 Astra 58.2%（官方比较图） | 官方发布材料 |
| HLE Full（w/ tools; max） | **70.0%** | — | 官方发布材料 |
| OSWorld V2.1（max） | 79.6% | — | 官方发布材料 |
| GDPval-AA v2.1（Elo） | **1846**（95% 区间 1820–1872） | AA 自测值与官方图一致 | Artificial Analysis |
| Intelligence Index v4.3.2 / v5.0 | 55.1（#4/215）/ 46（22/76） | — | Artificial Analysis |
| Kimi Hallu Bench Hard（w/ tools） | **8.3%** | K3 为 23.4%（刻意选择题集，非日常错误率） | 官方发布材料 |
| 输出速度（AA 实测） | 约 80.7 tok/s | — | Artificial Analysis |

> 官方另报：SWE-Marathon v1.1 51.7、Kimi Code Bench 3.0 Long-horizon 61.2（K3 为 55.95）、BenchCAD 92.7%/72.8%（带/不带工具）、OfficeQA Pro v2 64.4、Frontier Finance 58.6、Chartography 90.2%、ZeroBench Main 63.0%（pass@5）。均厂商评估口径，不与独立复测混比。

### Kimi K3（2026-07-17 发布）

| Benchmark | Kimi K3 | 对比参照 | 来源 |
|-----------|---------|----------|------|
| Terminal-Bench v2.1（独立复测） | **85.0%**，总榜第 6（前 5 均为 GPT-5.6 变体），**非 OpenAI 模型第 1** | Claude Opus 4.8 (max) 84.6%、Claude Fable 5 84.6%、GPT-5.5 (xhigh) 84.3%；榜首 GPT-5.6 Sol (xhigh) 89.5%；K2.6 为 65.9% | Artificial Analysis |
| Terminal-Bench 2.1（官方口径） | 88.3 | ⚠️ 与独立复测存在口径差，对外引用建议用独立数据 | kimi.com/blog/kimi-k3 |
| GDPval-AA v2（Elo，独立评测） | **1668**，全球第 3 | Claude Fable 5 1750、GPT-5.6 Sol (max) 1743；Claude Sonnet 5 (max) 1607；K2.6 为 1191 | Artificial Analysis |
| Intelligence Index（综合） | 57，第 3 | 与 Opus 4.8 / GPT-5.5 同档，落后 GPT-5.6 一档 | Artificial Analysis |
| Frontend Code Arena（Elo） | **1679，#1** | Claude Fable 5 1631；K2.6 由第 18 名跃升 17 位 | arena.ai |
| FrontierSWE（方案规划型） | 81.2 | Claude Fable 5 86.6 / GPT-5.6 Sol 71.3 | 官方技术博客 |
| DeepSWE（精准执行型） | 67.3 | mini-SWE-agent harness | 官方技术博客 |

> K3 代际跃升最大维度：Terminal-Bench +19.1pt、GDPval +477 Elo（均 vs K2.6）。SWE-bench Verified / LiveCodeBench / Tau2 / AIME 官方称"开源领先"，具体分数待 2026-07-27 技术报告 [⚠️ 待补充]。

### Kimi K2.6 vs 主流模型

| Benchmark | Kimi K2.6 | GPT-5.4 (xhigh) | Claude Opus 4.6 (max) | Gemini 3.1 Pro (high) | Kimi K2.5 |
|-----------|-----------|------------------|----------------------|----------------------|-----------|
| **Agent** |  |  |  |  |  |
| HLE-Full w/ tools | **54.0** | 52.1 | 53.0 | 51.4 | 50.2 |
| BrowseComp (swarm) | **86.3** | — | — | — | 78.4 |
| DeepSearchQA (f1) | **92.5** | 78.6 | 91.3 | 81.9 | 89.0 |
| Toolathlon | 50.0 | **54.6** | 47.2 | 48.8 | 27.8 |
| OSWorld-Verified | 73.1 | **75.0** | 72.7 | — | 63.3 |
| **编码** |  |  |  |  |  |
| Terminal-Bench 2.0 | 66.7 | 65.4 | 65.4 | **68.5** | 50.8 |
| SWE-Bench Pro | **58.6** | 57.7 | 53.4 | 54.2 | 50.7 |
| SWE-Bench Verified | 80.2 | — | 80.8 | **80.6** | 76.8 |
| **推理** |  |  |  |  |  |
| AIME 2026 | 96.4 | **99.2** | 96.7 | 98.3 | 95.8 |
| GPQA-Diamond | 90.5 | 92.8 | 91.3 | **94.3** | 87.6 |
| **视觉** |  |  |  |  |  |
| MathVision w/ python | 93.2 | **96.1** | 84.6 | 95.7 | 85.0 |
| V* w/ python | **96.9** | 98.4 | 86.4 | 96.9 | 86.9 |

> K2.6 在 Agent、编码（尤其 SWE-Bench Pro）和 DeepSearchQA 上达到开源 SOTA，与 GPT-5.4、Claude Opus 4.6、Gemini 3.1 Pro 等闭源旗舰模型处于同一梯队。

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 超长上下文 | K3 支持 1M tokens（1,048,576）；K2.x 为 256K |
| 长周期编码 | 13 小时连续编码，1,000+ 工具调用，跨语言（Rust/Go/Zig/Python） |
| Agent Swarm | 300 子 Agent 并发协作，4,000 协调步骤 |
| 原生多模态 | 文本 + 图像 + 视频理解（MoonViT）；⚠️ K3 开源权重官方口径仅 Text + Image，视频输入仅官方托管 API 可用 |
| 思考模式 | K2.6 可开关（enable_thinking）；**K2.7-Code 仅支持思考模式**（不支持关闭，temperature 固定 1.0） |
| Tool Calling | 原生工具调用，支持 MCP 协议 |
| 编码驱动设计 | 从提示生成完整前端 + 全栈应用 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 上下文 | K2.x 为 256K tokens | K3 已达 1M；K2.x 不如 Qwen 系列的 1M 上下文 |
| K3 思考模式 | 无法关闭 | 始终 max 档，轻量任务成本高 |
| K3 联网搜索 | 更新中 | 近期不建议用于生产流程 |
| 推理/数学 | 略弱于 GPT-5.4 | AIME 96.4 vs 99.2，HMMT 92.7 vs 97.7 |
| 视觉理解 | 略弱于 Gemini 3.1 Pro | MMMU-Pro 79.4 vs 83.0 |

## 推理部署

Kimi K2 系列模型权重开源（block-fp8 格式），推荐推理引擎：

- **vLLM** — 主流开源推理引擎
- **SGLang** — 高效推理框架
- **KTransformers** — MoE 优化推理
- **TensorRT-LLM** — NVIDIA 推理加速

> 模型文件大小约 595GB，需要多卡 GPU 集群部署。

## 关键技术论文

| 论文 | 时间 | 核心贡献 |
|------|------|----------|
| Kimi K2: Open Agentic Intelligence | 2025-07 | MoE 1T 架构、Muon 优化器、Agent 能力优化 |
| Agent Swarm | 2026-02 | 多 Agent 并发协作架构 |
| WorldVQA | 2026-02 | 视觉质量评估 |

## Changelog

| 日期 | 变更内容 |
|------|---------|
| 2026-11-08 | 校验修复（knowledge-verification-2026-11-08）：K3.1 Pro 权重状态由「承诺 11-04 前发布、尚未发布」改为已按期开放（百炼上新页 11-05 条目描述为 open-weight）；参数量补双口径（官方 3T 级 vs 精确 2.8T）；AA 仍标 Proprietary 注记为收录滞后，HF 发布日/许可证标待确认 |
| 2026-11-03 | 校验修复+补研（knowledge-verification-2026-11-03）：新增 Kimi K3.1 Pro 并切为当前旗舰（2026-10-24，K3 后训练版；定价 $2/$10；官方/AA 双口径评测见正文；权重承诺 11-04 前发布、截至 11-03 未发布，AA 暂标闭源）；解除 109 天未更新状态 |
| 2026-09-07 | 调研补充：区分 K3 官方托管 API 与开源权重的模态边界——开源权重（HF checkpoint）官方口径 Modality 仅 Text + Image、不支持视频输入（GitHub README Model Summary 表格 + vLLM day-0 "multimodal preprocessing (image-only)" + HF 仓库 py 源码级验证三重佐证），视频输入仅官方 API 可用（files API 上传 + `video_url` `ms://` 示例）；preprocessor_config.json 残留视频参数（sample_fps=8.0 等）+ vision tower 预留 4 帧时序 pos emb（init_pos_emb_time=4/sd2_tpool）确认架构留有视频口子但 processor 未开放；与百炼实测 k3 视频 400 结论一致 |
| 2026-09-01 | 路径修复：`api-sample` 目录已重命名为 `maas-solution-and-api-sample`，更新实测脚本引用路径 |
| 2026-08-24 | 实测补全：K3 百炼 MaaS 端点多模态实测（北京 workspace×2 + 新加坡节点三端点交叉验证）——k3 图片 base64/URL 均可用、视频不支持（400 报错）；同端点 kimi-k2.6 / kimi-k2.7-code 视频正常，确认系 k3 专属限制；补全 K3/K2.6 百炼接入信息；新增测试脚本 test_kimi_k3_multimodal.py |
| 2026-07-17 | 合并：inbox K3 调研素材 — 新增 Kimi K3 章节（2.8T/1M/KDA/AttnRes），主推更新为 K3，新增 K3 Benchmark 表（AA 独立评测与官方口径分列），K2.6 定位调整为长程 Agent，K2.7-Code 调整为编码专精 |
| 2026-06-29 | 修正：K2.7-Code 支持多模态视觉（图片+视频），明确仅支持思考模式（不支持关闭）；模型演进调整为时间倒序（K2.7-Code → K2.6 → K2.5 → K2）[来源: platform.kimi.com] |
| 2026-06-22 | 合并：百炼上新架与外部报道 — 新增 Kimi K2.7-Code 编码旗舰（2026-06-12 发布，百炼 06-15 上架），含 Benchmark、架构、Highspeed 变体 |
| 2026-06-07 | 新建：覆盖 K2/K2.5/K2.6 全系列模型知识 |

## 参考资料

- [Kimi K3.1 Pro 官方发布博客](https://www.kimi.com/en/blog/kimi-k3-1-pro)（2026-10-24，规格/官方评测/权重承诺）
- [DataLearner — Kimi K3.1 Pro 价格与评测汇总](https://www.datalearner.com/ai-models/pretrained-models/kimi-k3-1)（API 定价/AA 独立评测，2026-11-03 核实）
- [Kimi K3 Quickstart（官方文档）](https://platform.kimi.com/docs/guide/kimi-k3-quickstart)
- [Kimi K3 技术博客](https://www.kimi.com/blog/kimi-k3)
- [Kimi K2.6 技术博客](https://www.kimi.com/blog/kimi-k2-6)
- [GitHub: moonshotai/kimi-k2](https://github.com/moonshotai/kimi-k2)
- [Kimi API 平台模型列表](https://platform.kimi.ai/docs/models)
- [Kimi K2.7 Code 快速开始（官方文档）](https://platform.kimi.com/docs/guide/kimi-k2-7-code-quickstart)
- [阿里云百炼 Kimi 文档](https://help.aliyun.com/zh/model-studio/kimi-api-by-moonshot-ai)
- [ModelScope: Kimi-K2.6](https://www.modelscope.cn/models/moonshotai/Kimi-K2.6)
