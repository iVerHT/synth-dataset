import json
import os
import argparse


def coco_to_yolo(coco_json_path, yolo_labels_dir, classes_txt_path):
    with open(coco_json_path) as f:
        coco = json.load(f)

    os.makedirs(yolo_labels_dir, exist_ok=True)

    images = {img["id"]: img for img in coco["images"]}

    categories = sorted(coco["categories"], key=lambda c: c["id"])
    cat_id_to_yolo_idx = {cat["id"]: idx for idx, cat in enumerate(categories)}

    with open(classes_txt_path, "w") as f:
        for cat in categories:
            f.write(f"{cat['name']}\n")

    anns_by_image = {}
    for ann in coco["annotations"]:
        anns_by_image.setdefault(ann["image_id"], []).append(ann)

    for image_id, img_info in images.items():
        img_w = img_info["width"]
        img_h = img_info["height"]

        base_name = os.path.splitext(os.path.basename(img_info["file_name"]))[0]
        label_path = os.path.join(yolo_labels_dir, f"{base_name}.txt")

        lines = []
        for ann in anns_by_image.get(image_id, []):
            x, y, w, h = ann["bbox"]
            x_center = (x + w / 2) / img_w
            y_center = (y + h / 2) / img_h
            w_norm = w / img_w
            h_norm = h / img_h
            yolo_idx = cat_id_to_yolo_idx[ann["category_id"]]
            lines.append(f"{yolo_idx} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

        with open(label_path, "w") as f:
            f.write("\n".join(lines))

    print(f"Skrev {len(images)} label-filer til {yolo_labels_dir}")
    print(f"Klasser skrevet til {classes_txt_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco_json", type=str, default="output/merged/coco/coco_annotations.json")
    parser.add_argument("--yolo_labels_dir", type=str, default="output/merged/yolo/labels")
    parser.add_argument("--classes_txt", type=str, default="output/merged/yolo/classes.txt")
    args = parser.parse_args()

    coco_to_yolo(args.coco_json, args.yolo_labels_dir, args.classes_txt)