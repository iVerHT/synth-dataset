import subprocess
import argparse
from pathlib import Path
import concurrent.futures
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENE_SCRIPT = PROJECT_ROOT / "src" / "scene_setup.py"


def run_shard(shard_id, images_per_shard, output_root, base_seed, negative_prob):
    output_dir = output_root / f"shard_{shard_id:04d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = base_seed + shard_id
    log_path = output_dir / "log.txt"

    cmd = [
        "blenderproc", "run", str(SCENE_SCRIPT),
        "--",
        "--num_images", str(images_per_shard),
        "--output_dir", str(output_dir),
        "--seed", str(seed),
        "--negative_prob", str(negative_prob),
    ]

    print(f"[shard {shard_id}] Starter — {images_per_shard} bilder, seed={seed}")
    with open(log_path, "w") as log_file:
        result = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT)

    status = "OK" if result.returncode == 0 else f"FEILET (kode {result.returncode})"
    print(f"[shard {shard_id}] Ferdig — {status}. Logg: {log_path}")
    return shard_id, result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_shards", type=int, default=10)
    parser.add_argument("--images_per_shard", type=int, default=50)
    parser.add_argument("--output_root", type=str, default="output/shards")
    parser.add_argument("--base_seed", type=int, default=0)
    parser.add_argument("--max_parallel", type=int, default=2)
    parser.add_argument("--negative_prob", type=float, default=0.1)
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    failed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_parallel) as executor:
        futures = [
            executor.submit(run_shard, i, args.images_per_shard, output_root, args.base_seed, args.negative_prob)
            for i in range(args.num_shards)
        ]
        for future in concurrent.futures.as_completed(futures):
            shard_id, returncode = future.result()
            if returncode != 0:
                failed.append(shard_id)

    total = args.num_shards * args.images_per_shard
    print(f"\nAlle shards ferdig. Planlagt totalt: {total} bilder over {args.num_shards} shards.")
    if failed:
        print(f"OBS: {len(failed)} shard(s) feilet: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()