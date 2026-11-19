"""Continuous steering over the mapped city; splines are checkpoint metadata only.

Native Blueprint authoring, no runtime Python. Collision setup is separate.
Superseded 2026-11-17 by the rails drive (drive_rails.py): checkpoint, destination, move and schedule now build the
rails versions so an older applier (build_job_hunt route, apply_free_drive) cannot bring the steering back.
park, hide_sign and setup are still used as they are.
"""
import build_drive as b
import drive_data as D

GOALS=D.GOALS
PARK_COMPONENTS=('DestinationPost','BayEdgeLeft','BayEdgeRight')


def setup():
    for name,typ,value in [('Destination','vector','15535,80,2'),('NearDestination','bool','false'),
                           ('RouteMarkerIndex','int','-1'),('UsedShelter','bool','false')]:
        b.call('blueprint_add_variable',path=b.CAR,variable_name=name,variable_type=typ,
               default_value=value,category='Drive',update_existing=True)
    b.call('blueprint_add_variable',path=b.CAR,variable_name='PreviousDriveTransform',variable_type='transform',category='Drive',update_existing=True)
    info=b.call('blueprint_get_info',path=b.CAR)
    for name in ('PlaceAtCheckpoint','CheckDestination','CheckShelter'):
        if name not in info['functions']:b.call('blueprint_add_function',path=b.CAR,function_name=name)
    components={c['name'] for c in info.get('components',[])}
    if 'Collision' not in components:
        b.call('blueprint_add_component',path=b.CAR,component_name='Collision',component_class_path='/Script/Engine.BoxComponent')
    info=b.call('blueprint_get_info',path=b.ROAD)
    for name,kind in [('CityCollision','StaticMeshComponent'),('DestinationMarker','StaticMeshComponent'),('CitySky','StaticMeshComponent'),
                      *((name,'StaticMeshComponent') for name in PARK_COMPONENTS),
                      ('DestinationLabel','TextRenderComponent'),('ShelterSouth','TextRenderComponent'),('ShelterNorth','TextRenderComponent')]:
        if name not in {c['name'] for c in info.get('components',[])}:
            b.call('blueprint_add_component',path=b.ROAD,component_name=name,component_class_path='/Script/Engine.'+kind)


def vector(g,value):return g.math('MakeVector',**dict(zip('XYZ',value)))



def checkpoint(all_jobs=False):
    import drive_rails
    return drive_rails.place_at_checkpoint()


def move():
    import drive_rails
    return drive_rails.move()


def destination(all_jobs=False):
    import drive_rails
    return drive_rails.check_destination()


def shelter():
    g=b.G(b.CAR,'CheckShelter')
    fresh=g.branch(g.math('Not_PreBool',A=g.getv('UsedShelter')));g.side(fresh)
    position=g.f(b.A+'K2_GetActorLocation')
    close=[g.math('Less_DoubleDouble',A=g.math('Vector_Distance',V1=position,V2=vector(g,p)),B=540) for p in D.SHELTERS]
    can=g.math('BooleanAND',A=g.math('BooleanOR',A=close[0],B=close[1]),
               B=g.math('Less_DoubleDouble',A=g.math('Abs',A=g.getv('Speed')),B=320))
    can=g.math('BooleanAND',A=can,B=g.math('Less_IntInt',A=g.getv('Composure'),B=100))
    recover=g.branch(can);g.side(recover)
    g.setv('UsedShelter',True)
    g.setv('Composure',g.math('Clamp',Value=g.math('Add_IntInt',A=g.getv('Composure'),B=22),Min=0,Max=100))
    g.do(b.GS+'PlaySound2D',Sound='/Game/FoA/Audio/SFX/Dream/SFX_Dream_ReverseSwell_01.SFX_Dream_ReverseSwell_01',VolumeMultiplier=.23)
    g.finish()


def park(all_jobs=False):
    g=b.G(b.CAR,'Continue')
    ready=g.math('BooleanAND',A=g.getv('Active'),B=g.getv('NearDestination'))
    ready=g.math('BooleanAND',A=ready,B=g.math('Not_PreBool',A=g.getv('Arrived')))
    ready=g.math('BooleanAND',A=ready,B=g.math('Not_PreBool',A=g.getv('Failed')))
    gate=g.branch(ready);g.side(gate)
    for name,value in [('Arrived',True),('Speed',0),('Throttle',False),('BrakeHeld',False)]:g.setv(name,value)
    if all_jobs:
        from job_route import NAMES
        places=NAMES;arrival=g.getv('ArrivalJob')
    else:places=('Queen Market','Night Dispatch','Northline Supply');arrival=g.getv('Leg')
    place=places[0]
    for i in range(1,len(places)):place=g.math('SelectString',A=places[i],B=place,bPickA=g.math('EqualEqual_IntInt',A=arrival,B=i))
    g.setv('Place',g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=place))
    g.do(b.cls(b.MET)+':Hide',self=g.getv('Meteor'))
    hide_sign(g)
    valid=g.branch(g.f(b.SL+'IsValid',Object=g.getv('Journey')));g.side(valid)
    journey=g.cast(g.getv('Journey'),b.cls(b.JOURNEY),'BP L2Journey')
    g.do(b.cls(b.JOURNEY)+':Arrive',self=journey,StopIndex=arrival)
    g.finish()


def hide_sign(g):
    road=g.getv('Road')
    for name in ('DestinationMarker','DestinationLabel',*PARK_COMPONENTS):
        g.do(b.SC+'SetVisibility',self=g.getv(name,road,b.ROAD),bNewVisibility=False,bPropagateToChildren=False)


def schedule():
    import drive_rails
    return drive_rails.schedule()
