#!/usr/bin/env bash
# PIE proof of the UI loop (run while holding the editor lock as FOA_AGENT=ui; about 50 s of PIE).
# Frames land in Saved/UIShots/pie/NN_name.png and become Saved/UIShots/pie/ui_loop.mp4.
set -u
cd /p/FoA
export FOA_AGENT=ui MSYS_NO_PATHCONV=1
OUT=Saved/UIShots/pie; SHOTS=Saved/Screenshots/WindowsEditor
mkdir -p "$OUT"; rm -f "$OUT"/*.png
call() { python Tools/Unreal/ue_remote.py Tools/Unreal/ui/pie_call.py "FOA_CALL=$1" 2>&1 | tail -1; }
shot() {
  local before; before=$(ls -t $SHOTS/ScreenShot*.png 2>/dev/null | head -1)
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/pie_shot.py >/dev/null 2>&1
  for i in $(seq 1 30); do
    local now; now=$(ls -t $SHOTS/ScreenShot*.png 2>/dev/null | head -1)
    if [ -n "$now" ] && [ "$now" != "$before" ]; then sleep 0.3; cp "$now" "$OUT/$1.png"; echo "shot $1"; return; fi
    sleep 0.2
  done
  echo "shot $1 MISSING"
}
call BEGIN; sleep 5
shot 01_splash_unreal; sleep 2.2
shot 02_splash_lux3d; sleep 2.6
shot 03_splash_hayba; sleep 3.4
shot 04_title
call OnTitleConfirmed; sleep 1.2; shot 05_main_menu
call WakeUp; sleep 1.0; shot 06_wake_blend; sleep 2.2; shot 07_gameplay
call TogglePause; sleep 0.8; shot 08_pause
call RequestQuitToTitle; sleep 0.8; shot 09_confirm
call ConfirmPending; sleep 1.5; shot 10_title_again
call OnTitleConfirmed; sleep 0.8; call WakeUp; sleep 3.0; shot 11_gameplay_again
call END
# 1.5 s per frame slideshow
ffmpeg -y -loglevel error -framerate 2/3 -pattern_type glob -i "$OUT/*.png" -vf "scale=1920:-2,format=yuv420p" -r 30 "$OUT/ui_loop.mp4" && echo "mp4 $OUT/ui_loop.mp4"
