"""
YOLO 目标检测推理引擎
使用训练好的模型检测游戏 UI 元素

使用方式：
    from ml.training_scripts.yolo_detector import YOLODetector
    detector = YOLODetector("ml/weights/yolo/best.pt")
    coord = detector.find(image, "btn_attack")
"""
import cv2
import torch
from ultralytics import YOLO
from dataclasses import dataclass


@dataclass
class Detection:
    """单个检测结果"""
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x, y, w, h
    center: tuple[int, int]           # cx, cy


class YOLODetector:
    """YOLO 目标检测器封装"""

    def __init__(self, model_path: str = "ml/weights/yolo/best.pt",
                 conf_threshold: float = 0.6,
                 iou_threshold: float = 0.45):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = 0 if torch.cuda.is_available() else "cpu"

    def detect(self, image,
               target_class: str | None = None) -> list[Detection]:
        """检测图像中的目标，返回 Detection 列表"""
        results = self.model(
            image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
            device=self.device
        )[0]

        detections = []
        names = self.model.names

        if results.boxes is None:
            return []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            class_name = names[cls_id]

            if target_class and class_name != target_class:
                continue

            detections.append(Detection(
                class_name=class_name,
                confidence=conf,
                bbox=(x1, y1, x2 - x1, y2 - y1),
                center=(cx, cy)
            ))

        detections.sort(key=lambda d: -d.confidence)
        return detections

    def find(self, image, target: str):
        """快速查找单个目标，返回中心坐标，未找到返回 None"""
        detections = self.detect(image, target_class=target)
        return detections[0].center if detections else None

    def find_all(self, image, targets: list[str]) -> dict:
        """一次检测多个类别"""
        all_detections = self.detect(image)
        result = {t: [] for t in targets}
        for det in all_detections:
            if det.class_name in targets:
                result[det.class_name].append(det.center)
        return result

    def draw(self, image, detections=None):
        """在图像上绘制检测结果"""
        if detections is None:
            detections = self.detect(image)
        output = image.copy()
        for det in detections:
            x, y, w, h = det.bbox
            cx, cy = det.center
            color = (0, 255, 0)
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(output, label, (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.circle(output, (cx, cy), 3, (0, 0, 255), -1)
        return output


if __name__ == "__main__":
    print("YOLO 推理引擎已加载")
    print("请确保 ml/weights/yolo/best.pt 模型文件存在")
    print("使用方式: from ml.training_scripts.yolo_detector import YOLODetector")
