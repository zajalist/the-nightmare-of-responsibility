"""Builds the devlog clock loop from render_clock_loop.py's frames: the clock repeats exactly every N frames but the
mound strands do not, so the last K frames crossfade into the first K (all inside the clock's hold) and are dropped.
  python Tools/Splats/loop_media.py [N=82] [K=8]
Writes Saved/Devlog/clock_loop.mp4 (full resolution, 15 fps) and clock_loop.gif (960 px, palettegen + paletteuse
sierra2_4a, temporal denoise first so the dither does not crawl; kept under 10 MB)."""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

N = int(sys.argv[1]) if len(sys.argv) > 1 else 82
K = int(sys.argv[2]) if len(sys.argv) > 2 else 8
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved")
SRC = os.path.join(ROOT, "Screenshots", "WindowsEditor", "FoA_clockloop_%03d.png")
OUT = os.path.join(ROOT, "Devlog")
os.makedirs(OUT, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="clockloop_")
for j in range(N - K):
    a = np.asarray(Image.open(SRC % j).convert("RGB"), np.float32)
    if j < K:
        w = (j + 1) / (K + 1)
        a = np.asarray(Image.open(SRC % (N - K + j)).convert("RGB"), np.float32) * (1 - w) + a * w
    Image.fromarray(a.round().astype(np.uint8)).save(os.path.join(tmp, f"f_{j:03d}.png"))
seq = os.path.join(tmp, "f_%03d.png")
mp4, gif = os.path.join(OUT, "clock_loop.mp4"), os.path.join(OUT, "clock_loop.gif")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "15", "-i", seq, "-c:v", "libx264", "-crf", "16",
                "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4], check=True)
for colors in (128, 96, 64):
    vf = (f"scale=960:-1:flags=lanczos,hqdn3d=1:1:6:6,split[a][b];[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
          "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "15", "-i", seq, "-vf", vf, "-loop", "0", gif], check=True)
    if os.path.getsize(gif) < 10e6:
        break
print(mp4, os.path.getsize(mp4))
print(gif, os.path.getsize(gif), "colors", colors, "frames", N - K)
