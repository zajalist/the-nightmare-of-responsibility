"""Read-only: the static meshes the hands touch, exported as FBX for the Blender grip twin (anim lane), so the twins
solve against the game's own geometry (the bedroom door's knob is part of SM_Door_Bedroom; the glb the twin had is
normalised and not to scale). Writes P:/FoA-Assets/character/mpfb/ue_export/<mesh>.fbx and an index json with each
mesh's local bounds (the twin checks its import against them).
  FOA_AREAS=Level python Tools/Unreal/ue_remote.py Tools/Unreal/player/export_grip_meshes.py"""
import json
import os

import unreal

OUT = "P:/FoA-Assets/character/mpfb/ue_export"
MESHES = []
SKIP = ("Bedding", "desk_lamp", "wooden_table", "old_bed_frame", "door02", "door03", "DoorFrame")  # not touched: keep the run short
os.makedirs(OUT, exist_ok=True)
anchors = json.load(open(unreal.Paths.project_saved_dir() + "AnimShots/grip_anchors.json"))
for a in anchors.values():  # every mesh the dump saw on the grip actors (door plate, screws, boots, drawers, ...)
    for c in a["comps"]:
        if c.get("mesh") and c.get("visible") and not c["mesh"].startswith("/Engine") and not any(
                k in c["mesh"] for k in SKIP):
            MESHES.append(c["mesh"].split(".")[0])
index = {}
for path in sorted(set(MESHES)):
    sm = unreal.load_asset(path)
    if not isinstance(sm, unreal.StaticMesh):
        continue
    name = path.rsplit("/", 1)[1]
    task = unreal.AssetExportTask()
    task.object, task.filename = sm, f"{OUT}/{name}.fbx"
    task.automated, task.prompt, task.replace_identical = True, False, True
    ok = unreal.Exporter.run_asset_export_task(task)
    b = sm.get_bounding_box()
    index[name] = dict(path=path, ok=bool(ok), local_box=[[b.min.x, b.min.y, b.min.z], [b.max.x, b.max.y, b.max.z]])
with open(f"{OUT}/index.json", "w") as f:
    json.dump(index, f, indent=1)
print("GRIP_MESHES", {k: v["ok"] for k, v in index.items()})
