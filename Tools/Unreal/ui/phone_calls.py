"""Writes the Hayba call list that creates WBP_Phone's widget tree (replay: hayba_replay.py --calls; graph: wire_phone.py).
The widget is the phone's SCREEN, drawn by BP_Phone's world-space WidgetComponent (540 x 1170), never a 2D overlay.
  python Tools/Unreal/ui/phone_calls.py > Saved/UIShots/phone.jsonl
The phone at T0 and T10: clock, day and crossed-out days, the four tasks, the notebook, one action (Wake up, then Put the
phone away). Plain sentences, no labels or separators (the user's text rules)."""
import json

P = '/Game/FoA/UI/Game/WBP_Phone'
F = '/Game/FoA/UI/Fonts'
DISPLAY, UI = f'{F}/F_FoA_Display', f'{F}/F_FoA_UI'
BTN = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
INK, MUTED = [0.86, 0.86, 0.86, 1.0], [0.86, 0.86, 0.86, 0.62]
calls = []


def c(cmd, **p):
    calls.append({'cmd': cmd, 'params': p})


def text(name, txt):
    return {'class': 'TextBlock', 'name': name, 'properties': {'Text': txt}}


c('ui_create_widget', path='/Game/FoA/UI/Game', name='WBP_Phone')
c('ui_build_tree', widget_blueprint_path=P, tree={
    'class': 'Border', 'name': 'Brd_Screen', 'children': [
        {'class': 'VerticalBox', 'name': 'VB_Phone', 'children': [
            text('Txt_Clock', '6:40'),
            {'class': 'HorizontalBox', 'name': 'HB_Day', 'children': [text('Txt_DayLabel', 'Day'), text('Txt_DayNum', '18')]},
            {'class': 'HorizontalBox', 'name': 'HB_Crossed', 'children': [
                text('Txt_Crossed', '17'), text('Txt_CrossedLabel', 'days crossed out')]},
            {'class': 'VerticalBox', 'name': 'VB_Tasks', 'children': [
                text('Txt_Task0', 'Wake up'), text('Txt_Task1', 'Get dressed'),
                text('Txt_Task2', 'Leave the house'), text('Txt_Task3', 'Find a job')]},
            text('Txt_Notebook', ''),
            {'class': 'Spacer', 'name': 'Spc_Push'},
            {'class': BTN, 'name': 'Btn_Action'},
        ]}]})
# the screen fills the widget component's 540 x 1170 draw size (a 19.5:9 phone); content sits 56 px in
c('ui_set_widget_properties', widget_blueprint_path=P, widget_name='Brd_Screen',
  slot_props={'anchors_min': [0, 0], 'anchors_max': [1, 1], 'position': [0, 0], 'size': [0, 0], 'auto_size': False})
c('ui_set_brush', widget_blueprint_path=P, widget_name='Brd_Screen', brush_property='Background', draw_as='RoundedBox',
  tint=[0.006, 0.006, 0.006, 1.0])
c('ui_set_widget_properties', widget_blueprint_path=P, widget_name='Brd_Screen',
  properties={'Padding': '(Left=56,Top=96,Right=56,Bottom=72)'})
for name, pad in (('HB_Day', [0, 12, 0, 0]), ('HB_Crossed', [0, 6, 0, 0]), ('VB_Tasks', [0, 64, 0, 0]),
                  ('Txt_Notebook', [0, 40, 0, 0]), ('Btn_Action', [0, 24, 0, 0])):
    c('ui_set_widget_properties', widget_blueprint_path=P, widget_name=name, slot_props={'padding': pad})
c('ui_set_widget_properties', widget_blueprint_path=P, widget_name='Spc_Push', slot_props={'fill': 1})
c('ui_set_widget_properties', widget_blueprint_path=P, widget_name='Txt_DayNum', slot_props={'padding': [10, 0, 0, 0]})
c('ui_set_widget_properties', widget_blueprint_path=P, widget_name='Txt_CrossedLabel', slot_props={'padding': [8, 0, 0, 0]})
for i in range(1, 4):
    c('ui_set_widget_properties', widget_blueprint_path=P, widget_name=f'Txt_Task{i}', slot_props={'padding': [0, 14, 0, 0]})
# type (Darker Grotesque)
for name, font, face, size, col in (('Txt_Clock', DISPLAY, 'ExtraBold', 64, INK), ('Txt_DayLabel', UI, 'SemiBold', 19, INK),
                                    ('Txt_DayNum', UI, 'SemiBold', 19, INK), ('Txt_Crossed', UI, 'Medium', 16, MUTED),
                                    ('Txt_CrossedLabel', UI, 'Medium', 16, MUTED), ('Txt_Notebook', UI, 'Medium', 18, MUTED)) + \
        tuple((f'Txt_Task{i}', UI, 'SemiBold', 24, INK) for i in range(4)):
    c('ui_set_widget_properties', widget_blueprint_path=P, widget_name=name, properties={
        'Font': f'(FontObject="/Script/Engine.Font\'{font}.{font.rsplit("/", 1)[1]}\'",TypefaceFontName="{face}",Size={size})',
        'ColorAndOpacity': f'(SpecifiedColor=(R={col[0]},G={col[1]},B={col[2]},A={col[3]}),ColorUseRule=UseColor_Specified)'})
c('ui_set_widget_properties', widget_blueprint_path=P, widget_name='Txt_Notebook',
  properties={'AutoWrapText': True, 'Visibility': 'Collapsed'})
c('ui_set_variable', widget_blueprint_path=P, widget_name='Btn_Action', is_variable=True)
for i in range(4):
    c('ui_set_variable', widget_blueprint_path=P, widget_name=f'Txt_Task{i}', is_variable=True)
for name in ('Txt_DayNum', 'Txt_Crossed', 'Txt_Notebook'):
    c('ui_set_variable', widget_blueprint_path=P, widget_name=name, is_variable=True)
c('ui_compile_widget', widget_blueprint_path=P)
c('ui_save_widget', widget_blueprint_path=P)
for d in calls:
    print(json.dumps(d))
