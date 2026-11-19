"""Capture the graphs the AAA pass touched to Saved/GraphShots/aaa_*.png (FoAGraphTools, whole graph at 1:1).
FOA_STEP=capture opens each editor and queues the PNGs; FOA_STEP=close closes them again (run it a few seconds later)."""
import os
import unreal

SHOTS = [
    ('/Game/FoA/UI/Materials/M_UI_SandText', '', 'aaa_m_ui_sandtext'),
    ('/Game/FoA/UI/Materials/Functions/MF_UI_SandShape', '', 'aaa_mf_ui_sandshape'),
    ('/Game/FoA/UI/Materials/M_UI_Scrim', '', 'aaa_m_ui_scrim'),
    ('/Game/FoA/UI/Widgets/Menus/WBP_Title', 'FormStep', 'aaa_wbp_title_formstep'),
    ('/Game/FoA/UI/Game/WBP_HUD', 'ObjectiveStep', 'aaa_wbp_hud_objectivestep'),
    ('/Game/FoA/UI/Widgets/Menus/WBP_Pause', 'EventGraph', 'aaa_wbp_pause_eventgraph'),
    ('/Game/FoA/UI/Materials/M_UI_PhoneScreen', '', 'aaa_m_ui_phonescreen'),
    ('/Game/FoA/UI/Game/WBP_Phone', 'EventGraph', 'aaa_wbp_phone_eventgraph'),
]
step = os.environ.get('FOA_STEP', 'capture')
sub = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
for path, graph, name in SHOTS:
    a = unreal.load_asset(path)
    if step == 'capture':
        unreal.FoAGraphToolsLibrary.capture_graph_png(a, graph, f'P:/FoA/Saved/GraphShots/{name}.png', True)
    else:
        sub.close_all_editors_for_asset(a)
print(step, len(SHOTS))
