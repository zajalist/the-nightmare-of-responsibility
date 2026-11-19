"""Hayba TCP calls for boot card 2 per the approved page v3.1: "Made with" small above; the official Aholo logo
(unaltered, 60 px high) and "Lux3D" (Darker Grotesque 800, 43 pt) side by side 21 px apart. Also the Unreal card's
logo at the page's 12.5 vw (240 px). ui_reparent_element is MCP-only: Txt_Lux3D -> Row_Aholo is done through MCP
between the 'add' and 'finish' halves.
  python Tools/Unreal/ui/boot_card_calls.py add > Saved/UIShots/boot_add.jsonl
  python Tools/Unreal/ui/boot_card_calls.py finish > Saved/UIShots/boot_finish.jsonl"""
import json
import sys

S = '/Game/FoA/UI/Widgets/Menus/WBP_BootSplash'
LOGO = '/Game/FoA/UI/Textures/T_UI_Logo_Aholo.T_UI_Logo_Aholo'
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


if sys.argv[1] == 'add':
    c('ui_add_element', widget_blueprint_path=S, child_class='HorizontalBox', parent_widget_name='VB_Lux3D', name='Row_Aholo')
    c('ui_add_element', widget_blueprint_path=S, child_class='Image', parent_widget_name='Row_Aholo', name='Img_Aholo')
    c('ui_set_widget_properties', widget_blueprint_path=S, widget_name='Img_Aholo',
      properties={'Brush': {'ResourceObject': LOGO, 'TintColor': {'SpecifiedColor': [1, 1, 1, 1]}, 'DrawAs': 'Image',
                            'ImageSize': {'X': 267, 'Y': 60}}},
      slot_props={'vertical_alignment': 'Center', 'fill': 0})
else:
    c('ui_set_widget_properties', widget_blueprint_path=S, widget_name='Txt_Lux3D', properties={'Text': 'Lux3D'},
      slot_props={'vertical_alignment': 'Center', 'fill': 0, 'padding': [21, 0, 0, 0]})
    c('ui_set_widget_properties', widget_blueprint_path=S, widget_name='Row_Aholo',
      slot_props={'horizontal_alignment': 'Center', 'padding': [0, 8, 0, 0]})
    c('ui_set_widget_properties', widget_blueprint_path=S, widget_name='Txt_MadeWith', properties={'Text': 'Made with'},
      slot_props={'horizontal_alignment': 'Center'})
    c('ui_compile_widget', widget_blueprint_path=S)
    c('ui_save_widget', widget_blueprint_path=S)
for d in calls:
    print(json.dumps(d))
