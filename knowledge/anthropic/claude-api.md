# Anthropic Claude 模型

> 最后更新: 2026-08-01
> 所属厂商: Anthropic
> 产品类别: MaaS
> 状态: Published

> **定位**: Anthropic 旗舰模型系列，强调 Constitutional AI 安全对齐、长文本理解与高精度推理
**最高能力档**: Claude Fable 5（2026.06.09，Mythos-class，**1M 上下文**，$10/$50）——官方口径 highest-capability tier
**主力推荐**: Claude Opus 5（2026.07.24，coding / knowledge work SOTA，**1M 上下文**，$5/$25 = Fable 5 半价、与 Opus 4.8 同价）
**前旗舰**: Claude Opus 4.8（2026.05.28）
**适用**: 高精度推理、复杂长文本分析、代码生成、企业级 Agent、合规要求高场景
**不适用**: 预算敏感场景、超高并发低成本推理、渗透测试 / exploit 生成 / 二进制漏洞扫描类请求

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **Claude Fable 5** 🚩 | **最高能力档** | **1M** | SWE-Bench Pro 80.3%，Stripe 50M行Ruby迁移1天完成；敏感查询自动降级，**强制 30 天数据留存、不可用于 ZDR** | 2026.06.09 |
| **Claude Opus 5** ⭐ | **主力推荐**（Fable 5 半价） | **1M** | coding/knowledge work SOTA，最对齐模型；护栏拦截频率仅 Fable 5 的 ~15%；**无数据留存要求** | 2026.07.24 |
| **Claude Sonnet 5** | 均衡档（Sonnet 线当前主推） | **1M** | 最 agentic 的 Sonnet，性能接近 Opus 4.8 但价格更低；全计划可用、Free/Pro 默认模型 | 2026.06.30 |
| **Claude Haiku 4.5** | 轻量极速 | 200K | 极速响应，最具性价比；64K 最大输出 | [⚠️ 待确认]（官方全 ID `claude-haiku-4-5-20251001`） |

> 📌 **限制访问模型**：**Claude Mythos 5**（2026.06.09）与 Fable 5 同底座、同定价、同 API 行为，仅去除网络安全限制，**仅通过 Project Glasswing** 向美国政府网络防御者与关键基础设施提供商开放；非参与组织请用 Fable 5。详见下文专章。

> 📌 **历史模型**（仍可调用，不建议新项目选用）：**Opus 4.8**（2026.05.28）/ **Opus 4.7**（2026.04.16）/ **Opus 4.6** / **Sonnet 4.6** —— Opus 线已由 Opus 5 取代，Sonnet 线已由 Sonnet 5 取代。**Opus 4.1 已废弃，2026-08-05 退役**，官方指定迁移目标为 `claude-opus-5`。

### Claude Opus 5

- **模型 ID**：`claude-opus-5`
- **公司**：Anthropic
- **时间**：2026 年 7 月 24 日
- **上下文**：**1M tokens（默认即最大，不存在更小的 context 变体）**，最大输出 128K tokens
- **定价**：**$5 / $25 per 1M input/output tokens** —— 与 Opus 4.8 完全持平，为 Fable 5（$10/$50）的一半
- **Fast mode**：约 2.5× 默认速度，价格为基础价的 2 倍（即 $10/$50）；**仅 Claude API 提供**，Claude Code 中走 usage credits
- **数据留存**：general access **无留存要求**（对比 Fable 5 强制 30 天且不可用于 ZDR）
- **产品侧定位**：Claude Max 的**新默认模型**、Claude Pro 上可用的最强模型
- **官方定位**：接近 Fable 5 的前沿智能，但价格只有一半；Fable 5 仍是官方口径的最高能力档

#### 能力结论（⚠️ 官方仅公布图表与相对描述，未给出绝对分数）

> Anthropic 发布页中 Frontier-Bench v0.1 / CursorBench / ARC-AGI 3 / GDPval-AA v2 / OSWorld 2.0 / HLE / AutomationBench / DeepSearchQA 的结果**全部以图片图表呈现**，正文未给任何具体数值。因此本节只保留官方原文的相对表述，**不填具体百分比**。

- **SOTA 声明有明确范围**：在 Frontier-Bench、GDPval-AA 这类 **coding 与 knowledge work 评测**上是新 SOTA；**网络安全任务上仍落后于 Mythos 5**
- **Frontier-Bench v0.1**：超过所有其他模型，性能相比 Opus 4.8 **翻倍以上**，且单任务成本更低
- **CursorBench 3.2**（max effort）：距 Fable 5 峰值 **0.5% 以内**，单任务成本仅一半；在 high / xhigh / max 各档上，给定成本下的性能优于所有其他模型
- **ARC-AGI 3**（新颖问题求解）：约为次优模型的 **3 倍**
- **Zapier AutomationBench**：同等单任务成本下通过率约为次优模型 **1.5×**；即使最低 effort 档也超过所有其他模型
- **OSWorld 2.0**（Computer Use）：任意给定成本下优于所有其他模型，以**约 1/3 的成本**超过 Fable 5 的最好成绩
- **生命科学**：所有内部生命科学评测均优于 Opus 4.8；有机化学（如从光谱数据推断分子结构）**+10.2pp**，蛋白序列变异对功能影响预测 **+7.7pp**
- **对齐**：自动化行为审计中为 Anthropic 至今**最对齐模型**，整体 misaligned behavior 得分 **2.3**（近期模型最低），优于 Opus 4.8 / Sonnet 5 / Fable 5；欺骗行为发生率最低、最不易被诱导滥用
- **视觉输出**：可生成显著更强的可视化产物（如交互式风洞模拟、细胞结构交互图）

> ⚠️ **Frontier-Bench 脚注（重要）**：该结果为 Anthropic **内部运行**（mini-SWE-agent harness + GKE 后端，每任务 5 次取均值），且 **Opus 5 与 Fable 5 被安全分类器拒答时均由 Opus 4.8 兜底作答**。因此该对比并非纯模型对比，引用时需说明。

#### 行为特征（官方与早期客户观察）

Opus 5 的核心改进被官方归纳为**自我验证与反复迭代直到成功**，而非单纯的分数提升：

- Frontier-Bench 某任务要求根据机械零件图纸写 FreeCAD 建模代码，但**故意不给模型任何直接查看图纸的手段**——Opus 5 自己写了一条计算机视觉流水线从原始像素提取几何信息，再重建出完整零件，且可重复成功；同条件下其他模型 5 次尝试均失败
- 面对某流行开源包管理器的真实 bug，Opus 5 找到根因并修掉了社区补丁漏掉的边界情况；对比模型只修了表面症状就报告已解决
- 某交易公司工程师用它在单次会话内构建了新交易所的行情数据接入；此前模型即使给了详细方案也无法完成。因找不到可校验的实时数据源，Opus 5 自建了测试 harness 来验证解析正确性

| 客户 / 场景 | 结论 |
|---|---|
| Cognition / Devin | FrontierCode 1.1 上以一半成本逼近 Fable 级；擅长困难调试与根因分析 |
| Cursor | CursorBench 上略低于 Fable 5，行为特征高度接近 |
| Zapier | AutomationBench 榜首，且未比此前 Claude 模型多花 token；此前模型均未通过，Opus 5 达 100% |
| Lovable | 最难 agentic coding 任务较 Opus 4.7 **+22%**，且 run 间方差显著更小 |
| Box | 整体优于 Opus 4.8 **+8%**；数据分析 +11%，尽职调查 +17% |
| 法律 Agent 场景 | 公司治理、仲裁等领域增益最大；低推理档即可维持质量，较 Opus 4.8 max 推理平均少生成 **26%** token |
| 某交易基准 | 约 Opus 4.8 **1/7** 的推理 token、不到一半延迟 |
| 某金融建模 | 跨 effort 档平均准确率 **+9pp**，轮次与工具调用少 1/3，耗时降 60% |
| 前端评测场景 | 会主动用浏览器以桌面与手机宽度自查页面，发现并修复移动端折叠遮挡与按钮出屏问题 |
| Kiro | 已支持 Opus 5，面向长程多步 agentic coding |

#### 安全护栏：从领域级封禁改为任务阶段级切分

这是 Opus 5 相对 Fable 5 最实质的改进，也解决了 Fable 5 「静默降级」带来的正当用例误伤问题。

- Anthropic **刻意未在 cyber 任务上训练** Opus 5；其 cyber 能力提升纯粹来自**通用能力增强的溢出**
- 分类器触发频率比 Fable 5 **低约 85%**
- 护栏按**任务阶段**而非知识领域切分：

| 环节 | 处置 |
|---|---|
| 源码级漏洞发现 | ✅ 允许 |
| 二进制漏洞扫描（更常与恶意行为关联） | ❌ 阻断 |
| 渗透测试 | ❌ 阻断 |
| exploit 生成 | ❌ 阻断 |

- **依据**：OSS-Fuzz 评测双轴结果——**发现漏洞**上 Opus 5 与 Mythos 5 接近，**开发 exploit** 上远落后于 Mythos 5。即瓶颈仍卡在「武器化」这一环，因此可以安全放宽「发现」环节
- **降级行为**：Claude.ai / Claude Code / Claude Cowork 中被标记请求默认降级到 Opus 4.8；API 侧也可开启降级
- **Cyber Verification Program（CVP）**：已加入的企业与安全研究者可直接获得限制更少的 Opus 5 版本
- **生物方向**：护栏与 Opus 4.8 同级，因此 Opus 5 成为**当前最强的通用可得科研模型**；Fable 5 上被拦的生物类请求**改为路由到 Opus 5**（此前是 Opus 4.8）。但长程自主科研任务仍以 Mythos 5 更强
- **整体安全结论**：Opus 5 未推进危险两用能力前沿，在生物研究与攻击性网络安全两方面均仍落后于 Mythos 5

#### API 迁移注意事项（易踩坑）

1. **thinking 默认开启**（adaptive；省略 `thinking` 等价于 `{type: "adaptive"}`）
2. `thinking: {type: "disabled"}` **仅在 effort ≤ high 时可用**，与 `xhigh` / `max` 同用返回 **400**
3. 原始 thinking token **永不返回**
4. effort 阶梯完整支持至 `max`
5. **Prompt cache 最小块降为 512 token**（Opus 4.8 为 1024）
6. **独立限流池**，不与 Opus 4.x 合并池共享——迁移需重新申请配额
7. 安全分类器可返回 `stop_reason: "refusal"`，需在读取 `content` 前处理
8. 相对 Opus 4.8 是**同价 drop-in 升级**，特性集一致

#### 同期发布的两项 beta

- **会话中途变更工具集**：对话进行中可修改 Claude 可用的工具，**不会失效 prompt cache**
- **API 自动降级**：被安全分类器标记的 Opus 5 / Fable 5 请求可自动路由到其他模型，而非直接阻断；开启后 API 请求默认总是路由到当前可用的最佳模型

---

### Claude Fable 5

- **模型 ID**：claude-fable-5
- **公司**：Anthropic
- **时间**：2026 年 6 月 9 日
- **上下文**：**1M tokens**，最大输出 128K tokens
- **定价**：$10/$50 per 1M input/output tokens（Prompt Caching Write $12.50/MTok，Read $1/MTok）
- **定位**：Mythos-class 首个公开版本，介于 Opus 4.8 和限制级 Mythos 5 之间
- **核心升级**：
  1. **编程能力大幅领先**：SWE-Bench Pro 80.3%（+11.1pp vs Opus 4.8 69.2%），FrontierCode Diamond split 29.3%（远超 Opus 4.8 的 13.4% 和 GPT-5.5 的 5.7%）
  2. **长程 Agent 突破（days-long 自主执行）**：在 Agent Harness（Claude Code / Claude Managed Agents）中可连续工作数天，官方 Prompting Guide 明确「autonomous runs can extend for hours」；Stripe 用 1 天完成原本 50M 行 Ruby codebase 需 2 个月才能完成的迁移；Slay the Spire 持久记忆测试下表现提升 3× vs Opus 4.8
  3. **主动自验证（Proactive Self-Verification）**：自动编写测试代码校验自己写的代码；用 Vision 比对产出物与原始设计稿；长任务中按固定间隔主动自检；进展汇报前强制审计工具结果，消除虚构进度报告
  4. **并行子 Agent 委托**：比上代显著更可靠地派遣和维持多个并行子 Agent，可信赖地管理长时间运行的子 Agent 通信
  5. **视觉能力 SOTA**：可从截图重建 web app 源码；完整通关 Pokémon FireRed 仅凭原始游戏截图（无地图辅助）；GDP.pdf（视觉文档推理）29.8% 领跑竞品
  6. **内置降级保护**：涉及**网络安全、生物化学、模型蒸馏**的查询自动由 Opus 4.8 代答，发生频率 <5% 会话。这意味着约 1/20 的会话实际运行的不是 Fable 5
  7. **知识工作领先**：Hebbia Finance Benchmark SOTA，IMC 交易分析评测全面领先；GDP.pdf 29.8% > GPT-5.5 24.9% > Opus 4.8 22.5%
  8. **Token 效率更高**：同等任务下 token 消耗优于前代模型
- **可用渠道**：Claude API（claude-fable-5）、Amazon Bedrock；订阅计划（Pro/Max/Team/Enterprise）含免费期至 2026.06.22，之后需用 usage credits
- **注意**：订阅用户免费使用窗口 2026.06.22 截止，之后回归前须等容量扩充

#### Fable 5 编程基准对比

| 基准 | Fable 5 | Opus 4.8 | GPT-5.5 | Gemini 3.1 Pro |
|------|---------|----------|---------|----------------|
| SWE-Bench Pro | **80.3%** | 69.2% | 58.6% | 54.2% |
| FrontierCode Diamond | **29.3%** | 13.4% | 5.7% | — |
| GDP.pdf（视觉）| **29.8%** | 22.5% | 24.9% | 16.7% |
| BioMysteryBench（fallback至Opus 4.8）| 40.0% | 40.0% | — | — |
| ExploitBench（fallback至Opus 4.8）| 40.0% | 40.0% | 34.0% | — |

> 注：Fable 5 在网络安全/生物查询上降级至 Opus 4.8 作答，因此其公开分数等于 Opus 4.8 的分数；Mythos 5（无限制版）在这些领域远超前者。

---

### Claude Mythos 5

- **模型 ID**：claude-mythos-5
- **公司**：Anthropic
- **时间**：2026 年 6 月 9 日（限制访问）
- **上下文**：**1M tokens**，最大输出 128K tokens
- **定价**：$10/$50 per 1M input/output tokens（与 Fable 5 相同）
- **定位**：Fable 5 同底座模型，**去除了网络安全限制**；目前仅通过 Project Glasswing 向美国政府网络防御者和关键基础设施提供商开放
- **核心能力（对比 Fable 5/Opus 4.8）**：
  1. **网络安全无上限**：ExploitBench 78.0%，约为 Opus 4.8（40.0%）的 2 倍，远超 GPT-5.5（34.0%）
  2. **生物科学研究**：BioMysteryBench 46.1% > Opus 4.8（40.0%）> Mythos Preview（29.6%）；蛋白质设计加速约 10×，14 个靶点中 9 个获强候选；某 E. coli 蛋白质新机制假设已被另一实验室独立证实
  3. **独立科研能力**：138 物种单细胞数据训练的基因组学模型，性能超过 Science 期刊论文发表的模型，且参数量仅为其 1/100
- **访问限制**：仅 Project Glasswing 合作伙伴；另有独立生物安全研究轨道（保留网络安全限制，仅开放生物化学限制）计划向特定研究人员开放
- **合规要求**：所有 Mythos-class 流量须 30 天数据留存，人工访问日志，自动删除；不用于训练

#### Mythos 5 关键基准

| 基准 | Mythos 5 | Fable 5（降级后） | Opus 4.8 | Mythos Preview |
|------|----------|-----------------|----------|----------------|
| ExploitBench | **78.0%** | 40.0% | 40.0% | 69.0% |
| BioMysteryBench | **46.1%** | 40.0% | 40.0% | 29.6% |
| SWE-Bench Pro | **80.3%** | **80.3%** | 69.2% | 77.8% |

> 来源：[Anthropic June 9, 2026 发布公告](https://www.anthropic.com/news)；[Vellum AI 基准分析](https://www.vellum.ai/blog/claude-fable-5-and-mythos-5-benchmarks-explained)

---

### Claude Opus 4.8

- **模型**：claude-opus-4-8
- **公司**：Anthropic
- **时间**：2026 年 5 月 28 日
- **上下文**：**1M tokens**，最大输出 128K tokens
- **定价**：$5/$25 per 1M input/output tokens（与 Opus 4.7 持平）
- **场景**：最高精度推理、复杂长文本分析、代码生成、企业级 Agent
- **核心升级**：
  1. **编程能力全面提升**：SWE-Bench Pro 69.2%（+4.9pp vs 4.7），SWE-Bench Verified 88.6%（+1.0pp），Terminal-Bench 74.6%（+8.5pp）
  2. **诚实度 4 倍提升**：模型漏报代码缺陷的概率降至原来的 1/4，不再假装无 bug，被社区视为比 benchmark 数字更重要的体验升级
  3. **知识工作突破**：GDPval-AA 1,890 分，领先 GPT-5.5（1,769）和 Gemini 3.1 Pro（1,314）
  4. **动态工作流**：Claude Code 新增 parallel subagents，单次会话可并行调度数百个子 Agent
  5. **effort 控制**：用户可调节 default / extra / max 三档推理深度，更高的 effort 等级可进一步改善质量
  6. **Fast mode 降价 3 倍**：$10/$50 per 1M tokens，速度 2.5×，仅为旧版 fast mode 的 1/3 价格
  7. **对齐水平达 Mythos 级**：首次在公开可用模型中达到 Mythos Preview 级别的对齐指标，Anthropic 预计数周内推 Mythos 级正式模型
  8. **Agentic 判断领先**：Online-Mind2Web（浏览器 Agent 基准）84%，超越 4.7 和 GPT-5.5
  9. **Tool calling 更高效**：用更少步骤完成相同任务；修复 4.7 的 comment-verbosity 过高和 tool-calling 一致性问题
  10. **法律 Agent 突破**：Legal Agent Benchmark 历史最高分，首个 all-pass 标准突破 10%
  11. **Messages API 系统条目**：开发者可在 messages 数组中插入 system entries，运行时更新指令而不破坏 prompt cache

#### 编程基准对比

| 基准 | Opus 4.8 | Opus 4.7 | GPT-5.5 | Gemini 3.1 Pro |
|------|----------|----------|---------|----------------|
| SWE-Bench Pro | **69.2%** | 64.3% | 58.6% | 54.2% |
| SWE-Bench Verified | **88.6%** | 87.6% | — | 80.6% |
| Terminal-Bench 2.1 | **74.6%** | 66.1% | 78.2% | 70.3% |
| HLE（带工具） | **57.9%** | 54.7% | 52.2% | 51.4% |
| OSWorld-Verified | **83.4%** | 82.8% | 78.7% | 76.2% |
| GDPval-AA | **1,890** | 1,753 | 1,769 | 1,314 |
| Online-Mind2Web | **84%** | — | <84% | — |

> 注：Terminal-Bench 对测试 harness 敏感。GPT-5.5 在 OpenAI 自有 Codex CLI 上得分 83.4%，但在公共 Terminus-2 harness 上为 78.2%。Opus 4.8 在同条件 Terminus-2 下 74.6%，对比 Gemini 3.1 Pro 的 70.3%。

#### 42 天快速迭代与版本策略

距上代 Opus 4.7（2026-04-16）仅 **42 天**，为 Anthropic 历史上最短 Opus 迭代间隔（此前约 70-75 天）。

**迭代动因**：
1. **修复 4.7 短板**：社区反馈 comment-verbosity 过高、tool-calling 不一致
2. **诚实性是 Agent 规模化前提**：4× 诚实性提升解锁大规模 Agent 部署
3. **竞争节奏加快**：GPT-5.5、Gemini 3.5 Pro/Flash 同期活跃
4. **为 Mythos 铺路**：在 Mythos 大规模开放前稳住旗舰位置

**版本发布策略**：Opus 先行 → Sonnet 1-4 周跟进 → Haiku 跳跃式更新（非每版本都跟）。

### Claude Opus 4.7

- **模型**：claude-opus-4-7
- **公司**：Anthropic
- **时间**：2026 年 4 月 16 日
- **上下文**：**1M tokens**，最大输出 128K tokens
- **场景**：最高精度推理、复杂长文本分析、代码生成、企业级 Agent
- **特点**：
  1. **视觉能力提升 3 倍**：多模态理解能力大幅增强
  2. **编程能力显著跃升**：编码 benchmark 领先 Opus 4.6
  3. **xhigh 推理等级**：高级推理能力
  4. **Task Budgets**：新增任务预算管理功能

### Claude Sonnet 5

- **模型 ID**：`claude-sonnet-5`
- **公司**：Anthropic
- **时间**：2026 年 6 月 30 日
- **上下文**：**1M tokens**，最大输出 128K tokens
- **定价**：**introductory $2 / $10 per 1M input/output tokens，有效期至 2026-08-31**；之后转标准定价 **$3 / $15**
- **定位**：至今**最 agentic 的 Sonnet 模型**——可制定计划、使用浏览器与终端类工具、自主运行；官方说法是数月前这些能力还需要更大更贵的模型才能做到
- **核心声明**：性能**接近 Opus 4.8 而价格更低**，在推理、工具使用、编程、知识工作等 agentic 关键面向上大幅超越 Sonnet 4.6
- **可用范围**：全计划可用——**Free 与 Pro 的默认模型**，Max / Team / Enterprise 均可用；同时上线 Claude Code 与 Claude Platform

#### 成本-性能曲线（官方图表结论）

> ⚠️ 官方 benchmark 对比表与成本-性能曲线**均为图片**，正文未给出 Sonnet 5 的绝对分数，此处只保留相对表述。

在 agentic search（BrowseComp）与 computer use（OSWorld-Verified）两项评测上：

- 对 Sonnet 4.6 是**严格改进**（strict improvement）
- 覆盖的**成本-性能选项区间比 Opus 4.8 更宽**
- **medium effort 下成本效率提升显著**；高 effort 档在部分任务上可**追平 Opus 4.8**
- 实际用法：Sonnet 5 与 Opus 4.8 之间可通过调 effort 档来找成本与性能的平衡点

> 📌 **Sonnet 4.6 分数修订（官方回溯修正）**：HLE 更换评分模型后，Sonnet 4.6 修正为 **34.6%（无工具）/ 46.8%（带工具）**；OSWorld-Verified 调整运行方式后，Sonnet 4.6 修正为 **78.5%**。两者均与 Sonnet 4.6 发布时公布的数字不同。

#### ⚠️ tokenizer 变更：定价不等于实际成本

Sonnet 5 使用**更新的 tokenizer**（同 Opus 4.7 引入的变更思路），代价是**同一输入会映射为更多 token，约 1.0–1.35×，视内容类型而定**。

官方明确说明：**introductory 定价就是为了让从 Sonnet 4.6 迁移到 Sonnet 5 大致成本中立**。因此：

- 2026-08-31 前迁移：约成本中立
- 2026-09-01 转 $3/$15 后：单价上浮叠加 token 量上浮，**实际账单涨幅会高于单价涨幅**，测算时不可只看单价

#### 安全与护栏

- 整体不良行为发生率**低于 Sonnet 4.6**，agentic 场景下更安全；更善于拒绕恶意请求、**更能抗住 prompt injection 的劫持尝试**；幻觉与迎合（sycophancy）率均低于 Sonnet 4.6
- 但在自动化行为审计中，其 misaligned behavior 率**高于能力更强的 Opus 4.8 与 Mythos Preview**
- **网络安全能力显著弱于当前 Opus 系列**：未刻意训练 cyber 任务；在 Firefox 147 漏洞 exploit 开发评测（与 Mozilla 合作，漏洞已在 Firefox 148 修复）中，**Sonnet 4.6 与 Sonnet 5 均从未成功开发出可用 exploit（均为 0.0%）**，Sonnet 5 仅部分成功率略高于 4.6——官方归因于通用智能提升而非专项训练
- **护栏强度**：默认开启 cyber 安全护栏，与 **Opus 4.7 / 4.8 同级**；因整体 cyber 风险被判定为低，护栏**显著宽松于 Fable 5**
- **CVP**：Sonnet 5 已纳入 Cyber Verification Program，当前覆盖原生 Claude Platform、AWS 上的 Claude Platform、Microsoft Foundry 中的 Claude（Azure 与 Anthropic 托管），Google Vertex 即将支持；已入项组织自动获得同等访问无需重新申请。**官方建议：需降低护栏的网络安全工作用 Opus 4.8**

#### API 行为

- adaptive thinking 默认开启（省略 `thinking` 即跑 adaptive）；手动 `budget_tokens` 已移除；非默认 sampling 参数会被拒绝
- `effort` 支持 `low` / `medium` / `high` / `xhigh` / `max`
- 高分辨率视觉（2576px）
- 为适应高 effort 档的更大 token 用量，官方已上调 Chat / Cowork / Claude Code / Claude Platform 的限流额度

---

### Claude Sonnet 4.6

- **模型**：`claude-sonnet-4-6`
- **公司**：Anthropic
- **时间**：2026 年 3 月
- **上下文**：**1M tokens**，最大输出 128K tokens
- **状态**：已由 Sonnet 5 取代，不建议新项目选用
- **场景**：均衡推理、性价比
- **特点**：编程/推理能力均衡；支持 adaptive thinking（推荐）
- **已修订分数**：HLE 34.6%（无工具）/ 46.8%（带工具）；OSWorld-Verified 78.5%

### Claude Haiku 4.5

- **模型**：`claude-haiku-4-5`（官方全 ID `claude-haiku-4-5-20251001`）
- **公司**：Anthropic
- **时间**：[⚠️ 待确认]
- **上下文**：200K tokens，最大输出 64K tokens
- **场景**：极速响应、代码补全、简单任务
- **特点**：Claude 家族最快、最具成本效益的模型

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **高精度推理** | Constitutional AI 安全对齐，强调输出安全性与无害性 |
| **长上下文** | Fable 5 / Opus 5 / Opus 4.x / Sonnet 5 / Sonnet 4.6 均为 1M tokens，标准 API 价格无长上下文附加费 |
| **代码生成** | Opus 5 在 Frontier-Bench / GDPval-AA 等 coding·knowledge work 评测上为 SOTA（官方未公布绝对分数）；Fable 5 SWE-Bench Pro 80.3% |
| **多模态** | 支持图片等多模态输入；Sonnet 5 支持高分辨率视觉（2576px）；Opus 5 可产出显著更强的可视化产物 |
| **Agent 能力** | Claude Code 编程 Agent；全系列支持 effort 阶梯调参（至 max）与 adaptive thinking；Opus 5 强于自我验证与长程迭代；Sonnet 5 为至今最 agentic 的 Sonnet |
| **安全对齐** | Opus 5 为 Anthropic 至今最对齐模型（misaligned behavior 2.3，近期最低）；Sonnet 5 抵抗 prompt injection 能力优于 Sonnet 4.6 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 价格 | 较高 | Fable 5 $10/$50；Opus 5 / Opus 4.8 $5/$25（Fast mode 翻倍）；Sonnet 5 $2/$10→$3/$15；详见下方定价表 |
| 网络安全护栏 | 分类器拦截 | 渗透测试 / exploit 生成 / 二进制漏洞扫描被阻断；需降低护栏需申请 CVP |
| Fable 5 数据留存 | 强制 30 天 | 不可用于 ZDR；Opus 5 / Opus 4.x 无此限制 |
| Sonnet 5 tokenizer | token 量 ×1.0–1.35 | 同输入映射为更多 token，测算成本不可只看单价 |
| Anthropic 访问 | 需翻墙 | 国内无法直接访问 |
| 推理延迟 | 非极致优化 | 定位高精度，非超低延迟 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 日常主力 / 性价比最优 | **Opus 5** | coding·knowledge work SOTA，Fable 5 半价、无数据留存要求 |
| 极限难度任务 | Fable 5 | 官方最高能力档；CursorBench 峰值仍领先 Opus 5（差距 <0.5%） |
| 大规模 Agent / 成本敏感 | **Sonnet 5** | 最 agentic 的 Sonnet，medium effort 成本效率最优，高 effort 可追平 Opus 4.8 |
| 极速响应 | Haiku 4.5 | 最快、最具成本效益 |
| 科学研究（通用可得） | **Opus 5** | 护栏与 Opus 4.8 同级，有机化学 +10.2pp / 蛋白 +7.7pp vs Opus 4.8 |
| 需降低护栏的网络安全工作 | Opus 4.8（官方建议）/ CVP 版 Opus 5 | Sonnet 5 cyber 能力显著偏弱，不适用 |
| 企业级合规（不接受数据留存） | Opus 5 / Sonnet 5 | Fable 5 强制 30 天留存且不可用于 ZDR |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 预算敏感用户 | 价格较高 |
| 超高并发低成本 | 非性价比路线 |
| 国内直接访问 | 需翻墙 |

## 定价（API）

| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) | Prompt Cache Write | Prompt Cache Read |
|------|---------------------|---------------------|-------------------|-------------------|
| **Claude Fable 5** | $10.00 | $50.00 | $12.50 | $1.00 |
| **Claude Mythos 5** | $10.00 | $50.00 | — | — |
| **Claude Opus 5** | $5.00 | $25.00 | [⚠️ 待核实] | [⚠️ 待核实] |
| **Claude Opus 5 Fast** | $10.00 | $50.00 | — | — |
| **Claude Opus 4.8** | $5.00 | $25.00 | $6.25 | $0.50 |
| **Claude Opus 4.8 Fast** | $10.00 | $50.00 | — | — |
| **Claude Sonnet 5**（introductory，至 2026-08-31） | **$2.00** | **$10.00** | [⚠️ 待补充] | [⚠️ 待补充] |
| **Claude Sonnet 5**（标准价，2026-09-01 起） | **$3.00** | **$15.00** | [⚠️ 待补充] | [⚠️ 待补充] |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | $3.75 | $0.30 |
| **Claude Haiku 4.5** | $1.00 | $5.00 | $1.25 | $0.10 |

> 来源：[Opus 5 官方公告](https://www.anthropic.com/news/claude-opus-5)（2026.07.24）、[Sonnet 5 官方公告](https://www.anthropic.com/news/claude-sonnet-5)（2026.06.30）、[Anthropic 官方定价页](https://www.anthropic.com/pricing)（2026.06.14 核实 Fable 5 / Opus 4.8 / Sonnet 4.6 / Haiku 4.5）

> ⚠️ **Opus 5 的 Prompt Caching 单价待核实**：官方公告未提及，`platform.claude.com` 定价页多次抓取超时。若沿用 Anthropic 惯用倍率（write 1.25×、read 0.1×）应为 $6.25 / $0.50，**但此为推算值、非官方值，不得引用**。已知变更：Opus 5 的 prompt cache **最小块从 1024 降为 512 token**。

> ⚠️ **Sonnet 5 真实成本提醒**：$2/$10 仅至 **2026-08-31**，之后转 $3/$15（+50%）。叠加新 tokenizer 带来的 **×1.0–1.35 token 量上浮**，官方只保证 introductory 期内从 Sonnet 4.6 迁移“大致成本中立”。向客户报价时必须同时告知这两重上浮。

> **价格对比参考**：Fable 5 / Mythos 5 是 Opus 5 与 Opus 4.8 的 **2 倍**；Opus 5 对 Opus 4.8 是**同价 drop-in 升级**，对 Fable 5 是**能力逼近 + 价格腰斩 + 免除 30 天留存**；早期 Opus 4.1 原价 $15/$75。

## 竞品对比

> ⚠️ **时效提醒**：下方两节对比定格于 2026.06（Fable 5 / Opus 4.8 时期）。**Opus 5（2026.07.24）发布后，coding 与 knowledge work 评测的 SOTA 已换为 Opus 5**，但官方未公布其绝对分数，因此无法将 Opus 5 列入下表。引用下表时需说明“这是 Opus 4.8 / Fable 5 口径”。

### Fable 5 vs 全家桶（2026.06.09）

| 维度 | Fable 5 | Opus 4.8 | GPT-5.5 | Gemini 3.1 Pro |
|------|---------|----------|---------|----------------|
| SWE-Bench Pro | **80.3%** | 69.2% | 58.6% | 54.2% |
| FrontierCode Diamond | **29.3%** | 13.4% | 5.7% | — |
| GDP.pdf（视觉） | **29.8%** | 22.5% | 24.9% | 16.7% |
| 定价（输入/输出） | $10/$50 | $5/$25 | — | — |

### Opus 4.8 vs Gemini 3.1 Pro

Opus 4.8 发布后，Anthropic 与 Google 在 AI Coding 核心基准上的差距进一步拉大：

| 维度 | Opus 4.8 | Gemini 3.1 Pro | 差距 |
|------|----------|----------------|------|
| SWE-Bench Pro | **69.2%** | 54.2% | +15.0pp |
| SWE-Bench Verified | **88.6%** | 80.6% | +8.0pp |
| Terminal-Bench 2.1 | **74.6%** | 70.3% | +4.3pp |
| HLE（带工具） | **57.9%** | 51.4% | +6.5pp |
| OSWorld-Verified | **83.4%** | 76.2% | +7.2pp |
| GDPval-AA | **1,890** | 1,314 | +576 分 |

**例外**：Finance Agent v2 上 Gemini 3.5 Flash（57.9%）领先 Opus 4.8（53.9%），说明 Google 在小模型+垂直金融场景有独特优势。

**核心判断**：Opus 4.8 的发布使 Google 在 AI Coding 领域追赶 Anthropic 的窗口期进一步延长。仅凭 Gemini 3.1 系列不足以弥合差距，需要 AlphaCode 产品化或 Gemini 3.x 后续重大迭代才有望缩小结构性差距。

## 参考资料

- [Anthropic 官方博客 — Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5)（2026.07.24）
- [Anthropic 官方博客 — Introducing Claude Sonnet 5](https://www.anthropic.com/news/claude-sonnet-5)（2026.06.30）
- [anthropics/skills 官方模型目录](https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/models.md) — 模型 ID / 上下文与输出上限 / API 破坏性变更 / 废弃时间表的权威清单
- [Anthropic 官方定价页](https://www.anthropic.com/pricing)（2026.06.14 核实）
- [Vellum AI: Fable 5 & Mythos 5 Benchmarks Explained](https://www.vellum.ai/blog/claude-fable-5-and-mythos-5-benchmarks-explained)
- [AppStackBuilder: Claude Fable 5 & Mythos 5 Launch](https://appstackbuilder.com/blog/claude-fable-5-mythos-5-launch-2026)
- [Forbes: Anthropic's Fable 5 AI Model Offers More Power At A Higher Price](https://www.forbes.com/sites/ronschmelzer/2026/06/10/anthropic-fable-5-ai-model-cost/)
- [Anthropic 官方博客 — Claude Opus 4.8](https://www.anthropic.com/news/claude-opus-4-8)
- [Claude Fable 5 官方产品页](https://www.anthropic.com/claude/fable)
- [Prompting Claude Fable 5（官方 Prompting Guide）](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)
- [Anthropic 官方博客 — Claude Opus 4.7](https://www.anthropic.com/news/claude-opus-4-7)
- [TechCrunch: Anthropic releases Opus 4.8 with new dynamic workflow tool](https://techcrunch.com/2026/05/28/anthropic-releases-opus-4-8-with-new-dynamic-workflow-tool/)
- [Anthropic API 文档](https://docs.anthropic.com)
- [Claude API Platform](https://console.anthropic.com)
- 定价：https://platform.claude.com/docs/zh-CN/about-claude/pricing

> ⚠️ **信源踩坑记录（2026-08-01）**：`platform.claude.com` 各页面存在持续抓取超时；其定价页的**搜索摘要**曾给出 Sonnet 5 为 $1/$5 → $1.50/$7.50，**经官方发布页逐字比对证实为错配、完全错误**。核实定价必须以 `anthropic.com/news/*` 发布页或官方定价页原文为准，**不可采信搜索摘要**。

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-08-01 | 合并 ai-native-expert 素材：**新增 Claude Opus 5（2026.07.24）**完整章节（$5/$25 同价 Opus 4.8 / Fable 5 半价、1M、无数据留存、512 cache 最小块、独立限流池、thinking disabled 仅 effort≤high、护栏从领域级下沉到任务阶段级 + OSS-Fuzz 双轴依据、CVP、两项 beta）；**新增 Claude Sonnet 5（2026.06.30）**完整章节（$2/$10 introductory→$3/$15、tokenizer ×1.0–1.35、Free/Pro 默认模型、Firefox 147 exploit 评测 0.0%、护栏同 Opus 4.7/4.8）；**版本代际校正**：“当前最强=Fable 5”改为“Fable 5 为最高能力档、Opus 5 为 coding/knowledge work SOTA”，主推表重构为 4 款并将 Opus 4.8/4.7/4.6/Sonnet 4.6 移入历史模型；**修正 Sonnet 4.6 上下文 200K→1M**、模型 ID 纠错、Haiku 4→Haiku 4.5；补记 Opus 4.1 于 2026-08-05 退役；修复核心能力表格式错误；记录定价信源踩坑（搜索摘要不可采信） |
| 2026-06-15 | 合并 ai-native-expert 素材：Fable 5 新增「days-long 自主执行」和「主动自验证（Proactive Self-Verification）」详细行为描述（来自官方 Prompting Guide）；补充并行子 Agent 委托能力 |
| 2026-06-14 | 新增 Claude Fable 5（2026.06.09）与 Claude Mythos 5 完整信息：定价 $10/$50、Mythos-class 架构、自动降级机制、SWE-Bench Pro 80.3%、关键 benchmarks；更新 Haiku 为 4.5；定价表补全 Prompt Caching；更新竞品对比 |
| 2026-06-03 | 合并 ai-native-expert 素材：新增 Agentic 基准（Online-Mind2Web 84%）、Legal Agent Benchmark、Tool calling 改进、Messages API 系统条目、42 天迭代策略分析 |
| 2026-05-31 | 更新 Opus 4.8（2026.05.28 发布），包含关键基准（SWE-Bench Pro 69.2%等）、诚实度4×提升、fast mode降价、与Gemini 3.1 Pro竞品对比 |
| 2026-05-28 | 新建文档，首次提炼 Claude Opus 4.7 系列信息 |