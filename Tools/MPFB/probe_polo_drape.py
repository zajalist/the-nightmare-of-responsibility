"""Read-only probe of the live polo source (the blend SK_Teen_Polo was last exported from): objects, polo size,
how tight the polo sits on the body per height band, and the sleeve hem band thickness.
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend P:/FoA-Assets/character/mpfb/teen/foa_teen_underarm_wedge_review.blend Tools/MPFB/probe_polo_drape.py"""
import json

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for p in rig.pose.bones:
    p.matrix_basis.identity()
bpy.context.view_layer.update()
print('objects', [(o.name, o.type, len(o.data.vertices) if o.type == 'MESH' else 0) for o in bpy.data.objects])
body = bpy.data.objects['Human']
shirt = next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
print('shirt modifiers', [(m.name, m.type) for m in shirt.modifiers], 'shape keys', bool(shirt.data.shape_keys))
P = np.array([shirt.matrix_world @ v.co for v in shirt.data.vertices])
bm = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
tree = BVHTree.FromPolygons([body.matrix_world @ v.co for v in bm.vertices], [list(f.vertices) for f in bm.polygons])
gap = np.array([(tree.find_nearest(p)[3] or 0) for p in P])
x, y, z = P.T
out = {'n': len(P), 'bbox': [P.min(0).tolist(), P.max(0).tolist()]}
groups = {g.index: g.name for g in shirt.vertex_groups}
arm = np.array([max([g.weight for g in v.groups if 'upperarm' in groups.get(g.group, '') or 'lowerarm' in groups.get(g.group, '')] or [0])
                for v in shirt.data.vertices])
out['vertex_groups'] = sorted(set(groups.values()))[:60]
bands = []
for z0 in np.arange(0.90, 1.56, 0.04):
    m = (z >= z0) & (z < z0 + 0.04) & (arm < 0.3)
    if m.any():
        front = m & (y < np.median(y[m]))
        bands.append(dict(z=round(float(z0), 2), n=int(m.sum()), gap_mm_med=round(float(np.median(gap[m]) * 1000), 1),
                          gap_mm_front=round(float(np.median(gap[front]) * 1000), 1) if front.any() else None,
                          y_front_min=round(float(y[m].min()), 3)))
out['bands'] = bands
sleeve = arm > 0.5
out['sleeve'] = dict(n=int(sleeve.sum()), gap_mm_med=round(float(np.median(gap[sleeve]) * 1000), 1),
                     gap_mm_p95=round(float(np.percentile(gap[sleeve], 95) * 1000), 1))
# boundary loops: the sleeve and waist openings
edges = {}
for e in shirt.data.edges:
    edges[e.key] = 0
for f in shirt.data.polygons:
    for k in f.edge_keys:
        edges[k] += 1
bnd = sorted({i for k, c in edges.items() if c == 1 for i in k})
out['boundary_verts'] = len(bnd)
bz = z[bnd]
out['boundary_z_hist'] = np.histogram(bz, bins=12)[0].tolist()
json.dump(out, open('P:/FoA/Saved/CharacterShots/polo_drape_probe.json', 'w'), indent=1)
print('wrote probe', json.dumps(out)[:1500])
