# 通义千问 (Qwen)

> 最后更新: 2026-11-10
> 所属厂商: 阿里云
> 产品类别: MaaS

**定位**: 阿里云自研大语言模型系列，覆盖文本/代码/多模态，开源+商业双轨并行
**当前主推**: Qwen3.8-Max（旗舰，文本+视觉）/ Qwen3.8-27B（开源 Dense 视觉语言，GUI/视觉场景）/ Qwen3.8-Flash（新架构轻量快速，2026-08-26）
**适用**: 企业级AI应用开发、智能对话、代码生成、多模态理解、长时间自主 Agent

## 当前主推模型

> 数据来源：[百炼模型广场](https://help.aliyun.com/zh/model-studio/models)，2026-07-25 核实；Qwen3.8-Flash 行据 qwen.ai 官方博客 + 千问AI平台模型页（2026-08-26/09-02），百炼模型广场在售列表待下次核实

| 模型 | 定位 | 上下文 | 特点 |
|------|------|--------|------|
| **Qwen3.8-Max** | 旗舰（文本+视觉） | **1M tokens** | 2.4T MoE 万亿参数；支持文本+图像输入（已实测）；思考与非思考模式；取代 Qwen3.7-Max；最新快照 qwen3.8-max-0902（2026-09-02 上线，见下方小节） |
| **Qwen3.8-27B** | 开源 Dense 视觉语言（GUI/视觉场景） | **262K tokens** | 27B Dense 原生视觉语言模型（2026-08-17 上线）；编程+办公端到端；百炼 CN 专属/国际站 BJ/SG 三端点可用，**混合思考可关闭**（实测）；销售指南 0930 起以本款替代 Qwen3.7-Plus |
| **Qwen3.8-Flash** | 轻量快速（新架构） | **1M tokens** | 下一代（Next）架构首发载体：125B MoE / 6B 激活 + 51B N-gram Embedding，原生图/视频输入，OpenAI + Anthropic 双协议兼容，训练成本仅上代 Plus 的 1/9；取代 Qwen3.7-Flash [来源: qwen.ai 官方博客 + qianwenai.com，2026-08-26] |

> 📌 **历史/存量模型**：**Qwen3.7-Plus 已退出主推（2026-11-05 起），API 仍可调用**——GUI/视觉场景改选 Qwen3.8-27B，通用多模态改选 Qwen3.8-Max；Qwen3.7-Max（被 3.8-Max 取代）、Qwen3.7-Flash（被 3.8-Flash 取代）同样仅建议存量项目使用。

### Qwen3.8-Max

- **模型**：Qwen3.8-Max
- **公司**：阿里云
- **时间**：2026 年 7 月 19 日（预览版上线）；正式版已上线百炼（2026-08-03 核实定价页已收录）
- **尺寸**：总参数 **2.4T（2.4 万亿）**，MoE 架构；激活参数未公开
- **上下文**：**1M tokens**，最大输出 **128K tokens** [来源: 百炼控制台模型页，2026-08-03 用户截图]
- **输入模态**：文本 + 图像（2026-08-03 API 实测确认，图片描述准确）[来源: alibaba-ai-hub/maas/maas-solution-and-api-sample/test_qwen38_max.py]；视频支持待确认
- **模式**：思考与非思考模式均支持
- **定价**：见下方「定价（API）」章节。
- **限流**：RPM 15,000 / TPM 2,000,000（200 万）[来源: 百炼控制台模型页截图]
- **开源**：Qwen3.8 系列开源版 **qwen3.8-2.4t-a95b** 已于 2026-08-12 上线百炼国际站（2.4T 总参 / 激活 95B，**原生 262K 上下文、可扩展约 1M**；GPQA Diamond 92.6 / PaperBench 93.0 / OSWorld 86.1，CodeArena 全球 #4）[来源: help.aliyun.com 上新页，2026-08-14 核实]；架构详见下方「Qwen3.8-2.4T-A95B 开源版」小节；qwen3.8-max 本体是否开放权重官方未明确
- **场景**：代码工程（全栈开发、代码重构、漏洞批量修复）、专业办公（Office 工作流、文档免转换直读、数据分析）、复杂推理、长程 Agent、多语言创作
- **特点**：Qwen 首款万亿级参数模型；官方自评"仅次于 Fable 5"——⚠️ 该表述仅官方自评，无第三方背书。**AA 现已收录**：Artificial Analysis Intelligence Index **v5 = 45**（2026-11-08 查询），低于 Gemini 4 Carbon 60 / Claude Opus 5.5 59 / GPT-6 Astra 57 / GPT-6.1 Sol 55 / Kimi K3.1 Pro 46；AA 指数随新模型发布重校准，跨时间引用需注明口径

**API 实测记录**（2026-08-03，新加坡节点，标准后付费 API Key）[来源: alibaba-ai-hub/maas/maas-solution-and-api-sample/test_qwen38_max.py]：
- 纯文本与图像输入均调用成功，图片描述准确（VL 能力确认）
- 知识截止日期、技术报告均未公开
- 视频输入、GUI Agent 等视觉专项能力待实测

**Benchmark（Qwen 官方博客，vs 同期旗舰）** [来源: qwen.ai/blog?id=qwen3.8，2026-08-17 合并]：

| 基准 | Qwen3.8-Max | Opus 4.8 | Fable 5 | GPT 5.6 Sol (max) | Qwen3.7-Max |
|------|------------|----------|---------|-------------------|-------------|
| Terminal-Bench 2.1 | **86.6** | 84.6 | 84.6 | 88.8 | 74.5 |
| PaperBench | **93.0** | 80.3 | — | 90.5 | — |
| SWE-bench Pro | 67.7 | — | **80.0** | 64.6 | 60.6 |
| DeepSWE 1.1 | 56.6 | — | **70.0** | 73.0 | 21.6 |
| FrontierSWE | 73.5 | 70.0 | **88.8** | — | 40.7 |
| GPQA Diamond | 92.6 | — | — | — | 92.4 |
| CodeArena | 全球 #4 | — | — | — | — |

**相对前代（Qwen3.7-Max）的差异化**：
- 参数量首次突破万亿（2.4T）
- 系列开源版已兑现：qwen3.8-2.4t-a95b（2026-08-12 上线；vs 3.7-Max 闭源 API only）
- 定位从"长时自主 Agent + 数学竞赛推理"转向"代码工程 + 专业办公"，对应 Qoder + QoderWork 两条产品线的高 ARPU 场景

### Qwen3.8-Max-0902 快照（2026-09-02 上线）

- **模型**：qwen3.8-max-0902（别名 qwen3.8-max-2026-09-02），Qwen3.8-Max 的最新能力快照
- **上线**：2026-09-02，国际站/全球节点均已上线 [来源: help.aliyun.com 上新页，2026-09-17 核实]
- **定价**：与稳定版一致，统一见下方「定价（API）」章节。
- **能力三维升级**（官方口径）：
  1. **编码深度突破**：工程级项目理解与长程自主开发能力增强
  2. **协作智能体**：多工具调度与协作能力增强
  3. **视觉理解精进**：图表推理、文档解析能力提升
- **快照演进**：稳定版别名 `qwen3.8-max` → `qwen3.8-max-0902`（2026-09-02）

### Qwen3.8-2.4T-A95B 开源版（2026-08-12 上线）

- **模型**：Qwen3.8-2.4T-A95B（HuggingFace: Qwen/Qwen3.8-2.4T-A95B）
- **定位**：Qwen3.8-Max 的开源权重版本，**Qwen 首款 Max 级开源模型**
- **上线**：2026-08-12，百炼国际站 [来源: help.aliyun.com 上新页]
- **许可证**：HuggingFace "other" 许可（非标准 Apache/MIT，商用前需确认）[来源: huggingface.co/Qwen/Qwen3.8-2.4T-A95B]
- **架构细节** [来源: mindstudio.ai 技术解析 + NVIDIA NeMo 模型页]：
  - 总参数 **2.4T**，激活参数 **95B** / token；92 层，hidden dim 8192
  - MoE：**512 experts**，每 token 10 routed + 1 shared，expert intermediate dim 2048
  - **混合注意力**（交替模式）：23 组 × (3× Gated DeltaNet + MoE → 1× Gated Attention + MoE)
    - Gated DeltaNet 层：128 linear attention heads（values）+ 16 heads（Q/K），head dim 128
    - Gated Attention 层：64 Q heads + 4 KV heads，head dim 256，RoPE dim 64
  - MTP（multi-token prediction）多步训练，提升生成质量
  - 上下文：**原生 262,144 tokens，可扩展至约 1,010,000 tokens**（1M 为 API 托管版默认配置，开源版需自行扩展）
  - 权重格式：safetensors，213 个分片；兼容 vLLM / SGLang / TokenSpeed 自部署
  - 特性参数：`reasoning_effort`（可调推理深度）、`preserve_thinking`（跨轮保留推理上下文）
- **思考模式（百炼 API 实测，2026-08-27）**：百炼端点上 `enable_thinking` **仅接受 True**——传 False 时专属端点与公共端点均报错 `The value of the enable_thinking parameter is restricted to True.`；`/no_think` 提示词软开关亦无效 → **百炼托管的 qwen3.8-2.4t-a95b 实际按仅思考模式运行，无法关闭思考**（与官方"深度思考模型用法"文档的"混合思考模式"分类不符，以 API 实测为准；自部署 vLLM 版不受此限）。曲线方案：`thinking_budget` 有效，设极小值可将思考压至极短再输出回复（实测 budget=1 时思考仅 2 字符），实测脚本 `maas-solution-and-api-sample/test_qwen38_a95b_thinking_switch.py`
- **思考长度控制：`thinking_budget` vs `reasoning_effort`（实测，2026-08-27，10 用例套件）**：两参数单独使用在 a95b 上均有效，定位不同——
  - `thinking_budget`（int）：思考 Token **硬上限**，粒度精确（实测 budget=1→思考均值 3 字符，近似关闭；1024→均值 100 字符，较基线 -43%）；官方 API 参考明确适用于 Qwen3.8 系列，推荐首选
  - `reasoning_effort`（string 档位）：推理**力度软引导**，低→中→高呈单调梯度（三轮实测：low 均值 106 / medium 134 / high 306 字符，基线 175；low 较基线 -40% 且方差极小）；注意官方 API 参考的 reasoning_effort 支持列表仅明文覆盖 qwen3.8-max/flash，未列开源版 a95b（实测有效但无官方背书）
  - **两参数互斥（实测同样适用 a95b）**：同时设置报错 `'reasoning_effort' and 'thinking_budget' cannot be set simultaneously`；`reasoning_effort=none` 也被拒（报错同 enable_thinking=False，印证 none→enable_thinking=False 映射生效）
  - **闭源版互转规则（官方文档，max/flash）**：reasoning_effort 未设时 budget 自动映射档位（0~4096→low，4097~16384→medium，16385~262144→xhigh），档位未设时自动映射 budget（low→4096，medium→16384，xhigh→262144）；均未设时默认 budget=131072 / effort=xhigh [来源: help.aliyun.com/zh/model-studio/qwen-api-via-dashscope]
  - 完整实测数据与脚本：`maas-solution-and-api-sample/test_qwen38_a95b_thinking_switch.py` + `maas-solution-and-api-sample/test_qwen38_a95b_thinking_switch_results_20260827.md`

**开源版 vs API 托管版（Qwen3.8-Max）差异**：

| 维度 | 开源版 (A95B) | API 版 (Max) |
|------|--------------|-------------|
| 上下文 | 原生 262K，可扩展 ~1M | 默认 1M |
| 最大输出 | 未公开 | 128K |
| 视觉输入 | ❌ 无 | ✅ 文本+图像 |
| 非思考模式 | ✅ 仅自部署可关；百炼端点强制思考（实测） | ✅ |
| 内置工具 | ❌ | ✅ |
| 部署方式 | vLLM / SGLang 自部署 | 百炼 API |

> **架构设计解读**（素材分析）：① Gated DeltaNet 线性注意力在长序列上 FLOPs 增长更慢，是 262K 原生上下文的效率基础；每隔 3 层插入一层标准注意力保留全局信息捕捉能力。② 512 experts 超高稀疏度——每 token 仅激活 11/512 ≈ 2.1% experts，2.4T 参数的推理成本接近 95B dense 模型；代价是全量权重须加载到 VRAM（213 个分片），自部署门槛极高。③ 首次 Max 级开源被视为生态策略转向：开源建壁垒，API 版以视觉/内置工具/1M 上下文作增值差异。

### Qwen3.8-27B 开源 Dense 版（2026-08-17 上线）

- **模型**：Qwen3.8-27B（27B Dense 原生视觉语言模型）
- **上线**：2026-08-17，百炼国际站 [来源: help.aliyun.com 上新页]
- **定位**：相较 3.6-27B 重点提升文本和视觉模态下的编程和办公场景能力，可靠地端到端完成复杂任务
- **可用端点（实测，2026-08-27）**：CN 专属端点 / 国际站 BJ / 国际站 SG 三端点均可调用
- **思考模式（百炼 API 实测，2026-08-27，10 用例三端点交叉验证）**：**真正的混合思考模式，可以关闭思考**——
  - `enable_thinking=False` ✅ 完全生效（思考 0 字符，模型直接回复），三端点行为一致；与官方文档分类一致（vs a95b 与文档不符）
  - 默认不传参数时开启思考（实测均值 357 字符）
  - `reasoning_effort=none` ✅ 等价关闭（映射生效且被允许）
  - `thinking_budget`（budget=1024→思考均值 148 字符）与 `reasoning_effort`（low→均值 121 字符）均有效；两参数互斥规则同样适用（同时设置报错）
  - `/no_think` 软开关未实现完全关闭（思考仍输出，与去异常后对照组相当），有硬开关后无实用价值
  - 完整实测数据与脚本：`maas-solution-and-api-sample/test_qwen38_27b_thinking_switch.py` + `maas-solution-and-api-sample/test_qwen38_27b_thinking_switch_results_20260827.md`

### Qwen3.8-Flash / Qwen3.8-Flash-Next（2026-08-26 发布）

- **模型**：Qwen3.8-Flash（API 生产版，`qwen3.8-flash`）/ Qwen3.8-Flash-Next（开源架构预览权重）——官方区分两个交付形态：Flash-Next 为架构预览 + 开放权重，Flash 为基于 Flash-Next 的生产 API（默认 1M 上下文 + 内置工具）
- **公司**：阿里云
- **时间**：2026 年 8 月 26 日晚发布并同步开源 [来源: qwen.ai/blog?id=qwen3.8-flash-next（全文经官方知乎镜像核验）+ 新京报]
- **定位**：轻量快速档主力，取代 Qwen3.7-Flash；多模态 MoE，**下一代（Next）新架构首发载体**——官方原文"Next 新架构将是全新一代 Qwen4 系列模型的雏形……先让社区对其进行检验"（延续 Qwen3-Next → 3.5/3.8 的打法）；首发上线"千问办公"
- **尺寸**：主模型 **125B MoE，每 token 激活 6B**（激活占比约 4.8%）；另配 **51B N-gram Embedding**（确定性查表、不进每 token 矩阵乘预算、可卸载 Host Memory 异步 prefetch 与计算重叠，仅前部一层）；MTP 多步训练提升 speculative decoding 接受率（MTP 参数量官方博客未公布 [⚠️ 待补充]）
- **上下文**：原生 262,144 tokens，YaRN 扩展至 1M；API 版默认 1M（输入 991K / 思考模式 983K、输出 131K、最大思维链 262K）[来源: qianwenai.com/models/qwen3.8-flash]
- **模态**：输入文本/图像/视频，输出文本
- **架构四件套** [来源: 官方博客]：
  1. **GDN + QSA 混合注意力**：每 4 层 3 层 Gated DeltaNet（历史压缩进固定大小循环状态），1 层全局注意力用 Qwen Sparse Attention（轻量 indexer 先聚合 micro-block 再按块筛选，逐层独立压缩，契合混合架构）；QSA kernel 1M 上下文 prefill 最高 7.6× / decode 4.9× 加速；**90% prefix cache 命中场景 1M prefill 吞吐 = Qwen3.7-Plus 的 8.6×**（官方自报，对应 agentic 高缓存复用流量形状）
  2. **Gated Residual**：残差流扩为 4 分支 + 逐元素动态门控（Hyper-Connection + GatedNorm 融合，省略 branch mixing），残差状态支持 FP8 存储
  3. **N-gram Embedding**：受 Gemma 3n PLE / DeepSeek Engram 启发，以查表方式低成本扩展模型容量
  4. **Muon 优化器**：2D 线性映射参数用 Muon（融合矩阵先拆分再正交化），Embedding/Router/GR 低秩用 AdamW；重拟合 Scaling Law；取消 batch warmup（实验证明不必要，省 18.8% optimizer steps）
- **训练成本**：约为 Qwen3.7-Plus 的 **1/9**（≈ -89%，官方原文"训练开销仅约为前者的 1/9"）[来源: 官方博客]
- **Benchmark（官方口径，媒体转述，未经独立复测）**：SWE-bench Pro 62.5（Opus 4.6 Max 53.4，+9.1；DeepSeek-V4-Flash 56.0）、SWE-bench Multilingual 81.0、DeepSWE 58.7、CoWorkBench 73.9（Opus 4.6 68.2）、JobBench 超 Opus 4.6 近 20 分、RealWorldQA 88.5、LVBench 76.6、OSWorld 2.0 binary 19.4 / partial 52.3、Vision2Web 64.0、ERQA 72.3 [来源: 电子工程专辑/腾讯新闻/亿邦动力转引官方模型卡与技术报告]；Base 模型对比 3.8-27B-Base / 3.7-Plus-Base 14 项 benchmark 8 项最优 [来源: 官方博客]
- **接口与平台**：OpenAI + Anthropic 双协议兼容（官方页明示可接入 Claude Code、Codex）；支持思考模式（enable_thinking）、前缀补全（Partial Mode）、结构化输出、微调；内置工具 code_interpreter / web_search / web_extractor / i2i_search / t2i_search（Responses API）；TPM 5M [来源: qianwenai.com]
- **开源**：Qwen3.8-Flash-Next 权重上架 Hugging Face / ModelScope，许可证 **Qwen Community License 1.0**（非 Apache；商用免费，100M MAU / $20M 营收门槛需另行授权）[来源: HF LICENSE]
- **生态**：HF 趋势榜发布当日登顶；FlagOS 首日适配 8 款 AI 芯片（新增 8 个高性能融合算子）；NVIDIA 官方博客发布 GB300 NVL72 agentic coding 实验（标题口径 "176B" = 125B 主模型 + 51B N-gram Embedding 总足迹，非激活口径）；消费级 4090 可跑（依赖卸载）；官方部署 recipe：transformers serve / vLLM / SGLang / TokenSpeed（4 路张量并行、262K）
- **边界与注意**：① "超越 Opus 4.6" 为 SWE-bench Pro 等 agent 编码分项，非全面领先（新京报同文亦有"性能与 Qwen3.7-Plus 接近"表述）；② OSWorld 2.0 binary 仅 19.4，GUI 执行类场景勿过度承诺；③ "6B 激活"≠部署小——125B 权重 + 51B n-gram 表 + 视觉组件均占内存，全精度 agentic 实验用 GB300 NVL72 整柜；④ 开源权重为架构预览，Qwen4 正式版结构可能微调
- **定价**：见下方「定价（API）」章节

### Qwen3.7 系列（历史/存量，已退出主推）

> API 仍可调用，仅供存量项目核对；定价不再展开，实际账单以百炼控制台和官方定价页为准。新项目迁移路径：**旗舰/通用多模态 → Qwen3.8-Max；GUI/视觉 → Qwen3.8-27B；低成本快速 → Qwen3.8-Flash**。

| 模型 | 原定位与关键规格 | 当前状态 |
|------|------------------|----------|
| **Qwen3.7-Max** | 上代旗舰；1M 上下文、最大输出 64K；面向长时 Agent、Agentic Coding 与数学推理 | 已由 Qwen3.8-Max 取代；关键对照数据保留在上方 Benchmark 表 |
| **Qwen3.7-Plus** | 多模态智能体；1M 上下文，支持文本、图像、视频与屏幕截图；面向 GUI/CLI 和视觉编码 | 已退出主推；GUI/视觉改选 Qwen3.8-27B，通用多模态改选 Qwen3.8-Max |
| **Qwen3.7-Flash** | 原生视觉语言快速档；面向 IPC、审校与大批量打标 | 已由 Qwen3.8-Flash 取代 |

- **Qwen3.7-Plus 历史专项数据**（第三方口径，仅供存量对照）：ScreenSpot Pro 79.0%、AndroidWorld 81.0%、OSWorld-Verified 73.3%；OmniDocBench 1.5 91.4%、OCR-Bench-V2 70.7%；Deep-Planning 62.3%、MCP-Mark 58.7%。stable 版未独立复测。
- **Qwen3.7-Max 其他历史记录**：35 小时自主编码（1,158 次工具调用）；HLE 41.4、HMMT 2026 97.1%、IMOAnswerBench 90.0%。TB / SWE / GPQA 对照统一见上方 Qwen3.8-Max Benchmark 表。

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **深度推理（Max）** | Qwen3.8-Max 支持思考与非思考模式；AA 与定量 Benchmark 统一见模型小节 |
| **Agentic Coding** | 面向工程级项目理解、长程自主开发与多工具协作；定量数据见 Qwen3.8-Max Benchmark |
| **超长上下文** | Qwen3.8-Max / Flash API 默认 1M tokens，适合大型代码仓库和长文档 |
| **多模态智能体** | Qwen3.8-27B 承接 GUI/视觉场景，Qwen3.8-Max 承接通用多模态；Qwen3.8-Flash 支持文本、图像与视频输入 |
| **数学与复杂推理** | 当前主推 Qwen3.8-Max；上代竞赛数学纪录收敛至 Qwen3.7 历史小节 |
| **多语言** | 覆盖 55 种语言，支持多语言创作与翻译 |
| **开源生态** | Qwen3.8-2.4T-A95B、Qwen3.8-27B 与 Qwen3.8-Flash-Next 覆盖旗舰、Dense 视觉与轻量架构预览 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| Qwen3.8-Max 视频输入 | 待确认 | 文本与图像输入已实测，不应承诺视频能力 |
| qwen3.8-2.4t-a95b 视觉输入 | 不支持 | 开源版与 API 版 Qwen3.8-Max 的模态能力不同 |
| qwen3.8-2.4t-a95b 百炼思考模式 | 仅思考 | 百炼端点不可关闭思考；自部署不受此限 |
| 并发限制 | 按账户与模型 | 以百炼控制台限额为准 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 长程 Agent / 复杂推理 / 极端数学 / 重度编码 | **3.8-Max** | 2.4T 旗舰，TB 2.1 86.6、SWE-Pro 67.7、PaperBench 93.0（3.7-Max 已被取代） |
| GUI/视觉 Agent / 视觉编码 / 编程办公性价比 | **3.8-27B** | 27B Dense 原生视觉语言，可关思考（实测），$0.5/$3；销售指南 0930 起以此替代 3.7-Plus |
| IPC / 审校 / 大批量打标等成本敏感场景 | **3.8-Flash** | 在线低延迟低成本，2026-08-26 新架构发布（取代 3.7-Flash） |
| 高并发轻量调用 | **3.8-Flash** | 低延迟低成本，TPM 5M，缓存命中价仅输入价 12.5% |

## 接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| API 直接调用 | DashScope API，兼容OpenAI格式 | 快速集成 |
| 平台托管 | 百炼平台，可视化编排 | 企业级应用 |

## 定价（API）

> 定价标准：阿里云国际站新加坡节点 USD 列表价，2026-09-17 核实；仅列当前 Qwen3.8 代模型。北京价格与国内计费项仅作参考，实际折扣与账单以控制台为准。

| 模型 | 输入（$/1M tokens） | 输出（$/1M tokens） | 缓存与其他说明 |
|------|---------------------|---------------------|----------------|
| **Qwen3.8-Max**（含 `qwen3.8-max-0902` 快照） | $2 | $6 | 缓存命中 $0.25；稳定版与 0902 快照同价 |
| **qwen3.8-2.4t-a95b**（开源版） | $2 | $6 | 支持缓存折扣（单价未公开）；北京 $1.65/$4.951 |
| **qwen3.8-27b**（开源 Dense 版） | $0.5 | $3 | 支持缓存折扣（单价未公开）；北京 $0.424/$1.696 |
| **Qwen3.8-Flash** | $0.15 | $0.47 | 国内参考：¥0.8/¥2.7、缓存命中 ¥0.1、显式缓存创建 ¥1.25、Batch ¥0.4/¥1.35 [来源: alibabacloud.com 新加坡定价页 + qianwenai.com，2026-09-02] |

## 竞品定价对比（参考）

| 模型 | 输入（每 1M tokens） | 输出（每 1M tokens） | 缓存 | 来源 |
|------|----------------------|----------------------|------|------|
| **Qwen3.8-Max**（新加坡） | $2 | $6 | $0.25 | alibabacloud.com |
| DeepSeek-V4-Pro（非峰） | $0.66（≈¥4.8） | $1.98（≈¥14.4） | $0.022 | api-docs.deepseek.com（2026-08-16 起峰谷定价：峰时×2，详见 [deepseek-v-series.md](../../knowledge/deepseek/deepseek-v-series.md)） |
| GLM-5.1（智谱） | ¥6（32K以内）/ ¥8 | ¥24 | ~¥3.4（$0.475） | open.bigmodel.cn |
| GPT-5.5 | $5（≈¥36） | $30（≈¥216） | $0.50 | apidog.com (AA) |
| Claude Opus 4.7 | $6.25（≈¥45） | $25（≈¥180） | $0.50 | apidog.com (AA) |

> Qwen3.8-Max 单价高于 DeepSeek-V4-Pro 与 GLM-5.1，核心差异点为 Terminal-Bench 2.1 86.6（GLM-5.1 58.7）、1M 上下文（GLM-5.1 128K）以及代码工程和专业办公能力。跨厂商比较仍需统一上下文、缓存、峰谷与汇率口径。

## 参考资料

- [Qwen3.8 官方博客](https://qwen.ai/blog?id=qwen3.8)
- [Qwen3.8-Flash-Next 官方博客](https://qwen.ai/blog?id=qwen3.8-flash-next)
- [阿里云国际站模型定价](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- [百炼模型定价](https://help.aliyun.com/zh/model-studio/model-pricing)
- [百炼模型上下架与更新](https://help.aliyun.com/zh/model-studio/newly-released-models)
- [Qwen3.7-Plus 官方博客](https://qwen.ai/blog?id=qwen3.7-plus)（历史模型）
- [Qwen3.7-Plus 第三方 Benchmark 汇总](https://www.qubrid.com/blog/qwen37-plus-is-now-available-on-qubrid-ai)（历史模型）
- [Computer Use AI 全球排名](https://benchlm.ai/best/computer-use)
- [Agentic LLM 参考](https://artificialanalysis.ai/models?intelligence=coding-index)
- [通义千问官网](https://tongyi.aliyun.com)
- [百炼平台](https://bailian.console.aliyun.com)
- [Qwen GitHub](https://github.com/QwenLM)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-11-10 | 定价与历史内容精简：API 定价仅保留 Qwen3.8 代，竞品对照改用 Qwen3.8-Max；合并 Qwen3.7 系列为历史存量小节，删除重复的 Plus vs Max 选型详解，保留迁移路径与关键历史数据 |
| 2026-11-08 | 校验修复（knowledge-verification-2026-11-08）：解除 Qwen3.8-Max「AA 尚未复测」过期表述——AA 已收录 v5 = 45（低于 Carbon/Opus 5.5/Astra/GPT-6.1 Sol/K3.1 Pro），官方「仅次于 Fable 5」自评加座次对照与口径提醒 |
| 2026-11-05 | 主推口径修正（用户明确）：**Qwen3.7-Plus 退出主推**（3.8 代无 Plus 继任者，官方销售指南 0930 起已以 Qwen3.8-27B 替代）；主推表置换为 Qwen3.8-Max / Qwen3.8-27B / Qwen3.8-Flash，Plus 小节改「存量在售，已退出主推」，系列定位/核心能力/适用场景/选型一句话同步改写；定价与 benchmark 数据保留供存量项目核对 |
| 2026-09-17 | 校验修复（knowledge-verification-2026-09-17）+ 合并：新增「Qwen3.8-Max-0902 快照」小节（2026-09-02 上线国际站/全球，编码深度/协作智能体/视觉理解三维升级，$2/$6 同稳定版）+ 主推表/定价表同步；Qwen3.7-Flash 国际站 USD 定价公布——三档阶梯 $0.030/$0.130（≤32K）、$0.100/$0.400（≤256K）、$0.200/$0.800（≤1M）+ Batch 5 折，解除"未公布"口径；a95b/27b 缓存列改"支持缓存折扣（单价未公开）"并补北京价 $1.65/$4.951、$0.424/$1.696；删除 3.8-Flash 行"免费额度 1M tokens"营销残留；修复 deepseek-v-series.md 断链（../../../ → ../../）；Changelog 主表最早 2 条（2026-08-03）移入折叠区 |
| 2026-09-02 | 压缩历史模型内容：Qwen3.7-Max 小节精简为要点式（关键基准/35h 标志事件/快照演进保留关键值，定价细节收敛至定价表，详细对照已由 Qwen3.8-Max Benchmark 表 3.7-Max 列承载）；「Plus vs Max 场景选型详解」压缩为「Plus vs Max 场景选型（3.7 代结论）」（Plus 视觉专项 benchmark 表保留，3.7-Max 占优维度与速度对比压为摘要）；系列定位分工压缩；适用场景表推荐由 3.7-Max 切换至 3.8-Max |
| 2026-09-02 | 合并：inbox Qwen3.8-Flash 调研 - 新增「Qwen3.8-Flash / Qwen3.8-Flash-Next」小节（2026-08-26 发布：125B/6B 激活 + 51B N-gram Embedding、GDN+QSA 混合注意力、Gated Residual、Muon 优化器、训练成本 1/9、SWE-bench Pro 62.5、Anthropic 协议兼容、Qwen Community 1.0 许可、Next 架构为 Qwen4 雏形）；主推表 Flash 层换代 Qwen3.7-Flash → Qwen3.8-Flash；定价表新增 3.8-Flash 行（新加坡 $0.15/$0.47，国内 ¥0.8/¥2.7/缓存 ¥0.1）；适用场景表同步 |
| 2026-09-01 | 路径修复：`api-sample` 目录已重命名为 `maas-solution-and-api-sample`，同步更新本文全部实测脚本引用路径（9 处，含来源标注与 Changelog 历史记录中的路径） |
| 2026-08-27 | 新增「Qwen3.8-27B 开源 Dense 版」小节（2026-08-17 上线，27B VL Dense）；API 实测（10 用例三端点交叉验证）：**27b 可关闭思考**——enable_thinking=False 完全生效（思考 0 字符，CN 专属/国际站 BJ/SG 三端点一致），默认开启思考，reasoning_effort=none 等价关闭，thinking_budget/reasoning_effort 均有效且互斥；与 a95b（仅思考模式）形成同系列内行为分化；新增脚本 `maas-solution-and-api-sample/test_qwen38_27b_thinking_switch.py` + 结果文件 `maas-solution-and-api-sample/test_qwen38_27b_thinking_switch_results_20260827.md`（含 Qwen3.8 系列思考模式横向对比表） |
| 2026-08-27 | API 实测（10 用例套件）：百炼端点（专属+公共均验证）qwen3.8-2.4t-a95b 的 `enable_thinking` 仅接受 True（传 False 报 invalid_parameter_error），`/no_think` 软开关无效，实际按仅思考模式运行——修正差异表"非思考模式"开源版口径（自部署可关、百炼托管不可关）；实测 `thinking_budget`（budget=1 思考压至均值 3 字符）与 `reasoning_effort`（low/medium/high 梯度 106/134/306 字符）均有效；**新发现：两参数互斥规则同样适用 a95b**（同时设置报错），`effort=none` 被拒印证 none→enable_thinking=False 映射生效；补录闭源版互转映射规则（low↔4096/medium↔16384/xhigh↔262144，默认 131072/xhigh）；新增实测脚本 `maas-solution-and-api-sample/test_qwen38_a95b_thinking_switch.py` + 结果文件 `maas-solution-and-api-sample/test_qwen38_a95b_thinking_switch_results_20260827.md` |
| 2026-08-17 | 合并：inbox 四模型调研 - 新增「Qwen3.8-2.4T-A95B 开源版」小节（92 层混合注意力架构 / 512 experts / 原生 262K 可扩展 ~1M / 许可证 "other" / vs API 版差异表）+ Qwen3.8-Max 官方 benchmark 五模型对比表；修正开源版上下文口径（1M → 原生 262K 可扩展，1M 为 API 版默认配置）；竞品定价表 DS-V4-Pro 行更新为 2026-08-16 峰谷定价 |
| 2026-08-14 | 校验修复：开源状态解除待确认——Qwen3.8 系列开源版 qwen3.8-2.4t-a95b 2026-08-12 上线国际站（2.4T 总参/激活 95B，1M ctx，GPQA 92.6/PaperBench 93.0/OSWorld 86.1），max 本体开源仍未明确；qwen3.7-flash 国际站已上线（上新页 2026-07-21），USD 定价暂未公布；Changelog 折叠 6 条 |
| 2026-08-03 | 清理 Qwen3.6-* 系列残留信息（历史模型标注、竞争力对比、限制表、私有化部署场景、参考链接），Changelog 历史记录保留 |

<details>
<summary>历史早期记录（2026-04 ~ 2026-08）</summary>

| 日期 | 变更内容 |
|------|----------|
| 2026-08-03 | 补录 qwen3.8-max 新加坡节点 USD 定价（控制台截图：输入 $2/输出 $6/缓存命中 $0.25，最大输出 128K，RPM 15000/TPM 200万）；定价表切换为 USD 主口径；修正 3.7-Max 缓存命中价："输入价 10%"（$0.25）→ 实际 $0.5（控制台核实，用户确认），3.8-Max 缓存价仅为 3.7-Max 一半 |
| 2026-08-03 | Qwen3.8-Max 正式版转正：定价已公布（中文定价页：新加坡 ¥14.988/¥44.965、北京/全球 ¥12/¥36，Batch 半价、缓存折扣、100万 Token 免费额度）；删除 Preview 预览版相关章节与信息，Qwen3.8-Max 升为主推旗舰（取代 Qwen3.7-Max）；API 实测确认支持文本+图像输入（VL）；国际站 USD 定价页尚未收录 |
| 2026-07-30 | 校验修复：定价切换为国际站新加坡节点标准（Max $2.5/$7.5 限时 5 折、Plus $0.4/$1.6 限时 8 折）；Flash 解除待官方验证（上新页 2026-07-21 确认，官方定位原生视觉语言，新加坡未上架）；Kimi K3 2026-07-27 已兑现开源；Changelog 折叠最早 2 条 |
| 2026-07-25 | 合并：用户口述 — Qwen3.7-Flash 上线，取代 Qwen3.6-Flash；定位 IPC/审校等在线成本敏感型场景及大批量打标；主推表、系列定位、适用场景、定价表同步更新 |
| 2026-07-20 | 校验修复：TB 2.0 69.7 → 补记 TB 2.1 = 74.5（AA harness）统一口径；AA Index 补注 v4.1 = 46；竞品对比表 GLM-5.1 TB 同步更新为 58.7 |
| 2026-07-20 | 合并：inbox Qwen3.8-Max 信息汇总 - 新增 Qwen3.8-Max-Preview 预览版子章节（2.4T MoE，2026-07-19 上线，承诺正式版开源）；SUMMARY 标注预览版上线；主推表保持 3.7 系列不变（预览版未 GA 不入主推表） |
| 2026-07-10 | 校验修复：移除 Plus "8折至 2026-07-02" 过期到期日，改为"截止日期以百炼控制台为准" |
| 2026-06-14 | 同步 HTML 选型页变更：系列定位分工更新 Max 不再是纯文本旗舰（0608 快照起支持视觉）；Plus 竞争力要点补充视觉场景首选定位 |
| 2026-06-12 | 合并：inbox 素材 — Qwen3.7-Max-2026-06-08 新增视觉能力（官方日志确认 + 视觉模型页面参数表）；修正多处"Max 仅文本"过时描述；新增快照版本演进记录；更新选型结论表（Max-0608 视觉可用但专项 benchmark 待验证）；JSON Mode 实测可用标注 |
| 2026-06-11 | 合并：inbox 选型分析素材 — 新增「Plus vs Max 场景选型详解」子章节（3 层对比 + benchmark 数据 + 推理速度 + 选型结论表）；更新 Plus Benchmark 详细数据（GUI Agent / Visual Coding / 文档理解 / 纯文本 Agent 四维度） |
| 2026-06-04 | 主推模型表更新：移除已取代的 Qwen3.6-Plus / Qwen3.6-Max-Preview，主推表仅保留百炼在售的 3 个模型（Qwen3.7-Max / Qwen3.7-Plus / Qwen3.6-Flash）；历史模型单独标注 |
| 2026-05-31 | 合并：inbox 素材 — 新增百炼 RMB 定价（¥12/¥36，5折 ¥6/¥18）、竞品定价对比表（DS-V4-Pro/GLM-5.1/GPT-5.5/Opus 4.7）、新用户 100 万 tokens 免费额度 |
| 2026-05-31 | 新增 Qwen3.7-Max（2026.05.19 发布），包含关键基准、AA Intelligence Index 56.6、35h 自主运行、定价、局限；更新模型表、能力/场景/限制/定价；标注 Qwen3.6-Max 被 3.7-Max 取代 |
| 2026-04-24 | 合并 qwen3.6.md 内容，补充 Qwen3.6-Max-Preview 详细信息和对比分析 |
| 2026-04-20 | 按_maas_template重构，对齐模板结构 |

</details>
