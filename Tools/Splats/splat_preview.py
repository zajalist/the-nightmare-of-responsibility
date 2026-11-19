"""Offline review render of a splat-mesh glTF (what UE imports), no editor: Gaussian discs, weighted blended OIT.

  python Tools/Splats/splat_preview.py IN.gltf OUT.png                 # 4 views from the capture point + overview
  python Tools/Splats/splat_preview.py --selftest

Reads POSITION (quad centre), TEXCOORD_1.x (radius cm) and COLOR_0 (display rgb, opacity) of the first primitive.
Views: 'from the capture point' looks out from where an Aholo world's panorama camera stood (glTF origin before the
converter's offset, i.e. -offset_m from the sidecar), at 4 headings with 90 deg FOV; 'overview' looks down at 40 deg
from outside. Footprint alpha = opacity * exp(-2 (d/r)^2), the material's Opacity Mask curve without the dither.
shortcut: order-independent blending (McGuire weighted OIT) instead of a sort, fine for review, not for colour QA.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

W, H = 480, 360


def load(path):
    doc = json.load(open(path, encoding='utf-8'))
    blob = open(os.path.join(os.path.dirname(path), doc['buffers'][0]['uri']), 'rb').read()
    attrs = doc['meshes'][0]['primitives'][0]['attributes']

    def acc(key, nc):
        a = doc['accessors'][attrs[key]]
        v = doc['bufferViews'][a['bufferView']]
        return np.frombuffer(blob, '<f4', a['count'] * nc, v['byteOffset']).reshape(-1, nc)[::4]  # one per quad
    side = os.path.splitext(path)[0] + '.splatmesh.json'
    off = json.load(open(side))['offset_m'] if os.path.exists(side) else [0, 0, 0]
    return acc('POSITION', 3).astype(np.float64), acc('TEXCOORD_1', 2)[:, 0] / 100.0, acc('COLOR_0', 4), -np.array(off)


def look(eye, target):
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, [0.0, 1.0, 0.0])
    r = r / np.linalg.norm(r) if np.linalg.norm(r) > 1e-6 else np.array([1.0, 0, 0])
    return np.stack([r, np.cross(r, f), f])  # rows: right, up, forward


def render(P, R, C, eye, rot, fov_deg=90.0, bg=(0.08, 0.08, 0.08), rmax=14):
    q = (P - eye) @ rot.T
    z = q[:, 2]
    ok = z > 0.05
    q, z, R, C = q[ok], z[ok], R[ok], C[ok]
    fpx = (W / 2) / math.tan(math.radians(fov_deg) / 2)
    u, v = W / 2 + fpx * q[:, 0] / z, H / 2 - fpx * q[:, 1] / z
    rp = np.clip(fpx * R / z, 0.5, rmax)                    # footprint radius in px (quad half-size)
    inside = (u > -rmax) & (u < W + rmax) & (v > -rmax) & (v < H + rmax)
    u, v, z, rp, C = u[inside], v[inside], z[inside], rp[inside], C[inside]
    wz = np.clip(10.0 / (1e-5 + (z / 5) ** 2 + (z / 200) ** 6), 1e-2, 3e3)   # McGuire depth weight
    acc, wsum, logt = np.zeros((H * W, 3)), np.zeros(H * W), np.zeros(H * W)
    for k in range(1, rmax + 1):                            # bucket by integer radius, one offset kernel per bucket
        sel = np.nonzero(np.ceil(rp) == k)[0]
        if not len(sel):
            continue
        for dy in range(-k, k + 1):
            for dx in range(-k, k + 1):
                x, y = np.round(u[sel]).astype(int) + dx, np.round(v[sel]).astype(int) + dy
                d2 = ((x - u[sel]) ** 2 + (y - v[sel]) ** 2) / rp[sel] ** 2
                m = (x >= 0) & (x < W) & (y >= 0) & (y < H) & (d2 <= 1.0)
                if not m.any():
                    continue
                s = sel[m]
                a = np.minimum(C[s, 3] * np.exp(-2.0 * d2[m]), 0.99)
                pix = y[m] * W + x[m]
                np.add.at(acc, pix, (a * wz[s])[:, None] * C[s, :3])
                np.add.at(wsum, pix, a * wz[s])
                np.add.at(logt, pix, np.log1p(-a))
    t = np.exp(logt)[:, None]
    col = acc / np.maximum(wsum, 1e-9)[:, None] * (1 - t) + np.array(bg) * t
    return (np.clip(col, 0, 1).reshape(H, W, 3) * 255).astype(np.uint8)


def sheet(path, out):
    P, R, C, eye = load(path)
    centre = np.median(P, 0)
    tiles = []
    for yaw in (0, 90, 180, 270):
        d = np.array([math.sin(math.radians(yaw)), 0.0, -math.cos(math.radians(yaw))])
        tiles.append(render(P, R, C, eye, look(eye, eye + d)))
    span = np.percentile(np.linalg.norm(P - centre, axis=1), 90)
    ov = centre + np.array([0.0, math.sin(math.radians(40)), math.cos(math.radians(40))]) * span * 2.2
    tiles.append(render(P, R, C, ov, look(ov, centre), fov_deg=60))
    tiles.append(np.full((H, W, 3), 20, np.uint8))
    img = np.vstack([np.hstack(tiles[0:3]), np.hstack(tiles[3:6])])
    Image.fromarray(img).save(out)
    print(out, f'{len(P)} splats, capture point {np.round(eye, 3).tolist()}, centre {np.round(centre, 3).tolist()}')


def selftest():
    P = np.array([[0.0, 0.0, -2.0], [0.0, 0.0, 2.0]])     # one red splat ahead, one behind the camera
    C = np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]], np.float32)
    img = render(P, np.array([0.2, 0.2]), C, np.zeros(3), look(np.zeros(3), np.array([0.0, 0.0, -1.0])))
    mid = img[H // 2, W // 2]
    assert mid[0] > 200 and mid[1] < 60, mid                 # red, centred; the splat behind is culled
    assert tuple(img[5, 5]) == (20, 20, 20), img[5, 5]      # background corner
    print('selftest OK')


if __name__ == '__main__':
    selftest() if '--selftest' in sys.argv else sheet(sys.argv[1], sys.argv[2])
