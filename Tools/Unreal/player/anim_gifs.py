"""Sorts a record_anim.sh burst's frames into its phases by file time against the '[anim] phase=<name> wall=<s>' log
marks and writes <tag>_still_back.png, <tag>_still_front.png, <tag>_loco.gif, <tag>_interact.gif, <tag>_idle.gif.
  python Tools/Unreal/player/anim_gifs.py Saved/AnimShots <tag>"""
import glob
import os
import re
import shutil
import sys

from PIL import Image

out, tag = sys.argv[1], sys.argv[2]
marks = [(m.group(1), float(m.group(2))) for m in
         re.finditer(r"phase=(\w+) wall=([\d.]+)", open(f"{out}/{tag}_events.txt", encoding="utf-8").read())]
frames = sorted(glob.glob(f"{out}/frames_{tag}/*.png"), key=os.path.getmtime)
assert frames and marks, f"{len(frames)} frames, {len(marks)} phase marks"


def phase_of(t):
    name = None
    for n, w in marks:
        if t >= w:
            name = n
    return name


by = {}
for f in frames:
    by.setdefault(phase_of(os.path.getmtime(f)), []).append(f)
print({k: len(v) for k, v in by.items()})
# the two stills are the single Shots taken at the end of 'settle' and 'swing' (they land in the next phase's window)
stills = [f for f in frames if phase_of(os.path.getmtime(f)) in ("swing", "loco")][:1] + \
         [f for f in by.get("loco", [])[:1]]
for f, name in zip(stills, ("still_back", "still_front")):
    shutil.copy(f, f"{out}/{tag}_{name}.png")


def gif(name, fs, width=800):
    if len(fs) < 3:
        print("skip", name, len(fs))
        return
    ts = [os.path.getmtime(f) for f in fs]
    ims = []
    for f in fs:
        im = Image.open(f).convert("RGB")
        ims.append(im.resize((width, round(im.height * width / im.width)), Image.LANCZOS).quantize(colors=128, method=Image.MEDIANCUT))
    dur = [max(40, min(250, round((ts[i + 1] - ts[i]) * 1000))) for i in range(len(ts) - 1)] + [400]
    ims[0].save(f"{out}/{tag}_{name}.gif", save_all=True, append_images=ims[1:], duration=dur, loop=0, optimize=True)
    print(name, len(fs), "frames", round(ts[-1] - ts[0], 1), "s ->", f"{out}/{tag}_{name}.gif",
          round(os.path.getsize(f"{out}/{tag}_{name}.gif") / 1e6, 1), "MB")


gif("loco", by.get("loco", [])[1:])
gif("interact", by.get("approach", []) + by.get("interact", []))
gif("idle", by.get("idle", []))
gif("sand", by.get("sand", []))
for name, fs in by.items():  # phases of other proof scripts (pie_screwdriver.py: kneel, game, close, side)
    if name not in ("loco", "approach", "interact", "idle", "sand", "swing", "settle", None):
        gif(name, fs)
