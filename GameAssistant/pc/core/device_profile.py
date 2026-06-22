"""多机型分辨率管理：自动检测设备分辨率，提供相对坐标转绝对坐标和模板缩放。"""
import json
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


class DeviceProfile:
    """处理不同机型屏幕分辨率的适配。

    工作流程：
    1. 加载 config/devices.json 获取参考分辨率和已知机型列表
    2. 通过 adb shell wm size 获取当前设备真实分辨率
    3. 计算缩放因子，支持相对坐标转换和模板缩放

    相对坐标格式：[rx, ry, rw, rh]，取值 0.0 ~ 1.0
    绝对坐标格式：(x, y, w, h)，取值像素
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        config_path: str = "config/devices.json",
    ):
        self.device_id = device_id
        self._load_config(Path(config_path))
        self.width, self.height = self._get_device_resolution()
        self._compute_scale()

    def _load_config(self, config_path: Path) -> None:
        if not config_path.exists():
            raise FileNotFoundError(
                f"设备配置文件不存在：{config_path}，"
                "请先运行 scripts/auto_detect_device.py 或手动创建"
            )
        with open(config_path, encoding="utf-8") as f:
            self.config = json.load(f)
        self.ref_w: int
        self.ref_h: int
        self.ref_w, self.ref_h = self.config["reference_resolution"]

    def _get_device_resolution(self) -> tuple[int, int]:
        cmd = ["adb", "shell", "wm", "size"]
        if self.device_id:
            cmd = ["adb", "-s", self.device_id, "shell", "wm", "size"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        # 输出格式："Physical size: 1080x2244"
        raw = result.stdout.strip()
        if ":" in raw:
            size_str = raw.split(":")[-1].strip()
        else:
            size_str = raw.strip()
        if "x" not in size_str:
            raise RuntimeError(f"无法解析 adb wm size 输出：{raw}")
        w, h = map(int, size_str.split("x"))
        return w, h

    def _compute_scale(self) -> None:
        self.scale_x = self.width / self.ref_w
        self.scale_y = self.height / self.ref_h

    def to_absolute(self, rel_roi: list[float]) -> tuple[int, int, int, int]:
        """相对坐标 [rx, ry, rw, rh] → 绝对坐标 (x, y, w, h)。"""
        rx, ry, rw, rh = rel_roi
        return (
            int(rx * self.width),
            int(ry * self.height),
            int(rw * self.width),
            int(rh * self.height),
        )

    def scale_template(self, template: np.ndarray) -> np.ndarray:
        """把参考分辨率的模板缩放到当前设备分辨率。"""
        h, w = template.shape[:2]
        new_w = int(w * self.scale_x)
        new_h = int(h * self.scale_y)
        return cv2.resize(template, (new_w, new_h))

    def get_roi(self, rel_roi: list[float]) -> np.ndarray:
        """返回绝对 ROI 区域的 (x, y, w, h, rx, ry, rw, rh) 元组，方便调试。"""
        x, y, w, h = self.to_absolute(rel_roi)
        rx, ry, rw, rh = rel_roi
        return (x, y, w, h, rx, ry, rw, rh)

    @property
    def ratio(self) -> float:
        """屏幕宽高比。"""
        return self.width / self.height

    @property
    def is_reference(self) -> bool:
        """当前设备是否就是参考分辨率设备。"""
        return self.width == self.ref_w and self.height == self.ref_h

    def __repr__(self) -> str:
        scale_info = (
            f"scale=({self.scale_x:.3f}x, {self.scale_y:.3f}y)"
            if not self.is_reference
            else "scale=(1.0x, 1.0y) [reference device]"
        )
        return (
            f"DeviceProfile({self.width}x{self.height}, "
            f"ref={self.ref_w}x{self.ref_h}, {scale_info})"
        )
