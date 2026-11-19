"""Which teen vertices stick out of the back of the hand in a fist? Prints the worst stretched edges and the vertices
outside the rest hand surface, with their weights. Read-only.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/diag_fist.py [teen=<body.fbx>] [pose=fist]"""
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
sys.argv = [a for a in sys.argv if not a.startswith("out=")] + ["out=P:/FoA/Saved/RigShots/audit/_diag", "who=teen",
                                                                "poses=rest"]
import rom_audit as R  # noqa: E402  (its main() runs a 1-pose audit; harmless)

r = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith("teen"))
rig = R.Rig.__new__(R.Rig)
rig.ob, rig.tag = r, "teen"
rig.body = next(o for o in bpy.data.objects if o.type == "MESH" and o.name == "teen_SK_Teen_Body")
rig.garments = []
rig.names = {b.name for b in r.data.bones}
rig.reset()
rig.rest = {b.name: r.matrix_world @ b.matrix_local for b in r.data.bones}
rig.axes = {}
rig._anatomy()
dom, wts = R.labels(rig)
co0, polys = R.evaluated(rig.body)
pose = R.A.get("pose", "fist")
R.POSES_ALL = {"fist": lambda q: (R.arms_fwd(q), R.hand_pose(q, "l", "fist"))}
R.POSES_ALL["fist"](rig)
co, _ = R.evaluated(rig.body)
edges = {}
for p in polys:
    for a, b in zip(p, p[1:] + p[:1]):
        e = (min(a, b), max(a, b))
        l0 = (co0[a] - co0[b]).length
        if l0 > 1e-7 and e not in edges:
            edges[e] = (co[a] - co[b]).length / l0
worst = sorted(edges.items(), key=lambda kv: -kv[1])[:12]
rows = []
for (a, b), k in worst:
    rows.append({"edge": [a, b], "stretch": round(k, 2), "wa": {n: round(x, 2) for n, x in wts[a].items()},
                 "wb": {n: round(x, 2) for n, x in wts[b].items()}, "rest_len_mm": round((co0[a] - co0[b]).length * 1000, 1)})
    print(rows[-1])
json.dump(rows, open("P:/FoA/Saved/RigShots/audit/diag_fist.json", "w"), indent=1)

# colour by dominant bone: distal phalanges red, middle orange, proximal yellow, hand grey; render the back of the fist
me = rig.body.data
attr = me.color_attributes.get("diag") or me.color_attributes.new("diag", "FLOAT_COLOR", "POINT")
pal = {"03": (1, 0.1, 0.1, 1), "02": (1, 0.55, 0.1, 1), "01": (0.95, 0.9, 0.2, 1)}
for i, d in enumerate(dom):
    c = (0.7, 0.7, 0.7, 1)
    for j, col in pal.items():
        if f"_{j}_" in d:
            c = col
    attr.data[i].color = c
me.color_attributes.active_color = attr
sc = bpy.context.scene
sc.display.shading.color_type = "VERTEX"
sc.render.resolution_x = sc.render.resolution_y = 900
cam = sc.camera
for shot in ("hand_back", "hand_palm"):
    R.shoot(cam, rig, shot, f"P:/FoA/Saved/RigShots/audit/diag_fist_{shot}.png")
