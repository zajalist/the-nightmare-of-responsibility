"""BP_FoAPlayer phone hold v2 (main, 2026-11-09): the phone rides hand_l, the arm animates into view. Hayba batches.
- BeginPhoneHold(Phone): keep it, attach it to Body at hand_l with PhoneAttachOffset (the transform bake_phone_grip.py
  solved: Palm_L on the palm, the screen 33 cm in front of the eye in the hold pose), show it, raise (target 1).
- UpdatePhoneHold (Tick): PhoneRaise runs to the target in 0.45 s, eased into ABP_FoAPlayer_MH.PhoneGripWeight (the
  layered arm pose brings the arm and the phone up); the thumb tap as before (PhoneGripTime = PhoneTapAlpha / 30); once
  lowered: detach, hide, forget. The camera never moves.
- Since 2026-11-10 the hand is also pinned to the camera while held (phone_camera_ik.py): PhoneHandTarget / Rotation /
  ElbowTarget = FollowCamera (view pitch held to -40..10) composed with PhoneHandInEye / PhoneElbowInEye (the solve's
  'camera' block, scaled to the 170/180 body), at PhoneIKWeight = the raise ease. The spine and clavicle no longer move it.
EndPhoneHold and PhoneTap are unchanged. Sets the PhoneAttachOffset class default from Saved/AnimShots/phone_grip_bake.json.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/phone_hold_attach_graphs.py"""
import json
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
MC = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH.ABP_FoAPlayer_MH_C'
K = '/Script/Engine.KismetMathLibrary:'
ACT = '/Script/Engine.Actor:'
SYS = '/Script/Engine.KismetSystemLibrary:'
GS = '/Script/Engine.GameplayStatics:'
VIS = 1 / 0.9444444444444444  # Body's 170/180 scale is inherited through the bone: keep the phone life size

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
baked = json.load(open('P:/FoA/Saved/AnimShots/phone_grip_bake.json'))
q, t = baked['attach']['rotation'], baked['attach']['location']
offset = '(Rotation=(X=%r,Y=%r,Z=%r,W=%r),Translation=(X=%r,Y=%r,Z=%r),Scale3D=(X=%r,Y=%r,Z=%r))' % (*q, *t, VIS, VIS, VIS)
cam = baked['camera']  # the solved hand and elbow in the eye frame; the body is 170/180 scale in game, so are its distances
hand_in_eye = '(Rotation=(X=%r,Y=%r,Z=%r,W=%r),Translation=(X=%r,Y=%r,Z=%r),Scale3D=(X=1,Y=1,Z=1))' % (
    *cam['hand_rotation'], *[c / VIS for c in cam['hand_location']])
elbow_in_eye = '(X=%r,Y=%r,Z=%r)' % tuple(c / VIS for c in cam['elbow_location'])


def fresh(name):
    nodes, _ = inspect(P, name)
    e = find(nodes, name)
    b = Batch(P, name)
    old = [n['node_id'] for n in nodes if n['node_id'] != e and n['title'] != 'Return Node']
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    return b, e


def apply_offsets():
    for k, v in (('PhoneAttachOffset', offset), ('PhoneHandInEye', hand_in_eye), ('PhoneElbowInEye', elbow_in_eye)):
        r = h.call('object_set_property', dict(path=P + '.Default__BP_FoAPlayer_C', properties={k: v}), owner='anim')
        assert r.get('ok'), r
    r = h.call('blueprint_compile', dict(path=P), owner='anim')
    assert r.get('ok') and r['data'].get('error_count', 0) == 0 and r['data'].get('warning_count', 0) == 0, r
    r = h.call('asset_save', dict(asset_paths=[P], force=True), owner='anim')
    assert r.get('data', {}).get('verified'), r


covered = any(r.lower() in ('global', 'asset:/game/foa/characters', 'asset:/game/foa/characters/player')
              for _, resources in h.leases_of('anim') for r in resources)
lease = None if covered else h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=60)
try:
    if '--defaults-only' in sys.argv:
        apply_offsets()
        print('PHONE_ATTACH updated existing graph defaults', offset, hand_in_eye, elbow_in_eye)
        sys.exit(0)
    for name, kind in (('PhoneAttachOffset', 'transform'), ('PhoneHandInEye', 'transform'), ('PhoneElbowInEye', 'vector')):
        r = h.call('blueprint_add_variable', dict(path=P, variable_name=name, variable_type=kind,
                                                  instance_editable=False, update_existing=True, category='Phone'))
        assert r.get('ok'), r
    b, e = fresh('BeginPhoneHold')
    b.set('keep', 'PhoneActor', 300, 0); b.link(e, 'Phone', 'keep', 'PhoneActor')
    b.get('body', 'Body', 300, 300)
    b.fn('attach', ACT + 'K2_AttachToComponent', 600, 0, SocketName='hand_l', LocationRule='SnapToTarget',
         RotationRule='SnapToTarget', ScaleRule='SnapToTarget', bWeldSimulatedBodies='false')
    b.link(e, 'Phone', 'attach', 'self'); b.link('body', 'Body', 'attach', 'Parent')
    b.get('off', 'PhoneAttachOffset', 600, 300)
    b.fn('seat', ACT + 'K2_SetActorRelativeTransform', 900, 0, bSweep='false', bTeleport='true')
    b.link(e, 'Phone', 'seat', 'self'); b.link('off', 'PhoneAttachOffset', 'seat', 'NewRelativeTransform')
    b.fn('show', ACT + 'SetActorHiddenInGame', 1200, 0, bNewHidden='false'); b.link(e, 'Phone', 'show', 'self')
    b.set('up', 'PhoneRaiseTarget', 1500, 0); b.pin('up', 'PhoneRaiseTarget', 1.0)
    b.chain(e, 'keep', 'attach', 'seat', 'show', 'up')
    b.comment('Phone in the left hand: Palm_L on the palm, by attachment', ['keep', 'body', 'attach', 'off', 'seat', 'show', 'up'])
    b.run()

    b, e = fresh('UpdatePhoneHold')
    b.get('phone', 'PhoneActor', 0, 300)
    b.fn('has', SYS + 'IsValid', 250, 300); b.link('phone', 'PhoneActor', 'has', 'Object')
    b.node('held', 'branch', 300, 0); b.link('has', 'ReturnValue', 'held', 'Condition')
    b.fn('dt', GS + 'GetWorldDeltaSeconds', 300, 600)
    b.get('r0', 'PhoneRaise', 300, 750); b.get('rt', 'PhoneRaiseTarget', 300, 900)
    b.fn('step', K + 'FInterpTo_Constant', 600, 700, InterpSpeed=1.0 / 0.45)
    b.link('r0', 'PhoneRaise', 'step', 'Current'); b.link('rt', 'PhoneRaiseTarget', 'step', 'Target'); b.link('dt', 'ReturnValue', 'step', 'DeltaTime')
    b.set('r', 'PhoneRaise', 600, 0); b.link('step', 'ReturnValue', 'r', 'PhoneRaise')
    b.fn('ease', K + 'FInterpEaseInOut', 900, 900, A=0.0, B=1.0, Exponent=2.0); b.link('r', 'Output_Get', 'ease', 'Alpha')
    b.get('a0', 'PhoneTapAlpha', 900, 1100); b.get('t0', 'PhoneTapTarget', 900, 1250)
    b.fn('pressing', K + 'Greater_DoubleDouble', 1150, 1250, B=0.5); b.link('t0', 'PhoneTapTarget', 'pressing', 'A')
    b.fn('speed', K + 'SelectFloat', 1400, 1250, A=1.0 / 0.07, B=1.0 / 0.14); b.link('pressing', 'ReturnValue', 'speed', 'bPickA')
    b.fn('tstep', K + 'FInterpTo_Constant', 1650, 1100)
    b.link('a0', 'PhoneTapAlpha', 'tstep', 'Current'); b.link('t0', 'PhoneTapTarget', 'tstep', 'Target')
    b.link('dt', 'ReturnValue', 'tstep', 'DeltaTime'); b.link('speed', 'ReturnValue', 'tstep', 'InterpSpeed')
    b.set('a', 'PhoneTapAlpha', 900, 0); b.link('tstep', 'ReturnValue', 'a', 'PhoneTapAlpha')
    b.fn('full', K + 'GreaterEqual_DoubleDouble', 1150, 300, B=0.99); b.link('a', 'Output_Get', 'full', 'A')
    b.node('pressed', 'branch', 1200, 0); b.link('full', 'ReturnValue', 'pressed', 'Condition')
    b.set('lift', 'PhoneTapTarget', 1450, -200); b.pin('lift', 'PhoneTapTarget', 0.0)
    b.get('body', 'Body', 1450, 400)
    b.fn('anim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 1700, 400); b.link('body', 'Body', 'anim', 'self')
    b.node('mh', 'cast', 1750, 0, class_path=MC); b.link('anim', 'ReturnValue', 'mh', 'Object')
    b.set('gw', 'PhoneGripWeight', 2050, 0, MC); b.link('mh', 'AsABP Fo APlayer MH', 'gw', 'self'); b.link('ease', 'ReturnValue', 'gw', 'PhoneGripWeight')
    b.fn('frame', K + 'Divide_DoubleDouble', 2050, 300, B=30.0); b.link('a', 'Output_Get', 'frame', 'A')
    b.set('gt', 'PhoneGripTime', 2350, 0, MC); b.link('mh', 'AsABP Fo APlayer MH', 'gt', 'self'); b.link('frame', 'ReturnValue', 'gt', 'PhoneGripTime')
    b.fn('low', K + 'LessEqual_DoubleDouble', 2350, 400, B=0.001); b.link('r', 'Output_Get', 'low', 'A')
    b.fn('away', K + 'LessEqual_DoubleDouble', 2350, 550, B=0.0); b.link('rt', 'PhoneRaiseTarget', 'away', 'A')
    b.fn('gone', K + 'BooleanAND', 2600, 450); b.link('low', 'ReturnValue', 'gone', 'A'); b.link('away', 'ReturnValue', 'gone', 'B')
    b.node('done', 'branch', 2650, 0); b.link('gone', 'ReturnValue', 'done', 'Condition')
    b.fn('free', ACT + 'K2_DetachFromActor', 2900, 0, LocationRule='KeepWorld', RotationRule='KeepWorld', ScaleRule='KeepWorld')
    b.link('phone', 'PhoneActor', 'free', 'self')
    b.fn('hide', ACT + 'SetActorHiddenInGame', 3200, 0, bNewHidden='true'); b.link('phone', 'PhoneActor', 'hide', 'self')
    b.set('forget', 'PhoneActor', 3500, 0)
    b.chain(e, 'held'); b.link('held', 'then', 'r', 'execute'); b.chain('r', 'a', 'pressed')
    b.link('pressed', 'then', 'lift', 'execute'); b.link('lift', 'then', 'mh', 'execute'); b.link('pressed', 'else', 'mh', 'execute')
    # the hand pinned to the camera (phone_camera_ik.py): the solved hand and elbow in the eye frame, view pitch held to -40..10
    b.get('cam', 'FollowCamera', 2350, 700)
    b.fn('cloc', '/Script/Engine.SceneComponent:K2_GetComponentLocation', 2600, 700); b.link('cam', 'FollowCamera', 'cloc', 'self')
    b.fn('crot', '/Script/Engine.SceneComponent:K2_GetComponentRotation', 2600, 850); b.link('cam', 'FollowCamera', 'crot', 'self')
    b.fn('cbr', K + 'BreakRotator', 2850, 850); b.link('crot', 'ReturnValue', 'cbr', 'InRot')
    b.fn('cpitch', K + 'FClamp', 3100, 850, Min=-40.0, Max=10.0); b.link('cbr', 'Pitch', 'cpitch', 'Value')
    b.fn('cview', K + 'MakeRotator', 3350, 850, Roll=0.0); b.link('cpitch', 'ReturnValue', 'cview', 'Pitch'); b.link('cbr', 'Yaw', 'cview', 'Yaw')
    b.fn('ct', K + 'MakeTransform', 3600, 750, Scale='1,1,1'); b.link('cloc', 'ReturnValue', 'ct', 'Location'); b.link('cview', 'ReturnValue', 'ct', 'Rotation')
    b.get('hie', 'PhoneHandInEye', 3600, 1000)
    b.fn('ht', K + 'ComposeTransforms', 3850, 850); b.link('hie', 'PhoneHandInEye', 'ht', 'A'); b.link('ct', 'ReturnValue', 'ht', 'B')
    b.fn('hb', K + 'BreakTransform', 4100, 850); b.link('ht', 'ReturnValue', 'hb', 'InTransform')
    b.get('eie', 'PhoneElbowInEye', 3850, 1100)
    b.fn('ew', K + 'TransformLocation', 4100, 1100); b.link('ct', 'ReturnValue', 'ew', 'T'); b.link('eie', 'PhoneElbowInEye', 'ew', 'Location')
    b.set('ikw', 'PhoneIKWeight', 2650, 0, MC); b.link('mh', 'AsABP Fo APlayer MH', 'ikw', 'self'); b.link('ease', 'ReturnValue', 'ikw', 'PhoneIKWeight')
    b.set('iht', 'PhoneHandTarget', 2950, 0, MC); b.link('mh', 'AsABP Fo APlayer MH', 'iht', 'self'); b.link('hb', 'Location', 'iht', 'PhoneHandTarget')
    b.set('ihr', 'PhoneHandRotation', 3250, 0, MC); b.link('mh', 'AsABP Fo APlayer MH', 'ihr', 'self'); b.link('hb', 'Rotation', 'ihr', 'PhoneHandRotation')
    b.set('iet', 'PhoneElbowTarget', 3550, 0, MC); b.link('mh', 'AsABP Fo APlayer MH', 'iet', 'self'); b.link('ew', 'ReturnValue', 'iet', 'PhoneElbowTarget')
    b.chain('mh', 'gw', 'gt', 'ikw', 'iht', 'ihr', 'iet', 'done'); b.link('done', 'then', 'free', 'execute'); b.chain('free', 'hide', 'forget')
    b.comment('Only while holding the phone', ['phone', 'has', 'held'])
    b.comment('Raise, lower and the thumb tap drive the arm layer', ['dt', 'r0', 'rt', 'step', 'r', 'ease', 'a0', 't0', 'pressing', 'speed',
                                                                      'tstep', 'a', 'full', 'pressed', 'lift', 'body', 'anim', 'mh', 'gw',
                                                                      'frame', 'gt'])
    b.comment('Put it away', ['low', 'away', 'gone', 'done', 'free', 'hide', 'forget'])
    b.comment('The hand pinned to the camera while held', ['cam', 'cloc', 'crot', 'cbr', 'cpitch', 'cview', 'ct', 'hie', 'ht', 'hb', 'eie', 'ew',
                                                           'ikw', 'iht', 'ihr', 'iet'])
    b.run()
    apply_offsets()
finally:
    if lease:
        h.release('anim', lease)
print('PHONE_ATTACH_GRAPHS done', offset)
print('PHONE_CAMERA_PIN', hand_in_eye, elbow_in_eye)
