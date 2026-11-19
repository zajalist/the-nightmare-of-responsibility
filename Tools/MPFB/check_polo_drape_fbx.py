"""FBX contract for the polo drape (run in Blender's Python for io_scene_fbx; no scene needed):
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/MPFB/check_polo_drape_fbx.py
Old = export/teen_underarm_wedge (the live SK_Teen_Polo), new = export/teen_polo_drape. Topology, UVs, material
slots, bones/reference pose, cluster bind matrices and every skin weight must be identical; only positions move,
at most 4 cm, and none above z 138 cm on the torso (collar and shoulders)."""
import json
from pathlib import Path

import numpy as np
from io_scene_fbx import parse_fbx

root = Path('P:/FoA-Assets/character/mpfb/export')


def read(p):
    return next(e for e in parse_fbx.parse(str(p))[0].elems if e.id == b'Objects').elems


def kids(e):
    return {v.id: v for v in e.elems}


def arr(e, n):
    return np.array(kids(e)[n].props[0])


def sig(e):
    return (e.id, tuple(str(list(p) if hasattr(p, 'tolist') else p) for p in e.props), tuple(sig(c) for c in e.elems))


old, new = [read(root / v / 'SK_Teen_Polo.fbx') for v in ('teen_underarm_wedge', 'teen_polo_drape')]
a, b = [next(e for e in rows if e.id == b'Geometry' and e.props[-1] == b'Mesh') for rows in (old, new)]
va, vb = [arr(e, b'Vertices').reshape(-1, 3) for e in (a, b)]
assert va.shape == vb.shape
assert np.array_equal(arr(a, b'PolygonVertexIndex'), arr(b, b'PolygonVertexIndex')), 'topology changed'
for tag in (b'LayerElementUV', b'LayerElementMaterial'):
    assert sig(kids(a)[tag]) == sig(kids(b)[tag]), tag


def bones(rows):
    return {e.props[1]: sig(kids(e)[b'Properties70']) for e in rows if e.id == b'Model' and e.props[-1] == b'LimbNode'}


assert bones(old) == bones(new), 'reference pose changed'


def clusters(rows):
    return [e for e in rows if e.id == b'Deformer' and e.props[-1] == b'Cluster']


changed = 0
for x, y in zip(clusters(old), clusters(new)):
    for n in (b'Transform', b'TransformLink'):
        assert np.array_equal(arr(x, n), arr(y, n)), n
    w = []
    for e in (x, y):
        row = np.zeros(len(va))
        if b'Indexes' in kids(e):
            row[arr(e, b'Indexes')] = arr(e, b'Weights')
        w.append(row)
    changed += int((abs(w[0] - w[1]) > 1e-7).sum())
assert changed == 0, f'{changed} weights changed'
d = np.linalg.norm(vb - va, axis=1)
# FBX positions are the Blender mesh axes in centimetres (z up here, as in the blend)
print('extent cm', np.ptp(va, axis=0).round(1), 'max', va.max(0).round(1))
high = va[:, 2] > 138.0
torso_high = high & (np.abs(va[:, 0]) < 16)
res = dict(vertices=len(va), moved=int((d > 1e-3).sum()), max_shift_cm=round(float(d.max()), 2),
           collar_max_shift_cm=round(float(d[torso_high].max()), 4) if torso_high.any() else 0.0,
           weights_changed=changed, topology_uv_materials_bind_refpose_unchanged=True)
assert res['max_shift_cm'] < 4.0 and res['collar_max_shift_cm'] < 1e-3, res
Path('P:/FoA/Saved/CharacterShots/polo_drape/fbx_validation.json').write_text(json.dumps(res, indent=2))
print('FBX_OK', res)
