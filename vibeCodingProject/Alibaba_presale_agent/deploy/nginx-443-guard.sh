#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  day1cloud.cn 443 自愈守卫（cron 每 5 分钟，幂等，只恢复不变更）
#
#  背景（2026-11-20 事故）：重跑 deploy-ecs.sh 时 cat > 整段覆盖 nginx 站点
#  配置，模板只含 listen 80，把 443/ssl 段抹掉（并移走 share-oss 软链），
#  导致公网 HTTPS 拒绝连接 3 小时无人知晓。本脚本作为兜底：
#    1. 证书在而站点配置缺 443 ssl 段   → 自动补段并 reload
#    2. share-oss 配置在而软链缺失       → 重建软链
#    3. 配置正常但 443 未监听           → reload/start nginx
#    4. nginx -t 校验失败               → 回滚本次修改，保留现场记日志
#
#  日志：/var/log/apa-443-guard.log（无动作时不写，避免日志噪音）
#  安全边界：绝不删除文件、绝不修改证书、绝不在 -t 失败时 reload。
# ═══════════════════════════════════════════════════════════════════════════
set -u

LOG=/var/log/apa-443-guard.log
SITE=/etc/nginx/sites-available/alibaba-presale-agent
CERT=/etc/nginx/ssl/day1cloud.cn.fullchain.pem
KEY=/etc/nginx/ssl/day1cloud.cn.key
SHARE_SRC=/etc/nginx/sites-available/share-oss
SHARE_LNK=/etc/nginx/sites-enabled/share-oss

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

changed=0

# ── 1) 站点配置缺 443 段但证书存在 → 补写（先备份原文件以便回滚）──
if [ -f "$CERT" ] && [ -f "$KEY" ] && ! grep -q 'listen 443' "$SITE" 2>/dev/null; then
    BAK="$SITE.guard-bak.$(date +%s)"
    cp -a "$SITE" "$BAK"
    cat >> "$SITE" <<'TLS'

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name day1cloud.cn www.day1cloud.cn;

    ssl_certificate     /etc/nginx/ssl/day1cloud.cn.fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/day1cloud.cn.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 8m;
    limit_req zone=apa_chat burst=10 nodelay;
    limit_conn apa_conn 8;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        chunked_transfer_encoding on;
    }
}
TLS
    changed=1
    log "443 段缺失且证书存在 → 已自动补写（备份：$BAK）"
fi

# ── 2) share-oss 软链缺失 → 重建 ──
if [ -f "$SHARE_SRC" ] && [ ! -e "$SHARE_LNK" ]; then
    ln -sf "$SHARE_SRC" "$SHARE_LNK"
    changed=1
    log "share-oss 软链缺失 → 已重建"
fi

# ── 3) 生效：有改动，或 443 未监听（含“配置对但未 reload”场景）──
if [ "$changed" = "1" ] || ! ss -tln 2>/dev/null | grep -q ':443 '; then
    if nginx -t >/dev/null 2>&1; then
        if systemctl is-active --quiet nginx; then
            systemctl reload nginx
            log "nginx -t 通过 → 已 reload"
        else
            systemctl start nginx
            log "nginx 未运行 → 已启动"
        fi
        sleep 2
        if ss -tln | grep -q ':443 '; then
            log "OK：443 已恢复监听"
        else
            log "WARN：reload 后仍无 443 监听，需人工排查（证书路径 / listen 指令 / 模块加载）"
        fi
    else
        log "ERR：nginx -t 校验失败，不做任何 reload，保留现场待人工排查"
        if [ "$changed" = "1" ]; then
            LATEST=$(ls -t "$SITE".guard-bak.* 2>/dev/null | head -1)
            if [ -n "$LATEST" ]; then
                cp -a "$LATEST" "$SITE"
                log "已回滚本次对站点配置的修改（还原自 $LATEST）"
            fi
        fi
    fi
fi

exit 0
