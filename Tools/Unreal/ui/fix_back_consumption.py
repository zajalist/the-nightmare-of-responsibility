"""Menus consume Back once instead of leaking it into the viewport input pipeline."""
from fix_intro_responsiveness import *

KIL = '/Script/Engine.KismetInputLibrary:'
UWBL = '/Script/UMG.WidgetBlueprintLibrary:'


def fix(path, intent):
    # Native Hayba follows the editor Override implementation and is idempotent.
    override = call('blueprint_add_event', path=path, event_name='OnKeyDown')
    g = graph(path, 'OnKeyDown')
    comparisons = [n for n in g['nodes'] if n['title'] == 'Equal (Key)']
    if any(n['title'] == 'Select' for n in g['nodes']):
        # Complete/read-verify an existing native graph, including a staged batch.
        entry, ret = override['entry_node_id'], override['result_node_id']
        reply, gate, back = node(g, 'Select'), node(g, 'Branch'), node(g, intent)
        desired = [
            link(node(g, 'Unhandled'), reply, 'ReturnValue', 'Option 0'),
            link(node(g, 'Handled'), reply, 'ReturnValue', 'Option 1'),
            link(reply, ret, 'ReturnValue', 'ReturnValue'),
            link(entry, gate), link(gate, back),
            link(node(g, 'Get Host'), back, 'Host', 'self'),
            link(back, ret), link(gate, ret, 'else')]
        edges = {(e['from_node'], e['from_pin'], e['to_node'], e['to_pin']) for e in g['edges']}
        ops = [op for op in desired if
               (op['from_node'], op['from_pin'], op['to_node'], op['to_pin']) not in edges]
        if any(op['from_node'] == entry for op in ops):
            ops.insert(0, dict(op='disconnect', node_id=entry, pin_name='then'))
        if not any(not n['pins'] for n in g['nodes']):
            ops.append(dict(op='comment', title='Consume Escape and controller Back',
                            node_ids=[n['node_id'] for n in g['nodes']]))
        if ops:
            patch(path, 'OnKeyDown', ops + [dict(op='fit_comments')])
        return
    if any(p.get('default_value') == 'Gamepad_FaceButton_Right'
           for n in comparisons for p in n['pins']):
        return
    if comparisons:  # Main menu already consumes Escape; preserve its two result nodes.
        esc = comparisons[0]['node_id']
        gate = node(g, 'Branch')
        key = node(g, 'GetKey')
        patch(path, 'OnKeyDown', [
            add('pad', function_name=KIL+'EqualEqual_KeyKey', x=350, y=380),
            add('either', function_name=KML+'BooleanOR', x=580, y=320),
            link(key, 'pad', 'ReturnValue', 'A'),
            dict(op='set_pin', node_id='pad', pin_name='B', value='Gamepad_FaceButton_Right'),
            dict(op='disconnect', node_id=gate, pin_name='Condition'),
            link(esc, 'either', 'ReturnValue', 'A'), link('pad', 'either', 'ReturnValue', 'B'),
            link('either', gate, 'ReturnValue', 'Condition'), dict(op='fit_comments')])
        return
    assert len([n for n in g['nodes'] if n['title'] != 'Comment']) == 2, g
    entry, ret = override['entry_node_id'], override['result_node_id']
    ops = [
        add('key', function_name=KIL+'GetKey', x=220, y=240),
        add('esc', function_name=KIL+'EqualEqual_KeyKey', x=460, y=240),
        add('pad', function_name=KIL+'EqualEqual_KeyKey', x=460, y=420),
        add('either', function_name=KML+'BooleanOR', x=700, y=240),
        add('gate', 'branch', x=920, y=0),
        add('host', 'variable_get', variable_name='Host', x=920, y=-200),
        add('back', function_name=FC+intent, x=1160, y=-100),
        add('yes', function_name=UWBL+'Handled', x=1160, y=360),
        add('no', function_name=UWBL+'Unhandled', x=1160, y=500),
        add('reply', 'select', x=1460, y=300),
        link(entry, 'key', 'InKeyEvent', 'Input'),
        link('key', 'esc', 'ReturnValue', 'A'), link('key', 'pad', 'ReturnValue', 'A'),
        dict(op='set_pin', node_id='esc', pin_name='B', value='Escape'),
        dict(op='set_pin', node_id='pad', pin_name='B', value='Gamepad_FaceButton_Right'),
        link('esc', 'either', 'ReturnValue', 'A'), link('pad', 'either', 'ReturnValue', 'B'),
        link('either', 'gate', 'ReturnValue', 'Condition'),
        link('either', 'reply', 'ReturnValue', 'Index'),
        link('no', 'reply', 'ReturnValue', 'Option 0'), link('yes', 'reply', 'ReturnValue', 'Option 1'),
        link('reply', ret, 'ReturnValue', 'ReturnValue'),
        dict(op='disconnect', node_id=entry, pin_name='then'),
        link(entry, 'gate'), link('gate', 'back'), link('host', 'back', 'Host', 'self'),
        link('back', ret), link('gate', ret, 'else'),
        dict(op='comment', title='Consume Escape and controller Back',
             node_ids=['key', 'esc', 'pad', 'either', 'gate', 'host', 'back', 'yes', 'no', 'reply']),
        dict(op='fit_comments')]
    patch(path, 'OnKeyDown', ops)


if __name__ == '__main__':
    os.environ['HAYBA_AGENT_ID'] = os.environ['FOA_AGENT'] = 'ui'
    assert not call('editor_get_state').get('pie_running'), 'User PIE is protected'
    editor_lock.acquire('ui', wait_s=60, ttl=90, areas=['UI'])
    try:
        for path, intent in [
            ('/Game/FoA/UI/Widgets/Common/WBP_ConfirmDialog', 'CloseOverlay'),
            ('/Game/FoA/UI/Widgets/Menus/WBP_Credits', 'CloseOverlay'),
            ('/Game/FoA/UI/Widgets/Menus/WBP_MainMenu', 'HandleBack')]:
            fix(path, intent)
    finally:
        editor_lock.release('ui')
