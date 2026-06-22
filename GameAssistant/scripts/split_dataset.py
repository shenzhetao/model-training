"""
数据集划分脚本
将标注好的原始数据按比例划分为训练集和验证集

支持 4 类场景：
  1. datasets/raw_yolo/ — YOLO 数据（标注后用 scripts/split_dataset.py 划分）
  2. datasets/raw/    — 保留旧路径兼容（LabelImg 直接输出到此处）
"""
import os
import shutil
import random
import yaml

_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_SCRIPT_DIR)


def _get_class_count(data_yaml: str = "ml/yolo/dataset.yaml") -> int:
    """从 dataset.yaml 自动读取类别数量，不再硬编码。"""
    if os.path.exists(data_yaml):
        with open(data_yaml, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("nc", 1)
    return 1


def split_dataset(
    raw_dir: str = "datasets/raw_yolo",
    output_dir: str = "ml/yolo/datasets",
    train_ratio: float = 0.9,
    seed: int = 42,
):
    """
    将标注好的数据划分为训练集和验证集

    raw_dir: 包含截图和标注文件的目录（LabelImg 输出）
    output_dir: 输出目录，生成 images/train, images/val, labels/train, labels/val
    train_ratio: 训练集比例，默认 0.9（90% 训练，10% 验证）
    """
    random.seed(seed)
    nc = _get_class_count()
    print(f"[INFO] 自动检测到 nc={nc}，开始划分数据...")

    for subset in ["train", "val"]:
        os.makedirs(os.path.join(output_dir, "images", subset), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "labels", subset), exist_ok=True)

    # 兼容两类目录结构：
    #   1. datasets/raw/*.png + *.txt（所有图平铺）
    #   2. datasets/raw/{label}/*.png + *.txt（按类别分子目录，collect_for_yolo.py 的默认行为）
    all_images = []
    for entry in os.listdir(raw_dir):
        full_path = os.path.join(raw_dir, entry)
        if os.path.isfile(full_path) and entry.lower().endswith(('.jpg', '.png', '.jpeg')):
            all_images.append(entry)
        elif os.path.isdir(full_path):
            for f in os.listdir(full_path):
                if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                    all_images.append(os.path.join(entry, f))

    if not all_images:
        print(f"错误：在 {raw_dir} 下没找到任何图片（.jpg/.png/.jpeg）")
        return

    random.shuffle(all_images)

    split_idx = int(len(all_images) * train_ratio)
    train_files = all_images[:split_idx]
    val_files = all_images[split_idx:]

    for subset, files in [("train", train_files), ("val", val_files)]:
        for f in files:
            base = os.path.splitext(f)[0]
            img_src = os.path.join(raw_dir, f)
            label_src = os.path.join(raw_dir, base + ".txt")

            img_dst = os.path.join(output_dir, "images", subset, os.path.basename(f))
            label_dst = os.path.join(output_dir, "labels", subset, os.path.basename(base) + ".txt")

            shutil.copy(img_src, img_dst)
            if os.path.exists(label_src):
                shutil.copy(label_src, label_dst)

    print(f"训练集: {len(train_files)} 张")
    print(f"验证集: {len(val_files)} 张")
    print(f"输出目录: {output_dir}")
    print("\n数据集划分完成！接下来运行训练脚本 ml/training_scripts/train_yolo.py")


if __name__ == "__main__":
    split_dataset()
