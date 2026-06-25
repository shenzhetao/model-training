"""
GameAssistant - PC 端游戏辅助脚本

功能：
- 通过 ADB 连接 Android 设备
- 截图并使用 YOLO 模型进行目标检测
- 根据检测结果执行游戏操作

使用方法：
1. 安装依赖：pip install ultralytics opencv-python pillow
2. 下载训练好的模型文件（.pt）
3. 修改下方配置参数
4. 运行脚本：python game_assistant.py
"""

import os
import time
import cv2
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# ============================================================
# 配置区域 - 根据你的游戏修改这些参数
# ============================================================

# 模型路径（下载训练好的模型后修改此路径）
MODEL_PATH = "best.pt"

# ADB 配置
ADB_HOST = "127.0.0.1"      # ADB 服务器地址（模拟器用 localhost）
ADB_PORT = "5555"            # ADB 端口（模拟器默认 5555，真机通过 USB）
DEVICE_SERIAL = None         # 设备序列号，为 None 则自动选择第一个已连接设备

# 推理配置
CONFIDENCE_THRESHOLD = 0.4  # 置信度阈值，低于此值的检测结果将被忽略
SCREEN_WIDTH = 1920         # 屏幕宽度（用于坐标映射）
SCREEN_HEIGHT = 1080        # 屏幕高度

# 游戏操作配置
CHECK_INTERVAL = 0.5        # 检测间隔（秒），值越小检测越频繁但越耗资源
AUTO_ATTACK_ENABLED = True   # 是否启用自动攻击
AUTO_MOVE_ENABLED = True     # 是否启用自动移动

# 类别配置（根据你的训练类别修改）
CLASS_CONFIG = {
    # "类别名称": {
    #     "id": YOLO模型中的类别ID（从0开始）,
    #     "enabled": 是否启用对此类别的响应,
    #     "action": 响应动作（见 ActionType）
    # }
    "player": {
        "id": 0,
        "enabled": False,  # 检测玩家本身一般不需要响应
        "action": "none"
    },
    "enemy": {
        "id": 1,
        "enabled": True,
        "action": "attack"  # 发现敌人时攻击
    },
    "coin": {
        "id": 2,
        "enabled": True,
        "action": "collect"  # 发现金币时移动过去
    },
    "boss": {
        "id": 3,
        "enabled": True,
        "action": "attack"   # 发现BOSS时攻击
    },
}

# ============================================================
# ADB 通信模块
# ============================================================

class ADBDevice:
    """ADB 设备通信类"""
    
    def __init__(self, serial: Optional[str] = None, host: str = "127.0.0.1", port: str = "5555"):
        self.serial = serial
        self.host = host
        self.port = port
        
    def _build_cmd(self, *args) -> List[str]:
        """构建 ADB 命令"""
        cmd = ["adb"]
        if self.serial:
            cmd.extend(["-s", self.serial])
        elif self.host and self.port:
            cmd.extend(["-H", self.host, "-P", self.port])
        cmd.extend(args)
        return cmd
    
    def _run(self, *args, check: bool = True) -> Tuple[int, str, str]:
        """执行 ADB 命令"""
        import subprocess
        cmd = self._build_cmd(*args)
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timeout"
        except FileNotFoundError:
            return -1, "", "adb not found"
    
    def is_connected(self) -> bool:
        """检查设备是否连接"""
        code, stdout, _ = self._run("get-state", check=False)
        return code == 0 and "device" in stdout
    
    def get_resolution(self) -> Tuple[int, int]:
        """获取设备屏幕分辨率"""
        code, stdout, _ = self._run("shell", "wm", "size", check=False)
        if code == 0 and stdout.strip():
            # 解析输出，格式如 "Physical size: 1080x2400"
            size_str = stdout.split(":")[-1].strip()
            if "x" in size_str:
                parts = size_str.split("x")
                return int(parts[0]), int(parts[1])
        return 0, 0
    
    def screenshot(self) -> Optional[np.ndarray]:
        """截取屏幕并返回 BGR numpy 数组"""
        # 方法1：使用 exec-out 直接获取（推荐，较快）
        code, stdout, stderr = self._run("shell", "screencap", "-p", "/sdcard/screen.png", check=False)
        if code != 0:
            return None
            
        code, stdout, _ = self._run("shell", "exec-out", "cat", "/sdcard/screen.png", check=False)
        if code != 0 or not stdout:
            return None
        
        # 将 bytes 转换为 numpy 数组
        try:
            if isinstance(stdout, str):
                stdout = stdout.encode('latin1')
            nparr = np.frombuffer(stdout, dtype=np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None
    
    def tap(self, x: int, y: int) -> bool:
        """点击指定坐标"""
        code, _, _ = self._run("shell", "input", "tap", str(x), str(y), check=False)
        return code == 0
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """滑动操作"""
        code, _, _ = self._run(
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration),
            check=False
        )
        return code == 0
    
    def press_back(self) -> bool:
        """按返回键"""
        code, _, _ = self._run("shell", "input", "keyevent", "KEYCODE_BACK", check=False)
        return code == 0
    
    def press_home(self) -> bool:
        """按 Home 键"""
        code, _, _ = self._run("shell", "input", "keyevent", "KEYCODE_HOME", check=False)
        return code == 0


# ============================================================
# 检测结果数据结构
# ============================================================

@dataclass
class Detection:
    """检测到的目标"""
    class_name: str
    class_id: int
    confidence: float
    x: int  # 中心点 x
    y: int  # 中心点 y
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """返回 (x1, y1, x2, y2) 格式"""
        x1 = max(0, self.x - self.width // 2)
        y1 = max(0, self.y - self.height // 2)
        x2 = self.x + self.width // 2
        y2 = self.y + self.height // 2
        return (x1, y1, x2, y2)


class ActionType(Enum):
    """动作类型"""
    NONE = "none"
    ATTACK = "attack"
    COLLECT = "collect"
    MOVE_TO = "move_to"
    TAP = "tap"


# ============================================================
# 游戏辅助核心类
# ============================================================

class GameAssistant:
    """游戏辅助主类"""
    
    def __init__(self, model_path: str, device: ADBDevice):
        self.model_path = model_path
        self.device = device
        self.model = None
        self.class_names = []
        self.last_action_time = {}  # 记录上次动作时间，避免频繁操作
        
    def load_model(self):
        """加载 YOLO 模型"""
        try:
            from ultralytics import YOLO
            print(f"[初始化] 正在加载模型: {self.model_path}")
            self.model = YOLO(self.model_path)
            
            # 获取类别名称
            if hasattr(self.model, 'names'):
                self.class_names = list(self.model.names.values())
            else:
                # 如果模型没有类别名称，使用配置中的
                self.class_names = list(CLASS_CONFIG.keys())
                
            print(f"[初始化] 模型加载成功，共 {len(self.class_names)} 个类别: {self.class_names}")
            return True
        except Exception as e:
            print(f"[错误] 模型加载失败: {e}")
            return False
    
    def detect(self, image: np.ndarray) -> List[Detection]:
        """使用模型检测目标"""
        if self.model is None:
            return []
        
        try:
            # 执行推理
            results = self.model.predict(
                image, 
                conf=CONFIDENCE_THRESHOLD,
                verbose=False,
                imgsz=640
            )
            
            detections = []
            for r in results:
                boxes = r.boxes
                if boxes is None:
                    continue
                    
                for box in boxes:
                    # 获取边界框坐标
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    
                    # 获取类别名称
                    if cls_id < len(self.class_names):
                        cls_name = self.class_names[cls_id]
                    else:
                        cls_name = f"class_{cls_id}"
                    
                    # 计算中心点和尺寸
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    width = int(x2 - x1)
                    height = int(y2 - y1)
                    
                    detections.append(Detection(
                        class_name=cls_name,
                        class_id=cls_id,
                        confidence=conf,
                        x=center_x,
                        y=center_y,
                        width=width,
                        height=height
                    ))
            
            return detections
            
        except Exception as e:
            print(f"[错误] 检测失败: {e}")
            return []
    
    def should_act(self, class_name: str, cooldown: float = 1.0) -> bool:
        """检查是否应该执行动作（有冷却时间）"""
        current_time = time.time()
        last_time = self.last_action_time.get(class_name, 0)
        
        if current_time - last_time >= cooldown:
            self.last_action_time[class_name] = current_time
            return True
        return False
    
    def execute_action(self, detection: Detection, screen_width: int, screen_height: int):
        """执行响应动作"""
        if not AUTO_ATTACK_ENABLED and not AUTO_MOVE_ENABLED:
            return
            
        # 获取类别配置
        config = CLASS_CONFIG.get(detection.class_name)
        if not config or not config.get("enabled", False):
            return
        
        action = config.get("action", "none")
        
        # 坐标转换：将图像坐标映射到实际屏幕坐标
        img_height, img_width = screen_height, screen_width  # 检测图像的尺寸
        scale_x = SCREEN_WIDTH / img_width if img_width > 0 else 1
        scale_y = SCREEN_HEIGHT / img_height if img_height > 0 else 1
        
        target_x = int(detection.x * scale_x)
        target_y = int(detection.y * scale_y)
        
        # 根据动作类型执行
        if action == "attack":
            if self.should_act(f"attack_{detection.class_name}", cooldown=0.5):
                print(f"[攻击] {detection.class_name} (置信度: {detection.confidence:.2f})")
                self.device.tap(target_x, target_y)
                
        elif action == "collect":
            if self.should_act(f"collect_{detection.class_name}", cooldown=0.3):
                print(f"[采集] {detection.class_name} (坐标: {target_x}, {target_y})")
                # 先移动到目标位置
                self.device.tap(target_x, target_y)
                
        elif action == "tap":
            if self.should_act(f"tap_{detection.class_name}"):
                print(f"[点击] {detection.class_name}")
                self.device.tap(target_x, target_y)
    
    def run(self):
        """主循环"""
        print("\n" + "="*50)
        print("         游戏辅助已启动")
        print("="*50)
        print(f"模型: {self.model_path}")
        print(f"检测间隔: {CHECK_INTERVAL}秒")
        print(f"置信度阈值: {CONFIDENCE_THRESHOLD}")
        print("="*50)
        print("按 Ctrl+C 停止\n")
        
        frame_count = 0
        start_time = time.time()
        
        try:
            while True:
                loop_start = time.time()
                
                # 截图
                screenshot = self.device.screenshot()
                if screenshot is None:
                    print("[警告] 截图失败，等待重试...")
                    time.sleep(1)
                    continue
                
                # 检测
                detections = self.detect(screenshot)
                
                # 打印检测结果（每10帧打印一次）
                frame_count += 1
                if frame_count % 10 == 0 and detections:
                    fps = 10 / (time.time() - loop_start)
                    print(f"[检测] FPS: {fps:.1f} | 发现 {len(detections)} 个目标")
                    for d in detections[:5]:  # 最多显示5个
                        print(f"    - {d.class_name}: {d.confidence:.2f} @ ({d.x}, {d.y})")
                
                # 执行动作
                h, w = screenshot.shape[:2]
                for detection in detections:
                    self.execute_action(detection, w, h)
                
                # 控制检测频率
                elapsed = time.time() - loop_start
                sleep_time = max(0.1, CHECK_INTERVAL - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n\n[退出] 游戏辅助已停止")
        except Exception as e:
            print(f"[错误] 运行异常: {e}")
            raise


# ============================================================
# 便捷启动函数
# ============================================================

def auto_connect_device() -> Optional[ADBDevice]:
    """自动连接设备"""
    import subprocess
    
    # 首先启动 ADB 服务器
    subprocess.run(["adb", "start-server"], capture_output=True)
    
    # 获取已连接设备
    result = subprocess.run(
        ["adb", "devices"], 
        capture_output=True, 
        text=True
    )
    
    lines = result.stdout.strip().split("\n")
    devices = []
    
    for line in lines[1:]:  # 跳过标题行
        line = line.strip()
        if line and "device" in line:
            parts = line.split()
            if len(parts) >= 2:
                devices.append(parts[0])
    
    if not devices:
        print("[错误] 未检测到已连接的 Android 设备")
        print("请确保：")
        print("  1. 手机已开启 USB 调试")
        print("  2. 已通过 USB 连接电脑")
        print("  3. 已在手机上允许 USB 调试授权")
        return None
    
    serial = devices[0]
    print(f"[连接] 找到设备: {serial}")
    
    device = ADBDevice(serial=serial)
    
    # 验证连接
    if not device.is_connected():
        print("[错误] 设备连接验证失败")
        return None
    
    # 获取分辨率
    width, height = device.get_resolution()
    print(f"[连接] 屏幕分辨率: {width}x{height}")
    
    return device


def main():
    """主入口"""
    print("\n" + "="*50)
    print("    GameAssistant - YOLO 游戏辅助启动器")
    print("="*50 + "\n")
    
    # 1. 连接设备
    print("[1/3] 连接 Android 设备...")
    device = auto_connect_device()
    if not device:
        input("\n按回车键退出...")
        return
    print("[1/3] 设备连接成功!\n")
    
    # 2. 加载模型
    print("[2/3] 加载 YOLO 模型...")
    if not os.path.exists(MODEL_PATH):
        print(f"[错误] 模型文件不存在: {MODEL_PATH}")
        print("\n请先在平台上训练模型，然后下载 best.pt 文件到此目录")
        input("\n按回车键退出...")
        return
    
    assistant = GameAssistant(MODEL_PATH, device)
    if not assistant.load_model():
        input("\n按回车键退出...")
        return
    print("[2/3] 模型加载成功!\n")
    
    # 3. 运行辅助
    print("[3/3] 启动游戏辅助...")
    print("[3/3] 辅助已启动!\n")
    
    assistant.run()


if __name__ == "__main__":
    main()
