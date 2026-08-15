import subprocess
import sys
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "pipeline.yaml"

with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)


def run_generate():
    gen = CONFIG["generate"]
    subprocess.run([
        sys.executable, "src/launch_parallel.py",
        "--num_shards", str(gen["shards"]),
        "--images_per_shard", str(gen["images_per_shard"]),
        "--output_root", CONFIG["paths"]["shards_root"],
        "--base_seed", str(gen["seed"]),
        "--max_parallel", str(gen["max_parallel"]),
    ], check=True)


def run_merge():
    subprocess.run([
        sys.executable, "src/merge_coco.py",
        "--shards_root", CONFIG["paths"]["shards_root"],
        "--output_dir", CONFIG["paths"]["merged_dir"],
    ], check=True)


def run_convert():
    merged = Path(CONFIG["paths"]["merged_dir"])
    subprocess.run([
        sys.executable, "src/annotations/coco_to_yolo.py",
        "--coco_json", str(merged / "coco" / "coco_annotations.json"),
        "--yolo_labels_dir", str(merged / "yolo" / "labels"),
        "--classes_txt", str(merged / "yolo" / "classes.txt"),
    ], check=True)


def run_download_hdris():
    subprocess.run([sys.executable, "src/download_hdris.py"], check=True)


STEP_FUNCTIONS = {
    "download-hdris": run_download_hdris,
    "generate": run_generate,
    "merge": run_merge,
    "convert": run_convert,
}


def main():
    steps = CONFIG.get("steps", [])
    if not steps:
        print("Ingen steg listet under 'steps' i configs/pipeline.yaml — ingenting å gjøre.")
        return

    print(f"Kjører steg: {steps}")
    for step in steps:
        if step not in STEP_FUNCTIONS:
            print(f"Ukjent steg '{step}' i pipeline.yaml — hopper over.")
            continue
        print(f"\n=== {step} ===")
        STEP_FUNCTIONS[step]()

    print("\nPipeline ferdig.")


if __name__ == "__main__":
    main()