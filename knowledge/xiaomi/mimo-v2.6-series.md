# MiMo-V2.6 系列（小米）

> 最后更新: 2026-10-19
> 所属厂商: 小米（Xiaomi MiMo）
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 小米原生全模态开源 MoE 系列，以「规模化强化学习 + 极致 token 效率 + MIT 开源」为差异化，官方叙事为"Scaling RL Towards Self-Improvement"
**当前主推**: MiMo-V2.6-Pro（旗舰，1.02T/42B）/ MiMo-V2.6-Flash（走量高效，309B/15B，1M 上下文，$0.14/$0.28）
**适用**: agentic 工作流（可重试、成功标准宽松）、多模态长文档/长视频理解、私有化部署（172.9GB FP8）、高并发批处理
**不适用**: 知识问答与事实核查（AA-Omniscience −13）、低延迟交互（TTFT 5.19s / 50 tok/s）、高价值安全任务（弱于 Pro 约 3 倍）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **MiMo-V2.6-Pro** 🚩 | 旗舰、能力上限 | 1M | 1.02T 总参 / 42B 激活、70 层（60 SWA + 10 全局）、384 路由专家 top-8、5 层 MTP（一次前向预测 7 token） | 2026-09-21/22 |
| **MiMo-V2.6-Flash** | 走量、高效推理 | 1M | 309B 总参 / 15B 激活、48 层（39 SWA + 9 全局）、256 路由专家 top-8、原生全模态 | 2026-09-21/22 |
| MiMo-V2.6-Pro-Ultraspeed | [⚠️ 待补充] | [⚠️ 待补充] | 具体规格与定价 [⚠️ 待补充] | 2026-09 |

> 📌 **发布口径**：权重 2026-09-21 上线 Hugging Face（与 Pro 相隔 18 秒），官方博客 09-22 发布；本表取官方发布日。
> 📌 **历史模型**：MiMo V2.5 全系仍被 Token Plan 覆盖，具体型号与规格本素材未提供，[⚠️ 待补充]。

### MiMo-V2.6-Flash

- **模型**：MiMo-V2.6-Flash（`mimo-v2.6-flash`）
- **公司**：小米（Xiaomi MiMo）
- **时间**：2026 年 9 月 21 日开源 / 9 月 22 日官宣
- **尺寸**：309B 总参 / 15B 激活
- **架构**：MoE，48 层（39 层滑动窗口注意力，窗口仅 128 token；9 层全局注意力），hidden 4096，256 路由专家 top-8、**无共享专家**；多模态编码器 ViT 681M + 音频 tokenizer 308M + 音频 patch 编码器 127M
- **上下文 / 输出**：1M / 128K tokens
- **多模态**：原生全模态输入（文本 + 图像 + 视频 + 音频）→ 文本输出
- **推理控制**：thinking 开关、工具调用、结构化输出、联网搜索、上下文缓存、流式输出
- **协议**：OpenAI 兼容 + Anthropic 兼容，现有项目改 `base_url` 与 `model` 即可迁移
- **开源**：MIT，FP8 权重 172.9GB / 65 分片，无需门控审批
- **限额**：RPM 100 / TPM 10M
- **订阅**：Token Plan（包月/包年）覆盖 Pro / Flash 及 V2.5 全系，另可按量计费
- **定价**：¥1 输入 / ¥2 输出 / ¥0.02 缓存命中；$0.14 / $0.28 / $0.0028（每百万 tokens）
- **场景**：专业办公高频调用、多 Agent 协同、多模态混合输入、可自部署的 agentic 工作流

### MiMo-V2.6-Pro

- **模型**：MiMo-V2.6-Pro
- **尺寸**：1.02T 总参 / 42B 激活
- **架构**：MoE，70 层（60 层 SWA + 10 层全局注意力），384 路由专家 top-8，5 层 MTP 投机解码
- **上下文 / 输出**：1M / 128K tokens
- **多模态**：原生全模态
- **开源**：MIT
- **定价**：[⚠️ 待补充]
- **定位**：错误代价高、部分答案无价值的任务——漏洞利用开发、安全审查、多步状态终端会话

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 原生全模态 | 文本/图像/视频/音频联合输入，1M 上下文适配会议录像、监控流、长视频理解 |
| Agentic 任务 | AA 独立实测 AutomationBench-AA 64%、Terminal-Bench 4.0 23%、AA-Briefcase 1491，均高于同分的 GPT-6 Luna |
| 高性价比 | AA 每任务成本 $0.06，输出价 $0.28（GPT-6 Luna $0.50）；训练成本约 85 万美元 / 6 天 |
| 开源可自部署 | MIT + 172.9GB FP8，小团队可在租用算力上自托管 |
| Harness 协同 | 基于真实 Harness 环境优化，适配 MiMo Desktop / MiMo Claw 等 Agent Harness |
| RL 方法论 | You Only RL Once：四域 + 多 harness 混训，单步 25088 条轨迹，GRS/GAR/MOPD2 提升反馈密度 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 知识可靠性 | AA-Omniscience **−13** | 答错多于答对，事实性任务需外挂 RAG/搜索 |
| 专业文档推理 | GDP.pdf **9%** | 明显弱于 GPT-6 Luna（23%） |
| Token 效率 | 78k tokens / 任务 | 为 GPT-6 Luna 的 1.56 倍，按量计费账单被放大 |
| 输出速度 / 延迟 | 49.8 tok/s / TTFT 5.19s | 不适合交互式低延迟场景 |
| 高价值安全任务 | ExploitGym 6.0（Pro 17.8） | 与 Pro 差约 3 倍，安全类任务应选 Pro |

### 与同档模型的独立对比（AA v4.3.2）

| 指标 | MiMo-V2.6-Flash | GPT-6 Luna (Max) |
|------|-----------------|------------------|
| Intelligence Index | 38 | 38 |
| AutomationBench-AA | 64% | 53% |
| Terminal-Bench 4.0 | 23% | 13% |
| AA-Briefcase | 1491 | 1335 |
| GDPval-AA v2.1 | 1608 | 1432 |
| HLE | 35% | 39% |
| GDP.pdf | 9% | 23% |
| AA-LCR v1.1 | 74% | 83% |
| AA-Omniscience | −13 | +1 |
| 每任务成本 | $0.06 | $0.07 |
| 输出速度 | 50 tok/s | 129 tok/s |

> 同为 38 分的第三方参照：Step 5 Preview AA 指数 44、每任务成本 $1.03（素材仅提供这两项，其余待补充）。

> 结论：Flash 与 Luna **同分不同命**——Flash 是「agentic + 全模态 + 可自部署」的轻量档，Luna 是「知识型 + 高速 + 低延迟」的轻量档，选型应按任务类型而非指数分。完整 GPT-6 Luna 侧数据见 [GPT-6 系列](../openai/gpt-6-series.md)。

## 定价概览

| 模型 | 输入价格 | 输出价格 | 缓存命中 | 备注 |
|------|---------|---------|---------|------|
| **MiMo-V2.6-Flash**（国内） | ¥1 / 1M | ¥2 / 1M | ¥0.02 / 1M | 按量计费；另有 Token Plan 订阅 |
| **MiMo-V2.6-Flash**（海外） | $0.14 / 1M | $0.28 / 1M | $0.0028 / 1M | 约为 Pro 的 1/3.1 |
| **MiMo-V2.6-Pro** | [⚠️ 待补充] | [⚠️ 待补充] | [⚠️ 待补充] | — |
| MiMo-V2.6-Pro-Ultraspeed | [⚠️ 待补充] | [⚠️ 待补充] | [⚠️ 待补充] | — |

> 定价来源：[官方模型页](https://mimo.mi.com/models/zh-CN/mimo-v2.6-flash)，核实日期 2026-10-19。Token Plan 覆盖 Pro / Flash 及 V2.5 全系。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 高吞吐 agentic 工作流 | Flash | 检索、分类、常规编辑、可重试调用；AutomationBench-AA 64% |
| 多模态长文档 / 长视频 / 会议理解 | Flash | 原生音视频输入 + 1M 上下文 |
| 私有化部署 / 数据不出域 | Flash | MIT + 172.9GB FP8，单机 8 卡级 |
| 高并发批处理 | Flash | RPM 100 / TPM 10M；Token Plan 覆盖高用量 |
| 漏洞利用开发 / 安全审查 / 多步终端 | Pro | 高价值安全任务与 Flash 差 3 倍（ExploitGym 17.8 vs 6.0） |
| 成本敏感的模型 × Harness 一体化 | Flash | 与 MiMo Desktop / MiMo Claw 协同调优 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 知识问答 / 事实核查 | AA-Omniscience −13，幻觉惩罚大于正确收益 |
| 专业文档深度推理（财报/合同） | GDP.pdf 9%，需外挂 RAG 或改用知识型模型 |
| 交互式低延迟对话 | TTFT 5.19s、输出 49.8 tok/s |
| 高价值安全任务 | 应选 Pro（ExploitGym 3 倍差距） |
| 依赖多服务商容灾 | 独立服务商极少，主要经小米自家平台 |

## 关键技术论文

- **MiMo-V2.6: Scaling Reinforcement Learning Towards Self-Improvement**（Xiaomi LLM-Core Team，arXiv:2610.11959，2026-10-08）
  - 三条扩展轴：① 更大 batch 与更高吞吐（异步训练，单步 1568 样本、2.7–3.7B tokens，上下文最长 1M）② 更多样环境（代码/通用/视觉/网络安全 × 多 harness）③ 更多 grader 算力（groupwise agentic grading）
  - 稳定性：冻结 MoE router + 多层 reward hacking 防御
  - 基础设施：统一轨迹表示、高并发多框架 rollout、控制面/数据面解耦、训练-推理一致性
  - 开源：training dynamics、RL environments、RL framework 一并开放

## 参考资料

- [MiMo-V2.6-Flash 官方模型页](https://mimo.mi.com/models/zh-CN/mimo-v2.6-flash)（规格、定价、限额、接入方式）
- [小米 MiMo-V2.6 官方博客](https://mimo.xiaomi.com/mimo-v2-6)（系列发布）
- [MiMo 官方新闻 / 模型列表](https://mimo.mi.com/docs/zh-CN/news)（训练成本与通过率提升）
- [arXiv:2610.11959 — MiMo-V2.6: Scaling RL Towards Self-Improvement](https://arxiv.org/abs/2610.11959)（2026-10-08）
- [Hugging Face: XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL)（MIT，FP8 权重）
- [Artificial Analysis — MiMo-V2.6-Flash vs GPT-6 Luna](https://artificialanalysis.ai/zh/models/comparisons/mimo-v2-6-flash-vs-gpt-6-luna)（独立评测，2026-10-19 核实）
- [Artificial Analysis — MiMo-V2.6-Flash vs Step 5 Preview](https://artificialanalysis.ai/zh/models/comparisons/mimo-v2-6-flash-vs-step-5)（延迟/成本口径）

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-19 | 新建文档：从小米 MiMo-V2.6 素材提炼系列知识。覆盖 Pro / Flash / Pro-Ultraspeed 定位、Flash 全量规格（309B/15B、48 层、1M、原生全模态、MIT、$0.14/$0.28）、AA v4.3.2 独立评测（Index 38、$0.06/task、AA-Omniscience −13）、与 GPT-6 Luna / Step 5 的横向对比、RL 方法论（You Only RL Once / GRS / GAR / MOPD2 / 异步 GRPO）与训练成本（Flash 85 万美元 / Pro 262 万美元、6 天、75 万条轨迹）。Pro 定价与 Ultraspeed 规格标注待补充 |
