"""Where are the finger joints on the skin? Measures wrist->knuckle->PIP->DIP->tip for the Teen and the Manny (tips from
the mesh), and renders the left hand with the joint centres drawn as spheres (top and side), Teen and Manny.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/hand_joints.py [teen=<body.fbx>] [tag=before]"""
import json
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
sys.argv += ["out=P:/FoA/Saved/RigShots/audit/_diag", "who=manny", "poses=rest"]
import rom_audit as R  # noqa: E402  (its main() renders one rest frame; we rebuild the scene below)

TAG = R.A.get("tag", "before")
OUT = "P:/FoA/Saved/RigShots/audit"
R.wipe()
cam = R.setup_render()
rigs = [R.Rig("teen", R.TEEN), R.Rig("manny", R.MANNY)]
rigs[1].ob.location.x += 3.0
bpy.context.view_layer.update()
for r in rigs:
    r.rest = {b.name: r.ob.matrix_world @ b.matrix_local for b in r.ob.data.bones}
report = {}
mat = bpy.data.materials.new("joint")
mat.diffuse_color = (1, 0.15, 0.1, 1)
for r in rigs:
    dom, _ = R.labels(r)
    co, _ = R.evaluated(r.body)
    rep = {}
    for dg in R.DIGITS:
        b3 = f"{dg}_03_l"
        d = (r.rest_head(b3) - r.rest_head(f"{dg}_02_l")).normalized()
        tipv = max((co[i] for i, n in enumerate(dom) if n == b3), key=lambda p: (p - r.rest_head(b3)).dot(d))
        tip = r.rest_head(b3) + d * (tipv - r.rest_head(b3)).dot(d)
        j = [r.rest_head("hand_l")] + [r.rest_head(f"{dg}_{k}_l") for k in ("01", "02", "03")] + [tip]
        seg = [round((j[i + 1] - j[i]).length * 100, 2) for i in range(4)]
        finger = sum(seg[1:])
        rep[dg] = {"wrist_to_01_cm": seg[0], "P1_cm": seg[1], "P2_cm": seg[2], "P3_cm": seg[3],
                   "P1_share_of_finger": round(seg[1] / finger, 3), "knuckle_share_of_hand": round(seg[0] / (seg[0] + finger), 3)}
        for p in j[1:4]:  # joint markers
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0045, location=p, segments=12, ring_count=8)
            s = bpy.context.object
            s.name = r.tag + "_joint"
            s.data.materials.append(mat)
    report[r.tag] = rep
    print(r.tag, json.dumps(rep))
bpy.context.scene.display.shading.color_type = "MATERIAL"
for m in bpy.data.materials:
    if m.name != "joint":
        m.diffuse_color = (0.78, 0.74, 0.70, 0.55)
bpy.context.scene.display.shading.show_xray = True
bpy.context.scene.display.shading.xray_alpha = 0.55
for r in rigs:
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = not o.name.startswith(r.tag)
    tgt = (r.rest_head("middle_01_l") + r.rest_head("hand_l")) / 2
    n = r.world("hand_l", r.axes["hand_l"]["n"])
    for view, v in (("top", -n), ("side", r.world("hand_l", r.axes["hand_l"]["k"]) * -1)):
        R.look(cam, tgt + v.normalized() * 0.32, tgt)
        bpy.context.scene.render.filepath = f"{OUT}/hand_joints_{TAG}_{view}_{r.tag}.png"
        bpy.ops.render.render(write_still=True)
json.dump(report, open(f"{OUT}/hand_joints_{TAG}.json", "w"), indent=1)
