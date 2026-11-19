"""In-place WBP_Encounter layout refinement using Hayba only; existing widgets and graph references survive.

Generate icons first with make_battle_icons.ps1. Run --selftest offline, --apply after user PIE ends.
The caller holds a UI/Gameplay lease. No shared button, font or material asset is modified.
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gen_encounter_tree import text, panel, canvas, pad, hbox, vbox  # noqa: E402

WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
ICONS = '/Game/FoA/Gameplay/Encounter/Icons'
ICON_NAMES = ('Act', 'Breathe', 'Mirror', 'Items', 'Flee', 'Target', 'Composure', 'Resolve')


def icon(name, kind, size=28):
    return {'class': 'Image', 'name': name, 'properties': {
        'Brush': f'(ResourceObject="/Script/Engine.Texture2D\'{ICONS}/T_Battle_{kind}.T_Battle_{kind}\'",'
                 f'ImageSize=(X={size},Y={size}),DrawAs=Image)',
        'ColorAndOpacity': '(R=0.92,G=0.92,B=0.92,A=1)', 'Visibility': 'HitTestInvisible'}}


def additions():
    command = canvas(panel('CommandPanel', hbox('BattleCommandHost', []),
                           '(Left=28,Top=24,Right=28,Bottom=22)'), [0, 1], [0, 1], [48, -48], [1160, 340])
    command['properties']['Background'] = '(DrawAs=Box,TintColor=(SpecifiedColor=(R=0.004,G=0.004,B=0.004,A=0.93)))'
    command['properties']['bIsVariable'] = True
    enemies = canvas(panel('EnemyPanel', vbox('BattleEnemyHost', []),
                           '(Left=22,Top=18,Right=22,Bottom=18)'), [0, 0], [0, 0], [48, 160], [410, 510])
    enemies['properties']['Background'] = '(DrawAs=Box,TintColor=(SpecifiedColor=(R=0.004,G=0.004,B=0.004,A=0.78)))'
    phase = canvas(text('Txt_BattlePhase', 'HUDPrompt', 'Getting dressed', size=26, just='Center'),
                   [0.5, 0], [0.5, 0], [0, 114], [1000, 50])
    phase['properties']['bIsVariable'] = True
    hint = canvas(text('Txt_BattleHelp', 'Body', 'Arrow keys navigate commands. Enter or gamepad A confirms. Change target switches clothes.',
                       size=22, alpha=0.95), [0, 1], [0, 1], [72, -16], [1150, 30])
    hint['properties']['bIsVariable'] = True
    return [command, enemies, phase, hint]


def selftest():
    nodes = additions()
    names = []
    def walk(n):
        names.append(n['name'])
        for child in n.get('children', []):
            walk(child)
    for n in nodes:
        walk(n)
    assert len(names) == len(set(names))
    assert 'CommandPanel' in names and 'Txt_BattlePhase' in names
    assert len(ICON_NAMES) == len(set(ICON_NAMES))
    assert not any(c in json.dumps(nodes, ensure_ascii=False) for c in ('·', '•'))
    print('battle UI selfcheck: unique in-place widgets, eight labelled icons, no decorative separators')


def apply():
    from hayba_call import call
    moves = []
    def c(cmd, **params):
        r = call(cmd, params)
        assert r.get('ok'), (cmd, r)
        data = r.get('data', {})
        assert not data.get('failed_properties') and not data.get('partial') and not data.get('failed'), (cmd, data)
        return data
    state = c('editor_get_state')
    assert not state.get('pie_running'), 'User PIE must end before applying UI'
    def props(name, properties=None, slot_props=None):
        p = {'widget_blueprint_path': WBP, 'widget_name': name}
        if properties:
            p['properties'] = properties
        if slot_props:
            p['slot_props'] = slot_props
        return c('ui_set_widget_properties', **p)
    def exists(name):
        return bool(c('ui_query', path=WBP, name_pattern=name).get('matches'))
    def add(node, parent='RootCanvas'):
        if not exists(node['name']):
            c('ui_build_tree', widget_blueprint_path=WBP, parent_widget_name=parent, tree=node)
    def move(name, parent, **slot):
        # Installed Hayba DLL lacks ui_reparent_element; the editor fallback preserves these exact widget objects.
        moves.append({'widget': name, 'parent': parent, 'slot': slot})

    for kind in ICON_NAMES:
        path = Path(os.environ['TEMP']) / 'hayba-asset-connectors' / 'foa' / 'battle' / f'T_Battle_{kind}.png'
        assert path.exists(), path
        # asset_import never overwrites. Existing originals are reused on the next pass.
        result = call('asset_import', {'source_file': str(path), 'destination_path': ICONS, 'asset_type': 'texture'})
        assert result.get('ok') or result.get('data', {}).get('code') == 'HAI_COLLISION', result
    for n in additions():
        add(n)
        if n.get('slot_props'):
            props(n['name'], slot_props=n['slot_props'])
        if n['name'] == 'Txt_BattleHelp':
            props(n['name'], properties=n['properties'])
            c('ui_set_variable', widget_blueprint_path=WBP, widget_name=n['name'], is_variable=True)
    move('CommandBox', 'BattleCommandHost', fill=1)
    move('EnemyRows', 'BattleEnemyHost')
    props('ActBox', slot_props={'padding': [0, 0, 48, 0], 'fill': 1})
    props('Txt_Target', text('x', 'H2', '', size=28)['properties'] | {'Text': 'The Shirt (inside out)'},
          {'padding': [0, 0, 0, 12]})
    props('LogPanel', slot_props={'anchors_min': [0.5, 0], 'anchors_max': [0.5, 0], 'alignment': [0.5, 0],
                                 'position': [0, 34], 'size': [1120, 68], 'auto_size': True})  # UI's plate fix (B3)
    props('Txt_Narration', {'WrapTextAt': 1060})
    props('SelfBox', slot_props={'position': [-48, -72]})
    props('PromptBox', slot_props={'position': [0, 60]})
    # The row graph reads its three children by index; their order and classes stay intact.
    for i in range(5):
        props(f'Row{i}', slot_props={'padding': [0, 0, 0, 6]})
        props(f'Txt_Enemy{i}', text('x', 'H2', '', size=24)['properties'] |
              {'Text': 'The Shirt (inside out)', 'LineHeightPercentage': 1})
        props(f'Pips{i}', slot_props={'padding': [0, 3, 0, 0]})
        props(f'Txt_Intent{i}', text('x', 'Narration', '', size=20, alpha=1)['properties'] |
              {'Text': 'Waiting.', 'WrapTextAt': 366, 'LineHeightPercentage': 1}, {'padding': [0, 2, 0, 0]})
    for name, label, kind in (('Breathe', 'Deep breath', 'Breathe'), ('Mirror', 'Check mirror', 'Mirror'),
                              ('Items', 'Items', 'Items'), ('Flee', 'Try to leave', 'Flee'),
                              ('NextTarget', 'Change target', 'Target')):
        row = f'BattleRow_{name}'
        add(hbox(row, [pad(icon(f'Icon_{name}', kind), right=12, vertical_alignment='Center')]), 'CmdButtons')
        move(f'Btn_{name}', row, padding=[0, 0, 0, 0])
        props(f'Btn_{name}', {'Label': label, 'TextAlphaRest': 0.95, 'TextAlphaDisabled': 0.5,
                             'SandMaterial': '/Game/FoA/UI/Materials/MI_UI_SandText_Menu.MI_UI_SandText_Menu'},
              {'padding': [0, 0, 0, 0]})
    # Keep ActButtons' direct children because RefreshAct casts them to WBP_SandButton.
    add(hbox('BattleActRow', [pad(vbox('BattleActIcons', [
        pad(icon('Icon_Act0', 'Act'), bottom=24, top=4), icon('Icon_Act1', 'Act')]), right=12)]), 'ActBox')
    move('ActButtons', 'BattleActRow')
    for i in range(3):
        props(f'Btn_Act{i}', {'TextAlphaRest': 0.95, 'TextAlphaDisabled': 0.5,
                              'SandMaterial': '/Game/FoA/UI/Materials/MI_UI_SandText_Menu.MI_UI_SandText_Menu'})
    for stat in ('Composure', 'Resolve'):
        row = f'Row_{stat}'
        add(pad(icon(f'Icon_{stat}', stat, 32), right=10, vertical_alignment='Center'), row)
        props(f'Icon_{stat}', icon(f'Icon_{stat}', stat, 32)['properties'])
    out = Path('P:/FoA/Saved/EncounterCaptures/battle_reparent.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(moves), encoding='utf-8')
    print(f'Battle layout properties applied; {len(moves)} in-place reparent operations queued in {out}')


if __name__ == '__main__':
    selftest()
    if '--apply' in sys.argv:
        apply()
