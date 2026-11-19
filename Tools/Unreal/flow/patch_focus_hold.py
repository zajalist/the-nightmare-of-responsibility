"""Focus that holds (story lane takes it over from anim, 2026-11-10). BPC_Interactor's focus flickered on low and
bed-adjacent targets: the boot under the bed's edge and the bed itself at the T7 hook dropped to None or to a neighbour
between 0.1 s scans. The interactor's Interact then had no Target and a real E did nothing. QA's B1/B2 stalled there.
Two edits, Hayba, idempotent:
  FindBest  stickiness: the actor already focused gets STICKY (4) off its cost, so a neighbour must be clearly better
            (angle in degrees + distance/Reach*5) to steal the focus; small camera motion no longer swaps targets.
  Scan      a short hold: if this scan finds nothing but the current Target is still valid, was found less than
            HOLD (0.35 s) ago, is still within Reach of the pawn (distance to its bounds centre minus the bounds' half
            diagonal) and is in front of the camera, keep it (no SetFocus(None)). Walking out of reach or turning away
            clears it on the next scan; a miss longer than HOLD clears it as before.
  python Tools/Unreal/flow/patch_focus_hold.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

ITR = '/Game/FoA/Gameplay/BPC_Interactor'
ITR_C = ITR + '.BPC_Interactor_C'
K, KS, GS = '/Script/Engine.KismetMathLibrary:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.GameplayStatics:'
STICKY, HOLD = 4.0, 0.35
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def sticky():
    ns, es = inspect(ITR, 'FindBest')
    if any(n['title'] == 'Get Target' for n in ns):
        return 'kept'
    add = find(ns, 'float + float')          # angle + distance cost
    less = find(ns, 'float < float')         # cost < BestCost
    setc = find(ns, 'Set BestCost')
    # A direct-ray preference may already wrap the base angle/distance score.
    scored = next(e for e in es if e['to_node']==setc and e['to_pin']=='BestCost')
    brk = find(ns, 'BreakHitResult')
    b = Batch(ITR, 'FindBest')
    b.get('cur', 'Target', 1500, 900)
    b.fn('same', K + 'EqualEqual_ObjectObject', 1750, 900)
    b.link(brk, 'HitActor', 'same', 'A')
    b.link('cur', 'Target', 'same', 'B')
    b.fn('bonus', K + 'SelectFloat', 2000, 900, A=STICKY, B=0.0)
    b.link('same', 'ReturnValue', 'bonus', 'bPickA')
    b.fn('cost', K + 'Subtract_DoubleDouble', 2250, 800)
    b.link(scored['from_node'], scored['from_pin'], 'cost', 'A')
    b.link('bonus', 'ReturnValue', 'cost', 'B')
    b.link('cost', 'ReturnValue', less, 'A')
    b.link('cost', 'ReturnValue', setc, 'BestCost')
    b.comment('The focused one is sticky', ['cur', 'same', 'bonus', 'cost'])
    b.run()
    return 'the current target costs %.0f less' % STICKY


def hold():
    ns, es = inspect(ITR, 'Scan')
    if any(n['title'] == 'Set FocusLastSeen' for n in ns):
        return guard_hold(ns, es)
    e = find(ns, 'Scan')
    best = find(ns, 'FindBest')
    setf = find(ns, 'SetFocus')
    ref = find(ns, 'Refresh')
    b = Batch(ITR, 'Scan')
    b.fn('found', KS + 'IsValid', 300, 300)
    b.link(best, 'Best', 'found', 'Object')
    b.node('anything', 'branch', 300, 0)
    b.link('found', 'ReturnValue', 'anything', 'Condition')
    b.fn('now', GS + 'GetTimeSeconds', 550, 300)
    b.set('seen', 'FocusLastSeen', 550, -150)
    b.link('now', 'ReturnValue', 'seen', 'FocusLastSeen')
    b.get('cur', 'Target', 550, 500)
    b.fn('curok', KS + 'IsValid', 800, 500)
    b.link('cur', 'Target', 'curok', 'Object')
    b.get('last', 'FocusLastSeen', 550, 650)
    b.fn('age', K + 'Subtract_DoubleDouble', 800, 650)
    b.link('now', 'ReturnValue', 'age', 'A')
    b.link('last', 'FocusLastSeen', 'age', 'B')
    b.fn('fresh', K + 'Less_DoubleDouble', 1050, 650, B=HOLD)
    b.link('age', 'ReturnValue', 'fresh', 'A')
    # never hold a target he has walked away from or turned from: still within Reach of its bounds (sphere), in front
    b.fn('bounds', '/Script/Engine.Actor:GetActorBounds', 800, 850, bOnlyCollidingComponents='true')  # the billboard's 128 cm box kept every target 'in reach'
    b.link('cur', 'Target', 'bounds', 'self')
    b.fn('owner', '/Script/Engine.ActorComponent:GetOwner', 550, 1000)
    b.fn('pawnat', '/Script/Engine.Actor:K2_GetActorLocation', 800, 1000)
    b.link('owner', 'ReturnValue', 'pawnat', 'self')
    b.fn('away', K + 'Vector_Distance', 1050, 900)
    b.link('pawnat', 'ReturnValue', 'away', 'V1')
    b.link('bounds', 'Origin', 'away', 'V2')
    b.fn('size', K + 'VSize', 1050, 1050)
    b.link('bounds', 'BoxExtent', 'size', 'A')
    b.fn('gap', K + 'Subtract_DoubleDouble', 1300, 950)
    b.link('away', 'ReturnValue', 'gap', 'A')
    b.link('size', 'ReturnValue', 'gap', 'B')
    b.get('reach', 'Reach', 1300, 1100)
    b.fn('inreach', K + 'LessEqual_DoubleDouble', 1550, 950)
    b.link('gap', 'ReturnValue', 'inreach', 'A')
    b.link('reach', 'Reach', 'inreach', 'B')
    b.fn('cam', GS + 'GetPlayerCameraManager', 800, 1250, PlayerIndex=0)
    b.fn('camat', '/Script/Engine.PlayerCameraManager:GetCameraLocation', 1050, 1250)
    b.link('cam', 'ReturnValue', 'camat', 'self')
    b.fn('camrot', '/Script/Engine.PlayerCameraManager:GetCameraRotation', 1050, 1400)
    b.link('cam', 'ReturnValue', 'camrot', 'self')
    b.fn('fwd', K + 'GetForwardVector', 1300, 1400)
    b.link('camrot', 'ReturnValue', 'fwd', 'InRot')
    b.fn('toward', K + 'Subtract_VectorVector', 1300, 1250)
    b.link('bounds', 'Origin', 'toward', 'A')
    b.link('camat', 'ReturnValue', 'toward', 'B')
    b.fn('dot', K + 'Dot_VectorVector', 1550, 1300)
    b.link('toward', 'ReturnValue', 'dot', 'A')
    b.link('fwd', 'ReturnValue', 'dot', 'B')
    b.fn('ahead', K + 'Greater_DoubleDouble', 1800, 1300, B=0.0)
    b.link('dot', 'ReturnValue', 'ahead', 'A')
    b.fn('k1', K + 'BooleanAND', 1300, 550)
    b.link('curok', 'ReturnValue', 'k1', 'A')
    b.link('fresh', 'ReturnValue', 'k1', 'B')
    b.fn('k2', K + 'BooleanAND', 1800, 1000)
    b.link('inreach', 'ReturnValue', 'k2', 'A')
    b.link('ahead', 'ReturnValue', 'k2', 'B')
    b.fn('keep', K + 'BooleanAND', 2050, 700)
    b.link('k1', 'ReturnValue', 'keep', 'A')
    b.link('k2', 'ReturnValue', 'keep', 'B')
    b.node('holdit', 'branch', 1300, 150)
    b.link('keep', 'ReturnValue', 'holdit', 'Condition')
    b.node('validtarget', 'branch', 800, 150)
    b.link('curok', 'ReturnValue', 'validtarget', 'Condition')
    b.cut(best, 'then', setf, 'execute')
    b.link(best, 'then', 'anything', 'execute')
    b.link('anything', 'then', 'seen', 'execute')
    b.link('seen', 'then', setf, 'execute')
    # Blueprint pure AND evaluates bounds even for None; guard the geometry with execution flow.
    b.link('anything', 'else', 'validtarget', 'execute')
    b.link('validtarget', 'then', 'holdit', 'execute')
    b.link('validtarget', 'else', setf, 'execute')
    b.link('holdit', 'then', ref, 'execute')   # keep the current focus this scan
    b.link('holdit', 'else', setf, 'execute')  # a real miss: focus clears as before
    b.comment('A short miss keeps the focus', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'a miss under %.2f s keeps the target' % HOLD


def guard_hold(ns, es):
    """Upgrade an existing hold graph without rebuilding its focus or geometry nodes."""
    def target(source, pin):
        hits = [e['to_node'] for e in es if e['from_node'] == source and e['from_pin'] == pin
                and e['to_pin'] == 'execute']
        assert len(hits) == 1, (source, pin, hits)
        return hits[0]

    anything = target(find(ns, 'FindBest'), 'then')
    holdit = target(anything, 'else')
    valid = [n['node_id'] for n in ns if n['title'].replace(' ', '') == 'IsValid'
             and any(e['to_node'] == n['node_id'] and e['to_pin'] == 'Object'
                     and e['from_pin'] == 'Target' for e in es)]
    assert len(valid) == 1, ('Target validity node', valid)
    if any(e['from_node'] == valid[0] and e['to_node'] == holdit and e['to_pin'] == 'Condition' for e in es):
        return 'kept with target guard'
    setf = find(ns, 'SetFocus')
    b = Batch(ITR, 'Scan')
    b.node('validtarget', 'branch', 800, 150)
    b.link(valid[0], 'ReturnValue', 'validtarget', 'Condition')
    b.cut(anything, 'else', holdit, 'execute')
    b.link(anything, 'else', 'validtarget', 'execute')
    b.link('validtarget', 'then', holdit, 'execute')
    b.link('validtarget', 'else', setf, 'execute')
    b.comment('Validate held focus', ['validtarget'])
    b.run()
    return 'target validity guards held-focus geometry'


def colliding():
    ns, es = inspect(ITR, 'Scan')
    node = find(ns, 'Get Actor Bounds') if any(n['title'] == 'Get Actor Bounds' for n in ns) else find(ns, 'GetActorBounds')
    b = Batch(ITR, 'Scan')
    b.pin(node, 'bOnlyCollidingComponents', 'true')
    b.run()
    return 'colliding bounds only'


if __name__ == '__main__':
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + ITR], ttl_s=240, wait_s=240)
    try:
        call('blueprint_add_variable', path=ITR, variable_name='FocusLastSeen', variable_type='float', category='Focus',
             update_existing=True)
        print('focus', dict(FindBest=sticky(), Scan=hold(), Bounds=colliding()))
    finally:
        h.release('story', token)
