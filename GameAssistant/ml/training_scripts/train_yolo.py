"""
YOLOv8 目标检测模型训练脚本
基于游戏截图数据训练 UI 元素检测模型

使用前请确认：
  1. 已激活虚拟环境（game-helper/venv 或单独的 venv）
  2. 已安装 ultralytics、torch、torchvision
  3. 数据已采集并标注（datasets/raw/ 下有图片和 .txt 标签）
  4. 已运行 scripts/split_dataset.py 划分数据集
"""
import os
import re
from pathlib import Path
from ultralytics import YOLO
import torch


def _rewrite_dataset_yaml(data_yaml: str) -> None:
    """把 dataset.yaml 里的 path 字段改写为绝对路径。

    原因：ultralytics 8.x 解析 yaml 时，path 字段是相对训练时 CWD 的，
    而不是相对 yaml 文件本身。如果项目位置固定就不会有歧义，
    但为了避免在不同工作目录下跑训练时踩坑，启动时强制改成绝对路径。
    """
    yaml_path = Path(data_yaml).resolve()
    if not yaml_path.exists():
        return  # 让后面的训练自己报错

    datasets_abs = (yaml_path.parent / "datasets").resolve()
    text = yaml_path.read_text(encoding="utf-8")
    # 把以 path: 开头的行改写为绝对路径
    new_text, n = re.subn(
        r"^path:\s*.*$",
        f"path: {datasets_abs.as_posix()}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n:
        yaml_path.write_text(new_text, encoding="utf-8")
        print(f"[INFO] dataset.yaml 的 path 已改写为绝对路径: {datasets_abs}")


def train_yolo(
    data_yaml: str = "ml/yolo/dataset.yaml",
    model_size: str = "n",
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 16,
    device: str | None = None,
    patience: int = 20,
    **kwargs,
):
    """
    训练 YOLO 模型

    参数:
    - data_yaml: 数据集配置文件路径
    - model_size: n=nano(最快), s=small(推荐), m=medium, l=large
    - epochs: 训练轮数，默认 100
    - imgsz: 输入图像尺寸，默认 640
    - batch: 批次大小，显存不足可调小
    - device: 训练设备，"0"=GPU0，"cpu"=CPU
    - patience: 早停轮数，验证集 mAP 多少轮不提升则停止
    """
    _rewrite_dataset_yaml(data_yaml)

    if device is None:
        device = "0" if torch.cuda.is_available() else "cpu"

    print(f"GPU 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    print(f"开始训练 YOLOv8{model_size}")
    print(f"数据集: {data_yaml}")
    print(f"训练轮数: {epochs}, 批次大小: {batch}, 输入尺寸: {imgsz}")
    print("=" * 50)

    model = YOLO(f"yolov8{model_size}.pt")

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project="ml/runs",
        name="yolo_game_ui",
        exist_ok=True,
        save=True,
        save_period=10,
        patience=patience,
        verbose=True,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.15,          # 提升到 0.15，数据少必须靠 augmentation
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        warmup_epochs=3,
        weight_decay=0.0005,
        **kwargs,            # 传入额外参数（如 mixup=0.15）
    )

    best_model_path = os.path.join(results.save_dir, "weights", "best.pt")
    print(f"\n训练完成！最佳模型: {best_model_path}")

    metrics = model.val(data=data_yaml)
    print(f"\n=== 验证集评估结果 ===")
    print(f"mAP50:    {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall:   {metrics.box.mr:.4f}")

    # 复制最佳模型到 weights 目录
    weights_dir = os.path.join(os.path.dirname(__file__), "..", "weights", "yolo")
    os.makedirs(weights_dir, exist_ok=True)
    import shutil
    final_path = os.path.join(weights_dir, "best.pt")
    shutil.copy(best_model_path, final_path)
    print(f"\n模型已复制到: {final_path}")

    return best_model_path


if __name__ == "__main__":
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    train_yolo(
        data_yaml="ml/yolo/dataset.yaml",
        model_size="n",
        epochs=50,       # 数据少（50 张起步），减半防止过拟合
        batch=8,         # batch 调小
        device=device,
        imgsz=640,
        mixup=0.15,      # 数据少必须开，yolo.train() 参数通过 kwargs 传入
    )
