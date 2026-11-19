"""Red/green check of fbx_io: re-export an SK_Teen FBX untouched and compare it with the original in Blender
(bones, vertices, normals, weights, slots, morphs). redcheck=1 moves one finger joint 1 cm first, and must FAIL.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/roundtrip_test.py src=<fbx> out=<fbx> [redcheck=1]"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import fbx_io  # noqa: E402

A = dict(x.split("=", 1) for x in sys.argv[sys.argv.index("--") + 1:] if "=" in x)


def compare(a, b):
    errs = []
    if set(a["bones"]) != set(b["bones"]):
        errs.append(("bone set", sorted(set(a["bones"]) ^ set(b["bones"]))))
    for n in a["bones"]:
        if n in b["bones"]:
            d = max(abs(x - y) for ra, rb in zip(a["bones"][n], b["bones"][n]) for x, y in zip(ra, rb))
            if d > 1e-3:
                errs.append(("bone", n, round(d, 5)))
    if len(a["verts"]) != len(b["verts"]):
        errs.append(("vert count", len(a["verts"]), len(b["verts"])))
    else:
        dv = max((p - q).length for p, q in zip(a["verts"], b["verts"]))
        if dv > 1e-3:
            errs.append(("verts moved cm", round(dv, 5)))
        dw = max(abs(wa.get(k, 0) - wb.get(k, 0)) for wa, wb in zip(a["weights"], b["weights"]) for k in set(wa) | set(wb))
        if dw > 2e-3:
            errs.append(("weights", round(dw, 5)))
    if a["normals"] and len(a["normals"]) == len(b["normals"]):
        dn = max(sum((x - y) ** 2 for x, y in zip(p, q)) ** 0.5 for p, q in zip(a["normals"], b["normals"]))
        if dn > 2e-2:
            errs.append(("normals", round(dn, 4)))
    if a["materials"] != b["materials"]:
        errs.append(("materials", a["materials"], b["materials"]))
    if a["shape_keys"] != b["shape_keys"]:
        errs.append(("shape keys", len(a["shape_keys"]), len(b["shape_keys"])))
    return errs


fbx_io.clear()
rig, meshes = fbx_io.load(A["src"])
mesh = meshes[0]
orig = fbx_io.snapshot(rig, mesh)
if A.get("redcheck") == "1":
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones["index_01_l"]
    eb.head.x += 1.0
    eb.tail.x += 1.0
    bpy.ops.object.mode_set(mode="OBJECT")
fbx_io.export(rig, mesh, A["out"])
fbx_io.clear()
rig2, meshes2 = fbx_io.load(A["out"])
errs = compare(orig, fbx_io.snapshot(rig2, meshes2[0]))
print("ROUNDTRIP", "FAIL" if errs else "PASS", errs[:12])
