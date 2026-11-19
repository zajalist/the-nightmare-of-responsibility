"""playercam lane (user bug 2026-11-18: "by turning fast I managed to glitch and see through my body", the screwdriver
inspect). Hayba graph batch on BP_FoAPlayer.UpdateFirstPersonVisibility:
- Interaction locked: the view yaw stays within LOCK_DEG of the animated torso. Before, the plain locked path allowed
  60 deg and the interaction-look path (InteractLook / EnvironmentContactMesh) had no yaw limit at all, so a fast mouse
  turn during a take held the view far over his shoulder, and the inspect that pauses the game opened there with the
  item inside his own arm. Cinematic-only keeps its 60 deg (scripted looks).
- Head hidden whenever the rendered camera is within NEAR_CM of the head bone, for any view target (a camera inside
  his head shows its inside); the door tool's 70 cm rule and the pawn's own view are unchanged.
Idempotent (skips when the LOCK_DEG clamp exists). Run inside an asset lease on BP_FoAPlayer:
  $env:HAYBA_AGENT_ID='playercam'; python Tools/Unreal/player/fp_lock_clamp.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
F = 'UpdateFirstPersonVisibility'
K = '/Script/Engine.KismetMathLibrary:'
LOCK_DEG, NEAR_CM = 30.0, 28.0


def pin(n, name):
    return str(next((p.get('default_value') for p in n['pins'] if p['name'] == name), ''))


def run():
    ns, es = inspect(P, F)
    by = {n['node_id']: n for n in ns}
    if any(n['title'] == 'Clamp (Float)' and pin(n, 'Min').startswith('-%d' % LOCK_DEG) for n in ns):
        print('LOCK_CLAMP kept')
        return
    src = lambda node, p: next((e['from_node'], e['from_pin']) for e in es if e['to_node'] == node and e['to_pin'] == p)  # noqa: E731
    # the locked path: torso yaw + Clamp(delta yaw, +-60) -> FPViewRotation
    c60 = next(n['node_id'] for n in ns if n['title'] == 'Clamp (Float)' and pin(n, 'Min').startswith('-60'))
    add = next(e['to_node'] for e in es if e['from_node'] == c60 and e['to_pin'] == 'B')
    torso = src(add, 'A')  # BreakRotator(torso).Yaw
    delta = src(c60, 'Value')
    # the interaction-look path: RInterpTo -> BreakRotator -> MakeRotator(clamped pitch, yaw)
    rin = next(n['node_id'] for n in ns if n['title'] == 'RInterpTo')
    brk = next(e['to_node'] for e in es if e['from_node'] == rin and by[e['to_node']]['title'] == 'BreakRotator')
    mk = next(e['to_node'] for e in es if e['from_node'] == brk and e['from_pin'] == 'Yaw' and by[e['to_node']]['title'] == 'MakeRotator')
    # the head rule: Distance(camera, head) and the door-only AND feeding the close OR
    dist = next(n['node_id'] for n in ns if n['title'] == 'Distance (Vector)')
    door = next(n['node_id'] for n in ns if n['title'] == 'AND Boolean' and any(
        e['from_node'] == n['node_id'] and by[e['to_node']]['title'] == 'OR Boolean' for e in es)
                and any(e['to_node'] == n['node_id'] and by[e['from_node']]['title'] == 'Contains' for e in es))
    close_or = next(e['to_node'] for e in es if e['from_node'] == door and e['from_pin'] == 'ReturnValue')

    b = Batch(P, F)
    b.get('lk', 'bInteractionLocked', 3000, 2050)
    b.fn('c30', K + 'FClamp', 3250, 1900, Min=-LOCK_DEG, Max=LOCK_DEG); b.link(delta[0], delta[1], 'c30', 'Value')
    b.fn('pick', K + 'SelectFloat', 3450, 1800); b.link('c30', 'ReturnValue', 'pick', 'A'); b.link(c60, 'ReturnValue', 'pick', 'B')
    b.link('lk', 'bInteractionLocked', 'pick', 'bPickA')
    b.cut(c60, 'ReturnValue', add, 'B'); b.link('pick', 'ReturnValue', add, 'B')
    b.fn('rel', K + 'Subtract_DoubleDouble', 3300, 2650); b.link(brk, 'Yaw', 'rel', 'A'); b.link(torso[0], torso[1], 'rel', 'B')
    b.fn('wrap', K + 'NormalizeAxis', 3500, 2650); b.link('rel', 'ReturnValue', 'wrap', 'Angle')
    b.fn('c30i', K + 'FClamp', 3700, 2650, Min=-LOCK_DEG, Max=LOCK_DEG); b.link('wrap', 'ReturnValue', 'c30i', 'Value')
    b.fn('back', K + 'Add_DoubleDouble', 3900, 2650); b.link(torso[0], torso[1], 'back', 'A'); b.link('c30i', 'ReturnValue', 'back', 'B')
    b.cut(brk, 'Yaw', mk, 'Yaw'); b.link('back', 'ReturnValue', mk, 'Yaw')
    b.comment('Locked view near torso', ['lk', 'c30', 'pick', 'rel', 'wrap', 'c30i', 'back'])
    b.fn('near', K + 'Less_DoubleDouble', 1200, 1050, B=NEAR_CM); b.link(dist, 'ReturnValue', 'near', 'A')
    b.fn('anynear', K + 'BooleanOR', 1400, 1000); b.link(door, 'ReturnValue', 'anynear', 'A'); b.link('near', 'ReturnValue', 'anynear', 'B')
    b.cut(door, 'ReturnValue', close_or, 'B'); b.link('anynear', 'ReturnValue', close_or, 'B')
    b.comment('Camera inside his head', ['near', 'anynear'])
    b.run()
    print('LOCK_CLAMP added')


if __name__ == '__main__':
    run()


# ---- second pass (PCI run_20261118_1414): centre the locked clamp on the capsule -----------------------------------
# The torso yaw comes from the shoulder line. During a reach it swings up to 50 deg in one tick, so a view pinned at
# the 30 deg edge by a fast mouse turn jumped up to 45 deg per tick. While locked the capsule does not follow the
# controller, so its yaw is the steady "body under the view": both locked paths now clamp around it. Cinematic-only
# keeps the torso-centred 60 deg path unchanged.
def capsule_centre():
    ns, es = inspect(P, F)
    by = {n['node_id']: n for n in ns}
    if any(n['title'] == 'Get Actor Rotation' for n in ns):
        print('LOCK_CAPSULE kept')
        return
    src = lambda node, p: next((e['from_node'], e['from_pin']) for e in es if e['to_node'] == node and e['to_pin'] == p)  # noqa: E731
    c30 = [n['node_id'] for n in ns if n['title'] == 'Clamp (Float)' and pin(n, 'Min').startswith('-%d' % LOCK_DEG)]
    pick = next(e['to_node'] for e in es if e['from_node'] in c30 and by[e['to_node']]['title'] == 'SelectFloat')
    c30b = next(c for c in c30 if any(e['from_node'] == c and e['to_node'] == pick for e in es))  # the bounded-path clamp
    c60 = src(pick, 'B')[0]
    add = next(e['to_node'] for e in es if e['from_node'] == pick)
    lk = src(pick, 'bPickA')
    torso = src(add, 'A')
    mk = next(e['to_node'] for e in es if e['from_node'] == add and by[e['to_node']]['title'] == 'MakeRotator')
    look = next(n['node_id'] for n in ns if n['title'] == 'GetControlRotation')
    lookb = next(e['to_node'] for e in es if e['from_node'] == look and by[e['to_node']]['title'] == 'BreakRotator')
    rel = next(e['to_node'] for e in es if (e['from_node'], e['from_pin']) == torso and e['to_pin'] == 'B' and by[e['to_node']]['title'] == 'float - float')
    back = next(e['to_node'] for e in es if (e['from_node'], e['from_pin']) == torso and e['to_pin'] == 'A' and e['to_node'] != add)
    b = Batch(P, F)
    b.fn('capr', '/Script/Engine.Actor:K2_GetActorRotation', 2950, 2350)
    b.fn('capb', K + 'BreakRotator', 3150, 2350); b.link('capr', 'ReturnValue', 'capb', 'InRot')
    # bounded path, locked: capsule yaw + clamp(control yaw - capsule yaw)
    b.fn('lrel', K + 'Subtract_DoubleDouble', 3350, 2200); b.link(lookb, 'Yaw', 'lrel', 'A'); b.link('capb', 'Yaw', 'lrel', 'B')
    b.fn('lwrap', K + 'NormalizeAxis', 3550, 2200); b.link('lrel', 'ReturnValue', 'lwrap', 'Angle')
    b.fn('lcl', K + 'FClamp', 3750, 2200, Min=-LOCK_DEG, Max=LOCK_DEG); b.link('lwrap', 'ReturnValue', 'lcl', 'Value')
    b.fn('lyaw', K + 'Add_DoubleDouble', 3950, 2200); b.link('capb', 'Yaw', 'lyaw', 'A'); b.link('lcl', 'ReturnValue', 'lyaw', 'B')
    b.fn('lsel', K + 'SelectFloat', 4150, 2100); b.link('lyaw', 'ReturnValue', 'lsel', 'A'); b.link(add, 'ReturnValue', 'lsel', 'B')
    b.link(lk[0], lk[1], 'lsel', 'bPickA')
    b.cut(add, 'ReturnValue', mk, 'Yaw'); b.link('lsel', 'ReturnValue', mk, 'Yaw')
    b.cut(pick, 'ReturnValue', add, 'B'); b.link(c60, 'ReturnValue', add, 'B')
    b.ops.append(dict(op='remove', node_ids=[pick, c30b]))
    # interaction-look path: clamp around the capsule too
    b.cut(torso[0], torso[1], rel, 'B'); b.link('capb', 'Yaw', rel, 'B')
    b.cut(torso[0], torso[1], back, 'A'); b.link('capb', 'Yaw', back, 'A')
    b.comment('Locked view near body', ['capr', 'capb', 'lrel', 'lwrap', 'lcl', 'lyaw', 'lsel'])
    b.run()
    print('LOCK_CAPSULE added')


if __name__ == '__main__' and 'second' in sys.argv:
    capsule_centre()
