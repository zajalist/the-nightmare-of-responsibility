"""Unselected transient editor-world hand captures; leaves the manual sequence and viewport alone."""
import unreal,time,json
from pathlib import Path
E=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);w=E.get_editor_world();assert not E.get_game_world()
gs=unreal.get_default_object(unreal.GameplayStatics);made=[]
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
    if a.get_actor_label().startswith('TMP_handQA_'):a.destroy_actor()
out=Path('P:/FoA/Saved/CharacterShots/fingers');out.mkdir(exist_ok=True,parents=True)
def spawn(cls):
    tr=unreal.Transform(location=unreal.Vector(0,0,1500))
    a=gs.call_method('BeginDeferredActorSpawnFromClass',(w,cls.static_class(),tr,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a=gs.call_method('FinishSpawningActor',(a,tr,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT));a.set_actor_label('TMP_handQA_'+str(len(made)));made.append(a);return a
body=spawn(unreal.SkeletalMeshActor);bc=body.skeletal_mesh_component
bc.set_skeletal_mesh_asset(unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body'))
bc.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE);bc.set_animation(unreal.load_asset('/Game/FoA/Characters/Teen/_FingerQA/Target/AS_FingerSource'))
bc.set_position(4.8,False);bc.set_update_animation_in_editor(True)
cap=spawn(unreal.SceneCapture2D);cc=cap.capture_component2d;cc.fov_angle=32
cc.texture_target=unreal.RenderingLibrary.create_render_target2d(w,1000,1000,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR;cc.capture_every_frame=True;cc.always_persist_rendering_state=True
cc.primitive_render_mode=unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST;cc.show_only_actor_components(body)
pp=cc.post_process_settings;pp.override_auto_exposure_method=True;pp.auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL
pp.override_auto_exposure_apply_physical_camera_exposure=True;pp.auto_exposure_apply_physical_camera_exposure=False;cc.post_process_settings=pp
pp.override_auto_exposure_bias=True;pp.auto_exposure_bias=-4;cc.post_process_settings=pp
lights=[]
for i in range(2):
    light=spawn(unreal.PointLight);lc=light.point_light_component
    for k,v in [('intensity_units',unreal.LightUnits.CANDELAS),('intensity',20 if i==0 else 8),('attenuation_radius',300),('source_radius',15)]:lc.set_editor_property(k,v)
    lights.append(light)
shots=[('relaxed_l',5.8,'l'),('relaxed_r',5.8,'r'),('authored_l',.8,'l'),('authored_r',.8,'r')]
S={'i':0,'stage':0,'ready':time.monotonic()+.5,'h':None,'error':None}
def finish():
    unreal.unregister_slate_post_tick_callback(S['h'])
    for a in reversed(made):a.destroy_actor()
    (out/'done.txt').write_text(S['error'] or 'complete')
def tick(dt):
    if time.monotonic()<S['ready']:return
    try:
        name,t,side=shots[S['i']]
        if S['stage']==0:bc.set_position(t,False);S['stage']=1;S['ready']=time.monotonic()+.3
        elif S['stage']==1:
            hand=bc.get_socket_transform('hand_'+side);center=bc.get_socket_location('middle_01_'+side)
            forward=hand.rotation.rotate_vector(unreal.Vector(0,0,1 if side=='l' else -1));right=hand.rotation.rotate_vector(unreal.Vector(1,0,0))
            eye=center+forward*42+right*12
            cap.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,center),False,True)
            lights[0].set_actor_location(center+forward*55+right*30,False,True);lights[1].set_actor_location(center+forward*20-right*45,False,True)
            S['stage']=2;S['ready']=time.monotonic()+.6
        else:
            unreal.RenderingLibrary.export_render_target(w,cc.texture_target,str(out),name+'.png');S['i']+=1
            if S['i']==len(shots):return finish()
            S['stage']=0;S['ready']=time.monotonic()+.1
    except Exception as ex:S['error']=repr(ex);finish()
S['h']=unreal.register_slate_post_tick_callback(tick)
