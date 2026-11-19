"""Fallback for the menu words (the brief's "same hour" fallback): plain Darker Grotesque words drawn by Txt_Label itself,
with the sand MI as the label's Font Material (Slate multiplies the glyph coverage in, so the letters keep the sand
grain and tone), and no retainer effect. Ret_Sand stays (it still carries the hover opacity), its EffectMaterial goes.
SandMID stays None, so WBP_SandButton's PushState/SetReveal must skip it: wire_sand_button.py guards them with IsValid.
  python Tools/Unreal/ui/words_fallback_calls.py > Saved/UIShots/words_fallback.jsonl
  python Tools/Unreal/hayba_call.py --batch Saved/UIShots/words_fallback.jsonl --keep-going"""
import json

B = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
MI = '/Game/FoA/UI/Materials/MI_UI_SandText_Menu.MI_UI_SandText_Menu'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
W = '/Game/FoA/UI/Widgets'
INSTANCES = {f'{W}/Menus/WBP_MainMenu': ['Btn_WakeUp', 'Btn_Settings', 'Btn_Credits', 'Btn_Quit'],
             f'{W}/Menus/WBP_Pause': ['Btn_Resume', 'Btn_Settings', 'Btn_RestartDay', 'Btn_QuitToTitle'],
             f'{W}/Common/WBP_ConfirmDialog': ['Btn_Confirm', 'Btn_Cancel']}


def c(cmd, **p):
    print(json.dumps({'cmd': cmd, 'params': p}))


c('ui_set_widget_properties', widget_blueprint_path=B, widget_name='Ret_Sand', properties={'EffectMaterial': None})
c('ui_set_widget_properties', widget_blueprint_path=B, widget_name='Txt_Label',
  properties={'Font': {'FontObject': FONT, 'TypefaceFontName': 'SemiBold', 'Size': 38, 'FontMaterial': MI},
              'ColorAndOpacity': {'SpecifiedColor': [0.93, 0.89, 0.82, 1.0]}})
c('blueprint_set_defaults', path=B, properties={'SandMaterial': None})
c('ui_compile_widget', widget_blueprint_path=B)
c('ui_save_widget', widget_blueprint_path=B)
for wbp, names in INSTANCES.items():
    for n in names:
        c('ui_set_widget_properties', widget_blueprint_path=wbp, widget_name=n, properties={'SandMaterial': None})
    c('ui_compile_widget', widget_blueprint_path=wbp)
    c('ui_save_widget', widget_blueprint_path=wbp)
