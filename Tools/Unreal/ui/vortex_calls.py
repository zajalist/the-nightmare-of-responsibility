"""Hayba calls: Img_Vortex (M_UI_SandVortex) over WBP_SandButton's face, 56 px out on the left and 40 px below, drawn
above the word, hit-test invisible, hidden at rest (PushState sets its opacity from the hover/focus state).
  python Tools/Unreal/ui/vortex_calls.py > Saved/UIShots/vortex.jsonl; python Tools/Unreal/hayba_call.py --batch ..."""
import json

B = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
MAT = '/Game/FoA/UI/Materials/M_UI_SandVortex.M_UI_SandVortex'
for cmd, p in (('ui_add_element', dict(child_class='Image', parent_widget_name='Ovl_Face', name='Img_Vortex')),
               ('ui_set_widget_properties', dict(widget_name='Img_Vortex',
                                                 properties={'Brush': {'ResourceObject': MAT, 'DrawAs': 'Image'},
                                                             'Visibility': 'HitTestInvisible', 'RenderOpacity': 0.0},
                                                 slot_props={'horizontal_alignment': 'Fill', 'vertical_alignment': 'Fill',
                                                             'padding': [-56, 0, 0, -40]})),
               ('ui_set_variable', dict(widget_name='Img_Vortex', is_variable=True)),
               ('ui_compile_widget', {})):
    print(json.dumps({'cmd': cmd, 'params': dict(widget_blueprint_path=B, **p)}))
