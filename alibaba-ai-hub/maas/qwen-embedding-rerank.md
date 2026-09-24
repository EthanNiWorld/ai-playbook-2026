# Qwen 向量与重排序（Embedding & Rerank）

> 最后更新: 2026-09-20
> 所属厂商: 阿里云（通义实验室）
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 基于 Qwen3.7 底座的文本向量化（Embedding）与重排序（Rerank）模型线，覆盖检索系统的召回与精排两阶段
**当前主推**: qwen3.7-text-embedding（旗舰向量）/ qwen3.7-text-embedding-flash（轻量向量）/ qwen3.7-text-rerank（精排）
**适用**: RAG、语义搜索、推荐系统、文本聚类、零样本分类、异常检测（rerank 限检索/候选精排环节）
**不适用**: 图片/视频多模态向量化与重排序（需 qwen3-vl-embedding / qwen3-vl-rerank，本文档未覆盖其参数）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 角色 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| qwen3.7-text-embedding | 向量旗舰 | 128K | 性能最强，维度最高 2560，支持稠密+稀疏混合检索 | [⚠️ 待补充] |
| qwen3.7-text-embedding-flash | 向量轻量 | 128K | 价格为标准版 1/4，201 语种 + 128K 上下文全保留 | 2026-09-01 |
| qwen3.7-text-rerank | 检索精排 | 32K | 单次最多 500 条候选精排，websearch 较上代 +35% | 2026-09-01 |

### qwen3.7-text-embedding（旗舰向量模型）
- 模型：qwen3.7-text-embedding
- 公司：阿里云（通义实验室）
- 时间：[⚠️ 待补充]
- 尺寸：未公开
- 上下文：131,072 tokens（128K）
- 场景：生产级 RAG 底库、语义搜索、代码检索、跨语言检索、聚类/分类/异常检测等下游任务
- 特点：当前性能最强的文本向量模型，较 text-embedding-v4 在 MTEB 多语言/中英/Code 检索等任务提升约 20%；支持 256~2560 自定义维度与稠密+稀疏三种向量输出
- 定价：北京 0.5 元/百万 tokens（Batch File 0.25）；新加坡 0.525 元/百万

### qwen3.7-text-embedding-flash（轻量向量模型）
- 模型：qwen3.7-text-embedding-flash
- 公司：阿里云（通义实验室）
- 时间：2026-09-01（百炼上新）[来源: help.aliyun.com 上新页，2026-09-17 核实]
- 尺寸：未公开
- 上下文：131,072 tokens（128K）
- 场景：大规模语料向量化、在线实时向量化、预算敏感的多语言场景
- 特点：面向成本和吞吐敏感场景，价格仅标准版 1/4；较 text-embedding-v4 多语言覆盖 100→201 种、长文本 32K→128K，语义/跨语言/代码检索整体基本持平（AIRBench-zh +3%）
- 定价：北京 0.125 元/百万 tokens（Batch File 0.063）；新加坡未上架

### qwen3.7-text-rerank（重排序模型）
- 模型：qwen3.7-text-rerank
- 公司：阿里云（通义实验室）
- 时间：2026-09-01（百炼上新）[来源: help.aliyun.com 上新页，2026-09-17 核实]
- 尺寸：未公开
- 上下文：32,768 tokens（32K），单条文档最大 30,000 tokens
- 场景：RAG 二阶段精排、搜索结果重排序、Agentic Memory 检索精排
- 特点：较 qwen3-rerank 在通用与 Web 检索、代码检索、指令遵循、Agentic 与 Memory 检索大幅提升，websearch 相对提升约 35%；单次最多 500 条候选、单请求 120K tokens
- 定价：北京 0.5 元/百万 tokens；官方模型信息页仅列北京节点

> 📌 **历史模型**：text-embedding-v4（属 Qwen3-Embedding 系列，向量维度 64~2048、上下文较短的代际基线）与 qwen3-rerank 仍可调用，但官方选型文档已推荐纯文本场景使用 qwen3.7 系列替代，不建议新项目选用。

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 自定义向量维度 | 两个 embedding 模型均支持：标准版 256~2560，flash 版 256~1024；维度选择参考：1024 为通用推荐平衡点，1536/2048+ 追求精度，768 及以下降低存储成本 |
| 任务指令（instruct） | 通过英文任务指令引导模型针对特定检索场景优化；标准版指令遵循较 text-embedding-v4 提升 16.4%；使用时须将 text_type 设为 query |
| query/document 区分 | text_type 参数区分查询与文档向量（query 优化"提问"、document 优化"被匹配"），短文本匹配长文本时应启用；仅 DashScope SDK/API 支持 |
| 稠密与稀疏向量 | output_type 支持 dense / sparse / dense&sparse 三种输出；标准版稀疏向量采用类 SPLADE 新训练策略（效果 +8.4%）并新增跨语言稀疏检索；稀疏向量适合 SKU、日志等精确关键词匹配 |
| rerank 排序策略 | rerank 的 instruct 参数支持问答检索（默认）与语义相似度两种策略；top_n 控制返回条数 |
| 批量推理（Batch） | 两个 embedding 模型支持 Batch File 调用（5 折）；rerank 不支持 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| embedding 单批规模 | 批次 20 条 / 单批 128,000 tokens | 单次 API 调用最多 20 条文本 |
| rerank 单请求规模 | 500 条文档 / 单条 30K tokens / 单请求 120K tokens（建议） | 单条超限返回 HTTP 400，不会截断 |
| rerank 上下文 | 32K | 显著小于两个 embedding 模型的 128K |
| 多语言覆盖 | 三模型均为 201 种主流语种与方言 | 含简繁中文、粤语等 |
| 地域部署 | flash 与 rerank 官方模型信息页仅列华北2（北京） | 标准版支持北京 + 新加坡（国际）；新加坡标准版 RPM 仅 2000（北京 24000） |
| 输出形态 | rerank 输出相关性分数与排序，不生成文本 | 与 embedding 的向量输出是两种范式 |

## 定价概览

| 模型 | 输入价格（北京） | 输入价格（新加坡） | 输出价格 | Batch（北京） | 备注 |
|------|---------|---------|---------|---------|------|
| qwen3.7-text-embedding | 0.5 元/百万 tokens | 0.525 元/百万 tokens | — | 0.25 元/百万 | — |
| qwen3.7-text-embedding-flash | 0.125 元/百万 tokens | 未上架 | — | 0.063 元/百万 | — |
| qwen3.7-text-rerank | 0.5 元/百万 tokens | 官方页未列 | — | 不支持 | 限流 RPM 3000 / TPM 900 万（北京） |

> 定价来源：https://help.aliyun.com/zh/model-studio/qwen3-7-text-embedding 、https://help.aliyun.com/zh/model-studio/qwen3-7-text-embedding-flash 、https://help.aliyun.com/zh/model-studio/qwen3-7-text-rerank ，核实日期：2026-09-07（不含限时优惠，以百炼控制台为准）

> ⚠️ 国际站（USD）定价页未收录 qwen3.7-text-* 全系（2026-09-17 核实，仅列 text-embedding-v4/v3、qwen3-rerank 等旧代）——新加坡节点 USD 定价未上架，上表"新加坡"列为中国站模型信息页的 ¥ 口径参考。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 生产级 RAG / 企业知识库 | text-embedding（召回）+ text-rerank（精排） | 官方建议流程：embedding 召回 50–100 条候选 → rerank 筛 Top 5–10 → 交给 LLM |
| 大规模语料建库 / 实时向量化 | text-embedding-flash | 单 token 成本 1/4，维度 1024 以内够用时性价比最优 |
| 高精度检索 / 混合检索 | text-embedding | 需要 2048/2560 高维、稠密+稀疏混合（dense&sparse）、代码检索、跨语言检索时选标准版 |
| 搜索结果重排 / Agentic Memory 精排 | text-rerank | 初始检索返回 20–100+ 条相关度参差的候选时收益最大；候选来自向量召回、关键词检索或推荐粗排均可 |
| 推荐系统 / 聚类 / 零样本分类 / 异常检测 | 任一 embedding 模型 | 只需"度量语义相似度"、无候选精排环节的任务，无需 rerank |
| 纯生成任务（对话/写作/代码/翻译） | 均不需要 | LLM 自身语义理解不依赖外部向量模型，仅当业务需要语义相似度或外部知识取材时才引入 |

## 参考资料

- qwen3.7-text-embedding 模型信息: https://help.aliyun.com/zh/model-studio/qwen3-7-text-embedding
- qwen3.7-text-embedding-flash 模型信息: https://help.aliyun.com/zh/model-studio/qwen3-7-text-embedding-flash
- qwen3.7-text-rerank 模型信息: https://help.aliyun.com/zh/model-studio/qwen3-7-text-rerank
- 向量化（Embedding）API 与选型: https://help.aliyun.com/zh/model-studio/embedding
- 重排序（Rerank）API: https://help.aliyun.com/zh/model-studio/rerank

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-09-20 | 移除定价表备注列「免费额度」信息（用户规范：材料不再考虑免费额度） |
| 2026-09-17 | 校验修复（knowledge-verification-2026-09-17）：embedding-flash 与 text-rerank 上线时间回填 2026-09-01（百炼上新页）；新增"国际站 USD 定价页未收录 qwen3.7-text-* 全系"显式标注；旗舰 embedding 上线时间仍待补充 |
