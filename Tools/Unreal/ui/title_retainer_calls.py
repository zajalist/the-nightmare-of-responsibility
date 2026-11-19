"""Hayba calls that draw the logotype as sand letters with the page's time-shift echo: the Logo (WBP_Logotype) in
WBP_Title and WBP_MainMenu goes inside a RetainerBox (Ret_Title) whose Effect Material is MI_UI_SandText_Title
(Scale 9, echo 0.55). A retainer clips to its own box, and the echo smears glyphs downward, so the Logo gets room
inside it (16 px sides, 8 top, 48 below: Txt_Line1 sits 8 px left of its box) and the retainer slot gives it back.
  python Tools/Unreal/ui/title_retainer_calls.py > Saved/UIShots/title_retainer.jsonl
  python Tools/Unreal/hayba_call.py --batch Saved/UIShots/title_retainer.jsonl"""
import json

MI = '/Game/FoA/UI/Materials/MI_UI_SandText_Title.MI_UI_SandText_Title'
T = '/Game/FoA/UI/Widgets/Menus/WBP_Title'
M = '/Game/FoA/UI/Widgets/Menus/WBP_MainMenu'
ROOM = [16, 8, 16, 48]
RET = {'EffectMaterial': MI, 'TextureParameter': 'Texture'}


def c(wbp, cmd, **p):
    print(json.dumps({'cmd': cmd, 'params': dict(widget_blueprint_path=wbp, **p)}))


# title: Logo sat in Ovl_Frame at Left/Top (146, 243) (title_calls.py)
c(T, 'ui_add_element', child_class='RetainerBox', parent_widget_name='Ovl_Frame', name='Ret_Title')
c(T, 'ui_reparent_element', widget_name='Logo', new_parent_name='Ret_Title')
c(T, 'ui_set_widget_properties', widget_name='Logo', slot_props={'padding': ROOM})
c(T, 'ui_set_widget_properties', widget_name='Ret_Title', properties=RET,
  slot_props={'horizontal_alignment': 'Left', 'vertical_alignment': 'Top', 'padding': [146 - 16, 243 - 8, 0, 0]})
c(T, 'ui_compile_widget')
c(T, 'ui_save_widget')
# main menu: Scale_Logo (a ScaleBox, one child) > Logo; park the Logo, put the retainer in, move the Logo into it
c(M, 'ui_reparent_element', widget_name='Logo', new_parent_name='VB_Column')
c(M, 'ui_add_element', child_class='RetainerBox', parent_widget_name='Scale_Logo', name='Ret_Title')
c(M, 'ui_reparent_element', widget_name='Logo', new_parent_name='Ret_Title')
c(M, 'ui_set_widget_properties', widget_name='Logo', slot_props={'padding': ROOM})
c(M, 'ui_set_widget_properties', widget_name='Ret_Title', properties=RET, slot_props={'padding': [-v for v in ROOM]})
c(M, 'ui_compile_widget')
c(M, 'ui_save_widget')
