#!/usr/bin/env bash
# First slot after the relaunch: rescan, then every graph builder (Hayba tree steps for HUD/SkipHint run between).
cd /p/FoA; export FOA_AGENT=ui MSYS_NO_PATHCONV=1
R() { echo "== $1"; python Tools/Unreal/ue_remote.py "Tools/Unreal/ui/$1.py" "${@:2}" 2>&1 | grep -v '^\s*$\|comment flag' | tail -4; }
R rescan_ui
R build_settings_lib
R build_front_end
R wire_menus
R wire_overlays FOA_WIDGETS=Pause,Confirm
R place_front_end
date +%H:%M:%S
