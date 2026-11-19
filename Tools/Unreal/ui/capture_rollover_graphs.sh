#!/usr/bin/env bash
# Graph PNGs of the rollover build and the menu look (FoAGraphTools, async: each PNG lands ~1.5 s after its request).
# One capture per run, then the asset editors are closed again (never leave an editor open on an asset others edit).
set -u
cd /p/FoA
export FOA_AGENT=ui HAYBA_AGENT_ID=ui MSYS_NO_PATHCONV=1
G=P:/FoA/Saved/GraphShots
shot() {  # asset graph png
  FOA_AREAS="$1" python Tools/Unreal/ue_remote.py Tools/Unreal/ui/capture_graph.py "FOA_ASSET=$1" "FOA_GRAPH=$2" "FOA_PNG=$G/$3" 2>&1 | tail -1
  python - "$G/$3" <<'PY'
import os, sys, time
t = time.time()
while not os.path.exists(sys.argv[1]) and time.time() - t < 8:
    time.sleep(0.3)
print('png', os.path.exists(sys.argv[1]), sys.argv[1])
PY
}
shot /Game/FoA/UI/Framework/BP_FoAFrontEnd PlayDayRollover ui_fe_PlayDayRollover.png
shot /Game/FoA/UI/Framework/BP_FoAFrontEnd RolloverCovered ui_fe_RolloverCovered.png
shot /Game/FoA/UI/Game/WBP_DayRollover PlayRollover ui_rollover_PlayRollover.png
shot /Game/FoA/UI/Game/WBP_DayRollover StepRollover ui_rollover_StepRollover.png
shot /Game/FoA/UI/Materials/M_UI_SandWipe "" ui_M_UI_SandWipe.png
shot /Game/FoA/UI/Menu/M_PP_MenuV31 "" ui_M_PP_MenuV31.png
cat > "$TEMP/ui_close_editors.py" <<'PY'
import unreal
s = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
for p in ('/Game/FoA/UI/Framework/BP_FoAFrontEnd', '/Game/FoA/UI/Game/WBP_DayRollover', '/Game/FoA/UI/Materials/M_UI_SandWipe',
          '/Game/FoA/UI/Menu/M_PP_MenuV31'):
    a = unreal.load_asset(p)
    if a:
        s.close_all_editors_for_asset(a)
print('editors closed')
PY
cp "$TEMP/ui_close_editors.py" Tools/Unreal/ui/_close_editors.py
FOA_AREAS=/Game/FoA/UI/Framework/BP_FoAFrontEnd python Tools/Unreal/ue_remote.py Tools/Unreal/ui/_close_editors.py 2>&1 | tail -1
rm -f Tools/Unreal/ui/_close_editors.py
