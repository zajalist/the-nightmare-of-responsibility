"""WBP_SandLine timer handles (coordinator, 2026-11-18): every Play logged "Dismiss SetTimer passed a negative or zero
time" (13 per DRM log from the dream room's Line_Thought, 39 per log from WBP_L2Journey's Line_Title) and failed the QA
script-warnings check. The source is Play's K2_SetTimer('Dismiss', Hold) with Hold 0, which was the way it cleared an
old auto-dismiss. Now the auto-dismiss timer lives in a handle:
  Play      ClearAndInvalidate(DismissTimer); only when Hold > 0: DismissTimer = SetTimer('Dismiss', Hold)
  Dismiss   ClearAndInvalidate(DismissTimer) (was Clear Timer by Function Name)
  Destruct  ClearAndInvalidate(DismissTimer), Clear Timer 'Step'
In place, idempotent, compile and save in one lease:  python Tools/Unreal/ui/textfx/sandline_timer.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, ok, save  # noqa: E402

P = '/Game/FoA/UI/Widgets/Common/WBP_SandLine'
KSL, KML = '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetMathLibrary'


def timer_node(nodes, fn, title='Set Timer by Function Name'):
    return next(n['node_id'] for n in nodes if n['title'].replace('\n', ' ').startswith(title)
                and any(p['name'] == 'FunctionName' and p.get('default_value') == fn for p in n['pins']))


def clear(b):
    return b.fn(f'{KSL}:K2_ClearAndInvalidateTimerHandle', Handle=b.get('DismissTimer'))


def build():
    if 'DismissTimer' not in {v['name'] for v in hc.call('blueprint_get_info', {'path': P})['data'].get('variables', [])}:
        ok(hc.call('blueprint_add_variable', {'path': P, 'variable_name': 'DismissTimer', 'variable_type': 'struct:/Script/Engine.TimerHandle',
                                               'category': 'Sand line'}), 'var')
        compile_bp(P, widget=True)

    nodes, edges = graph(P, 'Play')
    if not any(n['title'].startswith('Set DismissTimer') for n in nodes):
        set_dismiss, set_step = timer_node(nodes, 'Dismiss'), timer_node(nodes, 'Step')
        before = next(x['from_node'] for x in edges if x['to_node'] == set_dismiss and x['to_pin'] == 'execute')
        e = next(n['node_id'] for n in nodes if n['title'] == 'Play')
        b = B(P, 'Play')
        b.refs.update({set_dismiss, set_step, before, e})
        cl = clear(b)
        held = b.node('branch', {'Condition': b.fn(f'{KML}:Greater_DoubleDouble', A=(e, 'Hold'), B=0.0)})
        keep = b.set('DismissTimer', (set_dismiss, 'ReturnValue'))
        b.ops += [dict(op='disconnect', node_id=before, pin_name='then'), dict(op='disconnect', node_id=set_dismiss, pin_name='then')]
        b.chain(before, cl, held, set_dismiss, keep, set_step)
        b.link(held, 'else', set_step, 'execute')
        b.run()

    nodes, edges = graph(P, 'Dismiss')
    old = [n['node_id'] for n in nodes if n['title'].replace('\n', ' ').startswith('Clear Timer by Function Name')
           and any(p['name'] == 'FunctionName' and p.get('default_value') == 'Dismiss' for p in n['pins'])]
    if old:
        prev = next(x['from_node'] for x in edges if x['to_node'] == old[0] and x['to_pin'] == 'execute')
        nxt = next(x['to_node'] for x in edges if x['from_node'] == old[0] and x['from_pin'] == 'then')
        b = B(P, 'Dismiss')
        b.refs.update({prev, nxt})
        b.ops.append(dict(op='remove', node_ids=old))
        b.chain(prev, clear(b), nxt)
        b.run()

    nodes, edges = graph(P, 'EventGraph')
    dest = [n['node_id'] for n in nodes if n['title'].startswith('Event Destruct')]
    if not any(x['from_node'] in dest and x['from_pin'] == 'then' for x in edges):
        b = B(P, 'EventGraph')
        b.ops.append({'op': 'add_event', 'ref': 'dest', 'event_name': 'Destruct', 'x': 0, 'y': 600})
        b.refs.add('dest')
        b.chain('dest', clear(b), b.fn(f'{KSL}:K2_ClearTimer', FunctionName='Step'))
        b.run()
    compile_bp(P, widget=True)
    print('saved', save(P))


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[P])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        build()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
