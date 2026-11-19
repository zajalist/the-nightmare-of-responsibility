"""UV-space previews of the generated maps: mask as colour, folds lit by a raking light at phase 0 and 90 deg.
  python -I Tools/Cloth/preview_maps.py <bake_dir> <garment> <out.jpg>"""
import os
import sys
sys.path.append(os.path.expandvars(r"%APPDATA%\Python\Python314\site-packages"))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

bake, g, out = sys.argv[1:4]
m = np.asarray(Image.open(os.path.join(bake, g + "_mask.png")).convert("RGBA"), np.float32) / 255
f = np.asarray(Image.open(os.path.join(bake, g + "_folds_gl.png")).convert("RGBA"), np.float32) / 127.5 - 1
L = np.array([0.6, 0.5, 0.62]); L /= np.linalg.norm(L)
tiles = []
for phi in (0.0, np.pi / 2):
    xy = np.cos(phi) * f[..., :2] + np.sin(phi) * f[..., 2:]
    n = np.dstack([xy, np.ones(xy.shape[:2])]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    tiles.append(np.clip((n @ L) * 1.1, 0, 1)[..., None].repeat(3, 2))
cm = np.array([[1, 0.2, 0.2], [0.2, 1, 0.2], [0.3, 0.4, 1], [1, 0.9, 0.1]])
mc = np.clip(np.einsum("hwc,ck->hwk", m, cm), 0, 1)
mc = np.asarray(Image.fromarray((mc * 255).astype(np.uint8)).resize(tiles[0].shape[:2][::-1]), np.float32) / 255
strip = np.concatenate([mc] + tiles, 1)
Image.fromarray((strip * 255).astype(np.uint8)).resize((1536, 512)).save(out, quality=88)
print("wrote", out)
