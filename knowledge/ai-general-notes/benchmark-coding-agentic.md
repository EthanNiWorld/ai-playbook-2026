# AI Agent Benchmark 三维度评估框架

> 最后更新: 2026-07-20
> 领域: AI Engineering / AI Coding
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 评估 AI Agent 需看三个正交维度：**操作执行力**（SWE-bench Pro / Terminal-Bench / OSWorld）、**学术推理力**（HLE）和**知识工作力**（GDPval-AA）
**核心价值**: 编码产品看操作执行力；科研场景看学术推理力；企业专业脑力劳动（法律/财务/医疗）看知识工作力。三者正交，不会 HLE ≠ 不会思考
**相关产品**: [Claude API](../anthropic/claude-api.md), [Qwen](../../alibaba-ai-hub/maas/qwen.md), [Gemini](../google/maas/gemini.md), [GPT-5 系列](../openai/gpt-5-series.md)
<!-- SUMMARY_END -->

## 是什么

AI Agent Benchmark 是评估 AI 模型/Agent 自主完成任务能力的标准化测试集。评估需从三个正交维度切入：

**维度一：操作执行力**（Agent 能不能干活）——按交互界面递进：

| 层级 | Benchmark | 交互方式 | 核心能力 | 典型场景 |
|------|-----------|----------|----------|----------|
| 代码层 | SWE-bench Pro | 纯 CLI（读 repo → 生成 patch） | 跨文件代码修改 | AI Coding 工具 |
| 终端层 | Terminal-Bench 2.1 | CLI 终端（多步命令执行） | 系统操作能力 | DevOps/SRE |
| 图形层 | OSWorld-Verified | GUI 桌面（鼠标/键盘/屏幕理解） | 图形界面操作 | RPA/Computer Use |

三层共享底层能力（长上下文理解 + 工具调用 + 多步规划），交互界面逐层升级。

**维度二：学术推理力**（Agent 能不能解专家级学术题）——独立于交互维度：

| Benchmark | 测什么 | 典型场景 |
|-----------|--------|----------|
| HLE（Humanity's Last Exam） | 博士级学科知识推理（数学/物理/生物/人文） | 科研辅助、学术问答、领域专家级知识推理 |

> ⚠️ **HLE ≠ 通用思考能力**：HLE 测的是“学术知识推理”——需要深厚领域知识才能作答的专家级题目。不会 HLE 不代表不会思考，模型可能在工程推理、策略推理、规划推理等其他维度表现优秀。HLE 只是推理能力光谱中的一个维度，不是推理能力的全部。

**维度三：知识工作力**（Agent 能不能做专业脑力劳动）——独立于前两个维度：

| Benchmark | 测什么 | 典型场景 |
|-----------|--------|----------|
| GDPval-AA（Gross Domestic Product Value - Artificial Analysis） | 对 GDP 贡献最大行业中的知识工作能力 | 法律文书、财务分析、医疗摘要、咨询报告 |

> 三个维度正交而非递进：一个模型可以“手巧但学问不深”（操作强 HLE 低），也可以“学问深但不太会办事”（HLE 高 GDPval-AA 低）。对企业客户来说，GDPval-AA 可能是最直接相关的指标。

## 核心原理

### 1. SWE-bench 家族三代演进

| 版本 | 提出方 | 时间 | 题目数 | 核心特点 |
|------|--------|------|--------|----------|
| SWE-bench | 普林斯顿 NLP（Carlos E. Jimenez 等） | 2023-10 | 2,294 | 12 个 Python 开源仓库的 GitHub Issue/PR，开源在 HuggingFace，MIT 协议 |
| SWE-bench Verified | OpenAI + SWE-bench 原作者 | 2024-08 | 500 | 从 2,294 题中人工筛选，确认描述清晰、可解、验证可靠 |
| SWE-bench Pro | Scale AI（Xiang Deng, Jeff Da 等） | 2025（ICLR 2026） | 1,865 | 分 Public(731) / Commercial(276) / Held-out(858) |

**数据污染已成事实**：OpenAI 2025 年公开声明不再评估 SWE-bench Verified，原因包括数据污染（2,294 道题全部来自公开 GitHub）、测试缺陷（flawed tests + shortcut-reward 导致分数虚高）、SOTA 已超 70% 区分度不足。

**SWE-bench Pro 三重抗污染设计**：
1. **GPL/Copyleft 许可证壁垒**：Public 集选用 GPL 等 copyleft 仓库，法律上不能用于商业训练
2. **Commercial 集**：276 道题来自创业公司私有代码库，完全未公开
3. **Held-out 集**：858 道题用不同仓库，保持私有用以检测过拟合

效果：前沿模型 Verified >70%，Pro Public 最高 ~23.3%，Commercial ~17.8%。

### 2. Terminal-Bench 2.1

- 提出方：斯坦福大学 CRFM + Laude Institute
- 核心人物：John Yang 等（SWE-bench 核心贡献者）
- 定位：评估 AI Agent 在真实终端环境中的操作能力（系统管理、安全、ML 训练等）
- 内置 canary GUID 检测数据泄漏
- 当前版本 2.1（基于 2.0 Verified 改进），3.0 开发中

### 3. OSWorld-Verified

- 原始 OSWorld 论文：CMU/OSU 研究者 2024 年提出，369 个真实桌面任务（Ubuntu/Windows/macOS）
- OSWorld-Verified：人工验证的高质量子集（类似 SWE-bench → SWE-bench Verified 的模式）
- 发布时间为 2026-06-09 [来源: 用户口述] ⚠️ 待官方验证
- 核心场景：需要登录、输入用户名密码、通过图形验证码等 GUI 操作任务 [来源: 用户口述]

### 4. Humanity's Last Exam（HLE）

- 提出方：Center for AI Safety + Scale AI（2025-01，Nature 正式发表）
- 规模：2,500 道专家级题目，覆盖数学、自然科学、人文学科等数十个领域
- 设计目标：测试 AI 是否具备顶尖领域专家的推理能力
- 当前 SOTA：Claude Opus 4.8 57.9%（带工具），远未饱和
- 与操作执行力 benchmark 的本质区别：操作类测“手巧”（不同界面下的任务执行），HLE 测“学术知识深度”（博士级学科推理），两者正交而非递进。不会 HLE ≠ 不会思考，只代表学术知识推理这个特定维度不够强

### 5. GDPval-AA（Gross Domestic Product Value - Artificial Analysis）

- GDPval：OpenAI 2025 年 9 月推出，灵感来自宏观经济指标 GDP [来源: 用户口述]
- 设计目标：衡量 AI 在对美国 GDP 贡献最大的行业中完成知识型工作的能力 [来源: 用户口述]
- AA：Artificial Analysis（第三方独立评测机构），该评测的执行方 [来源: 用户口述]
- 覆盖：9 大行业、44 个职业、1,320 个任务
- 评分：Elo 评分制
- 与 HLE 的本质区别：HLE 测“你能不能通过博士资格考试”（学术知识深度），GDPval-AA 测“你能不能胜任律师/分析师/咨询顾问的日常工作”（专业办公能力）

## 关键认知框架

### 核心洞察 1：三个维度对应五类真实场景

**操作执行力维度**（按交互界面选择）：

| 场景类型 | 适用 Benchmark | 为什么选这个 |
|----------|---------------|-------------|
| AI Coding 工具（Qoder/Claude Code） | SWE-bench Pro | 核心工作是读代码 → 改代码 → 跑测试 |
| DevOps/SRE 自动化 | Terminal-Bench | 核心工作是在终端执行多步系统操作 |
| 企业 RPA / Computer Use / 桌面自动化 | OSWorld-Verified | 核心工作是操作 GUI（登录、填表、验证码） |

**学术推理力维度**（独立判断）：

| 场景类型 | 适用 Benchmark | 为什么选这个 |
|----------|---------------|-------------|
| 科研辅助 / 学术问答 / 领域专家级知识推理 | HLE | 需要博士级学科知识推理能力，解决前沿学术问题 |

**知识工作力维度**（独立判断）：

| 场景类型 | 适用 Benchmark | 为什么选这个 |
|----------|---------------|-------------|
| 法律文书 / 财务分析 / 医疗摘要 / 咨询报告 | GDPval-AA | 需要专业脑力劳动能力，而非学术知识或代码能力 |

### 核心洞察 2：Benchmark 生态红皇后效应

- 模型变强 → 旧 benchmark 被刷爆（SWE-bench Verified > 70%）→ 需要更难的
- 公开数据集天然被污染 → 必须引入私有集 + 法律壁垒（GPL）+ canary GUID
- OpenAI 2025 弃用 Verified 是行业转折信号
- 新一代 benchmark 共同特征：抗污染设计 + 人工验证 + 区分度保持

### 核心洞察 3：SWE-bench Pro 和 Terminal-Bench 走势"和谐"的原因

1. 都测 Agentic Coding 不同侧面：Pro = 跨文件代码修改（软件工程），TB = 终端多步操作（系统操作）
2. 共享底层能力：长上下文理解 + 工具调用 + 多步规划 + 代码生成
3. 都做了抗污染设计，保持了区分度
4. 互补而非重叠：两者同时高 = 全能型 Coding Agent

## 各厂商实现对照

### 前沿模型三维度表现

**操作执行力**：

| 模型 | SWE-bench Pro | Terminal-Bench 2.1 | OSWorld-Verified |
|------|:---:|:---:|:---:|
| Claude Opus 4.8 | **69.2%** | 74.6% | **83.4%** |
| GPT-5.5 | 58.6% | **78.2%** | 78.7% |
| Qwen3.7-Max | 60.6% | 74.5%（AA harness） | — |
| MiniMax M3 | 59.0% | 66.0% | [⚠️ 待补充] |
| GLM-5.1 | 58.4% | 58.7%（Claude Code harness） | [⚠️ 待补充] |
| Gemini 3.5 Flash | 55.1% | 76.2% | 78.4% |
| Gemini 3.1 Pro | 54.2% | 70.3% | 76.2% |
| DeepSeek-V4-Pro | 52.1% | [⚠️ 待确认 v2.1] | [⚠️ 待补充] |
| Qwen3.7-Plus | 57.6% | 47.0% [⚠️ AA TB-Hard] | 73.3% |

> 注：Terminal-Bench 列默认为 v2.1；标注“AA harness”表示来自 Artificial Analysis 统一 harness 评测；标注 [⚠️ AA TB-Hard] 的表示来自 AA 独立评测的 Terminal-Bench Hard 子集（统一 harness，与厂商自报分数不完全可比）。

**学术推理力**：

| 模型 | HLE |
|------|:---:|
| Claude Opus 4.8 | **57.9%** (w/ tools) / 49.8% (no tools) |
| GPT-5.5 | 52.2% (w/ tools) / 41.4% (no tools) |
| Gemini 3.1 Pro | 44.4% |
| Qwen3.7-Max | 41.4% |
| Gemini 3.5 Flash | 40.2% |
| Qwen3.7-Plus | 34.7% |
| DeepSeek-V4-Pro | [⚠️ 待补充] |
| GLM-5.1 | [⚠️ 待补充] |
| MiniMax M3 | [⚠️ 待补充] |

> 注：HLE 分数受测试条件影响（是否带工具、harness 配置）。Claude Opus 4.8 的 57.9% 来自 Anthropic 自报（带工具），AA 独立评测（纯文本）为 45.7%。

**知识工作力**：

| 模型 | GDPval-AA (Elo) |
|------|:---:|
| Claude Opus 4.8 | **1,890** |
| GPT-5.5 (xhigh) | 1,769 |
| MiniMax M3 | 1,668 (open-weight highest) |
| Gemini 3.5 Flash (high) | 1,656 |
| DeepSeek-V4-Pro (reasoning, high) | 1,558 |
| Qwen3.7-Max | 1,541 |
| GLM-5.1 (reasoning) | 1,535 |
| Qwen3.7-Plus | 1,517 |
| Gemini 3.1 Pro | [⚠️ 待补充] |

> Source: [AA GDPval-AA Leaderboard](https://artificialanalysis.ai/evaluations/gdpval-aa) (queried 2026-06-14)
> Detailed product analysis: see vendor-specific documents

## 最佳实践

### 技术选型决策树

```
你的 Agent 场景需要什么能力？
│
├── 操作执行力（Agent 干活）
│   ├── 纯代码修改（读 repo → 生成 patch）→ 看 SWE-bench Pro
│   ├── 终端命令执行（DevOps/ML 训练）    → 看 Terminal-Bench 2.1
│   └── GUI 桌面操作（登录/填表/RPA）      → 看 OSWorld-Verified
│
├── 学术推理力（Agent 解学术题）
│   └── 博士级学科知识推理（科研/学术）  → 看 HLE
│
└── 知识工作力（Agent 办事）
    └── 专业脑力劳动（法律/财务/医疗/咨询）→ 看 GDPval-AA
```

### 可迁移场景

- **企业 Agent 采购评估**：不应只看单一 benchmark，应根据实际工作流选择对应维度。对企业客户，GDPval-AA（知识工作力）可能是最直接相关的指标
- **Benchmark 可信度判断**：优先参考有抗污染设计的 benchmark（Pro > Verified），避免被虚高分数误导
- **模型迭代跟踪**：三个维度的 benchmark 同时提升 = 真正的全面进步，仅一个维度提升可能是针对性优化

## 常见误区

| 误区 | 事实 |
|------|------|
| SWE-bench Verified 高分 = 强编码能力 | Verified 已被数据污染，>70% 分数区分度不足，OpenAI 2025 年已公开弃用 |
| SWE-bench Pro 高分 = 什么都会 | Pro 只测代码修改（CLI），不测终端操作和 GUI 操作 |
| Terminal-Bench 和 SWE-bench 是竞争关系 | 两者互补：Pro 测软件工程，TB 测系统操作，共享底层能力 |
| OSWorld 就是 Terminal-Bench 的图形版 | 不完全对：OSWorld 测通用桌面操作（浏览器、桌面应用），Terminal-Bench 测纯命令行系统操作，任务类型本质不同 |
| HLE 高分 = 强 Agent | HLE 测的是学术知识推理，不测工具调用和多步执行；HLE 高但 SWE-bench/TB 低 = “学术强但干活一般” |
| 不会 HLE = 不会思考 | HLE 只是推理能力光谱中的一个维度（学术知识推理）；工程推理、策略推理、规划推理等同样重要，HLE 不覆盖这些 |
| 四层 benchmark 是递进关系 | 操作执行力、学术推理力、知识工作力是三个正交维度，不是“从低到高”的递进 |
| HLE 和 GDPval-AA 测的是同一回事 | HLE 测学术知识深度（博士考题），GDPval-AA 测专业办公能力（律师/分析师日常工作），两者完全不同 |

## 参考资料

- [SWE-bench Pro 论文] https://arxiv.org/html/2509.16941v1
- [SWE-bench 官网] https://www.swebench.com/
- [Scale AI Leaderboard] https://labs.scale.com/leaderboard/swe_bench_pro_public
- [OpenAI 弃用声明] https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- [Terminal-Bench 官网] https://www.tbench.ai/
- [OSWorld 论文] https://arxiv.org/abs/2404.07972
- [OSWorld 官网] https://os-world.github.io/
- [Gemini Flash 页面] https://deepmind.google/models/gemini/flash/
- [Claude Opus 4.8 页面] https://www.anthropic.com/news/claude-opus-4-8
- [HLE 论文] https://arxiv.org/abs/2501.14249
- [HLE Nature 发表] https://www.nature.com/articles/s41586-025-09962-4
- [HLE 官网] https://agi.safe.ai/
- [GDPval-AA 教育视角解读] https://fullstackeducator.substack.com/p/the-ai-benchmark-that-finally-matters

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-07-20 | 校验修复：Qwen3.7-Max TB 69.7[v2.0] → 74.5（AA harness v2.1）；GLM-5.1 TB 63.5[v2.0] → 58.7（Claude Code harness v2.1）；DeepSeek-V4-Pro 移除 v2.0 数值待确认 v2.1 |
| 2026-06-14 | 初始创建：SWE-bench 三代演进 + Terminal-Bench 2.1 + OSWorld-Verified 三层能力光谱；含用户口述 OSWorld-Verified 发布时间与 GUI 登录场景判断 [ 来源: 用户口述] |
| 2026-06-14 | 新增 HLE：四层能力光谱完整化；补充 HLE 基本信息、各模型得分 |
| 2026-06-14 | 架构重构：“四层光谱”→“双维度评估框架”（操作执行力 + 学术推理力），因 HLE 与前三层不在同一维度，正交而非递进 |
| 2026-06-14 | 修正 HLE 定位：“深度推理力”→“学术推理力”，HLE 测博士级学科知识推理而非通用思考能力，不会 HLE ≠ 不会思考 |
| 2026-06-14 | 新增维度三知识工作力（GDPval-AA）：三维度评估框架完整化；补充 GDPval-AA 基本信息、各模型 Elo 得分、与 HLE 的区别 [来源: 用户口述] |
| 2026-06-14 | GDPval-AA 分数修正与补充（AA 独立评测交叉验证）：MiniMax M3 从 1,495 修正为 1,668（原误用 M2.7 分数）；新增 DeepSeek-V4-Pro 1,558 / Qwen3.7-Max 1,541 / GLM-5.1 1,535 / Qwen3.7-Plus 1,517（均来自 artificialanalysis.ai） |
| 2026-06-14 | 三维度对照表补全 9 模型：操作执行力新增 GPT-5.5 / Gemini 3.1 Pro / MiniMax M3 / GLM-5.1 / DeepSeek-V4-Pro；学术推理力新增 Gemini 3.1 Pro，补充 AA text-only HLE 对比；知识工作力统一按 AA 独立评测 Elo 排序 |
