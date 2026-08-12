import blenderproc as bproc
import numpy as np
import yaml

bproc.init()

with open("configs/objects.yaml") as f:
    obj_config = yaml.safe_load(f)
categories = obj_config["categories"]


objs = []
for cat_id, cat_info in categories.items():
    model_path = f"assets/models/{cat_info['file']}"
    loaded = bproc.loader.load_obj(model_path)
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

bproc.renderer.enable_segmentation_output(map_by=["category_id", "instance", "name"])

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