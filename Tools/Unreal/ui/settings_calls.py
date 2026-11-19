"""Create missing settings trees through Hayba C++; later refinements edit their properties in place.
python Tools/Unreal/ui/settings_calls.py rows|screen > Saved/UIShots/settings_<part>.jsonl
"""
import ast
import json
import pathlib
import sys

COMMON = '/Game/FoA/UI/Widgets/Common'
MENUS = '/Game/FoA/UI/Widgets/Menus'
UI_FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
DISPLAY_FONT = '/Game/FoA/UI/Fonts/F_FoA_Display.F_FoA_Display'
PAPER = [0.86, 0.86, 0.86, 1.0]
MUTED = [0.62, 0.62, 0.62, 1.0]
SLIDER = COMMON + '/WBP_SettingRow_Slider.WBP_SettingRow_Slider_C'
SWITCH = COMMON + '/WBP_SettingRow_Switcher.WBP_SettingRow_Switcher_C'
SAND_BUTTON = COMMON + '/WBP_SandButton.WBP_SandButton_C'


def emit(cmd, **params):
    print(json.dumps(dict(cmd=cmd, params=params)))


def repair_slots(path):
    import fix_settings_layout
    fix_settings_layout.call = emit
    fix_settings_layout.repair(path)


def text(name, label, size=24, display=False, muted=False, **extra):
    return dict(class_='TextBlock', name=name, properties=dict(Text=label,
        Font=dict(FontObject=DISPLAY_FONT if display else UI_FONT,
                  TypefaceFontName='ExtraBold' if display else 'SemiBold', Size=size),
        ColorAndOpacity=dict(SpecifiedColor=MUTED if muted else PAPER), **extra))


def node(kind, name, children=(), properties=None, slot=None):
    result = dict(class_=kind, name=name)
    if children:
        result['children'] = list(children)
    if properties:
        result['properties'] = properties
    if slot:
        result['slot_props'] = slot
    return result


def clean(value):
    if isinstance(value, dict):
        if value.get('class_') == 'SizeBox':
            for axis in ('Width', 'Height'):
                if axis + 'Override' in value.get('properties', {}):
                    value['properties']['bOverride_' + axis + 'Override'] = True
        return {('class' if k == 'class_' else k): clean(v) for k, v in value.items()}
    return [clean(v) for v in value] if isinstance(value, list) else value


def make_rows():
    for kind in ('Slider', 'Switcher'):
        path = f'{COMMON}/WBP_SettingRow_{kind}'
        label = node('SizeBox', 'Size_Label', [text('Txt_Label', 'Setting')], dict(WidthOverride=300.0))
        value = node('SizeBox', 'Size_Value', [text('Txt_Value', '100', Justification='Center')],
                     dict(WidthOverride=72.0 if kind == 'Slider' else 240.0))
        controls = [label]
        if kind == 'Slider':
            controls += [node('Slider', 'Sld_Value', properties=dict(SliderBarColor=[0.60, 0.60, 0.60, 1],
                SliderHandleColor=PAPER, IsFocusable=True), slot=dict(fill=1, padding=[20, 0, 24, 0],
                vertical_alignment='Fill')), value]
        else:
            for name, glyph in (('Prev', '<'), ('Next', '>')):
                button = node('Button', 'Btn_' + name, [text('Txt_' + name, glyph, 32, Justification='Center')],
                              dict(BackgroundColor=[0, 0, 0, 0], IsFocusable=True))
                sized = node('SizeBox', 'Size_' + name, [button], dict(WidthOverride=48.0, HeightOverride=48.0))
                if name == 'Prev':
                    controls += [sized, value]
                else:
                    controls.append(sized)
            label['slot_props'] = dict(fill=1)
        content = node('Overlay', 'Ovl_Row', [
            node('Image', 'Img_Focus', properties=dict(Visibility='Hidden', Brush=dict(DrawAs='Box',
                 TintColor=dict(SpecifiedColor=[1, 1, 1, 0.14])))),
            node('HorizontalBox', 'HB_Row', controls)], slot=dict(anchors_min=[0, 0], anchors_max=[1, 1], position=[0, 0], size=[0, 0]))
        emit('ui_create_widget', path=COMMON, name='WBP_SettingRow_' + kind)
        emit('ui_build_tree', widget_blueprint_path=path, parent_widget_name='RootCanvas', tree=clean(content))
        for name in ('Txt_Label', 'Txt_Value', 'Img_Focus') + (('Sld_Value',) if kind == 'Slider' else ('Btn_Prev', 'Btn_Next')):
            emit('ui_set_variable', widget_blueprint_path=path, widget_name=name, is_variable=True)
        if kind == 'Switcher':
            emit('blueprint_add_event', path=path, event_name='OnKeyDown')
        repair_slots(path)
        emit('ui_compile_widget', widget_blueprint_path=path)
        emit('ui_save_widget', widget_blueprint_path=path)


ROWS = [
    ('Graphics', 'Row_Quality', 'Quality', ['Low', 'Medium', 'High', 'Epic', 'Cinematic']),
    ('Graphics', 'Row_WindowMode', 'Window mode', ['Fullscreen', 'Borderless', 'Windowed']),
    ('Graphics', 'Row_VSync', 'VSync', ['Off', 'On']),
    ('Graphics', 'Row_FrameCap', 'Frame rate limit', ['30', '60', '120', 'Unlimited']),
    ('Graphics', 'Row_ResScale', 'Resolution scale (%)', (25.0, 100.0, 5.0, 1.0, 0)),
    ('Graphics', 'Row_Resolution', 'Resolution', ['1280 x 720', '1600 x 900', '1920 x 1080', '2560 x 1440',
                                              '3840 x 2160', '2560 x 1080', '3440 x 1440']),
    ('Audio', 'Row_Master', 'Master volume', (0.0, 1.0, 0.05, 100.0, 0)),
    ('Audio', 'Row_Effects', 'Effects volume', (0.0, 1.0, 0.05, 100.0, 0)),
    ('Audio', 'Row_Ambience', 'Ambience volume', (0.0, 1.0, 0.05, 100.0, 0)),
    ('Audio', 'Row_Interface', 'Interface volume', (0.0, 1.0, 0.05, 100.0, 0)),
    ('Controls', 'Row_Sensitivity', 'Mouse sensitivity', (0.25, 2.5, 0.05, 1.0, 2)),
    ('Controls', 'Row_InvertY', 'Invert vertical look', ['Off', 'On']),
    ('Access', 'Row_Subtitles', 'Subtitles', ['Off', 'On']),
    ('Access', 'Row_SubtitleSize', 'Subtitle size', ['Small', 'Medium', 'Large']),
    ('Access', 'Row_ReduceMotion', 'Reduce motion', ['Off', 'On']),
    ('Access', 'Row_PhotoWarning', 'Photosensitivity warning', ['Off', 'On']),
]
TABS = [('Graphics', 'Graphics'), ('Audio', 'Audio'), ('Controls', 'Controls'), ('Access', 'Accessibility')]


def check_rows():
    source = ast.parse(pathlib.Path('Tools/Unreal/ui/wire_settings.py').read_text())
    expected = {entry[0] for n in source.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id in ('GRAPHICS', 'SAVED') for t in n.targets)
                for entry in ast.literal_eval(n.value)}
    assert len(ROWS) == 16 and {r[1] for r in ROWS} == expected
    assert all(len(spec) >= 2 for _, _, _, spec in ROWS)
    assert not any(c in label for _, _, label, _ in ROWS for c in '·•|/—–')


def make_screen():
    check_rows()
    path = MENUS + '/WBP_Settings'
    tabs = [node(SAND_BUTTON, 'Btn_Tab' + key, properties=dict(Label=label, bPlainLabel=True, LabelSize=32.0),
                 slot=dict(padding=[0, 0, 0, 20])) for key, label in TABS]
    pages = []
    for key, _ in TABS:
        rows = []
        for page, name, label, spec in ROWS:
            if page != key:
                continue
            props = dict(Label=label)
            if isinstance(spec, list):
                props['Options'] = spec
            else:
                props.update(zip(('MinValue', 'MaxValue', 'StepSize', 'DisplayScale', 'DisplayDecimals'), spec))
                if name == 'Row_ResScale':
                    props['Value'] = 100.0
            row = node(SWITCH if isinstance(spec, list) else SLIDER, name, properties=props)
            row_properties=dict(HeightOverride=64.0)
            if name=='Row_PhotoWarning':row_properties['Visibility']='Collapsed' # Startup warning consumer remains staged.
            rows.append(node('SizeBox', 'Size_' + name, [row], row_properties,
                             slot=dict(padding=[0, 0, 0, 14])))
        pages.append(node('VerticalBox', 'Page_' + key, rows))
    content = node('VerticalBox', 'VB_Settings', [
        text('Txt_Header', 'Settings', 59, display=True),
        dict(**text('Txt_AutoSave', 'Changes are saved automatically.', 20, muted=True),
             slot_props=dict(padding=[0, 8, 0, 48])),
        node('HorizontalBox', 'HB_Body', [
            node('SizeBox', 'Size_Tabs', [node('VerticalBox', 'VB_Tabs', tabs)], dict(WidthOverride=340.0)),
            node('WidgetSwitcher', 'Switch_Pages', pages, slot=dict(fill=1, padding=[60, 0, 0, 0]))], slot=dict(fill=1)),
        node(SAND_BUTTON, 'Btn_Back', properties=dict(Label='Back', bPlainLabel=True, LabelSize=32.0), slot=dict(horizontal_alignment='Left', padding=[0, 28, 0, 0]))])
    emit('ui_create_widget', path=MENUS, name='WBP_Settings')
    emit('ui_build_tree', widget_blueprint_path=path, parent_widget_name='RootCanvas', tree=clean([
        node('Image', 'Img_Scrim', properties=dict(Brush=dict(DrawAs='Box',
            TintColor=dict(SpecifiedColor=[0.003, 0.003, 0.003, 0.96])), Visibility='HitTestInvisible'),
            slot=dict(anchors_min=[0, 0], anchors_max=[1, 1], position=[0, 0], size=[0, 0])),
        node('Border', 'Brd_Content', [content], properties=dict(Padding='(Left=146,Top=112,Right=146,Bottom=80)',
             BrushColor=[0, 0, 0, 0]), slot=dict(anchors_min=[0, 0], anchors_max=[1, 1], position=[0, 0], size=[0, 0]))]))
    for name in [r[1] for r in ROWS] + ['Switch_Pages', 'Btn_Back'] + ['Btn_Tab' + key for key, _ in TABS]:
        emit('ui_set_variable', widget_blueprint_path=path, widget_name=name, is_variable=True)
    emit('blueprint_add_event', path=path, event_name='OnKeyDown')
    repair_slots(path)
    emit('ui_compile_widget', widget_blueprint_path=path)
    emit('ui_save_widget', widget_blueprint_path=path)


if __name__ == '__main__':
    check_rows()
    {'rows': make_rows, 'screen': make_screen}[sys.argv[1]]()
