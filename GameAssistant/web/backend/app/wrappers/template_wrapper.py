"""模板匹配器包装：封装 TemplateMatcher，提供简化推理接口。"""
import sys
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import settings

_PC_CORE = Path(__file__).resolve().parents[3] / "pc" / "core"
if str(_PC_CORE) not in sys.path:
    sys.path.insert(0, str(_PC_CORE))

from template_matcher import TemplateMatcher, Detection as TMD


class DetectionResult:
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


class TemplateWrapper:
    """模板匹配器包装类。"""

    def __init__(
        self,
        template_dir: Optional[str] = None,
        game_config_path: Optional[str] = None,
        device_id: Optional[str] = None,
        threshold: float = 0.85,
    ):
        self.template_dir = template_dir or settings.TEMPLATE_DIR
        self.game_config_path = (
            game_config_path
            or str(Path(__file__).resolve().parents[3] / "config" / "game.yaml")
        )

        sys.path.insert(0, str(_PC_CORE))
        from device_profile import DeviceProfile

        device = DeviceProfile(device_id=device_id) if device_id else None

        try:
            self.matcher = TemplateMatcher(
                template_root=Path(self.template_dir),
                device=device,
                config_path=self.game_config_path,
                threshold=threshold,
            )
            self._ready = True
        except FileNotFoundError as e:
            self.matcher = None
            self._ready = False
            self._init_error = str(e)

    @property
    def is_ready(self) -> bool:
        return self._ready

    def match(self, screen: np.ndarray, cls_name: str) -> list[DetectionResult]:
        """匹配指定类别。"""
        if not self._ready:
            raise RuntimeError(f"TemplateWrapper 未就绪: {getattr(self, '_init_error', 'unknown')}")
        raw: list[TMD] = self.matcher.match(screen, cls_name)
        return [
            DetectionResult(
                cls=d.cls, x=d.x, y=d.y, w=d.w, h=d.h,
                conf=d.conf, source=d.source,
            )
            for d in raw
        ]

    def match_one(self, screen: np.ndarray, cls_name: str) -> Optional[DetectionResult]:
        """匹配指定类别，返回置信度最高的那个。"""
        if not self._ready:
            return None
        raw: Optional[TMD] = self.matcher.match_one(screen, cls_name)
        if raw is None:
            return None
        return DetectionResult(
            cls=raw.cls, x=raw.x, y=raw.y, w=raw.w, h=raw.h,
            conf=raw.conf, source=raw.source,
        )

    def match_all(self, screen: np.ndarray) -> list[DetectionResult]:
        """匹配所有已注册类别。"""
        if not self._ready:
            raise RuntimeError(f"TemplateWrapper 未就绪: {getattr(self, '_init_error', 'unknown')}")
        raw: list[TMD] = self.matcher.match_all(screen)
        return [
            DetectionResult(
                cls=d.cls, x=d.x, y=d.y, w=d.w, h=d.h,
                conf=d.conf, source=d.source,
            )
            for d in raw
        ]
