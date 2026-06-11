# OpenAI Codex — AI 编程 Agent 平台

> 最后更新: 2026-06-11
> 所属厂商: OpenAI
> 产品类别: AI Coding
> 状态: Published

<!-- SUMMARY_START -->
**定位**: OpenAI 的多形态 AI 编程 Agent 平台，覆盖 CLI / IDE / Web / 桌面应用五种入口，核心是"Agent 指挥中心"——多 Agent 编排、Git Worktree 隔离、Skills 生态
**适用**: 需要多 Agent 并行编程、云端沙箱执行、GitHub 自动化 PR 的开发者/团队
**不适用**: 仅需代码补全（用 Copilot）；需要 IDE 内嵌体验（用 Cursor/Qoder）
**竞品**: Claude Code（Anthropic 终端 Agent）、GitHub Copilot、Cursor、Kiro（AWS）
**常搭配**: ChatGPT Plus/Pro 订阅、GitHub 仓库
<!-- SUMMARY_END -->

> ⚠️ 素材截止：2026-06-09。模型版本/定价等可能已有更新，使用前请验证。

## 产品原理解析

### 一句话定位

2025 年重新打造的 Agentic Coding 平台——不是 2021 年的代码补全模型，而是让开发者编排和管理多个 AI 编程 Agent 并行工作的完整产品。

### 产品演进时间线

| 时间 | 里程碑 | 来源 |
|------|--------|------|
| 2025.04 | Codex CLI 开源发布（Apache 2.0，TypeScript） | [blakecrosley.com](https://blakecrosley.com/guides/codex) |
| 2025.05.16 | Codex Cloud Agent 上线（Pro/Enterprise），搭载 **codex-1** 模型 | [OpenAI 官方博客](https://openai.com/index/introducing-codex/) |
| 2025.06.03 | 扩展至 ChatGPT Plus 用户 | [morphllm.com](https://www.morphllm.com/codex-pricing) |
| 2025.09.23 | API 密钥访问开放 | [morphllm.com](https://www.morphllm.com/codex-pricing) |
| 2025.12 | **GPT-5.2-Codex** 发布，上下文压缩、大型重构能力提升 | [OpenAI 博客](https://openai.com/index/introducing-the-codex-app/) |
| 2026.02.02 | **Codex 桌面应用**（macOS）发布 — "Agent 指挥中心" | [OpenAI 博客](https://openai.com/index/introducing-the-codex-app/) |
| 2026.02.06 | **GPT-5.3-Codex** 发布（Pro 预览） | [morphllm.com](https://www.morphllm.com/codex-pricing) |
| 2026.03.04 | Codex 桌面应用支持 Windows | [OpenAI 博客](https://openai.com/index/introducing-the-codex-app/) |
| 2026.03.17 | GPT-5.4 mini 进入 Codex（30% 配额消耗） | [blog.laozhang.ai](https://blog.laozhang.ai/en/posts/openai-codex-march-2026) |

### 五种产品形态

| 形态 | 说明 |
|------|------|
| **Codex Cloud**（Web） | 通过 chatgpt.com/codex 访问，Agent 在 OpenAI 云端隔离沙箱中运行代码，可关联 GitHub 仓库并自动创建 PR |
| **Codex CLI** | 开源终端工具（Apache 2.0），支持本地执行，适合命令行工作流 |
| **Codex IDE 扩展** | VS Code 插件，在编辑器内调用 Agent |
| **Codex 桌面应用** | macOS / Windows 原生应用，核心定位是 **"Agent 指挥中心"**（Command Center for Agents） |
| **API** | 按 Token 计费的原始模型访问，无 Cloud/桌面特性 |

> 来源：[IntuitionLabs — Codex App Guide](https://intuitionlabs.ai/articles/openai-codex-app-ai-coding-agents)

### 核心模型

| 模型 | 发布时间 | 说明 |
|------|---------|------|
| **codex-1** | 2025.05 | o3 模型针对软件工程优化的版本，SWE-Bench Verified 72.1% |
| **GPT-5.2-Codex** | 2025.12 | 上下文压缩、长任务、Windows 支持、网络安全增强 |
| **GPT-5.3-Codex** | 2026.02 | 最强编程模型，Pro 用户预览 |
| **GPT-5.4 mini** | 2026.03 | 轻量级，仅消耗 30% 配额 |

> 来源：[gradually.ai/en/codex-statistics](https://www.gradually.ai/en/codex-statistics/)；[morphllm.com/codex-pricing](https://www.morphllm.com/codex-pricing)

### 核心技术架构

桌面应用的关键创新：

1. **Multi-Agent 编排**：同时运行多个 Agent 线程，每个线程承载一个或多个 Agent 实例，状态可视化（运行中 / 暂停 / 完成）
2. **Git Worktree 隔离**：每个 Agent 在独立的 Git Worktree 上工作，多个 Agent 可并发修改同一仓库而不冲突
3. **Skills 框架**：可复用的指令 + 脚本 + API 配置包（Figma 设计导入、云部署、图像生成、文档处理等）
4. **Automations**：定时任务系统（类似 cron + prompt），可设每日 bug 分类、CI 故障摘要等
5. **安全沙箱**：使用原生 OS 沙箱（macOS hardened runtime），默认限制文件系统和网络访问，需用户显式授权

> 来源：[OpenAI 博客](https://openai.com/index/introducing-the-codex-app/)；[InfoQ — Codex App Server Architecture](https://www.infoq.com/news/2026/02/opanai-codex-app-server/)

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 用量窗口 | 5 小时滚动窗口（非月度） | 复杂重构可在 2-4 个任务内耗尽 Plus 配额 |
| 免费层 | 促销期有限 | Free/Go 用户仅获基础 Codex 访问 |
| 模型选择 | 绑定 ChatGPT 订阅等级 | Pro 用户才能使用 GPT-5.3-Codex |
| 桌面应用 | 仅 macOS + Windows | 无 Linux 桌面版 |

## 适用边界分析

### ✅ 适用场景

| 场景 | 说明 | 典型客户/案例 |
|------|------|--------------|
| 多 Agent 并行开发 | 同时让多个 Agent 处理不同模块/分支 | Cisco、Duolingo、Gap |
| GitHub 自动化 | 关联仓库 → Agent 自主修 bug → 创建 PR | 开源项目维护 |
| 大型重构 | 云端沙箱 + GPT-5.2-Codex 上下文压缩 | 企业代码库迁移 |
| 定时自动化 | Automations 设置每日 CI 故障摘要、bug 分类 | DevOps 团队 |
| 非编码者构建原型 | Web 界面 + 自然语言描述 → Agent 生成代码 | 产品经理快速验证 |

### ❌ 不适用场景

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 仅需代码补全 | Codex 是 Agent 平台，补全场景过重 | GitHub Copilot / Qoder |
| 需要 IDE 内嵌深度体验 | Codex IDE 扩展功能有限 | Cursor / Qoder |
| 非 GitHub 代码托管 | Codex Cloud 目前主要集成 GitHub | Claude Code（终端，不限平台） |
| 预算敏感 + 大量使用 | 5h 滚动窗口 + Pro $200/月 | Claude Code Max $100-200/月 |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| Codex 是 2021 年代码补全模型的延续 | 2025 年完全重建为 Agent 平台，与旧 Codex 模型仅有品牌关系 |
| Plus $20/月就够用 | 复杂任务可在数小时内耗尽配额，重度用户需 Pro $200/月 |
| Codex 桌面应用 = IDE | 桌面应用是"Agent 指挥中心"，不是代码编辑器 |

## 定价

### 订阅定价（捆绑 ChatGPT）

| 计划 | 价格 | Codex 访问 | 用量（5h 滚动窗口） |
|------|------|-----------|----------------------|
| Free/Go | $0（促销期） | 有限 | 基础限制 |
| **Plus** | **$20/月** | 完整（Web/CLI/IDE/iOS） | 45-225 本地消息 + 10-60 云任务 |
| **Pro** | **$200/月** | 完整 + 优先处理 | 300-1,500 本地消息 + 50-400 云任务（~6×） |
| Business | $25-30/用户/月 | 完整 + 更大 VM | 同 Plus 用量 + 管理控制 |
| Enterprise | 自定义 | 优先 + Credits Pool | 无固定滚动限制 |

### API 定价（按 Token）

| 模型 | 输入（/1M tokens） | 输出（/1M tokens） |
|------|-------------------|-------------------|
| gpt-5.1-codex-mini | $0.25 | $2.00 |
| codex-mini-latest | $1.50 | $6.00 |
| gpt-5.2-codex | $1.25 | $10.00 |
| gpt-5.3-codex | ~$1.75 | ~$14.00 |

> ⚠️ 5 小时滚动窗口机制：用量按 5h 滚动窗口重置而非月度。当前有 2× 速率限制促销（2026.02 起，结束时间未确认）。
>
> 来源：[morphllm.com/codex-pricing](https://www.morphllm.com/codex-pricing)；[help.openai.com](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)

## 采用数据

- 超过 **500 万开发者** 使用 [来源: 用户口述，Sarah Friar 6月反馈] ⚠️ 待官方验证
- 超过 **100 万开发者** 在过去一个月内使用（2026.02 数据）
- 使用量较 2025 年 8 月增长 **20×**
- 企业客户：Cisco、Virgin Atlantic、Vanta、Duolingo、Gap
- Sam Altman 称 GPT-5.2-Codex 为 "OpenAI 有史以来采用最快的模型"

> 来源：[OpenAI 博客](https://openai.com/index/introducing-the-codex-app/)；[TechRadar](https://www.techradar.com/pro/openai-reveals-codex-app-for-mac-a-much-easier-way-to-deploy-ai-agents-on-apple-devices)

## 竞品快速对照

| 维度 | **OpenAI Codex** | **Claude Code** | **Qoder** | **Kiro** | **Copilot** | **Cursor** |
|------|-----------------|----------------|-----------|----------|------------|-----------|
| 产品形态 | 云端+桌面App+CLI+IDE | 终端 Agent | IDE+Agent | 独立 IDE | IDE 插件 | AI IDE |
| 核心定位 | 多 Agent 编排平台 | 深度推理 Agent | 企业级 Agentic | Spec 驱动 | 代码补全+Agent | AI-Native IDE |
| 个人定价 | $20-200/月 | $20-200/月 | 企业定价 | 免费/Pro $20/月 | $10/月 | $20/月 |
| 团队定价 | $25-30/用户/月 | $125/seat | 企业定价 | Pro+ $40/月 | $19/用户/月 | $40/用户/月 |
| 差异化 | 多Agent并行+Skills生态 | 长上下文+真实代码库理解 | 企业安全合规 | Spec-Driven | GitHub生态 | 流畅IDE体验 |

> 来源：综合各产品官方定价页；[morphllm.com](https://www.morphllm.com/codex-pricing)；[shareuhack.com](https://www.shareuhack.com/en/posts/ai-coding-tool-pricing-collapse-april-2026)

## 产品战略分析

### 为什么从"模型"变成"平台"？

1. **模型同质化压力**：纯模型层面 OpenAI 在编程指标上领先，但 Anthropic 更早认识到"真实世界代码库"需要的是 Agent 能力而非单纯补全精度
2. **从"回答问题"到"完成任务"**：开发者需要能自主完成多步骤软件工程任务的 Agent，需要将模型 + 沙箱 + 工具链 + 版本控制打包
3. **"指挥中心"定位的差异化**：Codex 桌面应用明确定位为"第三类"AI 编程工具——既不是 IDE 内嵌助手（Copilot/Cursor），也不是终端 Agent（Claude Code），而是**多 Agent 编排平台**

> Greg Brockman（OpenAI 联合创始人）："在编程方面，我们在'真实世界代码'上起步比 Anthropic 慢了。但这也反过来提升了我们的执行力。"
>
> 来源：[OpenAI 创始人访谈（2026-04-24）](https://mp.weixin.qq.com/s/SDUqxjvUXN451bjpSH29pQ)（⚠️ 微信公众号来源，待交叉验证原始英文访谈）

### 为什么捆绑 ChatGPT 订阅？

- **降低获客成本**：ChatGPT 周活跃用户约 9 亿，捆绑直接触达庞大用户基
- **交叉销售**：Plus 用户"附赠"Codex 提升 ChatGPT Plus 价值感知
- **免费层促销**：暂时向 Free/Go 用户开放，"压缩采用时间"——先让用户形成工作流依赖再推升级
- **争夺开发者份额**：Anthropic 开发者份额 54%（Menlo Ventures），OpenAI 仅 21%，Codex 捆绑策略是反攻关键

### 为什么 5 小时滚动窗口？

- Agent 任务 Token 量极大（赛车 demo 消耗 700 万 tokens），月度限额会导致月末"挤兑"
- 滚动窗口天然分散使用高峰
- Plus 用户在复杂任务中快速耗尽配额 → 推动升级到 Pro（$200/月）

## 参考资料

### 官方
- [OpenAI — Introducing Codex（2025.05）](https://openai.com/index/introducing-codex/)
- [OpenAI — Introducing the Codex App（2026.02）](https://openai.com/index/introducing-the-codex-app/)
- [OpenAI Help Center — Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)
- [Codex Pricing — developers.openai.com](https://developers.openai.com/codex/pricing)

### 第三方分析
- [Morphllm — Codex Pricing 2026](https://www.morphllm.com/codex-pricing)
- [IntuitionLabs — OpenAI Codex App Guide](https://intuitionlabs.ai/articles/openai-codex-app-ai-coding-agents)
- [InfoQ — Codex App Server Architecture](https://www.infoq.com/news/2026/02/opanai-codex-app-server/)
- [Gradually.ai — Codex Statistics](https://www.gradually.ai/en/codex-statistics/)
- [Tom's Hardware — AI Coding Agents Comparison](https://www.tomshardware.com/tech-industry/artificial-intelligence/turns-out-ai-can-actually-build-competent-minesweeper-clones-four-ai-coding-agents-put-to-the-test-reveal-openais-codex-as-the-best-while-googles-gemini-cli-as-the-worst)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-06-09 | 创建：OpenAI Codex AI 编程 Agent 平台完整产品文档（来源：inbox 调研素材） |
| 2026-06-11 | 合并：用户口述增量 - Codex 用户突破 500 万（Sarah Friar 近期反馈） |
