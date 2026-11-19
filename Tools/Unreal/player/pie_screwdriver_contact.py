"""Bounded final-Teen screw contact fixture. Production Blueprint turning API, not input proof."""
import datetime,json,math,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C');door=find('/Game/FoA/Gameplay/BP_Door.BP_Door_C')
inv=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
assert d.get_editor_property('bWakeDone') and pc.get_view_target()==p and not p.get_editor_property('bCinematic')
gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_ScrewGrip',set(),[]))
folder=Path('P:/FoA/Saved/AnimShots/screwdriver')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True)
out=Path('P:/FoA/Saved/Integration/screwdriver_contact_final.json')
parts={c.get_name():c for c in door.get_components_by_class(unreal.SceneComponent)}
cam=parts['ToolCamera'];camera_original=(cam.get_editor_property('relative_location'),cam.get_editor_property('relative_rotation'),cam.field_of_view)
S=dict(start=time.time(),last=time.time(),h=None,done=False,phase=0,rows=[],samples=[],step=-1,shot_steps=set(),wide=False)
def xf(t):return dict(position=list(t.translation.to_tuple()),rotation=list(t.rotation.to_tuple()),scale=list(t.scale3d.to_tuple()))
def restore_camera():
    cam.set_relative_location_and_rotation(camera_original[0],camera_original[1],False,True)
    cam.set_field_of_view(camera_original[2])
def capture(label):
    row=dict(label=label,t=time.time()-S['start'],step=door.get_editor_property('ToolStepIndex'),angle=door.get_editor_property('ToolAngle'),pawn=xf(p.get_actor_transform()))
    body=p.get_editor_property('Body')
    bones=[dict(name=str(body.get_bone_name(i)),**xf(body.get_socket_transform(body.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT))) for i in range(body.get_num_bones())]
    path=folder/(label+'_body.json');path.write_text(json.dumps(dict(mesh=body.get_skeletal_mesh_asset().get_path_name(),space='component',world=xf(body.get_world_transform()),bones=bones)))
    row.update(Body=str(path),tool=xf(p.get_editor_property('HeldTool').get_world_transform()),contact=xf(parts['ToolContact'].get_world_transform()))
    S['rows'].append(row)
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(folder/(label+'.png'))+' -nosuffix',pc)
def sample(now):
    if now<S.get('sample_at',0):return
    S['sample_at']=now+.05
    body=p.get_editor_property('Body');tool=p.get_editor_property('HeldTool');box=tool.get_editor_property('static_mesh').get_bounding_box();tr=tool.get_world_transform()
    tip=unreal.MathLibrary.transform_location(tr,unreal.Vector((box.min.x+box.max.x)/2,(box.min.y+box.max.y)/2,box.max.z))
    shaft=tr.rotation.rotate_vector(unreal.Vector(0,0,1));shaft.normalize()
    shoulder,elbow,wrist=[body.get_socket_location(n) for n in ('upperarm_r','lowerarm_r','hand_r')]
    upper,lower=shoulder-elbow,wrist-elbow
    dot=lambda a,b:a.x*b.x+a.y*b.y+a.z*b.z
    acos=lambda x:math.degrees(math.acos(max(-1.,min(1.,x))))
    target=parts['ToolContact'].get_world_location()
    S['samples'].append(dict(t=now-S['start'],step=S['step'],seconds_since_step=now-S['step_at'],angle=door.get_editor_property('ToolAngle'),
        tip_error_cm=(tip-target).length(),axis_error_deg=acos(dot(shaft,parts['Pivot'].get_forward_vector())),
        grip_error_cm=(p.get_editor_property('HeldToolGrip').get_world_location()-p.get_editor_property('ToolGripWorld')).length(),
        elbow_flex_deg=180-acos(dot(upper,lower)/(upper.length()*lower.length())),reach_ratio=(wrist-shoulder).length()/(upper.length()+lower.length()),
        target=list(target.to_tuple()),tip=list(tip.to_tuple()),shoulder=list(shoulder.to_tuple()),elbow=list(elbow.to_tuple()),wrist=list(wrist.to_tuple()),pawn=list(p.get_actor_location().to_tuple())))
def finish(reason):
    if S['done']:return
    S['done']=True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        restore_camera()
        if door.get_editor_property('bToolActive') or door.get_editor_property('bToolReleasing'):door.call_method('CancelDoorTool',())
    finally:
        gi.call_method('SetProofProgressContext',original);unreal.GameplayStatics.delete_game_in_slot('FoA_QA_ScrewGrip',0)
        result=dict(status='complete',reason=reason,folder=str(folder),rows=S['rows'],samples=S['samples'],checks=S.get('checks'),driver='Production Blueprint API; OS input not asserted')
        out.write_text(json.dumps(result,indent=1));(folder/'evidence.json').write_text(json.dumps(result,indent=1))
def tick(dt):
    try:
        now=time.time()
        if now-S['start']>24:return finish('timeout')
        if S['phase']==0:
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            d.call_method('EnterBeat',(5,));inv.call_method('Add',('Screwdriver',));door.call_method('SetState',('KeyJammed',True))
            boot=door.get_editor_property('BootProgressionSource')
            if boot:boot.call_method('SetState',('Worn',True));d.call_method('ReportEvent',('BootsWorn',))
            door.call_method('Interact',('Use','Screwdriver'));assert door.get_editor_property('bToolActive');S['phase']=1
        elif S['phase']==1 and door.get_editor_property('bToolReady'):
            S.update(step=0,step_at=now,hold=now+.04,phase=2)
        elif S['phase']==2 and now>=S['hold']:
            sample(now);capture('first_ready');S.update(phase=3,hold=now+.25)
        elif S['phase']==3 and now>=S['hold']:
            target=parts['ToolContact'].get_world_location();eye=p.get_actor_location()+unreal.Vector(-95,-135,125)
            cam.set_world_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,target-unreal.Vector(0,0,20)),False,True);cam.set_field_of_view(55)
            S.update(phase=4,hold=now+.5)
        elif S['phase']==4 and now>=S['hold']:
            capture('stance');S.update(phase=5,hold=now+.2)
        elif S['phase']==5 and now>=S['hold']:
            restore_camera();S.update(phase=6,hold=now+.3)
        elif S['phase']==6 and now>=S['hold']:
            if not door.get_editor_property('bToolActive'):
                S['phase']=7;return
            step=door.get_editor_property('ToolStepIndex')
            if step!=S['step']:S.update(step=step,step_at=now)
            sample(now)
            if now-S['step_at']>.4 and step not in S['shot_steps']:
                capture('screw_'+str(step+1));S['shot_steps'].add(step)
            door.call_method('AdvanceDoorTool',(1.,min(dt,.1)))
        elif S['phase']==7 and not door.get_editor_property('bToolReleasing'):
            assert str(door.get_editor_property('State'))=='PlateOff' and door.get_editor_property('ToolStepIndex')==4
            assert not pc.is_move_input_ignored() and not pc.is_look_input_ignored() and pc.get_view_target()==p
            assert not p.get_editor_property('bCinematic') and 'Screwdriver' in [str(x) for x in inv.get_editor_property('Items')]
            settled=[r for r in S['samples'] if r['seconds_since_step']>.4]
            checks=dict(all_four_targets=set(r['step'] for r in settled)==set(range(4)),max_tip_cm=max(r['tip_error_cm'] for r in settled),max_axis_deg=max(r['axis_error_deg'] for r in settled),max_grip_cm=max(r['grip_error_cm'] for r in settled),elbow_range=[min(r['elbow_flex_deg'] for r in settled),max(r['elbow_flex_deg'] for r in settled)],first_ready=S['samples'][0],turn_max_by_step={i:max((r['angle'] for r in settled if r['step']==i),default=0) for i in range(4)},controls_released=True)
            S['checks']=checks
            assert checks['all_four_targets'] and checks['max_tip_cm']<.15 and checks['max_grip_cm']<.15 and checks['max_axis_deg']<.2,checks
            assert checks['first_ready']['tip_error_cm']<.15 and checks['first_ready']['grip_error_cm']<.15,checks['first_ready']
            assert all(v>650 for v in checks['turn_max_by_step'].values()),checks['turn_max_by_step']
            return finish('four_screws_contact_and_release_passed')
    except Exception as exc:finish('failed:'+repr(exc))
S['h']=unreal.register_slate_post_tick_callback(tick)
