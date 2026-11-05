# 百炼问答 Agent（Alibaba_presale_agent）

面向阿里云百炼售前 / BD / SA 及外部客户的问答服务：回答**百炼模型价格、模型能力与选型、AI Agent 产品**相关问题。

核心特征是「价格与模型记忆解耦」——价格类问题先抓官方定价页取证据，证据缺失就拒答并引导官方页，而不是让 LLM 凭记忆报价。每条回答落库为交付记录，支持 👍/👎 反馈闭环与后台分析。

## 工作流

```
提问 → BM25 检索本地知识库（alibaba-ai-hub/ + knowledge/ai-general-notes/）
     → 命中价格特征？→ 联网核实：官方定价页直抓（权威）+ 搜索引擎旁证
     → LLM 流式生成（价格数字只能引用证据块，无证据则拒答并附官方页链接）
     → 回答落库（交付记录）→ 用户 👍/👎（点踩需选原因）→ 反馈写回同一条记录
```

| 设计点 | 选择 | 理由 |
|---|---|---|
| 编排 | 纯 Python async 管线 | 单轮「检索→校验→流式作答」无 HITL，LangGraph 只增加依赖与冷启动成本 |
| Web UI | FastAPI + 原生 SSE + 零构建前端 | 需要原生 👍/👎、点踩原因、后台分析页；无 CDN 运行时依赖 |
| 交付记录 | SQLite（WAL）单表 | 踩率统计、原因过滤、CSV 导出需要可查询结构 |
| 价格来源 | 官方定价页抓取证据 + prompt 硬约束 | 价格写进 prompt 属反模式：过期不可控、不可追溯 |
| 检索 | 自实现 BM25（中文 bigram + 拉丁词） | 文档量百级，向量库只增加运维复杂度 |

## 快速开始（Docker Compose，推荐）

需要 Docker 20.10+ 与 Compose v2。

```bash
# 1. 取代码（本目录位于 ai-playbook-2026 仓库的 vibeCodingProject/ 下）
git clone --depth 1 https://github.com/EthanNiWorld/ai-playbook-2026.git
cd ai-playbook-2026/vibeCodingProject/Alibaba_presale_agent

# 2. 配置（只需填 API Key）
cp .env.example .env
# 编辑 .env，把 DASHSCOPE_API_KEY 的 <YOUR_API_KEY> 换成真实 Key
# 公网部署建议同时设置 ADMIN_TOKEN=$(openssl rand -hex 16)

# 3. 启动
docker compose up -d --build
```

启动后：

- 聊天页 `http://<服务器IP>:8000`
- 后台分析 `http://<服务器IP>:8000/admin`

**验收（必做）**：

```bash
curl -s http://127.0.0.1:8000/api/health
# {"ok":true,"kb_chunks":712,"llm_model":"qwen3.8-max"}
```

`kb_chunks` 必须大于 0。容器首次启动会 sparse clone 知识库（仅两个目录，约 2~3 秒）并建索引，健康检查的 `start-period` 已放宽到 90 秒。若为 0，说明克隆失败——查 `docker compose logs -f`，网络受限时可用 `KNOWLEDGE_REPO_URL` 指向自己的知识库仓库。

```bash
# 常用运维
docker compose logs -f              # 看日志
docker compose restart              # 改 .env 后重启
docker compose down                 # 停止（named volume 保留数据）
docker compose cp alibaba-presale-agent:/app/data/qa.db ./qa-backup.db   # 备份交付记录
```

### 国内网络环境

镜像构建需要访问 `deb.debian.org` 与 PyPI，国内机器常失败。两个应对方式：

```bash
# 方式一：在 .env 中打开镜像源，再 build
echo 'APT_MIRROR=mirrors.aliyun.com' >> .env
echo 'PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/' >> .env
docker compose up -d --build

# 方式二：改用 venv 直跑（见 deploy/deploy-ecs.sh，无需 Docker）
sudo bash deploy/deploy-ecs.sh
```

基础镜像也可覆盖：`docker build --build-arg BASE_IMAGE=<你的镜像站>/python:3.12-slim .`

## 本地开发

```bash
python3.12 -m venv .venv          # 需 3.12（3.13 亦可，勿用 3.14）
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env              # 填入 DASHSCOPE_API_KEY
python run.py                     # http://127.0.0.1:8000
```

本地开发时知识库**零拷贝直读**：从项目目录向上探测到仓库根（含 `alibaba-ai-hub/`）即直接读工作区文件，不走 GitHub 克隆；也可用 `LOCAL_KNOWLEDGE_PATH` 显式指定。

## 环境变量

| 变量 | 必须 | 默认值 | 说明 |
|---|---|---|---|
| `DASHSCOPE_API_KEY` | ✅ | — | 百炼 OpenAI 兼容协议 Key（兼容 `DASHSCOPE_API_KEY_INTL`） |
| `DASHSCOPE_BASE_URL` | 否 | 北京端点 | workspace 专属 Key 必须配专属端点，否则提问 403 |
| `QA_MODEL` | 否 | `qwen3.8-max` | 底层问答模型 |
| `ADMIN_TOKEN` | 否 | 空 | 设置后 `/api/admin/*` 需带 `X-Admin-Token` 请求头 |
| `TAVILY_API_KEY` | 否 | 空 | 高质量搜索；不配自动降级 DuckDuckGo |
| `KNOWLEDGE_REPO_URL` | 否 | `EthanNiWorld/ai-playbook-2026` | 知识库仓库（须含 `alibaba-ai-hub/`） |
| `KB_SYNC_INTERVAL_HOURS` | 否 | `24` | 克隆模式下自动 `git pull` 间隔 |
| `PRICE_PAGE_TTL_HOURS` | 否 | `6` | 官方定价页缓存有效期 |
| `LOCAL_KNOWLEDGE_PATH` | 否 | 自动探测 | 直读本地知识库根目录（容器内不要设置） |

定价口径：阿里云国际站（新加坡节点）USD 列表价，信源为 `alibabacloud.com/help/en/model-studio/model-pricing`。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | SSE 流式问答（`{question, session_id, history}`） |
| POST | `/api/feedback` | 反馈 `{answer_id, rating: up/down, reason}` |
| GET | `/api/health` | 健康检查（含索引片段数） |
| GET | `/api/admin/stats` | 总数 / 点赞 / 点踩 / 踩率 / 官方核实数 / 耗时 |
| GET | `/api/admin/answers` | 记录列表（`rating` / `q` 过滤） |
| GET | `/api/admin/export.csv` | 全量交付记录导出 |
| POST | `/api/admin/kb/sync` | 知识库同步 + 重建索引 |

## 项目结构

```
Alibaba_presale_agent/
├── app/
│   ├── server.py          # FastAPI 入口（SSE / 反馈 / admin API）
│   ├── pipeline.py         # 问答管线：检索 → 价格校验 → 流式生成 → 落库
│   ├── knowledge.py        # GitHub sparse clone/pull + BM25 检索
│   ├── price_verifier.py   # 官方定价页抓取（TTL 缓存）+ 搜索旁证
│   ├── searcher.py         # Tavily / DuckDuckGo 联网搜索
│   ├── prompts.py          # System Prompt（价格硬约束）
│   ├── store.py            # SQLite 交付记录 + 反馈
│   ├── llm.py              # DashScope OpenAI 兼容流式客户端
│   └── config.py           # 配置（路径全部动态推导，无硬编码绝对路径）
├── static/                 # 聊天页 + 后台分析页（零构建，vendored marked.min.js）
├── tests/                  # 离线单测 + 联调脚本（详见 tests/README.md）
├── deploy/
│   ├── deploy-ecs.sh       # ECS 一键部署（systemd + venv，Docker 不可用时的备选）
│   └── nginx.conf.example  # 反代示例（SSE 不缓冲）
├── docs/
│   ├── design.md           # 设计规格与决策依据
│   └── DEPLOY-ECS.md       # ECS 部署手册（含排障）
├── Dockerfile / docker-compose.yml
└── run.py                  # 本地入口
```

## 部署形态

| 方式 | 适用 | 入口 |
|---|---|---|
| **Docker Compose** | 首选；任意有 Docker 的机器 | 本文「快速开始」 |
| ECS 一键脚本 | 国内网络无法 build 镜像时（systemd + venv + nginx 限流） | `deploy/deploy-ecs.sh` + [docs/DEPLOY-ECS.md](docs/DEPLOY-ECS.md) |
| 手动逐步 | 需要理解每一步或定制 | [docs/DEPLOY-ECS.md](docs/DEPLOY-ECS.md) §1 起 |

## 测试

```bash
.venv/bin/python tests/test_self.py      # 离线单测，无需网络与服务
```

联调脚本（需服务已在 8000 端口运行、会真实消耗 LLM 额度）见 [tests/README.md](tests/README.md)。

## 已知限制与安全提示

- **`/api/chat` 无鉴权、无限流**。公网暴露后任何人可调用，直接消耗你的百炼额度。生产部署必须：① 用 nginx `limit_req` 限流（[deploy/deploy-ecs.sh](deploy/deploy-ecs.sh) 已内置 100r/m）；② 安全组不要直接开放 8000；③ 设置 `ADMIN_TOKEN`。
- `/admin` 页面 HTML 本身不鉴权，仅数据接口受 `X-Admin-Token` 保护，页面骨架公网可见。
- 知识库默认从 GitHub 拉取，**依赖外网**。知识库更新有 24h 延迟（或用后台「同步知识库」立即更新）。
- SQLite 单机存储，**不支持多副本水平扩展**；横向扩容前需换成 PostgreSQL。
- 价格类回答仅覆盖官方定价页能抓到的模型；页面上没有的模型会拒答并给出官方链接，这是预期行为。

## License

[MIT](LICENSE)
