"""Item inspect: drag and stick rotation did nothing (user, 2026-11-10). The four InputAxisKey events (Mouse X/Y,
Gamepad Right Thumbstick X/Y) fed AxisValue into their Set nodes but their exec 'then' was never wired (the first input
run died on the link, the rerun skipped the nodes it found), so AxisMouse*/AxisStick* stayed 0. Arrows and D-pad worked
(Rotate is wired). This wires each axis event's then -> its Set node, compiles and saves.
  python Tools/Unreal/ui/item_inspect_axis_fix.py        (quiet slot, PIE off; idempotent)"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, save  # noqa: E402

BP = '/Game/FoA/UI/Game/BP_ItemInspect'
assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
tok = editor_lock.acquire('ui', wait_s=120, ttl=90, areas=[BP])
try:
    ns, es = graph(BP, 'EventGraph')
    T = {n['node_id']: n['title'].replace('\n', ' ') for n in ns}
    b = B(BP, 'EventGraph')
    for e in es:
        if e['from_pin'] == 'AxisValue':
            src, dst = e['from_node'], e['to_node']
            if not any(x['from_node'] == src and x['to_node'] == dst and x['to_pin'] == 'execute' for x in es):
                b.link(src, 'then', dst, 'execute')
                print('wire', T[src], '->', T[dst])
    if b.ops:
        b.run()
    compile_bp(BP)
    ns, es = graph(BP, 'EventGraph')
    axis = [e for e in es if e['from_pin'] == 'AxisValue']
    wired = [e for e in axis if any(x['from_node'] == e['from_node'] and x['to_node'] == e['to_node'] and x['to_pin'] == 'execute' for x in es)]
    assert len(axis) == 4 and len(wired) == 4, (len(axis), len(wired))
    print('axis events wired', len(wired), '| BP_ItemInspect save', save(BP))
finally:
    if tok:
        hc.release('ui', tok)
        editor_lock.forget('ui', tok)
