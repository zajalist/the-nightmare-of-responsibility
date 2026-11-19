"""Credits lane, offline: contact sheet of look-dev .hdr captures through the same tone curve as M_UI_CreditsShowcase
(luminance x Exposure, x/(1+x), ^Contrast, x Tint), on the roll's black.
  python Tools/Unreal/ui/credits_showcase_sheet.py <dir> [exposure] [contrast]   -> <dir>/sheet.png"""
import glob
import os
import sys

import cv2
import numpy as np

TINT = np.array([0.90, 0.94, 0.96])  # BGR of (0.96, 0.94, 0.90)


def tone(hdr, exposure, contrast):
    lum = hdr[..., 2] * 0.2126 + hdr[..., 1] * 0.7152 + hdr[..., 0] * 0.0722  # cv2 reads BGR
    x = lum * exposure
    y = (x / (1 + x)) ** contrast
    return (y[..., None] * TINT) ** (1 / 2.2)  # Slate treats a UI material's Final Color as linear


def main(folder, exposure=1.0, contrast=1.3):
    files = sorted(glob.glob(os.path.join(folder, '*.hdr')))
    assert files, folder
    tiles = []
    for f in files:
        img = tone(cv2.imread(f, cv2.IMREAD_UNCHANGED).astype(np.float32), exposure, contrast)
        img = cv2.resize((np.clip(img, 0, 1) * 255).astype(np.uint8), (256, 256), interpolation=cv2.INTER_AREA)
        cv2.putText(img, os.path.basename(f)[:-4], (6, 248), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 90, 90), 1)
        tiles.append(img)
    cols = 6
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
    out = os.path.join(folder, 'sheet.png')
    cv2.imwrite(out, sheet)
    print(out, sheet.shape)


if __name__ == '__main__':
    main(sys.argv[1], *(float(a) for a in sys.argv[2:]))
