#!/usr/bin/env bash
# Whole-graph PNGs of the UI lane's graphs -> Saved/GraphShots/UI/<asset>__<graph>.png (hold the lock while running).
#   bash Tools/Unreal/ui/capture_graphs.sh [frontend] [menus] [hud] [materials]     (no argument = all groups)
cd /p/FoA; export FOA_AGENT=ui MSYS_NO_PATHCONV=1; OUT=P:/FoA/Saved/GraphShots/UI; mkdir -p "$OUT"
U=/Game/FoA/UI; FE=$U/Framework/BP_FoAFrontEnd
declare -A GROUP
GROUP[frontend]="$FE|EventGraph $FE|StartFrontEnd $FE|OnSplashFinished $FE|OnSplashCue $FE|TitleGlitch $FE|WakeUp
 $FE|CutToBlack $FE|AfterWakeFade $FE|OnStoryFinished $FE|FinishWake $FE|PlayUISound $FE|StartBed $FE|StopBed $FE|ShowScreen
 $FE|TogglePause $FE|Resume $FE|ConfirmPending $FE|HandleBack $FE|ReturnToTitle $FE|RestartDay
 $U/Framework/BPFL_FoASettings|LoadSettings $U/Framework/BPFL_FoASettings|ApplySettings"
GROUP[menus]="$U/Widgets/Menus/WBP_BootSplash|EventGraph $U/Widgets/Menus/WBP_BootSplash|UpdateSplash
 $U/Widgets/Menus/WBP_BootSplash|CheckCue $U/Widgets/Menus/WBP_BootSplash|SkipCard $U/Widgets/Menus/WBP_Title|EventGraph
 $U/Widgets/Menus/WBP_Title|FadeInStep $U/Widgets/Menus/WBP_MainMenu|EventGraph $U/Widgets/Menus/WBP_Pause|EventGraph
 $U/Widgets/Common/WBP_ConfirmDialog|EventGraph $U/Widgets/Common/WBP_SandButton|EventGraph
 $U/Widgets/Common/WBP_SandButton|PushState"
GROUP[hud]="$U/Game/WBP_HUD|EventGraph $U/Game/WBP_HUD|HandleBeatChanged $U/Game/WBP_HUD|FadeInStep
 $U/Game/WBP_SkipHint|SetHoldProgress"
GROUP[materials]="$U/Materials/M_UI_SandText| $U/Materials/Functions/MF_UI_SandShape| $U/Materials/Functions/MF_UI_SandGrain|
 $U/Materials/Functions/MF_UI_TimeEcho| $U/Materials/M_UI_SplatLogo| $U/Materials/M_UI_Scrim|"
GROUPS=("$@"); [ ${#GROUPS[@]} -eq 0 ] && GROUPS=(frontend menus hud materials)
for grp in "${GROUPS[@]}"; do
  for item in ${GROUP[$grp]}; do
    a="${item%%|*}"; gname="${item##*|}"; png="$OUT/$(basename "$a")__${gname:-Material}.png"
    rm -f "$png"
    python Tools/Unreal/ue_remote.py Tools/Unreal/ui/capture_graph.py "FOA_ASSET=$a" "FOA_GRAPH=$gname" "FOA_PNG=$png" >/dev/null 2>&1
    for i in $(seq 1 40); do [ -f "$png" ] && break; sleep 0.25; done
    [ -f "$png" ] && echo "ok $png" || echo "MISSING $png"
  done
done
