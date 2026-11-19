"""Door-tool lane: how the screwdriver sits in his hand at the lock plate, from BP_Door (BP_FoAPlayer's graphs are untouched).
- BeginDoorTool: before SetHeldTool, the player's ToolGripOffset (hand_r -> the screwdriver's grip frame, whose X is the
  tool's axis) becomes ROLL degrees about the tool's own axis from the measured offset. The screwdriver still points into
  the screw; the hand and wrist turn around it, so the forearm comes up from below instead of across the door.
- RefreshDoorTool: after SetToolHandRotation, for the screwdriver only, the right elbow's pole (ABP_FoAPlayer_MH
  ToolElbowTarget, world) is ToolHandTarget + POLE (door frame, cm): back, right and below the hand. The old pole sat
  30 back, 28 right and 5 below, which winged the elbow out at hand height.
Idempotent: built once; a rerun with ROLL=/POLE= only resets the two literals. Hayba batches, compiled 0/0, saved.
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/door_grip.py ROLL=-45 POLE=-25,20,-35"""
import math
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect, find, K, PLAYER_C, MH_C  # noqa: E402

DOOR = '/Game/FoA/Gameplay/BP_Door'
args = dict(a.split('=', 1) for a in sys.argv[1:])
ROLL = float(args.get('ROLL', -45))
POLE = args.get('POLE', '-25,20,-35')
# BP_FoAPlayer's ToolGripOffset default, measured 2026-11-18 (probe_doortool.py): the screwdriver grip in hand_r.
BASE_Q = (-0.326730, 0.185928, -0.634669, 0.675184)
BASE_T = (-2.121508, -6.681991, 0.220303)
BASE_S = 1.058824


def qmul(a, b):
    """Hamilton product a*b, (x, y, z, w)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def rotator(q):
    """FQuat::Rotator (pitch, yaw, roll), degrees."""
    x, y, z, w = q
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (z * x - w * y)))))
    yaw = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
    roll = math.degrees(math.atan2(-2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
    return pitch, yaw, roll


def quat(pitch, yaw, roll):
    """FRotator::Quaternion."""
    sp, cp = math.sin(math.radians(pitch) / 2), math.cos(math.radians(pitch) / 2)
    sy, cy = math.sin(math.radians(yaw) / 2), math.cos(math.radians(yaw) / 2)
    sr, cr = math.sin(math.radians(roll) / 2), math.cos(math.radians(roll) / 2)
    return (cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


def offset_literal(roll):
    # UE Compose(R, Base) applies R first (in the grip's own frame), then Base: quat Base.Q * R.Q; the translation stays.
    q = qmul(BASE_Q, quat(0, 0, roll))
    p, y, r = rotator(q)
    back = quat(p, y, r)
    assert min(sum((a - b) ** 2 for a, b in zip(back, q)), sum((a + b) ** 2 for a, b in zip(back, q))) < 1e-9, (q, back)
    # K2 pin literal for FTransform: translation | rotator (pitch, yaw, roll) | scale
    return '%.6f,%.6f,%.6f|%.6f,%.6f,%.6f|%.6f,%.6f,%.6f' % (*BASE_T, p, y, r, BASE_S, BASE_S, BASE_S)


def roll_in_begin():
    nodes, edges = inspect(DOOR, 'BeginDoorTool')
    by = {n['node_id']: n for n in nodes}
    have = [n['node_id'] for n in nodes if n['title'] == 'Set ToolGripOffset']
    if have:
        r = call('blueprint_graph_batch', dict(path=DOOR, graph_name='BeginDoorTool', compile=True, save=True,
                                               ops=[dict(op='set_pin', node_id=have[0], pin_name='ToolGripOffset', value=offset_literal(ROLL))]))
        print('roll reset to', ROLL, r.get('ok'), (r.get('data') or {}).get('compile'))
        return
    held = find(nodes, 'SetHeldTool')
    into = [e for e in edges if e['to_node'] == held and e['to_pin'] == 'execute']
    me = [e for e in edges if e['to_node'] == held and e['to_pin'] == 'self']
    assert len(into) == 1 and len(me) == 1 and by[into[0]['from_node']]['title'] == 'Cast To BP_FoAPlayer', (into, me)
    b = Batch(DOOR, 'BeginDoorTool')
    b.cut(into[0]['from_node'], into[0]['from_pin'], held, 'execute')
    b.set('grip', 'ToolGripOffset', 5250, -800, PLAYER_C)
    b.pin('grip', 'ToolGripOffset', offset_literal(ROLL))
    b.link(me[0]['from_node'], me[0]['from_pin'], 'grip', 'self')
    b.link(into[0]['from_node'], into[0]['from_pin'], 'grip', 'execute')
    b.link('grip', 'then', held, 'execute')
    b.comment('Roll the hand around the screwdriver', ['grip'])
    b.run()
    print('roll built', ROLL)


def pole_in_refresh():
    nodes, edges = inspect(DOOR, 'RefreshDoorTool')
    by = {n['node_id']: n for n in nodes}
    have = [n['node_id'] for n in nodes if n['title'] == 'Set ToolElbowTarget']
    if have:
        add = next(e['from_node'] for e in edges if e['to_node'] == have[0] and e['to_pin'] == 'ToolElbowTarget')
        rot = next(e['from_node'] for e in edges if e['to_node'] == add and e['to_pin'] == 'B')
        r = call('blueprint_graph_batch', dict(path=DOOR, graph_name='RefreshDoorTool', compile=True, save=True,
                                               ops=[dict(op='set_pin', node_id=rot, pin_name='Direction', value=POLE)]))
        print('pole reset to', POLE, r.get('ok'), (r.get('data') or {}).get('compile'))
        return
    turn = find(nodes, 'SetToolHandRotation')
    after = [e for e in edges if e['from_node'] == turn and e['from_pin'] == 'then']
    me = [e for e in edges if e['to_node'] == turn and e['to_pin'] == 'self']
    assert len(after) == 1 and len(me) == 1, (after, me)
    nxt = (after[0]['to_node'], after[0]['to_pin'])
    x, y = 5400, -600
    b = Batch(DOOR, 'RefreshDoorTool')
    b.cut(turn, 'then', *nxt)
    b.get('mode', 'ToolMode', x - 300, y + 200)
    b.fn('isdriver', K + 'EqualEqual_NameName', x - 50, y + 200, B='Screwdriver'); b.link('mode', 'ToolMode', 'isdriver', 'A')
    b.node('driver', 'branch', x, y); b.link('isdriver', 'ReturnValue', 'driver', 'Condition')
    b.get('body', 'Body', x, y + 300, PLAYER_C); b.link(me[0]['from_node'], me[0]['from_pin'], 'body', 'self')
    b.fn('anim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', x + 250, y + 300); b.link('body', 'Body', 'anim', 'self')
    b.node('mh', 'cast', x + 300, y, class_path=MH_C); b.link('anim', 'ReturnValue', 'mh', 'Object')
    b.get('hand', 'ToolHandTarget', x + 550, y + 300, MH_C); b.link('mh', 'AsABP Fo APlayer MH', 'hand', 'self')
    b.fn('frame', '/Script/Engine.Actor:GetTransform', x + 550, y + 450)
    b.fn('rot', K + 'TransformDirection', x + 800, y + 400, Direction=POLE); b.link('frame', 'ReturnValue', 'rot', 'T')
    b.fn('pole', K + 'Add_VectorVector', x + 1050, y + 300); b.link('hand', 'ToolHandTarget', 'pole', 'A'); b.link('rot', 'ReturnValue', 'pole', 'B')
    b.set('elbow', 'ToolElbowTarget', x + 1300, y, MH_C); b.link('mh', 'AsABP Fo APlayer MH', 'elbow', 'self'); b.link('pole', 'ReturnValue', 'elbow', 'ToolElbowTarget')
    b.link(turn, 'then', 'driver', 'execute')
    b.link('driver', 'then', 'mh', 'execute')
    b.link('mh', 'then', 'elbow', 'execute')
    b.link('elbow', 'then', *nxt)
    b.link('mh', 'CastFailed', *nxt)
    b.link('driver', 'else', *nxt)
    b.comment('Hang the elbow below the hand', ['mode', 'isdriver', 'driver', 'body', 'anim', 'mh', 'hand', 'frame', 'rot', 'pole', 'elbow'])
    b.run()
    print('pole built', POLE)


if __name__ == '__main__':
    assert not call('editor_get_state', {})['data']['pie_running'], 'PIE is running: wait'
    roll_in_begin()
    pole_in_refresh()
