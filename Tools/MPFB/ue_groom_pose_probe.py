"""Actual cinematic pose, matched strand visibility only; bounded owned PIE diagnostic."""
import json,time,os
from pathlib import Path
import unreal
editor_pose=os.environ.get('FOA_GROOM_EDITOR_POSE')=='1'
sub=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w=sub.get_editor_world() if editor_pose else sub.get_game_world();assert w
if editor_pose:assert not sub.get_game_world()
def actor(path):return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=actor('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d=actor('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
p=face=hair=None
out=Path('P:/FoA/Saved/CharacterShots/groom_pose');out.mkdir(exist_ok=True,parents=True)
gs=unreal.get_default_object(unreal.GameplayStatics);tr=unreal.Transform()
cap=gs.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.SceneCapture2D.static_class(),tr,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cap=gs.call_method('FinishSpawningActor',(cap,tr,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cc=cap.capture_component2d;cc.fov_angle=40;cc.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
cc.texture_target=unreal.RenderingLibrary.create_render_target2d(w,1280,960,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.capture_every_frame=True;cc.always_persist_rendering_state=True
pps=cc.post_process_settings;pps.override_dynamic_global_illumination_method=True;pps.dynamic_global_illumination_method=unreal.DynamicGlobalIlluminationMethod.LUMEN
pps.override_reflection_method=True;pps.reflection_method=unreal.ReflectionMethod.LUMEN;cc.post_process_settings=pps
S={'start':time.monotonic(),'phase':3 if editor_pose else 0,'h':None,'error':None,'samples':[]}
def camera(eye,aim,fov):
    eye=unreal.Vector(*eye);aim=unreal.Vector(*aim)
    cap.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True);cc.fov_angle=fov
def shot(name):
    players=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'))
    assert p in players,'Captured actor replaced during diagnostic'
    visible=hair.is_visible();expected=not name.endswith('_off') and name not in ('wide_removed','fp_handoff')
    S['samples'].append({'shot':name,'actor':p.get_path_name(),'hair_visible':visible,'cast_shadow':hair.get_editor_property('cast_shadow')})
    assert visible==expected,'Hair visibility was overridden during diagnostic'
    unreal.RenderingLibrary.export_render_target(w,cc.texture_target,str(out),name+'.png')
def restore_hair():
    if S.get('restored'):return
    if S.get('asset_removed'):hair.set_groom_asset(unreal.load_asset(S['groom_path']));hair.set_binding_asset(unreal.load_asset(S['binding_path']) if S['binding_path'] else None)
    if 'visible' in S:hair.set_visibility(S['visible']);face.set_visibility(S['face_visible']);hair.set_cast_shadow(S['cast_shadow'])
    if 'tick_enabled' in S:p.set_actor_tick_enabled(S['tick_enabled'])
    S['asset_removed']=False
    S['restored']=True

def finish(reason):
    unreal.unregister_slate_post_tick_callback(S['h'])
    restore_hair()
    if S.get('seq'):S['seq'].play()
    cap.destroy_actor();(out/'report.json').write_text(json.dumps({k:v for k,v in S.items() if k not in ('seq','h')},indent=1));(out/'done.txt').write_text(reason)
def tick(dt):
    global p,face,hair
    try:
        t=time.monotonic()-S['start']
        if t>28:return finish('timeout')
        if S['phase']==0 and t>.2:fe.call_method('OnSplashFinished');S['phase']=1
        elif S['phase']==1 and t>.6:fe.call_method('OnTitleConfirmed');S['phase']=2
        elif S['phase']==2 and t>1:fe.call_method('WakeUp');S['phase']=3
        elif S['phase']==3:
            if not editor_pose:
                story=fe.get_editor_property('Story')
                if story and story.is_in_viewport():story.call_method('Finish');return
                seq=d.get_editor_property('SeqPlayer')
                if not seq:return
                q=seq.get_current_time();seconds=(q.time.frame_number.value+q.time.sub_frame)*q.rate.denominator/q.rate.numerator
                if seconds<11:return
                S['sequence_seconds']=seconds;S['seq']=seq;seq.pause()
            players=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'))
            S['players']=[{'path':a.get_path_name(),'hidden':a.get_editor_property('hidden')} for a in players]
            visible=[a for a in players if not a.get_editor_property('hidden')]
            assert len(players)==1 or len(visible)==1,S['players']
            p=players[0] if len(players)==1 else visible[0]
            S['actor_hidden']=p.get_editor_property('hidden')
            face=p.get_editor_property('Face');hair=p.get_editor_property('Hair')
            S['tick_enabled']=p.is_actor_tick_enabled();p.set_actor_tick_enabled(False)
            S['grooms']=[]
            for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
                for g in a.get_components_by_class(unreal.GroomComponent):
                    S['grooms'].append({'path':g.get_path_name(),'asset':str(g.get_editor_property('groom_asset')),'binding':str(g.get_editor_property('binding_asset')),'parent':str(g.get_attach_parent()),'socket':str(g.get_attach_socket_name()),'relative':g.get_relative_transform().export_text(),'visible':g.is_visible(),'cast_shadow':g.get_editor_property('cast_shadow')})
            S['face_asset']=str(face.get_skinned_asset())
            S['face_materials']=[str(face.get_material(i)) for i in range(face.get_num_materials())]
            body=p.get_editor_property('Body')
            expected=json.loads(Path('P:/FoA/Saved/Integration/manual_sleep_integrated.json').read_text())['expected_world']
            S['pose_world']={n:list(body.get_socket_location(n).to_tuple()) for n in expected}
            S['pose_error_cm']={n:sum((a-b)**2 for a,b in zip(S['pose_world'][n],v))**.5 for n,v in expected.items()}
            def xf(v):return {'position':list(v.translation.to_tuple()),'rotation':[v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w],'scale':list(v.scale3d.to_tuple())}
            bones=[{'name':str(body.get_bone_name(i)),**xf(body.get_socket_transform(body.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT))} for i in range(body.get_num_bones())]
            (out/'body_pose.json').write_text(json.dumps({'mesh':body.get_skinned_asset().get_path_name(),'space':'component','world':xf(body.get_world_transform()),'bones':bones},indent=1))
            S['visible']=hair.is_visible();S['face_visible']=face.is_visible();S['cast_shadow']=hair.get_editor_property('cast_shadow');hair.set_visibility(True);face.set_visibility(True)
            S['head_world']=list(face.get_socket_location('head').to_tuple())
            S['hair_bounds']=str(unreal.SystemLibrary.get_component_bounds(hair));S['face_bounds']=str(unreal.SystemLibrary.get_component_bounds(face))
            hx,hy,hz=S['head_world'];camera((hx-5,hy+80,hz+20),(hx+5,hy,hz),40);S['phase']=4;S['ready']=t+1
        elif S['phase']==4 and t>S['ready']:shot('head_on');hair.set_cast_shadow(False);S['phase']=40;S['ready']=t+.6
        elif S['phase']==40 and t>S['ready']:shot('head_geometry_only');hair.set_visibility(False);S['phase']=5;S['ready']=t+.6
        elif S['phase']==5 and t>S['ready']:
            shot('head_off');hair.set_visibility(True);camera((260,70,175),(290,-191,145),80);S['phase']=6;S['ready']=t+.8
        elif S['phase']==6 and t>S['ready']:shot('wide_on');hair.set_visibility(False);S['phase']=7;S['ready']=t+.6
        elif S['phase']==7 and t>S['ready']:
            shot('wide_off');S['groom_path']=hair.get_editor_property('groom_asset').get_path_name();binding=hair.get_editor_property('binding_asset');S['binding_path']=binding.get_path_name() if binding else None
            hair.set_groom_asset(None);S['asset_removed']=True;S['phase']=8;S['ready']=t+.8
        elif S['phase']==8 and t>S['ready']:
            shot('wide_removed')
            if editor_pose:return finish('complete')
            restore_hair();S['seq'].play();S.pop('seq');d.call_method('SkipWakeUp')
            S['phase']=9;S['ready']=t+1
        elif S['phase']==9 and t>S['ready']:
            players=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'))
            S['after_skip_handoff']=[{'path':a.get_path_name(),'hidden':a.get_editor_property('hidden')} for a in players]
            S['wake_done']=d.get_editor_property('bWakeDone')
            S['handoff_face_visible']=face.is_visible();S['handoff_hair_visible']=hair.is_visible()
            cam=p.get_editor_property('FollowCamera');loc=cam.get_world_location();rot=cam.get_world_rotation()
            cap.set_actor_location_and_rotation(loc,rot,False,True);cc.fov_angle=cam.field_of_view
            S['handoff_camera']={'position':list(loc.to_tuple()),'rotation':str(rot),'parent':str(cam.get_attach_parent()),'socket':str(cam.get_attach_socket_name())}
            S['phase']=10;S['ready']=t+.7
        elif S['phase']==10 and t>S['ready']:
            shot('fp_handoff');S['visible']=hair.is_visible();S['face_visible']=face.is_visible();S['tick_enabled']=p.is_actor_tick_enabled();S['restored']=False
            p.set_actor_tick_enabled(False);hair.set_visibility(True);face.set_visibility(True)
            hx,hy,hz=face.get_socket_location('head').to_tuple();camera((hx+55,hy+95,hz+10),(hx,hy,hz-25),65)
            S['standing_hair']={'socket':str(hair.get_attach_socket_name()),'relative':hair.get_relative_transform().export_text(),'head':list(face.get_socket_location('head').to_tuple())}
            S['phase']=11;S['ready']=t+.7
        elif S['phase']==11 and t>S['ready']:
            shot('standing');source=p.get_editor_property('mesh');source.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            source.set_animation(unreal.load_asset('/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach'));source.set_position(4.95,False);source.set_play_rate(0)
            S['phase']=12;S['ready']=t+.8
        elif S['phase']==12 and t>S['ready']:
            hx,hy,hz=face.get_socket_location('head').to_tuple();camera((hx+55,hy+95,hz+10),(hx,hy,hz-25),65)
            S['reach_hair']={'socket':str(hair.get_attach_socket_name()),'relative':hair.get_relative_transform().export_text(),'head':list(face.get_socket_location('head').to_tuple())}
            S['phase']=13;S['ready']=t+.7
        elif S['phase']==13 and t>S['ready']:shot('reaching');return finish('complete')
        if editor_pose:cc.capture_scene()
    except Exception as ex:S['error']=repr(ex);finish('error')
S['h']=unreal.register_slate_post_tick_callback(tick)
