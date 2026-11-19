"""Offline twin of the in-engine thumb test: fist and power grip with the thumb tip RESTING on the index's middle
phalanx, fitted against the real skin (no thumb vertex inside the index/middle fingers), then rendered close so a thin
thumb tip can be told apart from an intersection. Prints the fitted angles and the mesh clearance.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/thumb_test.py [teen=<body.fbx>]"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
sys.argv += ["out=P:/FoA/Saved/RigShots/audit/_diag", "who=manny", "poses=rest"]
import rom_audit as R  # noqa: E402

R.TEEN = R.A.get("teen", "P:/FoA-Assets/character/mpfb/export/teen_rigfix/SK_Teen_Body.fbx")
R.wipe()
cam = R.setup_render()
bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 900
r = R.Rig("teen", R.TEEN)
dom, _ = R.labels(r)
idx_faces = [p.index for p in r.body.data.polygons if all(dom[v].startswith(("index_0", "middle_0")) and dom[v].endswith("_r") for v in p.vertices)]
thumb_v = [i for i, d in enumerate(dom) if d in ("thumb_03_r", "thumb_02_r")]
tip_v = [i for i, d in enumerate(dom) if d == "thumb_03_r"]


def mesh_state():
    co, polys = R.evaluated(r.body)
    tree = BVHTree.FromPolygons(co, [polys[i] for i in idx_faces])
    worst = 1e9
    for i in thumb_v:
        loc, nrm, _, dist = tree.find_nearest(co[i])
        if loc is None:
            continue
        signed = dist if (co[i] - loc).dot(nrm) >= 0 else -dist
        worst = min(worst, signed)
    return co, worst


def set_thumb(a, b, c, d, e=0.0):
    for j in ("01", "02", "03"):
        r.ob.pose.bones[f"thumb_{j}_r"].matrix_basis.identity()
    bpy.context.view_layer.update()
    r.flex("thumb_01_r", a)
    r.spread("thumb_01_r", b)
    r.rot("thumb_01_r", r.dir("thumb_01_r"), e)  # roll: the opposition twist of the thumb metacarpal
    r.flex("thumb_02_r", c)
    r.flex("thumb_03_r", d)


def fit(label):
    i2, i3 = r.head("index_02_r"), r.head("index_03_r")
    centre = (r.head("hand_r") + r.head("index_01_r") + r.head("pinky_01_r")) / 3
    mid = (i2 + i3) / 2
    target = mid + (mid - centre).normalized() * 0.017

    def cost(x):
        set_thumb(*x)
        co, pen = mesh_state()  # cost
        tipp = max((co[i] for i in tip_v), key=lambda p: (p - r.head("thumb_03_r")).dot(r.dir("thumb_03_r")))
        return (tipp - target).length * 100 + 20 * max(0.0, -pen * 100 + 0.1), pen
    lo, hi = [-10, -40, -20, -20, -60], [80, 40, 70, 70, 60]
    gbest, gx = 1e9, None
    for start in ([30.0, 0.0, 20.0, 20.0, 0.0], [55.0, -15.0, 35.0, 25.0, 20.0], [60.0, 10.0, 45.0, 30.0, -20.0],
                  [45.0, 20.0, 25.0, 15.0, 30.0]):  # several starts: the thumb has local minima beside the index
        x = start
        best, _ = cost(x)
        for step in (10, 5, 2.5):
            improved = True
            while improved:
                improved = False
                for k in range(5):
                    for dv in (-step, step):
                        y = list(x)
                        y[k] = min(hi[k], max(lo[k], y[k] + dv))
                        c, _ = cost(y)
                        if c < best - 1e-4:
                            best, x, improved = c, y, True
        if best < gbest:
            gbest, gx = best, x
    set_thumb(*gx)
    co, pen = mesh_state()
    tipp = max((co[i] for i in tip_v), key=lambda p: (p - r.head("thumb_03_r")).dot(r.dir("thumb_03_r")))
    return {"pose": label, "thumb_01_curl": gx[0], "thumb_01_spread": gx[1], "thumb_02_curl": gx[2], "thumb_03_curl": gx[3],
            "thumb_01_roll": gx[4], "tip_to_target_mm": round((tipp - target).length * 1000, 1),
            "min_signed_clearance_mm": round(pen * 1000, 1)}


out = []
for label, curls in (("fist", R.hand_pose), ("grip", R.hand_pose)):
    r.reset()
    R.arms_fwd(r)
    curls(r, "r", label)
    out.append(fit(label))
    print("THUMB", json.dumps(out[-1]))
    n = r.world("hand_r", r.axes["hand_r"]["n"])
    k = r.world("hand_r", r.axes["hand_r"]["k"])
    tgt = (r.head("index_02_r") + r.head("thumb_03_r")) / 2
    for view, v in (("radial", -k + R.U * 0.3), ("front", r.dir("hand_r") + R.U * 0.2 - k * 0.3), ("palm", n - k * 0.4)):
        R.look(cam, tgt + v.normalized() * 0.22, tgt)
        bpy.context.scene.render.filepath = f"P:/FoA/Saved/RigShots/audit/thumb_{label}_{view}.png"
        bpy.ops.render.render(write_still=True)
json.dump(out, open("P:/FoA/Saved/RigShots/audit/thumb_test.json", "w"), indent=1)
