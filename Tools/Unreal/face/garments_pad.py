"""Battle garment base colours with edge padding (offline). The Lux3D bakes leave black between UV islands, which bleeds
into seams and lower mips as dark blotches. Push-pull fill: each island's colour spreads outward into the black.
  python Tools/Unreal/face/garments_pad.py   -> P:/FoA-Assets/character/garments/rig/padded/T_Garment_<Name>_BaseColor.png
Self-check: island pixels are unchanged and no pure-black texel is left."""
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path('P:/FoA-Assets/character/garments/rig')
OUT = SRC / 'padded'
OUT.mkdir(exist_ok=True)


def pad(rgb, mask):
    """Push-pull: average the known texels down a mip pyramid, then fill unknown texels from the coarser level."""
    if min(rgb.shape[:2]) <= 1:
        return rgb
    h, w = rgb.shape[:2]
    c = (rgb * mask[..., None]).reshape(h // 2, 2, w // 2, 2, 3).sum((1, 3))
    n = mask.reshape(h // 2, 2, w // 2, 2).sum((1, 3))
    coarse_mask = n > 0
    coarse = np.where(coarse_mask[..., None], c / np.maximum(n, 1)[..., None], 0.0)
    coarse = pad(coarse, coarse_mask.astype(np.float32))
    up = coarse.repeat(2, 0).repeat(2, 1)
    return np.where(mask[..., None] > 0, rgb, up)


for name in ('Shirt', 'Trousers', 'Sock', 'Tie'):
    img = np.asarray(Image.open(SRC / f'T_SK_Garment_{name}_basecolor.png').convert('RGB')).astype(np.float32) / 255.0
    mask = (img.max(-1) > 0.012).astype(np.float32)  # the islands; the bake background is pure black
    out = pad(img, mask)
    assert np.allclose(out[mask > 0], img[mask > 0]), 'island texels changed'
    assert (out.max(-1) > 0.005).all(), 'black texels left'
    Image.fromarray((out * 255 + 0.5).clip(0, 255).astype(np.uint8)).save(OUT / f'T_Garment_{name}_BaseColor.png')
    print(name, 'islands', round(float(mask.mean()), 3), '->', OUT / f'T_Garment_{name}_BaseColor.png')
