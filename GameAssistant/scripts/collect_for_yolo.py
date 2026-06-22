"""
YOLO 数据采集脚本
用于按游戏状态批量采集截图，为 YOLO 模型训练准备原始数据
"""
import os
import sys

# 强制使用 venv 里的 Python（避免系统 Python 没有依赖）
# venv 路径：<项目根>/game-helper/venv
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_VENV_PY = os.path.join(_PROJECT_ROOT, "..", "game-helper", "venv", "Scripts", "python.exe")
_VENV_PY = os.path.normpath(_VENV_PY)

# 任何非 venv 的 Python（系统 Python、Microsoft Store 别名等）都重定向到 venv
def _in_venv():
    return os.path.normpath(sys.executable).lower() == _VENV_PY.lower()

if not _in_venv() and os.path.isfile(_VENV_PY):
    print(f"[start_env] 检测到非 venv 解释器: {sys.executable}")
    print(f"[start_env] 切换到 venv: {_VENV_PY}")
    import subprocess
    ret = subprocess.call([_VENV_PY, os.path.abspath(__file__)] + sys.argv[1:])
    sys.exit(ret)

_SCRIPT_DIR = _PROJECT_ROOT
sys.path.insert(0, os.path.join(_SCRIPT_DIR, "pc", "core"))
os.chdir(_SCRIPT_DIR)

from screenshot_collector import ScreenshotCollector

DEVICE_ID = "3DJ0224910000759"


def main():
    collector = ScreenshotCollector(
        output_dir=os.path.join(_SCRIPT_DIR, "datasets", "raw_yolo"),
        device_id=DEVICE_ID
    )

    print(f"设备分辨率: {collector.get_screen_resolution()}")
    print()

    # 可根据实际游戏修改以下类别名称和数量
    scenarios = [
        # 第一期只有 1 个 YOLO 场景：quest_marker（NPC 头顶 ?/! 标记）
        # 其他 4 类用模板匹配，无需 YOLO 采集
        ("quest_marker", 50),   # 起步 50 张，建议总采集 80-100 张
    ]
    total = sum(count for _, count in scenarios)
    print(f"共 {len(scenarios)} 个类别，预计采集 {total} 张截图")
    print("采集说明：")
    print("  - quest_marker：到有 NPC（头顶带 ? 或 ! 标记）的区域")
    print("  - 每张图可能有 1-3 个标记，尽量覆盖不同场景（野外/城内/副本）")
    print("=" * 50)

    for i, (label, count) in enumerate(scenarios):
        print(f"\n[{i+1}/{len(scenarios)}] >>> 请操作到【{label}】场景，然后按回车键开始采集 {count} 张")
        input("按回车键开始...")
        collector.capture_with_state(label, count=count)
        print(f"  完成 {count} 张截图，已保存到 datasets/raw_yolo/{label}/")

    print("\n" + "=" * 50)
    print("全部采集完成！")
    print("接下来请使用 LabelImg 进行数据标注（详见 YOLO使用说明.md）")


if __name__ == "__main__":
    main()
