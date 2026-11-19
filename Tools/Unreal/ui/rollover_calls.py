"""Writes the Hayba call list that creates WBP_DayRollover's widget tree (graph: wire_rollover.py; front end:
wire_rollover_fe.py). Contract P13 "Day rollover" (docs/mechanics/contract.md).
  python Tools/Unreal/ui/rollover_calls.py > Saved/UIShots/rollover.jsonl
  python Tools/Unreal/hayba_call.py --batch Saved/UIShots/rollover.jsonl --keep-going
Black sand pours over the screen (Img_Wipe, M_UI_SandWipe); on the black, the old day is struck through, the new day
comes up large, and the line this failure taught sits under it (collapsed when empty). Plain words, no labels.
Everything is set inside one ui_build_tree under the RootCanvas ui_create_widget makes (TCP has no ui_set_text_style)."""
import json

P = '/Game/FoA/UI/Game/WBP_DayRollover'
F = '/Game/FoA/UI/Fonts'
DISPLAY, UI = f'{F}/F_FoA_Display.F_FoA_Display', f'{F}/F_FoA_UI.F_FoA_UI'
WIPE = '/Game/FoA/UI/Materials/M_UI_SandWipe.M_UI_SandWipe'
PAPER, MUTED = [0.86, 0.82, 0.75, 1.0], [0.62, 0.59, 0.54, 1.0]


def c(cmd, **p):
    print(json.dumps({'cmd': cmd, 'params': p}))


def text(name, txt, font, face, size, col, slot, **extra):
    return {'class': 'TextBlock', 'name': name, 'slot_props': slot,
            'properties': {'Text': txt, 'Font': {'FontObject': font, 'TypefaceFontName': face, 'Size': size},
                           'ColorAndOpacity': {'SpecifiedColor': col}, 'Justification': 'Center', **extra}}


c('ui_create_widget', path='/Game/FoA/UI/Game', name='WBP_DayRollover')
c('ui_build_tree', widget_blueprint_path=P, parent_widget_name='RootCanvas', tree=[
    {'class': 'Image', 'name': 'Img_Wipe',
     'properties': {'Brush': {'ResourceObject': WIPE, 'DrawAs': 'Image'}, 'Visibility': 'HitTestInvisible'},
     'slot_props': {'anchors': [0, 0, 1, 1], 'position': [0, 0], 'size': [0, 0]}},
    {'class': 'VerticalBox', 'name': 'VB_Card', 'properties': {'Visibility': 'HitTestInvisible', 'RenderOpacity': 0.0},
     'slot_props': {'anchors': [0.5, 0.5, 0.5, 0.5], 'position': [0, 0], 'alignment': [0.5, 0.5], 'auto_size': True},
     'children': [
         {'class': 'Overlay', 'name': 'Ovl_Old', 'slot_props': {'horizontal_alignment': 'Center'}, 'children': [
             text('Txt_Old', 'Day 1', UI, 'SemiBold', 34, MUTED, {}),
             {'class': 'Image', 'name': 'Img_Strike',
              'properties': {'Brush': {'DrawAs': 'Box', 'ImageSize': {'X': 8, 'Y': 3}, 'TintColor': {'SpecifiedColor': PAPER}},
                             'RenderTransformPivot': {'X': 0.0, 'Y': 0.5}, 'RenderTransform': {'Scale': {'X': 0.0, 'Y': 1.0}}},
              'slot_props': {'horizontal_alignment': 'Fill', 'vertical_alignment': 'Center', 'padding': [-6, 4, -6, 0]}}]},
         text('Txt_New', 'Day 2', DISPLAY, 'ExtraBold', 112, PAPER, {'horizontal_alignment': 'Center', 'padding': [0, 4, 0, 0]}),
         text('Txt_Learned', 'The alarm only stops when you stand up.', UI, 'Medium', 26, MUTED,
              {'horizontal_alignment': 'Center', 'padding': [0, 28, 0, 0]}, AutoWrapText=True, WrapTextAt=760)]}])
for v in ('Img_Wipe', 'VB_Card', 'Img_Strike', 'Txt_Old', 'Txt_New', 'Txt_Learned'):
    c('ui_set_variable', widget_blueprint_path=P, widget_name=v, is_variable=True)
c('ui_compile_widget', widget_blueprint_path=P)
c('ui_save_widget', widget_blueprint_path=P)
