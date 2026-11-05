#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  百炼问答 Agent · ECS 一键部署（Docker 容器化）
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
#      --from-tar /tmp          从本机上传的 tar 包构建，读取：
#                                 /tmp/apa_src.tar.gz  （必需：app static run.py requirements.txt Dockerfile）
#                                 /tmp/apa_data.tar.gz （可选：历史 SQLite，仅在数据卷为空时导入）
#
#  其他参数：
#      --no-build               跳过镜像构建，直接用现有 alibaba-presale-agent:latest
#
#  幂等：可重复执行。容器会被重建，named volume 与 .env 保留并备份。
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/EthanNiWorld/ai-playbook-2026.git}"
APP_SUBDIR="${APP_SUBDIR:-vibeCodingProject/Alibaba_presale_agent}"
INSTALL_DIR="${INSTALL_DIR:-/opt/alibaba-presale-agent}"
SERVICE="alibaba-presale-agent"          # 容器名（同时用于旧 systemd 服务清理）
IMAGE="${IMAGE:-alibaba-presale-agent:latest}"
VOLUME="${VOLUME:-alibaba-presale-agent-data}"
PORT="${PORT:-8000}"
SOURCE="github"
TAR_DIR="/tmp"
DO_BUILD=1
# 构建源：apt 用阿里云；pip 用清华（阿里云 PyPI 镜像缺 pydantic 2.14.3，会解析失败）
APT_MIRROR="${APT_MIRROR:-mirrors.aliyun.com}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

for arg in "$@"; do
  case "$arg" in
    --from-github) SOURCE="github" ;;
    --from-tar)    SOURCE="tar" ;;
    --from-tar=*)  SOURCE="tar"; TAR_DIR="${arg#*=}" ;;
    --no-build)    DO_BUILD=0 ;;
    -h|--help)     sed -n '2,25p' "$0"; exit 0 ;;
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

# 旧的原生部署（systemd + venv）会占用端口，先停掉再交给容器
for svc in "$SERVICE" bqa; do
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    systemctl disable --now "$svc" >/dev/null 2>&1 || true
    warn "已停止旧 systemd 服务 $svc（其目录保留，可作回滚备份）"
  fi
done

# ─────────────────────────────── 1. 采集配置 ───────────────────────────────
log "配置"
EXISTING_ENV="$INSTALL_DIR/.env"
# 已有 .env 里同名的值作为默认，重跑不会丢配置
env_get() { [ -f "$EXISTING_ENV" ] && sed -n "s/^$1=//p" "$EXISTING_ENV" | head -1 || true; }

DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-$(env_get DASHSCOPE_API_KEY)}"
DASHSCOPE_BASE_URL="${DASHSCOPE_BASE_URL:-$(env_get DASHSCOPE_BASE_URL)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-$(env_get ADMIN_TOKEN)}"
TAVILY_API_KEY="${TAVILY_API_KEY:-$(env_get TAVILY_API_KEY)}"
QA_MODEL="${QA_MODEL:-$(env_get QA_MODEL)}"
KNOWLEDGE_REPO_URL="${KNOWLEDGE_REPO_URL:-$(env_get KNOWLEDGE_REPO_URL)}"
KB_SYNC_INTERVAL_HOURS="${KB_SYNC_INTERVAL_HOURS:-$(env_get KB_SYNC_INTERVAL_HOURS)}"
KB_AUTO_SYNC="${KB_AUTO_SYNC:-$(env_get KB_AUTO_SYNC)}"
PRICE_PAGE_TTL_HOURS="${PRICE_PAGE_TTL_HOURS:-$(env_get PRICE_PAGE_TTL_HOURS)}"

if [ -z "$DASHSCOPE_API_KEY" ]; then
  [ -t 0 ] || die "缺少 DASHSCOPE_API_KEY（非交互环境请通过环境变量传入）"
  read -rp "  百炼 API Key (sk-...): " DASHSCOPE_API_KEY
fi
[ -n "$DASHSCOPE_API_KEY" ] || die "DASHSCOPE_API_KEY 不能为空"

if [ -z "$DASHSCOPE_BASE_URL" ] && [ -t 0 ]; then
  echo "  提示：workspace 专属 Key 必须配配套的专属端点；留空则用默认北京端点（仅对通用 Key 有效）"
  read -rp "  Base URL（回车用默认 https://dashscope.aliyuncs.com/compatible-mode/v1）: " DASHSCOPE_BASE_URL
fi
DASHSCOPE_BASE_URL="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"

if [ -z "$ADMIN_TOKEN" ]; then
  ADMIN_TOKEN="$(openssl rand -hex 16)"
  echo "  已自动生成后台口令 ADMIN_TOKEN=$ADMIN_TOKEN（请记下）"
fi
: "${QA_MODEL:=qwen3.8-max}"
: "${KNOWLEDGE_REPO_URL:=$REPO_URL}"
: "${KB_SYNC_INTERVAL_HOURS:=24}"
: "${KB_AUTO_SYNC:=1}"
: "${PRICE_PAGE_TTL_HOURS:=6}"
: "${SERVER_NAME:=_}"

# ─────────────────────────────── 2. 系统依赖 ───────────────────────────────
log "安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
if ! grep -q 'mirrors.aliyun.com' /etc/apt/sources.list 2>/dev/null; then
  sed -i 's|http://.*archive.ubuntu.com|https://mirrors.aliyun.com|g; s|http://security.ubuntu.com|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true
fi
apt-get update -qq
apt-get install -y -qq git curl nginx openssl ca-certificates
if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y -qq docker.io
  systemctl enable --now docker >/dev/null 2>&1 || true
fi
docker info >/dev/null 2>&1 || die "docker daemon 未运行：systemctl start docker 后重试"
ok "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null) / nginx $(nginx -v 2>&1 | awk -F/ '{print $2}')"

# ─────────────────────────────── 3. 取源码 ───────────────────────────────
log "获取应用代码（来源：$SOURCE）"
WORK="$(mktemp -d)"

if [ "$SOURCE" = "github" ]; then
  git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$WORK/src" >/dev/null 2>&1 \
    || die "GitHub 拉取失败（境内直连常超时）。若代码尚未 push，或用不了 GitHub，请改用 --from-tar"
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
if [ -f "$EXISTING_ENV" ]; then
  BAK="$INSTALL_DIR/backup-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BAK"
  cp -a "$EXISTING_ENV" "$BAK"/ 2>/dev/null || true
  warn "已备份旧 .env 到 $BAK（数据在卷 $VOLUME 中，不受影响）"
fi
# 只同步构建/运行所需文件；data 始终在 named volume 里，不落宿主目录
for item in app static run.py requirements.txt Dockerfile docker-compose.yml \
            .dockerignore .env.example deploy docs LICENSE README.md; do
  if [ -e "$SRC/$item" ]; then
    cp -a "$SRC/$item" "$INSTALL_DIR"/
  fi
done
ok "源码已就位"

# ─────────────────────────────── 5. 写 .env ───────────────────────────────
log "写入运行时配置"
cat > "$EXISTING_ENV" <<EOF
DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
DASHSCOPE_BASE_URL=${DASHSCOPE_BASE_URL}
ADMIN_TOKEN=${ADMIN_TOKEN}
QA_MODEL=${QA_MODEL}
TAVILY_API_KEY=${TAVILY_API_KEY}
KNOWLEDGE_REPO_URL=${KNOWLEDGE_REPO_URL}
KB_SYNC_INTERVAL_HOURS=${KB_SYNC_INTERVAL_HOURS}
KB_AUTO_SYNC=${KB_AUTO_SYNC}
PRICE_PAGE_TTL_HOURS=${PRICE_PAGE_TTL_HOURS}
EOF
chmod 600 "$EXISTING_ENV"
ok ".env 已写入（9 个变量，权限 600）"

# ─────────────────────────────── 6. 构建镜像 ───────────────────────────────
if [ "$DO_BUILD" = "1" ]; then
  log "构建镜像 $IMAGE（首次约 2~4 分钟；有缓存时秒级）"
  docker build \
    --build-arg APT_MIRROR="$APT_MIRROR" \
    --build-arg PIP_INDEX_URL="$PIP_INDEX_URL" \
    -t "$IMAGE" "$INSTALL_DIR" \
    || die "镜像构建失败。若卡在拉取基础镜像，改用镜像站：BASE_IMAGE=<镜像站>/python:3.12-slim 重新执行"
  ok "镜像就绪：$(docker images "$IMAGE" --format '{{.Repository}}:{{.Tag}} {{.Size}}' | head -1)"
else
  docker image inspect "$IMAGE" >/dev/null 2>&1 || die "--no-build 但本地没有 $IMAGE"
  ok "跳过构建，复用现有镜像"
fi

# ─────────────────────────────── 7. 数据卷 ───────────────────────────────
log "准备数据卷 $VOLUME"
docker volume create "$VOLUME" >/dev/null
# 卷内是否已有数据库（有则视为线上数据，绝不用旧文件覆盖）
HAS_DB="$(docker run --rm --user root -v "$VOLUME":/app/data --entrypoint bash "$IMAGE" \
  -c 'test -f /app/data/qa.db && echo yes || echo no' 2>/dev/null || echo no)"

if [ "$HAS_DB" = "yes" ]; then
  ok "数据卷中已有交付记录，跳过迁移（沿用现有数据）"
else
  LEGACY_DATA=""
  for d in "$TAR_DIR/apa_data" "$INSTALL_DIR/data" /opt/bqa/data; do
    if [ -f "$d/qa.db" ]; then LEGACY_DATA="$d"; break; fi
  done
  # tar 包里带的历史数据包
  if [ -z "$LEGACY_DATA" ] && [ -f "$TAR_DIR/apa_data.tar.gz" ]; then
    mkdir -p "$TAR_DIR/apa_data" && tar xzf "$TAR_DIR/apa_data.tar.gz" -C "$TAR_DIR/apa_data"
    [ -f "$TAR_DIR/apa_data/qa.db" ] && LEGACY_DATA="$TAR_DIR/apa_data"
  fi
  if [ -n "$LEGACY_DATA" ]; then
    docker run --rm --user root -v "$VOLUME":/app/data -v "$LEGACY_DATA":/legacy:ro \
      --entrypoint bash "$IMAGE" \
      -c 'cp /legacy/qa.db /app/data/qa.db && chown -R 10001:10001 /app/data' \
      && ok "已导入历史交付记录（来源：$LEGACY_DATA）" \
      || warn "历史数据导入失败，将从空库开始"
  else
    ok "无历史数据可迁移，从空库开始"
  fi
fi

# 知识库：卷内已是 git 检出则复用；否则容器内 clone；再失败才退回本地旧 kb
LOCAL_KB_ENV=""
HAS_GIT_KB="$(docker run --rm --user root -v "$VOLUME":/app/data --entrypoint bash "$IMAGE" \
  -c 'test -d /app/data/kb/.git && echo yes || echo no' 2>/dev/null || echo no)"
if [ "$HAS_GIT_KB" = "yes" ]; then
  ok "数据卷中已有 git 知识库，定时同步可直接工作"
else
  log "克隆知识库到数据卷（境内访问 GitHub 可能较慢，最多等 150 秒）"
  if docker run --rm --user root -v "$VOLUME":/app/data --entrypoint bash "$IMAGE" -c "
      [ -d /app/data/kb ] && mv /app/data/kb /app/data/kb.bak.\$(date +%s)
      timeout 150 git clone -q --depth 1 --filter=blob:none --sparse '$KNOWLEDGE_REPO_URL' /app/data/kb \
        && cd /app/data/kb \
        && git sparse-checkout set alibaba-ai-hub knowledge/ai-general-notes \
        && chown -R 10001:10001 /app/data/kb"; then
    ok "知识库已克隆（容器内私有副本，含 .git，支持每日自动检查更新）"
  else
    LEGACY_KB=""
    for d in "$INSTALL_DIR/kb" /opt/bqa/kb; do
      if [ -d "$d/alibaba-ai-hub" ]; then LEGACY_KB="$d"; break; fi
    done
    if [ -n "$LEGACY_KB" ]; then
      docker run --rm --user root -v "$VOLUME":/app/data -v "$LEGACY_KB":/legacy:ro \
        --entrypoint bash "$IMAGE" \
        -c 'mkdir -p /app/data/kb && cp -a /legacy/. /app/data/kb/ && chown -R 10001:10001 /app/data/kb'
      LOCAL_KB_ENV="-e LOCAL_KNOWLEDGE_PATH=/app/data/kb"
      warn "GitHub 克隆失败，已复用本地旧知识库（$LEGACY_KB，只读快照，不含 .git → 自动同步会跳过）"
    else
      warn "知识库未就绪：容器启动时会再试一次 clone，若仍失败请检查网络"
    fi
  fi
fi

# ─────────────────────────────── 8. 起容器 ───────────────────────────────
log "启动容器 $SERVICE"
# 生成重建脚本：改完 .env 只需 bash run-container.sh，不必重跑整个部署
{
  cat <<EOF
#!/usr/bin/env bash
# 由 deploy-ecs.sh 生成：按当前 $INSTALL_DIR/.env 重建容器（数据卷保留）
set -euo pipefail
docker rm -f $SERVICE >/dev/null 2>&1 || true
docker run -d --name $SERVICE --restart unless-stopped \\
  -p $PORT:$PORT \\
  --env-file $INSTALL_DIR/.env \\
  -v $VOLUME:/app/data \\
EOF
  [ -n "$LOCAL_KB_ENV" ] && printf '  %s \\\n' "$LOCAL_KB_ENV"
  printf '  %s\n' "$IMAGE"
} > "$INSTALL_DIR/run-container.sh"
chmod 700 "$INSTALL_DIR/run-container.sh"

docker rm -f "$SERVICE" >/dev/null 2>&1 || true
bash "$INSTALL_DIR/run-container.sh" >/dev/null
sleep 3
docker ps --filter "name=^${SERVICE}$" --format '{{.Status}}' | grep -q Up \
  || die "容器启动失败：docker logs $SERVICE 查看原因"
ok "容器已启动（$PORT → /app/data 挂载卷 $VOLUME）"

# ─────────────────────────────── 9. nginx ───────────────────────────────
log "配置 nginx 反代与限流"
# 旧部署可能留有自己写的限流文件（limit_req_zone / limit_req_status 都是全局指令，
# 与本脚本的 apa-ratelimit.conf 重复会导致 nginx -t 失败），先移到备份；
# 失败可一键回滚，避免把线上 nginx 配坏。
mkdir -p /root/nginx-conf-backup
MOVED=()
move_aside() {
  local src="$1" dst="/root/nginx-conf-backup/$(basename "$1").$(date +%s).$$"
  mv "$src" "$dst"; MOVED+=("$src|$dst")
  warn "已移走冲突配置：$src"
}

for f in /etc/nginx/conf.d/*.conf; do
  [ -f "$f" ] || continue
  case "$f" in */apa-ratelimit.conf) continue ;; esac
  if grep -qE 'limit_(req|conn)_(zone|status)' "$f" 2>/dev/null; then move_aside "$f"; fi
done

# 旧站点（如 bqa）与本站点同为 default_server，会报 duplicate default_server
for f in /etc/nginx/sites-enabled/*; do
  [ -e "$f" ] || continue
  case "$(basename "$f")" in alibaba-presale-agent|default) continue ;; esac
  move_aside "$f"
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
if ! nginx -t >/dev/null 2>&1; then
  # 校验失败：把移走的旧配置原样放回，保证线上 nginx 仍可用
  for pair in ${MOVED[@]+"${MOVED[@]}"}; do
    mv "${pair#*|}" "${pair%%|*}" 2>/dev/null || true
  done
  nginx -t >/dev/null 2>&1 && systemctl reload nginx >/dev/null 2>&1 || true
  die "nginx 配置校验失败，已回滚旧配置。执行 nginx -t 查看具体原因"
fi
systemctl enable nginx >/dev/null 2>&1 || true
systemctl reload nginx
ok "nginx 已生效（80 → 127.0.0.1:$PORT，SSE 不缓冲，100r/m 限流）"

# ─────────────────────────────── 10. 健康检查 ───────────────────────────────
log "健康检查（首次启动需建索引，最多等 90 秒）"
CHUNKS=0
for _ in $(seq 1 30); do
  sleep 3
  CHUNKS=$(curl -s --max-time 5 "http://127.0.0.1:$PORT/api/health" 2>/dev/null \
    | sed -n 's/.*"kb_chunks":\([0-9]*\).*/\1/p' || echo 0)
  if [ "${CHUNKS:-0}" -gt 0 ]; then break; fi
  printf '.'
done
echo

if [ "${CHUNKS:-0}" -gt 0 ]; then
  ok "知识库索引 $CHUNKS 个片段"
else
  warn "知识库片段为 0：多半是 clone 失败。查看 'docker logs $SERVICE | tail -30'，或改用 --from-tar 携带 apa_kb.tar.gz"
fi

PUB_IP="$(curl -s --max-time 5 https://ipinfo.io/ip 2>/dev/null || curl -s --max-time 5 ifconfig.me 2>/dev/null || echo '<ECS_PUBLIC_IP>')"

cat <<EOF

════════════════════════════════════════════════════════════════
 部署完成（Docker 容器：$SERVICE）
════════════════════════════════════════════════════════════════
  首页      http://$PUB_IP/
  后台      http://$PUB_IP/admin
  后台口令  $ADMIN_TOKEN
  健康检查  curl http://$PUB_IP/api/health

  日志      docker logs -f $SERVICE
  重启      docker restart $SERVICE
  改配置    vim $INSTALL_DIR/.env && bash $INSTALL_DIR/run-container.sh
  备份数据  docker cp $SERVICE:/app/data/qa.db ~/qa-\$(date +%F).db（建议先 docker stop $SERVICE）
  数据卷    $VOLUME（docker volume inspect $VOLUME 看宿主路径）

  安全提醒：确认安全组只放行 22（限自己 IP）与 80，不要开放 $PORT。
  临时目录  $WORK（脚本未自动清理，可手动删除）
════════════════════════════════════════════════════════════════
EOF
