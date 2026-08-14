import blenderproc as bproc
import numpy as np
import yaml
import math
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HDRI_ROOT = PROJECT_ROOT / "assets" / "hdris_raw" / "hdris"
DISTRACTOR_DIR = PROJECT_ROOT / "assets" / "distractors"
OBJECTS_CONFIG = PROJECT_ROOT / "configs" / "objects.yaml"

bproc.init()
# ---------------------------------------------------------------------------
# 1. Last inn mål-objekter (fra objects.yaml)
# ---------------------------------------------------------------------------
with open(OBJECTS_CONFIG) as f:
    obj_config = yaml.safe_load(f)
categories = obj_config["categories"]


target_objs = []
for cat_id, cat_info in categories.items():
    model_path = PROJECT_ROOT / "assets" / "models" / cat_info["file"]
    loaded = bproc.loader.load_obj(str(model_path))
    for obj in loaded:
        obj.set_cp("category_id", cat_id)
        obj.set_name(cat_info["name"])
    target_objs.extend(loaded)

# ---------------------------------------------------------------------------
# 2. Last inn distractor-objekter (valgfritt — hopper over hvis mappa er tom)
# ---------------------------------------------------------------------------
distractor_objs = []
if DISTRACTOR_DIR.exists():
    distractor_files = list(DISTRACTOR_DIR.glob("*.obj"))
    for file_path in distractor_files:
        loaded = bproc.loader.load_obj(str(file_path))
        for obj in loaded:
            obj.set_cp("category_id", 0)   # 0 = ingen ekte kategori, kun distractor
            obj.set_cp("is_distractor", True)
            obj.set_name(f"distractor_{file_path.stem}")
        distractor_objs.extend(loaded)

if not distractor_objs:
    print("Ingen distractor-objekter funnet i assets/distractors — fortsetter uten.")

# ---------------------------------------------------------------------------
# 3. Sample kamera FØRST — uavhengig av objektene
# ---------------------------------------------------------------------------
def sample_camera_pose():
    location = bproc.sampler.shell(
        center=[0, 0, 0],
        radius_min=4,
        radius_max=8,
        elevation_min=15,
        elevation_max=70
    )
    poi = np.random.uniform([-0.5, -0.5, 0], [0.5, 0.5, 0.5])
    rotation_matrix = bproc.camera.rotation_from_forward_vec(
        poi - location,
        inplane_rot=np.random.uniform(-0.2, 0.2)
    )
    return bproc.math.build_transformation_mat(location, rotation_matrix)


cam2world = sample_camera_pose()
bproc.camera.add_camera_pose(cam2world)

# ---------------------------------------------------------------------------
# 4. Plasser mål-objekter + distractors inne i kameraets synsfelt
#    (kollisjonssjekket, så de ikke overlapper hverandre)
# ---------------------------------------------------------------------------
def sample_pose_in_frustum(obj):
    cam_location = np.array(cam2world)[:3, 3]  # posisjon fra kameraets transformasjonsmatrise

    for _ in range(100):
        candidate = np.random.uniform([-2, -2, 0], [2, 2, 2])
        distance_to_cam = np.linalg.norm(candidate - cam_location)

        if (bproc.camera.is_point_inside_camera_frustum(candidate)
                and 2.5 <= distance_to_cam <= 7.0):
            obj.set_location(candidate)
            obj.set_rotation_euler(np.random.uniform(0, 2 * np.pi, 3))
            return

    obj.set_location([0, 0, 0.5])


all_placeable = target_objs + distractor_objs
bproc.object.sample_poses(
    all_placeable,
    sample_pose_func=sample_pose_in_frustum,
    objects_to_check_collisions=all_placeable
)

# ---------------------------------------------------------------------------
# 5. Lys — randomisert type, posisjon, energi og farge
# ---------------------------------------------------------------------------
light = bproc.types.Light()
light.set_type(random.choice(["POINT", "SPOT"]))
light.set_location(bproc.sampler.shell(
    center=[0, 0, 1],
    radius_min=2,
    radius_max=5,
    elevation_min=20,
    elevation_max=80
))
light.set_energy(random.uniform(200, 3000))
light.set_color(np.random.uniform([0.8, 0.8, 0.8], [1.0, 1.0, 1.0]))

# ---------------------------------------------------------------------------
# 6. HDRI-bakgrunn — randomisert valg, rotasjon og styrke
# ---------------------------------------------------------------------------
hdri_files = list(HDRI_ROOT.glob("*/*.hdr"))
if not hdri_files:
    raise RuntimeError(f"Fant ingen HDRI-filer i {HDRI_ROOT}")

hdri_path = random.choice(hdri_files)
print("Using HDRI:", hdri_path)

bproc.world.set_world_background_hdr_img(
    str(hdri_path),
    strength=random.uniform(0.3, 1.5),
    rotation_euler=[0, 0, random.uniform(0, 2 * math.pi)]
)

# ---------------------------------------------------------------------------
# 7. Segmentering + render
# ---------------------------------------------------------------------------
bproc.renderer.enable_segmentation_output(map_by=["class", "instance", "name"])
bproc.renderer.set_max_amount_of_samples(64)
data = bproc.renderer.render()

# ---------------------------------------------------------------------------
# 8. COCO-annotasjoner
# ---------------------------------------------------------------------------
bproc.writer.write_coco_annotations(
    "output/coco_data",
    instance_segmaps=data["instance_segmaps"],
    instance_attribute_maps=data["instance_attribute_maps"],
    colors=data["colors"],
    color_file_format="JPEG",
    mask_encoding_format="polygon"
)

# poi = bproc.object.compute_poi(objs)
# cam_location = [3.5, -3.5, 2.5]
# rotation_matrix = bproc.camera.rotation_from_forward_vec(
#     poi - np.array(cam_location)
# )

# # cam2world = bproc.math.build_transformation_mat(cam_location, rotation_matrix)
# # bproc.camera.add_camera_pose(cam2world)

# # hdri_path = bproc.loader.get_random_world_background_hdr_img_path_from_haven("assets\hdris_raw")
# # bproc.world.set_world_background_hdr_img(
# #     hdri_path,
# #     rotation_euler=[0, 0, random.uniform(0, 2 * math.pi)]
# # )


# hdri_files = list(HDRI_ROOT.glob("*/*.hdr"))

# if not hdri_files:
#     raise RuntimeError(f"Fant ingen HDRI-filer i {HDRI_ROOT}")

# hdri_path = random.choice(hdri_files)

# print("Using HDRI:", hdri_path)

# bproc.world.set_world_background_hdr_img(
#     str(hdri_path),
#     rotation_euler=[0, 0, random.uniform(0, 2 * math.pi)]
# )

# bproc.renderer.enable_segmentation_output(map_by=["class", "instance", "name"])

# bproc.renderer.set_max_amount_of_samples(64)
# data = bproc.renderer.render()

# bproc.writer.write_coco_annotations(
#     "output/coco_data",
#     instance_segmaps=data["instance_segmaps"],
#     instance_attribute_maps=data["instance_attribute_maps"],
#     colors=data["colors"],
#     color_file_format="JPEG",
#     mask_encoding_format="polygon"
# )