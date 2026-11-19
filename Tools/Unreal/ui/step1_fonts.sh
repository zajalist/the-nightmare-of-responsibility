#!/usr/bin/env bash
# Step 1 of the visible front end: Darker Grotesque everywhere, then renders of title, menu, dialog and HUD.
# Short runs only (each ue_remote run well under 30 s). Holds the UI lease as ui.
set -u
cd /p/FoA
export FOA_AGENT=ui HAYBA_AGENT_ID=ui MSYS_NO_PATHCONV=1
unset FOA_AREAS
python Tools/Unreal/editor_lock.py acquire ui --areas UI --ttl 900 --wait 300 | tail -1
echo "== faces";       python Tools/Unreal/ue_remote.py Tools/Unreal/import_fonts.py 2>&1 | tail -2
echo "== composites";  python Tools/Unreal/ui/font_swap_calls.py | head -3 > Saved/UIShots/composites.jsonl
python Tools/Unreal/ui/hayba_replay.py --calls Saved/UIShots/composites.jsonl
echo "== typography";  python Tools/Unreal/ue_remote.py Tools/Unreal/make_typography.py 2>&1 | tail -1
echo "== styles";      python Tools/Unreal/ui/apply_font_styles.py
echo "== logotype line 2"
python Tools/Unreal/hayba_call.py ui_set_widget_properties '{"widget_blueprint_path": "/Game/FoA/UI/Widgets/Common/WBP_Logotype", "widget_name": "Txt_Line2", "slot_props": {"padding": [228, -30, 0, 0]}}' | head -4
python Tools/Unreal/hayba_call.py ui_compile_widget '{"widget_blueprint_path": "/Game/FoA/UI/Widgets/Common/WBP_Logotype"}' | head -3
python Tools/Unreal/hayba_call.py ui_save_widget '{"widget_blueprint_path": "/Game/FoA/UI/Widgets/Common/WBP_Logotype"}' | head -3
