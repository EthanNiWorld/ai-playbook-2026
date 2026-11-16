# Google TPU（第八代：8t / 8i / 8tx / 8i Max）

> 最后更新: 2026-11-13
> 所属厂商: Google
> 产品类别: AI 基础设施（计算）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: Google 自研 AI 加速器第八代四系统——8t（训练）/ 8i（实时推理）/ 8tx（机密推理）/ 8i Max（超长上下文+密度），"一年四款"为 TPU 史上首次（官方原文背书）；战略主线"未来将属于专业化"：共同硅基 + 系统级重组合，月级 SKU 迭代
**适用**: 大规模训练、生产级低延迟推理、受监管客户敏感数据后训练（微调/蒸馏/agent RL）、百万 token 级长上下文推理
**不适用**: 8tx/8i Max 尚未 GA（2027 上市，仅高管采访口径，售前不可承诺 2026 可得）；非 GCP 生态；CUDA 深度绑定的存量负载（迁移成本待评估）
**竞品**: NVIDIA GPU（H100/Blackwell Confidential Computing、Blackwell/Rubin 双 die）
**常搭配**: Vertex AI / GKE / Axion ARM 主机（8t/8i）/ 第五代 AMD EPYC（8tx）/ TorchTPU + vLLM/SGLang 开放栈
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

第八代 TPU 从"训练/推理"二分扩展为**按 AI 生命周期切片的四系统**：8t 训练、8i 实时推理、8tx 机密推理、8i Max 超长上下文。官方原文 "This is the first time we have introduced four TPU systems in a single year"（2026-11-09 博文，Amin Vahdat 署名）。

### 底层原理（通俗版）

**家族谱系**（第七代为 Ironwood / TPU7x，Cloud TPU 文档口径；命名 t=training、i=inference 由官方描述支撑，x 官方未给字母释义但定位 secure/confidential inference，Max=双芯片最大配置）：

| 系统 | 定位 | 关键规格（官方） | 状态 |
|---|---|---|---|
| **8t** | 训练 | 较上代训练性能至多 2.7 倍；单 superpod 9,600 芯片、2PB 共享 HBM、121 ExaFLOPS、Virgo 网络、百万芯片近线性扩展、>97% goodput、OCS；Axion ARM 主机 | 2026-04 Cloud Next 首发，2026 年内 GA |
| **8i** | 实时推理 | 推理性价比提升 80%；288GB HBM + 384MB 片上 SRAM（上代 3 倍，官方明言"按生产级推理模型 KV cache 占地设计"）；ICI 带宽翻倍至 19.2 Tb/s；Boardfly 网络直径减半；CAE 片上延迟至多降 5 倍；Axion ARM 主机 | 2026-04 Cloud Next 首发，2026 年内 GA |
| **8tx** | 机密推理 | **与 8t 相同硅片**（"Built on the same silicon as TPU 8t"）+ 第五代 AMD EPYC 主机 + Boardfly 低延迟网络；硬件级安全使数据与权重在活跃使用中受保护隔离；较 8t 延迟至多低 2 倍、性能损失近零；单系统内完成私有数据微调/蒸馏/agent RL，敏感数据不出域 | 2026-11-09 公布，2027 上市（采访口径） |
| **8i Max** | 超长上下文+密度 | **两颗 8i 同封装**，算力/SRAM/HBM 带宽均翻倍；既有机柜占地容纳两倍硅片 → 每平方英尺/每瓦算力显著提升；定位"海量上下文窗口与单柜最高算力密度" | 2026-11-09 公布，2027 上市（采访口径） |

> 两代际性能每瓦提升至多 2 倍（vs Ironwood，4 月官方口径）。TPU 业务官方口径：**近 100 家客户**（前沿实验室、交易公司、零售、高校等）。

**"新芯片 vs 新系统"**（官方博文 "Building the computer around the chip" 一节）：新芯片受多年制造周期约束；新系统是围绕芯片重组合封装/高速内存/光网络/安全，可在**数月而非数年**交付——8tx/8i Max 并非全新芯片设计，而是现有硅片的系统级重配置。这是"月级 SKU 迭代"对 NVIDIA"年度单片节奏"的差异化。

**"专业化"战略**（Vahdat 彭博受访原话，经 Quartz/Deccan Chronicle 等多源交叉验证）："This really follows the thesis that we have here at Google, which is that **the future is going to be about specialization, and the upsides for specialization continue to be significant**." 官方博文与采访共同指向：在通用 GPU 年度单片节奏之外，用"共同硅基 + 系统级重组合"按 AI 生命周期切片售卖（训练/低延迟推理/机密/长上下文+密度）；对 NVIDIA 的竞争意义不在峰值算力而在 **TCO 与场景契合度**。真正攻击 NVIDIA 护城河的是 **TorchTPU 开源 + vLLM/SGLang 官方后端**——TPU 历史最大采用障碍是 JAX 生态锁定，PyTorch 原生化直接拆除迁移成本。

**为什么是机密计算（8tx）**：常规加密覆盖静态与传输态，**计算态数据必须在内存中明文解密**——机密计算把保护下沉到硬件层（TEE 思路），消灭这一缺口。配第五代 AMD EPYC（SEV-SNP 机密 VM 能力，x86 机密计算生态与企业认证最成熟；注意 8t/8i 官方配 Google 自研 Axion ARM 主机，8tx 换 AMD 属有意为之）。对标 NVIDIA H100（2022 起 Confidential Computing：GPU TEE + CPU TEE 配对 + 远程证明）/Blackwell 延续，属 **📋 跟进对齐**（NVIDIA 先行）；Google 差异点 = **训练级算力（8t 硅片）+ 推理网络（Boardfly）合一**，单系统完成微调→蒸馏→agent RL 闭环且敏感数据不出域，瞄准金融/医疗/政务受监管客户的云端后训练合规刚需——这是 agent RL 时代新增的合规需求，非通用算力升级。

**为什么是双 die（8i Max）**：百万 token 级上下文 decode 是**访存受限**（KV cache 读取主导），HBM 带宽与片上 SRAM 才是长上下文吞吐瓶颈，算力同步翻倍只为保证数据供给不空转。对标 NVIDIA Blackwell 双 reticle die（2024 已交付）/Rubin 传闻双 die，属 **📋 跟进对齐**；Google 场景化差异 = 把翻倍预算全押**带宽/SRAM（上下文）与单柜密度**。工程价值：**电力而非芯片供给已是数据中心硬约束**（4 月官方原话 "power, not just chip supply, is a binding constraint"），同功耗翻倍密度 = 不新增供电合同的前提下扩产推理容量。

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 8tx/8i Max 可得性 | 2027 上市 | 仅 Vahdat 彭博受访口径（Quartz 等多源交叉），官方博文未给时间；非 GA，售前不可承诺 2026 可得 |
| 绝对算力数字 | 未官方确认 | "Rubin ~35 / 8i ~10 / 8i Max ~20 PFLOPS" 为流出数据，两家公司均未官方确认；官方仅相对指标（翻倍等） |
| 成本/销售额对比 | 分析师估算 | "较 NVIDIA 低 ~30%"、"销售额 $12B(2026)→$135B+(2028)" 为彭博行业研究分析师估算，非 Google 官方指引 |
| 生态迁移 | 历史 JAX 锁定 | TorchTPU 开源（PyTorch 原生）+ vLLM/SGLang 官方后端正在拆除，存量 CUDA 负载迁移成本仍需评估 |

## 适用边界分析

### ✅ 适用场景

| 场景 | 说明 | 典型客户/案例 |
|------|------|--------------|
| 大规模训练 | 8t superpod 百万芯片近线性扩展、>97% goodput | 前沿实验室（官方称近 100 家客户） |
| 生产级低延迟推理 | 8i Boardfly + CAE，性价比 +80% | 交易公司、零售 |
| 受监管敏感数据后训练 | 8tx 单系统微调/蒸馏/agent RL，数据不出域 | 金融/医疗/政务 |
| 超长上下文推理 | 8i Max 带宽/SRAM 翻倍，单柜最高密度 | 百万 token 级 agent 负载 |

### ❌ 不适用场景

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 2026 年内需要 8tx/8i Max | 尚未 GA（2027 采访口径） | 8t/8i（2026 年内 GA）或 NVIDIA GPU |
| 非 GCP 生态 | TPU 仅 GCP 提供 | NVIDIA GPU（多云）/ AWS Trainium |
| 存量 CUDA 深度绑定负载 | 迁移成本（TorchTPU 正在降低） | 评估 TorchTPU/vLLM 后端后再决策 |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| "8tx/8i Max 是全新芯片" | 官方明确为现有硅片的系统级重配置（8tx 与 8t 同硅片；8i Max 为两颗 8i 同封装） |
| "一年四款是媒体说法" | 官方博文原文背书 "first time…four TPU systems in a single year" |
| "TPU 只是谷歌自用" | 官方称近 100 家外部客户；TorchTPU/vLLM/SGLang 开放栈拆除 JAX 锁定 |
| "2027 上市是官方文档承诺" | 仅 Vahdat 彭博受访表述，官方博文未给时间，属高管公开表态非文档字段 |
| "成本低 30% 是官方口径" | 彭博行业研究分析师估算，非 Google 官方指引 |

## 关键配置与最佳实践

**官方软件栈**（2026-11-09 博文）：
- **TorchTPU 开源**：PyTorch 原生跑 TPU 无需改代码 + vLLM/SGLang 官方 TPU 后端
- **TPU agent suite**（Preview）：接入 Claude Code/Cursor/Google Antigravity，自然语言自动调优
- **XLA Serving Engine**：C++ 低延迟运行时，跨 TPU/GPU/CPU；InferenceX/AgentX benchmark 上 vLLM-TorchTPU 栈宣称 SOTA 性价比
- **Agent Compute Engine**：agent 等待工具/人工时自动挂起恢复会话，省闲置算力
- **TPU Sync 模型状态层**：HBM/DRAM/共享存储/网络统一为内存层级，KV cache 毫秒级下片、PD 分离流式传输、RL 权重同步；官方宣称 KV 传输延迟与 TTFT 降超 90%
- **Cloud Pathways GA**：GKE 单控制器编排多 slice，亚分钟热切换
- **GKE 动态切分**：OCS 光路交换，超切分/子切分；官方口径作业启动快至 5 倍、故障恢复快至 4.5 倍

### 踩坑记录

| 问题 | 原因 | 解决方案 | 记录日期 |
|------|------|----------|----------|
| 把流出 PFLOPS 当官方规格 | 媒体/流出数据未经官方确认 | 仅引用官方相对指标；绝对数字标注"流出待确认" | 2026-11-13 |
| 把分析师估算当官方指引 | 彭博行业研究 ≠ Google 官方 | 成本/销售额对比显式标注"分析师估算" | 2026-11-13 |
| 把 2027 上市当 GA 承诺 | 高管采访口径非文档字段 | 售前不可承诺 8tx/8i Max 2026 可得 | 2026-11-13 |

## 竞品快速对照

| 维度 | Google TPU 第八代 | NVIDIA GPU |
|------|--------|-------|
| 机密计算 | 8tx（硬件 TEE + AMD EPYC，2027） | H100 CC（2022 起）/ Blackwell CC，先行 |
| 双 die 封装 | 8i Max（两颗 8i，带宽/SRAM 翻倍，2027） | Blackwell 双 reticle die（2024 已交付），先行 |
| 迭代节奏 | 共同硅基 + 系统重组合，月级 SKU | 年度单片节奏 |
| 生态 | TorchTPU/vLLM/SGLang 开放栈（拆除 JAX 锁定） | CUDA 生态锁定（护城河） |
| 长上下文 | 8i Max 押注 HBM 带宽/SRAM + 单柜密度 | Rubin 传闻双 die（未官方确认） |

> 平台侧对照见 [vertex-ai.md](vertex-ai.md) 竞品快速对照表（自研芯片行已同步四系统口径）。

## 参考资料

- https://blog.google/innovation-and-ai/infrastructure-and-cloud/global-network/tpu-8i-max-and-8tx/ （官方公告全文，2026-11-09，Amin Vahdat 署名，SVP and Chief Technologist, AI and Infrastructure）
- https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/eighth-generation-tpu-agentic-era/ （4 月 8t/8i 官方公告全文）
- https://cloud.google.com/tpu （官方产品页，已收录 8tx/8i Max；直连超时经搜索快照确认）
- https://docs.cloud.google.com/tpu/docs/release-notes （Ironwood = 第七代 TPU7x 口径）
- Bloomberg《Google Escalates Nvidia Rivalry With New Versions of Its TPU Systems》2026-11-09（付费墙未直抓全文，标题与引语经搜索快照核验）
- Quartz / Deccan Chronicle / readprism 等英文媒体对彭博采访的独立转述（2027 上市与 specialization 引语交叉验证）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-11-13 | 新建：inbox/ai-knowledge-by-qoder-ai-native-agent-20261113.md（TPU 条目）- 第八代四系统全规格/官方软件栈/机密计算与双 die 原理/专业化战略入库；信源从中财网转彭博升级为 blog.google 官方双公告直抓 + 彭博引语英文原文多源交叉；分析师估算与流出 PFLOPS 维持降级标注；2027 上市维持采访信源分级 |