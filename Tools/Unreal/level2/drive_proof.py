"""Real-input free-driving proof; explicit placement fixtures are recorded.
Outer exclusive runner owns input, save hashes, PIE end and map return.
No graph writes. Hazards are disabled in this movement-only fixture.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import time
import unreal

OUT=Path('P:/FoA/Saved/Codex/l2_drive');OUT.mkdir(parents=True,exist_ok=True)
ROOT='/Game/FoA/Level2/Drive'
UES=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
KEYS=('W','A','D','S','Q','Enter','SpaceBar')
# Independent Toronto massing edge, not driving/collision graph output.
WALL_A=(8496.873579677855,1840.8293152713597)
WALL_B=(10617.315721186593,1810.233980107899)
GOALS=((15535,80,2),(33200,8650,2),(45400,-6800,2))


def angle(value):return (value+180)%360-180
def xy_distance(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])


def measured_wall():
    """Re-measure the source edge; never infer expected contact from a test hit."""
    source=Path('P:/FoA-Assets/level2/toronto/processed/queen_600m')
    raw=(source/'buildings.json').read_bytes();data=json.loads(raw)
    frame=json.loads((source/'corridor.json').read_text())
    building=next(r for r in data['records'] if r['building_id']==137021)
    polygon=json.loads(building['geometry'])['coordinates'][0]
    def ue(point):
        delta=[point[i]-frame['origin_utm_m'][i] for i in range(2)]
        return (sum(delta[i]*frame['along_utm'][i] for i in range(2))*100,
                -sum(delta[i]*frame['left_utm'][i] for i in range(2))*100)
    points=list(map(ue,polygon))
    assert any(xy_distance(a,WALL_A)<.01 and xy_distance(b,WALL_B)<.01 for a,b in zip(points,points[1:])), 'Source wall changed'
    dx,dy=WALL_B[0]-WALL_A[0],WALL_B[1]-WALL_A[1];length=math.hypot(dx,dy)
    normal=(-dy/length,dx/length);mid=tuple((a+b)/2 for a,b in zip(WALL_A,WALL_B))
    return dict(source=str(source/'buildings.json'),sha256=hashlib.sha256(raw).hexdigest(),building_id=137021,
                a=WALL_A,b=WALL_B,mid=mid,normal=normal,heading=math.degrees(math.atan2(normal[1],normal[0])))


def stop():
    old=getattr(unreal,'_l2_drive_proof',None)
    if old and not old['done']:old['finish']('runner_stop')


def start():
    stop();w=UES.get_game_world();assert w,'PIE world not ready'
    assert 'L_L2_DriveProto' in w.get_path_name(),w.get_path_name()
    gi=unreal.GameplayStatics.get_game_instance(w)
    gi.call_method('SetProofProgressContext',('FoA_QA_Play',set(),[]))
    car=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,ROOT+'/BP_L2Car.BP_L2Car_C'))
    meteor=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,ROOT+'/BP_Meteor.BP_Meteor_C'))
    road=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,ROOT+'/BP_L2RoadNetwork.BP_L2RoadNetwork_C'))
    assert car and meteor and road
    pc=unreal.GameplayStatics.get_player_controller(w,0)
    manager=unreal.GameplayStatics.get_player_camera_manager(w,0)
    capture=os.environ.get('FOA_DRIVE_PROOF')=='VIDEO'
    wall=measured_wall();properties=unreal.get_default_object(unreal.SystemLibrary)
    s=dict(start=time.monotonic(),rows=[],samples=[],shots=[],fixtures=[],checks={},id=0,done=False,handle=None,
           state='begin',since=0,pending=None,held=set(),next_shot=0,wall=wall,camera_view=None,city_collision=None)
    time_scale=unreal.GameplayStatics.get_global_time_dilation(w)
    unreal.GameplayStatics.set_global_time_dilation(w,1)
    keys={}
    for name in KEYS:
        key=unreal.Key();key.set_editor_property('key_name',name);keys[name]=key

    def get(name):return car.get_editor_property(name)
    def setv(name,value):
        kind='Bool' if isinstance(value,bool) else 'Int' if isinstance(value,int) else 'Double'
        properties.call_method('Set'+kind+'PropertyByName',(car,name,value))
        if kind=='Double' and get(name)!=value:
            properties.call_method('SetFloatPropertyByName',(car,name,value))
        assert get(name)==value,('Fixture property did not change',name,value,get(name))
    def position():return tuple(car.get_actor_location().to_tuple())
    def snapshot():
        return dict(t=round(time.monotonic()-s['start'],3),state=s['state'],position=position(),
                    yaw=car.get_actor_rotation().yaw,speed=get('Speed'),near=get('NearDestination'),arrived=get('Arrived'))

    def world_alive():
        valid=unreal.SystemLibrary.is_valid
        return (valid(w) and UES.get_game_world()==w and all(valid(a) for a in (car,meteor,road,pc,manager,gi))
                and all(a.get_world()==w for a in (car,meteor,road)))

    def request(*events):
        assert s['pending'] is None,'Input delivery must be acknowledged before next batch'
        s['id']+=1;s['pending']=(events,time.monotonic())
        for event in events:
            if event['event']=='pressed':s['held'].add(event['key'])
            else:s['held'].discard(event['key'])
        tmp=OUT/'input_request.pending'
        tmp.write_text(json.dumps(dict(id=s['id'],events=events)));tmp.replace(OUT/'input_request.json')
        s['rows'].append(dict(kind='actual_input',id=s['id'],events=events))

    def key(name,down):return dict(key=name,event='pressed' if down else 'released')
    def stage(name):s.update(state=name,since=time.monotonic(),baseline=snapshot())
    def mark(name):
        s['checks'][name]=snapshot()
        if not capture and name in ('forward','look_forward','wall_contact','explicit_parking'):
            path=OUT/('free_drive_'+name+'.png')
            unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(path)+' -nosuffix')
            s['shots'].append(dict(t=s['checks'][name]['t'],file=str(path)))

    def fixture(name,at,yaw=0,speed=0):
        assert not s['held'],'Release actual keys before fixture placement'
        setv('Speed',float(speed));setv('Throttle',False);setv('BrakeHeld',False)
        car.set_actor_location(unreal.Vector(*at),False,True)
        car.set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),True)
        setv('CameraReady',False)
        s['fixtures'].append(dict(kind='checkpoint_fixture',name=name,position=at,yaw=yaw,speed=speed,
                                 excluded_from_driven_distance=True))

    def finish(reason,error=None):
        if s['done']:return
        s['done']=True
        if s['handle'] is not None:unreal.unregister_slate_post_tick_callback(s['handle'])
        if world_alive():unreal.GameplayStatics.set_global_time_dilation(w,time_scale)
        result={k:s[k] for k in ('rows','samples','shots','fixtures','checks','wall','camera_view','city_collision')}
        result.update(reason=reason,error=error,elapsed=round(time.monotonic()-s['start'],3),
                      scope='Free driving and parking with real keyboard input; labelled fixtures; hazards excluded')
        (OUT/('video_done.json' if capture else 'proof_done.json')).write_text(json.dumps(result,indent=1))
    s['finish']=finish;unreal._l2_drive_proof=s
    car.call_method('Activate',(0,))
    setv('MeteorsLeft',0);setv('NextMeteor',999.);meteor.call_method('Hide')
    s['fixtures'].append(dict(kind='hazard_isolation',MeteorsLeft=0,NextMeteor=999,reason='Movement proof only'))
    assert xy_distance(tuple(get('Destination').to_tuple()),GOALS[0])<.1
    camera=get('FollowCamera');boom=get('CameraBoom');collision=get('Collision')
    assert car.get_editor_property('root_component')==collision,'Swept collision must be the root'
    assert tuple(collision.get_unscaled_box_extent().to_tuple())==(200.,90.,60.)
    assert abs(boom.get_editor_property('target_arm_length')-850)<.1
    assert abs(boom.get_editor_property('relative_location').z-185)<.1
    assert boom.get_editor_property('do_collision_test')
    assert abs(camera.get_editor_property('field_of_view')-80)<.1
    assert abs(get('CameraPitch')-12)<.1 and abs(position()[2]-2)<.1,'Road -63 + root lift65'
    city=road.get_editor_property('CityCollision');assert city,'Placed road is missing CityCollision'
    mesh=city.get_editor_property('static_mesh');assert mesh,'Placed city collision has no mesh'
    assert city.get_editor_property('visible') and not city.get_editor_property('hidden_in_game'),'Building backing is hidden'
    assert city.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION,'Building collision is disabled'
    s['city_collision']=dict(mesh=mesh.get_path_name(),visible=True,collision=str(city.get_collision_enabled()))
    mark('camera_and_collision_configuration')

    def verify_game_view():
        eye=manager.get_camera_location();rotation=manager.get_camera_rotation();fov=manager.get_fov_angle()
        offset=tuple(eye.to_tuple()[i]-position()[i] for i in range(3));yaw=math.radians(car.get_actor_rotation().yaw)
        behind=offset[0]*math.cos(yaw)+offset[1]*math.sin(yaw)
        lateral=-offset[0]*math.sin(yaw)+offset[1]*math.cos(yaw)
        s['camera_view']=dict(position=eye.to_tuple(),offset=offset,pitch=rotation.pitch,yaw=rotation.yaw,fov=fov)
        assert pc.get_view_target()==car,'Game view is not owned by the driving car'
        assert -1000<behind<-200 and abs(lateral)<120 and 150<offset[2]<500,('Game camera is not a low chase view',s['camera_view'])
        assert abs(rotation.pitch+12)<2 and abs(angle(rotation.yaw-car.get_actor_rotation().yaw))<3 and abs(fov-80)<.1,s['camera_view']
        assert math.dist(eye.to_tuple(),camera.get_world_location().to_tuple())<2,'Rendered camera differs from FollowCamera'

    def tick(dt):
        if s['done'] or s.get('busy'):return
        s['busy']=True
        try:
            if not world_alive():return finish('PIE ended or replaced')
            assert str(gi.get_editor_property('SaveSlot'))=='FoA_QA_Play'
            now=time.monotonic();elapsed=now-s['start']
            if elapsed>40:return finish('timeout')
            if s['pending']:
                events,sent=s['pending']
                if not all(pc.is_input_key_down(keys[e['key']])==(e['event']=='pressed') for e in events):
                    assert now-sent<4,'Input delivery not acknowledged';return
                s['pending']=None;s['since']=now;s['baseline']=snapshot()
            age=now-s['since'];state=s['state'];pos=position();speed=get('Speed');yaw=car.get_actor_rotation().yaw
            if not s['samples'] or elapsed-s['samples'][-1]['t']>.1:s['samples'].append(snapshot())
            if capture and elapsed>=s['next_shot']:
                path=OUT/f"free_capture_{len(s['shots']):04}.png"
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(path)+' -nosuffix')
                s['shots'].append(dict(t=elapsed,file=str(path)));s['next_shot']=elapsed+.25
            if state=='begin':request(key('W',True));stage('forward')
            elif state=='forward' and age>1.25:
                assert xy_distance(pos,s['baseline']['position'])>350 and speed>700,'W did not accelerate and travel'
                verify_game_view()
                mark('forward');request(key('A',True));stage('left')
            elif state=='left' and age>.65:
                assert angle(yaw-s['baseline']['yaw'])<-20 and pos[1]<s['baseline']['position'][1]-80,'Sustained A did not steer left'
                mark('left');request(key('A',False),key('D',True));stage('right')
            elif state=='right' and age>.65:
                base=s['baseline'];rad=math.radians(base['yaw'])
                lateral=-(pos[0]-base['position'][0])*math.sin(rad)+(pos[1]-base['position'][1])*math.cos(rad)
                assert angle(yaw-base['yaw'])>20 and lateral>80,'Sustained D did not yaw and travel laterally right'
                mark('right');request(key('D',False),key('W',False),key('S',True));stage('brake')
            elif state=='brake' and speed<-.5:
                assert age>.4,'S reversed without braking first'
                mark('braked_through_zero');stage('reverse')
            elif state=='reverse' and age>.6:
                base=s['baseline'];direction=(math.cos(math.radians(base['yaw'])),math.sin(math.radians(base['yaw'])))
                assert sum((pos[i]-base['position'][i])*direction[i] for i in range(2))<-80 and speed<-200,'S did not reverse'
                mark('reverse');request(key('S',False),key('Q',True));stage('look_back')
            elif state=='look_back' and age>1:
                assert abs(abs(angle(camera.get_world_rotation().yaw-yaw))-180)<12,'Q did not look behind'
                mark('look_back');request(key('Q',False));stage('look_forward')
            elif state=='look_forward' and age>1:
                assert abs(angle(camera.get_world_rotation().yaw-yaw))<12,'Q release did not restore chase view'
                mark('look_forward');stage('wall_fixture')
            elif state=='wall_fixture' and age>.3:
                at=tuple(wall['mid'][i]-wall['normal'][i]*1000 for i in range(2))+(2,)
                fixture('independently_measured_building_wall',at,wall['heading'])
                request(key('W',True));stage('wall')
            elif state=='wall' and age>2.8:
                gap=sum((wall['mid'][i]-pos[i])*wall['normal'][i] for i in range(2))
                if not 175<gap<230:
                    end=unreal.Vector(*(pos[i]+wall['normal'][i]*1200 for i in range(2)),pos[2])
                    hits=unreal.SystemLibrary.sphere_trace_multi_for_objects(w,unreal.Vector(*pos),end,200,
                        [getattr(unreal.ObjectTypeQuery,'OBJECT_TYPE_QUERY'+str(i)) for i in range(1,7)],False,[car],
                        unreal.DrawDebugTrace.NONE,True,unreal.LinearColor(),unreal.LinearColor(),0.)
                    if isinstance(hits,tuple) and hits and isinstance(hits[0],bool):hits=hits[1]
                    blockers=[]
                    for hit in hits or []:
                        data=hit.to_tuple();other,component=data[9],data[10]
                        blockers.append(dict(actor=other.get_actor_label() if other else None,component=component.get_name() if component else None,
                                             impact=data[5].to_tuple(),initial=bool(data[1])))
                    raise AssertionError(('Swept box missed or penetrated measured wall',gap,pos,blockers))
                assert speed<5 and xy_distance(pos,s['baseline']['position'])>500,'No real approach then speed reset'
                mark('wall_contact');stage('wall_hold')
            elif state=='wall_hold' and age>.65:
                assert xy_distance(pos,s['baseline']['position'])<5 and speed<5,'Held W penetrated building'
                mark('wall_remains_blocked')
                request(key('W',False),key('S',True),key('A',True));stage('wall_escape')
            elif state=='wall_escape' and age>.8:
                gap=sum((wall['mid'][i]-pos[i])*wall['normal'][i] for i in range(2))
                assert gap>250 and xy_distance(pos,s['baseline']['position'])>80,'Reverse/steer remained stuck at wall'
                assert abs(angle(yaw-s['baseline']['yaw']))>15 and speed<-100,'S+A did not reverse with steering'
                mark('wall_reverse_steer_escape')
                request(key('S',False),key('A',False));stage('outside_fixture')
            elif state=='outside_fixture':
                fixture('outside_parking_radius',(GOALS[0][0]-800,GOALS[0][1],2));stage('outside_wait')
            elif state=='outside_wait' and age>.3:
                assert not get('NearDestination');request(key('Enter',True));stage('outside_enter')
            elif state=='outside_enter' and age>.15:
                assert not get('Arrived'),'Enter parked outside650cm'
                mark('outside_rejected');request(key('Enter',False));stage('fast_fixture')
            elif state=='fast_fixture':
                fixture('inside_radius_but_moving',(GOALS[0][0]-500,GOALS[0][1],2),speed=500)
                request(key('W',True));stage('fast_wait')
            elif state=='fast_wait':
                assert speed>=180 and xy_distance(pos,GOALS[0])<650 and not get('NearDestination')
                request(key('Enter',True));stage('fast_enter')
            elif state=='fast_enter':
                assert speed>=180 and xy_distance(pos,GOALS[0])<650 and not get('Arrived'),'Enter ignored speed gate'
                mark('moving_rejected');request(key('Enter',False),key('W',False));stage('park_fixture')
            elif state=='park_fixture':fixture('inside_radius_stopped',GOALS[0]);stage('park_wait')
            elif state=='park_wait' and age>.7:
                assert speed<180 and get('NearDestination') and not get('Arrived'),'Auto-parked without Enter or destination not ready'
                mark('no_auto_parking');request(key('Enter',True));stage('park_enter')
            elif state=='park_enter' and get('Arrived'):
                assert speed==0 and not meteor.get_editor_property('Active')
                mark('explicit_parking');request(key('Enter',False));stage('final_release')
            elif state=='final_release':
                assert not any(pc.is_input_key_down(k) for k in keys.values()),'Keys still held'
                finish('passed')
        except Exception as exc:finish('failed',repr(exc))
        finally:s['busy']=False
    s['handle']=unreal.register_slate_post_tick_callback(tick)
    print('Free-driving actual-input proof started; bounded at40s')


stop() if os.environ.get('FOA_DRIVE_PROOF')=='STOP' else start()
