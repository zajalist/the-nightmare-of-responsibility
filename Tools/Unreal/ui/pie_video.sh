#!/usr/bin/env bash
# Real-time PIE proof of the UI flow: pie_rec.py requests 'Shot showui' frames (about 4-5 fps, the PIE viewport renders
# them, so window focus does not matter) while pie_call.py drives the front end. Frames are cropped to the 16:9 game
# view and become an MP4 timed by their file times, frame-blended to 30 fps. Run holding the editor lock as FOA_AGENT=ui.
#   bash Tools/Unreal/ui/pie_video.sh boot    # boot splashes + title fade-up only (about 20 s)
#   bash Tools/Unreal/ui/pie_video.sh         # the whole loop: boot, title, menu, wake, pause, confirm, title again
# The recorder is a slate post-tick callback registered for the run only (STOP always runs before END).
set -u
cd /p/FoA
export FOA_AGENT=ui HAYBA_AGENT_ID=ui FOA_EXCLUSIVE=1 MSYS_NO_PATHCONV=1
MODE=${1:-loop}
OUT=Saved/UIShots/pie_$MODE; SHOTS=Saved/Screenshots/WindowsEditor
mkdir -p "$OUT/frames"; rm -f "$OUT"/frames/*.png
call() { python Tools/Unreal/ue_remote.py Tools/Unreal/ui/pie_call.py "FOA_CALL=$1" 2>&1 | tail -1; }
rec() { python Tools/Unreal/ue_remote.py Tools/Unreal/ui/pie_rec.py "FOA_REC=$1" 2>&1 | tail -1; }
touch "$OUT/.mark"
rec START                      # armed before PIE exists: it shoots from the first PIE frame
T0=$(date +%s.%N)
at() { local w; w=$(python -c "import time; print(max(0, $T0 + $1 - time.time()))"); sleep "$w"; }
call BEGIN
at 2.0; call LIT
if [ "$MODE" = boot ]; then
  at 21; rec STOP; call END
elif [ "$MODE" = title ]; then   # boot skipped: title, sand-letter menu, Wake up hand-off, first pause; ~30 s of PIE
  at 3;    call OnSplashFinished
  at 10;   call OnTitleConfirmed
  at 15;   call WakeUp
  at 25;   call TogglePause
  at 29;   call ""
  at 30;   rec STOP; call END
else
  at 21;   call OnTitleConfirmed
  at 24.5; call WakeUp
  at 29.5; call TogglePause
  at 32;   call RequestQuitToTitle
  at 34.5; call ConfirmPending
  at 40;   call ""
  at 41;   rec STOP; call END
fi
sleep 1
find "$SHOTS" -name 'ScreenShot*.png' -newer "$OUT/.mark" -exec mv {} "$OUT/frames/" \;
python - "$OUT" <<'PY'
import glob, os, subprocess, sys
from PIL import Image
import numpy as np
out = sys.argv[1]
fs = sorted(glob.glob(f'{out}/frames/*.png'), key=os.path.getmtime)
assert fs, 'no frames'
ts = [os.path.getmtime(f) for f in fs]
# crop: the PIE viewport inside the editor window, then the 16:9 game view inside it (pillarbox bars removed)
a = np.asarray(Image.open(fs[-1]).convert('L')).astype(int)
x0, y0, x1, y1 = 4, 135, 1684, 1019                         # PIE viewport in a maximized 1920x1056 editor shot
v = a[y0:y1, x0:x1]
cols = np.where(v.max(0) > 20)[0]
cx0, cx1 = (cols.min(), cols.max() + 1) if len(cols) else (0, v.shape[1])
w = (cx1 - cx0) // 2 * 2; h = (y1 - y0) // 2 * 2
os.makedirs(f'{out}/crop', exist_ok=True)
with open(f'{out}/crop/list.txt', 'w') as fh:
    for i, f in enumerate(fs):
        Image.open(f).convert('RGB').crop((x0 + cx0, y0, x0 + cx0 + w, y0 + h)).save(f'{out}/crop/{i:04d}.png')
        d = (ts[i + 1] - ts[i]) if i + 1 < len(fs) else 0.5
        fh.write(f"file '{i:04d}.png'\nduration {max(d, 0.02):.3f}\n")
    fh.write(f"file '{len(fs) - 1:04d}.png'\n")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{out}/crop/list.txt', '-vf',
                'framerate=30,format=yuv420p', '-c:v', 'libx264', '-crf', '18', '-movflags', '+faststart',
                f'{out}/{os.path.basename(out)}.mp4'], check=True)
print('frames', len(fs), 'span', round(ts[-1] - ts[0], 1), 's ->', f'{out}/{os.path.basename(out)}.mp4')
PY
rm -rf "$OUT/frames"
