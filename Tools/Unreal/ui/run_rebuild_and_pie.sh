#!/usr/bin/env bash
# Queue for the UI lease; title fixes; BP_Phone; rebuild the front end, splash/title, phone screen, phone actor, HUD and
# skip hint (Hayba compiles); release. Then an EXCLUSIVE PIE burst (waits for a :x0-:x2 window) and release.
# Logs: Saved/UIShots/rebuild.log, Saved/UIShots/pie_title.log.
set -u
cd /p/FoA
export FOA_AGENT=ui HAYBA_AGENT_ID=ui MSYS_NO_PATHCONV=1 FOA_AREAS=UI
L=Saved/UIShots/rebuild.log
: > $L
HC="python Tools/Unreal/hayba_call.py"
HR="python Tools/Unreal/ui/hayba_replay.py"
python Tools/Unreal/editor_lock.py acquire ui --areas UI --ttl 900 --wait 1800 >> $L 2>&1
T=/Game/FoA/UI/Widgets/Menus/WBP_Title; M=/Game/FoA/UI/Widgets/Menus/WBP_MainMenu
for s in "wire_bp_phone.py" "build_front_end.py" "wire_menus.py FOA_WIDGETS=Splash,Title" "wire_phone.py" "wire_bp_phone.py" "wire_hud.py" "wire_skiphint.py"; do
  echo "=== $s $(date +%T)" >> $L
  python Tools/Unreal/editor_lock.py renew ui >> $L 2>&1
  $HR Tools/Unreal/ui/$s >> $L 2>&1
done
python Tools/Unreal/editor_lock.py release ui >> $L 2>&1
echo "=== pie $(date +%T)" >> $L
python Tools/Unreal/editor_lock.py acquire ui --ttl 90 --wait 1800 >> $L 2>&1   # waits for a :x0-:x2 PIE window
bash Tools/Unreal/ui/pie_video.sh title > Saved/UIShots/pie_title.log 2>&1
python Tools/Unreal/editor_lock.py release ui >> $L 2>&1
echo "=== done $(date +%T)" >> $L
