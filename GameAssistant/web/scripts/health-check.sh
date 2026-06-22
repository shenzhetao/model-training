#!/bin/bash
# health-check.sh — 服务健康检查脚本
# 用法: ./scripts/health-check.sh
# 建议 crontab: */5 * * * * /opt/gameassistant/scripts/health-check.sh

set -euo pipefail

API_URL="${API_URL:-http://localhost:3000}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
FAILED=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

alert() {
    local msg="$1"
    log "[ALERT] $msg"
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$msg" | mail -s "[GameAssistant] 健康检查告警" "$ALERT_EMAIL"
    fi
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -s -X POST "$ALERT_WEBHOOK" -H 'Content-Type: application/json' \
            -d "{\"text\":\"[GameAssistant] $msg\"}" > /dev/null 2>&1 || true
    fi
}

# ── 1. 检查 Nginx ─────────────────────────────────────────
log "==> 检查 Nginx..."
if curl -sf --max-time 5 "${API_URL}/api/v1/users/me" > /dev/null 2>&1; then
    log "    Nginx: OK"
else
    log "    Nginx: FAIL"
    FAILED=1
    alert "Nginx / API 不可达"
fi

# ── 2. 检查 MySQL ─────────────────────────────────────────
log "==> 检查 MySQL..."
if docker exec ga_mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
    log "    MySQL: OK"
else
    log "    MySQL: FAIL"
    FAILED=1
    alert "MySQL 连接失败"
fi

# ── 3. 检查磁盘空间 ───────────────────────────────────────
log "==> 检查磁盘空间..."
ROOT_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$ROOT_USAGE" -gt 85 ]; then
    log "    磁盘使用率: ${ROOT_USAGE}% — 警告!"
    alert "磁盘空间不足: ${ROOT_USAGE}%"
elif [ "$ROOT_USAGE" -gt 70 ]; then
    log "    磁盘使用率: ${ROOT_USAGE}% — 注意"
else
    log "    磁盘使用率: ${ROOT_USAGE}% — OK"
fi

# ── 4. 检查 Docker 容器状态 ──────────────────────────────
log "==> 检查容器状态..."
for container in ga_mysql ga_backend ga_nginx; do
    STATUS=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
    if [ "$STATUS" == "healthy" ] || [ "$STATUS" == "unknown" ]; then
        # unknown for containers without healthcheck (nginx in prod)
        RUNNING=$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null || echo "false")
        if [ "$RUNNING" == "true" ]; then
            log "    $container: RUNNING"
        else
            log "    $container: NOT RUNNING"
            FAILED=1
            alert "$container 未运行"
        fi
    else
        log "    $container: $STATUS"
        FAILED=1
        alert "$container 健康检查失败: $STATUS"
    fi
done

# ── 5. 检查备份最近是否运行 ──────────────────────────────
log "==> 检查备份状态..."
LATEST_BACKUP=$(ls -t "$HOME/ga_backup_"*.sql.gz 2>/dev/null | head -1 || echo "")
if [ -n "$LATEST_BACKUP" ]; then
    DAYS_OLD=$(( ($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")) / 86400 ))
    if [ "$DAYS_OLD" -gt 2 ]; then
        log "    备份已超过 ${DAYS_OLD} 天未运行 — 警告!"
        alert "备份已超过 ${DAYS_OLD} 天未运行"
    else
        log "    最新备份: $(basename "$LATEST_BACKUP") (${DAYS_OLD} 天前)"
    fi
else
    log "    未找到备份文件!"
    alert "未找到备份文件"
fi

# ── 6. 检查 SSL 证书到期 ──────────────────────────────────
log "==> 检查 SSL 证书..."
CERT_FILE="${CERT_FILE:-/etc/nginx/certs/server.crt}"
if [ -f "$CERT_FILE" ]; then
    EXPIRY=$(openssl x509 -in "$CERT_FILE" -noout -enddate 2>/dev/null | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || echo 0)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
    if [ "$DAYS_LEFT" -lt 30 ]; then
        log "    SSL 证书将在 ${DAYS_LEFT} 天后到期 — 警告!"
        alert "SSL 证书将在 ${DAYS_LEFT} 天后到期"
    else
        log "    SSL 证书有效期: ${DAYS_LEFT} 天"
    fi
else
    log "    未找到 SSL 证书文件"
fi

# ── 总结 ───────────────────────────────────────────────────
if [ "$FAILED" -eq 0 ]; then
    log "==> 所有检查通过"
else
    log "==> 检查发现问题，请查看上述告警"
fi

exit $FAILED
