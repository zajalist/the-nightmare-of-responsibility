"""Animated look previews (lookdev lane): renders raw + looks A-D over the capture_seq.py sequence, then encodes
Saved/LookDev/anim/<look>.gif (960 px, 12 fps) and <look>.mp4 (1920 px, ping-pong loop).
  python Tools/LookDev/anim.py [A B ...]
A dream hiccup (line slip + one micro-tear) fires on two frames, as the calm-baseline glitch event does in game."""
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lookdev as L  # noqa: E402

SEQ = L.ROOT + "/" + os.environ.get("FOA_SEQ", "seq")          # FOA_SEQ=seq_wide FOA_REF=Shot_Wide for the wide move
REF = os.environ.get("FOA_REF", "Shot_ThirdPerson")               # the still whose exposure the sequence matches
OUT = L.ROOT + "/anim"
TAG = os.environ.get("FOA_TAG", "")                                # output suffix, e.g. _tp
FPS = 12
HICCUP = (17, 18)


def cv2_lum(path):
    return L.cv2.imread(path, L.cv2.IMREAD_UNCHANGED)[..., 2::-1] @ L.LW


def setup():
    """Point lookdev at the sequence: frame i is 'camera' f###, with its own pose, exposure and focus."""
    meta = json.load(open(SEQ + "/poses.json", encoding="utf-8"))
    L.SRC = SEQ
    d0 = L.cv2.imread(SEQ + "/f000_depth_0.exr", L.cv2.IMREAD_UNCHANGED)[..., 2]
    h, w = d0.shape
    focus0 = float(np.median(d0[h * 2 // 5:h * 3 // 5, w * 2 // 5:w * 3 // 5]))
    names = []
    # each capture's eye adaptation differs: match the reference still's brightness (75th percentile luminance)
    still = cv2_lum(f"{L.ROOT}/src/{REF}_color_0.exr") * L.EXPO[REF]
    expo = float(np.percentile(still, 75) / np.percentile(cv2_lum(SEQ + "/f000_color_0.exr"), 75))
    for i, (x, y, z, pitch, yaw, _t) in enumerate(meta["poses"]):
        n = f"f{i:03d}"
        L.POSE[n] = ((x, y, z), (pitch, yaw), meta["fov"])
        L.EXPO[n] = expo
        L.FOCUS[n] = focus0 - 2.0 * i  # the push moves the camera 2 cm a frame toward the subject
        names.append(n)
    return names


def job(args):
    key, i = args
    names = setup()
    n = names[i]
    if key == "raw":
        img = L.raw_frame(n)
    else:
        P = dict(L.LOOKS[key][2])
        if i in HICCUP:
            P.update(slip=max(P["slip"], 8), slip_bands=max(P["slip_bands"], 2), tear=max(P["tear"], 25),
                     tear_cols=max(P["tear_cols"], 1))
        img = L.render(n, P, t=i / FPS)
    L.save(img, f"{OUT}/frames{TAG}/{key}/{i:03d}.png")
    return key, i


def encode(key):
    """MP4: ping-pong loop at 1920 px. GIF: the forward pass only at 960 px; per-frame grain defeats GIF compression,
    so the GIF gets a light temporal denoise and a 64-colour palette (48 if it still tops 8 MB)."""
    src = f"{OUT}/frames{TAG}/{key}"
    n = len([f for f in os.listdir(src) if f[:1].isdigit()])
    for j, i in enumerate(list(range(n)) + list(range(n - 2, 0, -1))):  # ping-pong, so the loop has no jump
        shutil.copyfile(f"{src}/{i:03d}.png", f"{src}/pp{j:03d}.png")
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS)]
    subprocess.run(ff + ["-i", f"{src}/pp%03d.png", "-vf", "scale=1920:-2:flags=lanczos", "-c:v", "libx264",
                         "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", f"{OUT}/{key}{TAG}.mp4"], check=True)
    for dn, colors, dither in (("3:2:4:3", 64, "bayer:bayer_scale=5"), ("4:3:6:4", 48, "none")):
        subprocess.run(ff + ["-i", f"{src}/%03d.png", "-vf",
                             f"scale=960:-1:flags=lanczos,hqdn3d={dn},split[a][b];[a]palettegen=max_colors={colors}:"
                             f"stats_mode=diff[p];[b][p]paletteuse=dither={dither}:diff_mode=rectangle",
                             "-loop", "0", f"{OUT}/{key}{TAG}.gif"], check=True)
        if os.path.getsize(f"{OUT}/{key}{TAG}.gif") < 8e6:
            break
    return key, round(os.path.getsize(f"{OUT}/{key}{TAG}.gif") / 1e6, 2)


if __name__ == "__main__":
    keys = sys.argv[1:] or ["raw"] + list(L.LOOKS)
    names = setup()
    for k in keys:
        os.makedirs(f"{OUT}/frames{TAG}/{k}", exist_ok=True)
    with ProcessPoolExecutor(max_workers=5) as ex:
        for k, i in ex.map(job, [(k, i) for k in keys for i in range(len(names))]):
            if i == len(names) - 1:
                print("rendered", k, flush=True)
    for k in keys:
        print("encoded", *encode(k), "MB gif", flush=True)
