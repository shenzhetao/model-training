# GameAssistant 生产环境检查清单
# 部署前逐项确认

---

## 1. 环境准备

- [ ] 域名已解析到服务器 IP
- [ ] 服务器防火墙开放 80 (HTTP) 和 443 (HTTPS) 端口
- [ ] Docker & Docker Compose 已安装
- [ ] 域名 SSL 证书已申请（Let's Encrypt 或商业证书）

## 2. 环境变量

```bash
# 必需 - 部署前必须修改
JWT_SECRET_KEY=your-super-secret-random-key-here
MYSQL_ROOT_PASSWORD=your-secure-root-password
MYSQL_PASSWORD=your-secure-db-password

# 建议修改
APP_NAME=GameAssistant
CORS_ORIGINS=https://your-domain.com

# 根据需要
BACKEND_PORT=8000
HTTPS_PORT=443
HTTP_PORT=80
```

## 3. 目录权限

```bash
# 上传目录
mkdir -p uploads_data templates_data models_data nginx_cache
chmod 755 uploads_data templates_data models_data

# 备份目录
mkdir -p /var/backups/gameassistant
chmod 700 /var/backups/gameassistant

# SSL 证书目录
mkdir -p certs
chmod 700 certs
```

## 4. 数据库

- [ ] 首次部署：执行数据库迁移 SQL
  ```bash
  docker compose exec mysql mysql -u root -p gameassistant < migrations/sql/V1__initial_schema.sql
  ```
- [ ] 非首次部署：确认数据卷持久化配置正确
- [ ] 确认 `character-set-server=utf8mb4`

## 5. SSL 证书

- [ ] 证书文件放在 `certs/server.crt` 和 `certs/server.key`
- [ ] 测试自签名证书：
  ```bash
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout certs/server.key -out certs/server.crt \
    -subj "/CN=your-domain.com"
  ```
- [ ] Let's Encrypt 证书：参考 `scripts/certbot-renew.sh`

## 6. Docker Compose 启动

```bash
# 1. 复制并编辑环境变量
cp .env.example .env.prod
vim .env.prod

# 2. 启动所有服务
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 3. 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 4. 检查健康状态
docker compose ps
```

## 7. 健康检查

```bash
# API 健康检查
curl http://localhost:3000/api/v1/users/me

# Nginx 日志
docker exec ga_nginx tail -f /var/log/nginx/ga_access.log

# 后端日志
docker compose logs -f backend

# 磁盘使用
df -h
```

## 8. 自动化任务

- [ ] 备份脚本 `scripts/backup.sh` 已配置并测试
- [ ] 健康检查 `scripts/health-check.sh` 已配置到 crontab：
  ```cron
  0 2 * * * /opt/gameassistant/scripts/backup.sh >> /var/log/ga_backup.log 2>&1
  */5 * * * * /opt/gameassistant/scripts/health-check.sh >> /var/log/ga_health.log 2>&1
  0 3 * * * /opt/gameassistant/scripts/certbot-renew.sh >> /var/log/certbot-renew.log 2>&1
  ```
- [ ] 备份文件是否成功上传到远程存储

## 9. 安全检查

- [ ] JWT_SECRET_KEY 已修改（非默认值）
- [ ] 数据库密码已修改（非默认值）
- [ ] 禁用了 DEBUG 模式（DEBUG=false）
- [ ] 未暴露 3306 端口到外网
- [ ] SSL/TLS 1.2+ 已启用
- [ ] 定期查看 Nginx 访问日志异常

## 10. 性能检查

- [ ] 图片上传功能正常
- [ ] 标注创建和审核流程正常
- [ ] 训练发起和日志流正常
- [ ] 模型推理正常
- [ ] E2E 测试通过
