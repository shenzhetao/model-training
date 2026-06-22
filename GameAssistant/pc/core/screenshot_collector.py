"""
截图采集工具：连接 Android 设备，自动截取屏幕并保存
用于收集机器学习训练数据
"""

import os
import time
import subprocess
import cv2
import numpy as np
from datetime import datetime


class ScreenshotCollector:
    """Android 屏幕批量采集器"""

    def __init__(self, output_dir: str = "templates/workspace",
                 device_id: str | None = None):
        self.output_dir = output_dir
        self.device_id = f"-s {device_id}" if device_id else ""
        os.makedirs(output_dir, exist_ok=True)

    def capture(self, filename: str | None = None) -> str:
        """
        截取当前屏幕并保存到文件
        返回保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"screenshot_{timestamp}.png"

        filepath = os.path.join(self.output_dir, filename)
        local_tmp = "/sdcard/_tmp_screen.png"

        subprocess.run(
            f"adb {self.device_id} shell screencap -p {local_tmp}",
            shell=True, check=True
        )
        subprocess.run(
            f"adb {self.device_id} pull {local_tmp} {filepath}",
            shell=True, check=True
        )
        subprocess.run(
            f"adb {self.device_id} shell rm {local_tmp}",
            shell=True
        )

        return filepath

    def batch_capture(self, count: int, interval: float = 1.0,
                      prefix: str = "batch"):
        """
        批量采集截图
        count: 采集数量
        interval: 每次采集间隔（秒）
        prefix: 文件名前缀
        """
        print(f"开始批量采集，共 {count} 张，间隔 {interval}s")
        for i in range(count):
            filename = f"{prefix}_{i+1:04d}.png"
            path = self.capture(filename)
            print(f"  [{i+1}/{count}] 已保存: {path}")
            if i < count - 1:
                time.sleep(interval)
        print("采集完成")

    def capture_with_state(self, state_label: str, count: int = 10):
        """
        按游戏状态批量采集
        例如：capture_with_state("battle", 20) 采集20张战斗画面
        """
        state_dir = os.path.join(self.output_dir, state_label)
        os.makedirs(state_dir, exist_ok=True)

        original_dir = self.output_dir
        self.output_dir = state_dir
        self.batch_capture(count, prefix=state_label)
        self.output_dir = original_dir

    def capture_frame(self) -> np.ndarray | None:
        """
        截取当前屏幕，直接返回 BGR ndarray（不写文件）。
        用于 ElementDetector 实时检测。

        返回：
            BGR 格式的 numpy 数组，或失败时返回 None
        """
        local_tmp = "/sdcard/_tmp_screen.png"
        try:
            subprocess.run(
                f"adb {self.device_id} shell screencap -p {local_tmp}",
                shell=True, check=True, capture_output=True, timeout=10,
            )
            result = subprocess.run(
                f"adb {self.device_id} shell exec-out cat {local_tmp}",
                shell=True, capture_output=True, timeout=10,
            )
            subprocess.run(
                f"adb {self.device_id} shell rm {local_tmp}",
                shell=True, capture_output=True,
            )
            if result.stdout:
                frame = cv2.imdecode(
                    np.frombuffer(result.stdout, dtype=np.uint8),
                    cv2.IMREAD_COLOR,
                )
                return frame
            return None
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            print(f"[ScreenshotCollector] capture_frame 失败: {e}")
            return None

    def get_screen_resolution(self) -> tuple[int, int]:
        """获取设备屏幕分辨率"""
        result = subprocess.run(
            f"adb {self.device_id} shell wm size",
            shell=True, capture_output=True, text=True
        )
        output = result.stdout.strip()
        if "x" in output:
            resolution = output.split(":")[-1].strip()
            width, height = map(int, resolution.split("x"))
            return width, height
        return 1080, 1920


if __name__ == "__main__":
    DEVICE_ID = "3DJ0224910000759"
    collector = ScreenshotCollector(
        output_dir="templates/workspace",
        device_id=DEVICE_ID
    )

    print(f"设备分辨率: {collector.get_screen_resolution()}")

    # 单张测试截图
    print("\n截取测试图...")
    path = collector.capture("test_001.png")
    print(f"已保存: {path}")

    # 读取并验证截图
    img = cv2.imread(path)
    if img is not None:
        h, w = img.shape[:2]
        print(f"截图尺寸: {w}x{h}")
        print("截图验证通过")
    else:
        print("截图读取失败")
