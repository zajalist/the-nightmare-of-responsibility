"""Probe: load the teen MHM through MPFB and list garments, UVs, vertex groups, rest pose."""
import os, sys
sys.path.insert(0, "P:/FoA/Tools/MPFB")
import bpy
from load_teen import load_teen
mhm = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else None
body, rig = load_teen(mhm) if mhm else load_teen()
print("BODY", body.name, len(body.data.vertices))
for o in bpy.data.objects:
    if o.type == "MESH":
        print("OBJ", o.name, "parent", o.parent.name if o.parent else None, "v", len(o.data.vertices), "f", len(o.data.polygons),
              "uv", [u.name for u in o.data.uv_layers], "vg", len(o.vertex_groups), "mods", [m.type for m in o.modifiers],
              "mats", [m.name for m in o.data.materials if m])
for b in rig.data.bones:
    if b.name in ("pelvis","spine_01","spine_03","upperarm_l","lowerarm_l","hand_l","thigh_l","calf_l","foot_l","clavicle_l"):
        print("BONE", b.name, tuple(round(x,3) for x in b.head_local), tuple(round(x,3) for x in b.tail_local))
print("DIMS", tuple(round(x,3) for x in body.dimensions))
