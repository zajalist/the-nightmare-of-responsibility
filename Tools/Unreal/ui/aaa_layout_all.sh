#!/usr/bin/env bash
# ui lane: production layout (Tools/Unreal/bp_layout.py, Hayba only) on every UI Blueprint the AAA pass touched, one at a
# time, each under its own 120 s asset lease, never during PIE or inside a PIE window.
#   bash Tools/Unreal/ui/aaa_layout_all.sh   -> Saved/UIShots/aaa/layout_all.log
set -u
cd /p/FoA
export FOA_AGENT=ui HAYBA_AGENT_ID=ui MSYS_NO_PATHCONV=1
W=/Game/FoA/UI/Widgets
for A in $W/Menus/WBP_Title $W/Menus/WBP_MainMenu /Game/FoA/UI/Game/WBP_HUD $W/Menus/WBP_Pause $W/Menus/WBP_Settings \
         /Game/FoA/UI/Game/WBP_Phone /Game/FoA/UI/Game/WBP_DayRollover $W/Menus/WBP_BootSplash $W/Common/WBP_SandButton \
         $W/Common/WBP_SettingRow_Slider $W/Common/WBP_SettingRow_Switcher $W/Common/WBP_ConfirmDialog \
         /Game/FoA/UI/Framework/BP_FoAFrontEnd; do
  until python Tools/Unreal/hayba_call.py editor_get_state '{}' 2>/dev/null | grep -q '"pie_running": false' \
        && ! python Tools/Unreal/editor_lock.py status 2>&1 | grep -q "exclusive (held\|MAINTENANCE" \
        && [ $(( 10#$(date +%M) % 10 )) -ge 3 ] && [ $(( 10#$(date +%M) % 10 )) -le 8 ]; do sleep 10; done
  echo "$(date +%T) $A"
  python Tools/Unreal/editor_lock.py acquire ui --assets $A --ttl 120 2>&1 | tail -1
  timeout 115 python Tools/Unreal/bp_layout.py --apply $A 2>&1 | grep -v "^  " | tail -3
  python Tools/Unreal/editor_lock.py release ui 2>&1 | tail -1
done
echo all-done
