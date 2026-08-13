import blenderproc as bproc
import numpy as np
import yaml
import math
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HDRI_ROOT = PROJECT_ROOT / "assets" / "hdris_raw" / "hdris"


bproc.init()

with open("configs/objects.yaml") as f:
    obj_config = yaml.safe_load(f)
categories = obj_config["categories"]


objs = []
for cat_id, cat_info in categories.items():
    # model_path = f"assets/models/{cat_info['file']}"
    # loaded = bproc.loader.load_obj(model_path)
    model_path = PROJECT_ROOT / "assets" / "models" / cat_info["file"]
    loaded = bproc.loader.load_obj(str(model_path))
    for obj in loaded:
        obj.set_cp("category_id", cat_id)
        obj.set_name(cat_info["name"])
    objs.extend(loaded)


light = bproc.types.Light()
light.set_type("POINT")
light.set_location([2, -2, 2])
light.set_energy(1000)

poi = bproc.object.compute_poi(objs)
cam_location = [3.5, -3.5, 2.5]
rotation_matrix = bproc.camera.rotation_from_forward_vec(
    poi - np.array(cam_location)
)

cam2world = bproc.math.build_transformation_mat(cam_location, rotation_matrix)
bproc.camera.add_camera_pose(cam2world)

# hdri_path = bproc.loader.get_random_world_background_hdr_img_path_from_haven("assets\hdris_raw")
# bproc.world.set_world_background_hdr_img(
#     hdri_path,
#     rotation_euler=[0, 0, random.uniform(0, 2 * math.pi)]
# )


hdri_files = list(HDRI_ROOT.glob("*/*.hdr"))

if not hdri_files:
    raise RuntimeError(f"Fant ingen HDRI-filer i {HDRI_ROOT}")

hdri_path = random.choice(hdri_files)

print("Using HDRI:", hdri_path)

bproc.world.set_world_background_hdr_img(
    str(hdri_path),
    rotation_euler=[0, 0, random.uniform(0, 2 * math.pi)]
)

bproc.renderer.enable_segmentation_output(map_by=["class", "instance", "name"])

bproc.renderer.set_max_amount_of_samples(64)
data = bproc.renderer.render()

bproc.writer.write_coco_annotations(
    "output/coco_data",
    instance_segmaps=data["instance_segmaps"],
    instance_attribute_maps=data["instance_attribute_maps"],
    colors=data["colors"],
    color_file_format="JPEG",
    mask_encoding_format="polygon"
)