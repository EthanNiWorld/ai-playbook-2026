# 百炼问答 Agent — 设计规格

## Context

BD/SA 在客户现场需要快速回答百炼模型价格、模型选型、AI Agent 产品问题。本服务提供 Web 问答入口：知识来源为 GitHub 仓库 ai-playbook-2026 的 `alibaba-ai-hub/` 与 `knowledge/ai-general-notes/`；价格类问题必须联网核实；回答质量通过 👍/👎 反馈闭环，全部交付记录落库供后台分析迭代。

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

## 问答管线（pipeline.py）

```
stream_answer(question, history, session_id)
  ├─ 1. BM25 检索 top-6 片段（GitHub 文件引用仅落库供后台分析，不展示给客户；前端只展示官方定价页/搜索来源）
  ├─ 2. is_price_question(question) 命中？
  │     └─ verify_prices:
  │         ├─ 提取模型名（regex 归一 'qwen3.8 max' → 'qwen3.8-max'）
  │         ├─ 官方定价页（TTL 缓存）定位模型名上下文窗口 → official 证据块
  │         └─ 每模型 1 条搜索并发 → web 旁证块（不得作报价依据）
  ├─ 3. 组装 prompt：system（价格硬约束）+ 历史尾 8 条 + 知识片段 + 证据块 + 问题
  ├─ 4. LLM 流式生成 → SSE delta 事件
  └─ 5. 落库 answers 表 → done 事件携带 answer_id
```

SSE 事件类型：`status`（检索中/核实中/生成中）→ `sources` → `delta`\* → `done{answer_id, price_status, latency_ms}` / `error`。

## 价格硬约束（prompts.py 摘要）

- 价格数字只能逐字引用「官方定价页证据」，注明币种/计价单位 + 来源链接
- 证据缺失 → 固定话术「暂未能联网核实，请以官方定价页为准：<链接>」
- 口径：国际站新加坡 USD；仅内地上架模型须显式标注
- 折扣/免费额度证据未提及时不臆测

## 数据表 answers

```
id, session_id, question, answer, sources_json, price_status(''|official|web|none|error),
llm_model, latency_ms, created_at,
feedback('up'|'down'|NULL), feedback_reason, feedback_at
```

`price_status` 让后台可直接分析「价格类回答的核实成功率」；点踩原因聚类定位知识库缺口。

## 环境变量

见 README 表格。全部路径动态推导（`Path(__file__)`），无硬编码绝对路径。

## 后续迭代方向

- 反馈原因自动聚类（当前靠人工在后台浏览 + CSV 导出分析）
- 点踩记录驱动知识库修复流程（坏 case → 补文档 → 验证）
- 定价页结构化抽取（当前为文本窗口注入，模型多时精确度可再提升）
- ADMIN_TOKEN 升级为完整登录态（多管理员场景）
