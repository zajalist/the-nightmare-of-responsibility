"""One FBX per take from SK_Garment_<G>_anim.blend, named SK_Garment_<G>Armature_<Take>.fbx so UE's classic FBX
importer names (and replaces in place) the AnimSequence exactly like the existing clips.
  run_blender.ps1 -Blend .../anim/SK_Garment_<G>_anim.blend Tools/Rig/garment_take_fbx.py garment=<G>"""
import os
import sys

import bpy

A = dict(x.split("=", 1) for x in sys.argv[sys.argv.index("--") + 1:] if "=" in x)
G = A["garment"]
OUT = "P:/FoA-Assets/character/garments/rig/anim/takes"
os.makedirs(OUT, exist_ok=True)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
for act in list(bpy.data.actions):
    arm.animation_data_create()
    arm.animation_data.action = act
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = int(act.frame_range[0]), int(act.frame_range[1])
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm  # armature only: with a mesh in the file UE imports a skeletal mesh
    path = f"{OUT}/SK_Garment_{G}Armature_{act.name}.fbx"
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE"}, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, path_mode="AUTO")
    print("TAKE_FBX", path, tuple(act.frame_range))
