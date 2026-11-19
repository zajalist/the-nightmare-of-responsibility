#!/usr/bin/env bash
# Player lane: one EXCLUSIVE PIE burst (60 s cap, own window) proving the MetaHuman avatar in the bedroom.
#   bash Tools/Unreal/player/record_avatar.sh [walk_seconds]
# Outputs in Saved/PlayerShots/: avatar_still_back.png, avatar_still_front.png, avatar_walk.gif (+ frames/).
set -u
cd /p/FoA
export FOA_AGENT=player HAYBA_AGENT_ID=player MSYS_NO_PATHCONV=1 FOA_EXCLUSIVE=1
WALK=${1:-12}
OUT=Saved/PlayerShots; SHOTS=Saved/Screenshots/WindowsEditor; LOG=Saved/Logs/FoA.log
R() { python Tools/Unreal/ue_remote.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; }
mkdir -p "$OUT" "$SHOTS"
trap 'python Tools/Unreal/editor_lock.py release player' EXIT
trap 'exit 1' TERM INT HUP
GOT=0
for i in $(seq 1 20); do
  python Tools/Unreal/editor_lock.py acquire player --ttl 300 --wait 900 && { GOT=1; break; }; sleep 5; done
[ "$GOT" = 1 ] || { echo "no lease"; exit 1; }
R Tools/Unreal/ui/pie_window.py FOA_PIE_WINDOW=on
touch "$OUT/.mark"
DONE0=$(grep -a -c "\[avatar\] done" "$LOG")
T0=$(date +%s)
R Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 3
R Tools/Unreal/player/pie_avatar.py "FOA_WALK=$WALK"
until [ "$(grep -a -c "\[avatar\] done" "$LOG")" -gt "$DONE0" ] || [ $(( $(date +%s) - T0 )) -ge 60 ]; do sleep 1; done
R Tools/Unreal/ui/pie_call.py FOA_CALL=END
echo "pie burst $(( $(date +%s) - T0 )) s"
sleep 2
R Tools/Unreal/ui/pie_window.py FOA_PIE_WINDOW=off
python Tools/Unreal/editor_lock.py release player
grep -a "\[avatar\]" "$LOG" | tail -40 | sed 's/^.*\[avatar\]/[avatar]/' | grep -v "goal yaw" | tail -12
rm -rf "$OUT/frames"; mkdir -p "$OUT/frames"
find "$SHOTS" -name 'ScreenShot*.png' -newer "$OUT/.mark" -exec mv {} "$OUT/frames/" \;
python - "$OUT" <<'PY'
import glob, os, shutil, sys
from PIL import Image
out = sys.argv[1]
fs = sorted(glob.glob(f'{out}/frames/*.png'), key=os.path.getmtime)
assert len(fs) >= 3, f'only {len(fs)} frames'
shutil.copy(fs[0], f'{out}/avatar_still_back.png')
shutil.copy(fs[1], f'{out}/avatar_still_front.png')
walk = fs[2:]
ts = [os.path.getmtime(f) for f in walk]
frames = []
for f in walk:
    im = Image.open(f).convert('RGB')
    w = 800
    frames.append(im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).quantize(colors=128, method=Image.MEDIANCUT))
dur = [max(60, min(250, round((ts[i + 1] - ts[i]) * 1000))) for i in range(len(ts) - 1)] + [400]
frames[0].save(f'{out}/avatar_walk.gif', save_all=True, append_images=frames[1:], duration=dur, loop=0, optimize=True)
print('stills', fs[0], fs[1], '| walk frames', len(walk), 'span', round(ts[-1] - ts[0], 1), 's ->', f'{out}/avatar_walk.gif',
      round(os.path.getsize(f'{out}/avatar_walk.gif') / 1e6, 1), 'MB')
PY
