"""Lux3D textured GLB -> sand splat-mesh glTF (same channel layout as ply_to_splatmesh.py), for the world lane's
foreshadow silhouettes: the T8 shirt as a flat sand imprint on the floor, the T9 suit standing in sand.
  python Tools/Splats/glb_to_sandsplats.py the_shirt_enemy SM_SandShirtImprint --count 7000 --flat 0.25
  python Tools/Splats/glb_to_sandsplats.py suit_payoff SM_SandSuit --count 9000
  python Tools/Splats/glb_to_sandsplats.py --selftest
Area-weighted surface samples (trimesh) become one quad per grain; base at z 0, centred in x/y. --flat lays the
object on its back (its front up) and squashes its depth by that factor, so a shirt reads as a pressed imprint.
Output: P:/FoA-Assets/splatmesh/<name>.gltf/.bin/.splatmesh.json (Interchange import like the other splat meshes)."""
import argparse
import array
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ply_to_splatmesh import CORNER_UV, NUDGE_M, gltf_doc  # noqa: E402

LUX = 'P:/FoA-Assets/lux3d'
OUT = 'P:/FoA-Assets/splatmesh'


def sample(glb, n, seed):
    import trimesh
    m = trimesh.load(glb, force='mesh')
    g, _ = trimesh.sample.sample_surface(m, n, seed=seed)
    return np.asarray(g, dtype=np.float64)  # glTF metres, +Y up, front +Z


def place(g, flat):
    """glTF metres -> Unreal cm (x, y, z up). Standing: (x, z, y). Flat: lies on its back, glTF +Y (up) becomes
    Unreal +X (along the floor), glTF +Z (its front) becomes up, depth squashed by `flat`."""
    p = np.stack([g[:, 1], g[:, 0], g[:, 2] * flat], 1) if flat else np.stack([g[:, 0], g[:, 2], g[:, 1]], 1)
    p = p * 100.0
    lo, hi = p.min(0), p.max(0)
    return p - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]


def write(p, name, seed, radius_cm):
    """One quad per grain. glTF position = Unreal (x, z, y) / 100 (the importer swaps it back)."""
    rng = random.Random(seed)
    A = {k: array.array('f') for k in ('POSITION', 'NORMAL', 'TANGENT', 'COLOR_0') + tuple(f'TEXCOORD_{t}' for t in range(8))}
    idx, e = array.array('I'), NUDGE_M
    for i, (x, y, z) in enumerate(p):
        cx, cy, cz = x / 100.0, z / 100.0, y / 100.0
        A['POSITION'].extend((cx - e, cy - e, cz, cx + e, cy - e, cz, cx + e, cy + e, cz, cx - e, cy + e, cz))
        A['NORMAL'].extend((0.0, 1.0, 0.0) * 4)
        A['TANGENT'].extend((1.0, 0.0, 0.0, 1.0) * 4)
        A['TEXCOORD_0'].extend(CORNER_UV)
        A['TEXCOORD_1'].extend((radius_cm * (0.6 + 0.8 * rng.random()), min(max(rng.random(), 1e-3), 0.999)) * 4)
        for t in (2, 3, 4, 5, 6, 7):
            A[f'TEXCOORD_{t}'].extend((0.0, 0.0) * 4)
        v = 0.06 + 0.08 * rng.random()  # black sand, display space; the material tints it anyway
        A['COLOR_0'].extend((v, v, v, 0.95) * 4)
        b = 4 * i
        idx.extend((b, b + 1, b + 2, b, b + 2, b + 3))
    doc, blob = gltf_doc(A, idx, name)
    with open(f'{OUT}/{name}.bin', 'wb') as fh:
        fh.write(blob)
    with open(f'{OUT}/{name}.gltf', 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, separators=(',', ':'))
    lo, hi = p.min(0), p.max(0)
    side = {'generator': 'Tools/Splats/glb_to_sandsplats.py', 'splats': len(p), 'mode': 3,
            'rest_bounds_cm': {'min': lo.round(2).tolist(), 'max': hi.round(2).tolist()},
            'height_cm': round(float(hi[2]), 2), 'radius_cm': radius_cm}
    with open(f'{OUT}/{name}.splatmesh.json', 'w', encoding='utf-8') as fh:
        json.dump(side, fh, indent=1)
    return side


def selftest():
    g = np.array([[0.0, 0.0, 0.0], [0.5, 1.0, 0.1], [-0.5, 0.2, -0.1]])
    s = place(g, 0)
    assert np.allclose(s[:, 2].min(), 0) and np.allclose(s[:, 2].max(), 100), s     # glTF y (up) -> Unreal z
    f = place(g, 0.25)
    assert np.allclose(np.ptp(f[:, 2]), 5.0) and np.allclose(np.ptp(f[:, 0]), 100), f  # lies down, depth squashed
    assert abs(f[:, 1].min() + f[:, 1].max()) < 1e-9                                    # centred
    print('selftest ok')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('item', nargs='?')
    ap.add_argument('name', nargs='?')
    ap.add_argument('--count', type=int, default=8000)
    ap.add_argument('--flat', type=float, default=0.0)
    ap.add_argument('--radius', type=float, default=0.5, help='grain radius cm before RadiusScale')
    ap.add_argument('--seed', type=int, default=3)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    p = place(sample(f'{LUX}/{a.item}/textured.glb', a.count, a.seed), a.flat)
    print(a.name, write(p, a.name, a.seed, a.radius))


if __name__ == '__main__':
    main()
