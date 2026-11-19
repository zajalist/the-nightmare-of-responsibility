#!/usr/bin/env bash
# Hold A (ui lane): Darker Grotesque swap, Aholo boot card, sound hooks and Blueprint rebuilds (Hayba compiles), level save.
# Hold the editor lock as FOA_AGENT=ui. Each step prints its own result; stop and read on the first FAIL.
set -u
cd /p/FoA
export FOA_AGENT=ui FOA_AREAS=UI HAYBA_AGENT_ID=ui MSYS_NO_PATHCONV=1
R=Tools/Unreal/ue_remote.py
HR="python Tools/Unreal/ui/hayba_replay.py"
step() { echo; echo "=== $*"; }
step rescan;      python $R Tools/Unreal/ui/rescan_ui.py 2>&1 | tail -1
step faces;       python $R Tools/Unreal/import_fonts.py 2>&1 | tail -2
step typography;  python $R Tools/Unreal/make_typography.py 2>&1 | tail -1
step font+card;   $HR --calls Saved/UIShots/font_swap.jsonl
step settings;    $HR Tools/Unreal/ui/build_settings_lib.py
step front-end;   $HR Tools/Unreal/ui/build_front_end.py
step splash+title; $HR Tools/Unreal/ui/wire_menus.py FOA_WIDGETS=Splash,Title
step hud;         $HR Tools/Unreal/ui/wire_hud.py
step skiphint;    $HR Tools/Unreal/ui/wire_skiphint.py
step level;       python Tools/Unreal/editor_lock.py save_level ui | tail -2
