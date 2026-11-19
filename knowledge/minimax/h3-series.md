# MiniMax H 系列模型

> 最后更新: 2026-11-20
> 所属厂商: MiniMax（稀宇科技）
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: MiniMax Hailuo 全模态生成线（H 系列）：视频（H3）、图像（H3-Image）、音乐（Music 3.0）。H3-Image 为衍生自 H3 的开源图像生成/编辑模型，官方主打「速度 × 画面质量 × 指令遵循」三方面竞争力
**当前主推**: H3-Image（🚩 图像生成旗舰，2026.11.10 开源，AA 文生图/编辑双榜开放权重第一）/ H3（视频）/ Music 3.0（音乐）
**适用**: 4K 图像生成与编辑、多参考图合成、画面内文字推理、视频生成、音乐创作、开放权重自部署与量化研究
**不适用**: 欧盟/英国/韩国/美国地域商用（H3-Image 许可排除）；年化收入 >$1M 或对外托管未获授权的商业部署；用其权重/输出训练其他模型
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 关键规格 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **H3-Image** | 🚩 图像生成/编辑旗舰（开源权重） | 33.1B 稠密 DiT，原生 ~16MP 直出，6 步无 CFG | 10s 内 4K、最多 16 张参考图、生成编辑同 checkpoint；AA 双榜开放权重第一 | 2026.11.10 |
| **H3** | 全模态视频生成（Hailuo 视频线） | 33B，文本/图片/音频/视频输入 | 开放 H3-Base 权重；完整规格与定价见 [general_intro.md](general_intro.md) 产品矩阵 | 2026.07.31 |
| **Music 3.0** | 开放权重音乐生成 | ~111 亿参数，最长 5 分钟完整歌曲 | 作曲/编曲/演唱/制作一体；详见 [general_intro.md](general_intro.md) 产品矩阵 | 2026.08.13 |

> 📌 **路线图**：H3.1（视频线下一代）仍为路线图——2026-08-26 中期业绩电话会"接近完成"口径（媒体转述）[⚠️ 待验证]，未发布不列入主推表。M 系列（语言/Agent）见 [minimax-series.md](minimax-series.md)，勿与 H 系列混淆。
> 📌 **信息收敛**：H3 视频与 Music 3.0 的完整规格/定价当前权威源为 [general_intro.md](general_intro.md) 产品矩阵，本文件仅保留识别性摘要、不重复其数字；H3-Image 完整规格/定价/许可以本文件为权威源。

### H3-Image（图像生成/编辑）

- 模型：MiniMax-H3-Image（API ID `MiniMax-H3-Image` / `MiniMax-H3-Image-Highspeed`）
- 公司：MiniMax（稀宇科技）
- 时间：2026-11-10 发布并同日开放权重
- 尺寸：33.1B 参数稠密单流扩散 Transformer（DiT）
- 官方定位："这是一款衍生自 H3 的图像生成模型，其具备文本生成图像、图像参考和图像编辑能力"；tagline 加粗原文「同时具备了速度、画面质量、指令遵循三个方面的竞争力」
- 场景：4K 图像生成/编辑、多素材合成（最多 16 张参考图）、画面内文字推理
- 特点：官方称"10s 内生成 4K 高规格图像，速度可达市面主流水平的 5 倍"；原生 ~16MP 直出而非超分；生成与编辑共用同一 checkpoint；"开源模型中最强的指令遵循能力"（**厂商自称**）
- 定价：标准档 $2.30/M 文本输入、$1.50/M 图像输入、$3.80/M 图像输出；Highspeed 档 $2.30/$3.00/$7.60（详见下方定价概览）

#### 架构与规格

（来源：HF 模型卡原文，经 hf-mirror 镜像核验）

| 项 | 值 |
|---|---|
| 架构 | 33.1B 稠密单流 DiT，50 层、hidden 5376、56 注意力头、FFN 14336、3D 多模态 RoPE（同 H3-Omni-Transformer）；由 H3-Base 移除音频分支改造 |
| 采样 | 蒸馏至 6 步（6 NFEs）且无 CFG；API `num_inference_steps` 仅接受省略或 6（其他值 HTTP 400）、`guidance_scale` 仅接受省略或 1、不支持 negative prompt |
| 文本编码器 | 沿用 MiniMax-H3 的完整 Qwen3-VL 文本编码器（约 66.7GB，需从 H3 仓库单独下载）；DiT 读取其第 50 层 hidden states |
| VAE | CNN 编码器 + 24 层 2D ViT 解码器；16x 空间下采样、24 latent 通道、2x2 patch（每 token 覆盖 32×32 像素） |
| PDD 机制 | checkpoint 内置 `pdd_fused_heads.safetensors`（12MB）：逐步专用输出头替换 transformer 输出层 + 采样调度表；少步蒸馏以 checkpoint 原生权重而非 LoRA 交付 |
| 分辨率 | 原生 ~16MP 直出无超分：1:1=4096×4096、4:3=4736×3552、3:2=5024×3360、16:9=5472×3072、21:9=6272×2688；有效工作区间 4–20MP，API 面积 655,360–20,000,000 px；`min_generation_area` 默认 4,194,304（不足时同比例放大画布 LANCZOS 缩回） |
| 参考图 | 最多 16 张（模型/API 硬上限），按上传顺序以 `<Picture 1>`…`<Picture 16>` 定位；vLLM-Omni Day-0 配方实测验证范围为 9 张（框架配方口径，非模型上限） |
| 权重体积 | transformer 66.28GB（BF16，embedding/timestep/输出层 FP32）+ VAE 2.34GB（FP32）+ 其他 ≈ 68.65GB；加文本编码器合计约 135GB |
| PE 模型 | `MiniMax-H3-Image-PE` 提示词扩展器，NVFP4 17.9GB，基于 Qwen3.8-27B（Apache 2.0）衍生 |
| API 能力 | 兼容 OpenAI SDK；单请求 1–10 张图；prompt ≤32,000 字符（关闭增强时仅前 4096 token 生效）；支持 SSE 流式；**请求非幂等**（官方示例注释 "not idempotent: disable automatic retries to avoid duplicate generation and charges"，超时重试会重复计费） |

#### 许可与商用风险（关键）

**MiniMax-H3-Image Community License（License date: 2026-11-10），非 Apache/MIT，非 OSI 认证开源**（LICENSE 原文经 hf-mirror 核验）：

| 条款 | 内容 |
|---|---|
| 排除地域 | 原文 Excluded Territories = the European Union, the United Kingdom, the Republic of Korea and the United States of America（在这些地区使用未获授权，需单独申请） |
| 商用授权触发 | Section IV.1：年化收入（含关联方）超 **100 万美元**，**或**对外提供任何托管服务（Hosted Service(s) to any Third Parties）——双重触发，须事先取得书面授权（表单：platform.minimax.io/console/license） |
| 署名 | IV.2 商用界面须显著标注 "MiniMax-H3-Image" |
| 禁训 | V.3 不得用其权重或输出训练/改进其他 AI 模型 |
| 准据法/主体 | 香港特别行政区；许可主体 Nanonoble Pte. Ltd. |

> ⚠️ **与 H3（视频）许可的关键差异（来源冲突已判定）**：H3 视频 Community License（2026-08-02 版）Section IV.1 门槛为年收入超 **2000 万美元**（邮件申请 api@minimax.io，无托管触发条款）。H3-Image 实质收紧 20 倍门槛并新增托管触发——**是两份不同许可，非媒体误读**。商用落地前必须读 LICENSE 原文。

#### 第三方评测与榜单

- **Artificial Analysis（2026-11-13 直接核验）**：文生图榜（AA-Image-T2I v2.1，112 模型）H3-Image Elo **1066±15**（总榜 #23，区间 21–24）、Highspeed 1070±14（#22）；图像编辑榜（AA-Image-Editing v2.1，83 模型）Elo **1138±16**（总榜 #12，区间 8–17）、Highspeed 1134±16（#13）。**两榜均开放权重第一**（文生图第二 Qwen-Image-2.1 1046、第三 FLUX 3 Image Klein 1042；编辑第二 Fibo 2.0 1085、第三 Qwen-Image-2.1 1084）。
  - ⚠️ 限定：**开放权重第一 ≠ 全球第一**。文生图距闭源榜首 GPT Image 2.6 Sunburst（1261）约 195 Elo；编辑榜距榜首约 72–100 Elo。Highspeed 与标准档 Elo 在置信区间内持平（速度档不牺牲质量）。
- **标准学术 benchmark 仍缺**：官方未发布 GenEval/DPG-Bench/人类偏好等标准图像 benchmark 表，缺口仅被 AA Elo 部分填补。
- **vLLM-Omni 官方配方实测**（4×H200，SP4 并发 1，中位）：1024² 0.77s、2048² 0.88s、4736×3552 **3.84s**、单参考图编辑 2048² 1.35s；单卡 H200 驻留 73.4GiB——自部署 4K 级生成进入数秒量级，独立佐证模型内禀速度。
- **社区实测**：h3-image-bench（600 条分级 prompt @16MP，RTX 5080 16GB）；M5 Pro Mac mini ComfyUI INT8 约 9 分钟/4096²；RTX 4070 SUPER 12GB INT8 4MP 11–12s / 16MP 约 41s。

#### 部署生态

- **框架**：SGLang / vLLM-Omni / diffusers / ComfyUI / **LightX2V**（模型卡官方推荐）
- **Day-0 芯片适配**（据官方中文渠道+媒体；官方英文渠道未见此清单，维持原信源口径）：华为昇腾、平头哥、昆仑芯、摩尔线程、壁仞、海光、沐曦、天数智芯、NVIDIA、AMD、Intel、Tenstorrent
- **开源社区动能**（HF 近月）：下载 306,718；23 个微调、27 个量化、13 个 Space；量化覆盖 FP8/NVFP4/GGUF/W4A8/MLX；社区 2 步 pDMD 蒸馏 LoRA；剪枝 135GB→95GB（输出位相同）；MLX 移植 M1–M4（4-bit 4K 峰值约 7GB）；单卡 RTX 4090 24GB 可服务；AMD MI325X/MI350X 官方验证

#### 技术独创性分级与成本归因

**独创性分级**（依据信源优先级 1-3；官方无技术报告，任何首创判断降级待查证，故不标 🌟）：
- 🔧 **组合创新**："6 步 CFG 蒸馏 + 原生 16MP 直出 + 生成编辑同 checkpoint"——各单项均有先例（少步蒸馏 SDXL Turbo/Lightning 2023、FLUX Turbo；4K 直出 Seedream；统一 T2I+编辑 Qwen-Image-Edit/Nano Banana），独特性在"33B 单流 DiT @16MP @6 NFE 且以 checkpoint 原生权重交付蒸馏"的组合
- 📋 **跟进对齐/组件复用**：Qwen3-VL 冻结文本编码器（读第 50 层）+ Qwen3.8-27B PE——FLUX 用 T5、Qwen-Image 用 Qwen2.5-VL 先例；H3 视频已用 Qwen3-VL-32B，属家族内沿用；跨厂商复用 Apache 2.0 Qwen 组件是国产开源生态的现实选择，非 MiniMax 独有
- ⚙️ **工程优化**：SP/Ulysses 序列并行、CUDA Graph、VAE tiling、DLO 逐层卸载、单卡驻留 73.4GiB，幅度可观（自部署 4K 级 3.84s）

**能力为什么更强（因果链）**：6 NFE 无 CFG → 单图前向较 50 步 CFG（等效 100 NFE）降约 16 倍 → 4K 延迟成本进入日用区间（存量变强）；16MP 直出免超分管线 + 16 张参考图 → 多素材合成（官方示例：空房间+9 件家具合成客厅、3D 渲染上色成电影剧照）与画面内文字推理（中英文逻辑谜题在画面内解答）为开放权重新增能力边界（增量解锁）；同 checkpoint → 一套 135GB 栈服务双场景，部署与迭代成本减半（存量变强）。

**成本为什么更低（双轨归因）**：
- **架构内禀降本（可持续）**：少步蒸馏真实降单图算力（NFE 16 倍级下降）+ BF16/FP8/量化部署路径成熟，vLLM-Omni 实测支撑
- **定价策略降本（可回调）**：上市初期曾有短期促销（已结束）；Highspeed 输出价 2 倍（$7.60 vs $3.80）说明速度是付费分层而非免费增益
- 第三方参照：AA 口径 $21.79/千张（1K）低于 Nano Banana 2.1 的 $33.60

### H3（视频）与 Music 3.0

完整规格、定价与开源状态见 [general_intro.md](general_intro.md) 产品矩阵（信息收敛：本文件不重复其数字）。本次新增核实：
- **H3 视频许可**：Community License（2026-08-02 版），年收入超 2000 万美元须邮件申请授权（api@minimax.io），无托管触发条款；文本编码器为 Qwen3-VL-32B（Apache 2.0）
- H3-Image 即衍生自 H3（移除音频分支），文本编码器沿用 H3 的 Qwen3-VL

## 核心能力与限制

### 核心能力（H3-Image）

| 能力 | 说明 |
|------|------|
| 4K 高速生成 | 官方称 10s 内 4K、速度达市面主流 5 倍；服务口径标准模式 1.5–2 倍 / Highspeed 3–4 倍 |
| 原生高分辨率 | ~16MP 直出无超分，API 上限 20MP |
| 多参考图编辑 | 最多 16 张参考图，生成/编辑同 checkpoint |
| 指令遵循 | 官方称"开源模型中最强"（厂商自称）；画面内文字推理 |
| 开放权重 | 同日开源，社区量化/蒸馏/剪枝/MLX 生态活跃 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 许可地域 | 排除欧盟/英国/韩国/美国 | 非 OSI 开源，商用须读 LICENSE 原文 |
| 商用门槛 | 年化收入 >$1M 或对外托管须书面授权 | 比 H3 视频许可（$20M）收紧 20 倍 |
| 采样参数 | 仅 6 步、guidance 仅 1、无 negative prompt | 蒸馏模型硬约束 |
| 禁训条款 | 不得用权重/输出训练其他模型 | 许可 V.3 |
| 学术 benchmark | GenEval/DPG-Bench 等仍缺 | 仅有 AA Elo 与社区实测 |
| 请求幂等性 | 非幂等，超时重试重复计费 | 须禁用自动重试 |

## 定价概览

| 档位 | 文本输入 | 图像输入 | 图像输出 | 备注 |
|------|---------|---------|---------|------|
| 标准 | $2.30/M | $1.50/M | $3.80/M | 4K 文生图单张 $0.06879 |
| Highspeed | $2.30/M | $3.00/M | $7.60/M | 4K 文生图单张 $0.13001；速度付费分层 |
| Context-IR（提示词增强） | $2.30/M 输入 | — | — | 增强产生的 token 计入文本输入 |

> 定价来源：https://platform.minimax.io/docs/pricing/overview.md ，核实日期：2026-11-13
> H3 视频定价（¥0.8/秒）见 [general_intro.md](general_intro.md)，本文件不重复。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 4K 图像日常创作 | H3-Image | 10s 级延迟，成本进入日用区间 |
| 多素材合成/编辑 | H3-Image | 16 张参考图，生成编辑同栈 |
| 画面内文字/逻辑推理 | H3-Image | 中英文逻辑谜题在画面内解答 |
| 自部署/量化研究 | H3-Image | 开放权重，单卡 RTX 4090 可服务，MLX 4-bit 4K 峰值约 7GB |
| 视频生成 | H3 | 详见 general_intro.md |
| 音乐创作 | Music 3.0 | 详见 general_intro.md |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 欧盟/英国/韩国/美国商用 | 许可排除地域，须单独授权 |
| 用权重/输出训练其他模型 | 许可 V.3 禁止 |
| 需要 negative prompt / 多步采样调参 | API 硬约束（仅 6 步、guidance 1） |

## 参考资料

- https://www.minimax.cn/blog/minimax-h3-image （官方博文全文）
- https://hf-mirror.com/MiniMaxAI/MiniMax-H3-Image （HF 模型卡，镜像核验）
- https://hf-mirror.com/MiniMaxAI/MiniMax-H3-Image/raw/main/LICENSE （H3-Image 许可原文）
- https://hf-mirror.com/MiniMaxAI/MiniMax-H3/raw/main/LICENSE （H3 视频许可原文，门槛对比）
- https://platform.minimax.io/docs/pricing/overview.md （官方定价页）
- https://platform.minimax.io/docs/guides/image-generation （官方 API 指南）
- https://artificialanalysis.ai/image/leaderboard/text-to-image · /image/leaderboard/editing （AA 双榜，2026-11-13 核验）
- https://recipes.vllm.ai/MiniMaxAI/MiniMax-H3-Image （vLLM-Omni 官方配方与实测延迟）
- https://github.com/MiniMax-AI/awesome-minimax-h3-integration （官方生态索引）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-11-20 | 校验修复：清理限时促销/免费额度等营销性信息，定价保留官方标准列表价口径 |
| 2026-11-13 | 新建：inbox/ai-knowledge-by-qoder-ai-native-agent-20261113.md（H3-Image 条目）- H 系列首份独立文档；H3-Image 全规格/定价/许可/AA 双榜/生态入库；许可营收门槛冲突判定（H3 视频 $20M vs H3-Image $1M+托管触发，两份不同许可）；H3 视频/Music 3.0 按信息收敛引用 general_intro.md；「关键技术论文」节省略（官方无技术报告，仅模型卡文件级证据） |