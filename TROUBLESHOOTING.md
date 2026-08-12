# Troubleshooting

Kjente feil og løsninger for dette prosjektet (BlenderProc + conda på Windows).

## 1. `ValueError: setting an array element with a sequence` ved `write_coco_annotations`

**Symptom:**

```
File "...\blenderproc\python\writer\CocoWriterUtility.py", line 400, in binary_mask_to_polygon
    contours = np.array(measure.find_contours(padded_binary_mask, 0.5))
ValueError: setting an array element with a sequence. The requested array has an
inhomogeneous shape after 1 dimensions. The detected shape was (3,) + inhomogeneous part.
```

**Årsak:**

BlenderProc sin `CocoWriterUtility.binary_mask_to_polygon` bygger en numpy-array direkte fra
`skimage.measure.find_contours(...)`, som returnerer konturer med ulik lengde (avhengig av
objektets form). Eldre numpy-versjoner tillot dette stille (lagde automatisk en
"object"-array). Med numpy 2.x er dette nå en hard feil med mindre `dtype=object`
er satt eksplisitt.

Oppstår fordi conda-miljøet installerte en nyere numpy-versjon enn det BlenderProc sin
skrevne kode (i denne versjonen av pakken) forutsetter.

**Fiks:**

Åpne filen i det aktive conda-miljøet (bytt sti til ditt eget miljønavn/sti):

```
<conda-envs>\bproc\lib\site-packages\blenderproc\python\writer\CocoWriterUtility.py
```

Finn linjen (rundt linje 400):

```python
contours = np.array(measure.find_contours(padded_binary_mask, 0.5))
```

Endre til:

```python
contours = np.array(measure.find_contours(padded_binary_mask, 0.5), dtype=object)
```

**OBS:** Dette er en patch i en pip-installert pakke, ikke i vår egen kode. Patchen
forsvinner hvis `blenderproc` reinstalleres/oppgraderes i miljøet — må da gjøres på nytt.

---

## 2. `blenderproc run` feiler etter `conda create --clone`

**Symptom:**

```
Fatal error in launcher: Unable to create process using '"...\<gammelt_miljø>\python.exe" ...'
```

**Årsak:**

`conda create --clone` kopierer miljøets filer, men konsoll-script-launchere
(f.eks. `blenderproc.exe` på Windows) har en hardkodet, absolutt sti til Python-
interpreteren som var aktiv da pakken ble pip-installert. Kloning oppdaterer ikke
denne stien.

**Fiks:**

Reinstaller pip-pakken i det nye/klonede miljøet, slik at launcheren skrives på nytt
med riktig sti:

```bash
pip uninstall blenderproc
pip install blenderproc==<versjon>
```

---

## 3. `git` / annet nylig installert program ikke funnet i terminalen

**Symptom:**

```
'git' is not recognized as an internal or external command, operable program or batch file.
```

... selv om programmet nettopp ble installert og PATH ble oppdatert.

**Årsak:**

En allerede åpen terminal-sesjon leser PATH kun ved oppstart. Nye systemvariabler
(fra en installer) blir ikke lastet inn i en sesjon som allerede kjører.

**Fiks:**

Lukk hele terminalvinduet (ikke bare fanen) og åpne et nytt. Bekreft med f.eks.
`git --version`.

---

## 4. Category-navn i COCO-output blir et tall (`category_id`) i stedet for objektnavnet

**Symptom:**

```json
"categories": [{"id": 1, "supercategory": "coco_annotations", "name": 1}]
```

... selv om `obj.set_name("shape")` er satt på objektet.

**Årsak:**

`write_coco_annotations` henter category-navnet fra `instance_attribute_maps`, som kun
inneholder de attributtene som er bedt om via `map_by` i
`bproc.renderer.enable_segmentation_output(...)`. Uten `"name"` i denne lista faller
writeren tilbake på å bruke `category_id`-tallet som navn.

I tillegg: offisiell BlenderProc-dokumentasjon bruker nøkkelordet `"class"` (ikke
`"category_id"`) i `map_by` for å hente ut kategori-informasjon — `"class"` mappes
internt til `category_id`-feltet i output.

**Fiks:**

```python
bproc.renderer.enable_segmentation_output(map_by=["class", "instance", "name"])
```

---

## 5. `conda env export --from-history` mangler pip-pakker

**Symptom:**

`environment.yml` mangler pip-installerte pakker (f.eks. `blenderproc`) selv om de
er installert.

**Årsak:**

`--from-history` fanger kun opp conda-pakker som er eksplisitt installert med
`conda install`, ikke pip-pakker.

**Fiks:**

Sjekk manuelt hva som er pip-installert:

```bash
pip freeze | findstr <pakkenavn>
```

Legg til en `pip:`-seksjon manuelt i `environment.yml`:

```yaml
dependencies:
  - python=3.10
  - numpy
  - pip
  - pip:
      - blenderproc==2.8.0
```

Fjern også `prefix:`-linja (eller ignorer den) — den er maskinspesifikk og
overstyres uansett ved `conda env create -n <navn>` på en annen maskin.