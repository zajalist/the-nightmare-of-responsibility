"""T1 proof run: load the user's teen, measure tee/pants (and every other pair) clipping in 8 poses, run the layering
pass, measure again, render waist close-ups, save the layered character (never the user's file).
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/MPFB/layer_garments.py [mhm=<path>]
Out: Saved/CharacterShots/mpfb/layering/report.json + waist_<pose>_<view>.png, character/mpfb/teen/foa_teen_layered.blend"""
import json
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
from layering import body_region, check_pair, garment_pairs, garments, layer_all, rest_dirs  # noqa: E402
from load_teen import MHM, load_teen  # noqa: E402
from mpfb_common import ASSETS, SHOTS, args, ensure_dir  # noqa: E402
from poses import POSES, apply_pose, reset  # noqa: E402
from stage import shoot, stage  # noqa: E402

opts = dict(a.split("=", 1) for a in args() if "=" in a)
out = ensure_dir(os.path.join(SHOTS, "layering"))
body, rig = load_teen(opts.get("mhm", MHM))
pairs = garment_pairs(rig)
print("pairs (outer, inner):", [(o.name, i.name) for o, i in pairs])
checks = pairs + [(g, body) for g in garments(rig)]  # garment over garment, and skin showing through each garment


def measure(label):
    reset(rig)
    dirs = {inner.name: rest_dirs(inner, rig) for _, inner in checks}
    regions = {g.name: body_region(g, rig) for g, inner in checks if inner is body}
    rows = {}
    for pose in POSES:
        apply_pose(rig, body, pose)
        for outer, inner in checks:
            region = regions.get(outer.name) if inner is body else None
            n, worst, covered = check_pair(outer, inner, rig, dirs[inner.name], region)
            rows[f"{pose}|{outer.name}>{inner.name}"] = dict(outside=n, worst_mm=round(worst, 2), covered=covered)
            print(f"{label:6} {pose:10} {outer.name} > {inner.name}: outside {n:5d}  worst {worst:6.2f} mm  (covered {covered})")
    reset(rig)
    return rows


before = measure("BEFORE")
layer_all(rig)
after = measure("AFTER")
total_before = sum(r["outside"] for r in before.values())
total_after = sum(r["outside"] for r in after.values())
print(f"TOTAL outside verts: before {total_before}, after {total_after}")
with open(os.path.join(out, opts.get("report", "report") + ".json"), "w", encoding="utf-8") as f:
    json.dump(dict(mhm=opts.get("mhm", MHM), pairs=[(o.name, i.name) for o, i in pairs], before=before, after=after,
                   total_before=total_before, total_after=total_after), f, indent=1)

if opts.get("renders", "1") == "1":
    cam = stage(res=(800, 800))
    for pose in ("rest", "crouch", "twist_l30", "sit"):
        apply_pose(rig, body, pose)
        waist = rig.matrix_world @ rig.pose.bones["pelvis"].head + Vector((0, 0, 0.12))
        for view, yaw in (("front", 0), ("side", 90), ("back", 180)):
            shoot(cam, waist, 1.0, yaw, 50, f"{out}/{opts.get('report', 'report').replace('report', 'waist')}_{pose}_{view}.png")
    reset(rig)
    for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA")]:
        bpy.data.objects.remove(o)

if "mhm" in opts and "save" not in opts:  # a test variant: don't overwrite the real layered character
    sys.exit(0)
blend = os.path.join(ensure_dir(os.path.join(ASSETS, "teen")), opts.get("save", "foa_teen_layered") + ".blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("saved", blend)
