"""Offline proof-driver/teardown fault injection; not native movement validation."""
import ast
import hashlib
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

HERE=Path(__file__).parent


def selected(file,names):
    tree=ast.parse((HERE/file).read_text())
    return compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),file,'exec')


class V:
    def __init__(self,x=0,y=0,z=0,**kwargs):self.x,self.y,self.z=x,y,z
    def to_tuple(self):return (self.x,self.y,self.z)


class ProofTests(unittest.TestCase):
    def simulate(self,broken=None):
        now=[0.];held=set();callbacks=[];world=NS(get_path_name=lambda:'L_L2_DriveProto.Test')
        class Key:
            def set_editor_property(self,n,v):self.name=v
        class Obj:
            alive=True
            def __init__(self,**props):self.p=props
            def get_editor_property(self,n):return self.p[n]
            def set_editor_property(self,n,v,**kwargs):self.p[n]=v
            def get_world(self):return world
        class Car(Obj):
            def __init__(self):
                super().__init__(Speed=0,NearDestination=False,Arrived=False,Destination=V(15535,80,2),CameraPitch=12)
                self.loc=V(9000,180,2);self.yaw=0
            def get_actor_location(self):return self.loc
            def set_actor_location(self,v,*args):self.loc=v
            def get_actor_rotation(self):return NS(yaw=self.yaw)
            def set_actor_rotation(self,r,*args):self.yaw=r.yaw
            def get_root_component(self):return collision
            def call_method(self,n,args=None):self.p['Active']=True
        car=Car();meteor=Obj(Active=False);meteor.call_method=lambda n:None
        gi=Obj(SaveSlot='FoA_QA_Play');gi.call_method=lambda *args:None
        collision=Obj();collision.get_unscaled_box_extent=lambda:V(200,90,60)
        camera=Obj(field_of_view=80);camera.get_world_rotation=lambda:NS(yaw=car.yaw+(180 if 'Q' in held and broken!='lookback' else 0))
        camera.get_world_location=lambda:V(car.loc.x-830*math.cos(math.radians(car.yaw)),car.loc.y-830*math.sin(math.radians(car.yaw)),car.loc.z+360)
        manager=Obj()
        manager.get_camera_location=lambda:V(car.loc.x,car.loc.y,car.loc.z+5000) if broken=='game_camera' else camera.get_world_location()
        manager.get_camera_rotation=lambda:NS(pitch=-12,yaw=car.yaw)
        manager.get_fov_angle=lambda:80
        city=Obj(static_mesh=None if broken=='city_mesh' else NS(get_path_name=lambda:'/Game/CityCollision'),
                 visible=broken!='hidden_city',hidden_in_game=False)
        city.get_collision_enabled=lambda:0 if broken=='city_collision' else 1
        road=Obj(CityCollision=city)
        boom=Obj(target_arm_length=850,relative_location=V(0,0,185),do_collision_test=True)
        car.p.update(FollowCamera=camera,CameraBoom=boom,Collision=collision,root_component=collision)
        pc=NS(is_input_key_down=lambda k:k.name in held,get_view_target=lambda:car)
        properties=NS(call_method=lambda method,args:args[0].set_editor_property(args[1],args[2]))
        engine=NS(Key=Key,Vector=V,Rotator=lambda **kwargs:NS(**kwargs),PropertyAccessChangeNotifyMode=NS(NEVER=0),
            get_default_object=lambda cls:properties,
            CollisionEnabled=NS(NO_COLLISION=0),
            SystemLibrary=NS(is_valid=lambda a:a is not None and getattr(a,'alive',True),execute_console_command=lambda *a:None),
            GameplayStatics=NS(get_game_instance=lambda w:gi,get_actor_of_class=lambda w,c:meteor if 'Meteor' in c else road if 'RoadNetwork' in c else car,
                get_player_camera_manager=lambda w,i:manager,
                get_player_controller=lambda w,i:pc,get_global_time_dilation=lambda w:1,set_global_time_dilation=lambda *a:None),
            load_class=lambda a,b:b,register_slate_post_tick_callback=lambda f:callbacks.append(f) or 1,
            unregister_slate_post_tick_callback=lambda h:None)
        with tempfile.TemporaryDirectory() as directory:
            env=dict(unreal=engine,UES=NS(get_game_world=lambda:world),OUT=Path(directory),ROOT='/Game/FoA/Level2/Drive',
                KEYS=('W','A','D','S','Q','Enter','SpaceBar'),GOALS=((15535,80,2),(33770,210,2),(48844,340,2)),
                WALL_A=(8496.873579677855,1840.8293152713597),WALL_B=(10617.315721186593,1810.233980107899),
                Path=Path,hashlib=hashlib,json=json,math=math,os=NS(environ={}),time=NS(monotonic=lambda:now[0]))
            exec(selected('drive_proof.py',{'angle','xy_distance','measured_wall','stop','start'}),env)
            env['start']();s=engine._l2_drive_proof;seen=0;pending=[]
            for frame in range(900):
                now[0]+=.05
                request=Path(directory)/'input_request.json'
                if request.exists():
                    msg=json.loads(request.read_text())
                    if msg['id']>seen:
                        seen=msg['id'];pending.append((now[0]+.1,msg['events']))
                while pending and pending[0][0]<=now[0]:
                    _,events=pending.pop(0)
                    for e in events:
                        if e['event']=='pressed':held.add(e['key'])
                        else:held.discard(e['key'])
                        if e==dict(key='Enter',event='pressed') and car.p['NearDestination']:car.p['Arrived']=True;car.p['Speed']=0
                target=-400 if 'S' in held else 1200 if 'W' in held else 0
                if car.p['Arrived']:target=0
                speed=car.p['Speed'];speed+=max(-45,min(45,target-speed))
                turn=(int('D' in held)-int('A' in held))*max(-1,min(1,speed/500))*3.1
                if broken=='steering':turn=0
                car.yaw+=turn
                dx,dy=math.cos(math.radians(car.yaw))*speed*.05,math.sin(math.radians(car.yaw))*speed*.05
                proposed=V(car.loc.x+dx,car.loc.y+dy,2);wall=s['wall']
                gap=sum((wall['mid'][i]-proposed.to_tuple()[i])*wall['normal'][i] for i in range(2))
                if (s['state'].startswith('wall') and gap<200 and broken!='collision') or (s['state']=='wall_escape' and broken=='wall_stuck'):speed=0
                else:car.loc=proposed
                car.p['Speed']=speed
                car.p['NearDestination']=env['xy_distance'](car.loc.to_tuple(),car.p['Destination'].to_tuple())<=650 and abs(speed)<180
                if broken=='autopark' and car.p['NearDestination']:car.p['Arrived']=True
                callbacks[0](.05)
                if s['done']:break
            result=json.loads((Path(directory)/'proof_done.json').read_text())
            return result,held

    def test_driver_acknowledges_delayed_real_key_requests_and_all_checks(self):
        result,held=self.simulate()
        self.assertEqual(result['reason'],'passed',result.get('error'));self.assertFalse(held)
        for check in ('left','right','reverse','look_back','wall_remains_blocked','wall_reverse_steer_escape','outside_rejected','moving_rejected','no_auto_parking','explicit_parking'):
            self.assertIn(check,result['checks'])
        self.assertEqual(len(result['fixtures']),5)

    def test_driver_catches_missing_steering_collision_lookback_and_autopark(self):
        for failure in ('steering','collision','lookback','autopark','wall_stuck','game_camera'):
            with self.subTest(failure=failure):
                result,_=self.simulate(failure);self.assertEqual(result['reason'],'failed',result)

    def test_missing_hidden_or_noncolliding_placed_city_fails_before_input(self):
        for failure in ('city_mesh','hidden_city','city_collision'):
            with self.subTest(failure=failure),self.assertRaises(AssertionError):self.simulate(failure)

    def test_release_attempts_all_keys_even_when_first_fails_and_end_always_runs(self):
        keys=[];runs=[]
        def call(command,args,**kwargs):
            keys.append(args['key'])
            if args['key']=='W':raise RuntimeError('injected')
            return {'ok':True}
        env=dict(h=NS(call=call),run=lambda *args:runs.append(args))
        exec(selected('drive_burst.py',{'release_inputs','end_pie'}),env)
        with self.assertRaises(AssertionError):env['end_pie']()
        self.assertEqual(keys,['W','A','D','S','Q','Enter','SpaceBar'])
        self.assertEqual(runs[-1],('Tools/Unreal/ui/pie_call.py','FOA_CALL=END'))


if __name__=='__main__':unittest.main()
