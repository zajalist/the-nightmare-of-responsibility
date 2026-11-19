"""BP_Jumpscare: the one jumpscare (docs/design/horror/jumpscare.md). Native Hayba graphs, no editor Python.
  $env:HAYBA_AGENT_ID='horror'; python Tools/Unreal/horror/build_jumpscare.py [assets|poll|dread|hit|animate|release|events|all]
Self-contained: its own trigger box, a 0.2 s poll timer (no Tick), reads BP_BeatDirector's public variables through
GetActorOfClass and calls only public APIs (BP_DreamDirector.TriggerGlitchBurst, BPL_SandFX.SpawnSandBurst).
Phase: 0 idle, 1 dread, 2 false calm, 3 hit, 5 done. bFired is set on the hit frame and never cleared.
Each graph is rebuilt in place (its nodes replaced, never the function), compiled and saved by one Hayba batch."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, find, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/Jumpscare/BP_Jumpscare'
C = P + '.BP_Jumpscare_C'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
DREAM_C = '/Game/FoA/PostProcess/BP_DreamDirector.BP_DreamDirector_C'
SANDFX = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C:SpawnSandBurst'
SHAKE = '/Game/FoA/Gameplay/Jumpscare/CS_Jumpscare.CS_Jumpscare_C'
SMX = '/Game/FoA/Audio/Mix/SMX_Jumpscare_Hush.SMX_Jumpscare_Hush'
STINGER = '/Game/FoA/Audio/SFX/Horror/SFX_Horror_Stinger_01.SFX_Horror_Stinger_01'  # the wave itself carries class and concurrency (wave_settings.py); no pitch variance on a timed hit
BED = '/Game/FoA/Audio/SFX/Horror/SFX_Horror_TensionBed_Loop_01.SFX_Horror_TensionBed_Loop_01'
TAIL = '/Game/FoA/Audio/MetaSounds/Dream/S_Dream_HeartbeatPanic.S_Dream_HeartbeatPanic'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
MESH = '/Game/FoA/Gameplay/Jumpscare/SM_Jumpscare_Monster.SM_Jumpscare_Monster'
MAT = '/Game/FoA/Gameplay/Jumpscare/MI_Jumpscare_Monster.MI_Jumpscare_Monster'
K = '/Script/Engine.KismetMathLibrary:'
KS = '/Script/Engine.KismetSystemLibrary:'
GS = '/Script/Engine.GameplayStatics:'
SC = '/Script/Engine.SceneComponent:'
AU = '/Script/Engine.AudioComponent:'
# Camera-space layout (cm, the player camera manager's frame: X forward, Y right, Z up). The Lux3D bust faces +Y,
# so yaw 90 turns its face to the lens; -10 z puts its eye line on the screen centre.
LUNGE_FROM, LUNGE_TO, EYE_Z, FACE_YAW = 95, 38, -10, 90
KEY_LIGHT, RIM_LIGHT = '10,12,-24', '50,-30,18'  # rim lowered from z 30: the skull top clipped hot in js8
HOLD, LUNGE_S, FOV_BACK_S = 0.65, 0.12, 0.9


def call(cmd, **params):
    r = h.call(cmd, params)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('failed'), d
    return d


def graph(name):
    ns, _ = inspect(P, name)
    e = find(ns, name)
    b = Batch(P, name)
    old = [n['node_id'] for n in ns if n['node_id'] != e]
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    return b, e


def compile_clean():
    c = h.call('blueprint_compile', {'path': P}).get('data') or {}
    ok = c.get('ok', True) and c.get('compiled', True) and not c.get('error_count', 0) and not c.get('warning_count', 0)
    return ok, {k: c.get(k) for k in ('error_count', 'warning_count', 'errors', 'warnings')}


def done(b, title):
    """One Hayba batch, compiled; saved only on a clean 0/0 compile. On failure its new nodes are removed and the Blueprint
    recompiled, so it never stays failing in memory (see BP_RoomAudio, 2026-11-09)."""
    b.comment(title, [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.ops.append(dict(op='fit_comments'))
    r = h.call('blueprint_graph_batch', dict(path=P, graph_name=b.graph, ops=b.ops, compile=True, save=False), timeout=120)
    d = r.get('data') or {}
    c = d.get('compile') or {}
    if (r.get('ok') and not d.get('compile_error') and c.get('ok', True) and c.get('compiled', True)
            and not c.get('error_count', 0) and not c.get('warning_count', 0)):
        call('asset_save', asset_paths=[P])
        print(b.graph, 'ok', d.get('applied'), '/', d.get('total'))
        return
    made = list((d.get('refs') or {}).values())
    if made:
        h.call('blueprint_remove_nodes', dict(path=P, graph_name=b.graph, node_ids=made))
    ok, summary = compile_clean()
    print(b.graph, 'FAILED, rolled back', len(made), 'nodes; recompile clean:', ok, summary, d.get('failed_index'),
          r.get('error') or d.get('error') or c.get('errors'))
    if ok:
        call('asset_save', asset_paths=[P])
    sys.exit(1)


def timer(b, ref, fn, x, y, t, loop=False):
    return b.fn(ref, KS + 'K2_SetTimer', x, y, FunctionName=fn, Time=t, bLooping=str(loop).lower())


def clear(b, ref, fn, x, y):
    return b.fn(ref, KS + 'K2_ClearTimer', x, y, FunctionName=fn)


def now(b, ref, x, y):
    return b.fn(ref, GS + 'GetTimeSeconds', x, y)


def setv(b, ref, var, x, y, value):
    b.set(ref, var, x, y)
    b.pin(ref, var, value)
    return ref


def math(b, ref, fn, x, y, a, ap='ReturnValue', **pins):
    """Binary math node with input A wired from (a, ap) and the other pins as constants."""
    b.fn(ref, K + fn, x, y, **pins)
    b.link(a, ap, ref, 'A')
    return ref


def assets():
    if not h.call('blueprint_get_info', {'path': P}).get('ok'):
        call('blueprint_create', name='BP_Jumpscare', package_path=P, parent_class_path='/Script/Engine.Actor')
    info = call('blueprint_get_info', path=P)
    have = {x['name'] for x in info['components']}
    for name, cls in [('Root', 'SceneComponent'), ('Zone', 'BoxComponent'), ('Monster', 'StaticMeshComponent'),
                      ('FaceLight', 'PointLightComponent'), ('RimLight', 'PointLightComponent'), ('Bed', 'AudioComponent')]:
        if name not in have:
            call('blueprint_add_component', path=P, component_name=name, component_class_path='/Script/Engine.' + cls)
    g = C + ':{}_GEN_VARIABLE'
    call('object_set_property', path=g.format('Zone'), properties={
        'BoxExtent': '(X=70,Y=85,Z=100)', 'bHiddenInGame': True, 'bGenerateOverlapEvents': True,
        'BodyInstance': '(CollisionProfileName="Trigger")'})
    call('object_set_property', path=g.format('Monster'), properties={
        'StaticMesh': MESH, 'OverrideMaterials': [MAT], 'bVisible': False, 'CastShadow': False,
        'bGenerateOverlapEvents': False, 'Mobility': 'Movable', 'bRenderCustomDepth': True, 'CustomDepthStencilValue': 200,  # 200: the time echo skips it (exact compare, world lane)
        'LightingChannels': '(bChannel0=True,bChannel1=True,bChannel2=False)',
        'BodyInstance': '(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'})
    for name, cd in (('FaceLight', 0.12), ('RimLight', 7.5)):  # js3 2.5/40 and js7 0.35/20 overexposed it in the dark room
        call('object_set_property', path=g.format(name), properties={
            'Intensity': cd, 'IntensityUnits': 'Candelas', 'AttenuationRadius': 90.0, 'CastShadows': False,
            'SourceRadius': 6.0, 'VolumetricScatteringIntensity': 0.0, 'bVisible': False, 'Mobility': 'Movable',
            'LightingChannels': '(bChannel0=False,bChannel1=True,bChannel2=False)'})  # light the monster only, never the pawn or room
    call('object_set_property', path=g.format('Bed'), properties={
        'Sound': BED, 'bAutoActivate': False, 'bAllowSpatialization': False})
    variables = [('Director', 'object:' + DIR_C, ''), ('Dream', 'object:' + DREAM_C, ''),
                 ('Camera', 'object:/Script/Engine.CameraComponent', ''), ('Phase', 'int', '0'), ('bFired', 'bool', 'false'),
                 ('LastBeat', 'int', '-1'), ('BeatStart', 'float', '0'), ('PhaseStart', 'float', '0'), ('HitTime', 'float', '0'),
                 ('BaseFOV', 'float', '90'), ('FOVPunch', 'float', '12'), ('ShakeScale', 'float', '1'),
                 ('Tail', 'object:/Script/Engine.AudioComponent', '')]
    for n, t, v in variables:
        call('blueprint_add_variable', path=P, variable_name=n, variable_type=t, default_value=v, instance_editable=False,
             update_existing=True, category='Jumpscare')
    for fn in ('Poll', 'StartDread', 'StartCalm', 'PlayStinger', 'Reveal', 'Animate', 'Release', 'Cancel', 'EndTail'):
        if fn not in info['functions']:
            call('blueprint_add_function', path=P, function_name=fn)
    ok, summary = compile_clean()
    assert ok, ('BP_Jumpscare does not compile clean after the asset step', summary)
    call('asset_save', asset_paths=[P])


def poll():
    b, e = graph('Poll')
    # Director and beat age
    b.fn('find', GS + 'GetActorOfClass', 0, 300, ActorClass=DIR_C)
    b.set('keep', 'Director', 250, 0)
    b.link('find', 'ReturnValue', 'keep', 'Director')
    b.get('dir', 'Director', 250, 300)
    b.fn('valid', KS + 'IsValid', 500, 300)
    b.link('dir', 'Director', 'valid', 'Object')
    b.node('hasDir', 'branch', 500, 0)
    b.link('valid', 'ReturnValue', 'hasDir', 'Condition')
    b.get('beat', 'BeatIndex', 750, 300, DIR_C)
    b.link('dir', 'Director', 'beat', 'self')
    b.get('last', 'LastBeat', 750, 450)
    b.fn('changed', K + 'NotEqual_IntInt', 1000, 300)
    b.link('beat', 'BeatIndex', 'changed', 'A')
    b.link('last', 'LastBeat', 'changed', 'B')
    b.node('newBeat', 'branch', 1000, 0)
    b.link('changed', 'ReturnValue', 'newBeat', 'Condition')
    b.set('saveBeat', 'LastBeat', 1250, -150)
    b.link('beat', 'BeatIndex', 'saveBeat', 'LastBeat')
    now(b, 'now', 1250, 300)
    b.set('saveStart', 'BeatStart', 1500, -150)
    b.link('now', 'ReturnValue', 'saveStart', 'BeatStart')
    b.chain(e, 'find', 'keep', 'hasDir')  # impure nodes must sit on the exec path
    b.link('hasDir', 'then', 'newBeat', 'execute')
    b.chain('newBeat', 'saveBeat', 'saveStart')
    # Gate: the player's own view, no rollover, top-down or wardrobe scene, not fired yet
    x = 1800
    b.fn('pawn', GS + 'GetPlayerPawn', x, 600, PlayerIndex=0)
    b.fn('pc', GS + 'GetPlayerController', x, 750, PlayerIndex=0)
    b.fn('view', '/Script/Engine.Controller:GetViewTarget', x + 250, 750)
    b.link('pc', 'ReturnValue', 'view', 'self')
    b.fn('isPawnView', K + 'EqualEqual_ObjectObject', x + 500, 650)
    b.link('view', 'ReturnValue', 'isPawnView', 'A')
    b.link('pawn', 'ReturnValue', 'isPawnView', 'B')
    for i, var in enumerate(('bRollingOver', 'bTopDown', 'bWardrobeTransition')):
        b.get(var, var, x, 900 + i * 120, DIR_C)
        b.link('dir', 'Director', var, 'self')
    b.fn('busyA', K + 'BooleanOR', x + 250, 950)
    b.link('bRollingOver', 'bRollingOver', 'busyA', 'A')
    b.link('bTopDown', 'bTopDown', 'busyA', 'B')
    b.fn('busy', K + 'BooleanOR', x + 500, 1000)
    b.link('busyA', 'ReturnValue', 'busy', 'A')
    b.link('bWardrobeTransition', 'bWardrobeTransition', 'busy', 'B')
    b.get('fired', 'bFired', x + 500, 1150)
    b.fn('blocked', K + 'BooleanOR', x + 750, 1050)
    b.link('busy', 'ReturnValue', 'blocked', 'A')
    b.link('fired', 'bFired', 'blocked', 'B')
    b.fn('free', K + 'Not_PreBool', x + 1000, 1050)
    b.link('blocked', 'ReturnValue', 'free', 'A')
    b.fn('gate', K + 'BooleanAND', x + 1250, 800)
    b.link('isPawnView', 'ReturnValue', 'gate', 'A')
    b.link('free', 'ReturnValue', 'gate', 'B')
    # Window T4-T5, the zone, ages
    b.fn('is4', K + 'EqualEqual_IntInt', x, 1300, B=4)
    b.link('beat', 'BeatIndex', 'is4', 'A')
    b.fn('is5', K + 'EqualEqual_IntInt', x, 1450, B=5)
    b.link('beat', 'BeatIndex', 'is5', 'A')
    b.fn('inWin', K + 'BooleanOR', x + 250, 1350)
    b.link('is4', 'ReturnValue', 'inWin', 'A')
    b.link('is5', 'ReturnValue', 'inWin', 'B')
    b.fn('ok', K + 'BooleanAND', x + 1500, 900)
    b.link('gate', 'ReturnValue', 'ok', 'A')
    b.link('inWin', 'ReturnValue', 'ok', 'B')
    b.get('zone', 'Zone', x, 1600)
    b.fn('inZone', '/Script/Engine.PrimitiveComponent:IsOverlappingActor', x + 250, 1600)
    b.link('zone', 'Zone', 'inZone', 'self')
    b.link('pawn', 'ReturnValue', 'inZone', 'Other')
    b.fn('outZone', K + 'Not_PreBool', x + 500, 1600)
    b.link('inZone', 'ReturnValue', 'outZone', 'A')
    b.get('start', 'BeatStart', x, 1750)
    b.fn('beatAge', K + 'Subtract_DoubleDouble', x + 250, 1750)
    b.link('now', 'ReturnValue', 'beatAge', 'A')
    b.link('start', 'BeatStart', 'beatAge', 'B')
    b.get('pstart', 'PhaseStart', x, 1900)
    b.fn('dreadAge', K + 'Subtract_DoubleDouble', x + 250, 1900)
    b.link('now', 'ReturnValue', 'dreadAge', 'A')
    b.link('pstart', 'PhaseStart', 'dreadAge', 'B')
    # Phase 0 -> dread: in the window, in the zone, the beat at least 1.5 s old
    math(b, 'settled', 'GreaterEqual_DoubleDouble', x + 500, 1750, 'beatAge', B=1.5)
    b.fn('armA', K + 'BooleanAND', x + 1750, 1000)
    b.link('ok', 'ReturnValue', 'armA', 'A')
    b.link('inZone', 'ReturnValue', 'armA', 'B')
    b.fn('arm', K + 'BooleanAND', x + 2000, 1100)
    b.link('armA', 'ReturnValue', 'arm', 'A')
    b.link('settled', 'ReturnValue', 'arm', 'B')
    # Phase 1 -> false calm: T5 at least 2.5 s old (the snap played out) and the player left the door, or 10 s passed
    math(b, 'snapped', 'GreaterEqual_DoubleDouble', x + 500, 1850, 'beatAge', B=2.5)
    math(b, 'longDread', 'GreaterEqual_DoubleDouble', x + 500, 1950, 'dreadAge', B=10)
    b.fn('leaving', K + 'BooleanOR', x + 750, 1700)
    b.link('outZone', 'ReturnValue', 'leaving', 'A')
    b.link('longDread', 'ReturnValue', 'leaving', 'B')
    b.fn('calmA', K + 'BooleanAND', x + 1000, 1500)
    b.link('is5', 'ReturnValue', 'calmA', 'A')
    b.link('snapped', 'ReturnValue', 'calmA', 'B')
    b.fn('calm', K + 'BooleanAND', x + 1250, 1600)
    b.link('calmA', 'ReturnValue', 'calm', 'A')
    b.link('leaving', 'ReturnValue', 'calm', 'B')
    b.fn('earlyLeave', K + 'BooleanAND', x + 1250, 1400)
    b.link('is4', 'ReturnValue', 'earlyLeave', 'A')
    b.link('outZone', 'ReturnValue', 'earlyLeave', 'B')
    b.fn('notOk', K + 'Not_PreBool', x + 1750, 1250)
    b.link('ok', 'ReturnValue', 'notOk', 'A')
    # Phase switch as branches (exec joins after the beat bookkeeping)
    b.get('phase', 'Phase', x + 2000, 300)
    for i, ref in enumerate(('p0', 'p1', 'p2')):
        b.fn(ref, K + 'EqualEqual_IntInt', x + 2250, 300 + i * 120, B=i)
        b.link('phase', 'Phase', ref, 'A')
    X = x + 2600
    b.node('isIdle', 'branch', X, 0)
    b.link('p0', 'ReturnValue', 'isIdle', 'Condition')
    b.link('newBeat', 'else', 'isIdle', 'execute')
    b.link('saveStart', 'then', 'isIdle', 'execute')
    b.node('canArm', 'branch', X + 250, -200)
    b.link('arm', 'ReturnValue', 'canArm', 'Condition')
    b.fn('dread', C + ':StartDread', X + 500, -200)
    b.chain('isIdle', 'canArm', 'dread')
    b.node('isDread', 'branch', X + 250, 150)
    b.link('p1', 'ReturnValue', 'isDread', 'Condition')
    b.link('isIdle', 'else', 'isDread', 'execute')
    b.node('lostA', 'branch', X + 500, 50)
    b.link('notOk', 'ReturnValue', 'lostA', 'Condition')
    b.fn('cancelA', C + ':Cancel', X + 750, -50)
    b.chain('isDread', 'lostA', 'cancelA')
    b.node('toCalm', 'branch', X + 750, 150)
    b.link('calm', 'ReturnValue', 'toCalm', 'Condition')
    b.link('lostA', 'else', 'toCalm', 'execute')
    b.fn('startCalm', C + ':StartCalm', X + 1000, 100)
    b.chain('toCalm', 'startCalm')
    b.node('leftEarly', 'branch', X + 1000, 300)
    b.link('earlyLeave', 'ReturnValue', 'leftEarly', 'Condition')
    b.link('toCalm', 'else', 'leftEarly', 'execute')
    b.fn('cancelB', C + ':Cancel', X + 1250, 300)
    b.chain('leftEarly', 'cancelB')
    b.node('isCalm', 'branch', X + 500, 450)
    b.link('p2', 'ReturnValue', 'isCalm', 'Condition')
    b.link('isDread', 'else', 'isCalm', 'execute')
    b.node('lostB', 'branch', X + 750, 450)
    b.link('notOk', 'ReturnValue', 'lostB', 'Condition')
    b.fn('cancelC', C + ':Cancel', X + 1000, 450)
    b.chain('isCalm', 'lostB', 'cancelC')
    done(b, 'Watch the door after the key snaps')


def dread():
    b, e = graph('StartDread')
    setv(b, 'phase', 'Phase', 250, 0, 1)
    now(b, 'now', 250, 250)
    b.set('start', 'PhaseStart', 500, 0)
    b.link('now', 'ReturnValue', 'start', 'PhaseStart')
    b.fn('hush', GS + 'PushSoundMixModifier', 750, 0, InSoundMixModifier=SMX)
    b.get('bed', 'Bed', 1000, 250)
    b.fn('swell', AU + 'FadeIn', 1000, 0, FadeInDuration=4, FadeVolumeLevel=0.8, StartTime=0)
    b.link('bed', 'Bed', 'swell', 'self')
    b.chain(e, 'phase', 'start', 'hush', 'swell')
    done(b, 'Dread at the dead door')

    b, e = graph('StartCalm')
    setv(b, 'phase', 'Phase', 250, 0, 2)
    b.get('bed', 'Bed', 500, 250)
    b.fn('drop', AU + 'FadeOut', 500, 0, FadeOutDuration=0.6, FadeVolumeLevel=0)
    b.link('bed', 'Bed', 'drop', 'self')
    b.fn('wait', K + 'RandomFloatInRange', 750, 250, Min=1.2, Max=1.9)
    timer(b, 'later', 'PlayStinger', 750, 0, 1.5)
    b.link('wait', 'ReturnValue', 'later', 'Time')
    b.chain(e, 'phase', 'drop', 'later')
    done(b, 'False calm')

    b, e = graph('PlayStinger')
    b.fn('sting', GS + 'PlaySound2D', 250, 0, Sound=STINGER, VolumeMultiplier=1)
    timer(b, 'hit', 'Reveal', 500, 0, 0.40)  # the stinger file's riser is 0.40 s long: the hit lands with the reveal
    b.chain(e, 'sting', 'hit')
    done(b, 'Riser into the hit')

    b, e = graph('Cancel')
    clear(b, 'c1', 'PlayStinger', 250, 0)
    clear(b, 'c2', 'Reveal', 500, 0)
    b.get('bed', 'Bed', 750, 250)
    b.fn('fade', AU + 'FadeOut', 750, 0, FadeOutDuration=1.5, FadeVolumeLevel=0)
    b.link('bed', 'Bed', 'fade', 'self')
    b.fn('unhush', GS + 'PopSoundMixModifier', 1000, 0, InSoundMixModifier=SMX)
    setv(b, 'phase', 'Phase', 1250, 0, 0)
    b.chain(e, 'c1', 'c2', 'fade', 'unhush', 'phase')
    done(b, 'Stand down, still armed')


def attach(b, ref, comp, parent_ref, parent_pin, x, y):
    b.get(ref + 'C', comp, x, y + 250)
    b.fn(ref, SC + 'K2_AttachToComponent', x, y, LocationRule='KeepRelative', RotationRule='KeepRelative',
         ScaleRule='KeepRelative', bWeldSimulatedBodies='false')
    b.link(ref + 'C', comp, ref, 'self')
    b.link(parent_ref, parent_pin, ref, 'Parent')
    return ref


def show(b, ref, comp, x, y, on):
    b.get(ref + 'C', comp, x, y + 250)
    b.fn(ref, SC + 'SetVisibility', x, y, bNewVisibility=str(on).lower(), bPropagateToChildren='false')
    b.link(ref + 'C', comp, ref, 'self')
    return ref


def hit():
    b, e = graph('Reveal')
    setv(b, 'phase', 'Phase', 250, 0, 3)
    setv(b, 'fired', 'bFired', 500, 0, 'true')
    now(b, 'now', 500, 250)
    b.set('t0', 'HitTime', 750, 0)
    b.link('now', 'ReturnValue', 't0', 'HitTime')
    b.fn('pcm', GS + 'GetPlayerCameraManager', 750, 300, PlayerIndex=0)
    b.fn('lens', '/Script/Engine.Actor:K2_GetRootComponent', 1000, 300)
    b.link('pcm', 'ReturnValue', 'lens', 'self')
    attach(b, 'aM', 'Monster', 'lens', 'ReturnValue', 1000, 0)
    attach(b, 'aK', 'FaceLight', 'lens', 'ReturnValue', 1250, 0)
    attach(b, 'aR', 'RimLight', 'lens', 'ReturnValue', 1500, 0)
    b.get('mon', 'Monster', 1750, 300)
    b.fn('pose', SC + 'K2_SetRelativeLocationAndRotation', 1750, 0, NewLocation=f'{LUNGE_FROM},0,{EYE_Z}',
         NewRotation=f'0,{FACE_YAW},0', bSweep='false', bTeleport='true')
    b.link('mon', 'Monster', 'pose', 'self')
    for i, (comp, loc) in enumerate((('FaceLight', KEY_LIGHT), ('RimLight', RIM_LIGHT))):
        r = 'place' + comp
        b.get(r + 'C', comp, 2000 + i * 250, 300)
        b.fn(r, SC + 'K2_SetRelativeLocation', 2000 + i * 250, 0, NewLocation=loc, bSweep='false', bTeleport='true')
        b.link(r + 'C', comp, r, 'self')
    show(b, 'vM', 'Monster', 2500, 0, True)
    show(b, 'vK', 'FaceLight', 2750, 0, True)
    show(b, 'vR', 'RimLight', 3000, 0, True)
    # The over-the-shoulder camera puts the pawn closer to the lens than the monster: hide it for the hold only
    b.fn('pawnH', GS + 'GetPlayerPawn', 3100, 450, PlayerIndex=0)
    b.fn('hidePawn', '/Script/Engine.Actor:SetActorHiddenInGame', 3100, -150, bNewHidden='true')
    b.link('pawnH', 'ReturnValue', 'hidePawn', 'self')
    # Reduce motion: 0.3x shake, no FOV punch
    b.fn('rm', '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 3250, 300, Collection=MPC, ParameterName='ReduceMotion')
    math(b, 'calm', 'Greater_DoubleDouble', 3500, 300, 'rm', B=0.5)
    b.fn('scale', K + 'SelectFloat', 3750, 300, A=0.3, B=1.0)
    b.link('calm', 'ReturnValue', 'scale', 'bPickA')
    b.set('keepScale', 'ShakeScale', 3750, 0)
    b.link('scale', 'ReturnValue', 'keepScale', 'ShakeScale')
    b.fn('punch', K + 'SelectFloat', 4000, 300, A=0.0, B=12.0)
    b.link('calm', 'ReturnValue', 'punch', 'bPickA')
    b.set('keepPunch', 'FOVPunch', 4000, 0)
    b.link('punch', 'ReturnValue', 'keepPunch', 'FOVPunch')
    b.fn('shake', '/Script/Engine.PlayerCameraManager:StartCameraShake', 4250, 0, ShakeClass=SHAKE)
    b.link('pcm', 'ReturnValue', 'shake', 'self')
    b.link('scale', 'ReturnValue', 'shake', 'Scale')
    # The pawn's camera for the FOV punch
    b.fn('pawn', GS + 'GetPlayerPawn', 4500, 300, PlayerIndex=0)
    b.fn('cam', '/Script/Engine.Actor:GetComponentByClass', 4750, 300, ComponentClass='/Script/Engine.CameraComponent')
    b.link('pawn', 'ReturnValue', 'cam', 'self')
    b.set('keepCam', 'Camera', 4750, 0)
    b.link('cam', 'ReturnValue', 'keepCam', 'Camera')
    b.get('camV', 'Camera', 5000, 300)
    b.fn('camOk', KS + 'IsValid', 5000, 450)
    b.link('camV', 'Camera', 'camOk', 'Object')
    b.node('hasCam', 'branch', 5000, 0)
    b.link('camOk', 'ReturnValue', 'hasCam', 'Condition')
    b.get('fov', 'FieldOfView', 5250, 300, '/Script/Engine.CameraComponent')
    b.link('camV', 'Camera', 'fov', 'self')
    b.set('keepFov', 'BaseFOV', 5250, 0)
    b.link('fov', 'FieldOfView', 'keepFov', 'BaseFOV')
    # The DreamDirector for the post-process hit on the cut (Release); the hit frame itself stays clean so the face reads
    b.fn('findDream', GS + 'GetActorOfClass', 5500, 300, ActorClass=DREAM_C)
    b.set('keepDream', 'Dream', 5500, 0)
    b.link('findDream', 'ReturnValue', 'keepDream', 'Dream')
    b.link('hasCam', 'else', 'findDream', 'execute')
    timer(b, 'anim', 'Animate', 6500, 0, 0.01, True)
    timer(b, 'end', 'Release', 6750, 0, HOLD)
    b.chain(e, 'phase', 'fired', 't0', 'aM', 'aK', 'aR', 'pose', 'placeFaceLight', 'placeRimLight', 'vM', 'vK', 'vR',
            'hidePawn', 'rm', 'keepScale', 'keepPunch', 'shake', 'keepCam', 'hasCam', 'keepFov', 'findDream', 'keepDream', 'anim', 'end')
    done(b, 'The face in the lens')


def animate():
    b, e = graph('Animate')
    now(b, 'now', 0, 300)
    b.get('t0', 'HitTime', 0, 450)
    b.fn('t', K + 'Subtract_DoubleDouble', 250, 300)
    b.link('now', 'ReturnValue', 't', 'A')
    b.link('t0', 'HitTime', 't', 'B')
    # Lunge: ease out from LUNGE_FROM to LUNGE_TO over LUNGE_S, then a fast tremble
    math(b, 'la', 'Divide_DoubleDouble', 500, 300, 't', B=LUNGE_S)
    b.fn('lc', K + 'FClamp', 750, 300, Min=0, Max=1)
    b.link('la', 'ReturnValue', 'lc', 'Value')
    b.fn('le', K + 'Ease', 1000, 300, A=0, B=1, EasingFunc='EaseOut', BlendExp=2.5, Steps=2)
    b.link('lc', 'ReturnValue', 'le', 'Alpha')
    b.fn('dist', K + 'Lerp', 1250, 300, A=LUNGE_FROM, B=LUNGE_TO)
    b.link('le', 'ReturnValue', 'dist', 'Alpha')
    trem = []
    for i, (freq, amp) in enumerate(((95, 1.5), (71, 1.5), (53, 3.0))):
        r = 'w' + str(i)
        math(b, r, 'Multiply_DoubleDouble', 500, 500 + i * 150, 't', B=freq)
        b.fn(r + 's', K + 'Sin', 750, 500 + i * 150)
        b.link(r, 'ReturnValue', r + 's', 'A')
        math(b, r + 'a', 'Multiply_DoubleDouble', 1000, 500 + i * 150, r + 's', B=amp)
        trem.append(r + 'a')
    b.fn('d', K + 'Add_DoubleDouble', 1500, 300)
    b.link('dist', 'ReturnValue', 'd', 'A')
    b.link(trem[0], 'ReturnValue', 'd', 'B')
    b.fn('loc', K + 'MakeVector', 1750, 300, Y=0, Z=EYE_Z)
    b.link('d', 'ReturnValue', 'loc', 'X')
    b.fn('rot', K + 'MakeRotator', 1750, 500, Yaw=FACE_YAW)
    b.link(trem[1], 'ReturnValue', 'rot', 'Pitch')
    b.link(trem[2], 'ReturnValue', 'rot', 'Roll')
    b.get('phase', 'Phase', 1750, 700)
    b.fn('holding', K + 'EqualEqual_IntInt', 2000, 700, B=3)
    b.link('phase', 'Phase', 'holding', 'A')
    b.node('isHold', 'branch', 2000, 0)
    b.link('holding', 'ReturnValue', 'isHold', 'Condition')
    b.get('mon', 'Monster', 2250, 300)
    b.fn('pose', SC + 'K2_SetRelativeLocationAndRotation', 2250, 0, bSweep='false', bTeleport='true')
    b.link('mon', 'Monster', 'pose', 'self')
    b.link('loc', 'ReturnValue', 'pose', 'NewLocation')
    b.link('rot', 'ReturnValue', 'pose', 'NewRotation')
    # FOV: punched in on the hit frame, eased back (squared) over FOV_BACK_S
    math(b, 'fa', 'Divide_DoubleDouble', 2500, 450, 't', B=FOV_BACK_S)
    b.fn('fc', K + 'FClamp', 2750, 450, Min=0, Max=1)
    b.link('fa', 'ReturnValue', 'fc', 'Value')
    b.fn('fk', K + 'Subtract_DoubleDouble', 3000, 450, A=1)
    b.link('fc', 'ReturnValue', 'fk', 'B')
    b.fn('fk2', K + 'Multiply_DoubleDouble', 3250, 450)
    b.link('fk', 'ReturnValue', 'fk2', 'A')
    b.link('fk', 'ReturnValue', 'fk2', 'B')
    b.get('punch', 'FOVPunch', 3250, 600)
    b.fn('fp', K + 'Multiply_DoubleDouble', 3500, 450)
    b.link('fk2', 'ReturnValue', 'fp', 'A')
    b.link('punch', 'FOVPunch', 'fp', 'B')
    b.get('base', 'BaseFOV', 3500, 600)
    b.fn('fov', K + 'Subtract_DoubleDouble', 3750, 450)
    b.link('base', 'BaseFOV', 'fov', 'A')
    b.link('fp', 'ReturnValue', 'fov', 'B')
    b.get('cam', 'Camera', 3750, 300)
    b.fn('camOk', KS + 'IsValid', 3750, 650)
    b.link('cam', 'Camera', 'camOk', 'Object')
    b.node('hasCam', 'branch', 3750, 0)
    b.link('camOk', 'ReturnValue', 'hasCam', 'Condition')
    b.link('isHold', 'then', 'pose', 'execute')
    b.link('pose', 'then', 'hasCam', 'execute')
    b.link('isHold', 'else', 'hasCam', 'execute')
    b.fn('setFov', '/Script/Engine.CameraComponent:SetFieldOfView', 4000, -150)
    b.link('cam', 'Camera', 'setFov', 'self')
    b.link('fov', 'ReturnValue', 'setFov', 'InFieldOfView')
    math(b, 'over', 'GreaterEqual_DoubleDouble', 4250, 450, 't', B=FOV_BACK_S)
    b.node('isOver', 'branch', 4250, 0)
    b.link('over', 'ReturnValue', 'isOver', 'Condition')
    b.link('setFov', 'then', 'isOver', 'execute')
    b.link('hasCam', 'else', 'isOver', 'execute')
    clear(b, 'stop', 'Animate', 4500, 0)
    b.chain(e, 'isHold')
    b.chain('hasCam', 'setFov')
    b.chain('isOver', 'stop')
    done(b, 'Lunge, tremble, FOV back')


def release():
    b, e = graph('Release')
    b.get('mon', 'Monster', 250, 300)
    b.fn('where', SC + 'K2_GetComponentLocation', 250, 450)
    b.link('mon', 'Monster', 'where', 'self')
    setv(b, 'phase', 'Phase', 250, 0, 5)
    show(b, 'hM', 'Monster', 500, 0, False)
    show(b, 'hK', 'FaceLight', 750, 0, False)
    show(b, 'hR', 'RimLight', 1000, 0, False)
    b.fn('pawnS', GS + 'GetPlayerPawn', 1100, 450, PlayerIndex=0)
    b.fn('showPawn', '/Script/Engine.Actor:SetActorHiddenInGame', 1100, -150, bNewHidden='false')
    b.link('pawnS', 'ReturnValue', 'showPawn', 'self')
    b.get('dream', 'Dream', 1250, 300)
    b.fn('dreamOk', KS + 'IsValid', 1250, 450)
    b.link('dream', 'Dream', 'dreamOk', 'Object')
    b.node('hasDream', 'branch', 1250, 0)
    b.link('dreamOk', 'ReturnValue', 'hasDream', 'Condition')
    b.fn('glitch', DREAM_C + ':TriggerGlitchBurst', 1500, -150, Strength=0.6, Seconds=0.2)  # a short tear on the cut; js3's 0.45 s smeared the release
    b.link('dream', 'Dream', 'glitch', 'self')
    b.fn('burst', SANDFX, 1750, 0, Scale=0.8)
    b.link('where', 'ReturnValue', 'burst', 'Location')
    b.link('hasDream', 'else', 'burst', 'execute')
    b.get('root', 'Root', 2000, 450)
    attach(b, 'bM', 'Monster', 'root', 'Root', 2000, 0)
    attach(b, 'bK', 'FaceLight', 'root', 'Root', 2250, 0)
    attach(b, 'bR', 'RimLight', 'root', 'Root', 2500, 0)
    b.fn('unhush', GS + 'PopSoundMixModifier', 2750, 0, InSoundMixModifier=SMX)
    b.fn('tail', GS + 'SpawnSound2D', 3000, 300, Sound=TAIL, VolumeMultiplier=0.6, bAutoDestroy='true')
    b.set('keepTail', 'Tail', 3000, 0)
    b.link('tail', 'ReturnValue', 'keepTail', 'Tail')
    b.fn('fadeLater', '/Script/Engine.KismetSystemLibrary:K2_SetTimer', 3250, 0, FunctionName='EndTail', Time=3.0,
         bLooping='false')
    b.chain(e, 'phase', 'hM', 'hK', 'hR', 'showPawn', 'hasDream', 'glitch', 'burst', 'bM', 'bK', 'bR', 'unhush', 'tail',
            'keepTail', 'fadeLater')
    done(b, 'Hard cut to the room')
    # the heartbeat tail fades out over 4 s, 3 s after the cut (au3: the 20 s panic heartbeat ran on to T10)
    b, e = graph('EndTail')
    b.get('tailV', 'Tail', 0, 250)
    b.fn('valid', '/Script/Engine.KismetSystemLibrary:IsValid', 250, 250)
    b.link('tailV', 'Tail', 'valid', 'Object')
    b.node('has', 'branch', 250, 0)
    b.link('valid', 'ReturnValue', 'has', 'Condition')
    b.fn('fade', AU + 'FadeOut', 500, 0, FadeOutDuration=4.0, FadeVolumeLevel=0)
    b.link('tailV', 'Tail', 'fade', 'self')
    b.chain(e, 'has', 'fade')
    done(b, 'Let the heartbeat go')


def events():
    b = Batch(P, 'EventGraph')
    ns, _ = inspect(P, 'EventGraph')
    if ns:
        b.ops.append(dict(op='remove', node_ids=[n['node_id'] for n in ns]))
    b.ops.append(dict(op='add_event', ref='begin', event_name='ReceiveBeginPlay', x=0, y=0))
    timer(b, 'poll', 'Poll', 300, 0, 0.2, True)
    b.chain('begin', 'poll')
    done(b, 'Watch from the start')


STEPS = {'assets': assets, 'poll': poll, 'dread': dread, 'hit': hit, 'animate': animate, 'release': release, 'events': events}

if __name__ == '__main__':
    assert not call('editor_get_state')['pie_running'], 'PIE is running: wait'
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    lease = h.lease_acquire(h.agent_id(), ['asset:' + P], ttl_s=180, wait_s=60)
    try:
        for name, step in STEPS.items():
            if which in ('all', name):
                step()
    finally:
        h.release(h.agent_id(), lease)
