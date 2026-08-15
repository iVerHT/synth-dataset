import blenderproc as bproc
import numpy as np
import yaml
import math
import random
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HDRI_ROOT = PROJECT_ROOT / "assets" / "hdris_raw" / "hdris"
OBJECTS_CONFIG = PROJECT_ROOT / "configs" / "objects.yaml"

parser = argparse.ArgumentParser()
parser.add_argument("--num_images", type=int, default=10)
parser.add_argument("--output_dir", type=str, default="output/coco_data")
parser.add_argument("--seed", type=int, default=None)
args = parser.parse_args()

if args.seed is not None:
    random.seed(args.seed)
    np.random.seed(args.seed)

bproc.init()

# ---------------------------------------------------------------------------
# 1. Last inn mål-objekter ÉN GANG — som en maks-pool av instanser
#    (billigere å parkere ubrukte objekter enn å lage/slette dem hver runde)
# ---------------------------------------------------------------------------
with open(OBJECTS_CONFIG) as f:
    obj_config = yaml.safe_load(f)
categories = obj_config["categories"]

target_pool = {}
for cat_id, cat_info in categories.items():
    model_path = PROJECT_ROOT / "assets" / "models" / cat_info["file"]
    base_objs = bproc.loader.load_obj(str(model_path))
    for obj in base_objs:
        obj.set_cp("category_id", cat_id)
        obj.set_name(cat_info["name"])

    max_inst = cat_info.get("max_instances", 1)
    instances = list(base_objs)
    for i in range(max_inst - 1):
        for obj in base_objs:
            dup = obj.duplicate()
            dup.set_cp("category_id", cat_id)
            dup.set_name(f"{cat_info['name']}_{i + 1}")
            instances.append(dup)
    target_pool[cat_id] = instances


def compute_avg_object_size(objs):
    sizes = []
    for obj in objs:
        bbox = np.array(obj.get_bound_box())
        dims = bbox.max(axis=0) - bbox.min(axis=0)
        sizes.append(np.mean(dims))
    return np.mean(sizes)


all_target_objs = [o for objs in target_pool.values() for o in objs]
target_size = compute_avg_object_size(all_target_objs)
print(f"Gjennomsnittlig objektstørrelse: {target_size:.3f} enheter")

# ---------------------------------------------------------------------------
# 2. Distractor-pool — samme prinsipp, laget én gang
# ---------------------------------------------------------------------------
MAX_DISTRACTORS = 8


def create_distractor_pool(num, reference_size):
    shapes = ["CUBE", "SPHERE", "CYLINDER", "CONE"]
    pool = []
    for i in range(num):
        obj = bproc.object.create_primitive(random.choice(shapes))
        scale_factor = (reference_size / 2.0) * random.uniform(0.2, 0.9)
        obj.set_scale([scale_factor] * 3)
        obj.set_cp("category_id", 0)
        obj.set_cp("is_distractor", True)
        obj.set_name(f"distractor_{i}")
        pool.append(obj)
    return pool


distractor_pool = create_distractor_pool(MAX_DISTRACTORS, target_size)

PARKING_SPOT = [1000, 1000, 1000]  # gjemmested for objekter som ikke brukes denne runden


def park_unused(objs):
    for obj in objs:
        obj.set_location(PARKING_SPOT)


# ---------------------------------------------------------------------------
# 3. Lys — opprettes ÉN gang, egenskapene randomiseres hver runde
# ---------------------------------------------------------------------------
light = bproc.types.Light()

# ---------------------------------------------------------------------------
# 4. HOVEDLØKKE — én iterasjon = ett bilde
# ---------------------------------------------------------------------------
for img_idx in range(args.num_images):
    print(f"--- Bilde {img_idx + 1}/{args.num_images} ---")
    bproc.utility.reset_keyframes()

    # Velg tilfeldig antall aktive instanser per kategori, parker resten
    active_targets = []
    for cat_id, instances in target_pool.items():
        min_inst = categories[cat_id].get("min_instances", 1)
        max_inst = categories[cat_id].get("max_instances", 1)
        num_active = random.randint(min_inst, max_inst)
        chosen = random.sample(instances, num_active)
        park_unused([o for o in instances if o not in chosen])
        active_targets.extend(chosen)

    num_active_distractors = random.randint(3, MAX_DISTRACTORS)
    active_distractors = random.sample(distractor_pool, num_active_distractors)
    park_unused([o for o in distractor_pool if o not in active_distractors])

    # Kamera
    def sample_camera_pose():
        location = bproc.sampler.shell(
            center=[0, 0, 0], radius_min=4, radius_max=8,
            elevation_min=15, elevation_max=70
        )
        poi = np.random.uniform([-0.5, -0.5, 0], [0.5, 0.5, 0.5])
        rotation_matrix = bproc.camera.rotation_from_forward_vec(
            poi - location, inplane_rot=np.random.uniform(-0.2, 0.2)
        )
        return bproc.math.build_transformation_mat(location, rotation_matrix)

    cam2world = sample_camera_pose()
    bproc.camera.add_camera_pose(cam2world)

    # Plassering i frustumet, avstand skalert etter objektstørrelse
    def sample_pose_in_frustum(obj):
        cam2world_mat = np.array(cam2world)
        cam_location = cam2world_mat[:3, 3]
        forward = -cam2world_mat[:3, 2]
        right = cam2world_mat[:3, 0]
        up = cam2world_mat[:3, 1]
        fov_x, fov_y = bproc.camera.get_fov()
        depth = np.random.uniform(target_size * 4, target_size * 10)
        margin = 0.6
        max_offset_x = depth * np.tan(fov_x / 2) * margin
        max_offset_y = depth * np.tan(fov_y / 2) * margin
        offset_x = np.random.uniform(-max_offset_x, max_offset_x)
        offset_y = np.random.uniform(-max_offset_y, max_offset_y)
        candidate = cam_location + depth * forward + offset_x * right + offset_y * up
        obj.set_location(candidate)
        obj.set_rotation_euler(np.random.uniform(0, 2 * np.pi, 3))

    all_active = active_targets + active_distractors
    random.shuffle(all_active)
    bproc.object.sample_poses(
        all_active,
        sample_pose_func=sample_pose_in_frustum,
        objects_to_check_collisions=all_active
    )

    # Lys — randomiser egenskapene på det EKSISTERENDE lyset (ikke lag nytt)
    light.set_type(random.choice(["POINT", "SPOT"]))
    light.set_location(bproc.sampler.shell(
        center=[0, 0, 1], radius_min=2, radius_max=5,
        elevation_min=20, elevation_max=80
    ))
    light.set_energy(random.uniform(200, 3000))
    light.set_color(np.random.uniform([0.8, 0.8, 0.8], [1.0, 1.0, 1.0]))

    # HDRI
    hdri_files = list(HDRI_ROOT.glob("*/*.hdr"))
    hdri_path = random.choice(hdri_files)
    bproc.world.set_world_background_hdr_img(
        str(hdri_path),
        strength=random.uniform(0.3, 1.5),
        rotation_euler=[0, 0, random.uniform(0, 2 * math.pi)]
    )

    # Render + skriv COCO (appender automatisk til eksisterende annotasjonsfil)
    bproc.renderer.enable_segmentation_output(map_by=["class", "instance"])
    bproc.renderer.set_max_amount_of_samples(64)
    data = bproc.renderer.render()

    bproc.writer.write_coco_annotations(
        args.output_dir,
        instance_segmaps=data["instance_segmaps"],
        instance_attribute_maps=data["instance_attribute_maps"],
        colors=data["colors"],
        color_file_format="JPEG",
        mask_encoding_format="rle"
    )

print("Ferdig med shard.")