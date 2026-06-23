"""元素检测器包装：4 模板 + 1 YOLO 混合检测，统一对外接口。"""
import sys
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import settings

# 动态添加 GameAssistant pc/core 到 sys.path（如果存在）
_PC_CORE = Path(__file__).resolve().parents[3] / "pc" / "core"
if _PC_CORE.exists() and str(_PC_CORE) not in sys.path:
    sys.path.insert(0, str(_PC_CORE))

try:
    from template_matcher import TemplateMatcher, Detection as TMD
    from element_detector import ElementDetector
    _HAS_DETECTOR = True
except ImportError:
    TMD = None  # type: ignore
    ElementDetector = None  # type: ignore
    _HAS_DETECTOR = False


class DetectionResult:
    """统一的检测结果（与前端协议对齐）。"""
    def __init__(
        self,
        cls: str,
        x: int,
        y: int,
        w: int,
        h: int,
        conf: float,
        source: str,
    ):
        self.cls = cls
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.conf = conf
        self.source = source

    def to_dict(self) -> dict:
        return {
            "cls": self.cls,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "conf": round(float(self.conf), 4),
            "source": self.source,
        }


class DetectorWrapper:
    """元素检测器包装类，封装 ElementDetector 并提供简化的推理接口。"""

    def __init__(
        self,
        template_dir: Optional[str] = None,
        yolo_model_path: Optional[str] = None,
        game_config_path: Optional[str] = None,
        device_id: Optional[str] = None,
        yolo_conf: float = 0.4,
    ):
        self.template_dir = template_dir or settings.TEMPLATE_DIR
        self.yolo_model_path = yolo_model_path
        self.game_config_path = (
            game_config_path
            or str(Path(__file__).resolve().parents[3] / "config" / "game.yaml")
        )

        if not _HAS_DETECTOR:
            self.detector = None
            self._ready = False
            self._init_error = "template_matcher / element_detector 模块不可用"
            return

        try:
            if _PC_CORE.exists() and str(_PC_CORE) not in sys.path:
                sys.path.insert(0, str(_PC_CORE))
            from device_profile import DeviceProfile

            device = DeviceProfile(device_id=device_id) if device_id else None

            self.detector = ElementDetector(
                template_dir=Path(self.template_dir),
                yolo_model_path=Path(self.yolo_model_path) if self.yolo_model_path else None,
                game_config_path=self.game_config_path,
                device=device,
                yolo_conf=yolo_conf,
            )
            self._ready = True
        except FileNotFoundError as e:
            self.detector = None
            self._ready = False
            self._init_error = str(e)
        except Exception as e:
            self.detector = None
            self._ready = False
            self._init_error = str(e)

    @property
    def is_ready(self) -> bool:
        return self._ready

    def detect(self, screen: np.ndarray) -> list[DetectionResult]:
        """对一张截图执行混合检测。"""
        if not self._ready:
            raise RuntimeError(f"Detector 未就绪: {getattr(self, '_init_error', 'unknown')}")
        raw_results: list = self.detector.detect(screen)
        return [
            DetectionResult(
                cls=d.cls,
                x=d.x,
                y=d.y,
                w=d.w,
                h=d.h,
                conf=d.conf,
                source=d.source,
            )
            for d in raw_results
        ]

    def find(self, screen: np.ndarray, cls: str) -> Optional[DetectionResult]:
        """找第一个指定类别（置信度最高）。"""
        if not self._ready:
            return None
        raw = self.detector.find(screen, cls)
        if raw is None:
            return None
        return DetectionResult(
            cls=raw.cls, x=raw.x, y=raw.y,
            w=raw.w, h=raw.h, conf=raw.conf, source=raw.source,
        )

    def draw(self, screen: np.ndarray, detections: list[DetectionResult]) -> np.ndarray:
        """在截图上绘制检测框（调试用）。"""
        if not self._ready:
            return screen
        if TMD is None:
            return screen
        raw = [TMD(
            cls=d.cls, x=d.x, y=d.y, w=d.w, h=d.h,
            conf=d.conf, source=d.source,
        ) for d in detections]
        return self.detector.draw(screen, raw)
