import requests
import os
import random
import shutil

MATERIALS_DIR = "assets/materials_raw/materials"
NUM_MATERIALS = 10
RESOLUTION = "1k"

os.makedirs(MATERIALS_DIR, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "TextureDownloader/1.0 (iverhthorsberg@gmail.com)"})

#
# Rydd opp i ufullstendige nedlastinger fra tidligere kjøringer
#
for name in os.listdir(MATERIALS_DIR):
    subfolder = os.path.join(MATERIALS_DIR, name)
    if not os.path.isdir(subfolder):
        continue

    png_path = os.path.join(subfolder, f"{name}.png")
    jpg_path = os.path.join(subfolder, f"{name}.jpg")
    has_valid = (os.path.exists(png_path) and os.path.getsize(png_path) > 0) or \
                (os.path.exists(jpg_path) and os.path.getsize(jpg_path) > 0)

    if not has_valid:
        print(f"Fjerner ufullstendig nedlasting: {name}")
        shutil.rmtree(subfolder)

print("Henter liste over tilgjengelige materialer...")
resp = session.get("https://api.polyhaven.com/assets?type=textures")
all_material_names = list(resp.json().keys())

random.seed(42)
selected = random.sample(all_material_names, min(NUM_MATERIALS, len(all_material_names)))

print(f"Laster ned {len(selected)} materialer i resolution {RESOLUTION}...")
failed = []

for i, name in enumerate(selected, 1):
    material_subfolder = os.path.join(MATERIALS_DIR, name)
    png_path = os.path.join(material_subfolder, f"{name}.png")
    jpg_path = os.path.join(material_subfolder, f"{name}.jpg")

    if (os.path.exists(png_path) and os.path.getsize(png_path) > 0) or \
       (os.path.exists(jpg_path) and os.path.getsize(jpg_path) > 0):
        continue

    files_resp = session.get(f"https://api.polyhaven.com/files/{name}")
    files = files_resp.json()

    try:
        diffuse_data = files["Diffuse"][RESOLUTION]
        if "png" in diffuse_data:
            material_url = diffuse_data["png"]["url"]
            extension = "png"
        elif "jpg" in diffuse_data:
            material_url = diffuse_data["jpg"]["url"]
            extension = "jpg"
        else:
            print(f"{name}: ingen PNG/JPG funnet")
            continue
    except KeyError:
        print(f"{name}: mangler Diffuse/{RESOLUTION}")
        continue

    out_path = os.path.join(material_subfolder, f"{name}.{extension}")

    print(f" [{i}/{len(selected)}] {name}")
    r = session.get(material_url)
    if r.status_code != 200 or len(r.content) == 0:
        print(f"    Feil ved nedlasting av {name} (status {r.status_code}), hopper over")
        failed.append(name)
        continue

    os.makedirs(material_subfolder, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(r.content)

print(f"Ferdig nedlastet - {len(os.listdir(MATERIALS_DIR))} materialer i {MATERIALS_DIR}")
if failed:
    print(f"Feilet for {len(failed)} filer: {failed}")