"""Round 3 fix: KismetMaterialLibrary.GetScalarParameterValue is impure in 5.9, and an impure node wired only as data
is pruned (editor-rules). Put the Reduce Motion read on the exec path in WBP_DayRollover.StepRollover (before the
breath) and WBP_Phone.TypeStep (before the text). In place, idempotent:  python Tools/Unreal/ui/textfx/r3_exec_fix.py"""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal'); sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock, hayba_call as hc  # noqa: E401,E402
from hayba_batch import B, compile_bp, graph, save  # noqa: E402

FIX = (('/Game/FoA/UI/Game/WBP_DayRollover', 'StepRollover', 'SetRenderScale'),
       ('/Game/FoA/UI/Game/WBP_Phone', 'TypeStep', 'SetText'))


def onpath(path, g, before_title):
    nodes, edges = graph(path, g)
    get = next(n['node_id'] for n in nodes if n['title'].startswith('GetScalarParameterValue'))
    if any(x['to_node'] == get and x['to_pin'] == 'execute' for x in edges):
        return False
    users = {x['to_node'] for x in edges if x['from_node'] == get}
    # the exec node whose data needs the read: the first node titled before_title downstream of it
    by = {n['node_id']: n for n in nodes}
    tgt = None
    frontier = set(users)
    while frontier and not tgt:
        nxt = set()
        for nid in frontier:
            if by[nid]['title'].startswith(before_title) and any(p['name'] == 'execute' for p in by[nid]['pins']):
                tgt = nid
            nxt |= {x['to_node'] for x in edges if x['from_node'] == nid and x['to_pin'] != 'execute'}
        frontier = nxt
    prev = next(x['from_node'] for x in edges if x['to_node'] == tgt and x['to_pin'] == 'execute')
    pin = next(x['from_pin'] for x in edges if x['to_node'] == tgt and x['to_pin'] == 'execute')
    b = B(path, g)
    b.refs.update({get, tgt, prev})
    b.ops.append(dict(op='disconnect', node_id=tgt, pin_name='execute'))
    b.link(prev, pin, get, 'execute'); b.link(get, 'then', tgt, 'execute')
    b.run()
    return True


for path, g, title in FIX:
    tok = editor_lock.acquire('ui', wait_s=900, ttl=150, areas=[path])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        if onpath(path, g, title):
            compile_bp(path, widget=True); print(g, 'saved', save(path))
        else:
            print(g, 'already on the exec path')
    finally:
        if tok: hc.release('ui', tok); editor_lock.forget('ui', tok)
