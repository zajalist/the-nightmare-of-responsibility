"""Knee in deep flex (crouch): pants and skin close-ups, plus where the pants' knee weights differ from the skin they
cover. Read-only. pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/diag_knee.py [teen=<body.fbx>] [garments=..] [tag=before]"""
import json
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
sys.argv += ["out=P:/FoA/Saved/RigShots/audit/_diag", "who=manny", "poses=rest"]
import rom_audit as R  # noqa: E402

TAG = R.A.get("tag", "before")
R.wipe()
cam = R.setup_render()
bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 800
r = R.Rig("teen", R.TEEN, R.GARMENTS)
pants = next(g for g in r.garments if "Pants" in g.name)
bw = R.labels(r)[1]
names = {g.index: g.name for g in pants.vertex_groups}
pw = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-4} for v in pants.data.vertices]
# compare each pants vertex's thigh/calf split with the nearest skin vertex's
bco = [r.body.matrix_world @ v.co for v in r.body.data.vertices]
tree = BVHTree.FromPolygons(bco, [tuple(p.vertices) for p in r.body.data.polygons])
kn = r.rest_head("calf_l")
rows = []
for i, v in enumerate(pants.data.vertices):
    p = pants.matrix_world @ v.co
    if (p - kn).length > 0.12 or p.x < 0:
        continue
    loc, nrm, fi, dist = tree.find_nearest(p)
    vs = r.body.data.polygons[fi].vertices
    j = min(vs, key=lambda k: (bco[k] - loc).length)
    calf_p = pw[i].get("calf_l", 0)
    calf_b = bw[j].get("calf_l", 0)
    rows.append({"v": i, "calf_pants": round(calf_p, 3), "calf_skin": round(calf_b, 3), "gap_mm": round(dist * 1000, 1)})
worst = sorted(rows, key=lambda x: -abs(x["calf_pants"] - x["calf_skin"]))[:15]
print("KNEE weight mismatch pants vs skin (calf share):", json.dumps(worst))
json.dump({"rows": rows}, open(f"P:/FoA/Saved/RigShots/audit/diag_knee_{TAG}.json", "w"))
r.reset()
R.arms_down(r), R.bend(r, 25), R.legs(r, (0.2, -1, 0.35), (0.05, 0.7, -1), (0.0, -1, -0.2))  # rom_audit "crouch"
bpy.context.view_layer.update()
bpy.context.scene.display.shading.show_cavity = False
tgt = r.head("calf_l")
for view, d, clothed in (("side", Vector((1, -0.2, 0.05)), True), ("front", Vector((0.3, -1, 0.3)), True),
                         ("side_skin", Vector((1, -0.2, 0.05)), False)):
    for g in r.garments:
        g.hide_render = not clothed
    R.look(cam, tgt + d.normalized() * 0.45, tgt)
    bpy.context.scene.render.filepath = f"P:/FoA/Saved/RigShots/audit/knee_{TAG}_{view}.png"
    bpy.ops.render.render(write_still=True)
