#!/bin/bash
# backup.sh — 全量备份脚本（数据库 + 上传文件）
# 用法: ./scripts/backup.sh
# 建议 crontab: 0 2 * * * /opt/gameassistant/scripts/backup.sh

set -euo pipefail

# ── 配置 ────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/var/backups/gameassistant}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ga_backup_${DATE}"
CONTAINER_NAME="${CONTAINER_NAME:-ga_mysql}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# ── 初始化 ──────────────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ── 1. 数据库备份 ──────────────────────────────────────────
log "==> 备份 MySQL 数据库..."
docker exec "${CONTAINER_NAME}" mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  -u root \
  --password="${MYSQL_ROOT_PASSWORD}" \
  gameassistant \
  | gzip > "${BACKUP_DIR}/${BACKUP_NAME}_db.sql.gz"

DB_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}_db.sql.gz" | cut -f1)
log "    数据库备份完成: ${BACKUP_NAME}_db.sql.gz (${DB_SIZE})"

# ── 2. 上传文件备份 ────────────────────────────────────────
log "==> 备份上传文件..."
UPLOADS_DIR="${UPLOADS_DIR:-./uploads_data}"
if [ -d "${UPLOADS_DIR}" ]; then
  tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_uploads.tar.gz" -C "${UPLOADS_DIR}" .
  UPLOAD_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}_uploads.tar.gz" | cut -f1)
  log "    上传文件备份完成: ${BACKUP_NAME}_uploads.tar.gz (${UPLOAD_SIZE})"
else
  log "    警告: 上传目录不存在，跳过"
fi

# ── 3. 模型文件备份 ────────────────────────────────────────
log "==> 备份模型文件..."
MODELS_DIR="${MODELS_DIR:-./models_data}"
if [ -d "${MODELS_DIR}" ]; then
  tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_models.tar.gz" -C "${MODELS_DIR}" .
  MODEL_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}_models.tar.gz" | cut -f1)
  log "    模型文件备份完成: ${BACKUP_NAME}_models.tar.gz (${MODEL_SIZE})"
else
  log "    警告: 模型目录不存在，跳过"
fi

# ── 4. 生成备份清单 ────────────────────────────────────────
MANIFEST="${BACKUP_DIR}/${BACKUP_NAME}_manifest.txt"
{
  echo "Backup: ${BACKUP_NAME}"
  echo "Created: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "Hostname: $(hostname)"
  echo "DB Size: ${DB_SIZE}"
  echo "---"
  ls -lh "${BACKUP_DIR}"/ga_backup_"${DATE}"_* 2>/dev/null || true
} > "${MANIFEST}"
log "    清单: ${MANIFEST}"

# ── 5. 清理过期备份 ────────────────────────────────────────
log "==> 清理超过 ${RETENTION_DAYS} 天的旧备份..."
find "${BACKUP_DIR}" -name "ga_backup_*" -mtime "+${RETENTION_DAYS}" -delete
log "    清理完成"

# ── 6. 同步到远程（可选）──────────────────────────────────
if [ -n "${REMOTE_BACKUP_HOST:-}" ] && [ -n "${REMOTE_BACKUP_PATH:-}" ]; then
  log "==> 同步到远程备份服务器..."
  rsync -avz --progress "${BACKUP_DIR}/${BACKUP_NAME}"* \
    "${REMOTE_BACKUP_HOST}:${REMOTE_BACKUP_PATH}/"
  log "    远程同步完成"
fi

log "==> 备份全部完成: ${BACKUP_NAME}"
