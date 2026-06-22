"""ADB 设备控制封装，支持截图、设备检测和重试机制。"""
import io
import time
import subprocess
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from app.config import settings


@dataclass
class ADBDevice:
    """ADB 设备信息。"""
    device_id: str
    state: str  # 'device', 'offline', 'unauthorized'
    resolution: tuple[int, int]
    model: Optional[str] = None
    product: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self.state == "device"


class ADBWrapper:
    """Android Debug Bridge 封装，提供截图和设备管理功能。

    特性：
    - 3 次重试 + 指数退避
    - 无设备时返回友好的错误信息
    - 支持截图直接返回 BGR ndarray
    """

    MAX_RETRIES = 3
    BASE_DELAY = 0.5  # seconds
    TIMEOUT = 15  # seconds per command

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.adb_host = settings.ADB_HOST
        self.adb_port = settings.ADB_PORT

    def _build_cmd(self, *args: str) -> list[str]:
        """构建 ADB 命令。"""
        cmd = ["adb"]
        if self.adb_host != "localhost":
            cmd.extend(["-H", self.adb_host, "-P", str(self.adb_port)])
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """执行 ADB 命令。"""
        cmd = self._build_cmd(*args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.TIMEOUT,
            check=check,
        )

    def _run_with_retry(self, *args: str) -> subprocess.CompletedProcess:
        """执行 ADB 命令，失败自动重试（指数退避）。"""
        for attempt in range(self.MAX_RETRIES):
            try:
                result = self._run(*args)
                if result.returncode == 0:
                    return result
                # ADB server not started — auto-start and retry once
                if "not found" in result.stderr or "daemon not running" in result.stderr:
                    self._run("start-server")
                    if attempt == 0:
                        continue
            except subprocess.TimeoutExpired:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.BASE_DELAY * (2 ** attempt))
                    continue
                raise
            except subprocess.CalledProcessError:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.BASE_DELAY * (2 ** attempt))
                    continue
                raise
        return self._run(*args)

    # ── 公开 API ──────────────────────────────────────────────

    def check_adb_available(self) -> bool:
        """检测 adb 命令是否可用。"""
        try:
            self._run("version", check=False)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def check_server_running(self) -> bool:
        """检测 ADB server 是否运行。"""
        try:
            result = self._run("get-state", check=False)
            return result.returncode == 0
        except Exception:
            return False

    def list_devices(self) -> list[ADBDevice]:
        """列出所有已连接的 ADB 设备。"""
        try:
            result = self._run("devices", "-l", check=False)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            raise RuntimeError(f"ADB 命令不可用: {e}")

        devices = []
        lines = result.stdout.strip().split("\n")
        for line in lines[1:]:  # skip header
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            device_id = parts[0]
            state = parts[1]

            resolution = (0, 0)
            model = None
            product = None

            # Parse extra info: product:xxx model:xxx device:xxx
            for part in parts[2:]:
                if part.startswith("product:"):
                    product = part.split(":", 1)[1]
                elif part.startswith("model:"):
                    model = part.split(":", 1)[1].replace("_", " ")

            # Get real resolution
            try:
                size_result = self._run("-s", device_id, "shell", "wm", "size", check=False)
                raw = size_result.stdout.strip()
                if ":" in raw:
                    size_str = raw.split(":")[-1].strip()
                else:
                    size_str = raw.strip()
                if "x" in size_str:
                    w, h = map(int, size_str.split("x"))
                    resolution = (w, h)
            except Exception:
                pass

            devices.append(ADBDevice(
                device_id=device_id,
                state=state,
                resolution=resolution,
                model=model,
                product=product,
            ))

        return devices

    def get_connected_device(self) -> Optional[ADBDevice]:
        """返回第一个已连接的设备。"""
        devices = self.list_devices()
        for d in devices:
            if d.is_connected:
                return d
        return None

    def capture_frame(self) -> np.ndarray:
        """截取当前设备屏幕，返回 BGR ndarray。

        使用 exec-out 直接通过 stdout 传输原始 PNG 数据，
        避免临时文件 I/O，延迟更低。
        """
        local_tmp = "/sdcard/_tmp_screen.png"

        def _capture() -> np.ndarray:
            self._run_with_retry("shell", "screencap", "-p", local_tmp)
            result = self._run_with_retry("shell", "exec-out", "cat", local_tmp)
            self._run("shell", "rm", "-f", local_tmp, check=False)

            if not result.stdout:
                raise RuntimeError("ADB 截图返回空数据，可能设备未连接或屏幕截图失败")

            raw = result.stdout.encode("latin1") if isinstance(result.stdout, str) else result.stdout
            frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError("无法解码截图数据，设备可能不支持 screencap")
            return frame

        for attempt in range(self.MAX_RETRIES):
            try:
                return _capture()
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.BASE_DELAY * (2 ** attempt))
                    continue
                raise RuntimeError(
                    f"截图失败（已重试 {self.MAX_RETRIES} 次）: {e}"
                ) from e

        raise RuntimeError("截图失败")

    def capture_to_bytes(self) -> bytes:
        """截取屏幕并返回 PNG 原始字节。"""
        frame = self.capture_frame()
        _, buffer = cv2.imencode(".png", frame)
        return buffer.tobytes()

    def get_screen_resolution(self, device_id: Optional[str] = None) -> tuple[int, int]:
        """获取指定设备（或当前设备）的屏幕分辨率。"""
        cmd_list = ["shell", "wm", "size"]
        if device_id:
            cmd_list = ["-s", device_id] + cmd_list
        try:
            result = self._run_with_retry(*cmd_list)
        except Exception:
            return (0, 0)

        raw = result.stdout.strip()
        if ":" in raw:
            size_str = raw.split(":")[-1].strip()
        else:
            size_str = raw.strip()
        if "x" in size_str:
            w, h = map(int, size_str.split("x"))
            return (w, h)
        return (0, 0)

    def tap(self, x: int, y: int) -> None:
        """点击屏幕坐标。"""
        self._run_with_retry("shell", "input", "tap", str(x), str(y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """滑动屏幕。"""
        self._run_with_retry(
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms)
        )
