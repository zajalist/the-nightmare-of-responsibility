"""QA (b) on the full logotype region (main, run_20261109_1328): the "re" of "Nightmare" sat on the bright curtain at
1.1:1. Img_TitleShade, a soft black falloff (T_UI_SoftDot) behind the title only, on WBP_Title and WBP_MainMenu; the
floor light pool below y 650 stays untouched. ui_move_element (draw it first) is MCP-only: the script prints that call.
  python Tools/Unreal/ui/aaa_title_shade.py [alpha] [w] [h] [cx] [cy]     (1080p pixels; default 0.95 1500 620 900 410)"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

A, W, H, CX, CY = (float(v) for v in (sys.argv[1:6] if len(sys.argv) > 5 else (0.95, 1500, 620, 900, 410)))
DOT = '/Game/FoA/UI/Textures/T_UI_SoftDot.T_UI_SoftDot'
for wbp in ('/Game/FoA/UI/Widgets/Menus/WBP_Title', '/Game/FoA/UI/Widgets/Menus/WBP_MainMenu'):
    names = [w['name'] for w in hc.call('ui_query', {'path': wbp, 'flatten': True})['data']['matches']]
    if 'Img_TitleShade' not in names:
        print(hc.call('ui_add_element', {'widget_blueprint_path': wbp, 'child_class': 'Image', 'parent_widget_name': 'Ovl_Frame',
                                         'name': 'Img_TitleShade'}).get('ok'))
        print('NOW (MCP): ui_move_element', json.dumps({'widget_blueprint_path': wbp, 'widget_name': 'Img_TitleShade', 'new_index': 0}))
    r = hc.call('ui_set_widget_properties', {
        'widget_blueprint_path': wbp, 'widget_name': 'Img_TitleShade',
        'properties': {'Brush': {'ResourceObject': DOT, 'TintColor': {'SpecifiedColor': [0, 0, 0, A]}, 'DrawAs': 'Image',
                                 'ImageSize': {'X': W, 'Y': H}}, 'Visibility': 'HitTestInvisible'},
        'slot_props': {'horizontal_alignment': 'HAlign_Left', 'vertical_alignment': 'VAlign_Top',  # NOTE: did not apply; ui_set_slot_layout (MCP) padding [150,100] Left Top did
                       'padding': f'(Left={CX - W / 2},Top={CY - H / 2},Right=0,Bottom=0)'}})
    print(wbp.rsplit('/', 1)[1], r.get('ok'), (r.get('data') or {}).get('succeeded'), (r.get('data') or {}).get('failed_properties'),
          (r.get('data') or {}).get('unknown_slot_props'))
    print(hc.call('ui_compile_widget', {'widget_blueprint_path': wbp})['data'].get('compiled_clean'),
          hc.call('ui_save_widget', {'widget_blueprint_path': wbp})['data'].get('saved'))
