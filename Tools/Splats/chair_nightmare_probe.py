"""Bounded PIE proof: painting gate, full vision, exact restoration, interrupted reset."""
import json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
def actor(path):return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
vision=actor('/Game/FoA/Gameplay/Ambient/BP_ChairNightmare.BP_ChairNightmare_C')
room=actor('/Game/FoA/Gameplay/Ambient/BP_RoomTakeover.BP_RoomTakeover_C');assert vision and room
chair=vision.get_editor_property('ChairMesh');assert chair
out=Path('P:/FoA/Saved/WorldShots/chair_nightmare');out.mkdir(parents=True,exist_ok=True)
def snapshot():
    tr=chair.get_world_transform()
    return {'transform':{'location':list(tr.translation.to_tuple()),'rotation':[tr.rotation.x,tr.rotation.y,tr.rotation.z,tr.rotation.w],'scale':list(tr.scale3d.to_tuple())},'mesh':chair.static_mesh.get_path_name(),
            'materials':[chair.get_material(i).get_path_name() for i in range(chair.get_num_materials())],
            'overlay':chair.get_overlay_material().get_path_name() if chair.get_overlay_material() else None,
            'visible':chair.is_visible(),'hidden':chair.get_editor_property('hidden_in_game'),
            'collision':str(chair.get_collision_enabled()),'profile':str(chair.get_collision_profile_name())}
room.call_method('Reset');vision.call_method('Reset');baseline=snapshot()
fe=actor('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
pawn=unreal.GameplayStatics.get_player_character(w,0);hair=pawn.get_editor_property('Hair');face=pawn.get_editor_property('Face')
eye=unreal.Vector(-80,60,145);aim=chair.get_world_location()+unreal.Vector(0,0,90)
transform=unreal.Transform(location=eye,rotation=unreal.MathLibrary.find_look_at_rotation(eye,aim))
gs=unreal.get_default_object(unreal.GameplayStatics)
cap=gs.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.SceneCapture2D.static_class(),transform,
    unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cap=gs.call_method('FinishSpawningActor',(cap,transform,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
rt=unreal.RenderingLibrary.create_render_target2d(w,1280,960,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc=cap.capture_component2d;cc.texture_target=rt;cc.fov_angle=65;cc.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
cc.capture_every_frame=True;cc.always_persist_rendering_state=True
pps=cc.post_process_settings
pps.override_dynamic_global_illumination_method=True;pps.dynamic_global_illumination_method=unreal.DynamicGlobalIlluminationMethod.LUMEN
pps.override_reflection_method=True;pps.reflection_method=unreal.ReflectionMethod.LUMEN
cc.post_process_settings=pps
S={'start':time.monotonic(),'game_start':unreal.GameplayStatics.get_time_seconds(w),'phase':0,'rows':[],'shots':[],'last':0,'checks':{},'h':None,'error':None,'hair_phase':0,'boot':0}
def hair_inventory():
    rows=[]
    for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
        for c in a.get_components_by_class(unreal.GroomComponent):
            rows.append({'path':c.get_path_name(),'asset':str(c.get_editor_property('groom_asset')),'binding':str(c.get_editor_property('binding_asset')),'parent':str(c.get_attach_parent()),'visible':c.is_visible(),'transform':str(c.get_world_transform()),'bounds':str(unreal.SystemLibrary.get_component_bounds(c))})
    return {'grooms':rows,'face_materials':[str(face.get_material(i)) for i in range(face.get_num_materials())]}
def shot(name):
    unreal.RenderingLibrary.export_render_target(w,rt,str(out),name+'.png');S['shots'].append(name)
def finish(reason):
    unreal.unregister_slate_post_tick_callback(S['h']);unreal.GameplayStatics.set_game_paused(w,False);room.call_method('Reset');vision.call_method('Reset')
    if 'hair_visible' in S:hair.set_visibility(S['hair_visible']);face.set_visibility(S['face_visible'])
    S['checks']['final_exact_restoration']=snapshot()==baseline;cap.destroy_actor()
    report={'reason':reason,'checks':S['checks'],'rows':S['rows'],'shots':S['shots'],'baseline':baseline,'final':snapshot(),'error':S['error']}
    (out/'runtime.json').write_text(json.dumps(report,indent=2));(out/'done.txt').write_text(reason)
def tick(dt):
    try:
        wall=time.monotonic()-S['start']
        if wall>27:return finish('timeout')
        if S['boot']<4:
            if S['boot']==0 and wall>.2:fe.call_method('OnSplashFinished');S['boot']=1
            elif S['boot']==1 and wall>.6:fe.call_method('OnTitleConfirmed');S['boot']=2
            elif S['boot']==2 and wall>1:fe.call_method('WakeUp');S['boot']=3
            elif S['boot']==3 and wall>1.5:
                story=fe.get_editor_property('Story')
                if story and story.is_in_viewport():story.call_method('Finish');return
                S['game_start']=unreal.GameplayStatics.get_time_seconds(w);S['boot']=4
            return
        t=unreal.GameplayStatics.get_time_seconds(w)-S['game_start']
        if S['hair_phase']==0 and t>4:
            S['hair_visible']=hair.is_visible();S['face_visible']=face.is_visible();S['chair_camera']=cap.get_actor_transform()
            head=face.get_socket_location('head');camera=head+unreal.Vector(-55,-65,35)
            cap.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,head+unreal.Vector(4,0,4)),False,True);cc.fov_angle=38
            unreal.GameplayStatics.set_game_paused(w,True);hair.set_visibility(True);face.set_visibility(True)
            S['hair_phase']=1;S['hair_clock']=time.monotonic();S['hair_head_world']=list(head.to_tuple())
            (out/'hair_inventory.json').write_text(json.dumps(hair_inventory(),indent=1))
        if S['hair_phase'] in (1,2,3,4):
            cc.capture_scene()
            if time.monotonic()-S['hair_clock']>.45:
                if S['hair_phase']==1:
                    shot('groom_on');hair.set_visibility(False);S['hair_phase']=2;S['hair_clock']=time.monotonic()
                elif S['hair_phase']==2:
                    shot('groom_off');hair.set_visibility(True)
                    camera=unreal.Vector(265,30,140)
                    cap.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,unreal.Vector(270,-191,100)),False,True);cc.fov_angle=85
                    S['hair_phase']=3;S['hair_clock']=time.monotonic()
                elif S['hair_phase']==3:
                    shot('groom_wide_on');hair.set_visibility(False);S['hair_phase']=4;S['hair_clock']=time.monotonic()
                else:
                    shot('groom_wide_off');hair.set_visibility(S['hair_visible']);face.set_visibility(S['face_visible'])
                    cap.set_actor_transform(S['chair_camera'],False,True);cc.fov_angle=65
                    unreal.GameplayStatics.set_game_paused(w,False);S['hair_phase']=5
            return
        if t-S['last']>.10:
            active=vision.get_editor_property('bActive');count=vision.get_editor_property('PlayCount')
            elapsed=unreal.GameplayStatics.get_time_seconds(w)-vision.get_editor_property('StartTime')
            S['rows'].append({'t':t,'elapsed':elapsed,'active':active,'plays':count,'chair_visible':chair.is_visible(),
                'shell_visible':vision.get_editor_property('ChairShell').is_visible(),'suit_visible':vision.get_editor_property('Apparition').is_visible()})
            S['last']=t
            if active and count==1:
                for at,name in ((.30,'darkening'),(1.15,'chair_erosion'),(2.8,'apparition'),(4.5,'crumble'),(5.55,'chair_reform')):
                    if elapsed>=at and name not in S['shots']:shot(name)
        if S['phase']==0 and t>.6:shot('before');room.call_method('SetStage',(4,));S['phase']=1
        elif S['phase']==1 and t>1.7:
            S['checks']['blocked_without_painting']=vision.get_editor_property('PlayCount')==0
            room.call_method('InspectPainting');S['phase']=2
        elif S['phase']==2 and t>4.8:
            S['checks']['painting_scene_not_overlapped']=vision.get_editor_property('PlayCount')==0
            S['phase']=20
        elif S['phase']==20 and t>13.5:
            S['checks']['natural_exact_restoration']=snapshot()==baseline
            S['checks']['played_once']=vision.get_editor_property('PlayCount')==1 and vision.get_editor_property('bPlayed')
            shot('restored');room.call_method('Reset');S['phase']=3
        elif S['phase']==3 and t>14:
            S['checks']['reset_rearmed']=not vision.get_editor_property('bPlayed')
            room.call_method('SetStage',(4,));room.call_method('InspectPainting')
            # The first run proves the quiet period; advance only the second-run fixture to test interruption.
            vision.call_method('StartVision');S['phase']=4
        elif S['phase']==4 and t>15.2:
            S['checks']['second_vision_started']=vision.get_editor_property('PlayCount')==2 and vision.get_editor_property('bActive')
            room.call_method('Reset');S['phase']=5
        elif S['phase']==5 and t>16:
            S['checks']['interrupted_exact_restoration']=snapshot()==baseline and not vision.get_editor_property('bActive')
            shot('reset_restored')
            body=pawn.get_editor_property('Body')
            def xf(v):return {'position':list(v.translation.to_tuple()),'rotation':[v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w],'scale':list(v.scale3d.to_tuple())}
            bones=[{'name':str(body.get_bone_name(i)),**xf(body.get_socket_transform(body.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT))} for i in range(body.get_num_bones())]
            (out/'body_pose.json').write_text(json.dumps({'mesh':body.get_skeletal_mesh_asset().get_path_name(),'space':'component','world':xf(body.get_world_transform()),'bones':bones},indent=1))
            camera=unreal.Vector(345,-112,98);cap.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,unreal.Vector(350,-191,79)),False,True);cc.fov_angle=40
            S['phase']=6;S['head_clock']=time.monotonic()
        elif S['phase']==6 and time.monotonic()-S['head_clock']>.35:
            shot('head_support');camera=unreal.Vector(258,35,105)
            cap.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,unreal.Vector(258,-191,64)),False,True);cc.fov_angle=65
            S['head_clock']=time.monotonic();S['phase']=7
        elif S['phase']==7 and time.monotonic()-S['head_clock']>.35:shot('whole_sleep_support');finish('complete')
    except Exception as ex:S['error']=repr(ex);finish('error')
S['h']=unreal.register_slate_post_tick_callback(tick)
print('CHAIR_PROBE_ARMED')

