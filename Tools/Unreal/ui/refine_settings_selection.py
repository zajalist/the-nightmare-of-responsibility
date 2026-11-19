"""Native in-place Settings current-page cue, using the buttons' existing rest-opacity state."""
import json
from pathlib import Path
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc

PATH = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
BUTTON = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
TABS = ('Btn_TabGraphics', 'Btn_TabAudio', 'Btn_TabControls', 'Btn_TabAccess')
OWNER = 'ui_settings_selection'
TOKEN = None


def call(command, **params):
    reply = hc.call(command, params, owner=OWNER, lease=TOKEN)
    assert reply.get('ok'), reply
    data = reply.get('data', {})
    assert data.get('ok', True) and not data.get('failed') and not data.get('rejected_properties'), data
    return data


def link(a, b, output='then', input='execute'):
    return dict(op='connect', from_node=a, from_pin=output, to_node=b, to_pin=input)


def main():
    global TOKEN
    assert not call('editor_get_state')['pie_running'], 'PIE must be stopped'
    TOKEN = hc.lease_acquire(OWNER, ['asset:' + PATH], ttl_s=60, wait_s=10)
    try:
        graph = call('blueprint_inspect_graph', path=PATH, graph_name='ShowPage')
        nodes, edges = graph['nodes'], graph['edges']
        if not any(n['title'] == 'Set TextAlphaRest' for n in nodes):
            entry = next(n['node_id'] for n in nodes if n['title'] == 'ShowPage')
            tail = next(n['node_id'] for n in nodes if n['title'] == 'SetActiveWidgetIndex')
            assert not any(e['from_node'] == tail and e['from_pin'] == 'then' for e in edges)
            ops, refs = [], []
            for index, name in enumerate(TABS):
                x = 620 + index * 1080
                button, equal, alpha, store, push = [f'{n}{index}' for n in ('button', 'equal', 'alpha', 'store', 'push')]
                ops += [dict(op='add_node', ref=button, node_type='variable_get', variable_name=name, x=x, y=220),
                        dict(op='add_node', ref=equal, node_type='call_function', function_name='/Script/Engine.KismetMathLibrary:EqualEqual_IntInt', x=x, y=420),
                        dict(op='set_pin', node_id=equal, pin_name='B', value=str(index)),
                        dict(op='add_node', ref=alpha, node_type='call_function', function_name='/Script/Engine.KismetMathLibrary:SelectFloat', x=x+250, y=420),
                        dict(op='set_pin', node_id=alpha, pin_name='A', value='1.0'),
                        dict(op='set_pin', node_id=alpha, pin_name='B', value='0.62'),
                        dict(op='add_node', ref=store, node_type='variable_set', variable_name='TextAlphaRest', class_path=BUTTON, x=x+500, y=0),
                        dict(op='add_node', ref=push, node_type='call_function', function_name=BUTTON+':PushState', x=x+780, y=0),
                        link(entry, equal, 'Index', 'A'), link(equal, alpha, 'ReturnValue', 'bPickA'),
                        link(alpha, store, 'ReturnValue', 'TextAlphaRest'), link(button, store, name, 'self'),
                        link(button, push, name, 'self'), link(tail, store), link(store, push)]
                refs += [button, equal, alpha, store, push]
                tail = push
            ops += [dict(op='comment', title='Current settings page', node_ids=refs, color=[.3, .22, .1]), dict(op='fit_comments', title_only=True)]
            call('blueprint_graph_batch', path=PATH, graph_name='ShowPage', ops=ops)
        for name in TABS + ('Btn_Back',):
            call('ui_set_widget_properties', widget_blueprint_path=PATH, widget_name=name,
                 properties=dict(bPlainLabel=True, LabelSize=32.0))
        compiled = call('blueprint_compile', path=PATH, save=True)
        assert compiled['error_count'] == compiled['warning_count'] == 0 and compiled['saved'] and not compiled['dirty'], compiled
        Path('Saved/UIShots/settings_selection_repair.json').write_text(json.dumps(dict(compile=compiled,
            graph=call('blueprint_inspect_graph', path=PATH, graph_name='ShowPage')), indent=2))
        print('Settings selected-page cue saved; runtime proof pending')
    finally:
        hc.release(OWNER, TOKEN)


if __name__ == '__main__':
    main()
