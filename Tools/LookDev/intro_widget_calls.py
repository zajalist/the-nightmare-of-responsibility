"""WBP_IntroStory shell, part 1: stage the 8 storyboard panels as textures and build the widget tree (Hayba calls).
  python Tools/LookDev/intro_widget_calls.py > %TEMP%/intro_calls.jsonl
  python Tools/Unreal/ui/hayba_replay.py --calls %TEMP%/intro_calls.jsonl     (lease: --areas UI)
Part 2 (graph and class defaults) is intro_widget_graph.py. Placeholder art: the approved storyboard thumbnails; the
final panels replace the textures in place (same names)."""
import json
import os
import shutil

W = '/Game/FoA/UI/Intro/WBP_IntroStory'
TEX = '/Game/FoA/UI/Intro/Textures'
UI_FONT = '/Game/FoA/UI/Fonts/F_FoA_UI'
STAGE = os.path.join(os.environ.get('TEMP', 'C:/Temp'), 'hayba-asset-connectors', 'lookdev', 'intro')
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


os.makedirs(STAGE, exist_ok=True)
for i in range(1, 9):  # asset name = file basename
    dst = os.path.join(STAGE, f'T_Intro_P{i}.jpg')
    shutil.copyfile(f'P:/FoA/Saved/LookDev/storyboard/P{i}.jpg', dst)
    c('asset_import', source_file=dst.replace('\\', '/'), destination_path=TEX, asset_type='texture')
c('ui_create_widget', path='/Game/FoA/UI/Intro', name='WBP_IntroStory')
c('ui_build_tree', widget_blueprint_path=W, tree={
    'class': 'CanvasPanel', 'name': 'Cvs_Root', 'children': [
        {'class': 'Image', 'name': 'Img_Black'},
        {'class': 'Image', 'name': 'Img_Panel'},
        {'class': 'TextBlock', 'name': 'Txt_Sub', 'properties': {'Text': ''}},
        {'class': 'Button', 'name': 'Btn_Skip'}]})
for name in ('Img_Black', 'Img_Panel', 'Btn_Skip'):  # full screen
    c('ui_set_slot_layout', widget_blueprint_path=W, widget_name=name, anchors=[0, 0, 1, 1], position=[0, 0], size=[0, 0])
c('ui_set_slot_layout', widget_blueprint_path=W, widget_name='Txt_Sub', anchors=[0, 1, 1, 1], position=[0, -150],
  size=[0, 64])
c('ui_set_brush', widget_blueprint_path=W, widget_name='Img_Black', brush_property='Brush', draw_as='Box',
  tint=[0.0, 0.0, 0.0, 1.0])
c('ui_set_brush', widget_blueprint_path=W, widget_name='Btn_Skip', brush_property='WidgetStyle.Normal', draw_as='NoDrawType')
c('ui_set_brush', widget_blueprint_path=W, widget_name='Btn_Skip', brush_property='WidgetStyle.Hovered', draw_as='NoDrawType')
c('ui_set_brush', widget_blueprint_path=W, widget_name='Btn_Skip', brush_property='WidgetStyle.Pressed', draw_as='NoDrawType')
c('ui_set_text_style', widget_blueprint_path=W, widget_name='Txt_Sub', font_asset=UI_FONT, typeface='Medium', size=34,
  color=[0.925, 0.886, 0.8, 1.0])
c('ui_set_widget_properties', widget_blueprint_path=W, widget_name='Txt_Sub', properties={'Justification': 'Center'})
for name in ('Img_Panel', 'Txt_Sub', 'Btn_Skip'):
    c('ui_set_variable', widget_blueprint_path=W, widget_name=name, is_variable=True)
c('ui_compile_widget', widget_blueprint_path=W)
c('ui_save_widget', widget_blueprint_path=W)
for d in calls:
    print(json.dumps(d))
