"""Hayba TCP calls that turn WBP_SandButton into sand letters (M_UI_SandText through a RetainerBox).
  python Tools/Unreal/ui/sandbutton_calls.py tree > Saved/UIShots/sandbutton_tree.jsonl     # before wire_sand_button.py
  python Tools/Unreal/ui/sandbutton_calls.py finish > Saved/UIShots/sandbutton_finish.jsonl # after it
The word is drawn once into Ret_Sand's target; the effect material animates it. Txt_Label keeps 30 px under it for the
time-shift echo. The old grain bar (Img_Sand, M_UI_SandButton) goes."""
import json
import sys

B = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
MI = '/Game/FoA/UI/Materials/MI_UI_SandText_Menu.MI_UI_SandText_Menu'
W = '/Game/FoA/UI/Widgets'
INSTANCES = {f'{W}/Menus/WBP_MainMenu': ['Btn_WakeUp', 'Btn_Settings', 'Btn_Credits', 'Btn_Quit'],
             f'{W}/Menus/WBP_Pause': ['Btn_Resume', 'Btn_Settings', 'Btn_RestartDay', 'Btn_QuitToTitle'],
             f'{W}/Common/WBP_ConfirmDialog': ['Btn_Confirm', 'Btn_Cancel']}
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


if sys.argv[1] == 'tree':
    c('ui_add_element', widget_blueprint_path=B, child_class='RetainerBox', parent_widget_name='Ovl_Face', name='Ret_Sand')
    c('ui_add_element', widget_blueprint_path=B, child_class='Overlay', parent_widget_name='Ret_Sand', name='Ovl_Glyphs')
    c('ui_reparent_element', widget_blueprint_path=B, widget_name='Txt_Label', new_parent_name='Ovl_Glyphs')
    c('ui_set_widget_properties', widget_blueprint_path=B, widget_name='Txt_Label', slot_props={'padding': [12, 6, 12, 30]})
    c('ui_set_widget_properties', widget_blueprint_path=B, widget_name='Ret_Sand',
      properties={'EffectMaterial': MI, 'TextureParameter': 'Texture'},
      slot_props={'horizontal_alignment': 'Left', 'vertical_alignment': 'Center', 'padding': [0, 0, 0, -24]})
    c('ui_set_variable', widget_blueprint_path=B, widget_name='Ret_Sand', is_variable=True)
    c('ui_compile_widget', widget_blueprint_path=B)
    c('ui_save_widget', widget_blueprint_path=B)
else:
    c('ui_remove_element', widget_blueprint_path=B, widget_name='Img_Sand')
    c('ui_compile_widget', widget_blueprint_path=B)
    c('ui_save_widget', widget_blueprint_path=B)
    for wbp, names in INSTANCES.items():
        for n in names:  # instances had the old bar's Primary/Secondary MI as an override
            c('ui_set_widget_properties', widget_blueprint_path=wbp, widget_name=n, properties={'SandMaterial': MI})
        c('ui_compile_widget', widget_blueprint_path=wbp)
        c('ui_save_widget', widget_blueprint_path=wbp)
    c('ui_render_widget_to_png', widget_blueprint_path=f'{W}/Menus/WBP_MainMenu', width=1920, height=1080,
      out_path='step3_WBP_MainMenu_after.png', inline_image=False)
for d in calls:
    print(json.dumps(d))
