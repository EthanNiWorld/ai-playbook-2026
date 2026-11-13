# 百炼问答 Agent — 设计规格

## Context

BD/SA 在客户现场需要快速回答百炼模型价格、模型选型、AI Agent 产品问题。本服务提供 Web 问答入口：知识来源为 GitHub 仓库 ai-playbook-2026 的 `alibaba-ai-hub/` 与 `knowledge/ai-general-notes/`；价格类问题必须联网核实；回答质量通过 👍/👎 反馈闭环，全部交付记录落库供后台分析迭代。交付记录同时驱动「代码硬指标 + 跨厂商 LLM 评审 + 历史语料自迭代」的评测闭环（`tests/e2e/`），用于回归与诊断当前架构（见下文「评测与自迭代闭环」）。

## 核心设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 编排框架 | 纯 Python async 管线（非 LangGraph） | 单轮固定流水线无 HITL interrupt 需求；省依赖、冷启动快、流式简单。参考项目用 LangGraph 是因其多轮面试式交互 |
| 价格准确性 | LLM 与价格数字解耦：官方定价页直抓 → 证据块注入 prompt → 硬约束「无证据不报价」 | 价格写进 prompt / 让 LLM 记忆报价属反模式（价格过期不可控、不可追溯）；售前报价错误有合规风险 |
| 定价口径 | 阿里云国际站（新加坡节点）USD 列表价，官方页 `alibabacloud.com/help/en/model-studio/model-pricing` | 项目既定口径；该页为静态渲染可直接抓取 |
| 价格页缓存 | TTL 6h 本地缓存，抓取失败降级用过期缓存 | 避免每次问答都打官方页；短 TTL 平衡时效与延迟 |
| 检索方案 | 自实现 BM25（中文 bigram + 拉丁词） | 文档量百级、markdown 结构清晰，向量库增加运维复杂度无收益 |
| 知识获取 | 本地探测优先（dev 零拷贝）→ GitHub sparse clone（生产） | 与仓库同机开发时直接读工作区；服务器仅需两个目录，sparse clone 秒级 |
| 反馈闭环 | 👍/👎 + 点踩预设原因（价格不对/内容过时/答非所问/来源不可信）+ 自由补充 | 预设原因可结构化统计聚类；自由补充兜底 |
| 交付记录 | SQLite WAL，单表 answers，feedback 更新回写同一条 | 后台踩率统计/原因过滤/CSV 导出需要可查询结构 |
| 流式协议 | SSE（POST + fetch 流读取） | 兼容 nginx 反代（`proxy_buffering off` + `X-Accel-Buffering: no`）；WebSocket 无双向需求 |
| 前端 | 无构建原生 HTML/JS + vendored marked.min.js | 服务器可能无外网 CDN 访问；无 node 构建链，部署即静态文件 |
| Markdown 渲染安全 | marked 输出后正则清除 script/on事件属性/javascript: 链接 | LLM 输出不可信输入，防 XSS；引入 DOMPurify 对本项目过重 |
| 后台鉴权 | 可选 `ADMIN_TOKEN`（`X-Admin-Token` 头） | 公网域名暴露，stats/记录/同步接口必须可保护；不配置则仅限内网使用 |
| 会话 | localStorage 生成 session_id + 最近 8 条历史注入 | 多轮上下文提升追问质量；不持久化对话状态，无状态服务便于水平扩展 |
| 评测闭环 | 代码硬指标 + 跨厂商 GLM-5.3 评审 + 历史语料自迭代（build/run/refresh/diagnose） | 价格正确性由代码证据链硬门保证、表达由跨厂商 judge 评（避自评偏好）；评测集从真实交付增量自迭代；diagnose 重放定界，避免重复修已修好的问题 |

## 问答管线（pipeline.py）

```
stream_answer(question, history, session_id)
  ├─ 1. BM25 检索 top-6 片段（GitHub 引用公开可核对，随 sources 一并展示给客户自查）
  ├─ 2. is_price_question(question) 命中？
  │     └─ verify_prices:
  │         ├─ 提取模型名（regex 归一 'qwen3.8 max' → 'qwen3.8-max'）
  │         ├─ 官方定价页（TTL 缓存）定位模型名上下文窗口 → official 证据块
  │         └─ 每模型 1 条搜索并发 → web 旁证块（不得作报价依据）
  ├─ 3. 组装 prompt：system（价格硬约束）+ 历史尾 8 条 + 知识片段 + 证据块 + 问题
  ├─ 4. LLM 流式生成 → SSE delta 事件
  ├─ 5. 价格题：输出侧审计（回答表格内 $ 金额须 ⊆ 官方证据，否则 price_audit=mismatch）
  └─ 6. 落库 answers 表 → done 事件携带 answer_id / price_status / price_audit
```

SSE 事件类型：`status`（检索中/核实中/生成中）→ `sources`（含 official/web/knowledge，按可信度排序）→ `delta`\* → `done{answer_id, price_status, price_audit, latency_ms}` / `error`。

## 前端交互：停止与排队

- **停止**：流式期间发送按钮换成「停止」，点击即 `AbortController.abort()` 断开 SSE；uvicorn 感知断连后取消任务，上游 LLM 流随之关闭（真省 token）。落库侧用 `except (asyncio.CancelledError, GeneratorExit)` 将已生成正文/思考写入并标记 `interrupted=1`，不会出现「点了停止后台却什么都没留」；该条不返回 `answer_id`，所以前端不给反馈按钮，也不计入对话上下文。
- **排队**：生成中仍可输入，回车/点发送 = 入队（最多 3 条，超出提示），队首问题在当前流结束后由 `drainQueue()` 串行发出；输入提示文案随 busy 切换，排队条可一键清空。串行而非并行，避免多流并发打满 TPM 限流。

## 价格硬约束（prompts.py 摘要）

- 价格数字只能逐字引用「官方定价页证据」，注明币种/计价单位 + 来源链接
- 证据缺失 → 固定话术「暂未能联网核实，请以官方定价页为准：<链接>」
- 口径：国际站新加坡 USD；仅内地上架模型须显式标注
- 折扣/免费额度证据未提及时不臆测
- **输出侧审计（代码兜底，非仅 prompt 约定）**：`audit_answer_prices` 抽取回答表格内每个 `$` 金额，与官方证据（`official_md`，不含 web 旁证）比对；出现证据外价格则 `price_audit=mismatch:<金额>`，落库并在前端撤掉「已核实」绿标改警示、后台计入「价格审计不符」。只审计表格行、只比对 USD，避开正文成本测算与人民币换算等合法计算值。

## 数据表 answers

```
id, session_id, question, answer, thinking, sources_json,
price_status(''|official|web|none|error), price_audit(''|ok|mismatch:<金额|金额>), llm_model, latency_ms,
client_ip, user_agent, interrupted, created_at,
feedback('up'|'down'|NULL), feedback_reason, feedback_at
```

`thinking` 落库模型思考过程（reasoning_content），后台可回看模型当时的推理依据；
`client_ip` 为提问者真实 IP（优先取 nginx 写入的 X-Real-IP，其次 X-Forwarded-For 首跳，
最后才是直连对端地址），`user_agent` 用于辅助区分提问人/终端。`interrupted=1` 表示用户主动停止，
此时 `answer` 为已生成部分，用于统计「哪些问题客户等不下去」。老库在启动时由
`init_db()` 的 `_MIGRATIONS` 自动 `ALTER TABLE` 补列（含 `price_audit`），无需手工迁移。

`price_status` 让后台可直接分析「价格类回答的核实成功率」；`price_audit` 记录输出侧审计结果
（回答表格价格是否都来自官方证据），后台「价格审计不符」卡片直接暴露疑似抄错/臆造的坏 case；
点踩原因聚类定位知识库缺口。

## 评测与自迭代闭环（tests/e2e/）

回答质量不靠人工抽查，而是一条「代码硬指标 + 跨厂商 LLM 评审 + 历史语料自迭代」的闭环。两个脚本分工：`judge_quality.py` 提供分层评审判据与快速自检；`eval_harness.py` 复用其判据（`JUDGE_MODEL/RUBRIC/ask/hard_checks/verdict_of`），在其上构建可回归、可自迭代的评测集。

### 分层判据（judge_quality.py）

沿用项目「按出错成本分层」：

- **代码层**（`hard_checks`，确定性、不依赖模型）：价格六列表格存在/列序、内部路径泄漏（`knowledge/`、`alibaba-ai-hub/`、`*.md`）、价格数字集合、表格外正文长度。
- **GLM-5.3 表达层**（`RUBRIC` 四维 1-5 分）：structure / caliber / brevity / usability；eval 里另加 coverage（要点覆盖）。**绝不让 judge 用自身记忆判价格对错**——价格只来自定价页证据，judge 只评表达与交付。
- **跨厂商**：qwen3.8-max 生成、glm-5.3 评审，规避自评偏好。
- **判定优先级**（`verdict_of`）：代码硬失败（路径泄漏）> judge fail > 解析失败 warn > judge warn > 弱分 warn > pass。
- **实测约束**：glm-5.3 在 workspace 端点强制思考（不能传 `enable_thinking=False`），`max_tokens` 给足（judge_quality 8000 / eval 24000）防思考挤空正文；系统元数据用 `<system_meta>` 标签隔离并声明「只评审 `<answer>` 内文本」，否则被当回答泄漏扣分。
- **快速自检**：6 个固定 case（价格主/详情/幻觉诱导、对比、方案、规格），`judge_quality.py [n]`，落 `data/reports/quality-*`。

### 评测集四命令（eval_harness.py）

`build / run / refresh / diagnose`。语料来自 qa.db（本地 + ECS 远端拷贝，`--db` 多路径合并去重）。

- **build**：跨库去重（`_norm_q` 去空格+尾标点）+ 优先级（踩/审计不符 > 官方核实 > 其他，新记录优先）选 case → GLM 提炼锚点（type / must_contain / must_avoid / focus，**不依赖具体价格数字**，避免官方调价造成假回归）→ `golden_set.json`（`meta.sources` 存每库游标 `last_max_id`）。
- **run**：逐 case 回放当前架构 → 准确性硬门（仅 `type==price`：`price_status==official` 且 audit 非 mismatch；路径泄漏）+ GLM 评审（含 coverage）+ 耗时 avg/p95/max → 与基线对比（`--save-baseline` 固定 / `--baseline` 指定 / 默认上次报告）：准确性 pp delta + 耗时 delta + 逐 case 迁移 + 迭代结论（**硬门退化一票否决**；judge 退化提示复跑；准确性↑或持平且 p95↓=改进；耗时↑单独告警）。
- **refresh（自迭代）**：读每库游标之后的新记录（排除 `judge-/replay-/diagnose-` 会话防自污染）→ 去重已覆盖题 → 提炼锚点追加 golden set → 推进游标。新题型随真实交付持续进入评测集，**评测集不是一次性快照**。
- **diagnose（避免重复修已修好的问题）**：`_mine_problems` 跨记录聚合同题信号（踩/审计不符/中断/慢>120s；踩因留最新非空、慢取最大）→ `_replay` 用 `diagnose-*` 会话重放当前架构 → `_classify` 确定性自动判（审计是否复现、耗时 60/120s 阈值、反问看 clarify、爱情看有无工作引导尾巴），语义点踩标 🟡需人工并附重放答案 → 报告 ✅已解决 / 🟡改善需人工 / ❌仍存在。**只有重放仍复现的才是真优化目标**。

### 远端语料合并（免 SSH）

ECS 容器内 `/app/data/qa.db` → `sqlite3 VACUUM INTO` 一致性快照 → gzip → OSS 私有桶（云助手 RunCommand 触发，凭证走 `config.get_oss_config` 不回显）→ 本地 oss2 get 解压到 `data/eval/remote-qa.db`。与本地库合并去重，case id 加来源前缀防碰撞。

### 闭环如何转起来

```
真实交付(👍/👎+踩因+审计+耗时) 落 qa.db
  → refresh 把新题/坏 case 增量进评测集
  → run 回归当前架构并与基线比(准确性+耗时)
  → diagnose 挖历史坏 case 重放定界(已解决的不重复修)
  → 修知识库/prompt/工具 → 再 run 验证改进
  → --save-baseline 固定新基线
```

准确性优先、耗时并列，硬门退化一票否决。

### 关键坑（实测）

- `_read_history` 的 SELECT 必须含 `feedback_reason`，否则踩因恒空、diagnose 语义分类失效。
- 会话排除须含 `judge-/replay-/diagnose-` 三类（评测/重放/诊断自身写入的记录），否则 refresh 自迭代污染。
- 评测集与报告落 `data/eval`、`data/reports`（gitignore，含真实客户问题不入库）。
- run 单轮独立回放（不带历史），依赖上下文的省略式追问复现会失真，build 后可人工剔除。

## 环境变量

见 README 表格。全部路径动态推导（`Path(__file__)`），无硬编码绝对路径。

## 后续迭代方向

- 语义类点踩的自动定界（当前 diagnose 对语义踩标 🟡需人工、附重放答案待人工复核；确定性信号已自动判）
- 评测集覆盖多轮上下文（当前 run 单轮独立回放，省略式追问复现失真）
- 定价页结构化抽取（当前为文本窗口注入，模型多时精确度可再提升）
- ADMIN_TOKEN 升级为完整登录态（多管理员场景）
