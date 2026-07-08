# Qoder IDE 架构逆向分析

> 基于执行日志（qoder_execution_log_20260622.txt，3 个请求片段）的逆向分析
> 
> 分析日期：2026-06-22 | 日志模型：GLM-5.2 | 日志任务：GLM-5.1 Prompt Cache 测试


## 一、架构全景：Agent = Model + Harness

Qoder 的 Agent 由 Model 和 Harness 共同构成。**Harness = 模型以外的一切**——包括上下文构建、工具定义与执行、安全护栏、记忆管理，可拆解为五个子系统：Loop / Safety / Scheduler / Memory / Tools。

以下从两个互补视角描述同一架构：

### 1.1 执行流视角（一次请求怎么走过系统）

```
┌─────────────────────────────────────────────────────────────────────┐
│  Harness 层                                                         │
│                                                                     │
│  ① 拼接 system 消息（角色定义 + 工具定义 + 规则 + cache_control）    │
│  ② 注入记忆摘要（<memory_overview>）                                │
│  ③ 注入项目上下文（目录树 + 环境信息 + 用户偏好）                    │
│  ④ 上下文超限时自动压缩历史（<analysis> + <summary>，LOSSY）         │
│  ⑤ 组装完整 messages 数组，发送 API 请求                             │
├─────────────────────────────────────────────────────────────────────┤
│                         ↕  API 请求 / 响应                         │
├─────────────────────────────────────────────────────────────────────┤
│  Model 层（LLM）                                                    │
│                                                                     │
│  ⑥ 理解意图 → 规划方案 → 决策工具 → 生成响应                        │
│  ⑦ 输出 reasoning_content（思维链）+ content（最终文本 / tool_calls）│
│  ⑧ 可选：生成 suggestType 下一步建议                                │
├─────────────────────────────────────────────────────────────────────┤
│                         ↕  tool_calls ↔ role="tool"                │
├─────────────────────────────────────────────────────────────────────┤
│  Harness 层（工具执行）                                             │
│                                                                     │
│  ⑨ Safety 校验（rm -rf 拦截 / 规则检查 / 用户确认）                │
│  ⑩ Scheduler 调度（串行/并行策略 / 超时控制）                       │
│  ⑪ Tools 执行（参数校验 / 实际执行 / 结果格式化）                   │
│  ⑫ 回传 role="tool" 结果 → 回到 ⑥ 继续循环                        │
└─────────────────────────────────────────────────────────────────────┘
```

**日志证据**：3 个请求片段均呈现相同模式——system 消息含完整工具定义和 `cache_control`，消息序列包含 memory_overview 注入、项目上下文注入、历史压缩块，工具调用后以 role="tool" 回传。

### 1.2 组件职责视角（系统由谁组成）

```
Agent = Model + Harness
                       │
              ┌────────┴────────┐
              │                 │
         Model（主演）    Harness（幕后团队 · 五个子系统）
              │                 │
              │        ┌────────┴────────┐
              │        │                 │
              │   Loop（导演）     ┌──────┴──────┐
              │   · 上下文构建     │             │
              │   · 主循环控制   Safety        Scheduler
              │   · 超时/硬限制  （保镖）      （制片人）
              │   · Prompt Cache  · 危险拦截    · 并行调度
              │                  · 权限控制    · 串行强制
              │                  · 用户确认    · 超时管理
              │
              │        ┌────────┴────────┐
              │      Memory            Tools
              │     （编剧）          （剧组）
              │   · 记忆检索        · 24 个内置工具
              │   · 历史压缩        · MCP 协议扩展
              │   · 持久化存储      · 参数校验 + 执行
              │
              ▼
         tool_calls ──→ Harness 执行 ──→ role="tool" 回传
```

**职责边界**：Harness 五个子系统全权负责上下文管理、工具执行和安全护栏；Model 全权负责推理决策。二者通过工具调用协议协同，缺一不可。


## 二、核心机制

### 2.1 Agent = Model + Harness

| 维度 | Harness（Qoder IDE） | Model（LLM） |
|------|---------------------|--------------|
| 定位 | 框架层：上下文管理 + 工具执行 + 流程控制 | 推理层：理解 + 规划 + 决策 + 生成 |
| 上下文 | 主动构建（拼接系统提示 / 注入记忆 / 压缩历史） | 被动接收 |
| 工具决策 | 不干预（只提供工具定义） | 自主决定（是否调用、调哪个、填什么参数） |
| 工具执行 | 全权负责（调度 / 校验 / 超时 / 结果回传） | 不执行（只生成 tool_calls 指令） |
| 记忆 | 自动检索 + 执行写入 | 参与内容提炼（UpdateMemory 决策） |
| 循环控制 | 工具级超时（Bash 180s）；循环终止由 Model 自主决定 | 不再返回 tool_calls 时循环自然结束 |
| 安全约束 | 硬编码护栏（rm -rf / 行数限制 / 超时） | 仅受系统提示软约束 |
| 可观测性 | request_id + usage 追踪 | 不参与 |

**闭环**：Model 思考 → 生成 tool_calls → Harness 执行 → 回传 role="tool" 结果 → Model 观察 → 循环，直到 Model 返回最终文本答案。

### 2.2 记忆系统

- Harness 基于用户输入关键词自动检索，结果注入 `<memory_overview>` 标签
- 检索过程对 Model 透明，Model 仅看到注入结果
- 记忆持久化存储，支持跨会话复用
- 四类用户偏好记忆（user_info / hobby / communication / behavior）每类最多保留一条，超出时强制更新合并

### 2.3 历史压缩（上下文溢出时自动触发）

- Harness 生成 `<analysis>`（逐步骤分析）+ `<summary>`（结构化摘要，含 10 个标准字段）替代原始对话历史
- 日志明确标注摘要为 **LOSSY**（有损压缩），可能丢失代码细节、精确错误信息等
- 日志实证：一次完整会话被压缩为约 200 行 analysis + summary

### 2.4 Prompt Cache 标记

- Harness 为 **所有消息**（system / user / assistant / tool）标记 `cache_control: {"type": "ephemeral"}`
- 作用：告知 API 服务端缓存高重复内容，后续请求复用已处理 token
- 效果（日志 TTFT 实测）：

| 请求片段 | first_output_duration | 说明 |
|---------|----------------------|------|
| 片段 1 | 3583 ms | 首次请求，同时建立缓存 |
| 片段 2 | 972 ms | 命中缓存，TTFT ↓73% |
| 片段 3 | 629 ms | 命中缓存，TTFT ↓82% |

### 2.5 reasoning_content（思维链外化）

- Model 响应中除 `content`（最终输出）外，还包含 `reasoning_content` 字段
- 记录 Model 的推理过程（问题分析、方案评估、决策路径）
- 日志中共 7 段 reasoning_content，长度从数十字到数百字不等
- Harness 可选择性展示给用户，增强可解释性

### 2.6 下一步建议机制

- 最终响应中 Model 生成 `suggestType: "custom-suggest"` 建议项
- 基于会话上下文推断用户可能的下一步操作（含 suggestPrompt 和 confidence 字段）
- 属于 Model 自主行为，Harness 负责渲染展示


## 三、工具系统

### 3.1 工具清单（24 个，日志工具定义区）

| 类别 | 工具 | 数量 |
|------|------|------|
| 代码搜索 | SearchCodebase, Glob, Grep, LSP | 4 |
| 文件操作 | Read, Write, SearchReplace, DeleteFile | 4 |
| 命令执行 | Bash, GetTerminalOutput | 2 |
| 记忆管理 | SearchMemory, UpdateMemory | 2 |
| Web 能力 | WebFetch, WebSearch | 2 |
| 流程控制 | TodoWrite, SwitchMode, CreatePlan, AskUserQuestion | 4 |
| 诊断 | GetProblems, FetchRules | 2 |
| 扩展 | Agent（子代理）, Skill, RunPreview, CallMcpTool（MCP 协议） | 4 |

### 3.2 工具执行约束与护栏

| 约束 | 具体值 | 来源 | Trade-off |
|------|--------|------|----------|
| 文件编辑串行 | 禁止并行编辑同一文件 | 系统提示 | 多文件修改需逐轮进行 |
| Bash 串行 | 禁止并行执行命令 | 系统提示 | 命令间有依赖时安全，无依赖时效率低 |
| Bash 超时 | 默认 180s，最大 1800s | 工具参数定义 | 长任务需手动设 timeout 参数 |
| Bash 命令长度 | ≤ 500 字符 | 工具参数定义 | 复杂命令需写入脚本再执行 |
| SearchReplace 行数 | ≤ 600 行（original + new 合计） | 工具参数定义 | 大文件需分多次操作 |
| Write 文件大小 | ≤ 1000 行 | 工具参数定义 | 大文件需先写后追加 |
| Glob/Grep 结果上限 | ≤ 2000 条 | 工具参数定义 | 大项目需缩小搜索范围 |
| 记忆 fetch 上限 | ≤ 5 条 | 工具参数定义 | 深度回忆需多次检索 |
| 禁止 rm -rf | 硬禁止（no-rm-rf.md 规则） | 规则文件 | 无实际负面影响 |
| 禁止 git force push | 硬禁止 | 规则文件 | 特殊场景需用户手动执行 |
| 禁止跳过 hooks | 硬禁止（--no-verify 等） | 规则文件 | 保障 pre-commit 检查不被绕过 |
| 旧工具结果清理 | 标记为 `[Old tool result content cleared]` | Harness 行为 | 防止上下文溢出，但丢失历史数据 |


## 四、量化实证（日志提取）

| 指标 | 数值 | 说明 |
|------|------|------|
| 系统提示 token 估算 | ~15000 tokens（粗略估算） | 含角色定义 + 工具定义 + 规则文件，无直接计量 |
| 工具定义数 | 24 个 | 日志工具定义区完整枚举 |
| 工具调用次数 | 15 次 | 3 个片段中 role="tool" 消息数 |
| TTFT（首 Token 延迟） | 3583 → 972 → 629 ms | 首次请求建立缓存，后续命中下降 82% |
| 历史压缩产物 | ~200 行 | analysis + summary（10 个标准字段） |
| reasoning_content | 7 段 | 模型推理链外化 |
| 工具结果清理 | 8 条 | `[Old tool result content cleared]` |


## 五、日志可见能力与盲区

### 5.1 日志中可观察的能力

| 能力 | 日志证据 |
|------|---------|
| Prompt Cache 全消息标记 | 所有消息均含 `cache_control` |
| 记忆系统（检索 + 持久化 + 合并策略） | `<memory_overview>` 注入 + UpdateMemory 调用 |
| 历史有损压缩 | `<analysis>` + `<summary>` + LOSSY 标注 |
| 思维链外化 | `reasoning_content` 字段（7 段） |
| 下一步建议生成 | `suggestType: "custom-suggest"` |
| 工具并行调用（只读类） | 系统提示明文规定 |
| 规则系统（always_on + model_decision） | 4 个 always_on 规则加载 |

### 5.2 日志未覆盖的能力（盲区）

以下能力在工具定义中存在，但未在 3 个日志片段中实际调用：

- **Agent**（子代理）：CodeReview / Browser / Debug / ComputerUse / 自定义 Agent
- **CallMcpTool**：MCP 协议外部工具扩展
- **SwitchMode / CreatePlan**：Plan Mode 协作规划模式
- **RunPreview**：Web 预览浏览器集成
- **Skill**：技能调用（如 /commit、/review-pr）
- **SearchCodebase**：语义搜索（底层实现如向量检索不可见）


## 六、日志暴露的短板

### 6.1 SearchReplace 可靠性问题

日志中出现 3 次 SearchReplace 失败，但原因各异：

| 失败案例 | 实际原因 | 归因 |
|---------|---------|------|
| `run_once` 函数匹配失败 | 空白字符差异导致 original_text 无法匹配 | 精确匹配机制的固有局限 |
| `ef run_node`（缺 `d`） | 替换文本被截断，`def` 变成 `ef` | **工具实现 bug**（非匹配问题） |
| `__main__` 缩进错误 | Model 生成的 new_text 本身缩进层级不对 | **Model 输出质量问题**（非工具问题） |

三种失败分属不同层面（匹配机制 / 工具实现 / 模型输出），不应笼统归为"匹配脆弱"。

### 6.2 上下文有损压缩

摘要头部明确标注：
> ⚠️ IMPORTANT: The above summary is LOSSY.

压缩过程可能丢失：代码精确缩进、工具返回的原始数据、错误信息的完整堆栈。Model 在后续轮次中仅依赖摘要，无法回溯原始细节。

### 6.3 工具结果主动清理

日志中 8 条历史工具结果被替换为 `[Old tool result content cleared]`。Model 在后续推理中无法回溯这些工具的原始返回数据，可能影响依赖早期工具输出的长链任务。





## 七、核心术语

| 术语 | 定义 |
|------|------|
| Harness | Agent 框架层，负责上下文管理、工具执行、流程控制、安全护栏 |
| Model | 大语言模型，负责意图理解、任务规划、工具决策、代码生成 |
| Tool Calls | Model 返回的工具调用指令（含工具名 + 参数 JSON），Harness 执行后以 role="tool" 回传 |
| reasoning_content | Model 响应中的推理过程字段，记录思考路径，独立于最终输出 content |
| Prompt Cache | 通过 `cache_control: {"type": "ephemeral"}` 标记可缓存内容，复用高重复 token 以降低 TTFT 和成本 |
| 上下文压缩 | Harness 在上下文过长时自动生成 analysis + summary 替代原始历史（LOSSY） |
| MCP | Model Context Protocol，工具扩展协议，通过 CallMcpTool 调用外部服务 |


## 八、结论

Qoder IDE 的架构本质是通过 Harness 层将 LLM 从文本生成扩展为实际操作能力（文件 / 命令 / 代码编辑 / Web 检索）。Harness 通过自动记忆检索、有损历史压缩、Prompt Cache 标记、工具结果清理等机制管理上下文，在成本与性能间取得平衡。Model 的核心能力（意图理解、任务规划、工具选择、参数填充、结果分析、代码生成）不可由 Harness 替代，二者通过工具调用协议协同，缺一不可。

---
**报告结束**