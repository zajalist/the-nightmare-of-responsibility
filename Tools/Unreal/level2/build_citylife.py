"""City life lane: BP_L2CityLife, the pool of Lux3D things that move around the Level 2 city while the car drives.

  python -B Tools/Unreal/level2/build_citylife.py skeleton|graphs|Tend|Step|HideAll|Setup|events

One actor, placed once in the persistent map. A 0.25 s timer (no Tick) finds the drive's BP_L2Car and, while it is
Active on a rail, tends 16 pooled components: anything hidden, 30 m behind the car or 160 m from it re-forms 55-115 m
ahead on the car's rail. Walkers and rolling chairs stand on a pavement the offline table (citylife_data.LANES) says is
clear, and crumble into black sand (BP_SandFX's pooled burst, no sound) as the car draws level. Flocks, pages, briefcases,
umbrellas and the phone fly above the road. All motion is native: ProjectileMovement carries walkers and chairs at
walking speed, RotatingMovement turns the flocks, the chairs and the phone. Reads BP_L2Car only, never writes it.
"""
from pathlib import Path
import sys

sys.path[:0] = [str(Path(__file__).parent), 'P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import citylife_data as C
import drive_rails as R
from drive_rails import G, both, either, NOT, add, sub, ge, lt, gate, A, SC, GS, SL, K, cls

call = R.b.call
CAR = R.CAR
SANDFX = '/Game/FoA/VFX/Sand/BP_SandFX'
SANDLIB = '/Game/FoA/VFX/Sand/BPL_SandFX'
SP = '/Script/Engine.SplineComponent:'
PM = '/Script/Engine.ProjectileMovementComponent'
STR = '/Script/Engine.KismetStringLibrary:'
BP = C.BP

WALKERS = [f'WalkMesh{i}' for i in range(8)]
CHAIRS = [f'ChairMesh{i}' for i in range(2)]
FLOCKS = [f'Flock{i}' for i in range(5)]
COMPONENTS = ([('Root', 'SceneComponent')] + [(n, 'SkeletalMeshComponent') for n in WALKERS] +
              [(f'WalkMove{i}', 'ProjectileMovementComponent') for i in range(8)] +
              [(n, 'StaticMeshComponent') for n in CHAIRS] + [(f'ChairMove{i}', 'ProjectileMovementComponent') for i in range(2)] +
              [(f'ChairSpin{i}', 'RotatingMovementComponent') for i in range(2)] +
              [(n, 'InstancedStaticMeshComponent') for n in FLOCKS] + [(f'FlockSpin{i}', 'RotatingMovementComponent') for i in range(5)] +
              [('Phone', 'StaticMeshComponent'), ('PhoneSpin', 'RotatingMovementComponent')])
MOVERS = ([(f'WalkMove{i}', w) for i, w in enumerate(WALKERS)] + [(f'ChairMove{i}', c) for i, c in enumerate(CHAIRS)] +
          [(f'ChairSpin{i}', c) for i, c in enumerate(CHAIRS)] + [(f'FlockSpin{i}', f) for i, f in enumerate(FLOCKS)] +
          [('PhoneSpin', 'Phone')])
VARIABLES = [('Car', 'object:' + cls(CAR), ''), ('SandFX', 'object:' + cls(SANDFX), ''), ('Shown', 'bool', 'false'),
             ('Lanes', 'string', ''), ('TmpD', 'float', '0'), ('TmpAhead', 'float', '0'), ('TmpSide', 'float', '0'),
             ('TmpLane', 'string', ''), ('TmpPos', 'vector', '0,0,0'), ('LastGround', 'float', '0'),
             ('LastAir', 'float', '0')]
FUNCTIONS = {'Setup': [], 'Step': [], 'HideAll': [],
             'Tend': [('Pivot', 'object:/Script/Engine.SceneComponent'), ('Mover', 'object:' + PM), ('Ground', 'bool'),
                      ('Lateral', 'float'), ('Height', 'float'), ('YawOffset', 'float'), ('Velocity', 'vector'),
                      ('Crumble', 'float')]}


def tend_args():
    """(component, mover, Tend pins) per pooled thing, in the order Step tends them."""
    rows = []
    for i, name in enumerate(WALKERS):
        speed = C.WALK_SPEEDS[i // 2]
        v = [round(a * speed, 1) for a in C.WALK_FWD]
        rows.append((name, f'WalkMove{i}', dict(Ground=True, Lateral=0, Height=C.HEIGHTS[C.WALKERS[i][0]] / 2, YawOffset=C.WALK_YAW,
                                                 Velocity=','.join(map(str, v)), Crumble=2.0)))
    for i, name in enumerate(CHAIRS):
        rows.append((name, f'ChairMove{i}', dict(Ground=True, Lateral=0, Height=C.CHAIR_LIFT, YawOffset=0, Velocity='70,0,0',
                                                  Crumble=1.6)))
    for name, (lateral, height) in zip(FLOCKS, C.FLOCK_PLACES):
        rows.append((name, None, dict(Ground=False, Lateral=lateral, Height=height, YawOffset=0, Velocity='0,0,0', Crumble=0)))
    rows.append(('Phone', None, dict(Ground=False, Lateral=C.PHONE_PLACE[0], Height=C.PHONE_PLACE[1], YawOffset=0,
                                     Velocity='0,0,0', Crumble=0)))
    return rows


def skeleton():
    if not R.b.h.call('blueprint_get_info', {'path': BP}).get('ok'):
        call('blueprint_create', package_path=BP, name=BP.rsplit('/', 1)[1], parent_class_path='/Script/Engine.Actor')
    info = call('blueprint_get_info', path=BP)
    have = {c['name'] for c in info.get('components', [])}
    for name, typ in COMPONENTS:
        if name not in have:
            call('blueprint_add_component', path=BP, component_name=name, component_class_path='/Script/Engine.' + typ)
    have = {v['name'] for v in info['variables']}
    lanes = Path(C.__file__).with_name('citylife_lanes.txt').read_text()
    for name, typ, default in VARIABLES:
        if name not in have:
            call('blueprint_add_variable', path=BP, variable_name=name, variable_type=typ, category='City life',
                 default_value=lanes if name == 'Lanes' else default)
    for name, inputs in FUNCTIONS.items():
        if name not in info['functions']:
            call('blueprint_add_function', path=BP, function_name=name, inputs=[dict(name=n, type=t) for n, t in inputs])
    call('blueprint_compile', path=BP)
    call('asset_save', asset_paths=[BP])


def rail_at(g, what, distance):
    return g.f(SP + f'Get{what}AtDistanceAlongSpline', self=g.getv('Rail', g.getv('Car'), CAR), Distance=distance,
               CoordinateSpace='World')


def car(g, name):
    return g.getv(name, g.getv('Car'), CAR)


def tend():
    """Keep a pooled thing while it is ahead and near; else re-form it ahead on a clear pavement (ground) or over the road."""
    g = G(BP, 'Tend')
    pivot = g.arg('Pivot')
    g.group('Where it is')
    rel = g.math('Subtract_VectorVector', A=g.f(SC + 'K2_GetComponentLocation', self=pivot),
                 B=g.f(A + 'K2_GetActorLocation', self=g.getv('Car')))
    g.setv('TmpAhead', g.math('Dot_VectorVector', A=rel, B=rail_at(g, 'Direction', car(g, 'Distance'))))
    keep = both(g, g.f(SC + 'IsVisible', self=pivot), ge(g, g.getv('TmpAhead'), -C.BEHIND),
                lt(g, g.math('VSize', A=rel), C.FAR))
    held = g.branch(keep); g.side(held)
    g.group('Walk along the street')
    # walkers only (skeletal meshes): turn to the rail's tangent at their nearest point, keeping their direction, so
    # they follow the pavement round a bend instead of walking into a facade; chairs keep their own spin
    rail = lambda: g.getv('Rail', g.getv('Car'), CAR)  # noqa: E731
    walker = g.math('ClassIsChildOf', TestClass=g.f(GS + 'GetObjectClass', Object=g.arg('Pivot')),
                    ParentClass='/Script/Engine.SkeletalMeshComponent')
    gate(g, both(g, walker, g.f(SL + 'IsValid', Object=g.arg('Mover'))))
    key = g.f(SP + 'FindInputKeyClosestToWorldLocation', self=rail(), WorldLocation=g.f(SC + 'K2_GetComponentLocation', self=g.arg('Pivot')))
    tangent = g.f(SP + 'GetDirectionAtSplineInputKey', self=rail(), InKey=key, CoordinateSpace='World')
    facing = g.f(K + 'BreakRotator', InRot=g.f(SC + 'K2_GetComponentRotation', self=g.arg('Pivot')))
    heading = g.math('GetForwardVector', InRot=g.math('MakeRotator', Yaw=sub(g, (facing[0], 'Yaw'), g.arg('YawOffset'))))
    along = g.math('SelectFloat', A=0, B=180, bPickA=ge(g, g.math('Dot_VectorVector', A=heading, B=tangent), 0))
    street = g.f(K + 'BreakRotator', InRot=g.math('Conv_VectorToRotator', InVec=tangent))
    g.do(SC + 'K2_SetWorldRotation', self=g.arg('Pivot'), NewRotation=g.math('MakeRotator', Yaw=add(g, add(g, (street[0], 'Yaw'), along), g.arg('YawOffset'))),
         bSweep=False, bTeleport=True)
    g.do(PM + ':SetVelocityInLocalSpace', self=g.arg('Mover'), NewVelocity=g.arg('Velocity'))
    g.group('Crumble as the car passes')
    gate(g, both(g, g.arg('Ground'), lt(g, g.getv('TmpAhead'), C.CRUMBLE), g.math('Greater_DoubleDouble', A=g.arg('Crumble'), B=0)))
    g.do(cls(SANDFX) + ':Play', self=g.getv('SandFX'), Tag='Burst',
         Location=g.f(SC + 'K2_GetComponentLocation', self=g.arg('Pivot')), Scale=g.arg('Crumble'), Strength=1.0,
         Duration=1.4, Extra=0.0)
    g.do(SC + 'SetVisibility', self=g.arg('Pivot'), bNewVisibility=False, bPropagateToChildren=False)
    g.side(held, False)
    g.group('Next spot in the stream')
    # each new thing forms a gap past the previous one of its kind (ground or air), inside the window ahead of the car
    ground = g.arg('Ground')
    last = g.math('SelectFloat', A=g.getv('LastGround'), B=g.getv('LastAir'), bPickA=ground)
    gap = g.math('RandomFloatInRange', Min=g.math('SelectFloat', A=C.GAP_GROUND[0], B=C.GAP_AIR[0], bPickA=ground),
                 Max=g.math('SelectFloat', A=C.GAP_GROUND[1], B=C.GAP_AIR[1], bPickA=ground))
    g.setv('TmpD', add(g, last, gap))
    lo = lambda: add(g, car(g, 'Distance'), C.AHEAD[0])  # noqa: E731
    stale = either(g, lt(g, g.getv('TmpD'), lo()), ge(g, g.getv('TmpD'), add(g, car(g, 'Distance'), C.AHEAD[1] + C.STALE)))
    g.setv('TmpD', g.math('SelectFloat', A=add(g, lo(), g.math('RandomFloatInRange', Min=0, Max=C.GAP_GROUND[1])),
                          B=g.getv('TmpD'), bPickA=stale))
    room = g.branch(lt(g, g.getv('TmpD'), add(g, car(g, 'Distance'), C.AHEAD[1])))
    g.side(room, False)
    g.do(SC + 'SetVisibility', self=g.arg('Pivot'), bNewVisibility=False, bPropagateToChildren=False)
    g.side(room)
    g.setv('LastGround', g.math('SelectFloat', A=g.getv('TmpD'), B=g.getv('LastGround'), bPickA=g.arg('Ground')))
    g.setv('LastAir', g.math('SelectFloat', A=g.getv('LastAir'), B=g.getv('TmpD'), bPickA=g.arg('Ground')))
    g.group('Pick a spot ahead')
    bucket = g.math('Add_IntInt', A=g.math('Multiply_IntInt', A=car(g, 'RailIndex'), B=C.BUCKETS),
                    B=g.math('FTrunc', A=g.math('Divide_DoubleDouble', A=g.getv('TmpD'), B=C.BUCKET)))
    g.setv('TmpLane', g.f(STR + 'GetSubstring', SourceString=g.getv('Lanes'), StartIndex=bucket, Length=1))
    lane = lambda c: g.f(STR + 'EqualEqual_StrStr', A=g.getv('TmpLane'), B=c)  # noqa: E731
    right = either(g, lane('R'), both(g, lane('B'), g.math('RandomBool')))
    g.setv('TmpSide', g.math('SelectFloat', A=C.RIGHT, B=C.LEFT, bPickA=right))
    in_leg = both(g, ge(g, g.getv('TmpD'), C.STOP_CLEAR[0]), lt(g, g.getv('TmpD'), sub(g, car(g, 'RouteLength'), C.STOP_CLEAR[1])))
    clear = either(g, NOT(g, g.arg('Ground')), lane('R'), lane('L'), lane('B'))
    spot = g.branch(both(g, in_leg, clear))
    g.side(spot, False)
    g.do(SC + 'SetVisibility', self=g.arg('Pivot'), bNewVisibility=False, bPropagateToChildren=False)
    g.side(spot)
    g.group('Form there')
    lateral = g.math('SelectFloat', A=g.getv('TmpSide'), B=g.arg('Lateral'), bPickA=g.arg('Ground'))
    up = g.math('MakeVector', X=0, Y=0, Z=add(g, g.arg('Height'), C.GROUND_Z))
    side_off = g.math('Multiply_VectorFloat', A=rail_at(g, 'RightVector', g.getv('TmpD')), B=lateral)
    g.setv('TmpPos', g.math('Add_VectorVector', A=g.math('Add_VectorVector', A=rail_at(g, 'Location', g.getv('TmpD')), B=side_off), B=up))
    heading = g.f(K + 'BreakRotator', InRot=rail_at(g, 'Rotation', g.getv('TmpD')))
    yaw = add(g, add(g, (heading[0], 'Yaw'), g.math('SelectFloat', A=0, B=180, bPickA=g.math('RandomBool'))), g.arg('YawOffset'))
    g.do(SC + 'K2_SetWorldLocationAndRotation', self=g.arg('Pivot'), NewLocation=g.getv('TmpPos'),
         NewRotation=g.math('MakeRotator', Yaw=yaw), bSweep=False, bTeleport=True)
    g.do(SC + 'SetVisibility', self=g.arg('Pivot'), bNewVisibility=True, bPropagateToChildren=False)
    gate(g, g.f(SL + 'IsValid', Object=g.arg('Mover')))
    g.do(PM + ':SetVelocityInLocalSpace', self=g.arg('Mover'), NewVelocity=g.arg('Velocity'))
    g.finish()


def hide_all():
    g = G(BP, 'HideAll')
    for name, _, _ in tend_args():
        g.do(SC + 'SetVisibility', self=g.getv(name), bNewVisibility=False, bPropagateToChildren=False)
    g.finish()


def step():
    """Every 0.25 s: find the car once it exists; tend the pool while it drives a rail, hide it when it stops."""
    g = G(BP, 'Step')
    g.group('Find the car')
    find = g.branch(NOT(g, g.f(SL + 'IsValid', Object=g.getv('Car'))))
    g.side(find)
    found = g.do(GS + 'GetActorOfClass', ActorClass=cls(CAR))
    g.setv('Car', g.cast(found, cls(CAR), 'BP L2Car'))
    g.side(find, False)
    g.group('Driving')
    live = g.branch(both(g, car(g, 'Active'), car(g, 'RouteReady'), g.f(SL + 'IsValid', Object=car(g, 'Rail'))))
    g.side(live, False)
    gate(g, g.getv('Shown'))
    g.own('HideAll')
    g.setv('Shown', False)
    g.side(live)
    g.setv('Shown', True)
    g.group('Tend the pool')
    for name, mover, pins in tend_args():
        if mover:
            pins = dict(pins, Mover=g.getv(mover))
        g.own('Tend', Pivot=g.getv(name), **pins)
    g.finish()


def setup():
    g = G(BP, 'Setup')
    g.group('Sand and movers')
    fx = g.do(cls(SANDLIB) + ':GetSandFX')
    g.setv('SandFX', (fx[0], 'SandFX'))
    for mover, target in MOVERS:
        g.do('/Script/Engine.MovementComponent:SetUpdatedComponent', self=g.getv(mover), NewUpdatedComponent=g.getv(target))
    g.own('HideAll')
    g.do(SL + 'K2_SetTimer', FunctionName='Step', Time=C.STEP, bLooping=True)
    g.finish()


def events():
    ns, _ = R.b.inspect(BP, 'EventGraph')
    batch = R.b.Batch(BP, 'EventGraph')
    if ns:
        batch.ops.append(dict(op='remove', node_ids=[n['node_id'] for n in ns]))
    batch.ops.append(dict(op='add_event', ref='begin', event_name='ReceiveBeginPlay', x=0, y=0))
    batch.fn('setup', cls(BP) + ':Setup', 320, 0)
    batch.chain('begin', 'setup')
    batch.comment('City life', ['begin', 'setup'])
    batch.run()


def graphs():
    for fn in (hide_all, tend, step, setup, events):
        fn()


STEPS = {'skeleton': skeleton, 'graphs': graphs, 'Tend': tend, 'Step': step, 'HideAll': hide_all, 'Setup': setup,
         'events': events}

if __name__ == '__main__':
    for name in sys.argv[1:]:
        STEPS[name]()
