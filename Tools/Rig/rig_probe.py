"""Read-only probe: import the Teen body FBX (exactly what UE imported) and the UE5 Manny FBX side by side and print
skeleton facts. pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/rig_probe.py"""
import json
import bpy
import numpy as np

TEEN = "P:/FoA-Assets/character/mpfb/export/teen_chest_flattened/SK_Teen_Body.fbx"
MANNY = "P:/FoA-Assets/character/v3/manny/SKM_Manny_Simple.fbx"


def load(path, tag):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        o.name = tag + "_" + o.name
    rig = next(o for o in new if o.type == "ARMATURE")
    meshes = [o for o in new if o.type == "MESH"]
    return rig, meshes


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
out = {}
for tag, path in (("teen", TEEN), ("manny", MANNY)):
    rig, meshes = load(path, tag)
    bpy.context.view_layer.update()
    bones = rig.data.bones
    info = {"rig": rig.name, "scale": list(rig.scale), "rot": list(rig.rotation_euler), "nbones": len(bones),
            "bones": {b.name: {"parent": b.parent.name if b.parent else None,
                               "head": list(rig.matrix_world @ b.head_local),
                               "m": [list(r) for r in (rig.matrix_world @ b.matrix_local)]} for b in bones},
            "meshes": {}}
    for m in meshes:
        names = {g.index: g.name for g in m.vertex_groups}
        counts = [sum(1 for g in v.groups if g.weight > 1e-4) for v in m.data.vertices]
        sums = [sum(g.weight for g in v.groups if names[g.group] in bones) for v in m.data.vertices]
        zs = [(m.matrix_world @ v.co).z for v in m.data.vertices]
        info["meshes"][m.name] = {"verts": len(m.data.vertices), "max_infl": max(counts),
                                  "hist_infl": np.bincount(counts).tolist(), "min_sum": min(sums), "max_sum": max(sums),
                                  "zmin": min(zs), "zmax": max(zs), "groups": len(m.vertex_groups),
                                  "unused_groups": [g.name for g in m.vertex_groups if g.name not in bones]}
    out[tag] = info
    print(tag, rig.name, "bones", len(bones), "scale", tuple(rig.scale), {k: (v["verts"], v["max_infl"], round(v["zmin"], 3), round(v["zmax"], 3)) for k, v in info["meshes"].items()})
open("P:/FoA/Saved/RigShots/audit/rig_probe.json", "w").write(json.dumps(out, indent=1))
print("wrote rig_probe.json")
