"""Offline: stage the picked GASP clips into this project's Content under their ORIGINAL /Game paths (their internal
references stay valid), with every package they reference, so the editor can load and retarget them. Materials and
textures are skipped (the staged source mesh only serves the IK rig and renders grey); so are blueprints the clips
merely reference (notify classes: the retargeted copies drop their notifies). Never overwrites a file of ours.
  python Tools/Unreal/player/gasp_copy.py [--dry]            reads Saved/AnimShots/gasp_pick.json (gasp_scan.py --write)
Writes Saved/AnimShots/gasp_staged.json (every staged file, so gasp_retarget.py can delete the staging afterwards)."""
import json
import os
import re
import shutil
import sys

pick = json.load(open("P:/FoA/Saved/AnimShots/gasp_pick.json"))
src_content = os.path.join(pick["root"], "Content")
dst_content = "P:/FoA/Content"
SKIP = re.compile(r"/(Materials?|Textures?|Blueprints?|Audio|Sounds?|Maps|Levels|UI|VFX|Niagara)/|/(M|MI|MF|T|BP|ABP|SB|S|NS|W|WBP)_",
                  re.I)
GAME = re.compile(rb"/Game/[A-Za-z0-9_/\-\.]+")


def file_of(pkg):
    base = os.path.join(src_content, pkg[len("/Game/"):].replace("/", os.sep))
    for ext in (".uasset", ".umap"):
        if os.path.exists(base + ext):
            return base + ext
    return None


todo = [c["package"] for c in pick["clips"]]
seen, staged, skipped = set(), [], set()
while todo:
    pkg = todo.pop().split(".")[0]
    if pkg in seen:
        continue
    seen.add(pkg)
    f = file_of(pkg)
    if not f:
        continue
    data = open(f, "rb").read()
    for ref in {m.decode("ascii", "ignore").split(".")[0].rstrip("/") for m in GAME.findall(data)}:
        if ref in seen or not ref.count("/") > 2:
            continue
        if SKIP.search(ref + "/") or SKIP.search(ref):
            skipped.add(ref)
            continue
        todo.append(ref)
    rel = os.path.relpath(f, src_content)
    dst = os.path.join(dst_content, rel)
    staged.append({"package": pkg, "src": f, "dst": dst, "bytes": os.path.getsize(f)})
    # uexp/ubulk companions travel with the package
    for comp in (f[:-7] + ".uexp", f[:-7] + ".ubulk"):
        if os.path.exists(comp):
            staged[-1].setdefault("companions", []).append(comp)
            staged[-1]["bytes"] += os.path.getsize(comp)
total = sum(s["bytes"] for s in staged)
print(f"{len(staged)} packages, {total / 1e6:.1f} MB; skipped {len(skipped)} (materials, textures, blueprints, audio)")
for s in staged:
    print(f"  {s['bytes'] / 1e6:6.2f} MB  {s['package']}")
clash = [s["dst"] for s in staged if os.path.exists(s["dst"])]
assert not clash, f"would overwrite our files: {clash[:5]}"
if "--dry" not in sys.argv:
    for s in staged:
        os.makedirs(os.path.dirname(s["dst"]), exist_ok=True)
        shutil.copy2(s["src"], s["dst"])
        for comp in s.get("companions", []):
            shutil.copy2(comp, os.path.join(os.path.dirname(s["dst"]), os.path.basename(comp)))
    json.dump(staged, open("P:/FoA/Saved/AnimShots/gasp_staged.json", "w"), indent=1)
    print("staged ->", dst_content, "(rescan /Game in the editor before gasp_retarget.py)")
