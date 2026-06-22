#!/bin/bash
# certbot-renew.sh — Let's Encrypt 自动续期脚本
# 用法: ./scripts/certbot-renew.sh
# crontab: 0 3 * * * /opt/gameassistant/scripts/certbot-renew.sh >> /var/log/certbot-renew.log 2>&1

set -euo pipefail

DOMAIN="${DOMAIN:-your-domain.com}"
EMAIL="${CERTBOT_EMAIL:-admin@${DOMAIN}}"
WEBROOT="${WEBROOT:-/var/www/letsencrypt}"
CERT_DIR="${CERT_DIR:-./certs}"
CONTAINER_NAME="${NGINX_CONTAINER:-ga_nginx}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ── 1. 创建 Webroot 目录 ──────────────────────────────────
mkdir -p "${WEBROOT}/.well-known/acme-challenge"

# ── 2. 申请/续期证书 ──────────────────────────────────────
log "==> 申请/续期 Let's Encrypt 证书 for ${DOMAIN}..."

docker run --rm \
  -v "${PWD}/${CERT_DIR}:/etc/letsencrypt" \
  -v "${PWD}/${WEBROOT}:/usr/share/nginx/html:ro" \
  certbot/certbot \
  certonly \
  --webroot \
  --webroot-path "/usr/share/nginx/html" \
  --email "${EMAIL}" \
  --agree-tos \
  --no-eff-email \
  --domains "${DOMAIN}" \
  --domains "www.${DOMAIN}"

# ── 3. 复制证书到 Nginx 目录 ──────────────────────────────
log "==> 复制证书到 Nginx 目录..."
mkdir -p "${CERT_DIR}"
cp "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${CERT_DIR}/server.crt"
cp "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" "${CERT_DIR}/server.key"
chmod 644 "${CERT_DIR}/server.crt"
chmod 600 "${CERT_DIR}/server.key"

# ── 4. 重载 Nginx ─────────────────────────────────────────
log "==> 重载 Nginx..."
docker exec "${CONTAINER_NAME}" nginx -s reload

log "==> 证书续期完成!"

# ── 5. 检查到期时间 ───────────────────────────────────────
NEW_EXPIRY=$(openssl x509 -in "${CERT_DIR}/server.crt" -noout -enddate | cut -d= -f2)
log "    新证书到期时间: ${NEW_EXPIRY}"
