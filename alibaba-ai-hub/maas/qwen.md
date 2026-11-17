# 通义千问 (Qwen)

> 最后更新: 2026-11-17
> 所属厂商: 阿里云
> 产品类别: MaaS

**定位**: 阿里云自研大语言模型系列，覆盖文本/代码/多模态，开源+商业双轨并行
**当前主推**: Qwen4-Max 🚩（旗舰，文本+图像+视频，2026-11-16 GA）/ Qwen3.8-27B（开源 Dense 视觉语言，GUI/视觉场景）/ Qwen3.8-Flash（新架构轻量快速，2026-08-26）
**适用**: 企业级AI应用开发、智能对话、代码生成、多模态理解、长时间自主 Agent

## 当前主推模型

> 数据来源：[百炼模型广场](https://help.aliyun.com/zh/model-studio/models)，2026-07-25 核实；Qwen3.8-Flash 行据 qwen.ai 官方博客 + 千问AI平台模型页（2026-08-26/09-02）；Qwen4-Max 行据 help.aliyun.com 官方模型文档 + 国际站定价页（2026-11-16 抓取）与当日 API 实测

| 模型 | 定位 | 上下文 | 特点 |
|------|------|--------|------|
| **Qwen4-Max** 🚩 | 旗舰（文本+图像+视频） | **1M tokens** | 2.4T MoE / 71B 激活 + 328B N-gram Embedding；Next 架构旗舰首发；取代 Qwen3.8-Max（2026-11-16 GA）；任务级成本较上代降约 60%，详见下方小节 |
| **Qwen3.8-27B** | 开源 Dense 视觉语言（GUI/视觉场景） | **262K tokens** | 27B Dense 原生视觉语言模型（2026-08-17 上线）；编程+办公端到端；百炼 CN 专属/国际站 BJ/SG 三端点可用，**混合思考可关闭**（实测）；销售指南 0930 起以本款替代 Qwen3.7-Plus |
| **Qwen3.8-Flash** | 轻量快速（新架构） | **1M tokens** | 下一代（Next）架构首发载体：125B MoE / 6B 激活 + 51B N-gram Embedding，原生图/视频输入，OpenAI + Anthropic 双协议兼容，训练成本仅上代 Plus 的 1/9；取代 Qwen3.7-Flash [来源: qwen.ai 官方博客 + qianwenai.com，2026-08-26] |

> 📌 **历史/存量模型**：**Qwen3.8-Max 已被 Qwen4-Max 取代（2026-11-16），API 仍可调用**，仅建议存量项目使用；**Qwen3.7-Plus 已退出主推（2026-11-05 起）**——GUI/视觉场景改选 Qwen3.8-27B，通用多模态改选 Qwen4-Max；Qwen3.7-Max（被 3.8-Max 取代）、Qwen3.7-Flash（被 3.8-Flash 取代）同样仅建议存量项目使用。

### Qwen4-Max（2026-11-16 GA，当前旗舰）

- **模型**：Qwen4-Max（Model ID: `qwen4-max`），Qwen4 系列首款模型，**取代 Qwen3.8-Max**（官方定位"新一代旗舰"；AA 已将 3.8-Max 标记 deprecated 并建议改用 Qwen4 Max）
- **公司**：阿里云
- **时间**：**2026-11-16 GA**，按量计费可用，当日 CN / 国际站 SG / 国际站 BJ 三端点实测调通（报告：`maas-solution-and-api-sample/test_qwen4_max_preview_results_20261116.md`）
- **尺寸**：主干 **2.4T MoE，每 token 激活 71B**，另配 **328B N-gram Embedding**（第二层查表，不进每 token 矩阵乘预算）[来源: qwen.ai 官方博客，经 IT之家/凤凰/网易多源转述交叉确认]
- **上下文**：**1M tokens**（输入 991K / 思考模式 983K）；最大输出非思考 **131,072**，**思考+回答总预算 262,144** [来源: help.aliyun.com/zh/model-studio/qwen4-max]
- **输入模态**：文本 + 图像 + **视频**（Max 档首次官方确认视频；AA 仅测 text+image，视频待独立验证），输出文本
- **思考**：默认开启（`enable_thinking=true`）；`reasoning_effort` low / **high（默认）** / xhigh（minimal→low、medium→high、max→xhigh）；`preserve_thinking` 默认开启；`thinking_budget` 默认 131072。⚠️ 默认 effort 由 3.8 系 xhigh 降为 high，对比测试须对齐档位
- **工具与协议**：FC（含并行）/ 联网搜索 / 前缀补全 / JSON Object+Schema / 思维链摘要与加密 / 显式（TTL 5m/1h）+隐式缓存；OpenAI Chat Completions + Responses / Anthropic Messages / DashScope 四协议
- **限流**：TPM 5M（3.8-Max 为 2M）[来源: qianwenai.com/models/qwen4-max]
- **开源**：**本体闭源**（AA 确认权重未开放）；官方称 Qwen4 系列小尺寸模型将陆续开源（时间/型号未公布）——vs 3.8 代有 Max 级开源版 a95b，**私有化客户短期无 Qwen4 旗舰选项**，关键销售差异
- **入口**：百炼/QwenCloud API、Qwen Studio、QwenWork、Qoder
- **定价**：见下方「定价（API）」章节
- **场景**：办公生产力、创意创作、软件开发、科学研究；官方案例覆盖 Blender 3D 建模、Unity/Unreal 游戏开发、汽车产线规划与零件加工编程（单工件编程人工投入约 475 分钟→24 分钟）、金融投研、法律尽调、危重症临床辅助
- **技术报告 / 知识截止 / 专家数与路由细节 / Muon 是否沿用**：未公开 [⚠️ 待补充]

**架构与技术亮点（独创性分级）**：Next 架构（Qwen3.8-Flash-Next 首发验证，官方预告"Qwen4 雏形"兑现）首次上旗舰尺度，**无可确认的 🌟 首创点**：

| 亮点 | 分级 | 依据 |
|------|------|------|
| GDN + QSA 混合注意力（每 4 层 3 层 Gated DeltaNet + 1 层 QSA 块级稀疏全局注意力） | 🔧 组合创新 | GDN 学术原创：Songlin Yang / Jan Kautz / Ali Hatamizadeh（MIT+NVIDIA），ICLR 2025，arXiv:2412.06464；块级稀疏注意力先行者 DeepSeek NSA/MoBA、MiniMax MSA。vs 3.8-Max a95b 全局层为标准 Gated Attention，**全局层升级 QSA 是代际内真正架构 delta** |
| N-gram Embedding 51B（Flash）→ 328B（Max） | 🔧 组合创新 | 官方自认受 Gemma 3n PLE / DeepSeek Engram 启发（非首创）；新颖点在尺度——"容量与计算解耦"路线目前公开最大规模实践，补世界知识/感知容量不增激活算力 |
| Gated Residual 4 分支残差 | ⚙️ 工程优化 | Hyper-Connection（字节论文路线）+ GatedNorm 融合，3.8-Flash 已首发，本次沿用 |
| 激活 95B（a95b）→ 71B，总参维持 2.4T | ⚙️ 工程优化 | 激活占比约 3%，单 token 算力约 -25% |
| Token 效率：同性能 Work360 xhigh/high 消耗 -24%/-35%，TB 4.0 -48%/-49% | ⚙️ 工程优化 | 官方只给结果，机制未公开 [⚠️ 待查证] |
| Live Delivery 机制 + 开源 Qwen-Live-Delivery-Plugin | 🔧 组合创新（待查证） | "先交付可用首版、按反馈逐版扩展"内化为模型能力并配官方插件；迭代交付非新概念，是否模型能力而非 Harness 编排待官方博客全文确认 |
| Work360 自建评测（26 一级 / 182 二级 / 721 三级专业方向） | ⚙️ 工程优化 | 评测基建；自建 benchmark 利益相关，须与 AA 独立数据并陈 |
| Max 档原生视频输入 | 📋 跟进对齐 | Gemini 先行，自家 3.8-Flash 已有；对 Max 档补齐 |

**Benchmark（口径隔离）**：

| 口径 | Qwen4-Max | Qwen3.8-Max | 说明 |
|------|-----------|-------------|------|
| Work360（官方自建） | **52.69** | 47.74 | [来源: 官方博客，IT之家/凤凰转述] |
| AA Intelligence Index **v5.0.1**（2026-11-16 查询） | **43**（#38/81） | 34（#51/81，deprecated） | 同口径 +9；绝对座次仍低于 Fable 5.2（65）/ Opus 5.5 / Gemini 4 Carbon 等第一梯队 |
| AA 单任务成本 | **$3.27** | $10.02 | -67% |
| AA 全指数输出 tokens | 127M | 150M | -15%，但仍高于同类中位 78.6M（verbose 偏高） |

> ⚠️ **口径警告**：① AA 指数 v5→v5.0.1 重校准，旧记录"3.8-Max v5=45"与 Qwen4-Max 43 跨版本不可比，同版本下才是 43 vs 34；② TB 4.0 与 TB 2.1 为不同难度独立基准，Qwen4-Max 的 TB 4.0 绝对分未公布（官方仅公布 token 降幅）[⚠️ 待补充]；③ Work360 为自建基准，引用时须与 AA 独立数据并陈。

**能力增强因果链**：
- **存量变强**：Token 效率 → 同 262K 思考预算装下更长任务链，长程 Agent 截断/降智概率下降（AA 佐证：输出 -15% 且分数更高）；QSA+GDN → 1M 上下文从"标称"向"用得起"迁移（Flash 档 QSA kernel 最高 7.6×/4.9× 加速，Max 档幅度未公开）；328B N-gram 查表 → 世界知识与感知容量（官方宣传语"更强的世界知识与感知能力"）
- **增量解锁**：专业工具长程操作（交付物是专业软件工件而非文本）；Live Delivery 交付范式降低长任务"全有或全无"风险；Max 档视频理解使多模态 Agent 不再需 Flash/27B 分流

**成本归因（任务级成本降约 60%）**：
- **架构内禀降本（真实、可持续）**：激活 95B→71B + GDN/QSA 长序列注意力开销下降 + 328B 容量走查表不走算力 + token 效率 -24%~-49%。官方 Work360 单任务均价 **¥26.58→¥11.16（-58%）**；AA 独立口径 **$10.02→$3.27/task（-67%）**——两独立来源同指"约 6 成"（媒体标题"超 60%"与正文 58% 为口径差异，建议引用"约 60%，官方 58%/AA 67%"）
- **定价策略降本（让利，可能回调）**：列表价 -25%、**缓存命中价 -70%（降至输入价 5%，单价见定价章节）**——agentic 流量天然高前缀复用，缓存地板价是定向补贴 Agent 场景、锁定百炼流量的定价信号（与 3.8-Flash"90% 缓存命中 1M prefill 吞吐 8.6×"叙事一脉相承）。降本有坚实架构基础非纯补贴；价格若回调，架构红利仍在

**迁移注意（自 qwen4 代起，官方口径 + 实测）**：
- `max_tokens` / `max_completion_tokens` 等价，均限制**思考+回答总量**；沿用旧模型"仅为回答预留"的上限会导致输出提前截断
- `preserve_thinking` 默认开启，多轮历史 assistant 消息须经 `reasoning_content` 完整回传（或按新协议回传思维链密文）
- 口语名 `qwen4.0-max` 无效（404），Model ID 必须用 `qwen4-max`

**边界与待核实**：
- qianwenai.com 模型页"最大输出 393K"与 help.aliyun.com 131K/262K 矛盾，以 help.aliyun + API 实测为准
- Batch 口径矛盾：help.aliyun 能力表六节点均"批量推理不支持"，但国际站定价页列北京 Batch File 价（$0.707/$2.12），实测报告记"批量仅北京支持" [⚠️ 待核实]
- 绝对智能非第一梯队（AA 43 vs Fable 5.2 65），最难科研/推理任务勿过度承诺；Work360 为自建基准

### Qwen3.8-Max（上代旗舰，存量，已被 Qwen4-Max 取代）

> 📌 2026-11-16 被 Qwen4-Max 取代，API 仍可调用（含 `qwen3.8-max-0902` 快照，同价），仅建议存量项目使用；新项目旗舰场景选 Qwen4-Max。

- **规格**：2.4T MoE（Qwen 首款万亿级参数模型）；1M 上下文 / 最大输出 128K；文本+图像输入（2026-08-03 实测确认，视频未确认——视频需求改选 Qwen4-Max）；思考/非思考双模式；RPM 15,000 / TPM 2M
- **上线**：2026-07-19 预览、2026-08-03 正式版；定价见「定价（API）」章节；开源权重版为 a95b（见下节）
- **AA 口径（2026-11-16）**：v5.0.1 = **34**（#51/81，已标记 deprecated，AA 建议改用 Qwen4 Max）；旧记录 v5=45 为过期口径，跨版本不可比。官方"仅次于 Fable 5"仅自评，无第三方背书
- **迭代意义**：首次万亿参数 + 首次 Max 级开源；其 GDN 混合注意力 / MTP 设计直接演进为 3.8-Flash-Next 与 Qwen4 的 Next 架构

**代际基准锚点**（官方发布时口径，TB 2.1 时代）：

| 基准 | Qwen3.8-Max | Qwen3.7-Max |
|------|------------|-------------|
| Terminal-Bench 2.1 | **86.6** | 74.5 |
| PaperBench | **93.0** | — |
| SWE-bench Pro | 67.7 | 60.6 |
| DeepSWE 1.1 | 56.6 | 21.6 |
| FrontierSWE | 73.5 | 40.7 |
| GPQA Diamond | 92.6 | 92.4 |

> 📐 两模型均早于 TB 4.0 发布、无官方 4.0 分数，按全库规则不换算不补算；本表仅内部可比，不得与新模型 TB 4.0 分数混排。同期竞品对照（Opus 4.8 / Fable 5 / GPT 5.6 Sol）见 [Qwen3.8 官方博客](https://qwen.ai/blog?id=qwen3.8) 与 [benchmark-coding-agentic.md](../../knowledge/ai-general-notes/benchmark-coding-agentic.md)。

### Qwen3.8-2.4T-A95B 开源版（存量，2026-08-12 上线）

- **定位**：Qwen3.8-Max 的开源权重版（HF: Qwen/Qwen3.8-2.4T-A95B），**Qwen 首款 Max 级开源模型**；许可证 HF "other"（非标准 Apache/MIT，商用前需确认）
- **架构要点**：2.4T 总参 / 95B 激活，92 层；512 experts（每 token 10 routed + 1 shared，激活约 2.1%）；GDN : Gated Attention = 3:1 混合注意力 + MTP 多步训练——**Next 架构的直接前身**；原生 262K 上下文可扩展 ~1M（1M 为 API 托管版默认配置）；213 个 safetensors 分片须全量加载 VRAM，自部署门槛极高（vLLM / SGLang / TokenSpeed）[来源: mindstudio.ai 解析 + NVIDIA NeMo 模型页]
- **与 API 版（3.8-Max）差异**：无视觉输入、无内置工具、上下文原生 262K
- **思考模式（百炼实测 2026-08-27）**：百炼端点 `enable_thinking` 仅接受 True、`/no_think` 无效 → **托管版无法关闭思考**（与官方"混合思考"文档分类不符，以实测为准；自部署不受此限）；曲线方案 `thinking_budget` 设极小值（budget=1 思考仅约 3 字符）；`reasoning_effort` 实测有效但官方支持列表未列 a95b，与 budget **互斥**（同时设置报错）
- **实测脚本与数据**：`maas-solution-and-api-sample/test_qwen38_a95b_thinking_switch.py` + 同名 `_results_20260827.md`（含闭源版 effort↔budget 互转映射规则与 10 用例完整数据）
- **迭代意义**：Max 级开源被视为生态策略转向——开源建壁垒，API 版以视觉/内置工具/1M 上下文增值；至 Qwen4 代旗舰回归闭源，**私有化旗舰短期仅此一款可选**

### Qwen3.8-27B 开源 Dense 版（当前主推，2026-08-17 上线）

- **定位**：27B Dense 原生视觉语言模型，相较 3.6-27B 重点提升文本/视觉模态下的编程与办公端到端能力；百炼 CN 专属 / 国际站 BJ / SG 三端点实测可用（2026-08-27）
- **思考模式（实测，10 用例三端点交叉验证）**：**真混合思考，可关闭**——`enable_thinking=False` 完全生效（思考 0 字符，三端点一致，与官方文档分类一致），`reasoning_effort=none` 等价关闭；默认开启思考；`thinking_budget` / `reasoning_effort` 均有效且互斥（同时设置报错）；`/no_think` 软开关不能完全关闭，有硬开关后无实用价值
- **实测脚本与数据**：`maas-solution-and-api-sample/test_qwen38_27b_thinking_switch.py` + 同名 `_results_20260827.md`（含 Qwen3.8 系列思考模式横向对比表）

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


## 系列迭代思路与方向

> 3.7 → 3.8 → Qwen4 的演进主线，供选型与趋势判断；各代规格与实测详见上方专章。

| 维度 | 迭代轨迹 | 方向判断 |
|------|----------|----------|
| 架构 | 3.8-Max/a95b 首用 GDN 混合注意力 → 3.8-Flash-Next 补齐 QSA + Gated Residual + N-gram Embedding + Muon（Next 架构四件套）→ Qwen4-Max 旗舰尺度兑现 | "开源预览先行、旗舰随后"打法延续（Qwen3-Next → 3.5/3.8 → Flash-Next → Qwen4）；容量与计算解耦（N-gram 查表）是核心降本路线 |
| 效率与成本 | 激活 95B→71B（总参维持 2.4T）、token 效率提升、Flash 训练成本仅 3.7-Plus 的 1/9 | 任务级降本有架构内禀基础非纯补贴；缓存地板价（Qwen4-Max 命中价=输入价 5%）定向补贴 agentic 高前缀复用流量、锁定百炼生态 |
| 档位分工 | 3.7 代 Max/Plus/Flash 三档 → 3.8 代 Plus 退出主推、由开源 27B Dense 承接 GUI/视觉 → Qwen4 代 Max 补齐视频、通用多模态不再分流 | Plus 档被"开源 Dense + 轻量 MoE"夹击取代；旗舰向全模态 + 长程 Agent 收敛 |
| 开源策略 | 3.8 代首次 Max 级开源（a95b）→ Qwen4 本体闭源、小尺寸将陆续开源（时间/型号未公布） | 开源建生态壁垒、API 以全模态/内置工具/1M 上下文增值；私有化旗舰短期仅 a95b，关键销售差异 |
| 能力范式 | 文本/代码 → 多模态理解 → 长程自主 Agent + Live Delivery 迭代交付 | 交付物从文本转向专业软件工件；qwen4 起 max_tokens 语义变更（限思考+回答总量）是旧项目迁移主要坑 |

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **深度推理（Max）** | Qwen4-Max 思考默认开启（effort low/high/xhigh）；AA 与定量 Benchmark 统一见模型小节 |
| **Agentic Coding** | 面向工程级项目理解、长程自主开发与多工具协作；Qwen4-Max 新增 Live Delivery 迭代交付；定量数据见 Qwen4-Max Benchmark |
| **超长上下文** | Qwen4-Max / 3.8-Max / Flash API 默认 1M tokens，适合大型代码仓库和长文档 |
| **多模态智能体** | Qwen3.8-27B 承接 GUI/视觉场景，Qwen4-Max 承接通用多模态（文本+图像+视频）；Qwen3.8-Flash 支持文本、图像与视频输入 |
| **数学与复杂推理** | 当前主推 Qwen4-Max；上代基准锚点见存量模型小节 |
| **多语言** | 覆盖 55 种语言，支持多语言创作与翻译 |
| **开源生态** | Qwen3.8-2.4T-A95B、Qwen3.8-27B 与 Qwen3.8-Flash-Next 覆盖旗舰、Dense 视觉与轻量架构预览；Qwen4-Max 本体闭源，小尺寸模型将陆续开源（时间/型号未公布） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| Qwen4-Max 开源 | 本体闭源 | 小尺寸模型将陆续开源（未公布）；私有化旗舰需求短期无 Qwen4 选项 |
| Qwen4-Max Batch | 口径矛盾待核实 | 能力表六节点均"不支持" vs 定价页列北京 Batch File 价，调用前与控制台确认 |
| Qwen4-Max max_tokens 语义 | 限制思考+回答总量 | 自 qwen4 代起变更，旧模型迁移须调整上限与思考回传逻辑 |
| Qwen3.8-Max 视频输入 | 待确认（存量） | 文本与图像输入已实测，不应承诺视频能力；视频需求改选 Qwen4-Max |
| qwen3.8-2.4t-a95b 视觉输入 | 不支持 | 开源版与 API 版 Qwen3.8-Max 的模态能力不同 |
| qwen3.8-2.4t-a95b 百炼思考模式 | 仅思考 | 百炼端点不可关闭思考；自部署不受此限 |
| 并发限制 | 按账户与模型 | 以百炼控制台限额为准 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 长程 Agent / 复杂推理 / 重度编码 / 专业办公 | **4-Max** | 2.4T/71B 激活旗舰，Work360 52.69、AA v5.0.1 43，任务成本较上代降约 60%（3.8-Max 已被取代） |
| GUI/视觉 Agent / 视觉编码 / 编程办公性价比 | **3.8-27B** | 27B Dense 原生视觉语言，可关思考（实测），$0.5/$3；销售指南 0930 起以此替代 3.7-Plus |
| IPC / 审校 / 大批量打标等成本敏感场景 | **3.8-Flash** | 在线低延迟低成本，2026-08-26 新架构发布（取代 3.7-Flash） |
| 高并发轻量调用 | **3.8-Flash** | 低延迟低成本，TPM 5M，缓存命中价仅输入价 12.5% |

## 接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| API 直接调用 | DashScope API，兼容OpenAI格式 | 快速集成 |
| 平台托管 | 百炼平台，可视化编排 | 企业级应用 |

## 定价（API）

> 定价标准：阿里云国际站新加坡节点 USD 列表价，2026-11-16 核实；列 Qwen4-Max 与存量 Qwen3.8 代模型。北京价格与国内计费项仅作参考，实际折扣与账单以控制台为准。

| 模型 | 输入（$/1M tokens） | 输出（$/1M tokens） | 缓存与其他说明 |
|------|---------------------|---------------------|----------------|
| **Qwen4-Max** | $1.5 | $4.5 | 缓存命中 $0.075（输入价 5%，较 3.8-Max -70%）；显式缓存写 5m $1.875 / 1h $3；北京 $1.413/$4.24；CN 参考 ¥10/¥30、缓存命中 ¥0.5 [来源: alibabacloud.com 定价页 + qianwenai.com，2026-11-16] |
| **Qwen3.8-Max**（含 `qwen3.8-max-0902` 快照，存量） | $2 | $6 | 缓存命中 $0.25；稳定版与 0902 快照同价 |
| **qwen3.8-2.4t-a95b**（开源版） | $2 | $6 | 支持缓存折扣（单价未公开）；北京 $1.65/$4.951 |
| **qwen3.8-27b**（开源 Dense 版） | $0.5 | $3 | 支持缓存折扣（单价未公开）；北京 $0.424/$1.696 |
| **Qwen3.8-Flash** | $0.15 | $0.47 | 国内参考：¥0.8/¥2.7、缓存命中 ¥0.1、显式缓存创建 ¥1.25、Batch ¥0.4/¥1.35 [来源: alibabacloud.com 新加坡定价页 + qianwenai.com，2026-09-02] |

## 竞品定价对比（参考）

| 模型 | 输入（每 1M tokens） | 输出（每 1M tokens） | 缓存 | 来源 |
|------|----------------------|----------------------|------|------|
| **Qwen4-Max**（新加坡） | $1.5 | $4.5 | $0.075 | alibabacloud.com（2026-11-16） |
| DeepSeek-V4-Pro（非峰） | $0.66（≈¥4.8） | $1.98（≈¥14.4） | $0.022 | api-docs.deepseek.com（2026-08-16 起峰谷定价：峰时×2，详见 [deepseek-v-series.md](../../knowledge/deepseek/deepseek-v-series.md)） |
| GLM-5.1（智谱） | ¥6（32K以内）/ ¥8 | ¥24 | ~¥3.4（$0.475） | open.bigmodel.cn |
| GPT-5.5 | $5（≈¥36） | $30（≈¥216） | $0.50 | apidog.com (AA) |
| Claude Opus 4.7 | $6.25（≈¥45） | $25（≈¥180） | $0.50 | apidog.com (AA) |

> Qwen4-Max 单价高于 DeepSeek-V4-Pro 与 GLM-5.1，核心差异点为 1M 上下文（GLM-5.1 128K）、原生视频输入、专业办公/长程 Agent 能力（Work360 52.69）与任务级成本优势（AA 单任务 $3.27，较上代 -67%）。跨厂商比较仍需统一上下文、缓存、峰谷与汇率口径。

## 参考资料

- [Qwen4-Max 官方模型文档](https://help.aliyun.com/zh/model-studio/qwen4-max)
- [Qwen4-Max 官方博客](https://qwen.ai/blog?id=qwen4-max)
- [Qwen4-Max 千问AI平台模型页](https://www.qianwenai.com/models/qwen4-max)
- [AA：Qwen4 Max](https://artificialanalysis.ai/models/qwen4-max) / [AA：Qwen3.8 Max (0902)](https://artificialanalysis.ai/models/qwen3-8-max)
- [Gated Delta Networks 论文（ICLR 2025）](https://arxiv.org/abs/2412.06464)
- [Qwen3.8 官方博客](https://qwen.ai/blog?id=qwen3.8)
- [Qwen3.8-Flash-Next 官方博客](https://qwen.ai/blog?id=qwen3.8-flash-next)
- [阿里云国际站模型定价](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- [百炼模型定价](https://help.aliyun.com/zh/model-studio/model-pricing)
- [百炼模型上下架与更新](https://help.aliyun.com/zh/model-studio/newly-released-models)
- [Computer Use AI 全球排名](https://benchlm.ai/best/computer-use)
- [Agentic LLM 参考](https://artificialanalysis.ai/models?intelligence=coding-index)
- [通义千问官网](https://tongyi.aliyun.com)
- [百炼平台](https://bailian.console.aliyun.com)
- [Qwen GitHub](https://github.com/QwenLM)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-11-17 | 瘦身：压缩存量模型小节（3.8-Max/A95B 收敛为要点+代际基准锚点，27B 精简实测细节），新增「系列迭代思路与方向」演进表；修复 Qwen3.7 历史小节悬空引用，清理历史参考链接；9 月及以前 Changelog 移入折叠区并压缩 |
| 2026-11-17 | Qwen3.8-Max Benchmark 表对齐全库 TB 4.0 统一口径规则：新增 TB 4.0 行（五模型均早于 4.0 发布、无官方分数，不换算不补算，全"—"），TB 2.1 行标注发布时口径，表下补口径隔离警告（与 qwen-vs-hy 对比表同款处理） |
| 2026-11-16 | 用户要求删除 qwen4-max-preview 预览版信息（预览期至 11-25 后下线，无长期保留价值）：时间行/迁移注意/边界标注/参考资料四处清理，保留 qwen4.0-max 无效名提示与 393K 口径矛盾警示 |
| 2026-11-16 | 合并：inbox Qwen4-Max 发布调研 - 新增 Qwen4-Max 专章并切换主推/定价/竞品/场景；3.8-Max 转存量并修正 AA 过期口径（v5→v5.0.1 重校准，跨版本不可比）；Batch/393K 口径矛盾标注待核实 |
| 2026-11-10 | 定价与历史内容精简：API 定价仅保留 Qwen3.8 代，竞品对照改用 Qwen3.8-Max；合并 Qwen3.7 系列为历史存量小节，删除重复的 Plus vs Max 选型详解，保留迁移路径与关键历史数据 |
| 2026-11-08 | 校验修复（knowledge-verification-2026-11-08）：解除 Qwen3.8-Max「AA 尚未复测」过期表述——AA 已收录 v5 = 45（低于 Carbon/Opus 5.5/Astra/GPT-6.1 Sol/K3.1 Pro），官方「仅次于 Fable 5」自评加座次对照与口径提醒 |
| 2026-11-05 | 主推口径修正（用户明确）：**Qwen3.7-Plus 退出主推**（3.8 代无 Plus 继任者，官方销售指南 0930 起已以 Qwen3.8-27B 替代）；主推表/系列定位/核心能力/适用场景同步改写 |

<details>
<summary>历史早期记录（2026-04 ~ 2026-09）</summary>

| 日期 | 变更内容 |
|------|----------|
| 2026-09-17 | 校验修复+合并：新增 3.8-Max-0902 快照小节；Qwen3.7-Flash 国际站 USD 阶梯定价公布解除"未公布"；a95b/27b 补北京价与缓存口径；删免费额度营销残留；修复 deepseek-v-series 断链 |
| 2026-09-02 | 压缩 Qwen3.7-Max 历史内容与 Plus vs Max 选型详解；适用场景推荐切换 3.8-Max |
| 2026-09-02 | 合并：inbox Qwen3.8-Flash 调研 - 新增 Flash/Flash-Next 专章（Next 架构首发），主推/定价/场景同步换代 |
| 2026-09-01 | 路径修复：api-sample 重命名为 maas-solution-and-api-sample，全文脚本引用同步 |
| 2026-08-27 | 新增 27B 专章；实测确认 27b 可关思考（三端点一致），与 a95b 仅思考形成系列内行为分化 |
| 2026-08-27 | 实测 a95b 百炼端点仅思考模式（enable_thinking 仅 True），budget/effort 有效且互斥；补录闭源版互转映射 |
| 2026-08-17 | 合并：四模型调研 - 新增 A95B 开源版专章与 3.8-Max 官方五模型 benchmark 表；修正开源版上下文口径 |
| 2026-08-14 | 校验修复：a95b 开源上线解除待确认；3.7-flash 国际站上线、USD 定价未公布 |
| 2026-08-03 | 清理 Qwen3.6-* 系列残留信息（历史标注/对比/限制表/参考链接） |
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
