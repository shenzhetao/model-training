@echo off
rem restore.sh — 备份恢复脚本（Windows / Git Bash / WSL）
rem 用法: bash restore.sh 20260623_020000

setlocal

set BACKUP_DIR="C:\backups\gameassistant"
set BACKUP_NAME=%1

if "%BACKUP_NAME%"=="" (
    echo 用法: bash restore.sh ga_backup_YYYYMMDD_HHMMSS
    exit /b 1
)

echo [RESTORE] 开始恢复备份: %BACKUP_NAME%

set DB_BACKUP=%BACKUP_DIR%\%BACKUP_NAME%_db.sql.gz
set UPLOADS_BACKUP=%BACKUP_DIR%\%BACKUP_NAME%_uploads.tar.gz
set MODELS_BACKUP=%BACKUP_DIR%\%BACKUP_NAME%_models.tar.gz

rem ── 1. 恢复数据库 ──────────────────────────────────────
if exist "%DB_BACKUP%" (
    echo [RESTORE] 恢复数据库...
    docker exec -i ga_mysql mysql -u root --password=%MYSQL_ROOT_PASSWORD% gameassistant _
        < "%DB_BACKUP%"
    echo [RESTORE] 数据库恢复完成
) else (
    echo [RESTORE] 警告: 数据库备份文件不存在: %DB_BACKUP%
)

rem ── 2. 恢复上传文件 ────────────────────────────────────
if exist "%UPLOADS_BACKUP%" (
    echo [RESTORE] 恢复上传文件...
    docker cp "%UPLOADS_BACKUP%" ga_backend:/tmp/uploads_backup.tar.gz
    docker exec ga_backend bash -c "cd /app/uploads && tar -xzf /tmp/uploads_backup.tar.gz && rm /tmp/uploads_backup.tar.gz"
    echo [RESTORE] 上传文件恢复完成
) else (
    echo [RESTORE] 警告: 上传文件备份不存在，跳过
)

rem ── 3. 恢复模型文件 ────────────────────────────────────
if exist "%MODELS_BACKUP%" (
    echo [RESTORE] 恢复模型文件...
    docker cp "%MODELS_BACKUP%" ga_backend:/tmp/models_backup.tar.gz
    docker exec ga_backend bash -c "cd /app/models && tar -xzf /tmp/models_backup.tar.gz && rm /tmp/models_backup.tar.gz"
    echo [RESTORE] 模型文件恢复完成
) else (
    echo [RESTORE] 警告: 模型文件备份不存在，跳过
)

echo [RESTORE] 恢复全部完成!
