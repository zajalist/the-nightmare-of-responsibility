"""Crop a pie_ambience burst's raw window shots to the PIE viewport and cut them per event:
  python Tools/Splats/pie_ambience_media.py amb
-> Saved/WorldShots/pie_<plan>/<tag>_###.png, one <tag>.gif per event (2.5 fps) and <tag>_still.png (the frame with
the most sand, by default the one 60% of the way through). Frames pair with the log's 'shot' entries in order."""
import glob
import json
import os
import shutil
import sys

from PIL import Image

plan = sys.argv[1]
root = 'P:/FoA/Saved/WorldShots'
log = json.load(open(f'{root}/pie_{plan}.json'))
vp = next((e['vp'] for e in log if e['kind'] == 'vp'), None)
shots = [e for e in log if e['kind'] == 'shot']
raw = sorted(glob.glob(f'{root}/pie_{plan}_raw/*.png'))
assert len(raw) == len(shots) and shots, (len(raw), len(shots))
out = f'{root}/pie_{plan}'
shutil.rmtree(out, ignore_errors=True)  # a re-shoot replaces the last one's frames
os.makedirs(out, exist_ok=True)
print(len(raw), 'raw frames', len(shots), 'shots', 'vp', vp)
groups = {}
for f, s in zip(raw, shots):
    im = Image.open(f).convert('RGB')
    # Preserve full window captures: vp is desktop-relative, but these images
    # have no recorded window origin. Modulo is not a valid coordinate mapping.
    # A fixed 720 px fallback also discarded the upper third of 1080 px captures.
    tag = s['tag'].replace('Ev_', '')
    k = len(groups.setdefault(tag, []))
    p = f'{out}/{tag}_{k:03d}.png'
    im.save(p)
    groups[tag].append(p)
for tag, files in groups.items():
    frames = [Image.open(p).resize((640, round(640 * Image.open(p).height / Image.open(p).width))) for p in files]
    frames[0].save(f'{out}/{tag}.gif', save_all=True, append_images=frames[1:], duration=400, loop=0)
    Image.open(files[min(len(files) - 1, int(len(files) * 0.6))]).save(f'{out}/{tag}_still.png')
    print(tag, len(files), f'{out}/{tag}.gif')
