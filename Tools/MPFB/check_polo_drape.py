"""Compare the draped polo with its source: the collar and shoulders (torso z > 1.38 m) must not move; prints the
move per height band and renders front/side/3-4 stills of both on the MPFB stage (read-only on both blends).
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend P:/FoA-Assets/character/mpfb/teen/foa_teen_polo_drape.blend Tools/MPFB/check_polo_drape.py"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
SRC = 'P:/FoA-Assets/character/mpfb/teen/foa_teen_underarm_wedge_review.blend'
shirt = next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
with bpy.data.libraries.load(SRC) as (src, dst):
    dst.meshes = [shirt.data.name]
old = dst.meshes[0]
a = np.array([shirt.matrix_world @ v.co for v in old.vertices])
b = np.array([shirt.matrix_world @ v.co for v in shirt.data.vertices])
names = {g.index: g.name for g in shirt.vertex_groups}
arm = np.array([sum(g.weight for g in v.groups if names.get(g.group, '').startswith(('upperarm', 'lowerarm')))
                for v in shirt.data.vertices])
d = np.linalg.norm(b - a, axis=1) * 1000
z = a[:, 2]
out = dict(collar_shoulder_max_mm=round(float(d[(z > 1.38) & (arm < 0.3)].max()), 3),
           bands=[dict(z=round(float(z0), 2), max_mm=round(float(d[(z >= z0) & (z < z0 + 0.08)].max()), 1),
                       mean_mm=round(float(d[(z >= z0) & (z < z0 + 0.08)].mean()), 1))
                  for z0 in np.arange(0.94, 1.62, 0.08) if ((z >= z0) & (z < z0 + 0.08)).any()],
           sleeves_max_mm=round(float(d[arm > 0.5].max()), 1))
print('check', json.dumps(out))
json.dump(out, open('P:/FoA/Saved/CharacterShots/polo_drape/check.json', 'w'), indent=1)
assert out['collar_shoulder_max_mm'] < 0.5, 'collar or shoulders moved'
