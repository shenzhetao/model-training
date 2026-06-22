"""
模板采集脚本
一次性采集 4 个模板类（btn_attack / btn_skill / hp_bar_player / dialog_next），
存到 templates/ 目录，供 TemplateMatcher 使用。

采集流程：
  1. 脚本截取全屏，用户按回车确认
  2. 按 game.yaml 中的 ROI 裁剪出模板区域
  3. 保存到 templates/{cls}/{state}.png

使用前提：
  - 已连接 adb 设备
  - config/game.yaml 已配置 ui_rois 和参考分辨率
"""
import os
import sys

# venv 重定向（与 collect_for_yolo.py 保持一致）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_VENV_PY = os.path.join(_PROJECT_ROOT, "..", "game-helper", "venv", "Scripts", "python.exe")
_VENV_PY = os.path.normpath(_VENV_PY)


def _in_venv():
    return os.path.normpath(sys.executable).lower() == _VENV_PY.lower()


if not _in_venv() and os.path.isfile(_VENV_PY):
    import subprocess
    ret = subprocess.call([_VENV_PY, os.path.abspath(__file__)] + sys.argv[1:])
    sys.exit(ret)


_SCRIPT_DIR = _PROJECT_ROOT
sys.path.insert(0, os.path.join(_SCRIPT_DIR, "pc", "core"))
os.chdir(_SCRIPT_DIR)

import cv2
import json
import yaml
from pathlib import Path

from screenshot_collector import ScreenshotCollector


# 模板采集规格：(cls_name, [(state_name, 提示文本), ...], 是否多状态采集)
TEMPLATE_SPECS = [
    ("btn_attack", [
        ("normal", "右下角攻击键完全可见"),
    ]),
    ("btn_skill", [
        # skill1 ~ skill8，按实际槽位数量由 game.yaml 的 skill_slots.count 决定
        # 默认 8 个槽位，每个采集一张
    ]),
    ("hp_bar_player", [
        ("normal", "左上角玩家血条完整可见（满血）"),
    ]),
    ("dialog_next", [
        ("with_arrow", "和 NPC 对话，看到 ▶ 箭头"),
    ]),
]


def _build_skill_specs(count: int) -> list[tuple[str, str]]:
    return [(f"skill{i}", f"第 {i} 个技能槽位可见") for i in range(1, count + 1)]


def main():
    # 加载配置
    config_path = Path("config/game.yaml")
    if not config_path.exists():
        print(f"错误：配置文件不存在 {config_path}")
        print("请先创建 config/game.yaml")
        return

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with open("config/devices.json", encoding="utf-8") as f:
        devices = json.load(f)

    ref_w, ref_h = devices["reference_resolution"]
    skill_count = config["game"]["skill_slots"]["count"]
    skill_spec = ("btn_skill", _build_skill_specs(skill_count))
    # 替换 TEMPLATE_SPECS 中的 skill 项
    specs = [s for s in TEMPLATE_SPECS if s[0] != "btn_skill"]
    specs.insert(1, skill_spec)  # btn_skill 放第二位

    # 初始化截图采集器
    DEVICE_ID = os.environ.get("ADB_DEVICE", "")
    if not DEVICE_ID:
        print("错误：请设置环境变量 ADB_DEVICE（如 set ADB_DEVICE=3DJ0224910000759）")
        print("或在脚本中直接修改 DEVICE_ID 变量")
        return
    collector = ScreenshotCollector(
        output_dir="templates",
        device_id=DEVICE_ID,
    )

    # 获取分辨率
    width, height = collector.get_screen_resolution()
    print(f"设备分辨率: {width}x{height}")
    print(f"参考分辨率: {ref_w}x{ref_h}")
    print()

    # 计算缩放因子（用于将 game.yaml 的相对 ROI 还原为当前设备上的绝对坐标）
    scale_x = width / ref_w
    scale_y = height / ref_h
    print(f"缩放因子: ({scale_x:.3f}x, {scale_y:.3f}y)")
    print()

    output_root = Path("templates")
    total_specs = sum(len(states) for _, states in specs)

    print(f"共 {len(specs)} 个类别，{total_specs} 张模板待采集")
    print("=" * 50)
    print("操作说明：")
    print("  1. 按提示操作手机到指定场景")
    print("  2. 按回车截取模板")
    print("  3. 继续下一张，直到全部完成")
    print("  Ctrl+C 可中途退出，已保存的不受影响")
    print("=" * 50)
    print()

    idx = 0
    try:
        for cls_name, states in specs:
            cls_dir = output_root / cls_name
            cls_dir.mkdir(parents=True, exist_ok=True)

            # 取 ROI（相对坐标），转当前设备的绝对坐标
            if cls_name == "btn_skill":
                rel_roi = config["game"]["skill_slots"]["bar_roi"]
            else:
                rel_roi = config["game"]["ui_rois"][cls_name]["roi"]

            rx, ry, rw, rh = rel_roi
            abs_x = int(rx * width)
            abs_y = int(ry * height)
            abs_w = int(rw * width)
            abs_h = int(rh * height)

            print(f"\n[类别] {cls_name}")
            print(f"  ROI（绝对像素）: ({abs_x}, {abs_y}, {abs_w}, {abs_h})")
            print(f"  预期保存到: {cls_dir}/")

            for state_name, hint in states:
                idx += 1
                print(f"\n  [{idx}/{total_specs}] {cls_name}/{state_name}")
                print(f"  请操作：{hint}")
                input("  准备就绪按回车截取...")

                # 截全屏
                frame = collector.capture_frame()
                if frame is None:
                    print(f"  ⚠️ 截图失败，跳过")
                    continue

                # 裁剪 ROI
                tmpl = frame[abs_y:abs_y + abs_h, abs_x:abs_x + abs_w]
                if tmpl.size == 0:
                    print(f"  ⚠️ ROI 区域为空，跳过")
                    continue

                save_path = cls_dir / f"{state_name}.png"
                cv2.imwrite(str(save_path), tmpl)
                print(f"  ✓ 已保存：{save_path}  ({tmpl.shape[1]}x{tmpl.shape[0]})")

    except KeyboardInterrupt:
        print("\n\n⚠ 中途退出，已采集的内容不受影响")

    print()
    print("=" * 50)
    print("模板采集完成！")
    print(f"模板目录：{output_root}")
    print()
    print("验证方法：")
    print("  python -c \"from pc.core.template_matcher import TemplateMatcher; "
          "from pc.core.device_profile import DeviceProfile; "
          "from pc.core.screenshot_collector import ScreenshotCollector as SC; "
          "d=DeviceProfile(); "
          "m=TemplateMatcher(Path('templates'), d); "
          "f=SC().capture_frame(); "
          "print(m.match_all(f))\"")
    print()
    print("下一步：运行 scripts/collect_for_yolo.py 采集 YOLO 数据")


if __name__ == "__main__":
    main()
