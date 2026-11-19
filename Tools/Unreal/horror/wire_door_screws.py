"""Audio lane (owner of BP_Door since 2026-11-09): each screw that comes out of the lock plate squeaks its last turn and
drops. In AdvanceDoorTool's screwdriver branch, after `Set ToolStepIndex` (index + 1), it plays S_Props_ScrewTurn and
S_Props_ScrewDrop at ToolContact, then continues to the "all four out?" branch. Idempotent: skipped if already wired.
One Hayba batch, compiled; saved only on a clean 0/0 compile, otherwise its nodes are removed, the cut link restored and
the Blueprint recompiled.
  $env:HAYBA_AGENT_ID='horror'; python Tools/Unreal/horror/wire_door_screws.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_Door'
G = 'AdvanceDoorTool'
MS = '/Game/FoA/Audio/MetaSounds/Props/'
GS = '/Script/Engine.GameplayStatics:'


def compile_clean():
    c = h.call('blueprint_compile', {'path': P}).get('data') or {}
    return (c.get('ok', True) and c.get('compiled', True) and not c.get('error_count', 0) and not c.get('warning_count', 0)), c


def main():
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE is running: wait'
    ok, c = compile_clean()
    assert ok, ('BP_Door does not compile clean before the edit; not touching it', c.get('errors'), c.get('warnings'))
    ns, es = inspect(P, G)
    by = {n['node_id']: n for n in ns}
    if any('ScrewDrop' in str(p.get('default_value')) for n in ns for p in n.get('pins', [])):
        print('already wired')
        return
    adds = {e['to_node'] for e in es if by.get(e['from_node'], {}).get('title') == 'int + int'
            and by.get(e['to_node'], {}).get('title') == 'Set ToolStepIndex'}
    assert len(adds) == 1, adds
    step = adds.pop()
    nxt = [e for e in es if e['from_node'] == step and e['from_pin'] == 'then']
    assert len(nxt) == 1, nxt
    nxt = nxt[0]
    x, y = by[step].get('x', 0), by[step].get('y', 0)
    b = Batch(P, G)
    b.cut(step, 'then', nxt['to_node'], nxt['to_pin'])
    b.get('contact', 'ToolContact', x + 150, y + 250)
    b.fn('where', '/Script/Engine.SceneComponent:K2_GetComponentLocation', x + 150, y + 400)
    b.link('contact', 'ToolContact', 'where', 'self')
    b.fn('turn', GS + 'PlaySoundAtLocation', x + 300, y - 200, Sound=MS + 'S_Props_ScrewTurn.S_Props_ScrewTurn', VolumeMultiplier=0.8)
    b.fn('drop', GS + 'PlaySoundAtLocation', x + 550, y - 200, Sound=MS + 'S_Props_ScrewDrop.S_Props_ScrewDrop', VolumeMultiplier=0.9)
    for r in ('turn', 'drop'):
        b.link('where', 'ReturnValue', r, 'Location')
    b.link(step, 'then', 'turn', 'execute')
    b.link('turn', 'then', 'drop', 'execute')
    b.link('drop', 'then', nxt['to_node'], nxt['to_pin'])
    b.comment('Screw out', ['contact', 'where', 'turn', 'drop'])
    r = h.call('blueprint_graph_batch', dict(path=P, graph_name=G, ops=b.ops, compile=True, save=False), timeout=120)
    d = r.get('data') or {}
    c = d.get('compile') or {}
    clean = r.get('ok') and not d.get('compile_error') and not c.get('error_count', 0) and not c.get('warning_count', 0) \
        and c.get('compiled', True)
    if clean:
        h.call('asset_save', {'asset_paths': [P]})
        print('BP_Door screws wired, compile 0/0, saved')
        return
    made = list((d.get('refs') or {}).values())
    if made:
        h.call('blueprint_remove_nodes', dict(path=P, graph_name=G, node_ids=made))
    h.call('blueprint_connect_nodes', dict(path=P, graph_name=G, from_node=step, from_pin='then', to_node=nxt['to_node'],
                                           to_pin=nxt['to_pin']))
    ok, c2 = compile_clean()
    print('FAILED, rolled back; recompile clean:', ok, r.get('error') or d.get('error'), c.get('errors'), c.get('warnings'))
    if ok:
        h.call('asset_save', {'asset_paths': [P]})
    sys.exit(1)


if __name__ == '__main__':
    lease = h.lease_acquire(h.agent_id(), ['asset:' + P], ttl_s=180, wait_s=60)
    try:
        main()
    finally:
        h.release(h.agent_id(), lease)
