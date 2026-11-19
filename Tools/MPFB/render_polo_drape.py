"""Before/after stills of the polo drape on the MPFB stage (front, 3/4, side), offline in Blender:
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend P:/FoA-Assets/character/mpfb/teen/foa_teen_polo_drape.blend Tools/MPFB/render_polo_drape.py
Before = the polo mesh of foa_teen_underarm_wedge_review.blend swapped in; after = the draped one.
Out: Saved/CharacterShots/polo_drape/{before,after}_{front,34,side}.png"""
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
from poses import reset  # noqa: E402
from stage import shoot, stage  # noqa: E402

OUT = 'P:/FoA/Saved/CharacterShots/polo_drape'
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
shirt = next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
for o in bpy.data.objects:  # render what the game renders: helpers and covered skin masked
    for m in getattr(o, 'modifiers', []):
        if m.type == 'MASK':
            m.show_viewport = m.show_render = True
reset(rig)
with bpy.data.libraries.load('P:/FoA-Assets/character/mpfb/teen/foa_teen_underarm_wedge_review.blend') as (src, dst):
    dst.meshes = [shirt.data.name]
before, after = dst.meshes[0], shirt.data
cam = stage(res=(700, 800))
target = rig.matrix_world @ rig.pose.bones['spine_02'].head + Vector((0, 0, 0.05))
for tag, mesh in (('before', before), ('after', after)):
    shirt.data = mesh
    for view, yaw in (('front', 0), ('34', 35), ('side', 90)):
        shoot(cam, target, 1.45, yaw, 50, f'{OUT}/{tag}_{view}.png')
