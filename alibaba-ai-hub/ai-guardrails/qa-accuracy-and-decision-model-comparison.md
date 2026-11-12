# AI 安全护栏客户问答：准召数据与 Jev 类决策模型对比

> 最后更新: 2026-11-12
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: AI 安全 / 售前问答
> 状态: Published

<!-- SUMMARY_START -->
**场景**: 客户售前问题应答口径——①产品是否基于 Qwen3Guard；②分安全子类的准确率/召回率（行业标准测试集）；③Jev 类 decision 模型 vs Qwen3Guard 的推理耗时与召回率
**核心结论**: 官方口径产品由 Qwen3Guard 驱动（但产品≠单模型）；云 API 未公开分子类准召，公开锚点为 Qwen3Guard 技术报告（14 个英文 benchmark 8 个第一）；Jev 类无安全专项公开数据，合规护栏主用 Qwen3Guard 系、decision 类做业务自定义判断，同集 PoC 是唯一可信对比路径
**关联**: [产品全景文档](ai-guardrails.md) · [百炼决策模型](../maas/decision-model.md)
<!-- SUMMARY_END -->

## 〇、先决问题：这个产品是基于 Qwen3Guard 模型吗？

**官方口径：是。** 三处官方证据：

1. Qwen 官方博客明示：「您也可通过阿里云 AI 安全护栏服务一键接入企业级安全能力，享受**由 Qwen3Guard 驱动**的智能防护解决方案」（[Qwen3Guard 发布博客](https://qwenlm.github.io/zh/blog/qwen3guard/)）。
2. 百炼集成接入主推 Service 即 Qwen3Guard 版：`qwen_query_check` / `qwen_response_check`（含 `_pro`），[官方文档](https://help.aliyun.com/zh/document_detail/2923687.html)标注「基于 Qwen3Guard，主推」。
3. 检测 Agent 基础版内置模型即 **Qwen3Guard-Gen-4B**（[检测 Agent 计费方案](https://www.alibabacloud.com/help/zh/content-moderation/latest/detecting-agent-billing-schemes)）。

**但必须向客户讲清边界：产品 ≠ 单模型。**

- AI 安全护栏是多维度检测体系：内容合规/提示词攻击的文本分类由 Qwen3Guard 系承担；自定义词库（子串匹配）、敏感数据（S0~S3+脱敏）、恶意文件/URL、数字水印等是独立策略引擎，不是 Qwen3Guard 的能力。
- API 标准版/pro 版的具体基座与策略组合官方未逐一披露；检测 Agent 高级版可选 Qwen3.0-Plus / Qwen3.6-Flash / Qwen3.6-Plus 等其他模型。
- Qwen3Guard 模型本身：Qwen3 基座 + 安全分类专项微调（1.19M 标注样本），**Gen（生成式，整段分类）/ Stream（流式，逐 token 分类头）两变体 × 0.6B/4B/8B 三规模**，三级风险（Safe/Controversial/Unsafe），9 大风险类，119 种语言，已在 HuggingFace/ModelScope 开源。

## 一、问题 7：分安全子类的准确率/召回率（行业标准测试集）

### 1. 官方数据现状（诚实口径，禁止编造）

| 层面 | 数据可得性 |
| --- | --- |
| 云产品 API（护栏 Service） | **官方未公开**分子类 P/R 数值；产品概述明确支持「特定检测目标优化、检测阈值优化」等定制流程，分子类指标可走商务/工单渠道索取或定制评测 |
| Qwen3Guard 开源模型 | **有公开技术报告**（[arXiv 2510.14276](https://arxiv.org/html/2510.14276v1)）：分测试集 F1 数值表 + 子类混淆矩阵（图）+ 拒答检测 P/R 表 |

### 2. 公开锚点：Qwen3Guard 技术报告关键数据（2026-11-12 核实）

**采用的行业标准测试集**：Prompt 侧 ToxicChat、OpenAIMod、Aegis、Aegis2.0、SimpleSafetyTests、HarmBench、WildGuardTest；Response 侧 HarmBench、SafeRLHF、BeaverTails、XSTest、Aegis2.0、WildGuardTest、Think（推理内容安全，自标注已公开）；多语言 RTP-LX、PolyGuard；中文为 Qwen3-MT 翻译版 + 自研涉政集 PolST。测试集公开于 [HF: Qwen/Qwen3GuardTest](https://huggingface.co/datasets/Qwen/Qwen3GuardTest)。

**安全分类 F1 均值**（Gen 版，strict/loose 按测试集取最优；数据来源报告 Table 2~6）：

| 模型 | 英文 Prompt（7 集） | 英文 Response（7 集） | 中文 Prompt（3 集） | 中文 Response（4 集） | 多语言 Prompt（RTP-LX） | 多语言 Response（PolyGuard） |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3Guard-0.6B-Gen | 88.1 | 82.0 | 80.8 | 84.9 | 74.8 | 74.2 |
| Qwen3Guard-4B-Gen | 89.3 | 83.7 | 84.6 | 87.3 | 81.6 | 78.1 |
| Qwen3Guard-8B-Gen | **90.0** | **83.9** | **85.1** | 87.1 | **85.0** | 77.6 |
| WildGuard-7B | 85.8 | 79.9 | 55.1 | 61.5 | 43.9 | 63.5 |
| LlamaGuard3-8B | 79.4 | 70.7 | 45.6 | 62.2 | 46.6 | 65.8 |
| LlamaGuard4-12B | 75.9 | 67.5 | 44.1 | 56.5 | 41.7 | 53.4 |
| NemoGuard-8B | 82.9 | 78.1 | 39.1 | 63.0 | 42.7 | 69.5 |

- 14 个公开英文 benchmark 中 8 个第一；0.6B 小模型即超越 10 倍参数的上一代护栏模型。
- **国内客户最关心的涉政子类（PolST）**：Qwen3Guard-8B prompt F1 **88.6** / response **90.4**，LlamaGuard3 仅 19.8/28.0、WildGuard 仅 17.8/17.7——中文涉政是海外开源护栏的盲区，差距 4~5 倍。
- Stream 流式版仅小幅降点：4B-Stream 英文 prompt 89.1 / response 81.8（Gen 为 89.3/83.7），换逐 token 实时检测能力。

**拒答检测 P/R**（报告 Table 7，4B-Gen）：XSTest P 90.7 / R 98.9 / F1 94.6；WildGuardTest P 83.3 / R 98.4 / F1 90.2（与 WildGuard-7B 相当）。

**子类（9 类）层面**：报告公开的是 4B-Gen 对 unsafe 样本的**分类混淆矩阵（图，Figure 5）**，覆盖 Violent / Non-violent Illegal Acts / Sexual / PII / Suicide & Self-Harm / Unethical / Politically Sensitive / Copyright / Jailbreak；多数类别表现强，**Copyright 最弱**（样本稀少）。**无逐子类 P/R 数值表**——客户若要数值版分子类准召，只能实测。

### 3. 口径警示（售前必须说明）

开源模型 benchmark ≠ 云产品准召：云 API 返回是多策略合并结果（内容合规+提示词攻击+词库+敏感数据，block>mask>watch>pass），且阈值/标签开关可调。**引用开源数据时必须注明「Qwen3Guard 开源模型口径」，不能直接当作护栏 API 的 SLA 承诺。**

### 4. 落地处理：PoC 实测方案（推荐给客户的正式路径）

1. **数据集**：Qwen3GuardTest 公开集（行业标准锚点）+ 客户业务标注样本（建议每子类 ≥100 条违规 + 等量正常对照，覆盖客户真实话术）。
2. **被测**：护栏 API pro 版（query/response_security_check_pro，标签最细）；可选对照组：开源 Qwen3Guard-Gen-4B 自部署、百炼 decision-model-preview。
3. **输出**：分子类 P/R/F1 矩阵 + 正常对照误伤率 + P50/P95 延迟 + 成本；做阈值扫描（置信分 0~100 步长 1）与 strict/loose（争议内容归 unsafe/safe）两档策略对比。
4. **工程**：复用本目录 `test_guardrail_custom_keyword.py` / `bench_guardrail_latency.py` 框架扩展批量评测；万次级检测成本 <20 元（15 元/万次/维度），注意词库/配置变更 3~5 分钟生效窗口。

## 二、问题 10：Jev 类 decision 模型 vs Qwen3Guard（推理耗时 + 召回率）

### 1. 对象界定

- **Jev**：TypeSafe AI 2026-09-20 发布的首个 System One 决策模型——非自回归、不生成文本，一次前向并行返回 choice/noul/score + 概率分布；RLCD 校准训练（无论文、训练层黑箱）。
- **百炼 decision-model-preview**：同品类（System One 协议 + TypeSafe SDK 生态），2026-09-24 上线。详见[百炼决策模型](../maas/decision-model.md)。
- 客户语境：用 decision 模型做护栏判定，与 Qwen3Guard 系护栏对比。

### 2. 推理耗时对比

| 方案 | 口径 | 数据 | 来源 |
| --- | --- | --- | --- |
| TypeSafe Jev | 官方宣称 | 70~500ms | TypeSafe 官方发布（见 decision-model.md 溯源节） |
| 百炼 decision-model-preview | 实测 P50/P95 | **51ms / 68ms**（北京 workspace，2026-10-09，×20） | 本地实测 |
| 护栏 API query_security_check | 实测 avg/p90 | 185ms / 208ms（外网→北京，2026-11-11） | 本地实测 |
| 护栏 API response_security_check_hp | 实测 avg/p90 | 190ms / 219ms；官方服务端目标 <100ms/切片 | 本地实测 + [官方流式方案](https://help.aliyun.com/zh/document_detail/2980054.html) |
| Qwen3Guard 开源自部署 | 官方未公布 ms 数据 | Gen 需短生成（标签+类别，max_new_tokens≈128）；Stream 为逐 token 判别（分类头，无解码循环） | [技术报告](https://arxiv.org/html/2510.14276v1)架构节 |

**口径警示**：云 API 延迟 ≠ 模型推理耗时——实测 200ms 含外网 RTT（约 100~150ms）与多策略引擎开销；同地域 VPC 内网 + hp 版可压至 <100ms 级。架构上 decision 类与 Qwen3Guard-Stream 同属「prefill-only 判别、无解码」，延迟同量级；Gen 版多一次短生成。**耗时维度 decision 类略占优，但差距在网关链路里会被网络与策略开销稀释。**

### 3. 召回率对比（无公开同口径数据，禁止编造 head-to-head）

| 维度 | Qwen3Guard 系 | Jev 类 decision 模型 |
| --- | --- | --- |
| 安全专项训练 | 1.19M 安全标注样本专项微调 | 通用决策原语，无安全专项训练披露 |
| 公开安全 benchmark | 有（上文 Table 2~7，SOTA） | **无**（TypeSafe 无论文、无安全评测公开） |
| 风险分类体系 | 三级风险 + 9 大子类 + 119 语言 | 标签请求时动态定义（零样本），无内置安全 taxonomy |
| 概率可靠性 | 置信分 + 阈值可调 | Jev 宣称 RLCD 校准；**百炼 preview 实测主观维度概率 one-hot 退化**（probs=1.0/0.0），安全分类恰是主观维度密集场景，直接用需先校准验证 |
| 实测已知坑 | 提示词攻击维度误伤复述类指令 | other 兜底吸走明确分类；误用不报错（生成任务传入返回无意义概率） |

### 4. 结论与组合建议（售前应答口径）

1. **合规护栏主用 Qwen3Guard 系**：安全专项训练 + 公开 SOTA + 中文涉政碾压级优势 + 云产品多维策略（词库/敏感数据/文件/URL）是 decision 模型不具备的完整体系。
2. **decision 类适合业务自定义判断**（路由/分流/质检/规则并行），51ms 级延迟与动态标签是优势；做合规判定前必须用标注集验证校准与召回。
3. **客户若要「decision 模型做自定义护栏」，护栏产品内已有对应能力——检测 Agent**：自然语言描述风险、可选 Qwen3Guard-Gen-4B/Qwen3.0-Flash/Plus 等模型，无需外接 Jev；国际站 $8~$40/万条切片按模型分档。
4. **可组合**：decision 类做业务风险初筛（快、便宜）+ 护栏做合规兜底（准、全），网关串行或并行编排。
5. **同集 PoC 是唯一可信对比**：同一标注集（Qwen3GuardTest + 业务样本）分别跑护栏 API、decision-model-preview（noul 逐规则）、可选开源自部署，输出分子类 P/R/F1 + P50/P95 + 成本三维对比。复用现有脚本框架即可执行。

## 三、附：计费口径确认（客户问题 4 的前提修正）

客户「具体到百万 tokens 成本」的问法需先修正口径：**API 接入按成功调用次数计费，不按 token**（15 元/万次/维度，单次 ≤2000 字符同价）；**只有百炼集成接入按 token**（基础 0.0004 / pro 0.003 元/千 token，不足 1000 按 1000 计）。

API 按次 → 等效百万 token 成本换算：`15 元/万次 ÷ 平均每次调用 token 数 × 10⁶`。示例（单维度）：平均 500 token/次 → 3 元/百万 token；平均 2000 token/次 → 0.75 元/百万 token。双维度（内容合规+提示词攻击）×2。流式切片场景按切片次数另算（每切片独立计费）。详细价格表见[产品全景文档](ai-guardrails.md)第四节。

## 参考信源（2026-11-12 核实）

- [Qwen3Guard 官方发布博客](https://qwenlm.github.io/zh/blog/qwen3guard/)（产品由 Qwen3Guard 驱动、变体/规模/三级风险/119 语言）
- [Qwen3Guard Technical Report（arXiv 2510.14276）](https://arxiv.org/html/2510.14276v1)（Table 2~7 benchmark、Figure 5 子类混淆矩阵、Stream 架构）
- [HF: Qwen/Qwen3GuardTest 公开测试集](https://huggingface.co/datasets/Qwen/Qwen3GuardTest)
- [面向百炼用户的 AI 安全护栏服务](https://help.aliyun.com/zh/document_detail/2923687.html)（qwen_query_check 基于 Qwen3Guard 主推）
- [检测 Agent 计费方案](https://www.alibabacloud.com/help/zh/content-moderation/latest/detecting-agent-billing-schemes)（基础版内置 Qwen3Guard-Gen-4B）
- [百炼决策模型 decision-model-preview](../maas/decision-model.md)（Jev 溯源、51ms 实测、三个行为坑）
- 本地实测：[护栏延迟实测](bench_guardrail_latency_results_20261111.md) · [词库拦截实测](test_guardrail_custom_keyword_results_20261111.md)

## Changelog

- 2026-11-12 新建：应答客户问题 7/10——确认 Qwen3Guard 基座官方口径与产品边界；收录技术报告分测试集 F1 与拒答 P/R（子类仅混淆矩阵图，无逐子类数值表，已标注）；Jev 类 vs Qwen3Guard 耗时/召回对比框架与 PoC 方案；修正客户按 token 计费前提（API 按次）。