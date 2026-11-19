"""First-person phone hold (anim lane; main approved 2026-11-09). Hayba graph batches on BP_FoAPlayer.
The camera stays in his eyes. The phone is placed against the head camera, not the hand, and the LEFT hand follows it
through the left-hand IK in ABP_FoAPlayer_MH that environment contact already drives (EnvironmentHand*):
- BeginPhoneHold(Phone): detach the phone, raise (PhoneRaiseTarget 1). EndPhoneHold(): lower (target 0); when the
  lower finishes the hand releases and the phone hides. PhoneTap(): the thumb tap (montage section 'Tap', once the
  grip clip has it).
- UpdatePhoneHold (Tick, after UpdateFirstPersonVisibility so it uses this frame's camera): PhoneRaise eases over
  0.35 s; the phone's 'Screen' socket goes to lerp(PhoneLowOffset, PhoneReadOffset) in camera space (33 cm out, 6 cm
  low, 3 cm left by default), turned to face the eye, pitched down 70 deg while lowered, with a 0.4 cm / 0.6 deg
  breathing sway (x0.25 under Reduce Motion). The wrist goes to PhoneWristOffset in the screen frame, the hand rotation
  is PhoneHandRot composed with the screen rotation, the elbow hangs low and out so the forearm enters from below.
All offsets and the hand rotation are class defaults (Phone category), tuned from PIE measurements without regraphing.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/phone_hold_graphs.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
PC = P + '.BP_FoAPlayer_C'
MC = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH.ABP_FoAPlayer_MH_C'
HOLD = '/Game/FoA/Characters/Player/Montages/AM_FoA_PhoneHold.AM_FoA_PhoneHold'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
K = '/Script/Engine.KismetMathLibrary:'
SC = '/Script/Engine.SceneComponent:'
ACT = '/Script/Engine.Actor:'
GS = '/Script/Engine.GameplayStatics:'
SYS = '/Script/Engine.KismetSystemLibrary:'

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
VARS = [('PhoneActor', 'object:/Script/Engine.Actor', None), ('PhoneRaise', 'float', '0'), ('PhoneRaiseTarget', 'float', '0'),
        ('PhoneReadOffset', 'vector', '(X=33,Y=-3,Z=-6)'), ('PhoneLowOffset', 'vector', '(X=22,Y=-14,Z=-38)'),
        ('PhoneWristOffset', 'vector', '(X=-2,Y=-4,Z=-6)'), ('PhoneElbowOffset', 'vector', '(X=-12,Y=-22,Z=-28)'),
        ('PhoneHandRot', 'rotator', '(Pitch=0,Yaw=0,Roll=0)')]
for name, typ, default in VARS:
    args = dict(path=P, variable_name=name, variable_type=typ, instance_editable=False, update_existing=True, category='Phone')
    if default is not None:
        args['default_value'] = default
    r = h.call('blueprint_add_variable', args)
    assert r.get('ok'), r


def ensure_fn(name, inputs=()):
    if not h.call('blueprint_inspect_graph', dict(path=P, graph_name=name)).get('ok'):
        r = h.call('blueprint_add_function', dict(path=P, function_name=name, inputs=list(inputs)))
        assert r.get('ok'), r
    nodes, _ = inspect(P, name)
    return find(nodes, name), len(nodes)


# ---------------------------------------------------------------- BeginPhoneHold(Phone)
e, n = ensure_fn('BeginPhoneHold', [dict(name='Phone', type='object:/Script/Engine.Actor')])
if n <= 1:
    b = Batch(P, 'BeginPhoneHold')
    b.set('keep', 'PhoneActor', 300, 0); b.link(e, 'Phone', 'keep', 'PhoneActor')
    b.fn('free', ACT + 'K2_DetachFromActor', 600, 0, LocationRule='KeepWorld', RotationRule='KeepWorld', ScaleRule='KeepWorld')
    b.link(e, 'Phone', 'free', 'self')
    b.fn('show', ACT + 'SetActorHiddenInGame', 900, 0, bNewHidden='false'); b.link(e, 'Phone', 'show', 'self')
    b.set('up', 'PhoneRaiseTarget', 1200, 0); b.pin('up', 'PhoneRaiseTarget', 1.0)
    # shortcut: the left-hand finger grip (montage with Hold/Tap sections) is baked after the rig lane's finger-joint fix;
    # until then the fingers keep the idle pose and only the arm and wrist hold the phone.
    b.chain(e, 'keep', 'free', 'show', 'up')
    b.comment('Take the phone out', ['keep', 'free', 'show', 'up'])
    b.run()

# ---------------------------------------------------------------- EndPhoneHold()
e, n = ensure_fn('EndPhoneHold')
if n <= 1:
    b = Batch(P, 'EndPhoneHold')
    b.set('down', 'PhoneRaiseTarget', 300, 0); b.pin('down', 'PhoneRaiseTarget', 0.0)
    b.chain(e, 'down')
    b.comment('Put it away', ['down'])
    b.run()

# ---------------------------------------------------------------- PhoneTap()
e, n = ensure_fn('PhoneTap')
if n <= 1:
    b = Batch(P, 'PhoneTap')
    b.get('mesh', 'Mesh', 0, 300)  # inherited member of self: no class_path
    b.fn('anim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 300, 300); b.link('mesh', 'Mesh', 'anim', 'self')
    b.fn('tap', '/Script/Engine.AnimInstance:Montage_JumpToSection', 600, 0, SectionName='Tap', Montage=HOLD)
    b.link('anim', 'ReturnValue', 'tap', 'self'); b.chain(e, 'tap')
    b.comment('Thumb taps the screen', ['mesh', 'anim', 'tap'])
    b.run()

# ---------------------------------------------------------------- UpdatePhoneHold() (Tick)
e, n = ensure_fn('UpdatePhoneHold')
if n <= 1:
    b = Batch(P, 'UpdatePhoneHold')
    # active only with a phone
    b.get('phone', 'PhoneActor', 0, 300)
    b.fn('has', SYS + 'IsValid', 300, 300); b.link('phone', 'PhoneActor', 'has', 'Object')
    b.node('held', 'branch', 300, 0); b.link('has', 'ReturnValue', 'held', 'Condition'); b.chain(e, 'held')
    # raise / lower over 0.35 s
    b.fn('dt', GS + 'GetWorldDeltaSeconds', 300, 600)
    b.get('r0', 'PhoneRaise', 300, 750); b.get('rt', 'PhoneRaiseTarget', 300, 900)
    b.fn('step', K + 'FInterpTo_Constant', 600, 700, InterpSpeed=1.0 / 0.35)
    b.link('r0', 'PhoneRaise', 'step', 'Current'); b.link('rt', 'PhoneRaiseTarget', 'step', 'Target'); b.link('dt', 'ReturnValue', 'step', 'DeltaTime')
    b.set('r', 'PhoneRaise', 600, 0); b.link('step', 'ReturnValue', 'r', 'PhoneRaise'); b.link('held', 'then', 'r', 'execute')
    # put away when fully lowered
    b.fn('low', K + 'LessEqual_DoubleDouble', 900, 600, B=0.001); b.link('r', 'Output_Get', 'low', 'A')
    b.fn('away', K + 'LessEqual_DoubleDouble', 900, 800, B=0.0); b.link('rt', 'PhoneRaiseTarget', 'away', 'A')
    b.fn('gone', K + 'BooleanAND', 1200, 700); b.link('low', 'ReturnValue', 'gone', 'A'); b.link('away', 'ReturnValue', 'gone', 'B')
    b.node('done', 'branch', 900, 0); b.link('gone', 'ReturnValue', 'done', 'Condition'); b.chain('r', 'done')
    b.get('body0', 'Body', 1200, -500)
    b.fn('anim0', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 1500, -500); b.link('body0', 'Body', 'anim0', 'self')
    b.node('mh0', 'cast', 1500, -300, class_path=MC); b.link('anim0', 'ReturnValue', 'mh0', 'Object'); b.link('done', 'then', 'mh0', 'execute')
    b.set('release', 'EnvironmentHandWeight', 1800, -300, MC); b.pin('release', 'EnvironmentHandWeight', 0.0)
    b.link('mh0', 'AsABP Fo APlayer MH', 'release', 'self'); b.chain('mh0', 'release')
    b.fn('ungrip', '/Script/Engine.Character:StopAnimMontage', 2100, -300, AnimMontage=HOLD); b.chain('release', 'ungrip')
    b.fn('hide', ACT + 'SetActorHiddenInGame', 2400, -300, bNewHidden='true'); b.link('phone', 'PhoneActor', 'hide', 'self'); b.chain('ungrip', 'hide')
    b.set('forget', 'PhoneActor', 2700, -300); b.chain('hide', 'forget')
    # place the phone: its Screen socket in camera space, facing the eye
    b.fn('ease', K + 'FInterpEaseInOut', 1200, 1000, A=0.0, B=1.0, Exponent=2.0); b.link('r', 'Output_Get', 'ease', 'Alpha')
    b.get('lowoff', 'PhoneLowOffset', 1200, 1200); b.get('readoff', 'PhoneReadOffset', 1200, 1350)
    b.fn('off', K + 'VLerp', 1500, 1200); b.link('lowoff', 'PhoneLowOffset', 'off', 'A'); b.link('readoff', 'PhoneReadOffset', 'off', 'B')
    b.link('ease', 'ReturnValue', 'off', 'Alpha')
    b.fn('now', GS + 'GetTimeSeconds', 1200, 1600)
    b.fn('rm', '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 1500, -100, Collection=MPC, ParameterName='ReduceMotion')
    b.link('done', 'else', 'rm', 'execute')
    b.fn('calm', K + 'Lerp', 1800, 1700, A=1.0, B=0.25); b.link('rm', 'ReturnValue', 'calm', 'Alpha')
    b.fn('bt', K + 'Multiply_DoubleDouble', 1500, 1600, B=1.35); b.link('now', 'ReturnValue', 'bt', 'A')
    b.fn('bsin', K + 'Sin', 1800, 1600); b.link('bt', 'ReturnValue', 'bsin', 'A')
    b.fn('bz', K + 'Multiply_DoubleDouble', 2100, 1600, B=0.4); b.link('bsin', 'ReturnValue', 'bz', 'A')
    b.fn('bz2', K + 'Multiply_DoubleDouble', 2400, 1600); b.link('bz', 'ReturnValue', 'bz2', 'A'); b.link('calm', 'ReturnValue', 'bz2', 'B')
    b.fn('sway', K + 'MakeVector', 2700, 1600, X=0.0, Y=0.0); b.link('bz2', 'ReturnValue', 'sway', 'Z')
    b.fn('local', K + 'Add_VectorVector', 3000, 1300); b.link('off', 'ReturnValue', 'local', 'A'); b.link('sway', 'ReturnValue', 'local', 'B')
    b.get('cam', 'FollowCamera', 1800, 1100)
    b.fn('camt', SC + 'K2_GetComponentToWorld', 2100, 1100); b.link('cam', 'FollowCamera', 'camt', 'self')
    b.fn('eye', SC + 'K2_GetComponentLocation', 2100, 1250); b.link('cam', 'FollowCamera', 'eye', 'self')
    b.fn('spos', K + 'TransformLocation', 3300, 1100); b.link('camt', 'ReturnValue', 'spos', 'T'); b.link('local', 'ReturnValue', 'spos', 'Location')
    b.fn('face', K + 'FindLookAtRotation', 3600, 1100); b.link('spos', 'ReturnValue', 'face', 'Start'); b.link('eye', 'ReturnValue', 'face', 'Target')
    b.fn('rt2', K + 'Multiply_DoubleDouble', 2100, 1800, B=0.9); b.link('now', 'ReturnValue', 'rt2', 'A')
    b.fn('rsin', K + 'Sin', 2400, 1800); b.link('rt2', 'ReturnValue', 'rsin', 'A')
    b.fn('roll', K + 'Multiply_DoubleDouble', 2700, 1800, B=0.6); b.link('rsin', 'ReturnValue', 'roll', 'A')
    b.fn('roll2', K + 'Multiply_DoubleDouble', 3000, 1800); b.link('roll', 'ReturnValue', 'roll2', 'A'); b.link('calm', 'ReturnValue', 'roll2', 'B')
    b.fn('inv', K + 'Subtract_DoubleDouble', 3000, 2000, A=1.0); b.link('ease', 'ReturnValue', 'inv', 'B')
    b.fn('dip', K + 'Multiply_DoubleDouble', 3300, 2000, B=-70.0); b.link('inv', 'ReturnValue', 'dip', 'A')
    b.fn('tilt', K + 'MakeRotator', 3600, 1800, Yaw=0.0); b.link('roll2', 'ReturnValue', 'tilt', 'Roll'); b.link('dip', 'ReturnValue', 'tilt', 'Pitch')
    b.fn('srot', K + 'ComposeRotators', 3900, 1300); b.link('tilt', 'ReturnValue', 'srot', 'A'); b.link('face', 'ReturnValue', 'srot', 'B')
    b.fn('st', K + 'MakeTransform', 4200, 1100, Scale='1,1,1'); b.link('spos', 'ReturnValue', 'st', 'Location'); b.link('srot', 'ReturnValue', 'st', 'Rotation')
    b.fn('pmesh', ACT + 'GetComponentByClass', 3300, 1500, ComponentClass='/Script/Engine.StaticMeshComponent')
    b.link('phone', 'PhoneActor', 'pmesh', 'self')
    b.node('smc', 'cast', 3600, -100, class_path='/Script/Engine.StaticMeshComponent'); b.link('pmesh', 'ReturnValue', 'smc', 'Object')
    b.link('rm', 'then', 'smc', 'execute')
    b.fn('srel', SC + 'GetSocketTransform', 3900, 1500, InSocketName='Screen', TransformSpace='RTS_Actor')
    b.link('smc', 'AsStatic Mesh Component', 'srel', 'self')
    b.fn('sinv', K + 'InvertTransform', 4200, 1500); b.link('srel', 'ReturnValue', 'sinv', 'T')
    b.fn('at', K + 'ComposeTransforms', 4500, 1300); b.link('sinv', 'ReturnValue', 'at', 'A'); b.link('st', 'ReturnValue', 'at', 'B')
    b.fn('place', ACT + 'K2_SetActorTransform', 3900, -100, bSweep='false', bTeleport='true')
    b.link('phone', 'PhoneActor', 'place', 'self'); b.link('at', 'ReturnValue', 'place', 'NewTransform'); b.chain('smc', 'place')
    # the left hand follows the screen frame
    b.get('wo', 'PhoneWristOffset', 4200, 1800)
    b.fn('wrist', K + 'TransformLocation', 4500, 1800); b.link('st', 'ReturnValue', 'wrist', 'T'); b.link('wo', 'PhoneWristOffset', 'wrist', 'Location')
    b.get('hr', 'PhoneHandRot', 4200, 2000)
    b.fn('hand', K + 'ComposeRotators', 4500, 2000); b.link('hr', 'PhoneHandRot', 'hand', 'A'); b.link('srot', 'ReturnValue', 'hand', 'B')
    b.get('eo', 'PhoneElbowOffset', 4200, 2200)
    b.fn('me', ACT + 'K2_GetActorRotation', 4200, 2350)
    b.fn('eow', K + 'GreaterGreater_VectorRotator', 4500, 2200); b.link('eo', 'PhoneElbowOffset', 'eow', 'A'); b.link('me', 'ReturnValue', 'eow', 'B')
    b.fn('elbow', K + 'Add_VectorVector', 4800, 2200); b.link('wrist', 'ReturnValue', 'elbow', 'A'); b.link('eow', 'ReturnValue', 'elbow', 'B')
    b.get('body', 'Body', 4200, 2550)
    b.fn('fpos', SC + 'GetSocketLocation', 4500, 2550, InSocketName='lowerarm_l'); b.link('body', 'Body', 'fpos', 'self')
    b.fn('shaft', K + 'Subtract_VectorVector', 4800, 2550); b.link('fpos', 'ReturnValue', 'shaft', 'A'); b.link('wrist', 'ReturnValue', 'shaft', 'B')
    b.fn('fx', K + 'GreaterGreater_VectorRotator', 4800, 2750, A='.63229227,-.09620717,.76873333'); b.link('hand', 'ReturnValue', 'fx', 'B')
    b.fn('pron', K + 'MakeRotFromYX', 5100, 2550); b.link('shaft', 'ReturnValue', 'pron', 'Y'); b.link('fx', 'ReturnValue', 'pron', 'X')
    b.fn('anim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 4500, 2950); b.link('body', 'Body', 'anim', 'self')
    b.node('mh', 'cast', 4200, -100, class_path=MC); b.link('anim', 'ReturnValue', 'mh', 'Object'); b.chain('place', 'mh')
    prev = 'mh'
    for i, (name, src) in enumerate((('EnvironmentHandTarget', ('wrist', 'ReturnValue')), ('EnvironmentElbowTarget', ('elbow', 'ReturnValue')),
                                     ('EnvironmentHandRotation', ('hand', 'ReturnValue')), ('EnvironmentHandWeight', ('ease', 'ReturnValue')),
                                     ('EnvironmentForearmRotation', ('pron', 'ReturnValue')))):
        r = 'w%d' % i
        b.set(r, name, 4500 + i * 300, -100, MC); b.link(src[0], src[1], r, name); b.link('mh', 'AsABP Fo APlayer MH', r, 'self')
        b.chain(prev, r); prev = r
    b.comment('Only while holding the phone', ['phone', 'has', 'held'])
    b.comment('Raise and lower', ['dt', 'r0', 'rt', 'step', 'r', 'ease'])
    b.comment('Put it away', ['low', 'away', 'gone', 'done', 'body0', 'anim0', 'mh0', 'release', 'ungrip', 'hide', 'forget'])
    b.comment('Screen in front of the eye', ['lowoff', 'readoff', 'off', 'now', 'rm', 'calm', 'bt', 'bsin', 'bz', 'bz2', 'sway', 'local', 'cam',
                                             'camt', 'eye', 'spos', 'face', 'rt2', 'rsin', 'roll', 'roll2', 'inv', 'dip', 'tilt', 'srot', 'st',
                                             'pmesh', 'smc', 'srel', 'sinv', 'at', 'place'])
    b.comment('Left hand on the phone', ['wo', 'wrist', 'hr', 'hand', 'eo', 'me', 'eow', 'elbow', 'body', 'fpos', 'shaft', 'fx', 'pron',
                                         'anim', 'mh', 'w0', 'w1', 'w2', 'w3', 'w4'])
    b.run()

# ---------------------------------------------------------------- Tick: UpdatePhoneHold after the camera update
nodes, edges = inspect(P, 'EventGraph')
if not any(nd['title'].replace(' ', '') == 'UpdatePhoneHold' for nd in nodes):
    fpv = next(nd['node_id'] for nd in nodes if nd['title'].replace(' ', '') == 'UpdateFirstPersonVisibility'
               and any(x['to_node'] == nd['node_id'] and x['to_pin'] == 'execute' for x in edges))
    after = [x for x in edges if x['from_node'] == fpv and x['from_pin'] == 'then']
    b = Batch(P, 'EventGraph')
    b.fn('phonehold', PC + ':UpdatePhoneHold', 900, 3600)
    for x in after:
        b.cut(fpv, 'then', x['to_node'], x['to_pin']); b.link('phonehold', 'then', x['to_node'], x['to_pin'])
    b.link(fpv, 'then', 'phonehold', 'execute')
    b.comment('Phone in the left hand', ['phonehold'])
    b.run()
print('PHONE_HOLD_BUILT')
