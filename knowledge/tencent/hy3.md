# Hy3（腾讯混元）

> 最后更新: 2026-07-08
> 所属厂商: 腾讯（Tencent Hunyuan）
> 产品类别: MaaS
> 状态: Published（正式版）

<!-- SUMMARY_START -->
**定位**: 腾讯混元系列旗舰推理模型，高性价比通用推理 + Agent 底座，295B MoE 仅 21B 激活，开源可自部署（Apache 2.0）
**当前主推**: Hy3（2026-07-06 正式发布，取代 Hy3-preview）
**适用**: 个人/小团队 Agent 开发、预算敏感场景、私有化部署/二次开发、办公生产/金融建模/前端设计/游戏制作
**不适用**: 多模态 Agent（纯文本模型）、超长上下文场景（256K vs 竞品 1M）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Hy3** | 🚩 高性价比通用推理+Agent底座 | 256K tokens | 异构专家设计 + 快慢思考融合 + Apache 2.0 开源 | 2026-07-06 |
| Hy3-preview | 上一版（已被 Hy3 取代） | 256K tokens | 异构专家设计 + P-Penalty Loss + 开源 | 2026-04-22 |

### Hy3（正式版）

- **模型**：Hy3
- **公司**：腾讯混元（Tencent Hunyuan）
- **时间**：2026 年 7 月 6 日（preview 版 2026-04-22）
- **尺寸**：295B（MoE），激活参数 21B，MTP 层 3.8B
- **架构**：80 层主网络、192 个路由专家（每层激活 8 个 + 1 个常驻共享专家）、64 GQA 查询头 + 8 KV 头、隐藏维度 4096
- **上下文**：256K tokens
- **开源**：是（Apache 2.0，BF16 + FP8 权重均开放）
- **多模态**：纯文本
- **思考模式**：原生支持普通回答和深度思考，通过 `reasoning_effort` 在 no_think / low / high 之间切换（默认 no_think）
- **场景**：Agent 开发、编码辅助、工具调用、办公生产、金融建模、前端设计、游戏制作、私有化部署
- **核心升级（vs preview）**：
  1. **后训练数据质量和多样性提升 + RL 算力规模扩大**：以较小尺寸首次比肩国内外 2～5 倍参数规模的旗舰模型
  2. **Co-design 方法论**：以扎实模型底座为前提，用真实应用场景构建 Eval、以数据回流反哺训练，借助大模型泛化性把单产品沉淀的能力迁移到其他产品
  3. **270 位专家盲测**：Hy3 均分 2.67/4，优于 GLM-5.1（2.51/4），前端/数据与存储/CI-CD 优势显著
  4. **生产级稳定性**：工具调用错误恢复能力大幅提升，跨脚手架（CodeBuddy/Cline/KiloCode）SWE-bench Verified 标准差 ≤4%
  5. **幻觉率大幅下降**：12.5% → 5.4%，常识错误率 25.4% → 12.7%
  6. **多轮对话能力增强**：多轮问题率 17.4% → 7.9%，MRCR 42.9% → 75.1%
  7. **Apache 2.0 协议**（preview 为 Tencent Hunyuan Community License）
- **特点**：
  1. **异构专家尺寸设计 + P-Penalty Loss 路由优化**：推理效率提升 40%
  2. **快慢思考融合**：支持 no_think / low / high 推理强度切换
  3. **性价比**：输入 ¥1/1M tokens，输出 ¥4/1M tokens，缓存命中 ¥0.25/1M tokens
  4. **开源可自部署**：295B MoE 仅 21B 激活，推荐 8×H20-3e 部署，支持 vLLM / SGLang
  5. **长时 Agent**：495 步工作流

## 核心能力与限制

### 核心能力（Benchmark）

| 能力 | 指标 | 来源 |
|------|------|------|
| **编码（SWE-bench Verified）** | 78.0%（高推理强度+工具） | [DataLearner](https://www.datalearner.com/ai-models/pretrained-models/tencent-hy3) |
| **编码（SWE-bench Multilingual）** | 75.8% | 同上 |
| **编码（SWE-bench Pro）** | 57.9% | 同上 |
| **编码（DeepSWE）** | 28.0% | 同上 |
| **数学推理（IMO-AnswerBench）** | 90.0% | 同上 |
| **科学推理（GPQA Diamond）** | 90.4%（高推理强度） | 同上 |
| **高难度推理（HLE）** | 37.0（无工具）/ 53.2（工具） | 同上 |
| **浏览/信息检索（BrowseComp）** | 84.2%（联网+工具） | 同上 |
| **Agent 工具调用（MCP-Atlas）** | 79.1% | 同上 |
| **Agent 工具调用（TerminalBench 2.1）** | 71.7% | 同上 |
| **Agent 工具调用（Tool Decathlon）** | 48.5% | 同上 |
| **长上下文（AA-LCR）** | 73.4% | 同上 |
| **开源部署** | 21B 激活参数，Apache 2.0 免费商用 | [GitHub](https://github.com/Tencent-Hunyuan/Hy3) |

### 生产可靠性（vs preview）

| 指标 | preview | Hy3 正式版 | 说明 |
|------|---------|-----------|------|
| 幻觉率 | 12.5% | 5.4% | 基于真实产品内部评测 |
| 常识错误率 | 25.4% | 12.7% | 细粒度数据清洗+训练约束 |
| 多轮问题率 | 17.4% | 7.9% | 指代消解/省略还原/多轮约束继承 |
| MRCR（长对话理解） | 42.9% | 75.1% | 长程交互中复杂意图保持 |
| 跨脚手架标准差 | — | ≤4% | SWE-bench Verified 在 CodeBuddy/Cline/KiloCode 上 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 上下文 | 256K tokens | 竞品普遍 1M（如 Qwen3.7-Max/Plus） |
| 多模态 | 纯文本 | 无图/视频/屏幕输入能力 |
| 长时 Agent | 495 步工作流 | 无超长时自主运行验证（竞品如 Qwen3.7-Max 支持 35h） |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 个人/小团队 Agent 开发 | Hy3 | 性价比碾压，Agent 能力够用 |
| 私有化部署/二次开发 | Hy3 | Apache 2.0 + 21B 激活，部署成本低 |
| 编码辅助/软件工程 | Hy3 | SWE-bench Verified 78.0%，跨脚手架泛化性好 |
| 办公生产（PPT/文档/Excel） | Hy3 | WorkBuddy 任务成功率 72%→90%，耗时缩短 34% |
| 金融建模/数据分析 | Hy3 | 推理+工具调用能力强，幻觉率低 |
| 前端设计/代码生成 | Hy3 | 盲测中前端类别优势显著 |
| 游戏制作/AI 游戏助手 | Hy3 | WeGame 接入后综合成功率 92%，幻觉率 2.8% |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 多模态 Agent（GUI/视觉/屏幕） | 纯文本模型，无多模态能力 |
| 大型代码仓库/超长文档 | 256K 上下文，竞品 1M |

## Hy3 API 价格（每百万 Tokens）

| 输入 | 输出 | 输入（命中缓存） |
|------|------|------------------|
| ¥1 | ¥4 | ¥0.25 |

> 来源：[新京报](https://www.bjnews.com.cn/detail/1783323355129516.html)、[新浪财经官方发布](https://finance.sina.com.cn/stock/relnews/hk/2026-07-06/doc-inifwfpy8675405.shtml)

## 市场表现

- Preview 上线以来日均 token 消耗量增长 **20 倍**
- 连续三周登顶 OpenRouter 周榜（2026.04.27-05.11）
- Token 调用量达上一代 Hy2 的 10 倍
- 代码与智能体场景增幅超 16.5 倍
- 2026-06-11 OpenRouter 周 Token 量 3.3T，排名 #2（仅次于 DeepSeek V4 Flash）
- WorkBuddy 上自主选择 Hy3 的用户数增长 **6 倍**
- 已接入 WorkBuddy/CodeBuddy、元宝、Marvis、ima 等多个腾讯业务

### 为什么市场认可度高

1. **价格碾压**：输出价格远低于同级别旗舰模型，OpenRouter 用户以个人开发者和小团队为主，价格极度敏感
2. **能力"够用"且持续进步**：SWE-bench Verified 从 preview 的 74.4% 提升到 78.0%，工具调用和 Agent 实战能力持续增强
3. **开源可自部署**：295B MoE 仅 21B 激活，Apache 2.0 免费商用
4. **Co-design 飞轮**：腾讯多元产品矩阵（WorkBuddy/元宝/ima/Marvis/微信/游戏）提供真实反馈 → 模型优化 → 反哺所有产品，形成可迁移泛化的良性循环
5. **限免策略正确**：两周限免建立使用惯性，结束后留存率高

## Co-design 方法论

Hy3 的迭代采用了 **Co-design** 方法（来源：[腾讯混元解决方案](https://hunyuan.tencent.com/solutions)）：

1. **以扎实模型底座为前提**：295B MoE 架构 + 快慢思考融合
2. **用真实应用场景构建 Eval**：从 50+ 腾讯业务团队收集反馈，270 位专家盲测
3. **以数据回流反哺训练**：WorkBuddy/元宝/ima/Marvis 等产品的真实日志和反馈用于 SFT + RL
4. **借助大模型泛化性迁移能力**：单产品沉淀的能力（如意图理解、工具调用）可迁移到其他产品

> 本质上是**模型-产品协同进化**：模型能力提升 → 产品体验改善 → 更多用户 → 更多真实数据 → 模型继续提升

## 关键技术论文

[⚠️ 待补充]

## 参考资料

- [Hy3 官方发布页](https://hy.tencent.com/research/hy3)（官方博客）
- [腾讯混元解决方案](https://hunyuan.tencent.com/solutions)（Co-design 方法论）
- [Tencent Hunyuan Hy3 GitHub](https://github.com/Tencent-Hunyuan/Hy3)（官方 GitHub，Apache 2.0）
- [HuggingFace: tencent/Hy3](https://huggingface.co/tencent/Hy3)（模型权重）
- [ModelScope: Tencent-Hunyuan/Hy3](https://modelscope.cn/models/Tencent-Hunyuan/Hy3)
- [新浪财经：Hy3 正式发布报道](https://finance.sina.com.cn/stock/relnews/hk/2026-07-06/doc-inifwfpy8675405.shtml)
- [DataLearner: Hy3 评测与定价](https://www.datalearner.com/ai-models/pretrained-models/tencent-hy3)
- [新京报：Hy3 API 定价](https://www.bjnews.com.cn/detail/1783323355129516.html)
- [腾讯云 TokenHub](https://console.cloud.tencent.com/tokenhub/models/detail?modelId=hy3)
- [AI Studio 在线体验](https://aistudio.tencent.com/)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-07-08 | 全面更新：Hy3 正式版（2026-07-06 发布）。新增 Benchmark 数据、生产可靠性指标、Co-design 方法论、API 定价、业务接入情况。来源：官方发布页、新浪财经、DataLearner。**文件重命名**：hy3-preview.md → hy3.md |
| 2026-06-11 | 初始创建：Hy3-preview 产品知识提炼。来源：inbox/ai-knowledge-by-qoder-ai-native-agent-20260611.md |
