"""One focused full-body side photo of the real wake pose; no video, pose forcing or scene edits."""
import datetime,json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
fe=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
d=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
folder=Path('P:/FoA/Saved/CharacterShots/sleep_side')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True,exist_ok=True)
S=dict(start=time.time(),phase=0,h=None,pose={})

def view_report(name):
    rows={}
    for part in ('Body','Face','StartOutfit'):
        c=p.get_editor_property(part);o,e,r=unreal.SystemLibrary.get_component_bounds(c)
        rows[part]=dict(bounds_origin=list(o.to_tuple()),bounds_extent=list(e.to_tuple()),
                       head=list(c.get_socket_location('head').to_tuple()),
                       **{key:str(c.get_editor_property(key)) for key in ('owner_no_see','hidden_in_game','use_attach_parent_bound','component_use_fixed_skel_bounds')})
    rows['camera']=dict(component=str(p.get_editor_property('FollowCamera').get_world_transform()),
                        actual_location=str(pc.player_camera_manager.get_camera_location()),
                        actual_rotation=str(pc.player_camera_manager.get_camera_rotation()),
                        close=p.get_editor_property('bCameraClose'),actor_hidden=p.get_editor_property('hidden'))
    S['pose'][name]=rows

def finish(reason):
    unreal.unregister_slate_post_tick_callback(S['h'])
    result=dict(reason=reason,folder=str(folder),pose=S['pose'])
    (folder/'evidence.json').write_text(json.dumps(result,indent=1))
    Path('P:/FoA/Saved/CharacterShots/sleep_side/latest.json').write_text(json.dumps(result,indent=1))

def tick(dt):
    try:
        t=time.time()-S['start']
        if t>25:return finish('timeout')
        if S['phase']==0 and t>.3:fe.call_method('OnSplashFinished',());S['phase']=1
        elif S['phase']==1 and t>1:fe.call_method('OnTitleConfirmed',());S['phase']=2
        elif S['phase']==2 and t>1.8:fe.call_method('WakeUp',());S['phase']=3
        elif S['phase']==3:
            seq=d.get_editor_property('SeqPlayer')
            if not seq:return
            q=seq.get_current_time();seconds=(q.time.frame_number.value+q.time.sub_frame)*q.rate.denominator/q.rate.numerator
            if seconds<11:return
            body=p.get_editor_property('Body')
            S['pose']=dict(sequence_seconds=seconds,actor=str(p.get_actor_transform()),bones={})
            for b in ('pelvis','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r','ball_l','ball_r','head'):
                v=body.get_socket_location(b);S['pose']['bones'][b]=[v.x,v.y,v.z]
            def xf(tr):
                q=tr.rotation;v=tr.translation;s=tr.scale3d
                return dict(position=[v.x,v.y,v.z],rotation=[q.x,q.y,q.z,q.w],scale=[s.x,s.y,s.z])
            bones=[]
            for i in range(body.get_num_bones()):
                name=body.get_bone_name(i)
                bones.append(dict(name=str(name),**xf(body.get_socket_transform(name,unreal.RelativeTransformSpace.RTS_COMPONENT))))
            (folder/'body_pose.json').write_text(json.dumps(dict(mesh=body.get_skeletal_mesh_asset().get_path_name(),
                space='component',world=xf(body.get_world_transform()),bones=bones),indent=1))
            seq.set_disable_camera_cuts(True)
            camera=p.get_editor_property('FollowCamera')
            camera.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            eye=unreal.Vector(258,35,105);aim=unreal.Vector(258,-191,64)
            camera.set_world_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
            camera.set_field_of_view(65)
            pc.set_view_target_with_blend(p,0)
            S['ready']=t+.5;S['phase']=4
        elif S['phase']==4 and t>S['ready']:
            view_report('full_body_view')
            unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(folder/'full_body_side.png')+' -nosuffix',pc)
            S['ready']=t+.5;S['phase']=5
        elif S['phase']==5 and t>S['ready']:
            # Separate pillow/eye evidence, after the full-body image has landed.
            # A low side angle makes a real gap beneath the skull visible.
            camera=p.get_editor_property('FollowCamera')
            eye=unreal.Vector(325,-112,102);aim=unreal.Vector(329,-191,81)
            camera.set_world_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
            camera.set_field_of_view(38)
            face=p.get_editor_property('Face');anim=face.get_anim_instance()
            S['pose']['face']=dict(mesh=face.get_skeletal_mesh_asset().get_path_name(),
                sleep=p.get_editor_property('SleepEyeClosure'),
                blink_l=face.get_morph_target('eyeBlinkLeft'),
                blink_r=face.get_morph_target('eyeBlinkRight'))
            S['ready']=t+.5;S['phase']=6
        elif S['phase']==6 and t>S['ready']:
            view_report('pillow_view')
            unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(folder/'face_pillow_closed_eyes.png')+' -nosuffix',pc)
            S['ready']=t+.5;S['phase']=7
        elif S['phase']==7 and t>S['ready']:return finish('photo_requires_visual_review')
    except Exception as e:
        S['pose']['error']=repr(e);finish('error')
S['h']=unreal.register_slate_post_tick_callback(tick)
