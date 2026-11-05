# 百炼问答 Agent · ECS 部署手册（控制台手动版）

> 适用场景：你不想用 Docker、也不想让 Agent 代操作，而是**自己在阿里云控制台开一台 ECS，再 SSH 上去逐步部署**。
> 全流程实测跑通过一次：2vCPU/4GiB 北京节点，从开机器到 `https://域名` 可问答约 20 分钟。
>
> 仓库里另有 `Dockerfile` / `docker-compose.yml` / `deploy/nginx.conf.example`，属于容器化交付形态。
> **但在国内 ECS 上，`docker.io` 与容器内 `deb.debian.org` 经常直接不通**（实测 connection refused / 拉包零进展），
> 所以本手册走 **venv + systemd** 路线，这是在国内网络环境下最稳的一条路。

---

## 两条路，选一条

| 方式 | 适合 | 耗时 | 入口 |
|---|---|---|---|
| **A. 一键脚本**（`deploy/deploy-ecs.sh`） | 想少操作、不想逐条敲 | 3~5 分钟 | 本章 A |
| **B. 手动逐步** | 想理解每一步 / 排查问题 / 定制 | 约 20 分钟 | 从 §1 开始 |

---

## A. 一键脚本部署（推荐）

脚本：`deploy/deploy-ecs.sh`。已在真实 ECS 上跑通：712 个知识库片段、三域名 200、限流生效。

### A.1 前提：代码在哪

脚本默认从 GitHub 稀疏拉取 **`vibeCodingProject/Alibaba_presale_agent`** 一个目录。

> 注意：如果该目录还没 push 到 GitHub，GitHub 模式会直接报错退出 —— 改用 A.3 的 tar 模式即可。

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

### A.3 tar 模式（代码未 push 时）

本机打包（**只要这一个应用目录，知识库不用带**）：

```bash
cd <本仓库>/vibeCodingProject/Alibaba_presale_agent
tar --exclude='._*' --exclude='.DS_Store' --exclude='.venv' --exclude='__pycache__' \
    -czf /tmp/apa_src.tar.gz app static run.py requirements.txt Dockerfile deploy
scp -i ~/.ssh/alibaba-presale-agent.pem /tmp/apa_src.tar.gz root@<ECS_PUBLIC_IP>:/tmp/
```

ECS 上执行：

```bash
sudo SERVER_NAME="你的域名" bash deploy/deploy-ecs.sh --from-tar
```

可选：若想连历史交付记录一起搬过去，再传一个 `/tmp/apa_data.tar.gz`（内容为 `data/qa.db`），脚本会自动导入。

### A.4 脚本做了哪 11 步

1. 前置检查（root / systemd / 内存 / 系统版本）
2. 采集配置，`ADMIN_TOKEN` 缺失时**自动生成 32 位随机串**
3. 装 `python3-venv` / `git` / `nginx`，apt 源换阿里云
4. 取源码（GitHub 稀疏 clone 或解 tar）
5. **幂等落盘**：旧版自动备份 `.env` + `data/` 到 `/opt/alibaba-presale-agent/backup-<时间戳>/`
6. 知识库：tar 模式带包则本地直读；否则留空，由服务启动时自动 sparse clone（实测 2.6 秒 / 83MB / 74 个 md）
7. 写 `.env`（权限 600）
8. venv + pip 阿里云源装依赖
9. 注册 systemd：**只监听 `127.0.0.1:8000`**，开机自启 + 崩溃自动重启
10. nginx 反代 + SSE 不缓冲 + 每 IP `100r/m` 限流 + 每 IP 8 并发上限
11. 健康检查（首次启动需 clone 知识库，最多等 90 秒），最后打印访问地址与后台口令

### A.5 幂等与回滚

重复执行安全，脚本会自动：

- 备份旧 `.env` 与 `data/` → `/opt/alibaba-presale-agent/backup-<时间戳>/`
- 把定义了同名 `apa_chat` zone 的旧 nginx 配置移到 `/root/nginx-conf-backup/`（避免 `duplicate zone` 报错）
- 未显式传新 Key 时，**保留你现有的 `.env`**

回滚：把 `/opt/alibaba-presale-agent/backup-<时间戳>/` 里的 `.env` 与 `data/` 拷回，然后 `systemctl restart alibaba-presale-agent`。

### A.6 实测输出长什么样

```
▶ 获取应用代码（来源：tar）
  ✓ 已从 tar 包解出源码
▶ 安装到 /opt/alibaba-presale-agent
  ! 检测到旧版本，已备份 .env 与 data 到 /opt/alibaba-presale-agent/backup-20261105-234500
▶ 写入运行时配置
  ! 沿用已有 /opt/alibaba-presale-agent/.env
▶ 注册系统服务
  ✓ 服务已启动（仅监听 127.0.0.1:8000）
▶ 配置 nginx 反代与限流
  ✓ nginx 已生效（80 → 127.0.0.1:8000，SSE 不缓冲，100r/m 限流）
▶ 健康检查
  ✓ 知识库索引 712 个片段
```

---

## 0. 部署前需要准备的 4 样东西

| # | 东西 | 说明 |
|---|---|---|
| 1 | 阿里云账号 + RAM 子账号 AK | 若纯控制台操作可不准备；要用 CLI 才需要。**不要用主账号 AK** |
| 2 | 百炼 API Key | 注意 `sk-ws-` 前缀的 workspace 专属 Key **必须与配套的 workspace 域名一起用**，见 §4.4 |
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
| 更省 | `ecs.e-c1m1.large` 2vCPU / 2GiB | 也能跑，但 BM25 索引 + Python 常驻，2G 偏紧 |
| 稳定优先 | `ecs.u1-c1m2.large` 2vCPU / 4GiB | 约 ¥0.44/小时，CPU 不共享 |

**不需要 GPU。** 实测进程占用：RSS 约 **93MB**、CPU **2.3%**、系统可用内存 2.9GB —— 4GiB 其实严重过剩。

### 1.3 镜像

**Ubuntu 22.04 64 位**（自带 Python 3.10.12，本应用代码兼容 3.10）。
不要选 Python 3.9 的 Debian 11，代码里用了 `str | None` 语法。

### 1.4 系统盘

**ESSD PL0 · 40 GiB** 足够（源码 + 知识库 md + SQLite 合计不到 10MB）。

### 1.5 网络与公网

- 专有网络：新建 VPC `192.168.0.0/16` + 交换机 `192.168.1.0/24`（或复用已有）
- 公网 IP：**勾选「分配公网 IPv4 地址」**
- 计费方式：**按使用流量**，带宽峰值 `5 Mbps` 就够（页面很小，流量费可忽略）

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
| ~~`8000/8000`~~ | **不要开** | 应用只监听 `127.0.0.1:8000`，由 nginx 回源，无需对外 |

> 查自己的出口 IP：`curl ifconfig.me`
> **不要**为了图省事把 8000 放给 0.0.0.0/0 —— 那等于把无鉴权的 `/api/chat` 直接晾在公网，任何人可刷你的百炼额度。

### 1.8 确认下单

计费方式选 **按量付费**（测试用），确认配置 → 创建。约 1 分钟进入 `运行中`。

---

## 2. 登录服务器做基础准备

### 2.1 SSH 登录

```bash
ssh -i ~/.ssh/alibaba-presale-agent.pem root@<ECS_PUBLIC_IP>
```

### 2.2 换 apt 源（阿里云官方镜像通常已配好，非阿里云镜像才需要）

```bash
sudo sed -i 's|http://.*archive.ubuntu.com|https://mirrors.aliyun.com|g; s|http://security.ubuntu.com|https://mirrors.aliyun.com|g' /etc/apt/sources.list
sudo apt-get update
```

### 2.3 安装 Python 环境与工具

```bash
sudo apt-get install -y python3-venv python3-pip git curl
python3 --version   # 期望 Python 3.10.x
```

### 2.4 建目录

```bash
sudo mkdir -p /opt/alibaba-presale-agent/kb
sudo mkdir -p /opt/alibaba-presale-agent/data
```

---

## 3. 上传代码与知识库

### 3.1 在本地仓库打包（3 个包）

```bash
cd <本仓库>/vibeCodingProject/Alibaba_presale_agent

# ① 应用源码
tar --exclude='._*' --exclude='.DS_Store' --exclude='.venv' --exclude='__pycache__' \
    -czf /tmp/apa_src.tar.gz app static run.py requirements.txt Dockerfile docker-compose.yml deploy

# ② 知识库：只传 Markdown，避免把图片/视频/PDF 一起搬上去
cd <本仓库>
find alibaba-ai-hub knowledge/ai-general-notes -name '*.md' -print0 \
  | tar czf /tmp/apa_kb.tar.gz --null -T -

# ③ 历史交付记录（可选；从本地已有数据库带走历史数据）
cd <本仓库>/vibeCodingProject/Alibaba_presale_agent
tar czf /tmp/apa_data.tar.gz -C . data/qa.db
```

> macOS 的 `tar` 会带上 `._xxx` 的 AppleDouble 文件，导致服务端日志刷 `'utf-8' codec can't decode` 告警，所以必须 `--exclude='._*'`。

### 3.2 上传

两种方式，任选：

```bash
# 方式一：scp（网络正常时最省事）
scp -i ~/.ssh/alibaba-presale-agent.pem /tmp/apa_*.tar.gz root@<ECS_PUBLIC_IP>:/tmp/

# 方式二：ssh 管道（scp 被墙/被拦时用这个）
cat /tmp/apa_src.tar.gz | ssh -i ~/.ssh/alibaba-presale-agent.pem root@<IP> "cat > /tmp/apa_src.tar.gz"
cat /tmp/apa_kb.tar.gz  | ssh -i ~/.ssh/alibaba-presale-agent.pem root@<IP> "cat > /tmp/apa_kb.tar.gz"
cat /tmp/apa_data.tar.gz| ssh -i ~/.ssh/alibaba-presale-agent.pem root@<IP> "cat > /tmp/apa_data.tar.gz"
```

### 3.3 服务器解压

```bash
cd /opt/alibaba-presale-agent && tar xzf /tmp/apa_src.tar.gz
cd /opt/alibaba-presale-agent/kb && tar xzf /tmp/apa_kb.tar.gz
cd /opt/alibaba-presale-agent && tar xzf /tmp/apa_data.tar.gz   # 可选

# 校验
ls /opt/alibaba-presale-agent                      # 应看到 app static run.py requirements.txt Dockerfile deploy
ls /opt/alibaba-presale-agent/kb                   # 应看到 alibaba-ai-hub knowledge
find /opt/alibaba-presale-agent/kb -name '*.md' | wc -l   # 实测约 148
```

### 3.4 修正文件属主（重要）

从 macOS 打包上传后，服务器上文件属主可能变成 `502 staff`，数据库权限会变成 644（同机其他用户可读）：

```bash
chown -R root:root /opt/alibaba-presale-agent
chmod 700 /opt/alibaba-presale-agent/data
chmod 600 /opt/alibaba-presale-agent/data/qa.db
```

---

## 4. 配置环境变量

### 4.1 只需要 4 个变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | ✅ | 百炼 API Key（workspace 专属的 `sk-ws-` 类型） |
| `DASHSCOPE_BASE_URL` | ⚠️ 强相关 | **必须与该 Key 属于同一个 workspace 的专属端点**，见 §4.4 |
| `ADMIN_TOKEN` | 建议 | `/api/admin/*` 的访问口令，留空则后台无鉴权 |
| `QA_MODEL` | 否 | 默认 `qwen3.8-max`，搜索与回答共用这一个模型 |

### 4.2 写入 `.env`

```bash
cat > /opt/alibaba-presale-agent/.env <<'EOF'
DASHSCOPE_API_KEY=sk-ws-xxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_BASE_URL=https://llm-xxxxxxxxxxxxxxxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
ADMIN_TOKEN=请换成一个32位随机串
QA_MODEL=qwen3.8-max
EOF

chmod 600 /opt/alibaba-presale-agent/.env
```

> 生成强口令：`openssl rand -hex 16`
> 不要用手机号、生日、"手机号+名字缩写"这类可猜的口令 —— 后台能看到**所有用户的提问原文**。

### 4.3 服务是怎么读到它的

`app/config.py` 里 `load_dotenv(PROJECT_ROOT / ".env")`，而 `PROJECT_ROOT` 是 `app/` 的上一级目录，也就是 `/opt/alibaba-presale-agent`。
所以**改完 `/opt/alibaba-presale-agent/.env` 只需 `systemctl restart alibaba-presale-agent` 即生效**，不需要动代码、不需要动 systemd。

### 4.4 最容易踩的坑：Key 与 BASE_URL 必须配对

`.env` 里通常会有好几组 Key（不同 workspace）。**混搭会报错，而且报错信息很有迷惑性**：

| 组合 | 结果 |
|---|---|
| workspace Key + 默认北京端点 `https://dashscope.aliyuncs.com/compatible-mode/v1` | `401 Incorrect API key provided` |
| A 的 Key + B workspace 的端点 | `403 Workspace endpoint access denied` |
| **配套的 Key + 配套的 `_URL`** | ✅ 正常 |

自测一句：

```bash
cd /opt/alibaba-presale-agent && .venv/bin/python -c "
import asyncio,sys; sys.path.insert(0,'.')
from app.llm import stream_chat
async def main():
    n=0
    async for t in stream_chat([{'role':'user','content':'只回复两个字：收到'}], max_tokens=16): n+=len(t)
    print('LLM OK, 输出字符数=',n)
asyncio.run(main())"
```

---

## 5. 安装 Python 依赖

```bash
cd /opt/alibaba-presale-agent
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/
.venv/bin/pip install --no-input -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
```

验证：

```bash
.venv/bin/python -c "import fastapi,uvicorn,openai,httpx,dotenv;print('deps OK')"
```

---

## 6. 注册 systemd 服务

### 6.1 写 unit

```bash
cat > /etc/systemd/system/alibaba-presale-agent.service <<'EOF'
[Unit]
Description=Bailian QA Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/alibaba-presale-agent
Environment=LOCAL_KNOWLEDGE_PATH=/opt/alibaba-presale-agent/kb
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/alibaba-presale-agent/.venv/bin/python run.py --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

**两个关键点：**

- `--host 127.0.0.1`：只监听本机，外部只能经 nginx 进来。这样安全组**不需要**开放 8000。
- `LOCAL_KNOWLEDGE_PATH=/opt/alibaba-presale-agent/kb`：直接用上传的本地知识库，不走 `git clone`。
  （国内机器 `git clone github.com` 经常超时；容器化时 `docker-compose.yml` 注释里也建议服务器上不要设这个变量走 clone，我们是**反过来**——因为本机没有稳定的 GitHub 通路。）

### 6.2 启动与验证

```bash
systemctl daemon-reload
systemctl enable --now alibaba-presale-agent
sleep 5
systemctl is-active alibaba-presale-agent
journalctl -u alibaba-presale-agent -n 20 --no-pager | tail -10
curl -s http://127.0.0.1:8000/api/health
```

预期日志出现：

```
kb INFO BM25 索引重建完成: 712 个片段
server INFO 知识库索引就绪: 712 个片段
Uvicorn running on http://127.0.0.1:8000
```

`/api/health` 预期：

```json
{"ok":true,"kb_chunks":712,"llm_model":"qwen3.8-max"}
```

> 若 `kb_chunks` 明显偏小（比如 0 或几十），说明知识库路径没生效，检查 `LOCAL_KNOWLEDGE_PATH` 下是否有 `alibaba-ai-hub/` 和 `knowledge/ai-general-notes/` 两个目录。

---

## 7. nginx 反向代理（80 端口 + SSE + 限流）

### 7.1 安装

```bash
apt-get install -y nginx
```

### 7.2 站点配置

```bash
cat > /etc/nginx/sites-available/alibaba-presale-agent <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name qa.example.com example.com www.example.com;

    client_max_body_size 8m;
    limit_req zone=apa_chat burst=10 nodelay;

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
mv /etc/nginx/sites-enabled/default /root/nginx-default.bak   # 备份而非删除
```

**`proxy_buffering off` 是生死线**：本应用用 SSE 流式输出，nginx 一旦缓冲，前端就会等到全部生成完才一次性显示，体验完全崩掉（实测关掉后首包 TTFB 从"几十秒"→ **0.027s**）。

### 7.3 限流（防脚本刷模型额度）

```bash
cat > /etc/nginx/conf.d/ratelimit.conf <<'EOF'
limit_req_zone $binary_remote_addr zone=apa_chat:10m rate=100r/m;
limit_req_status 429;
EOF
```

含义：**每 IP 每分钟 100 个请求**，允许 10 个瞬时突发，超出直接返回 `429`。
一次完整问答（含 20~30 秒流式输出）只算 **1 个请求**；一次页面加载约 6 个请求 —— 正常使用完全够用。

> 想更严可加并发连接限制（脚本再多也只能排队）：
> ```nginx
> # conf.d/ratelimit.conf 增加
> limit_conn_zone $binary_remote_addr zone=apa_conn:10m;
> # server 块增加
> limit_conn apa_conn 2;
> ```

### 7.4 校验并生效

```bash
nginx -t && systemctl reload nginx && systemctl enable nginx
```

压测验证（用 GET 打 `/api/chat` 只返回 405，不会触发模型调用、不烧额度）：

```bash
for i in $(seq 1 100); do curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/api/chat & done > /tmp/rt.txt; wait
sort /tmp/rt.txt | uniq -c
# 预期：11 个 405（放行） + 89 个 429（拦截）
```

---

## 8. 验收清单

逐条跑，全部符合才算部署成功：

| # | 命令 | 预期 |
|---|---|---|
| 1 | `systemctl is-active alibaba-presale-agent nginx` | `active` `active` |
| 2 | `curl -s http://127.0.0.1:8000/api/health` | `{"ok":true,"kb_chunks":712,...}` |
| 3 | `curl -s http://<ECS_PUBLIC_IP>/` | 返回首页 HTML（标题「阿里小可爱AI问答助手」） |
| 4 | `curl -s -o /dev/null -w '%{http_code}' http://<ECS_PUBLIC_IP>/admin` | `200` |
| 5 | `curl -s -H 'X-Admin-Token: <你的ADMIN_TOKEN>' http://<IP>/api/admin/stats` | `{"total":N,...}`；**不带口令应 401** |
| 6 | `curl -s -N -o /dev/null -w 'TTFB=%{time_starttransfer}s' -X POST http://<IP>/api/chat -H 'Content-Type: application/json' -d '{"question":"你好","session_id":"t1"}'` | `TTFB` 在 1 秒内（说明流式未被缓冲） |
| 7 | 浏览器打开首页，问「qwen3.8-max 的输入价格是多少？」 | 20~30 秒内流式出现价格表 + 官方来源链接 |
| 8 | 重启机器后 `curl /api/health` | 仍 200（验证 `enable` + `Restart=always` 生效） |

---

## 9. 域名接入（可选）

### 9.1 解析

在云解析 DNS 里加：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---|---|---|---|
| A | `@` | `<ECS_PUBLIC_IP>` | 600 |
| A | `www` | `<ECS_PUBLIC_IP>` | 600 |

改完用**服务器侧**验证才准（本机 DNS 可能被公司网关劫持）：

```bash
ssh ... 'python3 -c "import socket;print(socket.gethostbyname(\"你的域名\"))"'
# 或绕过 DNS 直接验证 Host 路由
curl -s --resolve 你的域名:80:<ECS_PUBLIC_IP> http://你的域名/api/health
```

### 9.2 备案（大陆 ECS 的硬门槛）

- 大陆地域 ECS + 域名 + **80/443** → 必须有 ICP 备案，否则阿里云会在 80 端口返回备案提示页
- 判定方法：域名解析到该 IP 后，从**服务器上** `curl http://你的域名/` —— 返回你的页面 = 已可用；返回备案提示 = 未备案
- 未备案的临时办法：用非标端口（如 `http://域名:8000`）可访问，但**不推荐长期**，也不合规

### 9.3 HTTPS（备案后建议做）

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名 -d www.你的域名
```

### 9.4 办公网可能打不开

若公司网络有域名安全网关（如阿里云"云壳"），访问自有域名可能返回 403「域名不在安全策略默认允许范围内」。
这是**网络侧策略**，不是站点故障：同一站点用 IP 直连通常 200。解决方式是在网关控制台把域名加白。

---

## 10. 排障手册

| 症状 | 根因 | 处理 |
|---|---|---|
| `/api/health` 返回 200，但提问报 **401 Incorrect API key** | 只配了 Key，没配 `DASHSCOPE_BASE_URL`，回落到默认北京端点 | 补上配套的 workspace 端点，重启服务（§4.4） |
| 提问报 **403 Workspace endpoint access denied** | Key 与端点不属于同一 workspace | 换成配套的 `_KEY` + `_URL`（§4.4） |
| **Docker Hub `connection refused`** | 国内直连 docker.io 不通 | 走本手册的 venv 路线；或给 docker 配镜像加速器 |
| 容器 build 卡在 **`deb.debian.org`** 拉包 | 容器内 apt 源是海外源 | 容器内先 `sed` 换 `mirrors.aliyun.com`；或干脆不用 Docker |
| 日志刷 **`'utf-8' codec can't decode`** | macOS 打包带入 `._xxx` AppleDouble 文件 | 重新打包时 `--exclude='._*'`，或删掉服务器上的 `._*` |
| `qa.db` 属主是 **`502 staff`**、权限 644 | macOS 打包保留了 uid/gid | `chown -R root:root /opt/alibaba-presale-agent && chmod 600 /opt/alibaba-presale-agent/data/qa.db` |
| `scp` 卡住/被杀 | 网络或安全策略拦截 | 改用 `cat file \| ssh ... "cat > file"` 管道 |
| 页面能开，但回答**一次性蹦出来而非流式** | nginx 缓冲了 SSE | 确认 `proxy_buffering off;` + `proxy_cache off;` |
| 后台 `/admin` 打不开数据，提示 401 | 服务端设了 `ADMIN_TOKEN`，页面没填 | 在后台页顶部输入框填入同一个口令 |
| 后台「导出 CSV / 同步知识库」按钮报错 | 同上，缺 `X-Admin-Token` | 同上 |
| 换机器后**域名打不开** | 旧的是固定公网 IP，随实例释放已回收 | 更新 A 记录，或改用 EIP |

---

## 11. 日常运维

```bash
# 看日志
journalctl -u alibaba-presale-agent -f

# 改配置后重启
vim /opt/alibaba-presale-agent/.env && systemctl restart alibaba-presale-agent

# 备份交付记录
cp /opt/alibaba-presale-agent/data/qa.db /root/qa-$(date +%Y%m%d).db

# 更新代码（本地重新打包后）
tar xzf /tmp/apa_src.tar.gz -C /opt/alibaba-presale-agent && systemctl restart alibaba-presale-agent
# 注意：重启后要重建知识库索引，服务启动时自动做
```

### 费用与清理

- 按量实例 **持续计费**，2vCPU/4GiB 约 **¥0.31/小时 ≈ ¥7.4/天**
- 释放前先备份 `/opt/alibaba-presale-agent/data/qa.db`
- 释放顺序（控制台）：实例 → 安全组 → 交换机 → VPC；**实例释放不可逆，且公网 IP 一并回收**
- 想临时止血又不想释放：控制台「停止实例」→ 选「节省停机模式」（CPU/内存不再计费，云盘仍计费）

### 上线前安全自查

- [ ] 安全组 22 端口**只**放行自己的 IP
- [ ] 8000 端口**没有**对公网开放（应用只听 127.0.0.1）
- [ ] `ADMIN_TOKEN` 是 32 位随机串，不是手机号/生日
- [ ] `.env` 权限 `600`，属主 root
- [ ] `/opt/alibaba-presale-agent/data/qa.db` 权限 `600`
- [ ] 有 ICP 备案（用 80/443 时）
- [ ] 已上 HTTPS（否则提问内容在链路上是明文）
- [ ] 在百炼控制台设了**费用告警/额度上限**（最终兜底）
- [ ] 演示结束就释放机器（最彻底的风险消解）
