"""BP_FoAFrontEnd.ReturnToTitle: "Accessed None trying to read property HUD" on RemoveFromParent in plan CR
(run_20261118_0254), where the credits shortcut reaches the title without gameplay ever creating the HUD. The HUD is
the function's only use of it; RemoveFromParent now runs only when IsValid(HUD). In place, idempotent, compile and
save in one lease:  python Tools/Unreal/ui/return_title_guard.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, save  # noqa: E402

FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
KSL = '/Script/Engine.KismetSystemLibrary'


def build():
    nodes, edges = graph(FE, 'ReturnToTitle')
    by = {n['node_id']: n for n in nodes}
    huds = [n['node_id'] for n in nodes if n['title'] == 'Get HUD']
    assert len(huds) == 1, huds  # the only HUD read in the function
    rem = next(x['to_node'] for x in edges if x['from_node'] == huds[0] and x['to_pin'] == 'self')
    prev = next(x['from_node'] for x in edges if x['to_node'] == rem and x['to_pin'] == 'execute')
    if by[prev]['title'].startswith('Branch'):
        print('already guarded')
        return
    nxt = next(x['to_node'] for x in edges if x['from_node'] == rem and x['from_pin'] == 'then')
    b = B(FE, 'ReturnToTitle')
    b.refs.update({prev, rem, nxt, huds[0]})
    br = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=(huds[0], 'HUD'))})
    b.ops.append(dict(op='disconnect', node_id=prev, pin_name='then'))
    b.chain(prev, br, rem)
    b.link(br, 'else', nxt, 'execute')
    b.run()
    compile_bp(FE)
    print('saved', save(FE))


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[FE])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        build()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
