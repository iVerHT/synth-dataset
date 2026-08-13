import requests
import os
import random
import shutil

HDRI_DIR = "assets/hdris_raw/hdris"
NUM_HDRIS = 300
RESOLUTION = "1k"

os.makedirs(HDRI_DIR, exist_ok=True)

# Rydd opp i ufullstendige nedlastinger fra tidligere kjøringer
for name in os.listdir(HDRI_DIR):
    subfolder = os.path.join(HDRI_DIR, name)
    expected_file = os.path.join(subfolder, f"{name}.hdr")
    if os.path.isdir(subfolder) and (
        not os.path.exists(expected_file) or os.path.getsize(expected_file) == 0
    ):
        print(f"Fjerner ufullstendig nedlasting: {name}")
        shutil.rmtree(subfolder)

print("Henter liste over tilgjengelige HDRIer...")
resp = requests.get("https://api.polyhaven.com/assets?type=hdris")
all_hdri_names = list(resp.json().keys())

random.seed(42)
selected = random.sample(all_hdri_names, min(NUM_HDRIS, len(all_hdri_names)))

print(f"Laster ned {len(selected)} HDRIer i {RESOLUTION}...")
failed = []
for i, name in enumerate(selected, 1):
    hdri_subfolder = os.path.join(HDRI_DIR, name)
    out_path = os.path.join(hdri_subfolder, f"{name}.hdr")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        continue

    files_resp = requests.get(f"https://api.polyhaven.com/files/{name}")
    files = files_resp.json()

    try:
        hdri_url = files["hdri"][RESOLUTION]["hdr"]["url"]
    except KeyError:
        print(f"  [{i}/{len(selected)}] {name}: mangler {RESOLUTION}, hopper over")
        continue

    print(f"  [{i}/{len(selected)}] {name}")
    r = requests.get(hdri_url)
    if r.status_code != 200 or len(r.content) == 0:
        print(f"    FEIL ved nedlasting av {name} (status {r.status_code}), hopper over")
        failed.append(name)
        continue

    os.makedirs(hdri_subfolder, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(r.content)

print(f"Ferdig — {len(os.listdir(HDRI_DIR))} HDRIer i {HDRI_DIR}")
if failed:
    print(f"Feilet for {len(failed)} filer: {failed}")