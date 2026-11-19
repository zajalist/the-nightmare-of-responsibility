"""Pack the Poly Haven fabric maps into one 1K RGBA texture per fabric for UE (inputs are downloads: python -I).
  python -I Tools/Cloth/pack_micro.py
R,G = tangent normal XY in DirectX convention (UE), Z rebuilt in the shader.
B   = albedo detail: luminance of diffuse x AO divided by its mean, 0.5 = mean (multiplies the garment albedo x2).
A   = roughness.
Writes P:/FoA-Assets/character/cloth/ue/T_Cloth_Micro_<Name>.png (BC7, sRGB off in UE)."""
import os
import sys
sys.path.append(os.path.expandvars(r"%APPDATA%\Python\Python314\site-packages"))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

SRC = "P:/FoA-Assets/character/cloth/src/"
OUT = "P:/FoA-Assets/character/cloth/ue/"
FABRICS = {"Pique": "waffle_pique_cotton", "Wool": "poly_wool_herringbone", "Flannel": "caban",
           "Poplin": "stretch_poplin", "Leather": "brown_leather"}
RES = 1024


def load(path, mode):
    return np.asarray(Image.open(path).convert(mode).resize((RES, RES), Image.LANCZOS), np.float32) / 255.0


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, pid in FABRICS.items():
        d = SRC + pid + "/" + pid
        n = load(d + "_nor_gl_2k.png", "RGB")
        diff = load(d + ("_albedo_2k.png" if os.path.exists(d + "_albedo_2k.png") else "_diff_2k.png"), "RGB")
        ao = load(d + "_ao_2k.png", "L")
        rough = load(d + "_rough_2k.png", "L")
        lum = (diff @ np.array([0.2126, 0.7152, 0.0722], np.float32)) * ao
        detail = np.clip(0.5 * lum / max(lum.mean(), 1e-4), 0, 1)
        rgba = np.dstack([n[..., 0], 1.0 - n[..., 1], detail, rough])   # GL -> DX: flip green
        path = OUT + "T_Cloth_Micro_" + name + ".png"
        Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(path)
        print("wrote", path, "rough mean %.2f" % rough.mean(), "detail sd %.3f" % detail.std())


main()
