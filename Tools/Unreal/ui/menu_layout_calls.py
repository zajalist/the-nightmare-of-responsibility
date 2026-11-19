"""Hayba TCP calls: the menu keeps the title exactly where the title screen has it (page v3.1: 146, 243 at 110 pt) with the
words at (159, 576); a soft dark scrim sits behind the title block on both screens so it reads over the bright window.
  python Tools/Unreal/ui/menu_layout_calls.py > Saved/UIShots/menu_layout.jsonl   (then MCP ui_move_element: scrims to index 0)"""
import json

W = '/Game/FoA/UI/Widgets/Menus'
DOT = '/Game/FoA/UI/Textures/T_UI_SoftDot.T_UI_SoftDot'
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


for wbp in (f'{W}/WBP_Title', f'{W}/WBP_MainMenu'):
    c('ui_add_element', widget_blueprint_path=wbp, child_class='Image', parent_widget_name='Ovl_Frame', name='Img_TitleScrim')
    c('ui_set_widget_properties', widget_blueprint_path=wbp, widget_name='Img_TitleScrim',
      properties={'Brush': {'ResourceObject': DOT, 'TintColor': {'SpecifiedColor': [0, 0, 0, 0.55]}, 'DrawAs': 'Image',
                            'ImageSize': {'X': 1300, 'Y': 560}}},
      slot_props={'horizontal_alignment': 'Left', 'vertical_alignment': 'Top', 'padding': [-82, 94, 0, 0]})
M = f'{W}/WBP_MainMenu'
c('ui_set_widget_properties', widget_blueprint_path=M, widget_name='VB_Column',
  slot_props={'horizontal_alignment': 'Left', 'vertical_alignment': 'Top', 'padding': [146, 243, 0, 0]})
c('ui_set_widget_properties', widget_blueprint_path=M, widget_name='Scale_Logo',
  properties={'Stretch': 'UserSpecified', 'UserSpecifiedScale': 1.0}, slot_props={'fill': 0})
c('ui_set_widget_properties', widget_blueprint_path=M, widget_name='Gap_Logo', properties={'Size': {'X': 1, 'Y': 94}})  # menu top = y2 + 0.5 s2 + 4.2 vw = 599 px
c('ui_set_widget_properties', widget_blueprint_path=M, widget_name='VB_Buttons', slot_props={'padding': [5, 0, 0, 0]})
for wbp in (f'{W}/WBP_Title', M):
    c('ui_compile_widget', widget_blueprint_path=wbp)
    c('ui_save_widget', widget_blueprint_path=wbp)
if __name__ == '__main__':
    for d in calls:
        print(json.dumps(d))
