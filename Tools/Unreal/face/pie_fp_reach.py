"""First-person reach frames for the face lane's skin check, using the anim lane's proven walk-up driver unchanged
except: only the CommodeDrawer, frames without UI, output in Saved/FaceShots/<run>/ (never anim's folders), and a
shots.json at the end so face_burst.sh knows it finished. Gameplay exposure applies (the pawn is the view target).
  FOA_DRIVER=Tools/Unreal/face/pie_fp_reach.py bash Tools/Unreal/face/face_burst.sh fp_reach reach"""
import os
from pathlib import Path

RUN = os.environ.get('FOA_RUN', 'fp_reach')
OUT = Path('P:/FoA/Saved/FaceShots') / RUN
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob('*'):
    old.unlink()
src = Path('P:/FoA/Tools/Unreal/player/pie_approach.py').read_text(encoding='utf-8')
import re
src = re.sub(r"^KEYS = \(.*\)$", "KEYS = ('CommodeDrawer',)", src, count=1, flags=re.M)  # anim reorders its list
assert "KEYS = ('CommodeDrawer',)" in src
for a, b in (
             ("folder = Path('P:/FoA/Saved/AnimShots/approach') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')",
              f"folder = Path('{OUT.as_posix()}')"),
             ("'Shot showui filename='", "'Shot filename='"),
             ("    (folder / 'approach.json').write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1))",
              "    (folder / 'approach.json').write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1))\n"
              "    (folder / 'shots.json').write_text(json.dumps(dict(reason=reason, error=None, shots=[]), indent=1))")):
    assert a in src, a[:60]
    src = src.replace(a, b)
exec(compile(src, 'pie_approach.py (face copy)', 'exec'), {'__name__': '__face_reach__'})
