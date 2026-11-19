"""Five-second matched-pose hair lobe isolation inside a coordinator-owned battle proof.
Call while commands are held. Transient MID/capture only; no saved asset or camera ownership changes.
"""
import json,time,os,traceback
from pathlib import Path
import unreal
assert os.environ.get('FOA_OWNED_PROOF')=='1'
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);source=p.mesh;body=p.get_editor_property('Body');hair=p.get_editor_property('Hair')
original=hair.get_material(0);ticking=p.is_actor_tick_enabled()
mesh_ticks=[(c,c.is_component_tick_enabled()) for c in p.get_components_by_class(unreal.SkeletalMeshComponent)]
out=Path('P:/FoA/Saved/Integration/cinematic_audit/hair_lighting');out.mkdir(exist_ok=True)
mid=hair.create_dynamic_material_instance(0)
before={'color':mid.get_vector_parameter_value('HairColor'),'roughness':mid.get_scalar_parameter_value('HairRoughness'),'specular':mid.get_scalar_parameter_value('HairSpecular')}
if before['roughness']<=.1:
    hair.set_material(0,original)
    raise AssertionError('Parameterize existing roughness/specular with identical defaults first')
gs=unreal.get_default_object(unreal.GameplayStatics);xf=unreal.Transform()
cap=gs.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.SceneCapture2D.static_class(),xf,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cap=gs.call_method('FinishSpawningActor',(cap,xf,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT));cap.set_actor_label('TMP_character_hair_lighting')
cc=cap.capture_component2d;cc.fov_angle=35;cc.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
cc.texture_target=unreal.RenderingLibrary.create_render_target2d(w,768,768,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.capture_every_frame=True;cc.always_persist_rendering_state=True
pps=cc.post_process_settings;pps.override_dynamic_global_illumination_method=True;pps.dynamic_global_illumination_method=unreal.DynamicGlobalIlluminationMethod.LUMEN
pps.override_reflection_method=True;pps.reflection_method=unreal.ReflectionMethod.LUMEN;cc.post_process_settings=pps
head=body.get_socket_location('head');assert head.z>100,head
aim=head+unreal.Vector(0,0,2);eye=aim+p.get_actor_forward_vector()*105+p.get_actor_right_vector()*65+unreal.Vector(0,0,12)
cap.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
for component,enabled in mesh_ticks:component.set_component_tick_enabled(False)
p.set_actor_tick_enabled(False)
state={'start':time.monotonic(),'phase':0,'h':None,'rows':[],'done':False}
def finish(error=None):
    if state['done']:return
    state['done']=True
    try:
        if state['h']:unreal.unregister_slate_post_tick_callback(state['h'])
        hair.set_material(0,original)
        for component,enabled in mesh_ticks:component.set_component_tick_enabled(enabled)
        p.set_actor_tick_enabled(ticking)
        assert hair.get_material(0)==original,'Hair material did not restore'
    except Exception:error=traceback.format_exc()
    finally:
        cap.destroy_actor()
        (out/'report.json').write_text(json.dumps({'error':error,'baseline':{k:str(v) for k,v in before.items()},'rows':state['rows'],'restored':hair.get_material(0)==original,'capture_destroyed':True},indent=2))
def shot(name):
    assert unreal.GameplayStatics.get_player_character(w,0)==p
    assert p.get_editor_property('Hair')==hair and p.get_editor_property('Body')==body,'Component replaced during test'
    assert hair.get_material(0)==mid,'Transient comparison material replaced'
    current_head=body.get_socket_location('head');assert current_head.z>100,current_head
    if 'held_head' not in state:state['held_head']=current_head
    assert (current_head-state['held_head']).length()<.05,'Pose moved during comparison'
    unreal.RenderingLibrary.export_render_target(w,cc.texture_target,str(out),name+'.png')
    state['rows'].append({'shot':name,'head':list(body.get_socket_location('head').to_tuple()),
        'roughness':mid.get_scalar_parameter_value('HairRoughness'),'specular':mid.get_scalar_parameter_value('HairSpecular'),
        'color':str(mid.get_vector_parameter_value('HairColor'))})
def tick(dt):
    try:
        t=time.monotonic()-state['start']
        if t>7:return finish('timeout')
        if state['phase']==0 and t>1.2:
            shot('before');mid.set_scalar_parameter_value('HairRoughness',.85);mid.set_scalar_parameter_value('HairSpecular',.08);state['phase']=1
        elif state['phase']==1 and t>2.5:
            shot('rough_lobe');mid.set_vector_parameter_value('HairColor',unreal.LinearColor(.004,.003,.002,1));state['phase']=2
        elif state['phase']==2 and t>3.8:
            shot('dark_rough');mid.set_scalar_parameter_value('HairRoughness',before['roughness']);mid.set_scalar_parameter_value('HairSpecular',before['specular']);mid.set_vector_parameter_value('HairColor',before['color']);state['phase']=3
        elif state['phase']==3 and t>5.1:shot('restored');finish()
    except Exception:finish(traceback.format_exc())
state['h']=unreal.register_slate_post_tick_callback(tick)
