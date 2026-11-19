"""Where does skin poke through the polo? Lists the body vertices the T1 counter flags per pose, with their rest
position and dominant bone (read-only).
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend <blend> Tools/MPFB/diag_polo_clip.py"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from layering import BODY_REACH, body_region, bvh, coverage, evaluated, posed_dirs, rest_dirs, unmasked, visible_mask  # noqa: E402
from poses import POSES, apply_pose, reset  # noqa: E402

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Human']
shirt = next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
# The T1 counter counts skin the game renders: this review blend has its Mask modifiers (helpers, Delete.*,
# Hidden_by.*) switched off for renders, so switch them back on, as in the exported pieces.
for o in bpy.data.objects:
    for m in getattr(o, 'modifiers', []):
        if m.type == 'MASK':
            m.show_viewport = True
reset(rig)
rest_co = np.array([body.matrix_world @ v.co for v in body.data.vertices])
names = {g.index: g.name for g in body.vertex_groups}
gb = body.vertex_groups['body'].index
print('body mask modifiers', [(m.name, m.vertex_group, m.show_viewport, m.invert_vertex_group) for m in body.modifiers if m.type == 'MASK'])
dirs0 = rest_dirs(body, rig)
region = body_region(shirt, rig)
out = {}
for pose in POSES:
    apply_pose(rig, body, pose)
    tree = bvh(shirt)[0]
    with unmasked(body):
        co, _ = evaluated(body)
    vis = visible_mask(body)
    cov = coverage(co, posed_dirs(body, rig, dirs0), tree, BODY_REACH)
    bad = [i for i, ok in enumerate(vis) if ok and i in region and cov[i][0] and cov[i][1] > 0]
    rows = []
    for i in bad:
        v = body.data.vertices[i]
        bone = max(v.groups, key=lambda g: g.weight) if v.groups else None
        rows.append(dict(i=i, rest=np.round(rest_co[i], 3).tolist(), mm=round(cov[i][1] * 1000, 1),
                         bone=names.get(bone.group) if bone else None, in_body=any(g.group == gb and g.weight > 0 for g in v.groups)))
    out[pose] = rows
    print(pose, len(rows), 'in body group:', sum(r['in_body'] for r in rows), [(r['rest'], r['mm']) for r in rows if r['in_body']][:10])
reset(rig)
json.dump(out, open('P:/FoA/Saved/CharacterShots/polo_drape/clip_diag.json', 'w'), indent=1)
