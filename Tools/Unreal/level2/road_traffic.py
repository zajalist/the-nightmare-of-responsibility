"""Move the existing sedan mesh through Queen Street's two lanes."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_drive as b

ROAD_MIN, ROAD_MAX = 6400, 54300
SEDAN = b.D.ROOT + '/SM_L2Sedan/SM_L2Sedan/StaticMeshes/SM_L2Sedan'
# Traffic is bounded by the scanned road and stays outside the entry and hiring bays.
CARS = (
    ('TrafficEastA', 12900, 435, 540),
    ('TrafficWestA', 22000, -410, -650),
    ('TrafficEastB', 29400, 540, 630),
    ('TrafficWestB', 38800, -310, -560),
    ('TrafficEastC', 47800, 660, 590),
)


def declare():
    info = b.call('blueprint_get_info', path=b.ROAD)
    existing = {row['name'] for row in info['components']}
    for name, *_ in CARS:
        body = name+'Collision'
        if body not in existing:
            b.call('blueprint_add_component', path=b.ROAD, component_name=body,
                   component_class_path='/Script/Engine.BoxComponent', parent='Root')
        if name not in existing:
            b.call('blueprint_add_component', path=b.ROAD, component_name=name,
                   component_class_path='/Script/Engine.StaticMeshComponent', parent=body)
    if 'StepTraffic' not in info['functions']:
        b.call('blueprint_add_function', path=b.ROAD, function_name='StepTraffic',
               inputs=[dict(name='Delta', type='float'), dict(name='Driver', type='vector')])
    b.call('python_exec_file', path=Path(__file__).resolve().as_posix(), env={'FOA_TRAFFIC_TEMPLATE':'1'},
           resources=['asset:'+b.ROAD])


def build():
    g = b.G(b.ROAD, 'StepTraffic')
    driver = g.math('BreakVector', InVec=g.arg('Driver'))[0]
    dt = g.math('FClamp', Value=g.arg('Delta'), Min=0, Max=.1)
    for name, _, lane, speed in CARS:
        car = g.getv(name+'Collision')
        location = g.f(b.SC+'K2_GetComponentLocation', self=car)
        travel_sign = 1 if speed > 0 else -1
        coords = g.math('BreakVector', InVec=location)[0]
        x = (coords, 'X')
        gap = g.math('Multiply_DoubleDouble', A=travel_sign,
                     B=g.math('Subtract_DoubleDouble', A=(driver,'X'), B=x))
        cross = g.math('Abs', A=g.math('Subtract_DoubleDouble', A=(driver,'Y'), B=(coords,'Y')))
        ahead = g.math('InRange_FloatFloat', Value=gap, Min=0, Max=700)
        yielding = g.math('BooleanAND', A=ahead, B=g.math('Less_DoubleDouble', A=cross, B=215))
        rate = g.math('SelectFloat', A=0, B=speed, bPickA=yielding)
        step = g.math('Multiply_DoubleDouble', A=rate, B=dt)
        new_x = g.math('Add_DoubleDouble', A=x, B=step)
        # Both ends are outside the playable Queen Street job route.
        at_end = g.math('Greater_DoubleDouble' if speed>0 else 'Less_DoubleDouble',
                        A=new_x, B=ROAD_MAX if speed>0 else ROAD_MIN)
        new_x = g.math('SelectFloat', A=ROAD_MIN if speed>0 else ROAD_MAX, B=new_x, bPickA=at_end)
        y = g.math('Add_DoubleDouble', A=lane, B=g.math('Multiply_DoubleDouble', A=new_x, B=.0075))
        destination = g.math('MakeVector', X=new_x, Y=y, Z=2)
        g.do(b.SC+'K2_SetWorldLocation', self=car, NewLocation=destination, bSweep=False, bTeleport=True)
    g.finish()


def templates():
    import unreal as u
    from free_drive_setup import templates as get_templates

    _, sub, lib, _, handles, components = get_templates(b.ROAD)
    mesh = u.load_asset(SEDAN)
    assert mesh, SEDAN
    for name, x, lane, speed in CARS:
        component = components[name]
        body_name=name+'Collision'
        body=components[body_name]
        parent=lib.get_parent_handle(lib.get_data(handles[name]))
        if str(lib.get_variable_name(lib.get_data(parent)))!=body_name:
            assert sub.attach_subobject(handles[body_name],handles[name])
        component.set_static_mesh(mesh)
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_editor_property('absolute_location', False)
        component.set_editor_property('relative_location', u.Vector(0,0,-65))
        component.set_editor_property('relative_rotation', u.Rotator())
        component.set_editor_property('cast_shadow', False)
        component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        body.set_mobility(u.ComponentMobility.MOVABLE)
        body.set_box_extent(u.Vector(212,96,60),False)
        body.set_editor_property('absolute_location', True)
        body.set_editor_property('relative_location', u.Vector(x,lane+x*.0075,2))
        body.set_editor_property('relative_rotation', u.Rotator(yaw=0 if speed>0 else 180))
        body.set_editor_property('generate_overlap_events', False)
        body.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
        body.set_collision_object_type(u.CollisionChannel.ECC_WORLD_DYNAMIC)
        body.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_IGNORE)
        body.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN, u.CollisionResponseType.ECR_BLOCK)


if __name__ == '__main__':
    if os.environ.get('FOA_TRAFFIC_TEMPLATE') == '1':
        templates()
    else:
        from finalize_l2_graphs import checked_compile

        owner = 'main-road-traffic'
        os.environ.update(FOA_AGENT=owner, HAYBA_AGENT_ID=owner)
        b.D.OWNER = owner
        token = b.h.lease_acquire(owner, ['asset:'+path for path in (b.ROAD,b.CAR,b.MET)], ttl_s=240, wait_s=15)
        os.environ['FOA_LEASE'] = token
        try:
            assert not b.call('editor_get_state')['pie_running']
            declare()
            build()
            print(checked_compile(b.ROAD), flush=True)
            if sys.argv[1:] == ['traffic']:
                sys.exit(0)
            b.start_leg(True)
            b.schedule()
            b.drive_step()
            print(checked_compile(b.CAR), flush=True)
            b.call('blueprint_add_variable', path=b.MET, variable_name='NearStrike', variable_type='bool',
                   default_value='false', update_existing=True)
            for graph in (b.meteor_arm, b.meteor_impact, b.meteor_resolve):
                graph()
            print(checked_compile(b.MET), flush=True)
        finally:
            b.h.release(owner, token)
