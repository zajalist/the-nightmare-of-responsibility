"""Door-tool lane: the hand reaches from screw to screw instead of popping. BP_Door.RefreshDoorTool set ToolContact (the
point the screwdriver tip and the hand follow) straight onto the next screw; it now eases there:
NewLocation = VInterpTo(ToolContact's current place in the door's frame, the screw, 1/30 s, SPEED).
RefreshDoorTool runs on every StepDoorTool timer tick (30/s, game time), so the step is that tick, not the frame's delta
(world delta snapped the reach in one call whenever a frame took 0.1 s). SPEED 6: 87% of the reach in 0.3 s, 97% in
0.5 s. At rest it is exact. Idempotent (built once; SPEED=<n> on a rerun only resets the speed). Compiled 0/0, saved.
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/contact_ease.py [SPEED=6]"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect, K, SC  # noqa: E402

DOOR = '/Game/FoA/Gameplay/BP_Door'
G = 'RefreshDoorTool'
args = dict(a.split('=', 1) for a in sys.argv[1:])
SPEED = float(args.get('SPEED', 6))
STEP = 1 / 30  # StepDoorTool's timer period


def main():
    nodes, edges = inspect(DOOR, G)
    by = {n['node_id']: n for n in nodes}
    moves = [n['node_id'] for n in nodes if 'Relative Location' in n['title'] or 'RelativeLocation' in n['title']
             if any(e['to_node'] == n['node_id'] and e['to_pin'] == 'self' and by[e['from_node']]['title'] == 'Get ToolContact'
                    for e in edges)]
    assert len(moves) == 1, [(n['title']) for n in nodes if 'Location' in n['title']]
    move = moves[0]
    src = next(e for e in edges if e['to_node'] == move and e['to_pin'] == 'NewLocation')
    if by[src['from_node']]['title'].startswith('VInterp'):
        ease = src['from_node']
        ops = [dict(op='set_pin', node_id=ease, pin_name='InterpSpeed', value=str(SPEED))]
        dt = [e['from_node'] for e in edges if e['to_node'] == ease and e['to_pin'] == 'DeltaTime']
        if dt:  # first build fed the frame's delta: drop it for the fixed timer step
            ops = [dict(op='remove', node_ids=dt)] + ops
        ops.append(dict(op='set_pin', node_id=ease, pin_name='DeltaTime', value='%.6f' % STEP))
        r = call('blueprint_graph_batch', dict(path=DOOR, graph_name=G, compile=True, save=True, ops=ops))
        print('ease reset: speed', SPEED, 'step', STEP, r.get('ok'), (r.get('data') or {}).get('compile'), r.get('error'))
        return
    contact = next(e for e in edges if e['to_node'] == move and e['to_pin'] == 'self')
    b = Batch(DOOR, G)
    b.cut(src['from_node'], src['from_pin'], move, 'NewLocation')
    x, y = 1200, 1400
    b.fn('here', SC + 'K2_GetComponentLocation', x, y); b.link(contact['from_node'], contact['from_pin'], 'here', 'self')
    b.fn('frame', '/Script/Engine.Actor:GetTransform', x, y + 150)
    b.fn('local', K + 'InverseTransformLocation', x + 300, y); b.link('frame', 'ReturnValue', 'local', 'T'); b.link('here', 'ReturnValue', 'local', 'Location')
    b.fn('ease', K + 'VInterpTo', x + 600, y, InterpSpeed=SPEED, DeltaTime='%.6f' % STEP)
    b.link('local', 'ReturnValue', 'ease', 'Current'); b.link(src['from_node'], src['from_pin'], 'ease', 'Target')
    b.link('ease', 'ReturnValue', move, 'NewLocation')
    b.comment('Reach the next screw', ['here', 'frame', 'local', 'ease'])
    d = b.run()
    print('built, speed', SPEED, (d or {}).get('refs'))


if __name__ == '__main__':
    assert not call('editor_get_state', {})['data']['pie_running'], 'PIE is running: wait'
    main()
