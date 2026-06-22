"""OpenCV 模板匹配封装，支持多状态、多 ROI、运行时自动缩放。"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

from .device_profile import DeviceProfile


@dataclass
class Detection:
    """统一的检测结果结构，模板和 YOLO 共用此格式。"""
    cls: str
    x: int
    y: int
    w: int
    h: int
    conf: float
    source: str  # 'template:{state}' 或 'yolo'


class TemplateMatcher:
    """模板匹配器。

    启动时一次性加载所有模板并缩放到当前设备分辨率，
    运行时按 game.yaml 中的 ROI 在固定区域搜索，速度快且精度高。
    """

    def __init__(
        self,
        template_root: Path,
        device: DeviceProfile,
        config_path: str = "config/game.yaml",
        threshold: float = 0.85,
    ):
        self.template_root = Path(template_root)
        self.device = device
        self.threshold = threshold

        # 加载游戏配置
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # 启动时一次性加载+缩放所有模板
        self._cache: dict[str, list[tuple[str, np.ndarray]]] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """扫描 templates/ 目录，按 {cls}/{state}.png 结构加载并缩放。"""
        for cls_dir in self.template_root.iterdir():
            if not cls_dir.is_dir():
                continue
            cls_name = cls_dir.name
            if cls_name not in self.config.get("ui_rois", {}) and cls_name != "btn_skill":
                continue
            self._cache[cls_name] = []
            for state_file in sorted(cls_dir.glob("*.png")):
                tmpl = cv2.imread(str(state_file))
                if tmpl is None:
                    continue
                # 关键：缩放到当前设备分辨率
                tmpl_scaled = self.device.scale_template(tmpl)
                self._cache[cls_name].append((state_file.stem, tmpl_scaled))

    def _get_roi(self, cls_name: str) -> list[float]:
        """从 game.yaml 读取指定类别的 ROI（相对坐标）。"""
        if cls_name == "btn_skill":
            return self.config["skill_slots"]["bar_roi"]
        return self.config["ui_rois"][cls_name]["roi"]

    def match(self, screen: np.ndarray, cls_name: str) -> list[Detection]:
        """在 ROI 区域内匹配指定类别的所有状态模板。"""
        if cls_name not in self._cache:
            return []

        # 1. 取 ROI 相对坐标 → 转绝对坐标
        rel_roi = self._get_roi(cls_name)
        rx, ry, rw, rh = self.device.to_absolute(rel_roi)

        # 2. 裁剪搜索区域
        roi_screen = screen[ry:ry + rh, rx:rx + rw]
        if roi_screen.size == 0:
            return []

        results = []
        for state_name, tmpl in self._cache[cls_name]:
            # 3. 匹配
            if tmpl.shape[0] > roi_screen.shape[0] or tmpl.shape[1] > roi_screen.shape[1]:
                continue
            res = cv2.matchTemplate(roi_screen, tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(res >= self.threshold)

            # 4. 非极大值抑制（避免重叠框）
            for pt in zip(*locations[::-1]):
                conf = float(res[pt[1], pt[0]])
                results.append(Detection(
                    cls=cls_name,
                    x=rx + pt[0],
                    y=ry + pt[1],
                    w=tmpl.shape[1],
                    h=tmpl.shape[0],
                    conf=conf,
                    source=f"template:{state_name}",
                ))

        # NMS 去重
        return self._nms(results)

    def _nms(self, detections: list[Detection], iou_thresh: float = 0.3) -> list[Detection]:
        """简单的非极大值抑制，按 conf 降序保留。"""
        if not detections:
            return []
        dets = sorted(detections, key=lambda d: d.conf, reverse=True)
        keep = []
        for d in dets:
            overlapped = any(
                self._iou(d, k) > iou_thresh for k in keep
            )
            if not overlapped:
                keep.append(d)
        return keep

    def _iou(self, a: Detection, b: Detection) -> float:
        """计算两个检测框的 IoU。"""
        x1 = max(a.x, b.x)
        y1 = max(a.y, b.y)
        x2 = min(a.x + a.w, b.x + b.w)
        y2 = min(a.y + a.h, b.y + b.h)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        union = a.w * a.h + b.w * b.h - inter
        return inter / union if union > 0 else 0.0

    def match_all(self, screen: np.ndarray) -> list[Detection]:
        """匹配所有 4 个模板类别。"""
        results = []
        for cls in self.config.get("ui_rois", {}):
            results.extend(self.match(screen, cls))
        results.extend(self.match(screen, "btn_skill"))
        return results

    def match_one(self, screen: np.ndarray, cls_name: str) -> Optional[Detection]:
        """便捷方法：只找置信度最高的那个，不返回列表。"""
        matches = self.match(screen, cls_name)
        if not matches:
            return None
        return max(matches, key=lambda d: d.conf)
