"""Native Hayba: give narration a bounded backplate and keep it out of tool instructions."""
import json
from pathlib import Path
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

HUD = '/Game/FoA/UI/Game/WBP_HUD'
OWNER = 'ui_pacing_recovery'
TOKEN = None


def call(command, **params):
    reply = hc.call(command, params, owner=OWNER, lease=TOKEN)
    assert reply.get('ok'), reply
    data = reply.get('data', {})
    assert data.get('ok', True) and not data.get('failed') and not data.get('unknown_slot_props'), data
    return data


def link(a, b, output='then', input='execute'):
    return dict(op='connect', from_node=a, from_pin=output, to_node=b, to_pin=input)


def graph_patch(name, visibility):
    graph = call('blueprint_inspect_graph', path=HUD, graph_name=name)
    nodes, edges = graph['nodes'], graph['edges']
    if any(n['title'] == 'Get Brd_Narration' for n in nodes):
        return
    text = next(n['node_id'] for n in nodes if n['title'] == 'SetText (Text)')
    after = [e for e in edges if e['from_node'] == text and e['from_pin'] == 'then']
    ops = [dict(op='add_node', ref='plate', node_type='variable_get', variable_name='Brd_Narration', x=1040, y=440),
           dict(op='add_node', ref='visible', node_type='call_function',
                function_name='/Script/UMG.Widget:SetVisibility', x=1280, y=0),
           dict(op='set_pin', node_id='visible', pin_name='InVisibility', value=visibility),
           link('plate', 'visible', 'Brd_Narration', 'self')]
    if after:
        assert len(after) == 1
        ops += [dict(op='disconnect', node_id=text, pin_name='then'),
                link('visible', after[0]['to_node'], 'then', after[0]['to_pin'])]
    ops.append(link(text, 'visible'))
    if name == 'HandleNarration':
        branch = next(n['node_id'] for n in nodes if n['title'] == 'Branch')
        condition = next(e for e in edges if e['to_node'] == branch and e['to_pin'] == 'Condition')
        ops += [dict(op='disconnect', node_id=branch, pin_name='Condition'),
                dict(op='add_node', ref='tool', node_type='variable_get', variable_name='bToolStatus', x=-520, y=300),
                dict(op='add_node', ref='not_tool', node_type='call_function', function_name='/Script/Engine.KismetMathLibrary:Not_PreBool', x=-240, y=300),
                dict(op='add_node', ref='allowed', node_type='call_function', function_name='/Script/Engine.KismetMathLibrary:BooleanAND', x=80, y=240),
                link('tool', 'not_tool', 'bToolStatus', 'A'), link('not_tool', 'allowed', 'ReturnValue', 'B'),
                link(condition['from_node'], 'allowed', condition['from_pin'], 'A'),
                link('allowed', branch, 'ReturnValue', 'Condition')]
    ops += [dict(op='comment', title='Narration backplate', node_ids=['plate', 'visible'], color=[.18, .28, .34]), dict(op='fit_comments')]
    call('blueprint_graph_batch', path=HUD, graph_name=name, ops=ops)


def main():
    global TOKEN
    assert not call('editor_get_state')['pie_running'], 'PIE must be stopped'
    TOKEN = hc.lease_acquire(OWNER, ['asset:' + HUD], ttl_s=90, wait_s=10)
    try:
        query = call('ui_query', path=HUD, name_pattern='Brd_Narration')
        if not query.get('matches'):
            call('ui_build_tree', widget_blueprint_path=HUD, parent_widget_name='Ovl_Frame', tree=dict(
                **{'class': 'Border'}, name='Brd_Narration', properties=dict(Visibility='Collapsed',
                BrushColor=[.006, .006, .006, .88], Padding='(Left=20,Top=12,Right=20,Bottom=12)'),
                slot_props=dict(horizontal_alignment='Center', vertical_alignment='Bottom', padding=[48, 0, 48, 118])))
            call('ui_set_variable', widget_blueprint_path=HUD, widget_name='Brd_Narration', is_variable=True)
        call('ui_mutate_tree', operation='reparent', widget_blueprint_path=HUD, widget_name='Txt_Narration',
             new_parent_name='Brd_Narration', slot_props=dict(horizontal_alignment='Center', vertical_alignment='Center'))
        call('blueprint_compile', path=HUD)
        call('ui_set_widget_properties', widget_blueprint_path=HUD, widget_name='Txt_Narration',
             properties=dict(AutoWrapText=False, WrapTextAt=760.0))
        graph_patch('ClearNarration', 'Collapsed')
        graph_patch('HandleNarration', 'HitTestInvisible')
        compiled = call('blueprint_compile', path=HUD, save=True)
        assert compiled['error_count'] == compiled['warning_count'] == 0 and compiled['saved'] and not compiled['dirty'], compiled
        Path('Saved/UIShots/narration_repair.json').write_text(json.dumps(dict(compile=compiled,
            graphs={n: call('blueprint_inspect_graph', path=HUD, graph_name=n) for n in ('ClearNarration', 'HandleNarration')}), indent=2))
        print('Narration backplate and tool ownership saved; runtime visual proof pending')
    finally:
        hc.release(OWNER, TOKEN)


if __name__ == '__main__':
    main()
