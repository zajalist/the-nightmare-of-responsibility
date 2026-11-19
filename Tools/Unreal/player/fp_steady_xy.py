"""playercam lane (user bug 2026-11-18: "the head moves too much while you own the camera"). Hayba graph batch on
BP_FoAPlayer.SteadyFPEye. Measured (PCM, run_20261118_1326): SteadyFPEye steadied only the eye height; x/y rode the
animated head landmark 1:1, so the eye swung 17 cm forward at every walk start, 20-27 cm forward and sideways at every
stop (for about 1 s, single-tick steps up to 7 cm), 3-5 cm side to side while walking and 2.8 cm in idle.
Now x/y is the head landmark's offset in the capsule's frame through a follower (FPEyeOffset):
- free play: InterpSpeed FREE_SPEED (time constant 4 s), no step sway kept: the camera holds its place over the capsule
  and only drifts with real posture changes (a crouch, the pose after an interaction);
- cinematic or interaction locked: InterpSpeed AUTHORED_SPEED (as the eye height already follows), so kneels, reaches
  and scripted head moves keep the head's place; the switch glides, never snaps.
The capsule's own yaw carries the offset, so a mouse turn turns the camera about the capsule as the body does.
The 12% of the step bob the eye height keeps is scaled by (1 - MPC_Dream.ReduceMotion): Reduce Motion keeps none.
Idempotent (skips when FPEyeOffset is already set in the graph). Inside an asset lease on BP_FoAPlayer:
  $env:HAYBA_AGENT_ID='playercam'; python Tools/Unreal/player/fp_steady_xy.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
F = 'SteadyFPEye'
K = '/Script/Engine.KismetMathLibrary:'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
FREE_SPEED, AUTHORED_SPEED, BOB_K = 0.25, 12.0, 0.12


def run():
    ns, es = inspect(P, F)
    by = {n['node_id']: n for n in ns}
    if any(n['title'] == 'Set FPEyeOffset' for n in ns):
        print('STEADY_XY kept')
        return
    r = h.call('blueprint_add_variable', dict(path=P, variable_name='FPEyeOffset', variable_type='vector', default_value='0,0,0',
                                              instance_editable=False, update_existing=True, category='Camera'))
    assert r.get('ok'), r
    one = lambda title: next(n['node_id'] for n in ns if n['title'] == title)  # noqa: E731
    entry = one(F)
    eyew = one('TransformLocation')
    me = one('Get Actor Location')
    dt = one('GetWorldDeltaSeconds')
    make = one('MakeVector')
    place = one('Set World Location')
    keep = next(n['node_id'] for n in ns if n['title'] == 'float * float' and any(
        p['name'] == 'B' and str(p.get('default_value', '')).startswith('0.12') for p in n['pins']))
    first = next(e['to_node'] for e in es if e['from_node'] == entry and e['from_pin'] == 'then')
    before_place = next(e['from_node'] for e in es if e['to_node'] == place and e['to_pin'] == 'execute')
    brk = next(e['from_node'] for e in es if e['to_node'] == make and e['to_pin'] == 'X')
    assert by[brk]['title'] == 'BreakVector'

    b = Batch(P, F)
    # Reduce Motion scales the kept step bob (the MPC read is impure: it sits first on the exec chain)
    b.fn('rm', '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 200, -250, Collection=MPC, ParameterName='ReduceMotion')
    b.fn('rmkeep', K + 'Subtract_DoubleDouble', 450, -250, A=1.0); b.link('rm', 'ReturnValue', 'rmkeep', 'B')
    b.fn('bobk', K + 'Multiply_DoubleDouble', 700, -250, B=BOB_K); b.link('rmkeep', 'ReturnValue', 'bobk', 'A')
    b.link('bobk', 'ReturnValue', keep, 'B')
    b.cut(entry, 'then', first, 'execute'); b.link(entry, 'then', 'rm', 'execute'); b.link('rm', 'then', first, 'execute')
    # x/y: the eye's offset in the capsule frame, followed slowly in free play, closely when authored
    b.fn('rot', '/Script/Engine.Actor:K2_GetActorRotation', 5100, 1500)
    b.fn('offw', K + 'Subtract_VectorVector', 5100, 1700); b.link(eyew, 'ReturnValue', 'offw', 'A'); b.link(me, 'ReturnValue', 'offw', 'B')
    b.fn('offl', K + 'LessLess_VectorRotator', 5350, 1600); b.link('offw', 'ReturnValue', 'offl', 'A'); b.link('rot', 'ReturnValue', 'offl', 'B')
    b.get('held', 'FPEyeOffset', 5350, 1850)
    b.fn('fresh', K + 'EqualEqual_VectorVector', 5600, 1850, B='0,0,0', ErrorTolerance=0.01); b.link('held', 'FPEyeOffset', 'fresh', 'A')
    b.fn('start', K + 'SelectVector', 5850, 1750); b.link('offl', 'ReturnValue', 'start', 'A'); b.link('held', 'FPEyeOffset', 'start', 'B')
    b.link('fresh', 'ReturnValue', 'start', 'bPickA')
    b.get('cine', 'bCinematic', 5600, 2050); b.get('lock', 'bInteractionLocked', 5600, 2150)
    b.fn('authored', K + 'BooleanOR', 5850, 2050); b.link('cine', 'bCinematic', 'authored', 'A'); b.link('lock', 'bInteractionLocked', 'authored', 'B')
    b.fn('speed', K + 'SelectFloat', 6100, 2000, A=AUTHORED_SPEED, B=FREE_SPEED); b.link('authored', 'ReturnValue', 'speed', 'bPickA')
    b.fn('follow', K + 'VInterpTo', 6350, 1700); b.link('start', 'ReturnValue', 'follow', 'Current'); b.link('offl', 'ReturnValue', 'follow', 'Target')
    b.link(dt, 'ReturnValue', 'follow', 'DeltaTime'); b.link('speed', 'ReturnValue', 'follow', 'InterpSpeed')
    b.set('setoff', 'FPEyeOffset', 6600, 0); b.link('follow', 'ReturnValue', 'setoff', 'FPEyeOffset')
    b.fn('back', K + 'GreaterGreater_VectorRotator', 6850, 1600); b.link('setoff', 'Output_Get', 'back', 'A'); b.link('rot', 'ReturnValue', 'back', 'B')
    b.fn('world', K + 'Add_VectorVector', 7100, 1600); b.link(me, 'ReturnValue', 'world', 'A'); b.link('back', 'ReturnValue', 'world', 'B')
    b.fn('xy', K + 'BreakVector', 7350, 1600); b.link('world', 'ReturnValue', 'xy', 'InVec')
    b.cut(brk, 'X', make, 'X'); b.cut(brk, 'Y', make, 'Y'); b.link('xy', 'X', make, 'X'); b.link('xy', 'Y', make, 'Y')
    b.cut(before_place, 'then', place, 'execute'); b.link(before_place, 'then', 'setoff', 'execute'); b.link('setoff', 'then', place, 'execute')
    b.comment('Reduce Motion', ['rm', 'rmkeep', 'bobk'])
    b.comment('Steady eye over capsule', ['rot', 'offw', 'offl', 'held', 'fresh', 'start', 'cine', 'lock', 'authored', 'speed', 'follow',
                                                  'setoff', 'back', 'world', 'xy'])
    b.run()
    print('STEADY_XY added')


if __name__ == '__main__':
    run()


# ---- second pass (PCM run_20261118_1354) -------------------------------------------------------------------------
# 1. FollowCamera rode the head socket: SteadyFPEye's SetWorldLocation runs in the pawn tick, before that frame's anim
#    update, so the camera then moved with the head's frame-to-frame motion on a lever as long as its offset from the
#    head (single-tick spikes of 5-15 cm). It now hangs off the capsule: it moves with the capsule only.
# 2. The slow follower kept whatever offset the last cinematic left (21 cm behind the eye after the wake-up). Free play
#    now aims at the standing eye offset FPEyeNominal (median of the measured eye, 27 cm ahead, 3 cm right) plus
#    FREE_SHARE of the head's own deviation (x (1 - ReduceMotion)), eased at FREE_EASE.
FREE_SHARE, FREE_EASE, NOMINAL = 0.06, 3.0, '27,3,0'


def nominal_and_capsule():
    ns, es = inspect(P, F)
    if not any(n['title'] == 'Get FPEyeNominal' for n in ns):
        r = h.call('blueprint_add_variable', dict(path=P, variable_name='FPEyeNominal', variable_type='vector', default_value=NOMINAL,
                                                  instance_editable=False, update_existing=True, category='Camera'))
        assert r.get('ok'), r
        by = {n['node_id']: n for n in ns}
        pin = lambda n, k: str(next((p.get('default_value') for p in n['pins'] if p['name'] == k), ''))  # noqa: E731
        speed = next(n['node_id'] for n in ns if n['title'] == 'SelectFloat' and pin(n, 'A').startswith('12') and pin(n, 'B').startswith('0.25'))
        follow = next(n['node_id'] for n in ns if n['title'] == 'VInterpTo')
        offl = next(e['from_node'] for e in es if e['to_node'] == follow and e['to_pin'] == 'Target')
        authored = next(e['from_node'] for e in es if e['to_node'] == speed and e['to_pin'] == 'bPickA')
        rmkeep = next(n['node_id'] for n in ns if n['title'] == 'float - float' and pin(n, 'A').startswith('1.0'))
        assert by[offl]['title'] == 'Unrotate Vector', by[offl]['title']
        b = Batch(P, F)
        b.pin(speed, 'B', FREE_EASE)
        b.get('nom', 'FPEyeNominal', 5850, 2300)
        b.fn('dev', K + 'Subtract_VectorVector', 6100, 2250); b.link(offl, 'ReturnValue', 'dev', 'A'); b.link('nom', 'FPEyeNominal', 'dev', 'B')
        b.fn('share', K + 'Multiply_DoubleDouble', 6100, 2450, B=FREE_SHARE); b.link(rmkeep, 'ReturnValue', 'share', 'A')
        b.fn('kept', K + 'Multiply_VectorFloat', 6350, 2250); b.link('dev', 'ReturnValue', 'kept', 'A'); b.link('share', 'ReturnValue', 'kept', 'B')
        b.fn('freet', K + 'Add_VectorVector', 6600, 2250); b.link('nom', 'FPEyeNominal', 'freet', 'A'); b.link('kept', 'ReturnValue', 'freet', 'B')
        b.fn('tgt', K + 'SelectVector', 6850, 2100); b.link(offl, 'ReturnValue', 'tgt', 'A'); b.link('freet', 'ReturnValue', 'tgt', 'B')
        b.link(authored, 'ReturnValue', 'tgt', 'bPickA')
        b.cut(offl, 'ReturnValue', follow, 'Target'); b.link('tgt', 'ReturnValue', follow, 'Target')
        b.comment('Free eye target', ['nom', 'dev', 'share', 'kept', 'freet', 'tgt'])
        b.run()
    A = 'AttachFirstPersonCamera'
    ns, es = inspect(P, A)
    att = next(n['node_id'] for n in ns if n['title'] == 'Attach Component To Component')
    face = next((e['from_node'] for e in es if e['to_node'] == att and e['to_pin'] == 'Parent'), None)
    if face and next(n for n in ns if n['node_id'] == face)['title'] == 'Get Face':
        rel = next(n['node_id'] for n in ns if n['title'] == 'Set Relative Location')
        b = Batch(P, A)
        b.fn('root', '/Script/Engine.Actor:K2_GetRootComponent', 0, 650)  # the capsule (a member get of CapsuleComponent was purged)
        b.cut(face, 'Face', att, 'Parent'); b.link('root', 'ReturnValue', att, 'Parent')
        b.pin(att, 'SocketName', 'None'); b.pin(att, 'LocationRule', 'KeepWorld')
        b.pin(rel, 'NewLocation', '27,3,64')  # the standing eye in the capsule's frame until SteadyFPEye's first tick
        b.ops.append(dict(op='remove', node_ids=[face]))
        b.run()
    print('STEADY_XY nominal + capsule parent')


if __name__ == '__main__' and 'second' in sys.argv:
    nominal_and_capsule()


# ---- third pass (PCM run_20261118_1407): the eye height -------------------------------------------------------------
# x/y now holds within 0.2 cm, but standing still the height still targeted the real eye height, and the GASP stances
# put the eye 59 to 71 cm above the capsule centre: idle drifted 2.8 cm, every stop rose 2.5-3.4 cm over about 1.2 s.
# Free play (not cinematic, not interaction locked, not crouching) now aims at FPEyeHeightNominal plus the same small
# share of the real deviation (FREE_SHARE x (1 - ReduceMotion)); the existing FPEyeHeightA easing smooths it. Authored
# moments and crouch keep the old height (the real eye standing, 12% of the bob moving), so a crouch still lowers him.
Z_NOMINAL = 65.0


def nominal_height():
    ns, es = inspect(P, F)
    if any(n['title'] == 'Get FPEyeHeightNominal' for n in ns):
        print('STEADY_Z kept')
        return
    r = h.call('blueprint_add_variable', dict(path=P, variable_name='FPEyeHeightNominal', variable_type='float', default_value=str(Z_NOMINAL),
                                              instance_editable=False, update_existing=True, category='Camera'))
    assert r.get('ok'), r
    by = {n['node_id']: n for n in ns}
    pin = lambda n, k: str(next((p.get('default_value') for p in n['pins'] if p['name'] == k), ''))  # noqa: E731
    lerp = next(n['node_id'] for n in ns if n['title'] == 'Lerp')
    height = next(e['from_node'] for e in es if e['to_node'] == lerp and e['to_pin'] == 'A')  # real eye height above the capsule
    outs = [(e['to_node'], e['to_pin']) for e in es if e['from_node'] == lerp and e['from_pin'] == 'ReturnValue']
    share = next(n['node_id'] for n in ns if n['title'] == 'float * float' and pin(n, 'B').startswith(str(FREE_SHARE)))
    tgt = next(n['node_id'] for n in ns if n['title'] == 'SelectVector' and any(e['to_node'] == n['node_id'] and e['to_pin'] == 'bPickA' for e in es)
               and any(e['from_node'] == n['node_id'] and by[e['to_node']]['title'] == 'VInterpTo' and e['to_pin'] == 'Target' for e in es))
    authored = next(e['from_node'] for e in es if e['to_node'] == tgt and e['to_pin'] == 'bPickA')
    assert by[height]['title'] == 'float - float' and by[authored]['title'] == 'OR Boolean' and len(outs) == 2, (outs,)
    b = Batch(P, F)
    b.fn('mv', '/Script/Engine.Pawn:GetMovementComponent', 3000, 1400)
    b.fn('crouch', '/Script/Engine.NavMovementComponent:IsCrouching', 3250, 1400); b.link('mv', 'ReturnValue', 'crouch', 'self')
    b.fn('own', K + 'BooleanOR', 3500, 1350); b.link(authored, 'ReturnValue', 'own', 'A'); b.link('crouch', 'ReturnValue', 'own', 'B')
    b.get('zn', 'FPEyeHeightNominal', 3000, 1200)
    b.fn('zdev', K + 'Subtract_DoubleDouble', 3250, 1150); b.link(height, 'ReturnValue', 'zdev', 'A'); b.link('zn', 'FPEyeHeightNominal', 'zdev', 'B')
    b.fn('zkept', K + 'Multiply_DoubleDouble', 3500, 1150); b.link('zdev', 'ReturnValue', 'zkept', 'A'); b.link(share, 'ReturnValue', 'zkept', 'B')
    b.fn('zfree', K + 'Add_DoubleDouble', 3750, 1150); b.link('zn', 'FPEyeHeightNominal', 'zfree', 'A'); b.link('zkept', 'ReturnValue', 'zfree', 'B')
    b.fn('zwant', K + 'SelectFloat', 4000, 1100); b.link(lerp, 'ReturnValue', 'zwant', 'A'); b.link('zfree', 'ReturnValue', 'zwant', 'B')
    b.link('own', 'ReturnValue', 'zwant', 'bPickA')
    for node, p in outs:
        b.cut(lerp, 'ReturnValue', node, p); b.link('zwant', 'ReturnValue', node, p)
    b.comment('Free eye height', ['mv', 'crouch', 'own', 'zn', 'zdev', 'zkept', 'zfree', 'zwant'])
    b.run()
    print('STEADY_Z added')


if __name__ == '__main__' and 'third' in sys.argv:
    nominal_height()
