"""Offline (run with python -I): measure the drive's Lux3D GLBs in UE axes (cm, Z up; glTF x, z, y -> UE x, y, z, the
same mapping as Tools/Lux3D/glb_preview.py) so they can be imported standing on Z=0, centred, and with the car's nose on
+X; for a sign, find its panel (the tallest band of z where the horizontal extent is at least 70% of the widest) and
the panel's thin axis (its facing). Writes P:/FoA-Assets/lux3d/drive_cars_signs/_measure.json.
  python -I Tools/Unreal/level2/drive_lux3d_inspect.py"""
import json
import os
import sys

sys.path.append(os.path.expanduser('~/AppData/Roaming/Python/Python314/site-packages'))
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

ROOT = 'P:/FoA-Assets/lux3d/drive_cars_signs'
out = {}
for item in sorted(os.listdir(ROOT)):
    glb = os.path.join(ROOT, item, 'textured.glb')
    if not os.path.isfile(glb):
        continue
    sc = trimesh.load(glb)
    m = sc.dump(concatenate=True) if hasattr(sc, 'dump') else sc
    v = m.vertices[:, [0, 2, 1]] * 100.0
    lo, hi = v.min(0), v.max(0)
    row = dict(tris=int(len(m.faces)), min=lo.round(1).tolist(), max=hi.round(1).tolist(),
               size=(hi - lo).round(1).tolist(), centre=((hi + lo) / 2).round(1).tolist())
    if item.startswith('sign'):
        wide = 0 if row['size'][0] >= row['size'][1] else 1
        zs = np.linspace(lo[2], hi[2], 41)
        widths = []
        for a, b in zip(zs, zs[1:]):
            band = v[(v[:, 2] >= a) & (v[:, 2] < b)]
            widths.append(float(np.ptp(band[:, wide])) if len(band) else 0.0)
        top = max(widths)
        # the panel: the contiguous run of wide bands down from the top (a wide footing below the posts is not it)
        first = max(i for i, w in enumerate(widths) if w >= .7 * top)
        last = first
        while last > 0 and widths[last - 1] >= .7 * top:
            last -= 1
        z0, z1 = float(zs[last]), float(zs[first + 1])
        # its face: the depth of the upper 40% of that run (a catwalk or ledge sits lower and sticks out)
        band = v[(v[:, 2] >= z1 - .4 * (z1 - z0)) & (v[:, 2] <= z1)]
        thin = 1 - wide
        row.update(wide_axis='XY'[wide], panel_z=[round(z0, 1), round(z1, 1)], panel_width=round(top, 1),
                   panel_depth=[round(float(band[:, thin].min()), 1), round(float(band[:, thin].max()), 1)])
    out[item] = row
    print(item, json.dumps(row))
json.dump(out, open(os.path.join(ROOT, '_measure.json'), 'w'), indent=1)
