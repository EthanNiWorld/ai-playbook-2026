# 百炼决策模型（decision-model-preview）

> 最后更新: 2026-10-09
> 所属厂商: 阿里云
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 面向高频业务判断的结构化决策模型（预览版）——一次前向并行返回分类（choice）/是非判断（noul）/评分（score）及概率分布与置信度，**不生成文本**，延迟与成本与输出长度无关
**当前主推**: decision-model-preview（2026.09.24 上线，API 全量开放，限时免费）
**适用**: 工单分流、内容审核、智能体路由、质检评分、Agent 编排的"判断原语"（Router / Guardrail / Reviewer 节点）
**不适用**: 需要校准概率的量化决策、需要生成解释/理由、多跳推理、存量标准端点系统（决策模型仅支持 workspace 专属域名）
<!-- SUMMARY_END -->

> ⚠️ 素材截止 2026-10-09（预览版阶段，无 SLA 承诺；"限时免费"为培育期定价策略，生产接入需评估转正后价格风险）。

## 当前主推模型

| 模型 | 定位 | 输入上限 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **decision-model-preview** 🚩 | 结构化决策（非生成） | 65,536 tokens | System One 协议；choice/noul/score 一次前向并行返回；P50 51ms（约 qwen3.7-plus 的 1/25）；限时免费 | 2026.09.24 |

### decision-model-preview

> 来源：[官方模型页](https://help.aliyun.com/zh/model-studio/decision-model-preview)、[官方 API 参考](https://help.aliyun.com/zh/model-studio/decision-model-api)（2026-10 查询）、[第一财经](https://www.yicai.com/news/103378100.html) / [东方财富](https://emwap.eastmoney.com/a/202609243883964179.html)（2026-09-24 报道）；实测 2026-10-09（北京 + 新加坡 workspace 端点交叉验证）

- **模型 ID**：`decision-model-preview`（预览版），2026-09-24 上线，API 全量开放
- **协议**：System One（`POST /compatible-mode/v1/systemone`），**不兼容 chat/completions**
- **能力**：一次前向并行返回 choice（分类）/ noul（是非判断）/ score（评分）及概率分布与置信度；不生成文本，延迟与成本与输出长度无关（官方口径）
- **限流**：RPM 1,200 / TPM 2,000,000（北京与新加坡相同）；**限时免费**（两节点均免费，支持 Token Plan）
- **不支持**：Function Calling / 流式 / 联网 / 缓存
- **参数边界**：问题数不设上限（建议 ≤16，延迟近线性：实测 3 问 56ms → 16 问 103ms）；choice 选项 ≤255；score 等级 2-255（建议 3-7）

#### 端点实测（2026-10-09，重要集成约束）

- workspace 专属域名 `{WorkspaceId}.{region}.maas.aliyuncs.com/compatible-mode/v1/systemone` ✅ 北京/新加坡均通
- 标准 DashScope 端点 `dashscope.aliyuncs.com/compatible-mode/v1/systemone` ❌ HTTP 404
- **与通用 LLM 调用约束正好相反**：通用 LLM 必须走标准端点（workspace 域名不支持），决策模型只支持 workspace 域名——集成时需单独配置端点，存量标准端点系统无法直接接入

#### 实测性能（北京 workspace 端点）

| 模型 | 延迟 | 说明 |
|------|------|------|
| decision-model-preview ×20 | **P50=51ms / P95=68ms / min=40ms / max=68ms** | 极其稳定 |
| qwen3.7-plus（enable_thinking=False，同端点三问题 JSON 输出） | P50=1261ms | **约 25× 延迟差** |
| qwen3.7-plus（默认开 thinking） | P50≈10.6s | 约 200× |

- 决策模型免 prompt 工程、免 JSON 解析、概率原生返回；input_tokens 实测 55-268（小请求成本低）
- 实测脚本：[test_decision_model.py](maas-solution-and-api-sample/test_decision_model.py)（8 组用例，北京/新加坡）

#### 实测行为特征（三个重要坑）

1. **other 兜底选项会吸走明确分类**：同一工单（官方示例案例），无 other 时 billing=0.94；加 other 后 other=0.79 / billing=0.20——官方建议"补 other 兜底"与"强制自动分类"目标冲突，需按业务权衡（允许溢出人工 vs 强制归入主类）
2. **主观维度概率退化为 one-hot**：情感二分类上正负证据并存的句子（"不便宜但质量好"）仍返回 probs=1.0/0.0、conf=1.0；而规则边界清晰的维度（部门分类 0.94/0.06）分布平滑——**probabilities 字段不能自假为可靠后验分布，做阈值策略前需按维度实测校准**
3. **误用不报错**：把生成任务（"写诗"）当 noul 问题传入，返回 200 + P(yes)=0.75 无意义结果——服务端无"此请求不适合"保护，集成层需自行把关
- 错误输入（非法 type / 空 state）返回 400 InvalidParameter，报错信息清晰；嵌套结构化 state（对象/数组/多轮对话）支持良好

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **一次前向多问题并行** | 同一 state 下所有 questions 并行独立评估，一次输出全部概率分布；每加一问仅 ~+3ms |
| **类型化输出** | choice / noul / score + probabilities + confidence，免 prompt 工程与 JSON 解析 |
| **超低延迟** | P50 51ms / P95 68ms，约 qwen3.7-plus（关 thinking）的 1/25 |
| **动态标签** | 标签在请求时定义（criteria 字段），零样本即改即生效，标签变更无需重训 |
| **生产级限流** | RPM 1,200 / TPM 2,000,000 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 输出 | 最大输出 0 | 不生成任何文本；解释/理由类需求不适用 |
| 端点 | 仅 workspace 专属域名 | 标准 DashScope 端点 404；与通用 LLM 端点约束相反，需单独配置 |
| 概率校准 | 主观维度 one-hot 退化 | probs 不能自假为可靠后验分布，阈值策略前需按维度实测校准 |
| 误用保护 | 无 | 生成任务传入不报错，集成层需自行把关 |
| 预览阶段 | 无 SLA 承诺 | 限时免费为培育期定价策略，生产接入需评估转正后价格风险 |

## 定价概览

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|---------|---------|------|
| decision-model-preview | **限时免费**（北京/新加坡） | —（无输出生成） | 支持 Token Plan；转正价格未公布 |

> 定价来源：[官方模型页](https://help.aliyun.com/zh/model-studio/decision-model-preview)，核实日期 2026-10-09。

## 适用场景

### ✅ 适用（实测验证）

| 场景 | 类型 | 说明 |
|------|------|------|
| 工单分流 / 智能体路由 | choice | 一次前向同时出"派单团队+是否升级+严重度"，实测 0.94/0.96 置信度，50ms 级——直接驱动工单系统/Agent 编排器 |
| 内容审核 / 风控规则并行 | noul | 一条评论 5 条规则一次前向 57ms，P(yes) 可直接当风险分用 |
| 质检评分 / 满意度量表 | score | 概率加权期望输出非整数（实测 2.8 / 2.49），适合细粒度排序与趋势监控 |
| Agent 编排"判断原语" | choice/noul/score | Router / Guardrail / Reviewer 节点、缓存前置过滤、结果校验 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 需要校准概率的量化决策 | preview 校准仍有打磨空间（主观维度 one-hot） |
| 需要生成解释/理由 | 模型不生成文本 |
| 多跳推理 | 单次前向判别架构，无推理链 |
| 存量标准端点系统 | 仅支持 workspace 专属域名，无法直接接入 |

## 架构溯源：System One 协议来自 TypeSafe，非百炼自创

> 来源：TypeSafe 官方发布博客、[tonybai 拆解](https://tonybai.com/2026/09/20/jev-typesafe-system-one-model-intro/)、[LiteLLM 文档](https://docs.litellm.ai/docs/decisions)（百炼官方文档明示协议名 "TypeSafe System One" 并推荐 typesafe-sdk）

- 硅谷 AI 实验室 **TypeSafe AI** 于 2026-09-20 发布首个 "System One 模型" **Jev**（创始人 Diogo Almeida，前 OpenAI，ChatGPT 指令对齐技术奠基人之一），开创"**非自回归决策模型**"新类别：不生成文本、同一 state 下所有 questions 并行独立评估、一次前向输出全部概率分布；训练方法为 **RLCD**（面向校准决策的强化学习，优化目标 = 概率与真实结果匹配），区别于 LLM 的 RLHF/RLVR；Jev 定价输入 $0.042/M token、输出免费、70-500ms
- **时间线**：TypeSafe Jev（09-20，开创）→ **百炼 decision-model-preview（09-24，接入 System One 协议 + TypeSafe SDK 生态，限时免费）** → [OpenAI Decisions API（09-29/30 DevDay，GPT-6 Luna，limited preview）](../../knowledge/openai/gpt-6-series.md)——三大玩家 10 天内完成品类卡位；LiteLLM 已同时支持 /v1/systemone 与 /v1/decisions
- **是否基于 LLM 改的**：不是"chat LLM + 配置"，而是新模型类别（共享 tokenizer/transformer 底层特征：token 计量、65536 输入上限、TPM 限流；但去掉自回归解码循环，输出为类型化概率而非文本，训练目标为校准）。百炼未披露底座是否与 Qwen 同源及参数规模；与 TypeSafe 的合作/授权关系亦未披露，仅确认协议与 SDK 接入
- **与三种易混方案的本质差异**：① response_format 结构化输出：仍走 chat 协议 + 自回归生成，只保证格式合法，不改变延迟/成本结构；② BERT 类微调分类器：固定线性分类头，标签变更需重训；System One 标签在请求时动态定义，零样本即改即生效；③ 小模型+prompt+JSON 解析：延迟/稳定性/概率校准均不可比（实测 25× 延迟差）
- **生态已跟进**：LangChain TypeSafeClassifier / ModelRouterMiddleware / AutoModeMiddleware（工具风险拦截）、Vercel AI SDK experimental_evaluate——多供应商路径存在，客户无强 lock-in 顾虑

## 机制拆解（logit trick，三层结构）

> 来源：[dev.to 逆向分析](https://dev.to/programmerraja/how-jev-works-the-logit-trick-behind-typesafes-system-one-model-4lpd)（开源复现 simple-jev/mini-jev/von）+ [LangChain 官方博客](https://www.langchain.com/blog/building-a-harness-with-jev)；TypeSafe 无论文无架构图，机制层由开源复现验证，训练层仍黑箱

- **第 1 层 LLM 底座**：开源复现证明可以用 frozen 开源 LLM（Gemma/Qwen）直接搭建同等接口，**权重可以完全不动**——不是必须改架构或换头
- **第 2 层推理工程（接口与速度的全部来源，无需训练）**：① 选项重命名为单 token 标签（A/B/C…）；② 构造半截 assistant 回复 `{"answer": "`，让下一 token 位置正好落在答案上；③ **只跑 prefill 不进 decode 循环，读该位置 logits**（这就是 usage.output_tokens=0 的真正含义——不是架构改了，是服务端从不进解码）；④ 只对允许的标签子集做 softmax；⑤ 多问题共享相同长前缀 → **KV cache 复用 + 分支尾批处理**（实测"每加一问只 +3ms"的真正来源）；⑥ noul 不是 true/false 两 token，而是 0.1-0.9 九个数字 token 加权平均再重标度（避免二元选择导致的过度自信）；⑦ score = 等级索引概率加权期望（非整数输出的来源）；⑧ prompt 全冻结（换行变了 logits 就变，锁定才能保证概率可重复）
- **第 3 层 RLCD 校准后训练（TypeSafe 真正的护城河，完全未公开）**：开源版的 confidence 只是"softmax 落在赢家的比例"，**不是校准概率**（选项集变了每个数都会变）；TypeSafe 声称 Jev 校准（说 80% 就是对 80%），归功 RLCD，但无论文/无 reward function/无训练代码，arXiv 搜不到——"调用方式几周就被一个 Python 文件复现；训练方式才是秘密"
- **术语修正**："砍掉自回归解码循环、把生成头换成决策输出"表述过强——更准确是**不进 decode 循环（调用方式改变）**，LM head 大概率原封不动（标签 logits 就是从词表 logits 里读的），softmax 在服务端对子集做
- **对百炼 preview 的推断（行为证据，非官方披露）**：实测主观维度概率 one-hot 退化（probs=1.0/0.0），若 RLCD 校准训练充分则不应如此——百炼 preview 可能主要靠第 1+2 层（推理工程），校准层或尚未打磨到位；无法排除已做部分后训练，公开信息不可区分
- **售前选型启示**：该品类接口无壁垒（开源一个文件可复现），壁垒在校准；客户选型应拿自有标注数据验证 confidence 可靠性，而非相信接口数字

## 竞品对照

| 玩家 | 产品 | 时间 | 状态 |
|------|------|------|------|
| TypeSafe AI | Jev（首个 System One 模型，RLCD） | 2026-09-20 | GA（输入 $0.042/M，输出免费，70-500ms） |
| 阿里云百炼 | decision-model-preview | 2026-09-24 | **API 全量开放 + 限时免费**，早 OpenAI 约一周且开放度更高 |
| OpenAI | Decisions API（基于 GPT-6 Luna） | 2026-09-29/30 DevDay | limited preview，未公布定价 |

两大厂商同一周内各自产品化"LLM 判别器"形态，是行业共识信号：**高频结构化决策正从 chat API 的附属用法升级为独立产品形态**。

## 参考资料

- [官方模型页 — decision-model-preview](https://help.aliyun.com/zh/model-studio/decision-model-preview)（能力/限流/免费/65536 输入）
- [官方 API 参考 — 决策模型 API](https://help.aliyun.com/zh/model-studio/decision-model-api)（System One 协议/参数/示例）
- [第一财经 — 百炼决策模型上线](https://www.yicai.com/news/103378100.html)、[东方财富报道](https://emwap.eastmoney.com/a/202609243883964179.html)（2026-09-24）
- [InfoQ — OpenAI DevDay 2026](https://www.infoq.com/news/2026/10/openai-devday-2026/)、[HF Blog — What is Decisions API](https://huggingface.co/blog/sora-2/what-is-decisions-api-openais-fast-decision-layer)
- [tonybai — TypeSafe Jev / System One 拆解](https://tonybai.com/2026/09/20/jev-typesafe-system-one-model-intro/)
- [dev.to — logit trick 逆向分析](https://dev.to/programmerraja/how-jev-works-the-logit-trick-behind-typesafes-system-one-model-4lpd)
- [LangChain — Building a Harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev)
- [LiteLLM — Decisions 双端点支持](https://docs.litellm.ai/docs/decisions)
- 实测脚本：[test_decision_model.py](maas-solution-and-api-sample/test_decision_model.py)（2026-10-09，北京/新加坡 workspace 端点，8 组用例）

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-10-09 | 新建文档，提炼自 inbox 素材（含 2026-10-09 实测）：基本信息与限流（限时免费/1200 RPM/200 万 TPM）、端点实测（仅 workspace 域名、标准端点 404）、性能实测（P50 51ms ≈ qwen3.7-plus 1/25）、三个行为坑（other 吸分类/主观维度 one-hot/误用不报错）、架构溯源（TypeSafe System One + RLCD + 三方时间线）、logit trick 三层机制拆解、竞品对照 |
