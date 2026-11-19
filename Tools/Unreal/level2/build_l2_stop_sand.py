"""Lux3D (Aholo) sand objects at Level 2's job stops (level2 lane, 2026-11-18).

Each trial-shift stop happens on the street in first person. Two text-to-3D splat objects, made for the dream and never
used before, form out of black sand in the street ahead of him as the employer talks, and are gone when he drives on:
  Queen Market (06:00)    the unpaid bills, three metres tall, and the hourglass
  Night Dispatch (23:40)  the melting calendar and the twin-bell alarm clock
  Northline Supply        the necktie serpent and the fear-of-adulthood clock
Two pooled StaticMeshComponents on BP_L2Journey (StopSandA, StopSandB); FormStopSand (end of BeginJob) places them by
a ground trace, sets mesh, material and scale for the stop, shows them and plays SandEvent 1 -> 0 (form);
HideStopSand (ClearJob) hides them.
  python -B build_l2_stop_sand.py selftest | components | graphs | hooks
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

JOURNEY = '/Game/FoA/Level2/Journey/BP_L2Journey'
SAND = '/Game/FoA/Level2/Journey/Sand'
VFX = '/Game/FoA/VFX/Splats'
SLOTS = ('StopSandA', 'StopSandB')


def own(name):
    return f'{SAND}/{name}/{name}', f'{SAND}/MI_{name[3:]}'  # Interchange with materials off: no StaticMeshes subfolder


# Per stop, per slot: (mesh, material, uniform scale, forward cm, right cm, yaw offset from facing him).
# He stands at StreetTransform looking along +X (BeginJob sets control yaw 0); right is +Y.
STOPS = (  # dream-scale, 2.5-3 m tall, so they rise above the dialogue panel's gradient at eye level
    ((*own('SM_SandBills'), 4., 760., -230., 18.),
     (VFX + '/Meshes/SM_SandHourglass/SM_SandHourglass/StaticMeshes/SM_SandHourglass', VFX + '/Instances/MI_Sand_Hourglass', 5., 1000., 290., -12.)),
    # Night Dispatch: he stands on the south pavement (the street is to his right); Northline: the street is to his left,
    # the clock stands on the near pavement so the employer portrait (screen left) never covers it.
    ((*own('SM_SandCalendar'), 9.5, 700., 150., 15.),
     (VFX + '/Meshes/SM_AlarmClockSplats/SM_AlarmClockSplats/StaticMeshes/SM_AlarmClockSplats', VFX + '/Instances/MI_Sand_AlarmClock', 6.5, 950., 620., -20.)),
    ((*own('SM_SandNecktie'), 8., 700., -160., 25.),
     (VFX + '/Meshes/fear_of_adulthood_clock', VFX + '/Instances/MI_Sand_AlarmClock', 6., 1100., 170., -15.)),
)
FORM, STAGGER = 2.4, .6
# Queen Street, on foot (Phase 1): the sand crow watches him from the pavement ahead, then waits in the interview room.
STREET = (*own('SM_SandCrow'), .8, 700., -90., -35.)


def selftest():
    assert len(STOPS) == 3 and all(len(s) == len(SLOTS) for s in STOPS)
    for stop in STOPS:
        a, b = stop
        assert a[4] != b[4] and max(abs(a[4]), abs(b[4])) <= 700, 'apart, and on the street not in the facades'
        assert a[3] >= 600 and b[3] >= 600, 'far enough to stay in focus behind the panels'
    print('stop sand selftest ok')


def components():
    import build_drive as b
    info = b.call('blueprint_get_info', path=JOURNEY)
    have = {c['name'] for c in info.get('components', [])}
    for name in SLOTS:
        if name not in have:
            b.call('blueprint_add_component', path=JOURNEY, component_name=name,
                   component_class_path='/Script/Engine.StaticMeshComponent')
    for name in ('FormStopSand', 'HideStopSand', 'FormStreetSand'):
        if not b.h.call('blueprint_inspect_graph', {'path': JOURNEY, 'graph_name': name}).get('ok'):
            b.call('blueprint_add_function', path=JOURNEY, function_name=name)
    b.call('blueprint_compile', path=JOURNEY, save=True)


def templates():
    import unreal as u
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(), 'PIE running'
    from free_drive_setup import templates as read
    bp, sds, lib, gathered, handles, comps = read(JOURNEY)
    root = next(h for n, h in handles.items() if n in ('DefaultSceneRoot', 'Root'))
    for name in SLOTS:
        assert name in handles, ('add the component first', name)
        sds.attach_subobject(root, handles[name])
        c = comps[name]
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        for prop, value in (('cast_shadow', False), ('visible', False), ('generate_overlap_events', False),
                            ('can_character_step_up_on', u.CanBeCharacterBase.ECB_NO), ('absolute_location', True),
                            ('absolute_rotation', True), ('absolute_scale', True)):
            c.set_editor_property(prop, value)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('stop sand templates', SLOTS)


def graphs():
    from build_drive import G, GS, SL, SC
    K = '/Script/Engine.KismetMathLibrary:'
    PRIM = '/Script/Engine.PrimitiveComponent:'
    SM = '/Script/Engine.StaticMeshComponent:'

    g = G(JOURNEY, 'FormStopSand')
    stop = g.getv('Stop')
    gate = g.branch(g.math('Less_IntInt', A=stop, B=3))
    g.side(gate)
    base = g.math('BreakTransform', InTransform=g.getv('StreetTransform'))
    origin = (base[0], 'Location')
    # He faces the way the car arrived (BeginJob turns him to the car's yaw), so offsets turn with it.
    heading = g.math('BreakRotator', InRot=g.f('/Script/Engine.Actor:K2_GetActorRotation', self=g.getv('Car')))
    face = g.math('MakeRotator', Roll=0, Pitch=0, Yaw=(heading[0], 'Yaw'))

    def pick(kind, values):
        out = values[0]
        for i, v in enumerate(values[1:], 1):
            out = g.math('Select' + kind, A=v, B=out, **{'bSelectA' if kind == 'Object' else 'bPickA':
                                                         g.math('EqualEqual_IntInt', A=g.getv('Stop'), B=i)})
        return out
    for slot_index, slot in enumerate(SLOTS):
        rows = [stop_rows[slot_index] for stop_rows in STOPS]
        comp = g.getv(slot)
        mesh = g.cast(pick('Object', [r[0] for r in rows]), '/Script/Engine.StaticMesh', 'Static Mesh')
        g.do(SM + 'SetStaticMesh', self=g.getv(slot), NewMesh=mesh)
        material = g.cast(pick('Object', [r[1] for r in rows]), '/Script/Engine.MaterialInterface', 'Material Interface')
        g.do(PRIM + 'SetMaterial', self=g.getv(slot), ElementIndex=0, Material=material)
        local = g.math('MakeVector', X=pick('Float', [r[3] for r in rows]), Y=pick('Float', [r[4] for r in rows]), Z=0)
        at = g.math('Add_VectorVector', A=origin, B=g.math('GreaterGreater_VectorRotator', A=local, B=face))
        top = g.math('Add_VectorVector', A=at, B='0,0,400')
        bottom = g.math('Subtract_VectorVector', A=at, B='0,0,900')
        trace = g.do(SL + 'LineTraceSingle', Start=top, End=bottom, TraceChannel='TraceTypeQuery1', bTraceComplex=False,
                     bIgnoreSelf=True)
        hit = g.f(GS + 'BreakHitResult', Hit=(trace[0], 'OutHit'))
        ground = g.math('SelectVector', A=(hit[0], 'Location'), B=g.math('Subtract_VectorVector', A=at, B='0,0,92'),
                        bPickA=(trace[0], 'ReturnValue'))
        yaw = g.math('Add_DoubleDouble', A=g.math('Add_DoubleDouble', A=90., B=pick('Float', [r[5] for r in rows])),
                     B=(heading[0], 'Yaw'))  # front +Y turned back toward him
        g.do(SC + 'K2_SetWorldLocationAndRotation', self=g.getv(slot), NewLocation=ground,
             NewRotation=g.math('MakeRotator', Roll=0, Pitch=0, Yaw=yaw), bSweep=False, bTeleport=True)
        scale = pick('Float', [r[2] for r in rows])
        g.do(SC + 'SetWorldScale3D', self=g.getv(slot), NewScale=g.math('MakeVector', X=scale, Y=scale, Z=scale))
        g.do(SC + 'SetVisibility', self=g.getv(slot), bNewVisibility=True, bPropagateToChildren=False)
        start = g.math('Add_DoubleDouble', A=g.f(GS + 'GetTimeSeconds'), B=STAGGER * slot_index)
        g.do(PRIM + 'SetVectorParameterForCustomPrimitiveData', self=g.getv(slot), ParameterName='SandEvent',
             Value=g.math('MakeVector4', X=1, Y=start, Z=FORM, W=0))
    g.finish()

    g = G(JOURNEY, 'FormStreetSand')
    mesh, material, scale, fwd, right, yaw = STREET
    g.do(SC + 'SetVisibility', self=g.getv(SLOTS[1]), bNewVisibility=False, bPropagateToChildren=False)
    g.do(SM + 'SetStaticMesh', self=g.getv(SLOTS[0]), NewMesh=mesh)
    g.do(PRIM + 'SetMaterial', self=g.getv(SLOTS[0]), ElementIndex=0, Material=material)
    at = g.math('Add_VectorVector', A=g.f('/Script/Engine.Actor:K2_GetActorLocation', self=g.getv('Player')),
                B=g.math('MakeVector', X=fwd, Y=right, Z=0))
    trace = g.do(SL + 'LineTraceSingle', Start=g.math('Add_VectorVector', A=at, B='0,0,400'),
                 End=g.math('Subtract_VectorVector', A=at, B='0,0,900'), TraceChannel='TraceTypeQuery1',
                 bTraceComplex=False, bIgnoreSelf=True)
    hit = g.f(GS + 'BreakHitResult', Hit=(trace[0], 'OutHit'))
    ground = g.math('SelectVector', A=(hit[0], 'Location'), B=g.math('Subtract_VectorVector', A=at, B='0,0,92'),
                    bPickA=(trace[0], 'ReturnValue'))
    g.do(SC + 'K2_SetWorldLocationAndRotation', self=g.getv(SLOTS[0]), NewLocation=ground,
         NewRotation=g.math('MakeRotator', Roll=0, Pitch=0, Yaw=90. + yaw), bSweep=False, bTeleport=True)
    g.do(SC + 'SetWorldScale3D', self=g.getv(SLOTS[0]), NewScale=g.math('MakeVector', X=scale, Y=scale, Z=scale))
    g.do(SC + 'SetVisibility', self=g.getv(SLOTS[0]), bNewVisibility=True, bPropagateToChildren=False)
    g.do(PRIM + 'SetVectorParameterForCustomPrimitiveData', self=g.getv(SLOTS[0]), ParameterName='SandEvent',
         Value=g.math('MakeVector4', X=1, Y=g.f(GS + 'GetTimeSeconds'), Z=FORM + 1., W=0))
    # round 3: a black-sand hand the size of a building rises out of Queen Street and points the way to Queen Market
    from build_l2_round3 import HAND_POSE
    fwd, right, sink, roll, yaw, scale = HAND_POSE
    at = g.math('Add_VectorVector', A=g.f('/Script/Engine.Actor:K2_GetActorLocation', self=g.getv('Player')),
                B=g.math('MakeVector', X=fwd, Y=right, Z=0))
    trace = g.do(SL + 'LineTraceSingle', Start=g.math('Add_VectorVector', A=at, B='0,0,400'),
                 End=g.math('Subtract_VectorVector', A=at, B='0,0,900'), TraceChannel='TraceTypeQuery1',
                 bTraceComplex=False, bIgnoreSelf=True)
    hit = g.f(GS + 'BreakHitResult', Hit=(trace[0], 'OutHit'))
    ground = g.math('SelectVector', A=(hit[0], 'Location'), B=g.math('Subtract_VectorVector', A=at, B='0,0,92'),
                    bPickA=(trace[0], 'ReturnValue'))
    g.do(SC + 'K2_SetWorldLocationAndRotation', self=g.getv('StreetGiant'),
         NewLocation=g.math('Add_VectorVector', A=ground, B=g.math('MakeVector', X=0, Y=0, Z=sink)),
         NewRotation=g.math('MakeRotator', Roll=roll, Pitch=0, Yaw=yaw), bSweep=False, bTeleport=True)
    g.do(SC + 'SetWorldScale3D', self=g.getv('StreetGiant'), NewScale=g.math('MakeVector', X=scale, Y=scale, Z=scale))
    g.do(SC + 'SetVisibility', self=g.getv('StreetGiant'), bNewVisibility=True, bPropagateToChildren=False)
    g.do(PRIM + 'SetVectorParameterForCustomPrimitiveData', self=g.getv('StreetGiant'), ParameterName='SandEvent',
         Value=g.math('MakeVector4', X=1, Y=g.math('Add_DoubleDouble', A=g.f(GS + 'GetTimeSeconds'), B=.6), Z=4.5, W=0))
    g.finish()

    g = G(JOURNEY, 'HideStopSand')
    for slot in (*SLOTS, 'StreetGiant'):
        g.do(SC + 'SetVisibility', self=g.getv(slot), bNewVisibility=False, bPropagateToChildren=False)
    g.finish()


def hooks():
    """FormStopSand at the end of BeginJob, HideStopSand in ClearJob and EnterCar, FormStreetSand in ResumeRun."""
    import build_job_hunt as jobs
    import build_journey as j
    jobs.begin()
    jobs.clear()
    j.resume()
    j.enter_car()


def run(step):
    if step == 'selftest':
        return selftest()
    import build_drive as b
    import editor_lock
    owner = 'level2'
    os.environ.update(FOA_AGENT=owner, HAYBA_AGENT_ID=owner)
    token = editor_lock.acquire(owner, wait_s=1500, ttl=240, areas=[JOURNEY])
    os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases(owner)[0][0]
    try:
        assert not b.call('editor_get_state')['pie_running'], 'PIE is running'
        dict(components=components, graphs=graphs, hooks=hooks)[step]()
    finally:
        editor_lock.release(owner)


if __name__ == '__main__':
    if os.environ.get('FOA_SAND_STEP') == 'templates':
        sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
        templates()
    else:
        for name in sys.argv[1:]:
            print('== step', name, flush=True)
            run(name)
