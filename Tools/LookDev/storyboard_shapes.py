"""Hand-painted charcoal figures for intro panels whose actor can't be captured yet (marked as paint-overs)."""
import cv2
import numpy as np

import lookdev as L
import panels as Pn


def hooded_poly(cx, base, hgt, lean=0.0):
    """A hooded, robed figure: hood peak, bowed head, shoulders, robe widening to a torn hem (image coordinates)."""
    s = hgt / 100.0
    pts = [(-6, 0), (-9, -6), (-10, -14), (-6, -19), (0, -21), (5, -18), (8, -12), (9, -6), (13, 4), (16, 30),
           (19, 60), (22, 85), (25, 100), (14, 97), (8, 100), (0, 96), (-8, 100), (-15, 97), (-24, 100), (-20, 80),
           (-16, 50), (-13, 25), (-10, 6)]
    return np.int32([(cx + (px + lean * (py + 21) / 121 * 10) * s, base - (100 - py) * s * 0.83) for px, py in pts])


def hooded_layer(layers, cx, base, hgt, box):
    mid = layers["mid"].copy()
    h, w = mid.shape[:2]
    x0, y0, x1, y1 = box
    sub = mid[y0:y1, x0:x1]
    dark = (sub[..., :3] @ L.LW) < 0.35                  # the staged mesh is dark; the bed linen is light
    sub[..., 3] = np.where(dark, 0.0, sub[..., 3])
    layers["mid"] = mid
    m = np.zeros((h, w), np.float32)
    cv2.fillPoly(m, [hooded_poly(cx, base, hgt, lean=0.4)], 1.0, cv2.LINE_AA)
    m = L.blur(m, 0.7)
    grain = L.sample_noise(*np.meshgrid(np.arange(w) / 160.0, np.arange(h) / 160.0), 3)
    hem = np.clip((np.arange(h)[:, None] - (base - hgt * 0.12)) / (hgt * 0.12), 0, 1)   # the hem frays into sand
    a = np.clip(m * (1 - hem * (grain > 0.45)), 0, 1)
    rim = np.clip(L.blur(m, 2) - L.blur(m, 9), 0, 1) * (np.arange(w)[None, :] < cx)      # window light on its left edge
    col = Pn.INK * (0.9 + 0.3 * grain[..., None]) + Pn.PAPER * rim[..., None] * 0.9
    layers["figure"] = np.dstack([col.astype(np.float32), a.astype(np.float32)])
    return layers
