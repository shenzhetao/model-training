# YOLO 使用说明

## 文件清单

```
GameAssistant/
├── scripts/
│   ├── collect_for_yolo.py    # 数据采集脚本
│   └── split_dataset.py        # 数据集划分脚本
├── datasets/raw/
│   └── predefined_classes.txt  # 类别定义文件
├── ml/
│   ├── yolo/
│   │   └── dataset.yaml        # 数据集配置文件
│   ├── training_scripts/
│   │   ├── train_yolo.py       # 模型训练脚本
│   │   └── yolo_detector.py    # 推理引擎
│   └── weights/yolo/           # 训练产出模型放这里
└── pc/core/
    └── screenshot_collector.py  # 截图采集工具
```

---

## 第一阶段：数据采集

### 1.1 安装标注工具

```bash
pip install labelImg==1.8.6
```

### 1.2 启动采集脚本

```bash
cd GameAssistant
python scripts/collect_for_yolo.py
```

脚本会依次提示你操作到每个场景，按回车后自动采集指定数量的截图。

### 1.3 采集策略

| 类别 | 建议数量 | 采集要点 |
|------|---------|---------|
| btn_attack | 50 | 采集不同尺寸、不同颜色的攻击按钮 |
| btn_skill | 50 | 多个技能按钮，每个至少 10 张 |
| hp_bar_enemy | 30 | 满血、空血、半血等多种状态 |
| hp_bar_player | 30 | 同上 |
| dialog_confirm | 30 | 各种确认弹窗 |
| loading_icon | 30 | 加载画面截图 |
| quest_marker | 30 | 地图上的任务标记 |
| treasure_box | 30 | 开启前和开启后的宝箱 |

**重要**：采集时尽量变换场景——不同的光照、不同的 UI 缩放比例、不同的时间段。这样训练出来的模型才够鲁棒。

---

## 第二阶段：数据标注

### 2.1 标注工具

使用 **LabelImg**，支持 Windows 直接运行。

安装：
```bash
pip install labelImg==1.8.6
```

启动（以 YOLO 格式输出）：
```bash
cd GameAssistant
labelImg datasets/raw datasets/raw/predefined_classes.txt
```

### 2.2 标注操作

1. LabelImg 打开后，左侧切换到 `datasets/raw` 目录
2. 按 `W` 键开始画框
3. 用鼠标框住目标 UI 元素（要紧贴边缘，留 2-3 像素即可）
4. 在右侧列表中选择对应的类别名称
5. 按 `D` 键下一张，`A` 键上一张
6. 重复直到标注完全部图片

### 2.3 标注规范

- **只标注感兴趣的目标区域**，不要框住整个面板
- 模糊、遮挡、截断的 UI 也要标注
- 每个 `.png/.jpg` 图片会对应生成一个 `.txt` 文件（YOLO 格式）
- 标注顺序无所谓，关键是框要准确

### 2.4 类别定义

`predefined_classes.txt` 中定义了 8 个类别：

```
btn_attack      # 攻击按钮
btn_skill       # 技能按钮
hp_bar_enemy    # 敌人血条
hp_bar_player   # 玩家血条
dialog_confirm  # 确认对话框
loading_icon    # 加载图标
quest_marker    # 任务标记
treasure_box    # 宝箱
```

如果游戏有其他 UI 元素，可以修改此文件，但需要同步修改 `ml/yolo/dataset.yaml` 中的类别定义。

---

## 第三阶段：数据集划分

所有图片标注完成后，运行：

```bash
cd GameAssistant
python scripts/split_dataset.py
```

脚本会：
- 随机选取 80% 作为训练集，20% 作为验证集
- 自动创建 `ml/yolo/datasets/images/train`、`images/val`、`labels/train`、`labels/val` 目录
- 将图片和标注文件复制到对应目录

---

## 第四阶段：训练模型

### 4.1 安装依赖

```bash
pip install ultralytics torch torchvision
```

### 4.2 运行训练

```bash
cd GameAssistant
python ml/training_scripts/train_yolo.py
```

### 4.3 训练参数说明

脚本默认参数：
- 模型大小：`n`（nano，最轻量，速度最快）
- 训练轮数：50（测试用，正式训练建议 100-200）
- 批次大小：8
- 输入尺寸：640

训练过程中会显示 loss 曲线。完成后会自动评估验证集指标。

### 4.4 怎么看训练效果

训练完成后查看以下指标：

| 指标 | 入门 | 良好 | 优秀 |
|------|------|------|------|
| mAP50 | >0.6 | >0.75 | >0.85 |
| Recall | >0.65 | >0.80 | >0.90 |
| Precision | >0.70 | >0.80 | >0.90 |

如果指标过低，检查：
1. 标注是否准确（框有没有画歪）
2. 每个类别的样本数量是否足够（至少 30 张/类）
3. 类别定义是否合理

### 4.5 模型文件位置

训练完成后，最佳模型保存在：
```
GameAssistant/ml/weights/yolo/best.pt
```

---

## 第五阶段：推理测试

训练完成后，可以用推理引擎测试效果：

```python
from ml.training_scripts.yolo_detector import YOLODetector
import cv2

detector = YOLODetector(
    model_path="ml/weights/yolo/best.pt",
    conf_threshold=0.65
)

img = cv2.imread("templates/workspace/test_001.png")
coord = detector.find(img, "btn_attack")
print(f"攻击按钮坐标: {coord}")

# 检测所有目标
dets = detector.detect(img)
for d in dets:
    print(f"  {d.class_name}: {d.center} ({d.confidence:.2f})")

# 可视化
result = detector.draw(img)
cv2.imshow("Detection", result)
cv2.waitKey(0)
```

---

## 快速检查清单

- [ ] 安装 labelImg
- [ ] 运行 `python scripts/collect_for_yolo.py` 采集数据
- [ ] 用 LabelImg 标注所有截图
- [ ] 运行 `python scripts/split_dataset.py` 划分数据集
- [ ] 安装 ultralytics / torch / torchvision
- [ ] 运行 `python ml/training_scripts/train_yolo.py`
- [ ] 查看验证集 mAP 指标
- [ ] 用推理引擎测试实际效果
