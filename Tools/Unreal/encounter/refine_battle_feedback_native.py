"""Native in-place battle feedback repairs. Complete read-only graph export supplies verified GUIDs."""
import json
from pathlib import Path
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
ENC = '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'
OWNER = 'ui_battle_feedback'
TOKEN = None


def call(cmd, **params):
    result = hc.call(cmd, params, owner=OWNER, lease=TOKEN)
    assert result.get('ok'), result
    data = result.get('data', {})
    assert data.get('ok', True) and not data.get('failed'), data
    return data


def link(a, b, output='then', input='execute'):
    return dict(op='connect', from_node=a, from_pin=output, to_node=b, to_pin=input)


def main():
    global TOKEN
    assert not call('editor_get_state')['pie_running']
    full = json.loads(Path('Saved/UIShots/battle_feedback_full.json').read_text())
    TOKEN = hc.lease_acquire(OWNER, ['asset:' + WBP], ttl_s=60, wait_s=10)
    receipts = {}
    try:
        g = full['RefreshBattlePresentation']
        nodes, edges = g['nodes'], g['edges']
        if any(n['title'] == 'Get Txt_BattleHelp' for n in nodes):
            eg = full['EventGraph']
            items = next(n['node_id'] for n in eg['nodes'] if n['title'] == 'Items')
            assert any(n['title'] == 'MoveLabel' for n in nodes), 'Partial presentation patch'
            assert any(e['from_node'] == items and e['from_pin'] == 'then' for e in eg['edges']), 'Partial Items patch'
            print('Battle feedback already configured; no compile needed')
            return
        phase = next(n['node_id'] for n in nodes if n['title'] == 'Get Txt_BattlePhase')
        phase_set = next(e['to_node'] for e in edges if e['from_node'] == phase and e['to_pin'] == 'self')
        mirror_get = [n['node_id'] for n in nodes if n['title'] == 'Get Btn_Mirror']
        mirror_set = next(e['to_node'] for e in edges if e['from_node'] in mirror_get and e['to_pin'] == 'self'
                          and next(n['title'] for n in nodes if n['node_id'] == e['to_node']) == 'SetLabel')
        encounter = next(n['node_id'] for n in nodes if n['title'] == 'Get Encounter')
        call('ui_set_variable', widget_blueprint_path=WBP, widget_name='Txt_BattleHelp', is_variable=True)
        call('blueprint_compile', path=WBP)
        ops = [dict(op='add_node', ref='help', node_type='variable_get', variable_name='Txt_BattleHelp', x=1760, y=-260),
               dict(op='disconnect', node_id=phase_set, pin_name='self'), link('help', phase_set, 'Txt_BattleHelp', 'self'),
               dict(op='add_node', ref='mirror_move', node_type='variable_get', variable_name='MirrorMove', class_path=ENC, x=2180, y=-1200),
               dict(op='add_node', ref='mirror_label', node_type='call_function', function_name=WBP+'.WBP_Encounter_C:MoveLabel', x=2500, y=-1200),
               link(encounter, 'mirror_move', 'Encounter', 'self'), link('mirror_move', 'mirror_label', 'MirrorMove', 'Move'),
               link('mirror_label', mirror_set, 'Label', 'NewLabel')]
        replacements = {'Your turn. Choose an action.':'Your turn. Arrows or D-pad choose; Enter or A confirms.',
                        'The clothes move':"Clothes' turn. Watch their next move."}
        for n in nodes:
            if n['title'] == 'SelectString':
                for pin in n['pins']:
                    if pin['name'] == 'A' and pin['default'] in replacements:
                        ops.append(dict(op='set_pin', node_id=n['node_id'], pin_name='A', value=replacements[pin['default']]))
        ops += [dict(op='comment', title='Actual mirror cost', node_ids=['mirror_move','mirror_label'], color=[.12,.26,.16]),
                dict(op='fit_comments', title_only=True)]
        receipts['presentation'] = call('blueprint_graph_batch', path=WBP, graph_name='RefreshBattlePresentation', ops=ops)
        g = full['EventGraph']; nodes, edges = g['nodes'], g['edges']
        items = next(n['node_id'] for n in nodes if n['title'] == 'Items')
        assert not any(e['from_node'] == items and e['from_pin'] == 'then' for e in edges)
        encounter = next(e['from_node'] for e in edges if e['to_node'] == items and e['to_pin'] == 'self')
        ops = [dict(op='add_node', ref='line', node_type='variable_get', variable_name='Narration', class_path=ENC, x=1450, y=2500),
               dict(op='add_node', ref='text', node_type='variable_get', variable_name='Txt_Narration', x=1450, y=2700),
               dict(op='add_node', ref='feedback', node_type='call_function', function_name='/Script/UMG.TextBlock:SetText', x=1780, y=2300),
               link(encounter, 'line', 'Encounter', 'self'), link('line', 'feedback', 'Narration', 'InText'),
               link('text', 'feedback', 'Txt_Narration', 'self'), link(items, 'feedback'),
               dict(op='comment', title='Keep the items response', node_ids=['line','text','feedback'], color=[.3,.22,.1]),
               dict(op='fit_comments', title_only=True)]
        receipts['items'] = call('blueprint_graph_batch', path=WBP, graph_name='EventGraph', ops=ops)
        receipts['compile'] = call('blueprint_compile', path=WBP, save=True)
        c = receipts['compile']
        assert c['error_count'] == c['warning_count'] == 0 and c['saved'] and not c['dirty'], c
        Path('Saved/UIShots/battle_feedback_repair.json').write_text(json.dumps(receipts, indent=2))
        print('Battle truthful footer, dynamic Mirror cost and Items response saved; runtime proof pending')
    finally:
        hc.release(OWNER, TOKEN)


if __name__ == '__main__':
    main()
