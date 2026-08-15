import json
import random
import shutil
import argparse
from pathlib import Path
import yaml


def split_dataset(coco_json_path, images_dir, output_dir, val_ratio=0.2, seed=42):
    with open(coco_json_path) as f:
        coco = json.load(f)

    images = coco["images"]
    random.seed(seed)
    shuffled = images[:]
    random.shuffle(shuffled)

    split_idx = int(len(shuffled) * (1 - val_ratio))
    train_images = shuffled[:split_idx]
    val_images = shuffled[split_idx:]

    anns_by_image = {}
    for ann in coco["annotations"]:
        anns_by_image.setdefault(ann["image_id"], []).append(ann)

    categories = sorted(coco["categories"], key=lambda c: c["id"])
    cat_id_to_yolo_idx = {cat["id"]: idx for idx, cat in enumerate(categories)}

    def write_split(split_name, split_images):
        img_out_dir = output_dir / "images" / split_name
        label_out_dir = output_dir / "labels" / split_name
        img_out_dir.mkdir(parents=True, exist_ok=True)
        label_out_dir.mkdir(parents=True, exist_ok=True)

        for img in split_images:
            src_path = images_dir / Path(img["file_name"]).name
            dst_path = img_out_dir / Path(img["file_name"]).name
            if not src_path.exists():
                print(f"ADVARSEL: fant ikke {src_path}, hopper over")
                continue
            shutil.copy2(src_path, dst_path)

            base_name = Path(img["file_name"]).stem
            label_path = label_out_dir / f"{base_name}.txt"
            lines = []
            for ann in anns_by_image.get(img["id"], []):
                x, y, w, h = ann["bbox"]
                x_c = (x + w / 2) / img["width"]
                y_c = (y + h / 2) / img["height"]
                w_n = w / img["width"]
                h_n = h / img["height"]
                yolo_idx = cat_id_to_yolo_idx[ann["category_id"]]
                lines.append(f"{yolo_idx} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}")
            with open(label_path, "w") as f:
                f.write("\n".join(lines))

        return len(split_images)

    n_train = write_split("train", train_images)
    n_val = write_split("val", val_images)

    data_yaml = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": {idx: cat["name"] for idx, cat in enumerate(categories)},
    }
    with open(output_dir / "data.yaml", "w") as f:
        yaml.dump(data_yaml, f, sort_keys=False)

    n_neg_train = sum(1 for img in train_images if not anns_by_image.get(img["id"]))
    n_neg_val = sum(1 for img in val_images if not anns_by_image.get(img["id"]))

    print(f"Train: {n_train} bilder ({n_neg_train} uten objekter, {n_neg_train / n_train:.1%})")
    print(f"Val:   {n_val} bilder ({n_neg_val} uten objekter, {n_neg_val / n_val:.1%})")
    print(f"data.yaml skrevet til {output_dir / 'data.yaml'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco_json", type=str, default="output/merged/coco/coco_annotations.json")
    parser.add_argument("--images_dir", type=str, default="output/merged/images")
    parser.add_argument("--output_dir", type=str, default="output/dataset")
    parser.add_argument("--val_ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    split_dataset(Path(args.coco_json), Path(args.images_dir), Path(args.output_dir), args.val_ratio, args.seed)