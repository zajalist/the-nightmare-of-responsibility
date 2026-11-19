"""BP_Door: the key row uses the twin-solved key grip (anim lane, 2026-11-10; the user: "none of the animations were
fixed for turning the key"). Hayba graph batches on BP_Door, after BP_FoAPlayer's grip runtime
(grip_runtime_graphs.py / grip_runtime_hooks.py) and the Teen key pose (bake_grips.py).
- KeyGripHand (transform, class default): the hand in the key mesh's frame (grip_bake.json 'Key' hand_in_object, its
  translation divided by the key's 0.682 scale, which ComposeTransforms applies) and KeyStand (vector): where the Body
  root stands in the key's frame (root_in_object, x/y; the key's frame is the world's).
- BeginDoorTool: after SetDoorToolPresentation has placed the player, when ToolMode is Key: stand at KeyWorld + KeyStand (x/y, his
  height kept, facing the door: yaw of the door's -X, i.e. the key's +X), then BeginGrip(ToolMesh, 'Key', KeyGripHand).
- FinishDoorTool, CancelDoorTool, RestoreDoorTool: EndGrip on the player first.
Idempotent (checks for its own nodes). Compile 0/0 and save per batch.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/door_key_grip_graphs.py"""
import json
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

D = '/Game/FoA/Gameplay/BP_Door'
PC = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
K = '/Script/Engine.KismetMathLibrary:'
ACT = '/Script/Engine.Actor:'
assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
g = json.load(open('P:/FoA/Saved/AnimShots/grip_bake.json'))['Key']
S = 0.6818181818181818  # the key mesh's scale on the door (ToolKeyTransform)
q, t = g['hand_in_object']['quat'], [c / S for c in g['hand_in_object']['loc']]
HAND = '(Rotation=(X=%r,Y=%r,Z=%r,W=%r),Translation=(X=%r,Y=%r,Z=%r),Scale3D=(X=%r,Y=%r,Z=%r))' % (*q, *t, 1 / S, 1 / S, 1 / S)
STAND = '(X=%r,Y=%r,Z=0.0)' % (g['root_in_object'][0], g['root_in_object'][1])


def begin_hook():
    nodes, edges = inspect(D, 'BeginDoorTool')
    show = find(nodes, 'SetDoorToolPresentation')
    if any(n['title'] == 'BeginGrip' for n in nodes):
        grip = find(nodes, 'BeginGrip')
        cast = next(x['from_node'] for x in edges if x['to_node'] == grip and x['to_pin'] == 'self')
        branch = next(x['from_node'] for x in edges if x['to_node'] == cast and x['to_pin'] == 'execute')
        incoming = next(x for x in edges if x['to_node'] == branch and x['to_pin'] == 'execute')
        if incoming['from_node'] == show:
            return print('BeginDoorTool: grip already follows placement')
        assert incoming['from_node'] == find(nodes, 'Set bToolActive'), incoming
        exits = [next(x for x in edges if x['from_node'] == n and x['from_pin'] == p)
                 for n, p in ((grip, 'then'), (branch, 'else'), (cast, 'CastFailed'))]
        assert len({(x['to_node'], x['to_pin']) for x in exits}) == 1, exits
        after = next(x for x in edges if x['from_node'] == show and x['from_pin'] == 'then')
        b = Batch(D, 'BeginDoorTool')
        for x in [incoming, after] + exits:
            b.cut(x['from_node'], x['from_pin'], x['to_node'], x['to_pin'])
        b.link(incoming['from_node'], incoming['from_pin'], exits[0]['to_node'], exits[0]['to_pin'])
        b.link(show, 'then', branch, 'execute')
        for x in exits:
            b.link(x['from_node'], x['from_pin'], after['to_node'], after['to_pin'])
        b.run()
        _, actual = inspect(D, 'BeginDoorTool')
        assert any(x['from_node'] == show and x['to_node'] == branch for x in actual)
        assert all(any(x['from_node'] == old['from_node'] and x['from_pin'] == old['from_pin']
                       and x['to_node'] == after['to_node'] for x in actual) for old in exits)
        return print('BeginDoorTool: moved existing grip after placement')
    sat = show
    nxt = next(x for x in edges if x['from_node'] == sat and x.get('from_pin') == 'then')
    b = Batch(D, 'BeginDoorTool')
    b.cut(sat, 'then', nxt['to_node'], nxt['to_pin'])
    b.get('m', 'ToolMode', 0, 900)
    b.fn('iskey', K + 'EqualEqual_NameName', 250, 900, B='Key'); b.link('m', 'ToolMode', 'iskey', 'A')
    b.node('br', 'branch', 450, 700); b.link('iskey', 'ReturnValue', 'br', 'Condition'); b.link(sat, 'then', 'br', 'execute')
    b.get('pl', 'ToolPlayer', 450, 1100)
    b.node('cast', 'cast', 700, 700, class_path=PC); b.link('pl', 'ToolPlayer', 'cast', 'Object'); b.link('br', 'then', 'cast', 'execute')
    b.get('km', 'ToolMesh', 700, 1300)
    b.fn('kw', '/Script/Engine.SceneComponent:K2_GetComponentLocation', 950, 1300); b.link('km', 'ToolMesh', 'kw', 'self')
    b.get('ks', 'KeyStand', 950, 1450)
    b.fn('spot', K + 'Add_VectorVector', 1200, 1350); b.link('kw', 'ReturnValue', 'spot', 'A'); b.link('ks', 'KeyStand', 'spot', 'B')
    b.fn('now', ACT + 'K2_GetActorLocation', 1200, 1550); b.link('cast', 'AsBP Fo APlayer', 'now', 'self')
    b.fn('bs', K + 'BreakVector', 1450, 1350); b.link('spot', 'ReturnValue', 'bs', 'InVec')
    b.fn('bn', K + 'BreakVector', 1450, 1550); b.link('now', 'ReturnValue', 'bn', 'InVec')
    b.fn('at', K + 'MakeVector', 1700, 1400); b.link('bs', 'X', 'at', 'X'); b.link('bs', 'Y', 'at', 'Y'); b.link('bn', 'Z', 'at', 'Z')
    b.fn('face', K + 'MakeRotator', 1700, 1600, Roll=0.0, Pitch=0.0, Yaw=0.0)  # the door's face looks down -X: he faces +X
    b.fn('move', ACT + 'K2_SetActorLocationAndRotation', 1950, 700, bSweep='false', bTeleport='true')
    b.link('cast', 'AsBP Fo APlayer', 'move', 'self'); b.link('at', 'ReturnValue', 'move', 'NewLocation')
    b.link('face', 'ReturnValue', 'move', 'NewRotation'); b.link('cast', 'then', 'move', 'execute')
    b.get('kh', 'KeyGripHand', 1950, 1100)
    b.fn('grip', PC + ':BeginGrip', 2250, 700, Pose='Key'); b.link('cast', 'AsBP Fo APlayer', 'grip', 'self')
    b.link('km', 'ToolMesh', 'grip', 'Anchor'); b.link('kh', 'KeyGripHand', 'grip', 'HandInAnchor'); b.link('move', 'then', 'grip', 'execute')
    b.link('grip', 'then', nxt['to_node'], nxt['to_pin']); b.link('br', 'else', nxt['to_node'], nxt['to_pin'])
    b.link('cast', 'CastFailed', nxt['to_node'], nxt['to_pin'])
    b.comment('Seat the key grip', ['m', 'iskey', 'br', 'pl', 'cast', 'km', 'kw', 'ks',
                                                                                          'spot', 'now', 'bs', 'bn', 'at', 'face', 'move', 'kh', 'grip'])
    b.run()


def end_hook(fn):
    nodes, edges = inspect(D, fn)
    if any(n['title'] == 'EndGrip' for n in nodes):
        return print(fn, 'already lets go')
    e = find(nodes, fn)
    nxt = next(x for x in edges if x['from_node'] == e and x.get('from_pin') == 'then')
    b = Batch(D, fn)
    b.cut(e, 'then', nxt['to_node'], nxt['to_pin'])
    b.get('pl', 'ToolPlayer', 0, -400)
    b.node('cast', 'cast', 250, -300, class_path=PC); b.link('pl', 'ToolPlayer', 'cast', 'Object'); b.link(e, 'then', 'cast', 'execute')
    b.fn('end', PC + ':EndGrip', 550, -300); b.link('cast', 'AsBP Fo APlayer', 'end', 'self'); b.link('cast', 'then', 'end', 'execute')
    b.link('end', 'then', nxt['to_node'], nxt['to_pin']); b.link('cast', 'CastFailed', nxt['to_node'], nxt['to_pin'])
    b.comment('Let go of any twin-solved grip', ['pl', 'cast', 'end'])
    b.run()


lease = h.lease_acquire('anim', ['asset:/Game/FoA/Gameplay/BP_Door'], ttl_s=120)
try:
    for name, kind, val in (('KeyGripHand', 'transform', HAND), ('KeyStand', 'vector', STAND)):
        r = h.call('blueprint_add_variable', dict(path=D, variable_name=name, variable_type=kind, instance_editable=False,
                                                  update_existing=True, category='Tool grip'), owner='anim')
        assert r.get('ok'), r
    begin_hook()
    for fn in ('FinishDoorTool', 'CancelDoorTool', 'RestoreDoorTool'):
        end_hook(fn)
    for k, v in (('KeyGripHand', HAND), ('KeyStand', STAND)):
        r = h.call('object_set_property', dict(path=D + '.Default__BP_Door_C', properties={k: v}), owner='anim')
        assert r.get('ok'), r
    r = h.call('blueprint_compile', dict(path=D), owner='anim')
    d = r.get('data', r)
    assert not d.get('error_count'), d
    r = h.call('asset_save', dict(asset_paths=[D], force=True), owner='anim')
    assert r.get('data', {}).get('verified'), r
finally:
    h.release('anim', lease)
print('DOOR_KEY_GRIP done', HAND, STAND)
