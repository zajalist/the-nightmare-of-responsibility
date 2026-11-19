"""Offline: pick the ~30 Game Animation Sample (GASP) clips the anim lane imports, from the GASP project on disk.
  python Tools/Unreal/player/gasp_scan.py <GASP project folder> [--write]
Prints every candidate per slot (walk/jog loops, starts, stops, pivots, turn-in-place, idles and breaks) with sizes and
the pick; --write saves the pick to Saved/AnimShots/gasp_pick.json for gasp_copy.py. The masculine neutral set only
(M_Neutral_*), no crouch, traversal, strafe or weapons: what a tired man in a bedroom needs."""
import glob
import json

# The anim lane's fixed pick (2026-11-07): GASP's "Relaxed" set reads as the tired teen better than "Neutral".
# --fixed writes exactly these (paths under Content/Characters/UEFN_Mannequin/Animations) instead of the regex pick.
FIXED = [("walk_loop", "Walk/M_Relaxed_Walk_Loop_F"), ("jog_loop", "Run/M_Relaxed_Run_Loop_F"),
         ("walk_start", "Walk/M_Relaxed_Walk_Start_F_Lfoot"), ("walk_start", "Walk/M_Relaxed_Walk_Reface_Start_090_L_Lfoot"),
         ("walk_start", "Walk/M_Relaxed_Walk_Reface_Start_090_R_Rfoot"), ("walk_start", "Walk/M_Relaxed_Walk_Reface_Start_180_L_Lfoot"),
         ("walk_start", "Walk/M_Relaxed_Walk_Reface_Start_180_R_Rfoot"),
         ("walk_stop", "Walk/M_Relaxed_Walk_Stop_F_Lfoot"), ("walk_stop", "Walk/M_Relaxed_Walk_Stop_F_Rfoot"),
         ("walk_pivot", "Walk/M_Relaxed_Walk_Pivot_F_B_Lfoot"), ("walk_pivot", "Walk/M_Relaxed_Walk_Pivot_F_B_Rfoot"),
         ("jog_start", "Run/M_Relaxed_Run_Start_F_Lfoot"), ("jog_stop", "Run/M_Relaxed_Run_Stop_F_Lfoot"),
         ("turn_in_place", "Idle/M_Relaxed_Stand_Turn_090_L"), ("turn_in_place", "Idle/M_Relaxed_Stand_Turn_090_R"),
         ("turn_in_place", "Idle/M_Relaxed_Stand_Turn_180_L"), ("turn_in_place", "Idle/M_Relaxed_Stand_Turn_180_R"),
         ("idle", "Idle/M_Relaxed_Stand_Idle_Loop"), ("idle_breath", "Idle/M_Additive_Stand_Breath")] +         [("idle_break", f"Idle/M_Relaxed_Stand_Idle_Break_v{i:02d}") for i in (1, 2, 4, 5, 6, 7)]
import os
import re
import sys

root = sys.argv[1]
content = os.path.join(root, "Content")
assert os.path.isdir(content), f"no Content folder in {root}"
files = [f for f in glob.glob(os.path.join(content, "**", "*.uasset"), recursive=True)]
anims = [f for f in files if re.search(r"(^|[\\/])(M|MM|MF)?_?Neutral", f, re.I) or "Animations" in f]
SKIP = re.compile(r"crouch|travers|vault|mantle|climb|strafe|pistol|rifle|bow|sword|swim|jump|fall|land|_F_Neutral|Female|"
                  r"Feminine|LS_|Montage|_PoseSearch|PSD_|CHT_|Chooser|BlendSpace|BS_", re.I)
SLOTS = [  # slot, regex on the file name, how many to keep (best = shortest names first: the canonical clip)
    ("walk_loop", r"Walk_Loop_F\b|Walk_F_Loop|Walk_Fwd_Loop", 1),
    ("jog_loop", r"(Run|Jog)_Loop_F\b|(Run|Jog)_F_Loop", 1),
    ("walk_start", r"Walk_Start_F|Walk_Start_.*(L|R)(090|180)", 6),
    ("walk_stop", r"Walk_Stop_F|Walk_Stop", 2),
    ("walk_pivot", r"Walk_Pivot", 4),
    ("turn_in_place", r"(Stand|Idle).*Turn.*(090|180)|Turn_?In_?Place", 4),
    ("idle", r"Stand_Idle|Idle_Loop|Idle_Lp", 2),
    ("idle_break", r"Idle_Break|Fidget|Look_?Around|Tired|Breath|Stretch|Scratch", 6),
]
if "--fixed" in sys.argv:
    base = os.path.join(content, "Characters", "UEFN_Mannequin", "Animations")
    files = [(slot, os.path.join(base, rel.replace("/", os.sep) + ".uasset")) for slot, rel in FIXED]
    missing = [f for _, f in files if not os.path.exists(f)]
    assert not missing, missing
    print(f"FIXED {len(files)} clips, {sum(os.path.getsize(f) for _, f in files) / 1e6:.1f} MB raw")
    if "--write" in sys.argv:
        out = {"root": root, "clips": [{"slot": s, "package": "/Game/" + os.path.relpath(f, content)[:-7].replace(os.sep, "/")}
                                       for s, f in files]}
        json.dump(out, open("P:/FoA/Saved/AnimShots/gasp_pick.json", "w"), indent=1)
        print("written P:/FoA/Saved/AnimShots/gasp_pick.json")
    sys.exit(0)
pick, report = [], []
for slot, rx, keep in SLOTS:
    hits = sorted((f for f in anims if re.search(rx, os.path.basename(f), re.I) and not SKIP.search(f)),
                  key=lambda f: (len(os.path.basename(f)), f))
    report.append(f"## {slot}: {len(hits)} candidates")
    for f in hits[:12]:
        report.append(f"   {os.path.getsize(f) / 1e6:6.2f} MB  {os.path.relpath(f, content)}")
    pick += [(slot, f) for f in hits[:keep]]
print("\n".join(report))
total = sum(os.path.getsize(f) for _, f in pick)
print(f"\nPICK {len(pick)} clips, {total / 1e6:.1f} MB raw (the retargeted copies are re-compressed):")
for slot, f in pick:
    print(f"   {slot:14s} {os.path.relpath(f, content)}")
if "--write" in sys.argv:
    out = {"root": root, "clips": [{"slot": s, "package": "/Game/" + os.path.relpath(f, content)[:-7].replace(os.sep, "/")}
                                   for s, f in pick]}
    path = "P:/FoA/Saved/AnimShots/gasp_pick.json"
    json.dump(out, open(path, "w"), indent=1)
    print("written", path)
