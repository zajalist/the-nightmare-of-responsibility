"""Level 2 ending, redesigned for clarity and payoff (level2 lane, 2026-11-18).

The interview's last question gets the answer "I'll be there." Then:
  separation  his black-sand double across the desk (the Nightmare in his own shape) falls apart: its head, then its
              hands crumble away in grains, three sand bursts, the empty suit goes last; the stage camera eases in and
              MUS_Ending (BP_RoomAudio 'Ending') starts. 4.6 s.
  card        black, the house time-card: "First shift" / "Monday   06:00". 2.6 s.
  wake        the real bedroom in colour (LS_L2RealWake), the alarm rings and is switched off, he sits up,
              "I'm up." (his unsent draft from Level 1, now said). Then the credits roll (unchanged hand-off).
Owned graphs only: BP_L2Journey (Submit, StartSeparation, TickSeparation, SeparationBurst, EndSeparation),
BP_DreamThreshold (BeginEnding, EndingColour, EndingWake, StopWakeAlarm, ShowEndLine, FadeWakeToCredits,
RestoreWakeLook) and WBP_L2ShiftTimeCard (one TextBlock, TimeLine).
  python -B build_l2_ending.py selftest | declare | card | journey | threshold
Each editor step takes its own short lease and compiles and saves in the same batch."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = '/Game/FoA/Level2'
JOURNEY = ROOT + '/Journey/BP_L2Journey'
STOPSET = ROOT + '/Journey/BP_L2StopSet'
CARD = ROOT + '/Journey/WBP_L2ShiftTimeCard'
THRESHOLD = ROOT + '/Transition/BP_DreamThreshold'
GI = '/Game/FoA/Gameplay/GI_FoA'
SAND = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C:SpawnSandBurst'
ALARM = '/Game/FoA/Audio/SFX/Clock/SFX_Clock_AlarmRing_Loop_01.SFX_Clock_AlarmRing_Loop_01'
ALARM_OFF = '/Game/FoA/Audio/SFX/Clock/SFX_Clock_AlarmMechanism_01.SFX_Clock_AlarmMechanism_01'

# Separation timing (seconds from "I'll be there."). The shell material reads Amount 1 = all black, 0 = gone; under the
# suit only the head (0.6..0.4) and the hands (0.2..0) show, so the head goes first and the hands last.
DRAIN_START, DRAIN = .5, 2.2
BURST_FIRST, BURST_GAP, BURSTS = .5, 1.125, 3
BURST_HEIGHT, BURST_SCALE = (120., 165., 115.), (1.1, .9, 2.2)  # the last one hides the suit going
FOV_FROM, FOV_TO = 58., 47.
SEPARATION = 4.6
CARD_SECONDS = 2.6
CARD_TITLE, CARD_CLOCK = 'First shift', 'Monday   06:00'
ALARM_SECONDS, LINE_AT = 2.0, 3.9
END_LINE = 'I’m up.'
OFFER = 'You’ve given me enough. We open at six on Monday. Can you be here?'
ACCEPT = 'I’ll be there.'


def drain(age):
    """Shell Amount at `age` seconds into the separation (the graph's clamp(1 - (age - start) / drain))."""
    return min(1., max(0., 1. - (age - DRAIN_START) / DRAIN))


def bursts_due(age):
    """How many sand bursts have fired by `age` (the graph's clamp(floor((age - first) / gap) + 1, 0, 3))."""
    import math
    return min(BURSTS, max(0, math.floor((age - BURST_FIRST) / BURST_GAP) + 1))


def selftest():
    from job_wake_scene import WAKE_LENGTH
    assert drain(0) == 1 and drain(DRAIN_START + DRAIN) == 0 and drain(SEPARATION) == 0
    assert [bursts_due(a) for a in (0, .49, .5, 1.6, 1.7, 2.8, 9)] == [0, 0, 1, 1, 2, 3, 3]
    last_burst = BURST_FIRST + (BURSTS - 1) * BURST_GAP
    assert drain(last_burst) == 0, 'the suit goes only after the hands are gone'
    assert last_burst < SEPARATION - 1.5, 'hold on the empty room before the fade'
    assert ALARM_SECONDS < LINE_AT < WAKE_LENGTH - 2.5, 'the line plays after the alarm, with time to read'
    for text in (CARD_TITLE, CARD_CLOCK, END_LINE, OFFER, ACCEPT):
        assert not any(c in text for c in '·•|/—–'), text
    print('ending selftest ok: drain', [round(drain(a), 2) for a in (0, 1, 1.5, 2, 2.5, 3)], 'bursts at',
          [round(BURST_FIRST + i * BURST_GAP, 2) for i in range(BURSTS)])


# ---- editor steps -------------------------------------------------------------------------------------------------
def _b():
    import build_drive as b
    return b


def declare():
    b = _b()
    from build_drive import call
    info = call('blueprint_get_info', path=JOURNEY)
    have = {v['name'] for v in info['variables']}
    for name, kind, default in (('EndingStart', 'float', '0'), ('EndingBursts', 'int', '0')):
        if name not in have:
            call('blueprint_add_variable', path=JOURNEY, variable_name=name, variable_type=kind, default_value=default,
                 category='Ending', update_existing=True)
    for name in ('StartSeparation', 'TickSeparation', 'SeparationBurst', 'EndSeparation'):
        if not b.h.call('blueprint_inspect_graph', {'path': JOURNEY, 'graph_name': name}).get('ok'):
            call('blueprint_add_function', path=JOURNEY, function_name=name)
    call('blueprint_compile', path=JOURNEY, save=True)
    info = call('blueprint_get_info', path=THRESHOLD)
    have = {v['name'] for v in info['variables']}
    for name, kind in (('EndCard', 'object:' + b.cls(CARD)), ('WakeAlarm', 'object:/Script/Engine.AudioComponent')):
        if name not in have:
            call('blueprint_add_variable', path=THRESHOLD, variable_name=name, variable_type=kind, default_value='',
                 category='Ending', update_existing=True)
    for name in ('EndingWake', 'StopWakeAlarm', 'ShowEndLine'):
        if not b.h.call('blueprint_inspect_graph', {'path': THRESHOLD, 'graph_name': name}).get('ok'):
            call('blueprint_add_function', path=THRESHOLD, function_name=name)
    call('blueprint_compile', path=THRESHOLD, save=True)


def card():
    from build_drive import call
    if not call('ui_query', path=CARD, name_pattern='TimeLine').get('matches'):
        r = call('ui_build_tree', widget_blueprint_path=CARD, parent_widget_name='RootCanvas', tree=[dict(
            name='TimeLine', **{'class': 'TextBlock'}, properties={
                'Text': '', 'Justification': 'Center', 'Visibility': 'Collapsed',
                'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI', 'TypefaceFontName': 'SemiBold', 'Size': 40},
                'ColorAndOpacity': {'SpecifiedColor': [1, .97, .92, 1]},
                'ShadowOffset': [2, 2], 'ShadowColorAndOpacity': [0, 0, 0, .7]},
            slot_props=dict(anchors_min=[.5, 1], anchors_max=[.5, 1], alignment=[.5, 1], position=[0, -128], size=[1200, 64]))])
        print('TimeLine', r.get('rejected_properties'), r.get('unknown_slot_props'))
    for name in ('TimeBlack', 'TimeTitle', 'TimeClock', 'TimeLine'):
        call('ui_set_variable', widget_blueprint_path=CARD, widget_name=name, is_variable=True)
    call('ui_compile_widget', widget_blueprint_path=CARD)
    call('ui_save_widget', widget_blueprint_path=CARD)


def _guard(g, condition):
    br = g.branch(condition)
    g.side(br)
    return br


def journey():
    b = _b()
    from build_drive import G, cls, GS, SL, SC
    UW = '/Script/UMG.Widget:'

    def eq(g, name, value):
        return g.math('EqualEqual_IntInt', A=g.getv(name), B=value)

    g = G(JOURNEY, 'Submit')
    _guard(g, eq(g, 'Phase', 8))
    _guard(g, g.math('BooleanAND', A=g.getv('FinaleComplete'), B=g.math('Not_PreBool', A=g.getv('Submitted'))))
    g.setv('Submitted', True)
    g.setv('Phase', 9)
    g.own('DisableConfirm')
    g.own('ReleaseDialogue')
    g.do(cls(GI) + ':Learn', self=g.getv('Game'), Flag='Knows.L2CVSent')
    g.do(UW + 'RemoveFromParent', self=g.getv('HUD'))
    g.own('StartSeparation')
    g.own('RefreshProgressDisplays')
    g.finish()

    g = G(JOURNEY, 'StartSeparation')
    g.setv('EndingStart', g.f(GS + 'GetTimeSeconds'))
    g.setv('EndingBursts', 0)
    g.own('SetMusic', Track='Ending')
    g.do(SL + 'K2_SetTimer', FunctionName='TickSeparation', Time=.033, bLooping=True)
    g.do(SL + 'K2_SetTimer', FunctionName='EndSeparation', Time=SEPARATION, bLooping=False)
    from build_l2_sand_set import OBJECTS, CRUMBLE_SECONDS
    if os.environ.get('FOA_SAND') == '1':  # set once build_l2_sand_set.py added the components
        _guard(g, g.f(SL + 'IsValid', Object=g.getv('StopSet')))
        for name in OBJECTS:  # the room's Lux3D sand objects go first (SandEvent: 0 intact -> 1 gone)
            g.do('/Script/Engine.PrimitiveComponent:SetVectorParameterForCustomPrimitiveData',
                 self=g.getv(name, g.getv('StopSet'), STOPSET), ParameterName='SandEvent',
                 Value=g.math('MakeVector4', X=g.getv('InterviewSand'), Y=g.f(GS + 'GetTimeSeconds'), Z=CRUMBLE_SECONDS, W=1))
    g.finish()

    g = G(JOURNEY, 'TickSeparation')
    _guard(g, g.f(SL + 'IsValid', Object=g.getv('StopSet')))
    age = g.math('Subtract_DoubleDouble', A=g.f(GS + 'GetTimeSeconds'), B=g.getv('EndingStart'))
    gone = g.math('Divide_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=age, B=DRAIN_START), B=DRAIN)
    amount = g.math('FClamp', Value=g.math('Subtract_DoubleDouble', A=1., B=gone), Min=0., Max=1.)
    for part in ('InterviewBody', 'InterviewFace'):
        g.do('/Script/Engine.MeshComponent:SetScalarParameterValueOnMaterials',
             self=g.getv(part, g.getv('StopSet'), STOPSET), ParameterName='Amount', ParameterValue=amount)
    push = g.math('FClamp', Value=g.math('Divide_DoubleDouble', A=age, B=SEPARATION), Min=0., Max=1.)
    g.do('/Script/Engine.CameraComponent:SetFieldOfView', self=g.getv('StageCamera', g.getv('StopSet'), STOPSET),
         InFieldOfView=g.math('Lerp', A=FOV_FROM, B=FOV_TO, Alpha=g.math('Multiply_DoubleDouble', A=push, B=push)))
    due = g.math('Clamp', Value=g.math('Add_IntInt', A=g.math('FFloor', A=g.math(
        'Divide_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=age, B=BURST_FIRST), B=BURST_GAP)), B=1), Min=0, Max=BURSTS)
    _guard(g, g.math('Less_IntInt', A=g.getv('EndingBursts'), B=due))
    g.own('SeparationBurst')
    g.finish()

    g = G(JOURNEY, 'SeparationBurst')
    _guard(g, g.f(SL + 'IsValid', Object=g.getv('StopSet')))
    n = g.getv('EndingBursts')

    def pick(values):
        out = values[0]
        for i, v in enumerate(values[1:], 1):
            out = g.math('SelectFloat', A=v, B=out, bPickA=g.math('EqualEqual_IntInt', A=n, B=i))
        return out
    body = g.getv('InterviewBody', g.getv('StopSet'), STOPSET)
    at = g.math('Add_VectorVector', A=g.f(SC + 'K2_GetComponentLocation', self=body),
                B=g.math('MakeVector', X=0, Y=0, Z=pick(BURST_HEIGHT)))
    g.do(SAND, Location=at, Scale=pick(BURST_SCALE))
    g.setv('EndingBursts', g.math('Add_IntInt', A=g.getv('EndingBursts'), B=1))
    _guard(g, g.math('EqualEqual_IntInt', A=g.getv('EndingBursts'), B=BURSTS))
    g.do(SC + 'SetVisibility', self=g.getv('InterviewSuit', g.getv('StopSet'), STOPSET), bNewVisibility=False,
         bPropagateToChildren=False)
    g.finish()

    g = G(JOURNEY, 'EndSeparation')
    g.do(SL + 'K2_ClearTimer', FunctionName='TickSeparation')
    g.do(cls(THRESHOLD) + ':BeginEnding', self=g.getv('Threshold'))
    g.finish()


def threshold():
    import build_threshold as t
    from build_drive import G, cls, GS, SL, A
    from job_wake_scene import SEQUENCE, WAKE_LENGTH
    from job_dream_look import COMPONENT as MOTION
    from job_wake_scene import ROOM_SAND
    UW = '/Script/UMG.Widget:'
    TB = '/Script/UMG.TextBlock:'
    POST = '/Script/Engine.PostProcessComponent'
    VOLUME = '/Script/Engine.PostProcessVolume'
    BP = THRESHOLD

    def valid(g, obj):
        return _guard(g, g.f(SL + 'IsValid', Object=obj))

    def card_part(g, name):
        return g.getv(name, g.getv('EndCard'), CARD)

    g = G(BP, 'BeginEnding')
    g.setv('Phase', 7)
    t.music(g, 'Ending')
    g.do(cls('/Game/FoA/Characters/Player/BP_FoAPlayer') + ':SetCinematic', self=g.getv('Player'), bEnable=True)
    r = g.ref()
    g.get(r, 'CharacterMovement', 0, 0, '/Script/Engine.Character')
    g.put(r, 'self', g.getv('Player'))
    g.do('/Script/Engine.CharacterMovementComponent:SetMovementMode', self=(r, 'CharacterMovement'), NewMovementMode='MOVE_None')
    g.do(A + 'SetActorEnableCollision', self=g.getv('Player'), bNewActorEnableCollision=False)
    t.fade(g, 0, 1, .8)
    t.timer(g, 'EndingColour', 1.)
    g.finish()

    g = G(BP, 'EndingColour')
    g.own('RestoreWakeRoom')  # door closed, wardrobe standing (patch_wake_room.py builds it)
    g.setv('Phase', 8)
    g.setv('WakeActive', True)
    journey = g.getv('Journey')
    gate = g.branch(g.f(SL + 'IsValid', Object=journey))
    g.side(gate)
    g.do(cls(JOURNEY) + ':ReleaseStop', self=g.getv('Journey'))
    joined = g.setv('Phase', 8)
    g.link(gate, 'else', joined[0], 'execute')
    t.external(g, 'BlendWeight', 0., g.getv(MOTION), POST)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible', self=g.getv('Stream'), bInShouldBeVisible=False)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible', self=g.getv('CityStream'), bInShouldBeVisible=False)
    g.do('/Script/Engine.PrimitiveComponent:SetCollisionEnabled', self=g.getv('Floor'), NewType='NoCollision')
    g.do(A + 'SetActorHiddenInGame', self=g.getv('Player'), bNewHidden=True)
    g.do(A + 'SetActorHiddenInGame', self=g.getv('Merge', g.getv('Journey'), JOURNEY), bNewHidden=True)
    g.do(A + 'K2_SetActorLocation', self=g.getv('Player'), NewLocation='238,-191,155', bSweep=False, bTeleport=True)
    grade = g.own('FindWakeGrade')
    obj = g.cast((grade[0], 'Target'), VOLUME, 'Post Process Volume')
    g.setv('WakeGrade', obj)
    r = g.ref()
    g.get(r, 'bEnabled', 0, 0, VOLUME)
    g.put(r, 'self', obj)
    g.setv('WakeGradeWasEnabled', (r, 'bEnabled'))
    t.external(g, 'bEnabled', False, obj, VOLUME)
    sand = g.do(GS + 'GetAllActorsWithTag', Tag=ROOM_SAND)
    g.setv('WakeSandTargets', (sand[0], 'OutActors'))
    g.own('HideWakeSand', Index=0)
    pool = g.do(GS + 'GetActorOfClass', ActorClass=cls('/Game/FoA/VFX/Sand/BP_SandFX'))
    g.own('HideWakeActor', Target=pool)
    t.text(g)
    widget = g.ref()
    g.node(widget, 'create_widget', 0, 0, class_path=cls(CARD))
    g.put(widget, 'OwningPlayer', g.f(GS + 'GetPlayerController', PlayerIndex=0))
    g.chain(g.tail, widget)
    g.tail = widget
    g.setv('EndCard', (widget, 'ReturnValue'))
    g.do(TB + 'SetText', self=card_part(g, 'TimeTitle'), InText=CARD_TITLE)
    g.do(TB + 'SetText', self=card_part(g, 'TimeClock'), InText=CARD_CLOCK)
    g.do('/Script/UMG.UserWidget:AddToViewport', self=g.getv('EndCard'), ZOrder=96)
    t.timer(g, 'EndingWake', CARD_SECONDS)
    g.finish()

    g = G(BP, 'EndingWake')
    _guard(g, g.getv('WakeActive'))
    valid(g, g.getv('EndCard'))
    for name in ('TimeBlack', 'TimeTitle', 'TimeClock'):
        g.do(UW + 'SetVisibility', self=card_part(g, name), InVisibility='Collapsed')
    seq = g.do(t.LSP + 'CreateLevelSequencePlayer', LevelSequence=SEQUENCE,
               Settings='(bDisableMovementInput=True,bDisableLookAtInput=True,bHideHud=True,bPauseAtEnd=True)')
    g.setv('Sequence', seq)
    g.setv('SequenceActor', (seq[0], 'OutActor'))
    g.do(t.MSP + 'Play', self=g.getv('Sequence'))
    alarm = g.do(GS + 'SpawnSound2D', Sound=ALARM, VolumeMultiplier=.5, bAutoDestroy=True)
    g.setv('WakeAlarm', alarm)
    t.timer(g, 'StopWakeAlarm', ALARM_SECONDS)
    t.timer(g, 'ShowEndLine', LINE_AT)
    t.timer(g, 'FadeWakeToCredits', WAKE_LENGTH)
    g.finish()

    g = G(BP, 'StopWakeAlarm')
    valid(g, g.getv('WakeAlarm'))
    g.do('/Script/Engine.AudioComponent:Stop', self=g.getv('WakeAlarm'))
    g.do(GS + 'PlaySound2D', Sound=ALARM_OFF, VolumeMultiplier=.6)
    g.finish()

    g = G(BP, 'ShowEndLine')
    _guard(g, g.getv('WakeActive'))
    valid(g, g.getv('EndCard'))
    # round 3: the ui kit's sand line (forms from black sand, holds until the card goes)
    g.do('/Game/FoA/UI/Widgets/Common/WBP_SandLine.WBP_SandLine_C:Play', self=card_part(g, 'Line_End'), Line=END_LINE,
         Mood=0, Hold=0.)
    g.finish()

    g = G(BP, 'FadeWakeToCredits')
    _guard(g, g.getv('WakeActive'))
    t.fade(g, 1, 1, 0.)
    gate = g.branch(g.f(SL + 'IsValid', Object=g.getv('EndCard')))
    g.side(gate)
    g.do(UW + 'RemoveFromParent', self=g.getv('EndCard'))
    joined = g.do(SL + 'K2_SetTimer', FunctionName='BeginWakeCredits', Time=.5, bLooping=False)
    g.link(gate, 'else', joined[0], 'execute')
    g.finish()

    g = G(BP, 'RestoreWakeLook')
    t.external(g, 'BlendWeight', 0., g.getv(MOTION), POST)
    for name in ('EndingColour', 'EndingWake', 'StopWakeAlarm', 'ShowEndLine', 'FadeWakeToCredits', 'BeginWakeCredits',
                 'TickWakeCredits'):
        g.do(SL + 'K2_ClearTimer', FunctionName=name)
    gate = g.branch(g.f(SL + 'IsValid', Object=g.getv('WakeAlarm')))
    g.side(gate)
    g.do('/Script/Engine.AudioComponent:Stop', self=g.getv('WakeAlarm'))
    joined = g.setv('WakeAlarm', '')
    g.link(gate, 'else', joined[0], 'execute')
    gate = g.branch(g.f(SL + 'IsValid', Object=g.getv('EndCard')))
    g.side(gate)
    g.do(UW + 'RemoveFromParent', self=g.getv('EndCard'))
    joined = g.setv('EndCard', '')
    g.link(gate, 'else', joined[0], 'execute')
    was_wake = g.branch(g.getv('WakeActive'))
    g.side(was_wake)
    g.setv('WakeActive', False)
    g.own('RestoreWakeSand', Index=0)
    t.external(g, 'bEnabled', g.getv('WakeGradeWasEnabled'), g.getv('WakeGrade'), VOLUME)
    valid(g, g.getv('WakeCredits'))
    g.do(UW + 'RemoveFromParent', self=g.getv('WakeCredits'))
    g.setv('WakeCredits', '')
    g.finish()


def interview():
    """The interview's minimal screens and the offer's answer (build_interview.py's job-hunt graphs, rebuilt)."""
    import build_interview as ui
    for index in range(6):
        ui.render_question(index, True)
    ui.render(True)
    ui.feedback()


def texts():
    """Player text without slash separators: the street intro hint, the employer and shift screens."""
    import build_journey as j
    import build_job_hunt as jobs
    import shift_minigames
    from job_hunt_data import JOBS
    j.resume()
    jobs.render_pitch(JOBS)
    jobs.render(JOBS)
    shift_minigames.render_shift()


def arrive():
    """Arrive's street transform takes the car's yaw (the job stops face the street the car came in on)."""
    import build_journey as j
    j.arrive(True)


def land():
    """The landing card while the street streams in: the place name only (was 'Loading the street...')."""
    import build_threshold as t
    t.land()


STEPS = dict(declare=declare, card=card, journey=journey, threshold=threshold, interview=interview, texts=texts, land=land, arrive=arrive)
ASSETS = dict(declare=(JOURNEY, THRESHOLD), card=(CARD,), journey=(JOURNEY,), threshold=(THRESHOLD,), interview=(JOURNEY,),
              texts=(JOURNEY,), land=(THRESHOLD,), arrive=(JOURNEY,))


def run(step):
    if step == 'selftest':
        return selftest()
    _b()  # puts Tools/Unreal on sys.path
    import editor_lock
    owner = 'level2'
    os.environ.update(FOA_AGENT=owner, HAYBA_AGENT_ID=owner)
    token = editor_lock.acquire(owner, wait_s=1500, ttl=240, areas=list(ASSETS[step]))
    os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases(owner)[0][0]
    try:
        assert not _b().call('editor_get_state')['pie_running'], 'PIE is running: no graph edits now'
        STEPS[step]()
    finally:
        editor_lock.release(owner)


if __name__ == '__main__':
    for name in sys.argv[1:]:  # one short lease per step
        print('== step', name, flush=True)
        run(name)
