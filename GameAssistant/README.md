# GameAssistant Platform

游戏辅助工具全栈平台，支持图片管理、目标检测标注、模板匹配、YOLO 模型训练和推理测试。

## 架构概览

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Nginx      │────▶│   Backend   │
│   Vue 3      │     │  (Reverse    │     │  FastAPI    │
│   Pinia      │◀────│   Proxy)     │◀────│  Python     │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │   MySQL 8    │
                                          └──────────────┘
```

## 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 20+ (本地开发)

### 开发环境

```bash
# 1. 复制环境变量
cd GameAssistant/web
cp .env.example .env
cp frontend/.env.example frontend/.env

# 2. 使用 Docker Compose 启动所有服务
docker compose up -d

# 3. 访问前端
open http://localhost:3000
```

默认账号：`admin` / `admin123`

### 本地开发

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### 生产环境部署

```bash
# 1. 配置 SSL 证书
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/server.key -out certs/server.crt \
  -subj "/CN=your-domain.com"

# 2. 编辑环境变量
cp .env.example .env.prod
# 编辑 .env.prod 填入 JWT_SECRET_KEY 和数据库密码

# 3. 启动
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## 项目结构

```
GameAssistant/
├── docs/                    # 开发文档和循环报告
├── web/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/v1/     # API 路由
│   │   │   ├── crud/       # 数据库操作
│   │   │   ├── models/     # SQLAlchemy 模型
│   │   │   ├── schemas/    # Pydantic schema
│   │   │   ├── config.py   # 配置
│   │   │   ├── database.py # 数据库连接
│   │   │   └── main.py     # FastAPI 应用入口
│   │   ├── migrations/sql/  # 数据库迁移 SQL
│   │   ├── Dockerfile.backend
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── api/        # API 调用
│   │   │   ├── stores/     # Pinia 状态管理
│   │   │   ├── views/      # 页面组件
│   │   │   ├── layouts/    # 布局组件
│   │   │   ├── router/     # 路由配置
│   │   │   └── styles/     # 全局样式
│   │   ├── Dockerfile.frontend
│   │   └── package.json
│   ├── docker-compose.yml        # 开发环境
│   ├── docker-compose.prod.yml   # 生产环境
│   ├── nginx.conf               # 开发 Nginx 配置
│   ├── nginx.https.conf         # 生产 HTTPS 配置
│   └── .env.example
```

## 功能模块

| 模块 | 路径 | 功能 |
|---|---|---|
| 图片管理 | `/images` | 上传、浏览、筛选、删除图片 |
| 标注管理 | `/annotations` | 标注工具、审核流程、导出 |
| 模板管理 | `/templates` | 上传模板、大图预览、匹配测试 |
| 数据集管理 | `/datasets` | 创建数据集、版本管理、YOLO 导出 |
| 模型管理 | `/models` | 上传模型、评估曲线、下载 |
| 训练管理 | `/training` | 发起训练、实时曲线、日志下载 |
| 推理测试 | `/inference` | 图片/视频推理、推理历史 |

## API 文档

启动后端后访问: http://localhost:8000/docs

## 环境变量说明

| 变量 | 说明 | 默认值 |
|---|---|---|
| `JWT_SECRET_KEY` | JWT 签名密钥（**必须修改**） | - |
| `MYSQL_PASSWORD` | MySQL 密码（**必须修改**） | - |
| `MYSQL_DATABASE` | 数据库名 | gameassistant |
| `CORS_ORIGINS` | 允许的跨域来源 | localhost:3000 |
| `BACKEND_PORT` | 后端端口 | 8000 |
| `FRONTEND_PORT` | 前端端口 | 3000 |
| `DEBUG` | 调试模式 | false |

## 技术栈

**前端**: Vue 3, TypeScript, Pinia, Ant Design Vue 4, vue-echarts, Vite
**后端**: Python 3.10, FastAPI, SQLAlchemy (async), MySQL 8, Uvicorn
**部署**: Docker, Docker Compose, Nginx

## License

MIT
