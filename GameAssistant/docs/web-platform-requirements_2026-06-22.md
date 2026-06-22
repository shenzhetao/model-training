# 模型训练管理平台需求文档

> **项目名称**：GameAssistant Model Training Platform
> **生成时间**：2026-06-22（UTC+8）
> **目标用户**：个人开发者 / 游戏自动化玩家
> **GitHub 参考蓝本**：VLM-AutoYOLO（https://github.com/Somnusochi/VLM-AutoYOLO）
> **开发方向**：基于 VLM-AutoYOLO 架构，改用 Vue3 重构前端，增加游戏自动化专用模块（模板管理 + ADB 推理）

---

## 一、背景与目标

### 1.1 现状

GameAssistant 项目当前已实现以下检测能力：

| 模块 | 技术 | 用途 |
|---|---|---|
| 模板匹配 | OpenCV `matchTemplate` | 固定位置 UI 元素（攻击键、技能槽、血条、对话箭头） |
| YOLO 检测 | Ultralytics YOLOv8 | 动态位置元素（NPC 头顶 `?`/`!` 标记） |
| ElementDetector | 统一编排层 | 同时调用模板匹配 + YOLO，对外暴露统一接口 |

数据管线现状：

```
adb截图 → 手动采集 → LabelImg标注 → 手动划分 → 命令行训练 → 手动复制best.pt
```

### 1.2 目标

构建一个 **本地 Web 管理平台**，统一管理从数据采集到模型部署的完整闭环，让整个流程无需打开终端命令行。

### 1.3 核心差异点（vs VLM-AutoYOLO）

VLM-AutoYOLO 是通用 CV 平台，本平台在其基础上增加 **游戏自动化专用模块**：

- **模板管理**：`templates/` 目录的 Web 上传 / 预览 / 删除 / ROI 编辑
- **ADB 截图推理**：直接在平台上对真机截图跑 `ElementDetector`，无需切换到 IDE
- **混合检测对比**：模板匹配 vs YOLO vs 混合模式的实时对比
- **游戏录制抽帧**：从 OBS/其他工具录制的游戏视频中抽帧导入

---

## 二、功能需求

### 2.1 模块总览

```
┌─────────────────────────────────────────────────────────────┐
│                    Web 管理平台                              │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ 图片管理  │  │  标注    │  │ 模板管理  │  │ 数据集   │  │
│  │ /导入    │  │ /审核   │  │ /推理    │  │ /版本    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       └──────────────┼─────────────┼──────────────┘        │
│                      ▼                                    │
│              ┌────────────────┐                           │
│              │  模型管理       │                           │
│              │  /训练 /评估   │                           │
│              └────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 模块一：图片管理（Image Manager）

**功能描述**：管理所有原始图片（采集来的截图 + 视频抽帧图）

| 功能 | 描述 | 优先级 |
|---|---|---|
| 图片上传 | 单张上传 / ZIP 批量上传（最大 2GB）/ 文件夹拖拽 | P0 |
| 视频抽帧 | 上传 MP4/AVI/MKV → 配置抽帧策略（每 N 帧 / 场景变化 / 固定数量）→ 批量导入 | P0 |
| ADB 实时截图 | 点击按钮直接通过 adb 从真机截图，显示在平台上 | P0 |
| 缩略图预览 | 网格视图 + 灯箱大图预览，支持键盘左右翻页 | P0 |
| 图片删除 | 单张 / 批量选择删除 | P0 |
| 去重检测 | 上传时自动计算 MD5 / pHash，提示重复图片 | P1 |
| 图片元信息 | 显示尺寸、文件大小、上传时间、来源（ADB/视频/手动上传） | P1 |

---

### 2.3 模块二：标注管理（Annotation Manager）

**功能描述**：图片的标注管理

| 功能 | 描述 | 优先级 |
|---|---|---|
| Bounding Box 绘制 | 画矩形框、拖拽调整位置/大小、键盘快捷键切换类别 | P0 |
| 类别管理 | 添加/编辑/删除/重排类别，设置颜色 | P0 |
| 标注进度仪表盘 | 总图片数 / 已标注数 / 每类别标注数，进度条 | P0 |
| YOLO 格式导出 | 一键导出 `images/train` + `labels/train`（含 dataset.yaml） | P0 |
| 标注审核 | 标注完成后提交审核 → 管理员通过/打回，打回可写原因 | P1 |
| 自动标注（手动模式） | 用户先手动标注少量图 → 训练小模型 → 用该模型预标注剩余图 → 人工修正 | P1 |
| 自动标注（AI 模式） | 用 GroundingDINO / YOLO-World 零样本检测，输入文本提示词自动画框 | P1 |
| 标注历史 | Undo / Redo（基于 canvas editor） | P1 |
| 导出其他格式 | COCO JSON / Pascal VOC XML / CreateML JSON | P2 |

---

### 2.4 模块三：模板管理（Template Manager）【游戏自动化专用】

**功能描述**：管理 `templates/` 目录下的模板图片，与游戏自动化 PC 端保持同步

| 功能 | 描述 | 优先级 |
|---|---|---|
| 模板上传 | 上传模板图片，按类别（btn_attack / btn_skill / hp_bar_player / dialog_next）组织 | P0 |
| 模板预览 | 网格展示每个类别下的所有模板图，鼠标悬停放大 | P0 |
| 模板删除 | 单张 / 批量删除 | P0 |
| ROI 编辑 | 为每个模板手动指定搜索 ROI（左上/右下坐标），Web 界面可视化拖拽 | P0 |
| 模板匹配测试 | 上传一张游戏截图 → 选择一个模板类别 → 实时显示匹配位置 | P0 |
| 模板状态管理 | 标记模板是否激活（Active/Inactive），只加载激活的模板 | P1 |
| 与 PC 端同步 | 模板变更后生成 `templates/` 目录压缩包，供下载到 PC 端使用 | P0 |

---

### 2.5 模块四：数据集管理（Dataset Manager）

**功能描述**：数据集版本管理 + 训练前准备

| 功能 | 描述 | 优先级 |
|---|---|---|
| 数据集版本创建 | 创建命名版本（v1 / v2 / xxx），快照当前标注状态 | P0 |
| 数据集版本列表 | 显示每个版本的图片数、标注数、创建时间 | P0 |
| 版本克隆 | 基于已有版本克隆出新版（用于增量标注） | P1 |
| train/val 划分 | 滑块配置比例（默认 90/10）+ 随机种子 + 实时预览样本数 | P0 |
| 划分结果可视化 | 展示划分后的 train/val 分布，确认是否合理 | P1 |
| 类别分布统计 | 柱状图：每类别标注数量，漏标检测（某类太少提示） | P0 |
| 标注框尺寸统计 | 直方图：bbox 宽/高分布，标记异常大/小框 | P1 |
| 数据增强 | 水平翻转 / 旋转 / 亮度 / 对比度 变换，实时预览效果 | P1 |
| 数据集导出 | 打包下载 `images/` + `labels/` + `dataset.yaml` | P0 |

---

### 2.6 模块五：模型管理（Model Manager）

**功能描述**：管理训练出来的所有模型版本

| 功能 | 描述 | 优先级 |
|---|---|---|
| 模型上传 | 上传 .pt / .onnx 文件，显示文件大小 | P0 |
| 模型元信息 | 自动读取：类别列表、训练日期、mAP50、epochs、batch size、训练数据集版本 | P0 |
| 手动补充元信息 | 手动填写模型描述、标签、备注 | P1 |
| 模型对比 | 选择 2 个模型，上传同一张图，对比检测结果（BBox 可视化叠加） | P1 |
| ONNX 导出 | 对 .pt 模型一键导出 ONNX，自动下载 | P0 |
| 模型下载 | 下载 best.pt 或导出文件 | P0 |
| 模型删除 | 删除旧模型（保留最新 1 个不可删） | P1 |

---

### 2.7 模块六：训练管理（Training Manager）

**功能描述**：触发和管理 YOLO 训练任务

| 功能 | 描述 | 优先级 |
|---|---|---|
| 训练任务创建 | 选择：数据集版本 + 模型架构（YOLOv8n/s/m/l/x）+ 参数配置 | P0 |
| 训练参数配置 | epochs / batch / imgsz / lr0 / lrf / weight decay / patience | P0 |
| 增强参数 | mosaic / mixup / hsv 强度滑块 | P1 |
| 开始训练 | 后台启动训练脚本（子进程），不阻塞 Web 请求 | P0 |
| 实时日志流 | SSE 推送每 epoch 的 loss / mAP50 / mAP50-95，实时折线图 | P0 |
| 训练进度条 | 百分比进度 + ETA 剩余时间 | P0 |
| 训练历史 | 每次训练的记录：开始时间/结束时间/参数/结果/关联数据集版本 | P1 |
| 训练中断 | 手动停止（kill 子进程） | P0 |
| 训练恢复 | 从最后一个 epoch checkpoint 恢复训练（`resume=True`） | P2 |
| GPU 监控 | 训练期间显示 GPU 利用率 / 显存占用（`nvidia-smi`） | P1 |

---

### 2.8 模块七：推理测试（Inference Playground）【游戏自动化专用】

**功能描述**：在平台上直接测试训练好的模型和模板匹配，无需切换到 PC 端脚本

| 功能 | 描述 | 优先级 |
|---|---|---|
| ADB 实时截图推理 | 点击按钮 → adb 截图 → ElementDetector 全量检测 → Web 可视化结果 | P0 |
| 图片上传推理 | 上传截图 → 跑检测 → 结果叠加 BBox | P0 |
| 模板匹配单独测试 | 选择模板类别 → 单独运行 TemplateMatcher → 显示匹配位置 | P0 |
| YOLO 单独测试 | 选择模型 → 单独运行 YOLO 检测 → 显示结果 | P0 |
| 混合模式对比 | 同时开启/关闭模板+YOLO，3种模式对比结果 | P0 |
| 置信度阈值调整 | 滑块调整阈值 → 实时刷新结果 | P0 |
| 批量推理 | 上传图片 ZIP → 批量跑检测 → 下载带标注的结果包 | P1 |
| 推理性能统计 | 记录每张图的推理时间（截图 / 模板 / YOLO / 总计） | P1 |

---

## 三、技术架构

### 3.1 技术栈

| 层级 | 技术 | 说明 |
|---|---|---|
| **前端** | Vue 3.4+ (Composition API) + TypeScript + Vite | 用户要求 |
| **UI 组件库** | Ant Design Vue 4.x（方案 A：纯使用，通过 ConfigProvider 主题定制） | 方案 A：纯 Ant Design Vue，不引入 Tailwind CSS |
| **状态管理** | Pinia（Vue3 官方推荐）+ Axios | |
| **后端** | FastAPI + Python 3.10+ | |
| **数据库** | MySQL 8.0+（InnoDB 引擎） | 用户要求 |
| **缓存/任务队列** | Redis（备选，第一阶段可省略） | SSE 状态存储 / Celery 消息队列 |
| **实时通信** | Server-Sent Events（SSE） | 训练日志推送 |
| **文件存储** | 本地文件系统 + 目录结构 | |
| **ADB Bridge** | subprocess 调用 adb | |
| **数据库迁移** | Flyway | SQL 脚本管理 |

### 3.2 项目目录结构

```
GameAssistant/
├── web/                                 ← 新建，Web 平台代码存放目录
│   ├── frontend/                        ← Vue3 前端
│   │   ├── src/
│   │   │   ├── assets/                  ← 静态资源（图片、字体）
│   │   │   ├── types/                   ← TypeScript 共享类型定义（API 响应类型、领域模型类型）
│   │   │   ├── components/              ← 公共组件
│   │   │   │   ├── ImageUploader.vue   ← 图片上传组件
│   │   │   │   ├── AnnotationCanvas.vue ← 标注画布（最复杂组件）
│   │   │   │   │   └── tools/         ← 标注工具子组件（DrawTool、SelectTool、DeleteTool 等）
│   │   │   │   └── BBoxOverlay.vue     ← BBox 叠加层
│   │   │   ├── composables/             ← 跨组件复用逻辑
│   │   │   │   ├── useSSE.ts           ← SSE 连接管理（自动重连、心跳检测）
│   │   │   │   ├── useAnnotationCanvas.ts ← Canvas 操作（缩放/平移/坐标转换）
│   │   │   │   └── useUpload.ts        ← 分片上传逻辑
│   │   │   ├── views/
│   │   │   │   ├── ImageManager.vue
│   │   │   │   ├── Annotation.vue
│   │   │   │   ├── TemplateManager.vue
│   │   │   │   ├── DatasetManager.vue
│   │   │   │   ├── ModelManager.vue
│   │   │   │   ├── TrainingManager.vue
│   │   │   │   └── InferencePlayground.vue
│   │   │   ├── stores/                  ← Pinia 状态管理
│   │   │   │   ├── images.ts
│   │   │   │   ├── annotations.ts
│   │   │   │   ├── templates.ts
│   │   │   │   ├── datasets.ts
│   │   │   │   ├── models.ts
│   │   │   │   └── training.ts
│   │   │   ├── api/                    ← Axios 请求封装（含请求/响应拦截器）
│   │   │   │   ├── images.ts
│   │   │   │   ├── annotations.ts
│   │   │   │   ├── templates.ts
│   │   │   │   ├── datasets.ts
│   │   │   │   ├── models.ts
│   │   │   │   ├── training.ts
│   │   │   │   └── inference.ts
│   │   │   ├── router/                ← Vue Router（含路由守卫）
│   │   │   ├── App.vue
│   │   │   └── main.ts
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   └── package.json
│   │
│   ├── backend/                         ← FastAPI 后端
│   │   ├── app/
│   │   │   ├── main.py                 ← FastAPI 入口（挂载 /api/v1 路由）
│   │   │   ├── config.py               ← 配置管理（Pydantic Settings，支持 .env）
│   │   │   ├── database.py            ← 数据库连接（SQLAlchemy 2.0 + aiomysql）
│   │   │   ├── api/
│   │   │   │   └── v1/                ← API 版本前缀（/api/v1/）
│   │   │   │       ├── __init__.py
│   │   │   │       ├── images.py       ← 图片管理
│   │   │   │       ├── annotations.py  ← 标注管理
│   │   │   │       ├── templates.py    ← 模板管理
│   │   │   │       ├── datasets.py     ← 数据集管理
│   │   │   │       ├── models.py       ← 模型管理
│   │   │   │       ├── training.py     ← 训练管理
│   │   │   │       ├── inference.py    ← 推理测试
│   │   │   │       └── video.py       ← 视频抽帧
│   │   │   ├── schemas/               ← Pydantic 请求/响应模型
│   │   │   ├── crud/                  ← 数据库增删改查（每个表对应一个文件）
│   │   │   ├── ml/                    ← ML 核心模块（直接复用 GameAssistant 代码）
│   │   │   │   ├── element_detector.py
│   │   │   │   ├── template_matcher.py
│   │   │   │   ├── device_profile.py
│   │   │   │   ├── screenshot_collector.py
│   │   │   │   └── training.py
│   │   │   ├── wrappers/              ← ML 包装层（解耦 ML 核心与 API，便于测试和替换）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── detector_wrapper.py ← ElementDetector 包装：统一初始化/推理/销毁接口
│   │   │   │   ├── template_wrapper.py  ← TemplateMatcher 包装：统一模板加载/搜索/卸载接口
│   │   │   │   ├── trainer_wrapper.py  ← Training 包装：subprocess 启动/监控/停止
│   │   │   │   └── adb_wrapper.py     ← ADB 包装：连接检测/截图/设备信息
│   │   │   └── utils/
│   │   │       ├── file_utils.py
│   │   │       ├── hash_utils.py
│   │   │       ├── video_utils.py
│   │   │       └── adb_utils.py
│   │   ├── requirements.txt
│   │   └── migrations/                 ← Flyway SQL 迁移脚本
│   │
│   ├── docker-compose.yml              ← 一键启动（MySQL 8.0 + Redis + Backend + Frontend）
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend
│   ├── .env.example
│   └── README.md
│
└── GameAssistant/                     ← 原 PC 端项目（保持独立）
    ├── ml/
    ├── pc/
    ├── templates/
    └── scripts/
```

### 3.3 数据库设计（MySQL 8.0+，完整版）

> 基于 MySQL 8.0+（InnoDB 引擎），使用 Flyway 进行数据库迁移管理。

#### 3.3.1 ER 关系总览

```
users ──(1:N)──▶ annotation_projects
      │                    │
      │                    └──(1:N)──▶ annotation_project_images ──(N:1)──▶ images
      │
      └──(1:N)──▶ annotations

datasets ──(1:N)──▶ dataset_versions ──(1:N)──▶ dataset_version_images ──(N:1)──▶ images
      │
      └──(1:N)──▶ training_jobs ──(1:N)──▶ models

device_profiles ──(1:N)──▶ templates
      │
      └──(1:N)──▶ inference_logs

source_videos ──(1:N)──▶ video_extraction_tasks
      │
      └──(1:N)──▶ images（抽帧来源）
```

#### 3.3.2 MySQL 与 PostgreSQL 兼容性说明

| 特性 | MySQL 8.0+ | PostgreSQL 15+ |
|---|---|---|
| UUID 主键 | `CHAR(36)`（应用层生成 UUID） | `UUID DEFAULT uuid_generate_v4()` |
| 数组类型 | `JSON`（MySQL 无原生数组） | `UUID[]` |
| 部分索引 | 普通 `UNIQUE INDEX`（应用层过滤） | `CREATE INDEX ... WHERE ...` |
| JSON 类型 | `JSON` | `JSONB`（二进制，推荐） |
| 时区时间戳 | `DATETIME` | `TIMESTAMP WITH TIME ZONE` |
| 迁移工具 | Flyway | Alembic 或 Flyway |

#### 3.3.3 表结构详细设计

---

##### 表 1：`users`（用户表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 用户唯一标识（UUID，应用层生成） |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 用户名 |
| password_hash | VARCHAR(256) | NOT NULL | 密码哈希（bcrypt） |
| role | VARCHAR(32) | NOT NULL, DEFAULT 'annotator' | 角色：admin/annotator/reviewer |
| email | VARCHAR(128) | UNIQUE | 邮箱 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| is_active | TINYINT(1) | NOT NULL, DEFAULT 1 | 是否启用（0/1） |

```sql
CREATE TABLE users (
    id CHAR(36) PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'annotator',
    email VARCHAR(128) UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    INDEX idx_users_username (username),
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 2：`images`（图片元信息表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 图片唯一标识 |
| filename | VARCHAR(256) | NOT NULL | 存储文件名（UUID 重命名） |
| original_filename | VARCHAR(256) | NOT NULL | 原始上传文件名 |
| file_path | VARCHAR(512) | NOT NULL, UNIQUE | 文件存储路径（相对路径） |
| file_size | BIGINT | NOT NULL | 文件大小（字节） |
| width | INT | NOT NULL | 图片宽度（像素） |
| height | INT | NOT NULL | 图片高度（像素） |
| md5_hash | VARCHAR(32) | NOT NULL | MD5 去重 |
| phash | VARCHAR(64) | NULL | 感知哈希（pHash） |
| source | VARCHAR(16) | NOT NULL, DEFAULT 'upload' | 图片来源：upload/adb/video |
| source_video_id | CHAR(36) | NULL, FK | 视频抽帧来源视频 ID |
| source_video_timestamp | FLOAT | NULL | 抽帧时间戳（秒） |
| uploaded_by | CHAR(36) | NULL, FK → users.id | 上传用户 |
| uploaded_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 上传时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| is_deleted | TINYINT(1) | NOT NULL, DEFAULT 0 | 软删除（0/1） |

```sql
CREATE TABLE images (
    id CHAR(36) PRIMARY KEY,
    filename VARCHAR(256) NOT NULL,
    original_filename VARCHAR(256) NOT NULL,
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    md5_hash VARCHAR(32) NOT NULL,
    phash VARCHAR(64) NULL,
    source VARCHAR(16) NOT NULL DEFAULT 'upload',
    source_video_id CHAR(36) NULL,
    source_video_timestamp FLOAT NULL,
    uploaded_by CHAR(36) NULL,
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_images_md5 (md5_hash),
    INDEX idx_images_source (source),
    INDEX idx_images_uploaded_at (uploaded_at),
    INDEX idx_images_source_video (source_video_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 3：`source_videos`（源视频表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 视频唯一标识 |
| filename | VARCHAR(256) | NOT NULL | 存储文件名 |
| original_filename | VARCHAR(256) | NOT NULL | 原始文件名 |
| file_path | VARCHAR(512) | NOT NULL, UNIQUE | 文件存储路径 |
| file_size | BIGINT | NOT NULL | 文件大小（字节） |
| duration | FLOAT | NOT NULL | 视频时长（秒） |
| width | INT | NOT NULL | 视频宽度 |
| height | INT | NOT NULL | 视频高度 |
| fps | FLOAT | NOT NULL | 帧率 |
| uploaded_by | CHAR(36) | NULL, FK → users.id | 上传用户 |
| uploaded_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 上传时间 |
| is_deleted | TINYINT(1) | NOT NULL, DEFAULT 0 | 软删除 |

```sql
CREATE TABLE source_videos (
    id CHAR(36) PRIMARY KEY,
    filename VARCHAR(256) NOT NULL,
    original_filename VARCHAR(256) NOT NULL,
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    duration FLOAT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    fps FLOAT NOT NULL,
    uploaded_by CHAR(36) NULL,
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_source_videos_uploaded_at (uploaded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 4：`video_extraction_tasks`（视频抽帧任务表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 任务唯一标识 |
| video_id | CHAR(36) | FK → source_videos.id | 源视频 |
| strategy | VARCHAR(32) | NOT NULL | 抽帧策略：interval/count/scene_change |
| interval_seconds | FLOAT | NULL | 每隔 N 秒抽一帧 |
| frame_count | INT | NULL | 总共抽 N 帧 |
| scene_threshold | FLOAT | NULL | 场景变化阈值 |
| status | VARCHAR(32) | NOT NULL, DEFAULT 'pending' | 状态：pending/running/completed/failed |
| total_frames | INT | NULL | 计划抽取帧数 |
| extracted_frames | INT | NULL, DEFAULT 0 | 已抽取帧数 |
| started_at | DATETIME | NULL | 开始时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| created_by | CHAR(36) | NULL, FK → users.id | 创建用户 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| error_message | TEXT | NULL | 失败原因 |

```sql
CREATE TABLE video_extraction_tasks (
    id CHAR(36) PRIMARY KEY,
    video_id CHAR(36) NOT NULL,
    strategy VARCHAR(32) NOT NULL,
    interval_seconds FLOAT NULL,
    frame_count INT NULL,
    scene_threshold FLOAT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    total_frames INT NULL,
    extracted_frames INT NULL DEFAULT 0,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT NULL,
    INDEX idx_video_extraction_video_id (video_id),
    INDEX idx_video_extraction_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 5：`classes`（类别表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 类别唯一标识 |
| name | VARCHAR(128) | NOT NULL | 类别名称（英文，用于 YOLO label） |
| display_name | VARCHAR(128) | NOT NULL | 显示名称（可中文） |
| description | TEXT | NULL | 类别描述 |
| color | VARCHAR(7) | NOT NULL, DEFAULT '#3B82F6' | 标注颜色（HEX） |
| short_key | VARCHAR(8) | NULL | 快捷键（如 'q', 'w'） |
| sort_order | INT | NOT NULL, DEFAULT 0 | 显示顺序 |
| yolo_class_id | INT | NOT NULL, UNIQUE | YOLO 格式中的类别 ID（0-based） |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

```sql
CREATE TABLE classes (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    short_key VARCHAR(8) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    yolo_class_id INT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_classes_yolo_class_id (yolo_class_id),
    INDEX idx_classes_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 6：`annotations`（标注记录表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 标注唯一标识 |
| image_id | CHAR(36) | FK → images.id, NOT NULL | 图片 ID |
| class_id | CHAR(36) | FK → classes.id, NOT NULL | 类别 ID |
| bbox_x | FLOAT | NOT NULL | BBox 左上角 X（像素） |
| bbox_y | FLOAT | NOT NULL | BBox 左上角 Y（像素） |
| bbox_width | FLOAT | NOT NULL | BBox 宽度（像素） |
| bbox_height | FLOAT | NOT NULL | BBox 高度（像素） |
| conf | FLOAT | NULL | 置信度（自动标注时有值） |
| is_auto_annotated | TINYINT(1) | NOT NULL, DEFAULT 0 | 是否为自动标注 |
| annotated_by | CHAR(36) | NULL, FK → users.id | 标注用户 |
| annotated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 标注时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

```sql
CREATE TABLE annotations (
    id CHAR(36) PRIMARY KEY,
    image_id CHAR(36) NOT NULL,
    class_id CHAR(36) NOT NULL,
    bbox_x FLOAT NOT NULL,
    bbox_y FLOAT NOT NULL,
    bbox_width FLOAT NOT NULL,
    bbox_height FLOAT NOT NULL,
    conf FLOAT NULL,
    is_auto_annotated TINYINT(1) NOT NULL DEFAULT 0,
    annotated_by CHAR(36) NULL,
    annotated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_annotations_image_id (image_id),
    INDEX idx_annotations_class_id (class_id),
    INDEX idx_annotations_image_class (image_id, class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 7：`annotation_projects`（标注项目表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 项目唯一标识 |
| name | VARCHAR(128) | NOT NULL | 项目名称 |
| description | TEXT | NULL | 项目描述 |
| status | VARCHAR(32) | NOT NULL, DEFAULT 'draft' | 状态：draft/annotating/reviewing/completed |
| class_ids | JSON | NOT NULL | 该项目允许的类别 ID 列表 |
| total_images | INT | NOT NULL, DEFAULT 0 | 总图片数 |
| annotated_images | INT | NOT NULL, DEFAULT 0 | 已标注图片数 |
| reviewed_images | INT | NOT NULL, DEFAULT 0 | 已审核图片数 |
| assigned_to | CHAR(36) | NULL, FK → users.id | 指派给标注员 |
| reviewed_by | CHAR(36) | NULL, FK → users.id | 指派给审核员 |
| created_by | CHAR(36) | NULL, FK → users.id | 创建人 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| completed_at | DATETIME | NULL | 完成时间 |

```sql
CREATE TABLE annotation_projects (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    class_ids JSON NOT NULL,
    total_images INT NOT NULL DEFAULT 0,
    annotated_images INT NOT NULL DEFAULT 0,
    reviewed_images INT NOT NULL DEFAULT 0,
    assigned_to CHAR(36) NULL,
    reviewed_by CHAR(36) NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    INDEX idx_annotation_projects_status (status),
    INDEX idx_annotation_projects_assigned_to (assigned_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 8：`annotation_project_images`（标注项目-图片关联表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 唯一标识 |
| annotation_project_id | CHAR(36) | FK → annotation_projects.id | 标注项目 ID |
| image_id | CHAR(36) | FK → images.id | 图片 ID |
| assigned_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 加入时间 |

```sql
CREATE TABLE annotation_project_images (
    id CHAR(36) PRIMARY KEY,
    annotation_project_id CHAR(36) NOT NULL,
    image_id CHAR(36) NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_annotation_project_image (annotation_project_id, image_id),
    INDEX idx_annotation_project_images_project_id (annotation_project_id),
    INDEX idx_annotation_project_images_image_id (image_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 9：`annotation_reviews`（标注审核记录表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 审核唯一标识 |
| annotation_project_id | CHAR(36) | FK → annotation_projects.id | 标注项目 ID |
| image_id | CHAR(36) | FK → images.id | 被审核的图片 ID |
| review_status | VARCHAR(32) | NOT NULL | 结果：approved/rejected/revision_requested |
| reviewer_id | CHAR(36) | NULL, FK → users.id | 审核人 |
| rejection_reason | TEXT | NULL | 打回原因 |
| reviewed_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 审核时间 |

```sql
CREATE TABLE annotation_reviews (
    id CHAR(36) PRIMARY KEY,
    annotation_project_id CHAR(36) NOT NULL,
    image_id CHAR(36) NOT NULL,
    review_status VARCHAR(32) NOT NULL,
    reviewer_id CHAR(36) NULL,
    rejection_reason TEXT NULL,
    reviewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_annotation_review (annotation_project_id, image_id),
    INDEX idx_annotation_reviews_project (annotation_project_id),
    INDEX idx_annotation_reviews_image (image_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 10：`datasets`（数据集表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 数据集唯一标识 |
| name | VARCHAR(128) | NOT NULL | 数据集名称 |
| description | TEXT | NULL | 数据集描述 |
| created_by | CHAR(36) | NULL, FK → users.id | 创建人 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| is_deleted | TINYINT(1) | NOT NULL, DEFAULT 0 | 软删除 |

```sql
CREATE TABLE datasets (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_datasets_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 11：`dataset_versions`（数据集版本表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 版本唯一标识 |
| dataset_id | CHAR(36) | FK → datasets.id, NOT NULL | 所属数据集 |
| version_name | VARCHAR(128) | NOT NULL | 版本名称（如 "v1.0.0"） |
| version_number | INT | NOT NULL | 版本序号 |
| train_ratio | FLOAT | NOT NULL, DEFAULT 0.9 | 训练集比例（受 CHECK 约束：三者之和 ≤ 1.0） |
| val_ratio | FLOAT | NOT NULL, DEFAULT 0.1 | 验证集比例 |
| test_ratio | FLOAT | NOT NULL, DEFAULT 0.0 | 测试集比例 |
| random_seed | INT | NOT NULL, DEFAULT 42 | 随机种子 |
| image_count | INT | NOT NULL, DEFAULT 0 | 总图片数 |
| annotated_count | INT | NOT NULL, DEFAULT 0 | 已标注图片数 |
| class_ids | JSON | NOT NULL | 该版本包含的类别 ID 列表 |
| yolo_dataset_path | VARCHAR(512) | NULL | YOLO 格式数据集根目录路径 |
| dataset_yaml_content | TEXT | NULL | dataset.yaml 文件内容 |
| status | VARCHAR(32) | NOT NULL, DEFAULT 'preparing' | 状态：preparing/ready/training/archived |
| created_by | CHAR(36) | NULL, FK → users.id | 创建人 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

```sql
CREATE TABLE dataset_versions (
    id CHAR(36) PRIMARY KEY,
    dataset_id CHAR(36) NOT NULL,
    version_name VARCHAR(128) NOT NULL,
    version_number INT NOT NULL,
    train_ratio FLOAT NOT NULL DEFAULT 0.9,
    val_ratio FLOAT NOT NULL DEFAULT 0.1,
    test_ratio FLOAT NOT NULL DEFAULT 0.0,
    random_seed INT NOT NULL DEFAULT 42,
    image_count INT NOT NULL DEFAULT 0,
    annotated_count INT NOT NULL DEFAULT 0,
    class_ids JSON NOT NULL,
    yolo_dataset_path VARCHAR(512) NULL,
    dataset_yaml_content TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'preparing',
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dataset_version_name (dataset_id, version_name),
    UNIQUE KEY uk_dataset_version_number (dataset_id, version_number),
    INDEX idx_dataset_versions_dataset_id (dataset_id),
    INDEX idx_dataset_versions_status (status),
    INDEX idx_dataset_versions_created_at (created_at),
    CHECK (train_ratio + val_ratio + test_ratio <= 1.0 AND train_ratio >= 0 AND val_ratio >= 0 AND test_ratio >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 12：`dataset_version_images`（数据集版本-图片关联表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 唯一标识 |
| dataset_version_id | CHAR(36) | FK → dataset_versions.id | 数据集版本 ID |
| image_id | CHAR(36) | FK → images.id | 图片 ID |
| split | VARCHAR(16) | NOT NULL | 数据划分：train/val/test |
| added_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 加入时间 |

```sql
CREATE TABLE dataset_version_images (
    id CHAR(36) PRIMARY KEY,
    dataset_version_id CHAR(36) NOT NULL,
    image_id CHAR(36) NOT NULL,
    split VARCHAR(16) NOT NULL,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dataset_version_image (dataset_version_id, image_id),
    INDEX idx_dataset_version_images_version_id (dataset_version_id),
    INDEX idx_dataset_version_images_split (split),
    INDEX idx_dataset_version_images_image_id (image_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 13：`models`（模型表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 模型唯一标识 |
| name | VARCHAR(128) | NOT NULL | 模型名称 |
| description | TEXT | NULL | 模型描述 |
| architecture | VARCHAR(32) | NOT NULL | 模型架构（如 yolov8n, yolov8s） |
| task_type | VARCHAR(32) | NOT NULL, DEFAULT 'detect' | 任务类型：detect/segment/classify |
| file_path | VARCHAR(512) | NOT NULL, UNIQUE | 模型文件存储路径 |
| file_size | BIGINT | NOT NULL | 文件大小（字节） |
| format | VARCHAR(16) | NOT NULL, DEFAULT 'pt' | 格式：pt/onnx/engine |
| dataset_version_id | CHAR(36) | NULL, FK → dataset_versions.id | 训练所用数据集版本 |
| class_ids | JSON | NOT NULL | 模型包含的类别 ID 列表 |
| yolo_class_names | JSON | NOT NULL | YOLO class.names 字典 |
| epochs | INT | NULL | 训练轮数 |
| batch_size | INT | NULL | batch size |
| img_size | INT | NULL | 输入图片尺寸 |
| map50 | FLOAT | NULL | mAP50 指标 |
| map50_95 | FLOAT | NULL | mAP50-95 指标 |
| train_loss | FLOAT | NULL | 最终训练 loss |
| val_loss | FLOAT | NULL | 最终验证 loss |
| trained_at | DATETIME | NULL | 训练完成时间 |
| training_job_id | CHAR(36) | NULL, FK → training_jobs.id | 关联的训练任务 |
| tags | JSON | NULL | 标签列表 |
| is_active | TINYINT(1) | NOT NULL, DEFAULT 1 | 是否激活 |
| uploaded_by | CHAR(36) | NULL, FK → users.id | 上传人 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| is_deleted | TINYINT(1) | NOT NULL, DEFAULT 0 | 软删除 |

```sql
CREATE TABLE models (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    architecture VARCHAR(32) NOT NULL,
    task_type VARCHAR(32) NOT NULL DEFAULT 'detect',
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    format VARCHAR(16) NOT NULL DEFAULT 'pt',
    dataset_version_id CHAR(36) NULL,
    class_ids JSON NOT NULL,
    yolo_class_names JSON NOT NULL,
    epochs INT NULL,
    batch_size INT NULL,
    img_size INT NULL,
    map50 FLOAT NULL,
    map50_95 FLOAT NULL,
    train_loss FLOAT NULL,
    val_loss FLOAT NULL,
    trained_at DATETIME NULL,
    training_job_id CHAR(36) NULL,
    tags JSON NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    uploaded_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_models_architecture (architecture),
    INDEX idx_models_dataset_version_id (dataset_version_id),
    INDEX idx_models_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 14：`training_jobs`（训练任务表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 任务唯一标识 |
| name | VARCHAR(128) | NOT NULL | 任务名称 |
| dataset_version_id | CHAR(36) | FK → dataset_versions.id | 训练数据集版本 |
| base_model_architecture | VARCHAR(32) | NOT NULL | 基础模型架构（如 yolov8n） |
| status | VARCHAR(32) | NOT NULL, DEFAULT 'pending' | 状态：pending/preparing/running/paused/completed/failed/cancelled |
| epochs | INT | NOT NULL, DEFAULT 50 | 训练轮数 |
| batch_size | INT | NOT NULL, DEFAULT 8 | batch size |
| img_size | INT | NOT NULL, DEFAULT 640 | 输入图片尺寸 |
| lr0 | FLOAT | NOT NULL, DEFAULT 0.01 | 初始学习率 |
| lrf | FLOAT | NOT NULL, DEFAULT 0.01 | 最终学习率因子 |
| weight_decay | FLOAT | NOT NULL, DEFAULT 0.0005 | 权重衰减 |
| momentum | FLOAT | NOT NULL, DEFAULT 0.937 | 动量 |
| patience | INT | NOT NULL, DEFAULT 15 | 早停耐心值 |
| mosaic | FLOAT | NOT NULL, DEFAULT 1.0 | Mosaic 增强比例 |
| mixup | FLOAT | NOT NULL, DEFAULT 0.0 | Mixup 增强比例 |
| hsv_h | FLOAT | NOT NULL, DEFAULT 0.015 | HSV 增强 H 通道 |
| hsv_s | FLOAT | NOT NULL, DEFAULT 0.7 | HSV 增强 S 通道 |
| hsv_v | FLOAT | NOT NULL, DEFAULT 0.4 | HSV 增强 V 通道 |
| flip_lr | FLOAT | NOT NULL, DEFAULT 0.5 | 左右翻转概率 |
| resume_from | CHAR(36) | NULL, FK → training_jobs.id | 从哪个任务恢复 |
| best_model_id | CHAR(36) | NULL, FK → models.id | 训练完成后生成的模型 ID |
| process_id | INT | NULL | 训练子进程 PID |
| log_output | LONGTEXT | NULL | 训练日志（完整输出） |
| log_summary | JSON | NULL | 日志摘要（每个 epoch 的指标） |
| current_epoch | INT | NULL | 当前 epoch |
| gpu_device | VARCHAR(16) | NULL | 使用的 GPU 设备号 |
| started_at | DATETIME | NULL | 开始时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| created_by | CHAR(36) | NULL, FK → users.id | 创建人 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| error_message | TEXT | NULL | 失败原因 |

```sql
CREATE TABLE training_jobs (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    dataset_version_id CHAR(36) NOT NULL,
    base_model_architecture VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    epochs INT NOT NULL DEFAULT 50,
    batch_size INT NOT NULL DEFAULT 8,
    img_size INT NOT NULL DEFAULT 640,
    lr0 FLOAT NOT NULL DEFAULT 0.01,
    lrf FLOAT NOT NULL DEFAULT 0.01,
    weight_decay FLOAT NOT NULL DEFAULT 0.0005,
    momentum FLOAT NOT NULL DEFAULT 0.937,
    patience INT NOT NULL DEFAULT 15,
    mosaic FLOAT NOT NULL DEFAULT 1.0,
    mixup FLOAT NOT NULL DEFAULT 0.0,
    hsv_h FLOAT NOT NULL DEFAULT 0.015,
    hsv_s FLOAT NOT NULL DEFAULT 0.7,
    hsv_v FLOAT NOT NULL DEFAULT 0.4,
    flip_lr FLOAT NOT NULL DEFAULT 0.5,
    resume_from CHAR(36) NULL,
    best_model_id CHAR(36) NULL,
    process_id INT NULL,
    log_output LONGTEXT NULL,
    log_summary JSON NULL,
    current_epoch INT NULL,
    gpu_device VARCHAR(16) NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT NULL,
    INDEX idx_training_jobs_dataset_version_id (dataset_version_id),
    INDEX idx_training_jobs_status (status),
    INDEX idx_training_jobs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 15：`training_logs`（训练 epoch 日志表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 唯一标识 |
| training_job_id | CHAR(36) | FK → training_jobs.id, NOT NULL | 训练任务 ID |
| epoch | INT | NOT NULL | epoch 序号（从 1 开始） |
| train_box_loss | FLOAT | NULL | 训练 bbox loss |
| train_cls_loss | FLOAT | NULL | 训练分类 loss |
| train_dfl_loss | FLOAT | NULL | 训练 DFL loss |
| val_box_loss | FLOAT | NULL | 验证 bbox loss |
| val_cls_loss | FLOAT | NULL | 验证分类 loss |
| val_dfl_loss | FLOAT | NULL | 验证 DFL loss |
| precision | FLOAT | NULL | 精确率 |
| recall | FLOAT | NULL | 召回率 |
| map50 | FLOAT | NULL | mAP50 |
| map50_95 | FLOAT | NULL | mAP50-95 |
| lr | FLOAT | NULL | 当前学习率 |
| gpu_memory_mb | INT | NULL | GPU 显存占用（MB） |
| epoch_duration_sec | INT | NULL | 该 epoch 耗时（秒） |
| logged_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录时间 |

```sql
CREATE TABLE training_logs (
    id CHAR(36) PRIMARY KEY,
    training_job_id CHAR(36) NOT NULL,
    epoch INT NOT NULL,
    train_box_loss FLOAT NULL,
    train_cls_loss FLOAT NULL,
    train_dfl_loss FLOAT NULL,
    val_box_loss FLOAT NULL,
    val_cls_loss FLOAT NULL,
    val_dfl_loss FLOAT NULL,
    precision FLOAT NULL,
    recall FLOAT NULL,
    map50 FLOAT NULL,
    map50_95 FLOAT NULL,
    lr FLOAT NULL,
    gpu_memory_mb INT NULL,
    epoch_duration_sec INT NULL,
    logged_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_training_log_epoch (training_job_id, epoch),
    INDEX idx_training_logs_job_id (training_job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 16：`device_profiles`（设备配置表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 设备唯一标识 |
| name | VARCHAR(64) | NOT NULL | 设备名称 |
| device_id | VARCHAR(128) | NULL | adb device serial（如 3DJ0224910000759） |
| width | INT | NOT NULL | 屏幕宽度（像素） |
| height | INT | NOT NULL | 屏幕高度（像素） |
| dpi | INT | NULL | 屏幕 DPI |
| reference_width | INT | NOT NULL | 参考分辨率宽度（模板录制时的分辨率） |
| reference_height | INT | NOT NULL | 参考分辨率高度 |
| is_active | TINYINT(1) | NOT NULL, DEFAULT 1 | 是否激活 |
| is_default | TINYINT(1) | NOT NULL, DEFAULT 0 | 是否为默认设备 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

```sql
CREATE TABLE device_profiles (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    device_id VARCHAR(128) NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    dpi INT NULL,
    reference_width INT NOT NULL,
    reference_height INT NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device_profiles_device_id (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 17：`templates`（模板表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 模板唯一标识 |
| device_profile_id | CHAR(36) | NULL, FK → device_profiles.id | 所属设备配置 |
| class_name | VARCHAR(64) | NOT NULL | 模板类别（btn_attack / btn_skill 等） |
| name | VARCHAR(128) | NOT NULL | 模板名称 |
| file_path | VARCHAR(512) | NOT NULL, UNIQUE | 模板文件存储路径 |
| file_size | BIGINT | NOT NULL | 文件大小（字节） |
| width | INT | NOT NULL | 模板宽度 |
| height | INT | NOT NULL | 模板高度 |
| roi_x | INT | NULL | 搜索区域 ROI 左上角 X（像素） |
| roi_y | INT | NULL | 搜索区域 ROI 左上角 Y |
| roi_width | INT | NULL | ROI 宽度（NULL=全图搜索） |
| roi_height | INT | NULL | ROI 高度 |
| match_threshold | FLOAT | NOT NULL, DEFAULT 0.8 | 匹配置信度阈值 |
| is_active | TINYINT(1) | NOT NULL, DEFAULT 1 | 是否激活 |
| trained_at | DATETIME | NULL | 采集时间 |
| uploaded_by | CHAR(36) | NULL, FK → users.id | 上传人 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| is_deleted | TINYINT(1) | NOT NULL, DEFAULT 0 | 软删除 |

```sql
CREATE TABLE templates (
    id CHAR(36) PRIMARY KEY,
    device_profile_id CHAR(36) NULL,
    class_name VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    roi_x INT NULL,
    roi_y INT NULL,
    roi_width INT NULL,
    roi_height INT NULL,
    match_threshold FLOAT NOT NULL DEFAULT 0.8,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    trained_at DATETIME NULL,
    uploaded_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_templates_class_name (class_name),
    INDEX idx_templates_device_profile_id (device_profile_id),
    INDEX idx_templates_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 18：`template_classes`（模板类别表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 唯一标识 |
| class_name | VARCHAR(64) | NOT NULL, UNIQUE | 类别名称 |
| display_name | VARCHAR(128) | NOT NULL | 显示名称 |
| description | TEXT | NULL | 描述 |
| default_threshold | FLOAT | NOT NULL, DEFAULT 0.8 | 默认匹配阈值 |
| icon | VARCHAR(64) | NULL | 图标名称 |
| sort_order | INT | NOT NULL, DEFAULT 0 | 显示顺序 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

```sql
CREATE TABLE template_classes (
    id CHAR(36) PRIMARY KEY,
    class_name VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    default_threshold FLOAT NOT NULL DEFAULT 0.8,
    icon VARCHAR(64) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 初始数据
INSERT INTO template_classes (id, class_name, display_name, description, sort_order) VALUES
(UUID(), 'btn_attack', '攻击按钮', '右下角攻击键', 1),
(UUID(), 'btn_skill', '技能按钮', '8个技能槽', 2),
(UUID(), 'hp_bar_player', '角色血条', '角色血量条', 3),
(UUID(), 'dialog_next', '对话箭头', 'NPC对话下一步箭头', 4);
```

---

##### 表 19：`inference_logs`（推理日志表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 唯一标识 |
| image_id | CHAR(36) | NULL, FK → images.id | 推理图片（可选） |
| model_id | CHAR(36) | FK → models.id | 使用的模型 |
| template_ids | JSON | NULL | 使用的模板 ID 列表 |
| detection_mode | VARCHAR(32) | NOT NULL | 检测模式：template_only/yolo_only/hybrid |
| conf_threshold | FLOAT | NOT NULL | 置信度阈值 |
| input_width | INT | NOT NULL | 输入图片宽度 |
| input_height | INT | NOT NULL | 输入图片高度 |
| screenshot_latency_ms | FLOAT | NULL | 截图耗时（ms） |
| template_latency_ms | FLOAT | NULL | 模板匹配耗时（ms） |
| yolo_latency_ms | FLOAT | NULL | YOLO 推理耗时（ms） |
| total_latency_ms | FLOAT | NOT NULL | 总耗时（ms） |
| results | JSON | NOT NULL | 检测结果（完整 JSON） |
| result_count | INT | NOT NULL | 检测结果数量 |
| device_profile_id | CHAR(36) | NULL, FK → device_profiles.id | 使用的设备配置 |
| inference_type | VARCHAR(16) | NOT NULL, DEFAULT 'single' | 推理类型：single/batch |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 推理时间 |

```sql
CREATE TABLE inference_logs (
    id CHAR(36) PRIMARY KEY,
    image_id CHAR(36) NULL,
    model_id CHAR(36) NOT NULL,
    template_ids JSON NULL,
    detection_mode VARCHAR(32) NOT NULL,
    conf_threshold FLOAT NOT NULL,
    input_width INT NOT NULL,
    input_height INT NOT NULL,
    screenshot_latency_ms FLOAT NULL,
    template_latency_ms FLOAT NULL,
    yolo_latency_ms FLOAT NULL,
    total_latency_ms FLOAT NOT NULL,
    results JSON NOT NULL,
    result_count INT NOT NULL,
    device_profile_id CHAR(36) NULL,
    inference_type VARCHAR(16) NOT NULL DEFAULT 'single',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_inference_logs_model_id (model_id),
    INDEX idx_inference_logs_created_at (created_at),
    INDEX idx_inference_logs_detection_mode (detection_mode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 20：`operation_logs`（操作日志表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 唯一标识 |
| user_id | CHAR(36) | NULL, FK → users.id | 操作用户 |
| action | VARCHAR(64) | NOT NULL | 操作类型（如 annotation.create） |
| resource_type | VARCHAR(32) | NOT NULL | 资源类型（如 image/annotation/model） |
| resource_id | CHAR(36) | NULL | 资源 ID |
| details | JSON | NULL | 操作详情（变更前后的 JSON） |
| ip_address | VARCHAR(45) | NULL | IP 地址 |
| user_agent | VARCHAR(256) | NULL | 浏览器 User-Agent |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 操作时间 |

```sql
CREATE TABLE operation_logs (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NULL,
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    resource_id CHAR(36) NULL,
    details JSON NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(256) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operation_logs_user_id (user_id),
    INDEX idx_operation_logs_action (action),
    INDEX idx_operation_logs_resource (resource_type, resource_id),
    INDEX idx_operation_logs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

##### 表 21：`notifications`（通知表）

| 字段名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | CHAR(36) | PK | 唯一标识 |
| user_id | CHAR(36) | FK → users.id | 通知用户 |
| type | VARCHAR(64) | NOT NULL | 通知类型 |
| title | VARCHAR(256) | NOT NULL | 通知标题 |
| message | TEXT | NOT NULL | 通知内容 |
| resource_type | VARCHAR(32) | NULL | 关联资源类型 |
| resource_id | CHAR(36) | NULL | 关联资源 ID |
| is_read | TINYINT(1) | NOT NULL, DEFAULT 0 | 是否已读 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

```sql
CREATE TABLE notifications (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    type VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    message TEXT NOT NULL,
    resource_type VARCHAR(32) NULL,
    resource_id CHAR(36) NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notifications_user_id (user_id),
    INDEX idx_notifications_is_read (is_read),
    INDEX idx_notifications_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

#### 3.3.4 Flyway 迁移文件结构

```
backend/migrations/
└── sql/
    ├── V1__initial_schema.sql          ← 初始表（users, images, source_videos, classes）
    ├── V2__add_annotation_project_images.sql ← 标注项目-图片关联（新增，解决关联缺失问题）
    ├── V3__add_annotations.sql         ← 标注相关（annotations, annotation_projects, reviews）
    ├── V4__add_datasets.sql            ← 数据集（datasets, dataset_versions, dataset_version_images）
    ├── V5__add_training.sql            ← 训练（training_jobs, training_logs）
    ├── V6__add_templates.sql           ← 模板（templates, template_classes）
    └── V7__add_device_profiles.sql     ← 设备+推理（device_profiles, inference_logs, notifications）
```

#### 3.3.5 索引与性能优化

| 优化策略 | 表 | MySQL 实现方式 |
|---|---|---|
| 大表分区 | `inference_logs` | `PARTITION BY RANGE` 按月分区 |
| 大表分区 | `operation_logs` | `PARTITION BY RANGE` 按月分区 |
| 复合唯一索引 | `images.md5_hash` | `UNIQUE INDEX`（应用层确保 is_deleted=FALSE 不重复） |
| 复合唯一索引 | `annotations` | `UNIQUE INDEX(image_id, class_id, bbox_*)`（应用层过滤自动标注） |
| 唯一索引 | `annotation_project_images` | `UNIQUE KEY (annotation_project_id, image_id)`（防止重复添加同一图片） |
| 唯一索引 | `annotation_reviews` | `UNIQUE KEY (annotation_project_id, image_id)`（每张图片只审核一次） |
| JSON 索引 | `inference_logs.results` | `JSON` 字段配合应用层查询 |
| CHECK 约束 | `dataset_versions` | `CHECK (train_ratio + val_ratio + test_ratio <= 1.0)` 数据校验 |

#### 3.3.6 API 版本管理

所有后端 API 路由统一使用版本前缀 `/api/v1/`，便于未来 API 演进和向后兼容。

```
/api/v1/images          GET/POST
/api/v1/images/{id}     GET/PUT/DELETE
/api/v1/annotations      GET/POST
/api/v1/datasets         GET/POST
/api/v1/training        GET/POST
/api/v1/inference        POST
```

前端 Axios 请求统一封装 `baseURL: /api/v1`，配合 `openapi2ts` 或 `orval` 自动生成 TypeScript 类型。

---

## 四、开发阶段规划

### 第一阶段：基础框架搭建（约 1-2 天）

- [ ] 搭建 Vue3 + Vite + Ant Design Vue 项目骨架
- [ ] 搭建 FastAPI 后端骨架 + MySQL 连接
- [ ] 运行 Flyway 迁移脚本，创建所有表
- [ ] 实现用户认证（JWT）
- [ ] 实现图片上传 API（单张 + ZIP）

### 第二阶段：核心功能实现（约 3-4 天）

- [ ] 图片管理模块（上传/预览/删除/去重）
- [ ] 标注管理模块（Bounding Box 画布 + 类别管理）
- [ ] 模板管理模块（上传/预览/ROI编辑）
- [ ] 数据集版本管理（创建/划分/导出）
- [ ] 模型管理模块（上传/元信息读取/ONNX导出）

### 第三阶段：训练与推理（约 2-3 天）

- [ ] 训练管理（任务创建/启动/SSE日志流/进度）
- [ ] 推理测试（ADB截图 + ElementDetector调用 + 结果可视化）
- [ ] 视频抽帧导入
- [ ] GPU 监控集成

### 第四阶段：完善与优化（约 1-2 天）

- [ ] 标注审核流
- [ ] 数据集统计（类别分布/标注进度）
- [ ] 模型对比
- [ ] 训练历史 + 操作日志
- [ ] UI 细节打磨

---

## 五、依赖关系

### 游戏自动化侧（PC 端 Python）

```
GameAssistant/
├── ml/training_scripts/train_yolo.py      ← 训练脚本（被 Web 平台调用）
├── pc/core/element_detector.py            ← 推理模块（被 Web 平台调用）
├── pc/core/template_matcher.py            ← 模板匹配（被调用）
├── pc/core/device_profile.py              ← 设备配置（被调用）
├── pc/core/screenshot_collector.py        ← ADB 截图（被调用）
└── templates/                             ← 模板目录（被 Web 平台管理）
```

### Web 平台调用 PC 端的方式

通过 `wrappers/` 包装层统一调用，解耦 ML 核心与 FastAPI API 层：

| 包装层 | 核心接口 | 说明 |
|---|---|---|
| `detector_wrapper.py` | `.detect(image_path)` → ElementDetector 推理 | 单例模式管理 detector 生命周期，GPU OOM 时自动降级 |
| `template_wrapper.py` | `.search(image_path, class_name)` → 模板搜索 | 启动时预加载所有激活模板，文件缺失抛出异常 |
| `trainer_wrapper.py` | `.start()` / `.stop()` / `.get_status()` | subprocess 管理训练进程，捕获 exit code |
| `adb_wrapper.py` | `.screenshot()` → adb exec-out 截图 | 3 次重试 + 指数退避 + 连接状态检测 |

**wrappers 错误处理策略：**

| Wrapper | 错误场景 | 处理策略 |
|---|---|---|
| ADBWrapper | adb 连接断开、截图超时 | 3 次重试（间隔 1s/2s/4s）+ 指数退避 + 抛出自定义 `ADBConnectionError` |
| TrainerWrapper | 进程崩溃、日志解析失败 | 捕获 exit code，记录 `training_jobs.error_message`，UI 显示失败状态 |
| DetectorWrapper | GPU OOM、模型加载失败 | 单例模式管理 detector，GPU 显存不足时自动降 batch size |
| TemplateWrapper | 模板文件不存在 | 启动时预加载，若文件缺失抛出 `TemplateNotFoundError` |

**Scale 计算**：`scale = device_width / reference_width`，在 `adb_wrapper.py` 初始化设备配置时计算并缓存，不在数据库层存储。

---

### Web 平台调用 PC 端的方式



---

## 六、已参考的开源项目

| 项目 | GitHub | 借鉴内容 |
|---|---|---|
| **VLM-AutoYOLO** | github.com/Somnusochi/VLM-AutoYOLO | 整体架构、数据库 schema、训练任务管理、SSE 日志、标注界面 |
| **VisOS** | github.com/Dan04ggg/VisOS | 数据增强 UI、格式转换、标注画布交互设计 |
| **DatasetEngine** | github.com/InfusedChooch/DatasetEngine | 主动学习循环思路、数据集健康检查 |
| **AFKOps** | github.com/huytjuh/AFKOps | 混合检测架构设计（模板+YOLO）、Detection 统一接口 |
| **steve1316/uma-android-automation** | github.com/steve1316/uma-android-automation | Android + OpenCV + YOLO 混合架构参考 |

---

## 七、风险与注意事项

| 风险 | 影响 | 缓解方案 |
|---|---|---|
| Vue3 重构工作量 | 从 React 改为 Vue3，VLM-AutoYOLO 的前端代码无法直接复用 | 标注画布参考 VisOS 设计，其他页面全新开发 |
| adb 连接不稳定 | 推理测试失败 | 增加重试机制，UI 显示连接状态 |
| 训练占用 GPU 显存 | Web 推理同时训练时显存不足 | 训练和推理分时复用，或降低 batch size |
| 大批量图片上传（>1000张） | 上传超时 / 内存爆炸 | 分片上传，后台异步处理 |
| MySQL JSON 性能 | 数组字段（JSON）查询性能 | 必要时对 JSON 字段加表达式索引 |
