"""26s actual wake/lying + normal movement capture, after the real front-end/phone roam boot.
Uses the shipping wake sequence and ordinary AddMovementInput; never changes animation mode/poses.
"""
import json
import datetime
import math
import os
import time
from pathlib import Path
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(); assert w
p = unreal.GameplayStatics.get_player_character(w, 0)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
source, body, face = [p.get_editor_property(n) for n in ('Mesh', 'Body', 'Face')]
base_folder = Path('P:/FoA/Saved/CharacterShots/walk_sleep')
folder = base_folder / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
motion=folder/'walk_motion'; motion.mkdir(exist_ok=True)
S = dict(start=time.time(), phase=-3 if os.environ.get('FOA_COLD_BOOT')=='1' else 0, rows=[], h=None, done=False, shot=set(), walking=False,frames=[],next_frame=18.0)


def sample(label, pose=False):
    a = source.get_anim_instance(); f = face.get_anim_instance()
    root = source.get_socket_location('root') - p.get_actor_location()
    row = dict(label=label, t=round(time.time()-S['start'], 3), position=str(p.get_actor_location()),
        velocity=str(p.get_velocity()), source_mode=str(source.get_animation_mode()), source_class=a.get_class().get_name(),
        body_class=body.get_anim_instance().get_class().get_name(), root_relative=[root.x, root.y, root.z],
        sleep=p.get_editor_property('SleepEyeClosure'), blinkL=f.get_curve_value('CTRL_expressions_eyeBlinkL'),
        blinkR=f.get_curve_value('CTRL_expressions_eyeBlinkR'), move_ignored=pc.is_move_input_ignored())
    velocity=p.get_velocity()
    row['actor_yaw']=p.get_actor_rotation().yaw
    if math.hypot(velocity.x,velocity.y)>70:
        desired=math.degrees(math.atan2(velocity.y,velocity.x))
        row['movement_yaw']=desired
        row['facing_error']=abs((row['actor_yaw']-desired+180)%360-180)
    if a.get_class().get_name() == 'ABP_FoAPlayer_C':
        row.update(speed=a.get_editor_property('GroundSpeed'), should_move=a.get_editor_property('ShouldMove'), root_mode=str(a.get_editor_property('RootMotionMode')))
    if label.startswith('lying'):
        for component,key in ((source,'source'),(body,'body')):
            head=component.get_socket_transform('head',unreal.RelativeTransformSpace.RTS_COMPONENT).translation
            pelvis=component.get_socket_transform('pelvis',unreal.RelativeTransformSpace.RTS_COMPONENT).translation
            delta=head-pelvis
            row[key+'_head_from_pelvis']=[delta.x,delta.y,delta.z]
    S['rows'].append(row)
    if pose:
        def xf(t):
            q=t.rotation
            return dict(position=[t.translation.x,t.translation.y,t.translation.z],rotation=[q.x,q.y,q.z,q.w],scale=[t.scale3d.x,t.scale3d.y,t.scale3d.z])
        for component,suffix in ((body,'_bones'),(source,'_source_bones')):
            bones=[]
            for i in range(component.get_num_bones()):
                name=component.get_bone_name(i); t=component.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT)
                bones.append(dict(name=str(name),**xf(t)))
            (folder/(label+suffix+'.json')).write_text(json.dumps(dict(mesh=component.get_skeletal_mesh_asset().get_path_name(),space='component',world=xf(component.get_world_transform()),bones=bones),indent=1))
        unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename='+str(folder/(label+'.png'))+' -nosuffix', pc)
    return row


def finish(reason):
    if S['done']: return
    S['done']=True
    if S['h'] is not None: unreal.unregister_slate_post_tick_callback(S['h'])
    result=dict(reason=reason,folder=str(folder),rows=S['rows'],frame_times=S['frames'])
    (folder/'proof.json').write_text(json.dumps(result,indent=1))
    (base_folder/'latest.json').write_text(json.dumps(result,indent=1)); print('WALK_SLEEP',reason)


def tick(dt):
    try:
        t=time.time()-S['start']
        if t>26: return finish('cap')
        if S['phase']==-3 and t>.3:
            fe.call_method('OnSplashFinished',()); S['phase']=-2
        elif S['phase']==-2 and t>1.0:
            fe.call_method('OnTitleConfirmed',()); S['phase']=-1
        elif S['phase']==-1 and t>1.8:
            fe.call_method('WakeUp',()); S['start']=time.time(); S['phase']=1
        elif S['phase']==0:
            d.call_method('BeginMorning', ()); S['phase']=1
        elif S['phase']==1:
            for at,label in ((11,'lying_closed'),(15,'lying_face')):
                if t>at and label not in S['shot']:
                    S['shot'].add(label); row=sample(label,True)
                    assert row['sleep']>.99 and row['blinkL']>.9 and row['blinkR']>.9,row
                    for key in ('source','body'):
                        delta=row[key+'_head_from_pelvis']
                        assert (delta[0]**2+delta[1]**2)**.5>45 and abs(delta[2])<25,('Not visibly supine',row)
            if t>16:
                d.call_method('SkipWakeUp', ()); S['phase']=2
        elif S['phase']==2 and t>17:
            phone=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
            if phone:
                phone.get_component_by_class(unreal.WidgetComponent).get_widget().call_method('DoAction', ())
            # A diagnostic full-body view using the existing player camera only.
            # Shipping sleep shots above remain untouched. Runtime setters avoid
            # editor reconstruction of the character's skeletal components.
            camera=p.get_editor_property('FollowCamera')
            camera.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            eye=unreal.Vector(0,220,160)
            camera.set_world_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,unreal.Vector(80,-70,90)),False,True)
            camera.set_field_of_view(90.0)
            S['phase']=3
        elif S['phase']==3 and t>18:
            eye=unreal.Vector(0,230,160)
            aim=p.get_actor_location()+unreal.Vector(0,0,-8)
            camera=p.get_editor_property('FollowCamera')
            camera.set_world_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
            if os.environ.get('FOA_CAPTURE_MOTION')=='1' and t>=S['next_frame']:
                frame=len(S['frames']); S['frames'].append(t); S['next_frame']=t+.1
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(motion/('frame_%04d.png'%frame))+' -nosuffix',pc)
            if t<20.8: p.add_movement_input(unreal.Vector(-1,0,0),1.0)
            elif 20.8<t<21.8: p.add_movement_input(unreal.Vector(0,1,0),1.0)
            elif 22.3<t<23.5: p.add_movement_input(unreal.Vector(1,0,0),1.0)
            for at,label in ((19,'walk_a'),(20,'walk_b'),(21.4,'turn_north'),(23,'walk_east')):
                if t>at and label not in S['shot']:
                    S['shot'].add(label); row=sample(label,True)
                    assert row.get('speed',0)>70 and row.get('should_move') and 'IGNORE_ROOT_MOTION' in row.get('root_mode','').upper(),row
                    assert row['facing_error']<8,('Walking sideways instead of turning',row)
            if t>24.3:
                row=sample('idle_after',True)
                assert row['sleep']<.01 and 'ABP_FoAPlayer' in row['source_class'],row
                walk=[r for r in S['rows'] if r['label'].startswith('walk_') or r['label']=='turn_north']
                assert len(walk)==4 and all(abs(r['root_relative'][0])<2 and abs(r['root_relative'][1])<2 for r in walk),walk
                return finish('pose_evidence_collected_requires_visual_review')
    except Exception as e:
        S['rows'].append(dict(error=repr(e))); finish('error')


S['h']=unreal.register_slate_post_tick_callback(tick)
print('Actual sleeping and walking capture scheduled26s; ordinary movement input, no pose forcing')
