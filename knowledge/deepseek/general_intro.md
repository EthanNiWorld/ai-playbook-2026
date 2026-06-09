# DeepSeek（深度求索）公司分析报告

> **数据时效说明**：以下数据综合截至 2026 年 5 月的最新公开披露。DeepSeek 截至发稿仍为未上市公司，且历史上从未接受外部融资（首轮融资正在进行中），因此财务数据极度有限，主要基于媒体估算与第三方推测，**使用前请务必交叉验证**。文中已标注可信度分级。

## 一、公司概况

DeepSeek（全称：杭州深度求索人工智能基础技术研究有限公司）是中国最具影响力的开源大模型公司，由量化基金幻方量化创始人梁文锋于 2023 年创立。公司凭借 MLA（多头潜在注意力）、DeepSeekMoE 等原创架构创新和极致性价比的开源策略，在 2025 年 1 月引发全球 **"DeepSeek 时刻"**——R1 模型发布当天即导致 Nvidia 单日市值蒸发 5890 亿美元，DeepSeek App 登顶美国 App Store 下载榜[reference:0][reference:1]。

### 基本信息

**成立时间**：2023 年 7 月 17 日  
**总部**：中国浙江省杭州市  
**性质**：未上市私营公司（截至 2026.05，首轮外部融资进行中）  
**母体**：幻方量化（High-Flyer，量化对冲基金，梁文锋同为创始人）  
**创始人/CEO**：梁文锋（Liang Wenfeng）

---

## 二、创始团队与核心人物

### 2.1 创始人梁文锋

- 浙江大学信息与电子工程学系毕业
- 2008 年起带领团队使用机器学习探索全自动量化交易[reference:2]
- 2015 年创办 **幻方量化**（High-Flyer），管理规模一度达千亿人民币
- 2023 年创办 DeepSeek，以幻方自有资金注入，**不接受外部融资、不被商业化时间表绑架**
- 截至 2026 年 5 月，**最终受益股份约 84%**[reference:3]
- 公开曝光极少，几乎不接受媒体采访，被 BBC 称为"一夜成名的亿万富翁"[reference:4]
- 被 21 财经评价为"终于活成了山姆·奥尔特曼的样子"[reference:5]

### 2.2 团队特征

- 团队规模约 **150 人**（截至 2025 年初），为同体量影响力中最小的团队[reference:6]
- 高密度博士，核心成员来自浙大、北大、清华等顶校计算机系
- 研究文化浓厚：**不设产品经理**，所有人围绕模型研究展开工作
- 极简组织结构，类似学术研究院而非商业公司

---

## 三、愿景与使命

- **愿景**：Unravel the mystery of AGI with curiosity（以好奇心探索 AGI 的本质）[reference:7]
- **使命**：通过开源、开放的方式推动 AGI 研究，让所有人受益
- **核心理念**：
  - **"开源是信仰"**：所有核心模型（V2/V3/R1/V4）均完全开源，MIT 许可
  - **"算力不是壁垒，架构创新才是"**：用 600 万美元训练成本对标 5 亿美元级模型，颠覆"暴力堆算力"范式[reference:8]
  - **"商业化不是目标"**：梁文锋多次表态，公司定位为"纯粹的研究机构"[reference:9]
  - **"坚持 AGI 与开源，不因融资改变方向"**[reference:10]

---

## 四、企业文化

### 4.1 学术研究院式运作

- **不设 PM、不设 BD、不设市场部**：公司几乎 100% 是研究员和工程师
- **论文驱动**：每个核心模型版本都伴随完整技术报告发布（V2 Paper / V3 Paper / R1 Paper）
- **极致效率**：150 人团队产出的模型影响力对标数千人团队（OpenAI 600+ 人、Anthropic 800+ 人）

> ⚠️ **文化转变信号（2026-05）**：DeepSeek 开始公开招募 **Agent Harness 产品经理**和 R&D 工程师，"不设 PM" 的传统正在随着 Agent 产品化战略而改变。[reference:32]

### 4.2 "隐士"文化

- 创始人梁文锋极少公开露面，几乎不接受采访
- 公司没有官方媒体账号（仅技术博客和 API 文档）
- 不做市场推广，依赖模型质量和开源社区口碑自增长
- 被外界称为"AI 界的隐士"或"AI 界的少林寺"

### 4.3 组织规模

- 约 150 人（2025 年初）[reference:6]
- 融资后可能扩张，但梁文锋承诺"不改变 AGI 与开源方向"[reference:10]

---

## 五、关键产品矩阵（核心产品）

### 5.1 基础模型（V 系列 + R 系列）

**V 系列（通用旗舰）**

| 模型 | 发布时间 | 参数 | 核心特点 |
|------|---------|------|---------|
| **DeepSeek-V1** | 2024.01 | 67B | 首代开源通用模型 |
| **DeepSeek-V2** | 2024.05 | 236B MoE（21B 激活）| 首次引入 **MLA + DeepSeekMoE**，引发国产大模型"价格战"，被称为"价格屠夫"[reference:11] |
| **DeepSeek-V3** | 2024.12 | 671B MoE（37B 激活）| 训练成本仅 **557 万美元**，开源 SOTA，与 GPT-4o/Claude 3.5 同台竞技[reference:12] |
| **DeepSeek-V3-0324** | 2025.03.25 | 同上 | 借鉴 R1 推理能力增强 |
| **DeepSeek-V3.2** | 2025.12.01 | 同上 | V3 系列最终版 |
| **DeepSeek-V4-Pro** | **2026.04.24** | **1.6T MoE（49B 激活）** | 全能旗舰，**开源 SOTA**，Agentic Coding 超越 Sonnet 4.5，接近 Opus 4.6[reference:13] |
| **DeepSeek-V4-Flash** | **2026.04.24** | 284B MoE（13B 激活）| 极致高效轻量版 |

- V4 全系列支持 **1M 上下文**，均支持思考模式（含 reasoning_effort 参数）[reference:14]
- V4 明确与 **华为芯片** 合作[reference:13]

**R 系列（推理专项）**

| 模型 | 发布时间 | 核心特点 |
|------|---------|---------|
| **DeepSeek-R1** | **2025.01.20** | 纯强化学习（RL）自主激发推理能力，**GRPO 算法**，开源 MIT 许可，引发"DeepSeek 时刻"[reference:0] |
| **DeepSeek-R1-0528** | 2025.05.28 | 上下文 128K，幻觉率降低 45–50%，接近 o3 / Gemini 2.5 Pro |
| **R2**（传闻中）| 2026 年 | 下一代推理模型 [⚠️ 待验证] |

**其他模型线**

| 模型 | 发布时间 | 特点 |
|------|---------|------|
| **DeepSeek-Coder** 系列 | 2023.11 起 | 代码专项模型 |
| **DeepSeek-VL** 系列 | 2024 年 | 视觉语言模型 |
| **DeepSeek-Math** | 2024 年 | 数学推理 |
| **Janus** 系列 | 2024–2025 | 多模态理解与生成 |

### 5.2 DeepSeek App — C 端产品

- 类 ChatGPT 对话产品，集成 V4 + R1 双模型
- **2025.01.27** 登顶美国 App Store 免费下载第一名（超越 ChatGPT）[reference:1]
- DAU 高峰约 **2000 万**[reference:6]
- 商业化模式尚不明确，当前免费为主

### 5.3 API 开放平台（api.deepseek.com）

- 面向开发者与企业的 API 服务
- **定价极具竞争力**（被称为"价格屠夫"）：
  - V4-Pro（2.5 折特惠）：输入 0.25 元/百万 Token（缓存命中）、3 元/百万 Token（未命中）[reference:15]
  - V4-Flash 更便宜：输入缓存 **0.02 元/百万 Token**[reference:16]
  - 约为 Claude Opus 4.6 的 **1/5 价格**[reference:17]
- 被第三方大量接入（阿里百炼、火山引擎、AWS Bedrock 等均上架 DeepSeek 模型）

---

## 六、产品收入、DAU 与 ARR

### ⚠️ 数据可信度提示
> DeepSeek 从未披露过任何财务数据。以下所有数据均为 **媒体推测或第三方估算**，误差可能极大，**仅作参考**。

### 6.1 收入（极度有限的信息）

- **收入来源**：API 调用为主，C 端 App 尚未商业化[reference:8]
- **收入规模**：未披露，但按其定价策略（V4-Pro 约为 Claude 1/5 价格），即使 DAU 2000 万，API 收入规模可能相对有限
- **梁文锋态度**：多次表态"商业化不是目标"[reference:9]

### 6.2 用户与流量数据

| 指标 | 数据 | 说明 |
|------|------|------|
| DAU（高峰）| 约 **2000 万** | 2025.01 R1 发布后爆发[reference:6] |
| App Store 排名 | 全球 #1（Free）| 2025.01.27，超越 ChatGPT[reference:1] |
| 第三方接入 | 阿里百炼、火山引擎、AWS Bedrock 等 | API 被全球主流平台上架 |

### 6.3 成本与投入

- **V3 训练成本**：约 **557 万美元**（GPU 运算成本，不含研发人力）[reference:12]
- **GPU 集群**：约 2000–3000 张 H800 用于训练 V3[reference:18]
- **推理集群**：约 278 台 H800 服务器（2224 张 GPU）用于日常推理服务[reference:19]
- **满足 2000 万 DAU 估算需**：约 2.78 万张 GPU[reference:6]
- **硬件总投入**：约 **38 亿人民币**（媒体估算）[reference:6]

### 6.4 估值

| 阶段 | 估值 | 来源 |
|------|------|------|
| 2025 年初（R1 爆火后）| 未融资，市场传闻"拒绝数十亿美元估值" | [reference:5] |
| 2026.04（首轮融资传闻）| **不低于 100 亿美元**（约 682 亿人民币）| [reference:20] |
| 2026.05.08（最新传闻）| **约 500 亿美元**（约 3400 亿人民币）| [reference:3] |

> ⚠️ 融资尚未正式完成，最终估值以官方公告为准 [⚠️ 待验证]

---

## 七、算力部署与战略合作

### 7.1 算力规模

| 用途 | 规模 | 芯片 |
|------|------|------|
| V3 训练 | 约 2000–3000 张 H800 | Nvidia H800 |
| 日常推理 | 约 278 台服务器 / 2224 张 GPU | Nvidia H800 |
| DAU 2000 万满配 | 约 2.78 万张 GPU | 混合 |
| V4 训练 | 未披露 | H800 + **华为昇腾**[reference:13] |

### 7.2 算力战略特点

- **极致优化 > 暴力堆卡**：DeepSeek 的核心竞争力不是拥有最多 GPU，而是每张 GPU 的利用效率全球领先
- **PTX 层级优化**：超越 CUDA 标准编程接口，直接在 GPU 硬件指令层做优化[reference:21]
- **MLA 减少 KV-Cache**：相比传统 MHA，推理显存占用大幅降低，同等 GPU 数量可服务更多并发
- **与华为合作**：V4 明确宣布与华为芯片合作，推进国产化[reference:13]
- **算力成本颠覆性**：V3 训练仅 557 万美元 vs OpenAI GPT-5 预计数亿美元

### 7.3 战略合作关系

- **华为**：V4 明确与华为芯片合作[reference:13]
- **阿里云百炼**：DeepSeek 系列模型上架百炼 API 平台
- **火山引擎**：DeepSeek 系列模型上架火山方舟
- **AWS Bedrock**：DeepSeek R1 上架
- **幻方量化**：母体公司，提供初始资金与 GPU 资源

---

## 八、近期 CXO 核心观点精选

### 8.1 梁文锋（创始人 / CEO）

1. **"不接受外部融资，不稀释股权，不被任何人的商业化时间表绑架"**（2023–2025，核心信条）：从公司创立第一天划下的红线，直到 2026 年 4 月才首次松口[reference:9]
2. **"拿了上百亿美元投资也不改变方向——坚持 AGI 与开源"**（2026.05，融资谈判中态度强硬）：明确承诺融资不会改变公司基因[reference:10]
3. **"算力不是壁垒，架构创新才是"**（2024–2025）：用 557 万美元训练成本证明"暴力堆算力"范式不是唯一路径[reference:12]
4. **"AI 强大到不需要那么多算力"**（2025，被《自然》杂志引用）：MLA + MoE 双创新使推理效率提升数倍
5. **"开源是为了让所有人受益"**（2025，BBC 采访）：开源策略是信仰而非营销手段[reference:4]
6. **关于 AGI 时间线**（2026.04，罕见表态）：OFweek 报道称"没有人比梁文锋更清楚 AGI 有多远"[reference:22]

### 8.2 核心观点总结

梁文锋几乎不公开发表战略观点，其理念需从行动推断：
- **行动 1**：所有核心模型 MIT 开源 → 信仰"开源推动 AGI"
- **行动 2**：557 万美元训练 V3 → 信仰"效率 > 规模"
- **行动 3**：150 人团队 → 信仰"精英密度 > 人海战术"
- **行动 4**：不融资直到 2026 → 信仰"独立思考 > 资本驱动"

---

## 九、战略转型动态

### 9.1 2026 年关键变化

- **首轮融资即将落地**：估值 100–500 亿美元，拟筹 3 亿+ 美元，标志从"纯研究机构"向"有资本平台支撑的研究机构"转变[reference:3][reference:20]
- **V4 发布**：1.6T 参数旗舰 + 284B 轻量版双线发布，1M 上下文成为标配[reference:14]
- **明确与华为合作**：推进国产芯片路线，降低对 Nvidia H800 的依赖[reference:13]
- **沉默期结束**：从 V3.2（2025.12）到 V4（2026.04）间隔近 5 个月，是公司最长沉默期[reference:23]
- **Agentic 能力跃迁**：V4-Pro Agentic Coding 达到开源 SOTA，从"语言模型"走向"Agent 基座"[reference:13]
- **组建 Harness 团队（2026-05）**：公开招募 Agent Harness 产品经理和 R&D 工程师，正式启动桌面端 Agent 产品研发。内部对标 Claude Code，项目工作名 "Code Harness"（研究员陈德利公开确认）[reference:32]。标志着 DeepSeek 从"模型提供商"走向"Agent 产品公司"的战略拐点——Model + Harness = Agent 公式被内化为产品战略。

### 9.2 面临的核心挑战

1. **商业化悖论**：定价极低 + 免费 App + 开源 = 收入规模有限，而算力支出持续增长[reference:8]
2. **团队规模瓶颈**：150 人团队产出至今惊人，但 V4 级别模型的工程量可能需要扩编
3. **芯片供应**：中美芯片禁令下，H800 后续采购受限，华为昇腾兼容性仍需验证
4. **融资后的独立性**：梁文锋承诺"不改变方向"，但资本注入后能否保持"纯研究"文化存疑
5. **竞争白热化**：Qwen、GLM-5、MiniMax-M3 等国产同业持续逼近，国际上 Claude/GPT 仍是标杆
6. **Agent 产品化能力短板**：V4 模型能力强，但此前完全依赖第三方 Harness（DeepSeek-TUI、Deep Code CLI 等）定义用户体验；现在自建 Harness 团队，面临从"模型公司"到"产品公司"的组织能力转型挑战[reference:32]

### 9.3 V4 vs V3.2：Agent 场景的选型差异

V4 不是 V3.2 的常规升级，而是针对 Agent 长链路工作流的**定向修复**。在 AI Coding / 多 Agent 协作场景下，V4 的优势具有结构性意义。

**官方明确点名的 Agent 集成**（来自 DeepSeek 官方发布页[reference:28]）：
> *"DeepSeek-V4 is seamlessly integrated with leading AI agents like Claude Code, OpenClaw & OpenCode."*

**V3.2 在 Agent 场景的具体缺陷**（来自 HuggingFace 技术分析[reference:29]）：
> V3.2 在多轮工具调用中保留推理痕迹，但**遇到新的 user message 时会清空**。多轮 Agent 工作流中模型会丢失累积推理状态，必须从头重建。

**V4 三项 Agent 专项设计（针对已知失败模式的定向修复）**：

| 修复点 | V3.2 问题 | V4 方案 |
|------|------|------|
| 跨 turn 推理保留 | 新 user message 清空推理记录 | 含工具调用的对话中跨 user turn 保留完整推理链 |
| 工具调用格式 | JSON-in-string，嵌套转义易失败 | `\|DSML\|` 特殊 token + XML schema，区分 string / 结构化参数 |
| Agent 训练范式 | 合成数据为主 | DSec RL 沙盒（Rust + Firecracker），真实工具环境强化学习 |

**1M 上下文的计算效率（V4-Pro vs V3.2，相同硬件）**：

| 指标 | V3.2 | V4-Pro |
|------|:---:|:---:|
| 1M tokens 单 token 推理 FLOPs | 100% | **27%** |
| KV Cache 内存占用 | 100% | **10%** |

意义：1M 上下文不是"堆容量"，而是以更低成本跑更长 Agent 链路（每轮工具调用 I/O 都追加到上下文）。

**Agent Benchmark（V4-Pro-Max，来自 V4 技术报告）**：

| Benchmark | V4-Pro-Max | Claude Sonnet 4.5 | Claude Opus 4.6-Max |
|-----------|:---:|:---:|:---:|
| SWE Verified | 80.6 | — | 80.8 |
| MCPAtlas Public | 73.6 | — | 73.8 |
| Terminal Bench 2.0 | 67.9 | — | — |
| 内部 R&D Coding（PyTorch/CUDA/Rust/C++）| 67% | 47% | 70% |

**选型结论**：
- **AI Coding / 多 Agent 协作 / OpenClaw 生态等 Agent 场景** → 选 V4（V3.2 在跨 user turn 推理上有架构性硬伤）
- **纯对话 / 短链路 RAG / 一次性指令任务** → V3.2 仍可用，且推理成本更低

### 9.4 V4-Flash：V3.2 的官方继任者与 TPM 迁移注意事项

**V4-Flash 是 V3.2 的官方直接替代**（来自 DeepSeek 官方发布页[reference:28]）：
> *"deepseek-chat & deepseek-reasoner will be fully retired and inaccessible after Jul 24th, 2026. (Currently routing to deepseek-v4-flash non-thinking/thinking)."*

DeepSeek 已将 `deepseek-chat`（之前路由到 V3.2）自动切换路由到 V4-Flash。V4-Pro 是"升档"（旗舰级），不是"替代"。

**为什么 13B 激活参数能替代 37B**：

| 维度 | V3.2 | V4-Flash | V4-Pro |
|------|:---:|:---:|:---:|
| 参数总量 | 671B | 284B | 1.6T |
| 激活参数 | 37B | **13B** | 49B |
| 定位 | 通用日常 | 通用日常（继任者） | 旗舰/Agent 重场景 |
| 定价档位 | 中低 | 中低（同档） | 高 |

V4-Flash 的 CSA+HCA 混合注意力架构使得单 token FLOPs 降到 V3.2 的 10%、KV Cache 降到 7%[reference:29]，用架构效率换激活参数量，实现"小排量新引擎超越大排量旧引擎"。

**TPM 迁移陷阱：thinking mode 的隐性 Token 成本**：

百炼平台上 V4-Flash 与 V3.2 的默认 TPM 配额均为 1,200,000（模型独立限流）[reference:30]，提额操作数值上 1:1 平移。

但 **V4-Flash 默认开启 thinking mode**[reference:31]，thinking tokens 计入 output tokens 消耗 TPM：

| 模式 | 每个请求 output 构成 | 50M TPM 实际可用业务吞吐 |
|------|------|------|
| V3.2（无 thinking）| 回复 tokens 100% | 基准 100% |
| V4-Flash **non-thinking** | 回复 tokens 100% | ≈ 100%（与 V3.2 相当）|
| V4-Flash **thinking（默认）** | thinking + 回复 | **下降 50-80%**（thinking 通常占 2-5×）|

**迁移建议**：
- 不需要推理的场景：显式设置 `reasoning_effort: "none"` 关闭 thinking，保持与 V3.2 等效吞吐
- Agent / 复杂推理场景：保持 thinking 默认，但需重新评估 TPM 预算（实际吐量约为名义配额的 20-50%）
- V3.2 将于 **2026.07.24 完全下线**，迁移窗口明确

---

## 十、数据使用建议

1. **DeepSeek 从未披露任何财务数据**（收入、ARR、利润），所有财务估算均为第三方推测，**不可用于正式投资报告**。
2. **估值数据**（100–500 亿美元）为融资传闻，以最终官方公告为准。
3. **GPU 数量与训练成本**主要来自技术报告（V3 Paper 自称 557 万美元）和媒体估算，有一定可信度但精确数字存疑。
4. **若用于正式报告**，建议引用 DeepSeek 官方技术报告（arxiv）和一手媒体（The Information、Bloomberg、BBC）报道。

---

## 十一、DeepSeek 核心论文与影响力分析

### 核心研究脉络

DeepSeek 的研究主线为 **"架构创新 → 效率革命 → 推理能力涌现"**，核心贡献者为梁文锋领导的约 150 人团队。

**三大原创架构贡献**：

| 创新 | 核心思想 | 影响 |
|------|---------|------|
| **MLA（Multi-head Latent Attention）** | 将 KV-Cache 压缩为低秩潜在向量，推理显存减少 93%，计算效率提升 2–4× | 改写了大模型推理成本公式[reference:24] |
| **DeepSeekMoE** | 改进专家路由机制，更细粒度的专家划分 + 共享专家池 | 同参数量下激活量大幅减少，训练/推理成本双降[reference:25] |
| **GRPO（Group Relative Policy Optimization）** | R1 核心算法：无需 SFT 监督数据，纯 RL 自主激发推理能力 | 证明"推理能力可通过强化学习涌现"[reference:0] |

### 标志性论文与模型

| 论文 / 模型 | 时间 | 核心贡献 |
|------------|------|----------|
| **DeepSeek-V2: A Strong, Economical, and Efficient MoE Language Model** | 2024.05 | 首次将 MLA + DeepSeekMoE 合体，236B 参数但仅激活 21B，训练成本为同级模型 1/10[reference:11] |
| **DeepSeek-V3 Technical Report** | 2024.12 | 671B MoE 全开源，训练仅 557 万美元，性能对标 GPT-4o / Claude 3.5 Sonnet[reference:12] |
| **DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning** | **2025.01.20** | 纯 RL 激发推理，GRPO 算法，MIT 开源；引发全球"DeepSeek 时刻"，Nvidia 单日市值蒸发 5890 亿美元[reference:0][reference:1] |
| **DeepSeek-V4 Technical Report** | 2026.04 | 1.6T/284B 双版本，1M 上下文，Agentic Coding 开源 SOTA，明确华为芯片兼容[reference:13][reference:14] |
| **DeepSeek-Coder** 系列 | 2023–2024 | 代码领域早期代表作 |
| **DeepSeek-Math** | 2024 | 数学推理 SOTA |
| **Janus** 系列 | 2024–2025 | 多模态理解与生成 |

### "DeepSeek 时刻" 的全球影响

- **2025.01.20–27**：R1 发布 → App 登顶美国 App Store → Nvidia 市值单日蒸发 **5890 亿美元**（史上最大单日跌幅）
- **被《自然》杂志称为"又一个 DeepSeek 时刻"**[reference:26]
- **颠覆了全球对"AI 必须依赖美国顶级算力"的认知**[reference:27]
- **硅谷恐慌**：多家硅谷公司重新评估模型训练效率，"DeepSeek 恐慌"成为流行词[reference:17]
- **开源信仰落地**：R1 MIT 许可，被全球数百个项目直接使用或蒸馏

### 行业影响力

- **"效率革命"范式定义者**：用 557 万美元训练成本证明"暴力堆算力"不是唯一路径，永久改变了行业对模型训练成本的预期
- **开源 SOTA 标杆**：V3、R1、V4 连续三代在开源领域达到 SOTA，与闭源头部（GPT / Claude）直接竞争
- **架构创新输出**：MLA 和 DeepSeekMoE 被 Kimi K2、Yi-Lightning 等多个国产模型引用/采用[reference:26]
- **GPU 市场格局影响**：R1 发布直接导致 Nvidia 市值蒸发 5890 亿美元，迫使芯片厂商重新思考 AI 芯片定位
- **全球 AI 政策讨论**：DeepSeek 的成功使"中国 AI 威胁论"成为美国国会与欧洲监管层的高频议题
- **梁文锋个人影响力**：从"无名量化基金经理"到"全球 AI 最有影响力的人物之一"，BBC、NYT、Bloomberg 等均做长篇专访

---

## 十二、公司发展里程碑（Milestone）

| 时间 | 事件 | 备注 |
|------|------|------|
| **2015** | 梁文锋创办 **幻方量化**（High-Flyer）| 量化对冲基金，管理规模一度达千亿 |
| **2023.07.17** | **杭州深度求索** 正式注册成立 | 以幻方自有资金启动，不接受外部融资 |
| **2023.11** | 发布 **DeepSeek-Coder-1.0** | 首个产品，代码领域切入 |
| **2024.01** | 发布 **DeepSeek-V1**（67B）| 首代通用大模型 |
| **2024.05** | 发布 **DeepSeek-V2**（236B MoE）| 首次引入 **MLA + DeepSeekMoE**，引发"价格战"[reference:11] |
| **2024.08** | 发布 **DeepSeek-VL** / **DeepSeek-Math** | 多模态与数学推理 |
| **2024.12** | 发布 **DeepSeek-V3**（671B 开源旗舰）| 训练仅 557 万美元，全球震动[reference:12] |
| **2025.01.20** | 发布 **DeepSeek-R1**（开源 MIT）| **"DeepSeek 时刻"**：纯 RL 推理，GRPO 算法[reference:0] |
| **2025.01.27** | DeepSeek App **登顶美国 App Store 第一** | 超越 ChatGPT，Nvidia 市值单日 -5890 亿美元[reference:1] |
| **2025.03** | 传出腾讯、阿里等洽谈融资 | 梁文锋拒绝[reference:5] |
| **2025.03.25** | 发布 **V3-0324** 更新版 | 借鉴 R1 推理能力 |
| **2025.05.28** | 发布 **R1-0528** 更新版 | 上下文 128K，幻觉率 -45–50% |
| **2025.12.01** | 发布 **DeepSeek-V3.2** | V3 系列最终版 |
| **2026.04.24** | 发布 **DeepSeek-V4**（Preview 双版本）| V4-Pro 1.6T / V4-Flash 284B，1M 上下文，明确华为芯片[reference:13][reference:14] |
| **2026.04** | 传出 **首轮融资** 消息 | 目标估值 ≥100 亿美元，拟筹 ≥3 亿美元[reference:20] |
| **2026.05.08** | 融资估值传闻升至 **500 亿美元** | 约 3400 亿人民币[reference:3] |
| **2026.05** | **组建 Harness 团队**，公开招募 Agent Harness PM + R&D 工程师 | 内部对标 Claude Code，项目工作名 "Code Harness"[reference:32] |

---

*最后更新：2026 年 6 月 9 日 | 基于公开报道与技术报告整理*

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-05-22 | 初始创建，新增 DeepSeek 公司分析报告 |
| 2026-05-27 | 合并 ai-native-expert 沉淀：新增 9.3「V4 vs V3.2 Agent 场景选型差异」，含 OpenClaw 集成、跨 turn 推理修复、DSML 工具调用格式、Agent benchmark；新增 reference 28-29 |
| 2026-05-27 | 合并 ai-native-expert 沉淀：新增 9.4「V4-Flash：V3.2 的官方继任者与 TPM 迁移注意事项」，含官方路由切换证据、thinking mode TPM 陷阱、迁移建议；新增 reference 30-31 |
| 2026-06-09 | 新增：§4.1 PM 文化转变注释、§9.1 Harness 团队组建、§9.2 Agent 产品化能力短板挑战、里程碑表追加 2026.05 Harness 团队条目；新增 reference 32-33 |

## 参考来源

- [reference:0] DeepSeek 官方 / arxiv — R1 论文：Incentivizing Reasoning via RL
- [reference:1] BBC / NYT — 2025.01.27 DeepSeek App 登顶 App Store，Nvidia 市值蒸发 5890 亿
- [reference:2] 维基百科 — 深度求索词条
- [reference:3] 新浪财经 — 2026.05.08 估值 500 亿美元传闻
- [reference:4] BBC — 梁文锋专访"从量化基金到聊天机器人投资者"
- [reference:5] 21 财经 — "梁文锋终于活成了山姆·奥尔特曼的样子"
- [reference:6] 太平洋科技 — 团队 150 人、DAU 2000 万、2.78 万张 GPU 估算
- [reference:7] DeepSeek 官网 — 公司愿景
- [reference:8] 知乎专栏 — "用 600 万打败 5 亿：DeepSeek 如何重写 AI 游戏规则"
- [reference:9] 新浪财经 — "不接受外部融资，不被商业化时间表绑架"
- [reference:10] 快科技 — "拿了上百亿美元投资也坚持 AGI 与开源"
- [reference:11] 36 氪 / 媒体 — V2 首引 MLA + MoE，引发价格战
- [reference:12] DeepSeek V3 Technical Report — 训练成本 557 万美元
- [reference:13] 量子位 — V4 发布，明确华为芯片合作
- [reference:14] 知乎 — V4 双版本 1M 上下文、思考模式
- [reference:15] 21 财经 — V4-Pro API 2.5 折定价
- [reference:16] 证券时报 — V4-Flash 缓存价格 0.02 元/百万 Token
- [reference:17] 新浪财经 — "以 Claude Opus 4.6 五分之一的价格提供接近顶尖能力"
- [reference:18] Instagram / 日媒 — V3 训练约 2000-3000 张 H800
- [reference:19] 东方财富研报 — 278 台 H800 服务器推理
- [reference:20] OFweek / 证券时报 — 首轮融资传闻，估值≥100 亿美元
- [reference:21] AMD 相关报道 — DeepSeek PTX 层级 GPU 优化
- [reference:22] OFweek — "没有人比梁文锋更清楚 AGI 有多远"
- [reference:23] 36 氪 — "沉默了五个月的 DeepSeek"
- [reference:24] CSDN / 知乎 — MLA 技术解读
- [reference:25] 36 氪 / 知乎 — DeepSeekMoE 技术解读
- [reference:26] 钛媒体 / 《自然》— "又一个 DeepSeek 时刻"
- [reference:27] 超智咨询 — "迫使全球重新评估 AI 必须依赖美国顶级算力"
- [reference:28] DeepSeek 官方发布页 — V4 与 Claude Code / OpenClaw / OpenCode 集成；`deepseek-chat` 将于 2026.07.24 下线，已路由到 V4-Flash（https://api-docs.deepseek.com/news/news260424）
- [reference:29] HuggingFace 官方博客 — DeepSeek-V4: a million-token context that agents can actually use（https://huggingface.co/blog/deepseekv4）
- [reference:30] 阿里云百炼限流文档 — deepseek-v4-flash / deepseek-v3.2 默认 TPM 均为 1,200,000（https://help.aliyun.com/zh/model-studio/rate-limit）
- [reference:31] DeepSeek 官方定价页 — V4-Flash 默认 thinking mode、并发限制 2500（https://api-docs.deepseek.com/quick_start/pricing）
- [reference:32] 36氪 — DeepSeek 智能体产品要来了：组建 Harness 团队，对标 Claude Code（https://eu.36kr.com/en/p/3818407956366208）
- [reference:33] Verdent AI — DeepSeek's Coding Plan: V4, Harness Team, and 2026 Roadmap（https://www.verdent.ai/zh-CN/guides/deepseek-coding-plan-2026）
