"""4 模板 + 1 YOLO 混合元素检测器，统一编排，对外单一接口。"""
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

from .device_profile import DeviceProfile
from .template_matcher import TemplateMatcher, Detection


class ElementDetector:
    """混合元素检测器（4T + 1Y）。

    模板匹配（<5ms）处理位置固定的 UI：
        btn_attack / btn_skill / hp_bar_player / dialog_next
    YOLO 推理（~40ms）处理位置随机的元素：
        quest_marker（NPC 头顶 ?/! 标记）
    两者输出统一的 Detection 数据结构。
    """

    def __init__(
        self,
        template_dir: Path,
        yolo_model_path: Path,
        game_config_path: str = "config/game.yaml",
        device: Optional[DeviceProfile] = None,
        yolo_conf: float = 0.4,
    ):
        self.device = device or DeviceProfile()

        with open(game_config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.matcher = TemplateMatcher(
            template_root=template_dir,
            device=self.device,
            config_path=game_config_path,
            threshold=self.config.get("detection", {}).get("template_threshold", 0.85),
        )

        model_path = yolo_model_path or Path(self.config["detection"]["yolo_model"])
        if model_path.exists():
            self.yolo = YOLO(str(model_path))
        else:
            self.yolo = None
            print(f"[ElementDetector] 警告：YOLO 模型不存在 {model_path}，quest_marker 将无法检测")

        self.yolo_conf = yolo_conf
        self.yolo_classes = {i: c["name"] for i, c in enumerate(self.config["yolo_classes"])}

    def detect(self, screen: np.ndarray) -> list[Detection]:
        """对一张截图，返回所有 5 类元素的检测结果。"""
        results = []

        # 1. 模板匹配（4 类）
        results.extend(self.matcher.match_all(screen))

        # 2. YOLO 推理（1 类：quest_marker）
        if self.yolo is not None:
            yolo_results = self.yolo.predict(
                screen,
                classes=[0],          # quest_marker 是第 0 类
                conf=self.yolo_conf,
                verbose=False,
            )
            for r in yolo_results:
                for box, cls_id, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                    x1, y1, x2, y2 = box.cpu().numpy()
                    cls_name = self.yolo_classes.get(int(cls_id), f"unknown_{cls_id}")
                    results.append(Detection(
                        cls=cls_name,
                        x=int(x1), y=int(y1),
                        w=int(x2 - x1), h=int(y2 - y1),
                        conf=float(conf),
                        source="yolo",
                    ))

        return results

    def find(self, screen: np.ndarray, cls: str) -> Optional[Detection]:
        """便捷方法：找第一个指定类别（置信度最高）。"""
        candidates = [d for d in self.detect(screen) if d.cls == cls]
        if not candidates:
            return None
        return max(candidates, key=lambda d: d.conf)

    def find_all(self, screen: np.ndarray, cls: str) -> list[Detection]:
        """找所有指定类别的检测结果（用于 btn_skill 多个槽位）。"""
        return [d for d in self.detect(screen) if d.cls == cls]

    def draw(self, screen: np.ndarray, detections: list[Detection]) -> np.ndarray:
        """在截图上绘制所有检测框（调试用）。"""
        for d in detections:
            color = (0, 255, 0) if d.source.startswith("template") else (0, 165, 255)
            cv2.rectangle(screen, (d.x, d.y), (d.x + d.w, d.y + d.h), color, 2)
            label = f"{d.cls} {d.conf:.2f} [{d.source}]"
            cv2.putText(screen, label, (d.x, d.y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return screen
