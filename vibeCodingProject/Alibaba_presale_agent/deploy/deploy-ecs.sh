#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  百炼问答 Agent · ECS 一键部署脚本
#
#  在 ECS 上以 root 执行：
#      sudo bash deploy-ecs.sh
#
#  非交互方式（适合脚本化 / CI）：
#      sudo DASHSCOPE_API_KEY=sk-ws-xxx \
#           DASHSCOPE_BASE_URL=https://llm-xxx.xx.maas.aliyuncs.com/compatible-mode/v1 \
#           ADMIN_TOKEN=$(openssl rand -hex 16) \
#           SERVER_NAME=qa.example.com \
#           bash deploy-ecs.sh
#
#  源码来源（二选一）：
#      --from-github            从 GitHub 稀疏拉取（默认，代码需已 push）
#      --from-tar /tmp          从本机上传的 tar 包安装，读取：
#                                 /tmp/apa_src.tar.gz  （必需：app static run.py requirements.txt）
#                                 /tmp/apa_kb.tar.gz   （可选：知识库 md，不给则自动 clone）
#                                 /tmp/apa_data.tar.gz （可选：历史 SQLite）
#
#  幂等：可重复执行；会备份 data/ 与 .env，不会覆盖你的已有配置。
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/EthanNiWorld/ai-playbook-2026.git}"
APP_SUBDIR="${APP_SUBDIR:-vibeCodingProject/Alibaba_presale_agent}"
INSTALL_DIR="${INSTALL_DIR:-/opt/alibaba-presale-agent}"
SERVICE="alibaba-presale-agent"
PORT="8000"
SOURCE="github"
TAR_DIR="/tmp"

for arg in "$@"; do
  case "$arg" in
    --from-github) SOURCE="github" ;;
    --from-tar)    SOURCE="tar" ;;
    --from-tar=*)  SOURCE="tar"; TAR_DIR="${arg#*=}" ;;
    -h|--help)     sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "未知参数: $arg（-h 查看帮助）" >&2; exit 1 ;;
  esac
done

log()  { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ─────────────────────────────── 0. 前置检查 ───────────────────────────────
log "前置检查"
[ "$(id -u)" -eq 0 ] || die "请用 root 执行：sudo bash $0"
command -v systemctl >/dev/null || die "本脚本需要 systemd（请在 ECS 的 Ubuntu/Debian 上运行）"
. /etc/os-release 2>/dev/null || true
ok "系统：${PRETTY_NAME:-unknown} / 内核 $(uname -r) / 内存 $(free -m | awk '/Mem:/{print $2}')MB"

# ─────────────────────────────── 1. 采集配置 ───────────────────────────────
log "配置"
if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
  [ -f "$INSTALL_DIR/.env" ] || read -rp "  百炼 API Key (sk-...): " DASHSCOPE_API_KEY
fi
if [ -z "${DASHSCOPE_BASE_URL:-}" ]; then
  if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "  提示：workspace 专属 Key 必须配配套的专属端点；留空则用默认北京端点（仅对通用 Key 有效）"
    read -rp "  Base URL（回车用默认 https://dashscope.aliyuncs.com/compatible-mode/v1）: " DASHSCOPE_BASE_URL
    DASHSCOPE_BASE_URL="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
  fi
fi
if [ -z "${ADMIN_TOKEN:-}" ] && [ ! -f "$INSTALL_DIR/.env" ]; then
  ADMIN_TOKEN="$(openssl rand -hex 16)"
  echo "  已自动生成后台口令 ADMIN_TOKEN=$ADMIN_TOKEN（请记下）"
fi
: "${QA_MODEL:=qwen3.8-max}"
: "${SERVER_NAME:=_}"

# ─────────────────────────────── 2. 系统依赖 ───────────────────────────────
log "安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
if ! grep -q 'mirrors.aliyun.com' /etc/apt/sources.list 2>/dev/null; then
  sed -i 's|http://.*archive.ubuntu.com|https://mirrors.aliyun.com|g; s|http://security.ubuntu.com|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true
fi
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip git curl nginx openssl ca-certificates
ok "python $(python3 -V 2>&1 | awk '{print $2}') / nginx $(nginx -v 2>&1 | awk -F/ '{print $2}')"

# ─────────────────────────────── 3. 取源码 ───────────────────────────────
log "获取应用代码（来源：$SOURCE）"
# 临时工作目录：脚本结束后保留（内容很小），如无用可手动删除
WORK="$(mktemp -d)"

if [ "$SOURCE" = "github" ]; then
  git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$WORK/src" >/dev/null 2>&1 \
    || die "GitHub 拉取失败。若代码尚未 push，请改用 --from-tar（见 -h）"
  ( cd "$WORK/src" && git sparse-checkout set "$APP_SUBDIR" >/dev/null 2>&1 )
  [ -f "$WORK/src/$APP_SUBDIR/run.py" ] \
    || die "远端 $APP_SUBDIR 不存在。请先把该目录 push 到 GitHub，或改用 --from-tar"
  SRC="$WORK/src/$APP_SUBDIR"
  ok "已拉取 $APP_SUBDIR"
else
  [ -f "$TAR_DIR/apa_src.tar.gz" ] || die "缺少 $TAR_DIR/apa_src.tar.gz"
  mkdir -p "$WORK/src" && tar xzf "$TAR_DIR/apa_src.tar.gz" -C "$WORK/src"
  [ -f "$WORK/src/run.py" ] || die "apa_src.tar.gz 内容不含 run.py，打包目录不对"
  SRC="$WORK/src"
  ok "已从 tar 包解出源码"
fi

# ─────────────────────────────── 4. 落盘（幂等） ───────────────────────────────
log "安装到 $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
if [ -d "$INSTALL_DIR/app" ]; then
  BAK="$INSTALL_DIR/backup-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BAK"
  cp -a "$INSTALL_DIR/.env" "$BAK"/ 2>/dev/null || true
  cp -a "$INSTALL_DIR/data" "$BAK"/ 2>/dev/null || true
  warn "检测到旧版本，已备份 .env 与 data 到 $BAK"
fi
for item in app static run.py requirements.txt Dockerfile deploy; do
  if [ -e "$SRC/$item" ]; then
    cp -a "$SRC/$item" "$INSTALL_DIR"/
  fi
done

# 知识库：tar 模式且带了 kb 包则落地；否则留给服务自动 sparse clone
if [ "$SOURCE" = "tar" ] && [ -f "$TAR_DIR/apa_kb.tar.gz" ]; then
  mkdir -p "$INSTALL_DIR/kb"
  tar xzf "$TAR_DIR/apa_kb.tar.gz" -C "$INSTALL_DIR/kb"
  KB_MODE="local"
  ok "知识库已落地 $(find "$INSTALL_DIR/kb" -name '*.md' | wc -l) 个 md"
else
  KB_MODE="clone"
  ok "知识库：服务启动时自动 sparse clone（约 2~3 秒，83MB）"
fi

# 历史数据
if [ "$SOURCE" = "tar" ] && [ -f "$TAR_DIR/apa_data.tar.gz" ]; then
  tar xzf "$TAR_DIR/apa_data.tar.gz" -C "$INSTALL_DIR"
  ok "已导入历史交付记录"
fi

chown -R root:root "$INSTALL_DIR"
chmod 700 "$INSTALL_DIR/data" 2>/dev/null || true
chmod 600 "$INSTALL_DIR/data/qa.db" 2>/dev/null || true

# ─────────────────────────────── 5. 写 .env ───────────────────────────────
log "写入运行时配置"
if [ -n "${DASHSCOPE_API_KEY:-}" ]; then
  cat > "$INSTALL_DIR/.env" <<EOF
DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
DASHSCOPE_BASE_URL=${DASHSCOPE_BASE_URL:-}
ADMIN_TOKEN=${ADMIN_TOKEN:-}
QA_MODEL=${QA_MODEL}
EOF
  chmod 600 "$INSTALL_DIR/.env"
  ok ".env 已写入（4 个变量，权限 600）"
else
  warn "沿用已有 $INSTALL_DIR/.env"
fi
grep -q '^DASHSCOPE_API_KEY=..*' "$INSTALL_DIR/.env" || die ".env 里 DASHSCOPE_API_KEY 为空，无法启动"

# ─────────────────────────────── 6. Python 依赖 ───────────────────────────────
log "安装 Python 依赖"
if [ ! -x "$INSTALL_DIR/.venv/bin/python" ]; then
  python3 -m venv "$INSTALL_DIR/.venv"
fi
"$INSTALL_DIR/.venv/bin/pip" install -q --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/
"$INSTALL_DIR/.venv/bin/pip" install -q --no-input -i https://mirrors.aliyun.com/pypi/simple/ -r "$INSTALL_DIR/requirements.txt"
"$INSTALL_DIR/.venv/bin/python" -c "import fastapi,uvicorn,openai,httpx,dotenv" || die "依赖导入失败"
ok "依赖就绪"

# ─────────────────────────────── 7. systemd ───────────────────────────────
log "注册系统服务"
ENV_LINE=""
if [ "$KB_MODE" = "local" ]; then
  ENV_LINE="Environment=LOCAL_KNOWLEDGE_PATH=$INSTALL_DIR/kb"
fi
cat > /etc/systemd/system/${SERVICE}.service <<EOF
[Unit]
Description=Bailian QA Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
$ENV_LINE
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/.venv/bin/python run.py --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now "$SERVICE" >/dev/null 2>&1
systemctl restart "$SERVICE"
ok "服务已启动（仅监听 127.0.0.1:$PORT）"

# ─────────────────────────────── 8. nginx ───────────────────────────────
log "配置 nginx 反代与限流"
# 幂等处理：旧版可能留有其他文件也定义了同名 zone，会报 duplicate zone，先移到备份
mkdir -p /root/nginx-conf-backup
for f in /etc/nginx/conf.d/*.conf; do
  [ -f "$f" ] || continue
  case "$f" in */apa-ratelimit.conf) continue ;; esac
  if grep -q 'zone=apa_chat' "$f" 2>/dev/null; then
    mv "$f" "/root/nginx-conf-backup/$(basename "$f").$(date +%s)"
    warn "已移走旧限流配置：$f（备份在 /root/nginx-conf-backup/）"
  fi
done

cat > /etc/nginx/conf.d/apa-ratelimit.conf <<'EOF'
limit_req_zone $binary_remote_addr zone=apa_chat:10m rate=100r/m;
limit_conn_zone $binary_remote_addr zone=apa_conn:10m;
limit_req_status 429;
EOF

cat > /etc/nginx/sites-available/alibaba-presale-agent <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $SERVER_NAME;

    client_max_body_size 8m;
    limit_req zone=apa_chat burst=10 nodelay;
    limit_conn apa_conn 8;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
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
if [ -e /etc/nginx/sites-enabled/default ]; then
  mv /etc/nginx/sites-enabled/default /root/nginx-default.bak
fi
nginx -t >/dev/null 2>&1 || die "nginx 配置校验失败：nginx -t 查看详情"
systemctl enable nginx >/dev/null 2>&1 || true
systemctl reload nginx
ok "nginx 已生效（80 → 127.0.0.1:$PORT，SSE 不缓冲，100r/m 限流）"

# ─────────────────────────────── 9. 健康检查 ───────────────────────────────
log "健康检查（首次启动需 clone 知识库，最多等 90 秒）"
CHUNKS=0
for i in $(seq 1 30); do
  sleep 3
  CHUNKS=$(curl -s --max-time 5 "http://127.0.0.1:$PORT/api/health" 2>/dev/null | sed -n 's/.*"kb_chunks":\([0-9]*\).*/\1/p' || echo 0)
  if [ "${CHUNKS:-0}" -gt 0 ]; then
    break
  fi
  printf '.'
done
echo

if [ "${CHUNKS:-0}" -gt 0 ]; then
  ok "知识库索引 $CHUNKS 个片段"
else
  warn "知识库片段为 0：多半是 clone 失败。检查 'journalctl -u $SERVICE -n 50'，或改用 --from-tar 携带 apa_kb.tar.gz"
fi

PUB_IP="$(curl -s --max-time 5 https://ipinfo.io/ip 2>/dev/null || curl -s --max-time 5 ifconfig.me 2>/dev/null || echo '<ECS_PUBLIC_IP>')"
TOKEN_SHOW="$(grep '^ADMIN_TOKEN=' "$INSTALL_DIR/.env" | cut -d= -f2-)"

cat <<EOF

════════════════════════════════════════════════════════════════
 部署完成
════════════════════════════════════════════════════════════════
  首页      http://$PUB_IP/
  后台      http://$PUB_IP/admin
  后台口令  ${TOKEN_SHOW:-（未设置，任何人都能看后台）}
  健康检查  curl http://$PUB_IP/api/health

  日志      journalctl -u $SERVICE -f
  重启      systemctl restart $SERVICE
  改配置    vim $INSTALL_DIR/.env && systemctl restart $SERVICE
  备份数据  cp $INSTALL_DIR/data/qa.db /root/qa-\$(date +%F).db

  安全提醒：确认安全组只放行 22（限自己 IP）与 80，不要开放 $PORT。
  临时目录  $WORK（脚本未自动清理，可手动删除）
════════════════════════════════════════════════════════════════
EOF
