"""Repair existing Settings slot geometry with native Hayba calls. No trees or handlers are rebuilt."""
import json
from pathlib import Path
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

COMMON = '/Game/FoA/UI/Widgets/Common/'
SCREEN = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
OWNER = 'ui_settings_layout'
TOKEN = None
STRETCH = dict(anchors_min=[0, 0], anchors_max=[1, 1], position=[0, 0], size=[0, 0], auto_size=False)


def call(cmd, **params):
    response = hc.call(cmd, params, owner=OWNER, lease=TOKEN)
    assert response.get('ok'), response
    data = response.get('data', {})
    assert data.get('ok', True), data
    assert not data.get('unknown_slot_props') and not data.get('rejected_properties'), data
    return data


def props(path, name, values=None, slot=None):
    params = dict(widget_blueprint_path=path, widget_name=name)
    if values is not None:
        params['properties'] = values
    if slot is not None:
        params['slot_props'] = slot
    return call('ui_set_widget_properties', **params)


def by_name(root):
    result = {}
    def visit(node):
        if not isinstance(node, dict):
            return
        result[node['name']] = node
        for child in node.get('children', []):
            visit(child)
    visit(root)
    return result


def repair(path):
    if path == SCREEN:
        for name in ('Img_Scrim', 'Brd_Content'):
            props(path, name, slot=STRETCH)
        # The scrim is a real full-screen surface, so Pause never competes with Settings.
        props(path, 'Img_Scrim', dict(Brush=dict(DrawAs='Box', TintColor=dict(SpecifiedColor=[0.003, 0.003, 0.003, 1.0]))))
        props(path, 'Size_Tabs', slot=dict(fill=0, horizontal_alignment='Fill', vertical_alignment='Fill'))
        props(path, 'Switch_Pages', slot=dict(fill=1, horizontal_alignment='Fill', vertical_alignment='Fill', padding=[60, 0, 0, 0]))
        for name in ('Txt_Header', 'Txt_AutoSave', 'Btn_Back'):
            props(path, name, slot=dict(fill=0))
        props(path, 'HB_Body', slot=dict(fill=1))
    else:
        props(path, 'Ovl_Row', slot=STRETCH)
        for name in ('Img_Focus', 'HB_Row'):
            props(path, name, slot=dict(horizontal_alignment='Fill', vertical_alignment='Fill'))
        for name in ('Txt_Label', 'Txt_Value'):
            props(path, name, slot=dict(horizontal_alignment='Fill', vertical_alignment='Center'))
        if path.endswith('Switcher'):
            props(path, 'Size_Label', slot=dict(fill=1, vertical_alignment='Center'))
            for name in ('Size_Prev', 'Size_Value', 'Size_Next'):
                props(path, name, slot=dict(fill=0, vertical_alignment='Center'))
        else:
            props(path, 'Size_Label', slot=dict(fill=0, vertical_alignment='Center'))
            props(path, 'Size_Value', slot=dict(fill=0, vertical_alignment='Center'))
            props(path, 'Sld_Value', slot=dict(fill=1, vertical_alignment='Center', padding=[20, 0, 24, 0]))


def main():
    global TOKEN
    state = call('editor_get_state')
    assert not state['pie_running'], 'Settings authoring requires PIE stopped'
    receipts = []
    for path in (COMMON + 'WBP_SettingRow_Slider', COMMON + 'WBP_SettingRow_Switcher', SCREEN):
        TOKEN = hc.lease_acquire(OWNER, ['asset:' + path], ttl_s=90, wait_s=10)
        try:
            before = call('ui_query', path=path, include_properties=True, include_slot=True)
            repair(path)
            compiled = call('blueprint_compile', path=path, save=True)
            assert compiled['error_count'] == compiled['warning_count'] == 0, compiled
            assert compiled['saved'] and not compiled['dirty'], compiled
            after = call('ui_query', path=path, include_properties=True, include_slot=True)
            widgets = by_name(after['root'])
            for name in (('Img_Scrim', 'Brd_Content') if path == SCREEN else ('Ovl_Row',)):
                assert widgets[name]['slot']['anchors'] == dict(min_x=0, min_y=0, max_x=1, max_y=1), widgets[name]
            receipts.append(dict(path=path, before=before, after=after, compile=compiled))
            print('Saved clean Settings slot repair:', path)
        finally:
            hc.release(OWNER, TOKEN)
            TOKEN = None
    Path('Saved/UIShots/settings_layout_repair.json').write_text(json.dumps(receipts, indent=2))
    print('Native geometry verified; real 1280/960 runtime images remain required')


if __name__ == '__main__':
    main()
