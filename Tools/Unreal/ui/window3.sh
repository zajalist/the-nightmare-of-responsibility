#!/usr/bin/env bash
cd /p/FoA; export FOA_AGENT=ui MSYS_NO_PATHCONV=1
R() { echo "== $1"; python Tools/Unreal/ue_remote.py "Tools/Unreal/ui/$1.py" "${@:2}" 2>&1 | grep -v '^\s*$\|comment flag' | tail -3; }
R rescan_ui
R remove_dev_actors
R reimport_ui_textures FOA_TEX=T_UI_Logo_Unreal,T_UI_Logo_Hayba FOA_REIMPORT=T_UI_Logo_Unreal
R build_front_end
R wire_menus
date +%H:%M:%S
