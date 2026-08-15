import json
import shutil
import argparse
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OBJECTS_CONFIG = PROJECT_ROOT / "configs" / "objects.yaml"


def load_canonical_category_names():
    with open(OBJECTS_CONFIG) as f:
        obj_config = yaml.safe_load(f)
    return {cat_id: cat_info["name"] for cat_id, cat_info in obj_config["categories"].items()}


def merge_shards(shards_root: Path, output_dir: Path):
    shard_dirs = sorted([d for d in shards_root.iterdir() if d.is_dir() and (d / "coco_annotations.json").exists()])

    if not shard_dirs:
        raise RuntimeError(f"Fant ingen shard-mapper med coco_annotations.json i {shards_root}")

    canonical_names = load_canonical_category_names()

    output_images_dir = output_dir / "images"
    output_images_dir.mkdir(parents=True, exist_ok=True)

    merged_images = []
    merged_annotations = []
    merged_categories = {}

    next_image_id = 0
    next_annotation_id = 0
    info = None
    licenses = None

    for shard_dir in shard_dirs:
        coco_path = shard_dir / "coco_annotations.json"
        with open(coco_path) as f:
            shard_data = json.load(f)

        if info is None:
            info = shard_data.get("info")
            licenses = shard_data.get("licenses")

        for cat in shard_data["categories"]:
            cat_id = cat["id"]
            if cat_id not in canonical_names:
                continue  # ukjent kategori (f.eks. distractor-id 0) — hopp over
            if cat_id not in merged_categories:
                merged_categories[cat_id] = {
                    "id": cat_id,
                    "supercategory": cat.get("supercategory", "coco_annotations"),
                    "name": canonical_names[cat_id],  # alltid fra objects.yaml, ikke fra shard-data
                }

        old_to_new_image_id = {}

        for img in shard_data["images"]:
            old_id = img["id"]
            new_id = next_image_id
            old_to_new_image_id[old_id] = new_id

            src_image_path = shard_dir / img["file_name"]
            new_filename = f"{new_id:06d}.jpg"
            dst_image_path = output_images_dir / new_filename

            if not src_image_path.exists():
                print(f"ADVARSEL: fant ikke bildefil {src_image_path}, hopper over")
                continue

            shutil.copy2(src_image_path, dst_image_path)

            new_img = dict(img)
            new_img["id"] = new_id
            new_img["file_name"] = f"images/{new_filename}"
            merged_images.append(new_img)

            next_image_id += 1

        for ann in shard_data["annotations"]:
            if ann["category_id"] not in canonical_names:
                continue  # filtrer bort distractor-annotasjoner (skal aldri finnes, men trygghet i tillegg)
            if ann["image_id"] not in old_to_new_image_id:
                continue

            new_ann = dict(ann)
            new_ann["id"] = next_annotation_id
            new_ann["image_id"] = old_to_new_image_id[ann["image_id"]]
            merged_annotations.append(new_ann)
            next_annotation_id += 1

        print(f"{shard_dir.name}: {len(shard_data['images'])} bilder, {len(shard_data['annotations'])} annotasjoner")

    merged = {
        "info": info,
        "licenses": licenses,
        "categories": list(merged_categories.values()),
        "images": merged_images,
        "annotations": merged_annotations,
    }

    output_coco_dir = output_dir / "coco"
    output_coco_dir.mkdir(parents=True, exist_ok=True)
    output_json_path = output_coco_dir / "coco_annotations.json"
    with open(output_json_path, "w") as f:
        json.dump(merged, f)

    print(f"\nFerdig sammenslått: {len(merged_images)} bilder, {len(merged_annotations)} annotasjoner")
    print(f"Kategorier: {[c['name'] for c in merged['categories']]}")
    print(f"Skrevet til {output_json_path}")
    return output_json_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards_root", type=str, default="output/shards")
    parser.add_argument("--output_dir", type=str, default="output/merged")
    args = parser.parse_args()

    merge_shards(Path(args.shards_root), Path(args.output_dir))