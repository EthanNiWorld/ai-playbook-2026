# 百炼问答 Agent · ECS 部署手册（Docker 容器化）

> 适用场景：一台阿里云 ECS（Ubuntu 22.04/24.04），用 Docker 跑应用容器 + 宿主机 nginx 做反代与限流。
> 全流程已在真实 ECS 上跑通：容器 `Up (healthy)`、知识库 715 片段、域名 200、限流生效。
>
> **为什么是 Docker 而不是 venv + systemd**：容器把 Python 版本、系统依赖、构建过程全部固化，重装/迁移/回滚都是同一条命令；
> 宿主只负责 Docker、nginx 与 `/opt/alibaba-presale-agent/.env` 三件事，不会因为 `pip install` 装出脏环境。

---

## 三条路，选一条

| 方式 | 适合 | 耗时 | 入口 |
|---|---|---|---|
| **A. 一键脚本**（`deploy/deploy-ecs.sh`） | 想少操作、不想逐条敲 | 3~5 分钟 | 本章 A |
| **B. 手动 Docker 逐步** | 想理解每一步 / 排查问题 / 定制 | 约 20 分钟 | §2 起 |
| **C. docker compose** | 已有 Docker、想要最简一条命令 | 2 分钟 | [README「快速开始」](../README.md#快速开始docker-compose推荐) |

> 国内网络说明：`docker.io` 直连常被拦，但**基础镜像 `python:3.12-slim` 一旦拉到本地就可长期复用**；
> apt 走 `mirrors.aliyun.com`；**pip 必须走清华源** —— 阿里云 PyPI 镜像缺 `pydantic==2.14.3`，会解析失败。一键脚本已按此默认值配好。

---

## A. 一键脚本部署（推荐）

脚本：`deploy/deploy-ecs.sh`。已在真实 ECS 上跑通，并在**同一台机器上幂等重跑**验证（镜像复用、数据卷保留、nginx 冲突自动清理）。

### A.1 前提：代码在哪

脚本默认从 GitHub 稀疏拉取 **`vibeCodingProject/Alibaba_presale_agent`** 一个目录。

> 注意：境内 ECS `git clone github.com` 经常在建立连接阶段就超时（与带宽无关）。大概率要改用 A.3 的 tar 模式。

### A.2 GitHub 模式

```bash
# 在 ECS 上以 root 执行
sudo DASHSCOPE_API_KEY=sk-ws-xxxxxxxx \
     DASHSCOPE_BASE_URL=https://llm-xxxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1 \
     ADMIN_TOKEN=$(openssl rand -hex 16) \
     SERVER_NAME="qa.example.com example.com www.example.com" \
     bash deploy/deploy-ecs.sh
```

或者纯交互（脚本会逐项问）：

```bash
sudo bash deploy/deploy-ecs.sh
```

### A.3 tar 模式（代码未 push / GitHub 不通时）

本机打包（**只要这一个应用目录，知识库不用带**）：

```bash
cd <本仓库>/vibeCodingProject/Alibaba_presale_agent
tar --exclude='._*' --exclude='.DS_Store' --exclude='.venv' --exclude='__pycache__' --exclude='data' \
    -czf /tmp/apa_src.tar.gz app static run.py requirements.txt Dockerfile docker-compose.yml \
    .dockerignore .env.example deploy docs LICENSE README.md

# scp 直接传
scp -i ~/.ssh/alibaba-presale-agent.pem /tmp/apa_src.tar.gz root@<ECS_PUBLIC_IP>:/tmp/

# scp 卡住时改用 ssh 管道
cat /tmp/apa_src.tar.gz | ssh -i ~/.ssh/alibaba-presale-agent.pem root@<ECS_PUBLIC_IP> "cat > /tmp/apa_src.tar.gz"
```

ECS 上执行（脚本本身也要先传上去）：

```bash
# 若代码已在服务器上，直接用仓库里的脚本
sudo SERVER_NAME="你的域名" bash deploy/deploy-ecs.sh --from-tar

# 若脚本是单独上传的
sudo SERVER_NAME="你的域名" bash /tmp/deploy-ecs.sh --from-tar
```

可选：若想连历史交付记录一起搬过去，再传一个 `/tmp/apa_data.tar.gz`（内容为 `data/qa.db`），脚本会在**数据卷为空时**自动导入。

### A.4 脚本做了哪 10 步

1. 前置检查（root / systemd / 内存 / 系统版本），并**自动停掉旧的原生 systemd 服务**（`alibaba-presale-agent`、`bqa`），避免与容器抢 8000 端口
2. 采集配置：已有 `.env` 里的同名变量作为默认值，重跑不丢配置；`ADMIN_TOKEN` 缺失时自动生成 32 位随机串
3. 装系统依赖，缺 Docker 则 `apt install docker.io` 并启动
4. 取源码（GitHub 稀疏 clone 或解 tar）
5. **幂等落盘**：旧 `.env` 备份到 `/opt/alibaba-presale-agent/backup-<时间戳>/`
6. 写 `.env`（9 个变量，权限 600）
7. `docker build`（apt 阿里云源 + pip 清华源，可用 build-arg 覆盖）
8. 准备 named volume：**卷内已有 `qa.db` 就跳过迁移**，绝不覆盖线上数据；知识库优先在容器内 `git clone` 到卷里（带 `.git`，支持每日自动检查更新），失败才退回旧本地 kb（只读快照）
9. 起容器，并生成 `/opt/alibaba-presale-agent/run-container.sh`（改完 `.env` 用它能一条命令重建容器）
10. nginx 反代 + SSE 不缓冲 + `100r/m` 限流 + 8 并发，最后健康检查并打印访问地址与后台口令

### A.5 幂等与回滚

重复执行安全，脚本会自动：

- 备份旧 `.env` → `/opt/alibaba-presale-agent/backup-<时间戳>/`
- 把定义了 `limit_req_zone` / `limit_conn_zone` / `limit_req_status` 的**旧限流文件**移到 `/root/nginx-conf-backup/`（这些是全局指令，重复会导致 `nginx -t` 失败）
- 把旧站点链接（如 `sites-enabled/bqa`）也移走（否则 `duplicate default_server`）
- **`nginx -t` 失败会自动把移走的配置放回并 reload**，不会把线上 nginx 配坏
- 数据卷 `alibaba-presale-agent-data` 永远保留，容器重建不动数据

回滚：容器镜像层面 `docker rm -f alibaba-presale-agent && docker run ...`（旧镜像 tag 仍在 `docker images` 里）；配置层面把 `backup-<时间戳>` 里的 `.env` 拷回后 `bash run-container.sh`。

### A.6 实测输出长什么样

```
▶ 安装到 /opt/alibaba-presale-agent
  ! 已备份旧 .env 到 /opt/alibaba-presale-agent/backup-20261106-011443（数据在卷 alibaba-presale-agent-data 中，不受影响）
  ✓ 源码已就位
▶ 写入运行时配置
  ✓ .env 已写入（9 个变量，权限 600）
  ✓ 镜像就绪：alibaba-presale-agent:latest 459MB
▶ 准备数据卷 alibaba-presale-agent-data
  ✓ 数据卷中已有交付记录，跳过迁移（沿用现有数据）
  ✓ 数据卷中已有 git 知识库，定时同步可直接工作
▶ 启动容器 alibaba-presale-agent
  ✓ 容器已启动（8000 → /app/data 挂载卷 alibaba-presale-agent-data）
▶ 配置 nginx 反代与限流
  ! 已移走冲突配置：/etc/nginx/conf.d/bqa-ratelimit.conf
  ! 已移走冲突配置：/etc/nginx/sites-enabled/bqa
  ✓ nginx 已生效（80 → 127.0.0.1:8000，SSE 不缓冲，100r/m 限流）
▶ 健康检查（首次启动需建索引，最多等 90 秒）
  ✓ 知识库索引 715 个片段
```

---

## 0. 部署前需要准备的 4 样东西

| # | 东西 | 说明 |
|---|---|---|
| 1 | 阿里云账号 + RAM 子账号 AK | 若纯控制台操作可不准备；要用 CLI 才需要。**不要用主账号 AK** |
| 2 | 百炼 API Key | 注意 `sk-ws-` 前缀的 workspace 专属 Key **必须与配套的 workspace 域名一起用**，见 §4.3 |
| 3 | SSH 密钥对 | 控制台创建 ECS 时可直接新建并下载 `.pem` |
| 4 | 域名（可选） | 大陆 ECS 用 80/443 挂域名需要 ICP 备案，见 §9 |

---

## 1. 控制台创建 ECS

登录 <https://ecs.console.aliyun.com> → 「创建实例」，按下面选。

### 1.1 地域与可用区

选离你近的地域（如 **华北2 · 北京**）。跨境注意：本应用要调百炼的**新加坡 workspace 端点**，北京机器跨境调用实测可用，单次问答 20~30 秒。

### 1.2 实例规格

| 场景 | 规格 | 说明 |
|---|---|---|
| **推荐（实测）** | `ecs.e-c1m2.large` 2vCPU / **4GiB** | 经济型 e，按量约 **¥0.31/小时** |
| 更省 | `ecs.e-c1m1.large` 2vCPU / 2GiB | 也能跑，但 BM25 索引 + Python 常驻，2G 偏紧；镜像构建时也可能 OOM |
| 稳定优先 | `ecs.u1-c1m2.large` 2vCPU / 4GiB | 约 ¥0.44/小时，CPU 不共享 |

**不需要 GPU。** 容器内进程 RSS 约 93MB、CPU 2.3%，4GiB 其实严重过剩。

### 1.3 镜像

**Ubuntu 22.04 / 24.04 64 位**。宿主机只需要 Docker 与 nginx，应用跑在容器里的 `python:3.12-slim`，因此**宿主 Python 版本无关紧要**。

### 1.4 系统盘

**ESSD PL0 · 40 GiB** 足够（源码 + 镜像 459MB + 知识库 md + SQLite 合计不到 1GB）。

### 1.5 网络与公网

- 专有网络：新建 VPC `192.168.0.0/16` + 交换机 `192.168.1.0/24`（或复用已有）
- 公网 IP：**勾选「分配公网 IPv4 地址」**
- 计费方式：**按使用流量**，带宽峰值 `5 Mbps` 就够（页面很小；镜像构建只要几 MB 依赖）

> ⚠️ 这样拿到的是**固定公网 IP**（随实例分配），**不是弹性 IP（EIP）**。
> 实例一旦释放，IP 永久回收，DNS A 记录随之失效。需要长期保留 IP 请单独购买 EIP 并绑定。

### 1.6 登录凭证

选「**密钥对**」→ 新建密钥对 → 浏览器会下载 `.pem`。把它放到本地：

```bash
mkdir -p ~/.ssh && mv ~/Downloads/<你的密钥>.pem ~/.ssh/alibaba-presale-agent.pem
chmod 600 ~/.ssh/alibaba-presale-agent.pem
```

### 1.7 安全组（这一步最容易配错）

创建时新建安全组，**入方向**按下表配置：

| 端口 | 授权对象 | 用途 |
|---|---|---|
| `22/22` | **你的办公出口 IP**/32 | SSH 管理，**千万不要 0.0.0.0/0** |
| `80/80` | `0.0.0.0/0` | nginx 对外（可选上 443） |
| ~~`8000/8000`~~ | **不要开** | 容器端口只供 nginx 回源，无需对外 |

> 查自己的出口 IP：`curl ifconfig.me`
> **不要**为了图省事把 8000 放给 0.0.0.0/0 —— 那等于把无鉴权的 `/api/chat` 直接晾在公网，任何人可刷你的百炼额度。

### 1.8 确认下单

计费方式选 **按量付费**（测试用），确认配置 → 创建。约 1 分钟进入 `运行中`。

---

## 2. 登录服务器装 Docker

### 2.1 SSH 登录

```bash
ssh -i ~/.ssh/alibaba-presale-agent.pem root@<ECS_PUBLIC_IP>
```

### 2.2 换 apt 源（阿里云官方镜像通常已配好）

```bash
sed -i 's|http://.*archive.ubuntu.com|https://mirrors.aliyun.com|g; s|http://security.ubuntu.com|https://mirrors.aliyun.com|g' /etc/apt/sources.list
apt-get update
```

### 2.3 安装 Docker

```bash
apt-get install -y docker.io nginx git curl openssl
systemctl enable --now docker
docker version --format 'server {{.Server.Version}}'
```

### 2.4 建目录

```bash
mkdir -p /opt/alibaba-presale-agent
```

---

## 3. 上传代码并构建镜像

### 3.1 本地打包

```bash
cd <本仓库>/vibeCodingProject/Alibaba_presale_agent
tar --exclude='._*' --exclude='.DS_Store' --exclude='.venv' --exclude='__pycache__' --exclude='data' \
    -czf /tmp/apa_src.tar.gz app static run.py requirements.txt Dockerfile docker-compose.yml \
    .dockerignore .env.example deploy docs LICENSE README.md
```

> macOS 的 `tar` 会带上 `._xxx` 的 AppleDouble 文件，必须 `--exclude='._*'`，否则日志会刷解码告警。

### 3.2 上传与解包

```bash
scp -i ~/.ssh/alibaba-presale-agent.pem /tmp/apa_src.tar.gz root@<ECS_PUBLIC_IP>:/tmp/
ssh -i ~/.ssh/alibaba-presale-agent.pem root@<ECS_PUBLIC_IP> \
  'tar xzf /tmp/apa_src.tar.gz -C /opt/alibaba-presale-agent && ls /opt/alibaba-presale-agent'
```

scp 卡住时改用管道：`cat /tmp/apa_src.tar.gz | ssh ... "cat > /tmp/apa_src.tar.gz"`。

### 3.3 构建

```bash
cd /opt/alibaba-presale-agent
docker build \
  --build-arg APT_MIRROR=mirrors.aliyun.com \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  -t alibaba-presale-agent:latest .
```

| 坑 | 现象 | 处理 |
|---|---|---|
| 拉基础镜像失败 | `dial tcp ... docker.io: connect: connection refused` | 机器上已有 `python:3.12-slim` 就直接复用；否则加 `--build-arg BASE_IMAGE=<你的镜像站>/python:3.12-slim` |
| pip 解析失败 | 找不到 `pydantic==2.14.3` | **阿里云 PyPI 镜像滞后**，改用清华源（上面命令已默认） |
| apt 拉包卡住 | 卡在 `deb.debian.org` | 必须带 `--build-arg APT_MIRROR=mirrors.aliyun.com` |

一次构建成功后，后续改代码重建走层缓存通常 10~30 秒。

---

## 4. 配置环境变量

### 4.1 变量清单

| 变量 | 必填 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | ✅ | 百炼 API Key（workspace 专属的 `sk-ws-` 类型） |
| `DASHSCOPE_BASE_URL` | ⚠️ 强相关 | **必须与该 Key 属于同一个 workspace 的专属端点**，见 §4.3 |
| `ADMIN_TOKEN` | 建议 | `/api/admin/*` 的访问口令，留空则后台无鉴权 |
| `QA_MODEL` | 否 | 默认 `qwen3.8-max`，搜索与回答共用这一个模型 |
| `TAVILY_API_KEY` | 否 | 不配则自动降级 DuckDuckGo |
| `KNOWLEDGE_REPO_URL` | 否 | 知识库仓库，默认本仓库 |
| `KB_SYNC_INTERVAL_HOURS` | 否 | 自动同步间隔，默认 `24` |
| `KB_AUTO_SYNC` | 否 | 置 `0` 关闭定时同步 |
| `PRICE_PAGE_TTL_HOURS` | 否 | 官方定价页缓存时长，默认 `6` |

### 4.2 写入 `.env`

```bash
cat > /opt/alibaba-presale-agent/.env <<'EOF'
DASHSCOPE_API_KEY=sk-ws-xxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_BASE_URL=https://llm-xxxxxxxxxxxxxxxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
ADMIN_TOKEN=请换成一个32位随机串
QA_MODEL=qwen3.8-max
TAVILY_API_KEY=
KNOWLEDGE_REPO_URL=https://github.com/EthanNiWorld/ai-playbook-2026.git
KB_SYNC_INTERVAL_HOURS=24
KB_AUTO_SYNC=1
PRICE_PAGE_TTL_HOURS=6
EOF

chmod 600 /opt/alibaba-presale-agent/.env
```

> 生成强口令：`openssl rand -hex 16`
> 不要用手机号、生日、"手机号+名字缩写"这类可猜的口令 —— 后台能看到**所有用户的提问原文**。

### 4.3 最容易踩的坑：Key 与 BASE_URL 必须配对

`.env` 里通常会有好几组 Key（不同 workspace）。**混搭会报错，而且报错信息很有迷惑性**：

| 组合 | 结果 |
|---|---|
| workspace Key + 默认北京端点 `https://dashscope.aliyuncs.com/compatible-mode/v1` | `401 Incorrect API key provided` |
| A 的 Key + B workspace 的端点 | `403 Workspace endpoint access denied` |
| **配套的 Key + 配套的 `_URL`** | ✅ 正常 |

容器内自测一句（不依赖宿主 Python）：

```bash
docker run --rm --env-file /opt/alibaba-presale-agent/.env \
  --entrypoint python alibaba-presale-agent:latest -c "
import asyncio
from app.llm import stream_chat
async def main():
    n = 0
    async for t in stream_chat([{'role':'user','content':'只回复两个字：收到'}], max_tokens=16):
        n += len(t)
    print('LLM OK, 输出字符数=', n)
asyncio.run(main())"
```

---

## 5. 启动容器

```bash
docker volume create alibaba-presale-agent-data

docker run -d --name alibaba-presale-agent --restart unless-stopped \
  -p 8000:8000 \
  --env-file /opt/alibaba-presale-agent/.env \
  -v alibaba-presale-agent-data:/app/data \
  alibaba-presale-agent:latest
```

三个关键点：

- **数据全在卷里**：`qa.db`、知识库 clone、定价页缓存都在 `alibaba-presale-agent-data`，容器删了数据也在。
- **知识库自动 clone**：首次启动会 `git clone --filter=blob:none --sparse` 到卷里（境内可能较慢，健康检查的 `start-period` 已放宽到 90 秒）。**不要**在容器里设 `LOCAL_KNOWLEDGE_PATH`，那样自动同步会失效。
- **非 root 运行**：容器内是 `appuser(10001)`，卷首次挂载会继承该属主，所以不要用宿主目录做 bind mount。

验证：

```bash
docker ps --filter name=alibaba-presale-agent --format '{{.Status}}'
docker logs alibaba-presale-agent 2>&1 | tail -5
curl -s http://127.0.0.1:8000/api/health
```

预期日志：

```
kb INFO BM25 索引重建完成: 715 个片段
server INFO 知识库索引就绪: 715 个片段
server INFO 知识库自动同步已启用：每 24.0 小时检查远端提交，有更新才拉取
Uvicorn running on http://0.0.0.0:8000
```

`/api/health` 预期：

```json
{"ok":true,"kb_chunks":715,"llm_model":"qwen3.8-max"}
```

> 若 `kb_chunks` 为 0：说明 clone 失败。看 `docker logs`，或在能连 GitHub 的机器上把知识库 clone 好再 `docker cp` 进卷里。

---

## 6. nginx 反向代理（80 端口 + SSE + 限流）

### 6.1 限流 zone

```bash
cat > /etc/nginx/conf.d/apa-ratelimit.conf <<'EOF'
limit_req_zone $binary_remote_addr zone=apa_chat:10m rate=100r/m;
limit_conn_zone $binary_remote_addr zone=apa_conn:10m;
limit_req_status 429;
EOF
```

> `limit_req_zone` / `limit_conn_zone` / `limit_req_status` 都是**全局指令**，同一份配置里只能出现一次。
> 若机器上还有旧文件（如 `bqa-ratelimit.conf`）也定义了它们，`nginx -t` 会报 `directive is duplicate` —— 把旧文件移走即可。

### 6.2 站点配置

```bash
cat > /etc/nginx/sites-available/alibaba-presale-agent <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name qa.example.com example.com www.example.com;

    client_max_body_size 8m;
    limit_req zone=apa_chat burst=10 nodelay;
    limit_conn apa_conn 8;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        chunked_transfer_encoding on;
    }
}
EOF

ln -sf /etc/nginx/sites-available/alibaba-presale-agent /etc/nginx/sites-enabled/alibaba-presale-agent
```

`listen 80 default_server` 只能有一个：机器上若还有别的站点文件（如 `sites-enabled/bqa`）也写了 `default_server`，会报 `duplicate default_server`，需要把旧的移走：

```bash
for f in /etc/nginx/sites-enabled/*; do
  case "$(basename "$f")" in alibaba-presale-agent|default) continue ;; esac
  mv "$f" "/root/nginx-conf-backup/$(basename "$f").$(date +%s)"
done
mv /etc/nginx/sites-enabled/default /root/nginx-default.bak 2>/dev/null || true   # 备份而非删除
```

**`proxy_buffering off` 是生死线**：本应用用 SSE 流式输出，nginx 一旦缓冲，前端就会等到全部生成完才一次性显示（实测关掉后首包 TTFB 从"几十秒"→ **0.027s**）。

### 6.3 校验并生效

```bash
nginx -t && systemctl reload nginx && systemctl enable nginx
```

压测验证（用 GET 打 `/api/chat` 只返回 405，不会触发模型调用、不烧额度）：

```bash
for i in $(seq 1 100); do curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/api/chat & done > /tmp/rt.txt; wait
sort /tmp/rt.txt | uniq -c
# 预期：约 11 个 405（放行） + 89 个 429（拦截）
```

---

## 7. 验收清单

逐条跑，全部符合才算部署成功：

| # | 命令 | 预期 |
|---|---|---|
| 1 | `docker ps --filter name=alibaba-presale-agent --format '{{.Status}}'` | `Up ... (healthy)` |
| 2 | `curl -s http://127.0.0.1:8000/api/health` | `{"ok":true,"kb_chunks":715,...}` |
| 3 | `curl -s http://<ECS_PUBLIC_IP>/` | 返回首页 HTML |
| 4 | `curl -s -o /dev/null -w '%{http_code}' http://<ECS_PUBLIC_IP>/admin` | `200` |
| 5 | `curl -s -H 'X-Admin-Token: <你的ADMIN_TOKEN>' http://<IP>/api/admin/stats` | `{"total":N,...}`；**不带口令应 401** |
| 6 | `curl -s -N -o /dev/null -w 'TTFB=%{time_starttransfer}s' -X POST http://<IP>/api/chat -H 'Content-Type: application/json' -d '{"question":"你好","session_id":"t1"}'` | `TTFB` 在 1 秒内（说明流式未被缓冲） |
| 7 | 浏览器打开首页，问「qwen3.8-max 的输入价格是多少？」 | 20~30 秒内流式出现价格表 + 官方来源链接 |
| 8 | `systemctl restart docker && sleep 20 && curl -s http://127.0.0.1:8000/api/health` | 仍 200（验证 `restart unless-stopped` + healthcheck） |

---

## 8. 域名接入（可选）

### 8.1 解析

在云解析 DNS 里加：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---|---|---|---|
| A | `@` | `<ECS_PUBLIC_IP>` | 600 |
| A | `www` | `<ECS_PUBLIC_IP>` | 600 |

改完用**服务器侧**验证才准（本机 DNS 可能被公司网关劫持）：

```bash
ssh ... 'getent hosts 你的域名'
curl -s --resolve 你的域名:80:<ECS_PUBLIC_IP> http://你的域名/api/health
```

> 容器换版本、重启、重建都不影响域名：只要 nginx 还是回源 `127.0.0.1:8000`，DNS 一个字都不用改。

### 8.2 备案（大陆 ECS 的硬门槛）

- 大陆地域 ECS + 域名 + **80/443** → 必须有 ICP 备案，否则阿里云会在 80 端口返回备案提示页
- 判定方法：域名解析到该 IP 后，从**服务器上** `curl http://你的域名/` —— 返回你的页面 = 已可用；返回备案提示 = 未备案
- 未备案的临时办法：用非标端口（如 `http://域名:8000`）可访问，但**不推荐长期**，也不合规

### 8.3 HTTPS（备案后建议做）

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名 -d www.你的域名
```

certbot 会改写 `sites-available/alibaba-presale-agent` 加 443 段，`proxy_buffering off` 等 SSE 设置会自动继承。

### 8.4 办公网可能打不开

若公司网络有域名安全网关（如阿里云"云壳"），访问自有域名可能返回 403「域名不在安全策略默认允许范围内」。
这是**网络侧策略**，不是站点故障：同一站点用 IP 直连通常 200。解决方式是在网关控制台把域名加白。

---

## 9. 排障手册

| 症状 | 根因 | 处理 |
|---|---|---|
| `/api/health` 返回 200，但提问报 **401 Incorrect API key** | 只配了 Key，没配 `DASHSCOPE_BASE_URL`，回落到默认北京端点 | 补上配套的 workspace 端点，重建容器（§4.3） |
| 提问报 **403 Workspace endpoint access denied** | Key 与端点不属于同一 workspace | 换成配套的 `_KEY` + `_URL`（§4.3） |
| `docker build` 报 **`connection refused`** | 国内直连 docker.io 不通 | 复用本机已有的 `python:3.12-slim`，或 `--build-arg BASE_IMAGE=<镜像站>/python:3.12-slim` |
| `pip` 找不到 **`pydantic==2.14.3`** | 阿里云 PyPI 镜像滞后 | 改用 `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple` |
| `nginx -t` 报 **`"limit_req_status" directive is duplicate`** | 机器上还有旧限流文件（如 `bqa-ratelimit.conf`） | 把旧文件移到 `/root/nginx-conf-backup/`（一键脚本已自动处理） |
| `nginx -t` 报 **`duplicate default_server`** | 旧站点链接与本站点都声明了 `default_server` | 移走 `sites-enabled/` 下的旧站点链接 |
| `docker logs` 里知识库 clone **超时 / `kb_chunks:0`** | 境内访问 GitHub 不稳 | 稍后重启容器重试；或在能连 GitHub 的机器 clone 后 `docker cp` 进卷 |
| 容器起来了但写数据报 **`unable to open database file`** | 用宿主目录做 bind mount，属主不是 `10001` | 改用 named volume（`docker volume create`），不要 bind mount |
| 页面能开，但回答**一次性蹦出来而非流式** | nginx 缓冲了 SSE | 确认 `proxy_buffering off;` + `proxy_cache off;` |
| 后台 `/admin` 打不开数据，提示 401 | 服务端设了 `ADMIN_TOKEN`，页面没填 | 在后台页顶部输入框填入同一个口令 |
| 后台「导出 CSV / 同步知识库」按钮报错 | 同上，缺 `X-Admin-Token` | 同上 |
| 日志刷 **`'utf-8' codec can't decode`** | macOS 打包带入 `._xxx` AppleDouble 文件 | 重新打包时 `--exclude='._*'` |
| `scp` 卡住/被杀 | 网络或安全策略拦截 | 改用 `cat file \| ssh ... "cat > file"` 管道 |
| 换机器后**域名打不开** | 旧的是固定公网 IP，随实例释放已回收 | 更新 A 记录，或改用 EIP |

---

## 10. 日常运维

```bash
# 看日志（含知识库自动同步记录）
docker logs -f alibaba-presale-agent

# 改配置后重建容器（数据卷保留）
vim /opt/alibaba-presale-agent/.env && bash /opt/alibaba-presale-agent/run-container.sh

# 重启 / 停止
docker restart alibaba-presale-agent
docker stop alibaba-presale-agent

# 备份交付记录（WAL 模式下建议先停容器再拷）
docker stop alibaba-presale-agent
docker cp alibaba-presale-agent:/app/data/qa.db ./qa-$(date +%F).db
docker start alibaba-presale-agent

# 更新代码（本地重新打包上传后）
tar xzf /tmp/apa_src.tar.gz -C /opt/alibaba-presale-agent
cd /opt/alibaba-presale-agent && docker build --build-arg APT_MIRROR=mirrors.aliyun.com \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple -t alibaba-presale-agent:latest .
bash /opt/alibaba-presale-agent/run-container.sh
```

知识库更新有两条路：① 在 `/admin` 点「同步知识库」立即拉取重建；② 后台任务每 `KB_SYNC_INTERVAL_HOURS`（默认 24h）**先比对远端 HEAD，有新提交才 pull 并重建索引**，无变化不动索引。

### 费用与清理

- 按量实例 **持续计费**，2vCPU/4GiB 约 **¥0.31/小时 ≈ ¥7.4/天**
- 释放前先备份数据卷里的 `qa.db`（见上）
- 释放顺序（控制台）：实例 → 安全组 → 交换机 → VPC；**实例释放不可逆，且公网 IP 一并回收**
- 想临时止血又不想释放：控制台「停止实例」→ 选「节省停机模式」（CPU/内存不再计费，云盘仍计费）

### 上线前安全自查

- [ ] 安全组 22 端口**只**放行自己的 IP
- [ ] 8000 端口**没有**对公网开放（只由 nginx 回源）
- [ ] `ADMIN_TOKEN` 是 32 位随机串，不是手机号/生日
- [ ] `.env` 权限 `600`，属主 root
- [ ] 数据卷里 `qa.db` 属主 `10001`（named volume 默认即是）
- [ ] 有 ICP 备案（用 80/443 时）
- [ ] 已上 HTTPS（否则提问内容在链路上是明文）
- [ ] 在百炼控制台设了**费用告警/额度上限**（最终兜底）
- [ ] 演示结束就释放机器（最彻底的风险消解）
