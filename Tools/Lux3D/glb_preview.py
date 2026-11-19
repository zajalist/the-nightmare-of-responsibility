"""Offline turnaround of a Lux3D GLB (no editor): textured faces drawn with matplotlib from three views, so a generation
can be accepted or rejected before it is imported.
  python Tools/Lux3D/glb_preview.py <item> [<item> ...]  ->  Saved/WorldShots/lux3d/<item>_preview.png
Views are in UE axes (glTF x, z, y -> UE x, y, z; Z up): front (-Y), side (+X), three-quarter from above."""
import os
import sys

import matplotlib
import numpy as np
import trimesh

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

OUT = 'P:/FoA/Saved/WorldShots/lux3d'
os.makedirs(OUT, exist_ok=True)
for item in sys.argv[1:]:
    sc = trimesh.load(f'P:/FoA-Assets/lux3d/{item}/textured.glb')
    m = sc.dump(concatenate=True) if hasattr(sc, 'dump') else sc
    v = m.vertices[:, [0, 2, 1]] * 100.0            # UE cm, Z up
    f = m.faces
    uv = getattr(m.visual, 'uv', None)
    img = m.visual.material.baseColorTexture if hasattr(m.visual, 'material') else None
    if uv is not None and img is not None:
        tex = np.asarray(img.convert('RGB'), dtype=np.float32) / 255.0
        c = uv[f].mean(axis=1) % 1.0
        cols = tex[((1 - c[:, 1]) * (tex.shape[0] - 1)).astype(int), (c[:, 0] * (tex.shape[1] - 1)).astype(int)]
    else:
        cols = np.full((len(f), 3), 0.6)
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    shade = 0.55 + 0.45 * np.clip(n @ np.array([-0.4, -0.6, 0.7]) / np.linalg.norm([-0.4, -0.6, 0.7]), 0, 1)
    cols = np.clip(cols * shade[:, None], 0, 1)
    fig = plt.figure(figsize=(15, 5), dpi=110)
    lo, hi = v.min(0), v.max(0)
    r = (hi - lo).max() / 2
    mid = (hi + lo) / 2
    for k, (el, az, name) in enumerate(((0, -90, 'front -Y'), (0, 0, 'side +X'), (35, -55, 'three-quarter'))):
        ax = fig.add_subplot(1, 3, k + 1, projection='3d')
        ax.add_collection3d(Poly3DCollection(v[f], facecolors=cols, linewidths=0))
        for setl, i in ((ax.set_xlim, 0), (ax.set_ylim, 1), (ax.set_zlim, 2)):
            setl(mid[i] - r, mid[i] + r)
        ax.view_init(elev=el, azim=az)
        ax.set_box_aspect((1, 1, 1))
        ax.set_axis_off()
        ax.set_title(f'{item} {name}  {np.round(hi - lo, 1)} cm', fontsize=8)
    fig.savefig(f'{OUT}/{item}_preview.png', bbox_inches='tight')
    plt.close(fig)
    print(item, 'size cm', np.round(hi - lo, 1), 'faces', len(f), '->', f'{OUT}/{item}_preview.png')
