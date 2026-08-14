import blenderproc as bproc
import numpy as np
import yaml
import math
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HDRI_ROOT = PROJECT_ROOT / "assets" / "hdris_raw" / "hdris"
# DISTRACTOR_DIR = PROJECT_ROOT / "assets" / "distractors" #Kan eventuelt lage egne distractors i mappen distractors
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
    base_objs = bproc.loader.load_obj(str(model_path))

    for obj in base_objs:
        obj.set_cp("category_id", cat_id)
        obj.set_name(cat_info["name"])
    target_objs.extend(base_objs)

    min_inst = cat_info.get("min_instances", 1)
    max_inst = cat_info.get("max_instances", 1)
    num_instances = random.randint(min_inst, max_inst)

    # Første instans er allerede lastet ovenfor — lag (num_instances - 1) kopier til
    for i in range(num_instances - 1):
        for obj in base_objs:
            dup = obj.duplicate()
            dup.set_cp("category_id", cat_id)
            dup.set_name(f"{cat_info['name']}_{i + 1}")
            target_objs.append(dup)


# ---------------------------------------------------------------------------
# 2. Lag distractor-objekter (prosedurale primitiver)
# ---------------------------------------------------------------------------

def compute_avg_object_size(objs):
    sizes = []
    for obj in objs:
        bbox = np.array(obj.get_bound_box())
        dims = bbox.max(axis=0) - bbox.min(axis=0)
        sizes.append(np.mean(dims))
    return np.mean(sizes)


def create_distractors(num_distractors, reference_size):
    distractors = []
    shapes = ["CUBE", "SPHERE", "CYLINDER", "CONE", "MONKEY", "CONE"]
    for i in range(num_distractors):
        shape = random.choice(shapes)
        obj = bproc.object.create_primitive(shape)

        # Blender-primitiver er som standard ~2 enheter store (radius/side ≈ 1),
        # så vi skalerer relativt til det for å matche referansestørrelsen
        scale_factor = (reference_size / 2.0) * random.uniform(0.2, 0.9)
        obj.set_scale([scale_factor] * 3)

        obj.set_cp("category_id", 0)
        obj.set_cp("is_distractor", True)
        obj.set_name(f"distractor_{i}")
        distractors.append(obj)
    return distractors

target_size = compute_avg_object_size(target_objs)
print(f"Gjennomsnittlig objektstørrelse: {target_size:.3f} enheter")
distractor_objs = create_distractors(num_distractors=random.randint(3, 8), reference_size=target_size)

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
# def sample_pose_in_frustum(obj):
#     cam_location = np.array(cam2world)[:3, 3]  # posisjon fra kameraets transformasjonsmatrise

#     for _ in range(100):
#         candidate = np.random.uniform([-4, -4, 0], [4, 4, 4])
#         distance_to_cam = np.linalg.norm(candidate - cam_location)

#         if (bproc.camera.is_point_inside_camera_frustum(candidate)
#                 and 2.5 <= distance_to_cam <= 7.0):
#             obj.set_location(candidate)
#             obj.set_rotation_euler(np.random.uniform(0, 2 * np.pi, 3))
#             return

#     obj.set_location([0, 0, 0.5])
def sample_pose_in_frustum(obj):
    cam2world_mat = np.array(cam2world)
    cam_location = cam2world_mat[:3, 3]
    forward = -cam2world_mat[:3, 2]
    right = cam2world_mat[:3, 0]
    up = cam2world_mat[:3, 1]

    fov_x, fov_y = bproc.camera.get_fov()

    # Avstand skalert etter objektets faktiske størrelse, IKKE et fast tall
    depth = np.random.uniform(target_size * 4, target_size * 10)

    margin = 0.6
    max_offset_x = depth * np.tan(fov_x / 2) * margin
    max_offset_y = depth * np.tan(fov_y / 2) * margin

    offset_x = np.random.uniform(-max_offset_x, max_offset_x)
    offset_y = np.random.uniform(-max_offset_y, max_offset_y)

    candidate = cam_location + depth * forward + offset_x * right + offset_y * up
    obj.set_location(candidate)
    obj.set_rotation_euler(np.random.uniform(0, 2 * np.pi, 3))


all_placeable = target_objs + distractor_objs
random.shuffle(all_placeable)

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
    mask_encoding_format="rle"
)

