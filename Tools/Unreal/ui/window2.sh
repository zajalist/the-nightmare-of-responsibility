#!/usr/bin/env bash
# One lock window: rebuild the flow manager, confirm dialog copy, place it, save the level (Hayba level_save after).
cd /p/FoA; export FOA_AGENT=ui MSYS_NO_PATHCONV=1
R() { echo "== $1"; python Tools/Unreal/ue_remote.py "Tools/Unreal/ui/$1.py" "${@:2}" 2>&1 | grep -v '^\s*$\|comment flag' | tail -3; }
R rescan_ui
R build_front_end
R wire_overlays FOA_WIDGETS=Confirm
R place_front_end
date +%H:%M:%S
