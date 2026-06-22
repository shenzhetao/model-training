# 冒险岛类 2D 横版 MMORPG 训练方案

> **版本**：v1.0 | **日期**：2026-06-22
> **状态**：✅ **已完成全部 P1-P10 代码改动**

---

## 0. 已确认决策

| # | 问题 | 决策 |
|---|---|---|
| 1 | 参考分辨率 | 1080×1920（9:16 标准比例）|
| 2 | 采集设备 | 华为 nova 5 Pro（1080×2244）|
| 3 | YOLO 训练起步数据量 | 50 张 |
| 4 | 目标 | **5 类元素**：4 模板 + 1 YOLO |

---

## 1. 架构总览

```
screen (adb screencap)
       │
       ▼
┌──────────────────────────────┐
│     ElementDetector          │
│  ┌────────────────────────┐  │
│  │ TemplateMatcher (4类)   │  │  ← < 5ms/帧
│  │  • btn_attack           │  │
│  │  • btn_skill            │  │
│  │  • hp_bar_player        │  │
│  │  • dialog_next          │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ YOLO 推理 (1类)         │  │  ← ~40ms/帧
│  │  • quest_marker         │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
       │
       ▼
  list[Detection]  ← 统一数据结构
```

---

## 2. 多机型适配方案

**问题**：不同手机分辨率不同（nova 5 Pro 是 1080×2244，其他机型可能是 1080×2340/2400 等）。

**解决方案**：参考分辨率 + 相对坐标 + 运行时缩放。

### 原理

```
模板按 1080×1920（参考分辨率）采集
         │
         ▼ adb shell wm size 获取真实分辨率
设备 A：nova 5 Pro → 1080×2244（比例 ~9:18.7）
设备 B：某 9:19.5 屏 → 1080×2340
         │
         ▼ 相对坐标 × 比例因子
每台设备自动计算自己的 ROI 绝对坐标
模板在匹配前 cv2.resize 到目标分辨率
```

### 效果

| 设备 | 参考分辨率 | 真实分辨率 | 模板缩放 |
|---|---|---|---|
| nova 5 Pro | 1080×1920 | 1080×2244 | 高度 ×1.17 |
| 9:19.5 设备 | 1080×1920 | 1080×2340 | 高度 ×1.22 |
| 标准 9:16 | 1080×1920 | 1080×1920 | 无缩放 |

**注意**：异比例设备（9:19.5 vs 参考 9:16）会有轻微形变，建议实际使用中按目标机型单独采集模板。

---

## 3. 元素分类（5 类）

### 分类依据：位置是否固定

| 元素 | 检测方法 | 理由 |
|---|---|---|
| `btn_attack` | 🎯 模板 | 位置像素级固定 |
| `btn_skill` | 🎯 模板 | 槽位固定，ROI 内搜 |
| `hp_bar_player` | 🎯 模板 | 左上角固定 |
| `dialog_next` | 🎯 模板 | 对话框内固定 |
| `quest_marker` | 🧠 YOLO | NPC 头顶位置随机 |

### 排除说明

| 排除 | 原因 |
|---|---|
| hp_bar_enemy | 第一期不考虑 |
| loot_drop | 游戏自带自动拾取 |
| minimap | 不需要小地图功能 |
| loading_icon | 2D 横版手游基本不卡 |

---

## 4. 文件改动清单

| # | 文件 | 状态 | 改动量 |
|---|---|---|---|
| 1 | `config/devices.json` | ✨ 新建 | 15 行 |
| 2 | `config/game.yaml` | ✨ 新建 | 40 行 |
| 3 | `ml/yolo/dataset.yaml` | ⚙️ 改 | 5 行 |
| 4 | `ml/yolo/split_dataset.py` | ⚙️ 改 | 3 行 |
| 5 | `ml/yolo/train_yolo.py` | ⚙️ 改 | 5 行 |
| 6 | `scripts/collect_for_yolo.py` | ⚙️ 改 | 20 行 |
| 7 | `scripts/collect_templates.py` | ✨ 新建 | 100 行 |
| 8 | `pc/core/device_profile.py` | ✨ 新建 | 80 行 |
| 9 | `pc/core/template_matcher.py` | ✨ 新建 | 150 行 |
| 10 | `pc/core/element_detector.py` | ✨ 新建 | 100 行 |
| 11 | `pc/core/screenshot_collector.py` | ⚙️ 改 | 10 行 |

**总计**：7 改 + 4 新建 + 2 新目录

---

## 5. 配置文件

### 5.1 `config/devices.json`

**做什么**：存储已知机型分辨率，定义参考分辨率基准。

**怎么用**：程序启动时自动检测当前设备，自动匹配配置。

```json
{
  "reference_resolution": [1080, 1920],
  "devices": {
    "huawei-nova-5-pro": {
      "width": 1080,
      "height": 2244,
      "density": 2.75,
      "note": "采集设备"
    },
    "xiaomi-13": {
      "width": 1080,
      "height": 2400,
      "density": 3.0
    },
    "samsung-galaxy-s22": {
      "width": 1080,
      "height": 2340,
      "density": 3.0
    }
  }
}
```

### 5.2 `config/game.yaml`

**做什么**：游戏配置中心，所有原来硬编码的 ROI 和参数全部移到这里。改游戏或改槽数只需改这个文件。

**怎么用**：程序启动时一次性加载，后续所有模块都从这里读。

```yaml
game:
  name: "冒险岛类-仿品"
  package_name: "com.example.maplestory"

  skill_slots:
    count: 8                          # 槽位数（可改）
    bar_roi: [0.05, 0.78, 0.90, 0.15]  # 技能条整体区域

  ui_rois:
    btn_attack:    [0.75, 0.88, 0.20, 0.10]   # 攻击键
    hp_bar_player: [0.02, 0.02, 0.30, 0.08]   # 玩家血条
    dialog_next:   [0.70, 0.80, 0.25, 0.12]   # 对话下一步

  yolo_classes:
    - name: quest_marker
      description: "NPC 头顶 ?/! 标记"
```

---

## 6. 新建代码

### 6.1 `pc/core/device_profile.py`

**做什么**：多机型分辨率管理器。

**核心功能**：
- 通过 `adb shell wm size` 自动获取当前设备分辨率
- 提供 `to_absolute(rel_roi)` 把相对坐标（0~1）转成当前设备的绝对像素坐标
- 提供 `scale_template()` 把参考分辨率模板缩放到当前设备

**改了什么**：纯新增文件。

```python
class DeviceProfile:
    """处理不同机型屏幕分辨率"""

    def __init__(self, device_id=None, config_path="config/devices.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        self.ref_w, self.ref_h = self.config["reference_resolution"]
        self.width, self.height = self._get_device_resolution(device_id)
        self.scale_x = self.width / self.ref_w
        self.scale_y = self.height / self.ref_h

    def _get_device_resolution(self, device_id):
        cmd = ["adb", "shell", "wm", "size"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        size_str = result.stdout.strip().split(":")[-1].strip()
        w, h = map(int, size_str.split("x"))
        return w, h

    def to_absolute(self, rel_roi):
        rx, ry, rw, rh = rel_roi
        return (int(rx * self.width), int(ry * self.height),
                int(rw * self.width), int(rh * self.height))

    def scale_template(self, template):
        h, w = template.shape[:2]
        return cv2.resize(template, (int(w * self.scale_x), int(h * self.scale_y)))
```

**使用示例**：

```python
device = DeviceProfile()          # 自动检测：1080×2244
abs_roi = device.to_absolute([0.75, 0.88, 0.20, 0.10])  # → (810, 1975, 216, 224)
```

### 6.2 `pc/core/template_matcher.py`

**做什么**：封装 OpenCV 模板匹配，支持多状态、多 ROI、自动缩放。

**核心功能**：
- 启动时一次性加载所有模板并缩放到当前分辨率，缓存到内存
- 每个类别只在自己的 ROI 内搜索（缩小搜索范围，速度 ×5）
- 技能按钮自动在 `bar_roi` 区域内匹配 8 个槽位

**改了什么**：纯新增文件。

```python
@dataclass
class Detection:
    cls: str
    x: int; y: int; w: int; h: int
    conf: float
    source: str  # 'template' 或 'yolo'

class TemplateMatcher:
    TEMPLATE_CLASSES = ["btn_attack", "btn_skill", "hp_bar_player", "dialog_next"]

    def __init__(self, template_root, device, config, threshold=0.85):
        self.device = device
        self.config = config
        self.threshold = threshold
        self._cache = {}
        self._load_templates()   # 启动时一次加载+缩放

    def _load_templates(self):
        for cls in self.TEMPLATE_CLASSES:
            cls_dir = self.template_root / cls
            self._cache[cls] = []
            for state_file in cls_dir.glob("*.png"):
                tmpl = cv2.imread(str(state_file))
                tmpl_scaled = self.device.scale_template(tmpl)
                self._cache[cls].append((state_file.stem, tmpl_scaled))

    def match(self, screen, cls_name):
        # 1. 从 game.yaml 读 ROI 相对坐标
        rel_roi = (self.config["skill_slots"]["bar_roi"]
                   if cls_name == "btn_skill"
                   else self.config["ui_rois"][cls_name])
        # 2. 转绝对坐标
        rx, ry, rw, rh = self.device.to_absolute(rel_roi)
        # 3. 裁剪 ROI
        roi = screen[ry:ry+rh, rx:rx+rw]
        # 4. 匹配每个状态模板
        results = []
        for state_name, tmpl in self._cache.get(cls_name, []):
            res = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)
            for pt in zip(*np.where(res >= self.threshold)[::-1]):
                results.append(Detection(cls=cls_name, x=rx+pt[0], y=ry+pt[1],
                                        w=tmpl.shape[1], h=tmpl.shape[0],
                                        conf=float(res[pt[1], pt[0]]),
                                        source=f'template:{state_name}'))
        return results

    def match_all(self, screen):
        results = []
        for cls in self.TEMPLATE_CLASSES:
            results.extend(self.match(screen, cls))
        return results
```

### 6.3 `pc/core/element_detector.py`

**做什么**：4 模板 + 1 YOLO 的统一编排器，对外暴露单一 `detect()` 接口。

**改了什么**：纯新增文件。

```python
class ElementDetector:
    """混合元素检测器（4T + 1Y）"""

    def __init__(self, template_dir, yolo_model_path, device, game_config,
                 yolo_conf=0.4):
        self.matcher = TemplateMatcher(template_dir, device, game_config)
        self.yolo = YOLO(str(yolo_model_path))
        self.yolo_conf = yolo_conf
        self.yolo_classes = game_config["yolo_classes"]

    def detect(self, screen):
        results = []
        results.extend(self.matcher.match_all(screen))          # 4 模板
        for r in self.yolo.predict(screen, classes=[0],
                                   conf=self.yolo_conf, verbose=False):
            for box, cls_id, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                x1, y1, x2, y2 = box.cpu().numpy()
                results.append(Detection(
                    cls=self.yolo_classes[int(cls_id)]["name"],
                    x=int(x1), y=int(y1), w=int(x2-x1), h=int(y2-y1),
                    conf=float(conf), source='yolo'))
        return results

    def find(self, screen, cls):
        """找第一个指定类别"""
        for d in self.detect(screen):
            if d.cls == cls:
                return d
        return None
```

### 6.4 `scripts/collect_templates.py`

**做什么**：交互式采集模板图，一次性完成约 12 张。

**改了什么**：纯新增文件。

```python
TEMPLATE_SPECS = [
    ("btn_attack",    ["normal"],         "右下角攻击键可见"),
    ("btn_skill",     [f"skill{i}" for i in range(1, 9)],  # skill1~skill8
                      "8 个技能槽位都可见"),
    ("hp_bar_player", ["normal"],          "左上角玩家血条完整"),
    ("dialog_next",   ["with_arrow"],     "和 NPC 对话，看到 ▶"),
]

def main():
    device = DeviceProfile()
    collector = ScreenshotCollector(device)
    output_root = Path("templates")

    for cls_name, states, hint in TEMPLATE_SPECS:
        for state in states:
            print(f"\n>>> 请操作：{hint}")
            input("按回车截取...")
            screen = collector.capture_frame()
            rel_roi = get_roi(cls_name, state)
            x, y, w, h = device.to_absolute(rel_roi)
            cv2.imwrite(str(output_root / cls_name / f"{state}.png"),
                        screen[y:y+h, x:x+w])
            print(f"    ✓ 保存 templates/{cls_name}/{state}.png")
```

**产物目录结构**：

```
templates/
├── btn_attack/normal.png
├── btn_skill/skill1.png ~ skill8.png
├── hp_bar_player/normal.png
└── dialog_next/with_arrow.png
```

---

## 7. 改动代码

### 7.1 `ml/yolo/dataset.yaml`

**做什么**：定义 YOLO 训练集类别。

**改了什么**：8 类 → 1 类。

```yaml
# 改前：nc: 8, 8 个类别
# 改后：
nc: 1
names:
  0: quest_marker
```

### 7.2 `scripts/split_dataset.py`

**做什么**：把 raw 数据划分 train/val（9:1）。

**改了什么**：去掉硬编码 `EXPECTED_CLASSES = 8`，改成自动读 yaml。

```python
# 改前
EXPECTED_CLASSES = 8
if len(classes) != EXPECTED_CLASSES: raise ...

# 改后
import yaml
with open("dataset.yaml") as f:
    cfg = yaml.safe_load(f)
nc = cfg["nc"]   # 自动 = 1，不再写死
```

### 7.3 `ml/training_scripts/train_yolo.py`

**做什么**：用 ultralytics 训练 YOLO。

**改了什么**：epochs/batch 调小，防止数据少过拟合。

```python
# 改前
epochs=100, batch=16

# 改后
epochs=50, batch=8, mixup=0.15, patience=15
```

### 7.4 `scripts/collect_for_yolo.py`

**做什么**：交互式采集 YOLO 训练数据。

**改了什么**：8 场景 → 1 场景（只采 `quest_marker`），场景减少后操作流程更短。

```python
# 改前：8 个场景，每个 30-50 张
# 改后：
scenarios = [
    ("quest_marker", 50),   # 起步 50 张
]
```

### 7.5 `pc/core/screenshot_collector.py`

**做什么**：adb 截图封装。

**改了什么**：新增 `capture_frame()` 返回 ndarray（给检测器用），原有方法保留不变。

```python
def capture_frame(self) -> np.ndarray:
    """截一帧，返回 BGR ndarray（用于实时检测）"""
    result = subprocess.run(
        ["adb", "exec-out", "screencap", "-p"],
        capture_output=True)
    return cv2.imdecode(
        np.frombuffer(result.stdout, dtype=np.uint8),
        cv2.IMREAD_COLOR)
```

---

## 8. 实施步骤

| 阶段 | 操作 | 涉及文件 | 耗时 |
|---|---|---|---|
| P1 | 创建 `config/devices.json` + `game.yaml` | 新建 2 文件 | — |
| P2 | 创建 `pc/core/device_profile.py` | 新建 | — |
| P3 | 创建 `pc/core/template_matcher.py` | 新建 | — |
| P4 | 创建 `pc/core/element_detector.py` | 新建 | — |
| P5 | 改 `ml/yolo/dataset.yaml` 1 类 | 改 | — |
| P6 | 改 `ml/yolo/split_dataset.py` | 改 | — |
| P7 | 改 `ml/yolo/train_yolo.py` 调参 | 改 | — |
| P8 | 改 `scripts/collect_for_yolo.py` | 改 | — |
| P9 | 创建 `scripts/collect_templates.py` | 新建 | — |
| P10 | 改 `pc/core/screenshot_collector.py` | 改 | — |
| **P11** | **跑 `collect_templates.py`** | **~12 张** | **10-15 分钟** |
| **P12** | **跑 `collect_for_yolo.py`** | **~50 张** | **30-60 分钟** |
| **P13** | **AutoLabelImg 标注 50 张** | — | **30-60 分钟** |
| **P14** | **跑 `train_yolo.py` 训练** | — | **~30 分钟** |
| **P15** | **ElementDetector 联调测试** | — | — |

---

## 9. 风险提示

| 风险 | 影响 | 缓解 |
|---|---|---|
| 模板在异比例设备形变 | 匹配失败 | 建议各机型单独采集模板，或只用同比例设备 |
| quest_marker 数据不足 | mAP 低 | 起步 50 张 + mosaic/mixup augmentation |
| 模板阈值 0.85 偏严/偏松 | 漏检/误检 | 上线后用 `template_matcher.threshold` 调整 |
| 技能按钮 ROI 切分不均 | 部分槽漏检 | 按 `bar_roi` 整体搜索，不切分槽位 |

---

## 10. 下一步

等你确认后，我按 **P1→P10** 顺序执行代码改动。

**回复格式**：
- `"全部 OK"` → 开始改代码
- `"这里要改：xxx"` → 我先改某处再重新出方案
