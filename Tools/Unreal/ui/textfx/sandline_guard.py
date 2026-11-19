"""WBP_SandLine null guard (coordinator, 2026-11-18 02:10): about 2,600 "Accessed None ... GetEffectMaterial" errors in
Step and Play (run_20261118_0043 DR, DR2b, DR2d, DRP: about 380 each). A RetainerBox has no effect material until its
Slate widget exists, and WBP_L2Journey's Refresh plays its title before the card is added to the viewport (and the
card is collapsed or removed while driving), so Play and Step wrote parameters on None, and Step's timer kept firing.
Now:
  Play   sets bPlayed first and writes the material only when GetEffectMaterial is valid
  Step   with no material yet, it stops its own timer and leaves T alone, so the form plays in full later
  Event Construct (the retainer has just been built): a line that was played restarts Step
In place, idempotent, compile and save in one lease:  python Tools/Unreal/ui/textfx/sandline_guard.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, ok, save  # noqa: E402

P = '/Game/FoA/UI/Widgets/Common/WBP_SandLine'
KSL, RB, TB = '/Script/Engine.KismetSystemLibrary', '/Script/UMG.RetainerBox', '/Script/UMG.TextBlock'
DT = 0.0167


def has_mid(b):
    return b.fn(f'{KSL}:IsValid', Object=b.fn(f'{RB}:GetEffectMaterial', self=b.get('Ret_Line')))


def build():
    if 'bPlayed' not in {v['name'] for v in hc.call('blueprint_get_info', {'path': P})['data'].get('variables', [])}:
        ok(hc.call('blueprint_add_variable', {'path': P, 'variable_name': 'bPlayed', 'variable_type': 'bool',
                                               'default_value': 'false', 'category': 'Sand line'}), 'var')
        compile_bp(P, widget=True)

    nodes, edges = graph(P, 'Step')
    if not any(n['title'].startswith('IsValid') for n in nodes):
        e = next(n['node_id'] for n in nodes if n['title'] == 'Step')
        first = next(x['to_node'] for x in edges if x['from_node'] == e and x['from_pin'] == 'then')
        b = B(P, 'Step')
        b.refs.update({e, first})
        br = b.node('branch', {'Condition': has_mid(b)})
        b.ops.append(dict(op='disconnect', node_id=e, pin_name='then'))
        b.chain(e, br, first)
        b.chain((br, 'else'), b.fn(f'{KSL}:K2_ClearTimer', FunctionName='Step'))
        b.run()

    nodes, edges = graph(P, 'Play')
    if not any(n['title'].startswith('IsValid') for n in nodes):
        by = {n['node_id']: n for n in nodes}
        e = next(n['node_id'] for n in nodes if n['title'] == 'Play')
        first = next(x['to_node'] for x in edges if x['from_node'] == e and x['from_pin'] == 'then')
        scale = next(x['to_node'] for x in edges if x['from_pin'] == 'then' and by[x['from_node']]['title'].startswith('Set bLeaving'))
        before = next(x['from_node'] for x in edges if x['to_node'] == scale and x['to_pin'] == 'execute')
        vis = next(n['node_id'] for n in nodes if n['title'].startswith('SetVisibility'))
        b = B(P, 'Play')
        b.refs.update({e, first, scale, before, vis})
        played = b.set('bPlayed', True)
        br = b.node('branch', {'Condition': has_mid(b)})
        b.ops += [dict(op='disconnect', node_id=e, pin_name='then'), dict(op='disconnect', node_id=before, pin_name='then')]
        b.chain(e, played, first)
        b.chain(before, br, scale)
        b.link(br, 'else', vis, 'execute')
        b.run()

    nodes, edges = graph(P, 'EventGraph')
    cons = [n['node_id'] for n in nodes if n['title'].startswith('Event Construct')]
    if not any(x['from_node'] in cons and x['from_pin'] == 'then' for x in edges):
        b = B(P, 'EventGraph')
        b.ops.append({'op': 'add_event', 'ref': 'cons', 'event_name': 'Construct', 'x': 0, 'y': 300})
        b.refs.add('cons')
        br = b.node('branch', {'Condition': b.get('bPlayed')})
        b.chain('cons', br, b.fn(f'{KSL}:K2_SetTimer', FunctionName='Step', Time=DT, bLooping=True))
        b.run()
    compile_bp(P, widget=True)
    print('saved', save(P))
    nodes, edges = graph(P, 'EventGraph')
    cons = [n['node_id'] for n in nodes if n['title'].startswith('Event Construct')]
    assert len(cons) == 1 and any(x['from_node'] == cons[0] and x['from_pin'] == 'then' for x in edges), 'Construct not wired'


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[P])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        build()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
