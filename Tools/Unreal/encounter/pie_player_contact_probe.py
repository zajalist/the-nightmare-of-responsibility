"""Bounded actual reach/contact/interrupt proof, inside an owned PIE only."""
import unreal,json,time,os,traceback
from pathlib import Path
assert os.environ.get('FOA_OWNED_PROOF')=='1'
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);body=p.get_editor_property('Body')
enc=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'))
garments=list(enc.get_editor_property('Garments'));gar=garments[int(enc.get_editor_property('Target'))]
assert 'Shirt' in gar.get_editor_property('Data').get_path_name()
rig=gar.get_editor_property('Rig');home=rig.get_relative_transform();geometry=json.loads(Path('P:/FoA/Saved/Integration/cinematic_audit/shirt_contact_geometry.json').read_text())
out=Path('P:/FoA/Saved/Integration/cinematic_audit/contact');out.mkdir(exist_ok=True)
gs=unreal.get_default_object(unreal.GameplayStatics);xf=unreal.Transform()
cap=gs.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.SceneCapture2D.static_class(),xf,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cap=gs.call_method('FinishSpawningActor',(cap,xf,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT));cc=cap.capture_component2d
cc.fov_angle=60;cc.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR;cc.texture_target=unreal.RenderingLibrary.create_render_target2d(w,1024,768,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.capture_every_frame=True;cc.always_persist_rendering_state=True
pps=cc.post_process_settings;pps.override_dynamic_global_illumination_method=True;pps.dynamic_global_illumination_method=unreal.DynamicGlobalIlluminationMethod.LUMEN;pps.override_reflection_method=True;pps.reflection_method=unreal.ReflectionMethod.LUMEN;cc.post_process_settings=pps
eye=unreal.Vector(-30,-260,155);aim=unreal.Vector(-65,-45,102);cap.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
S={'h':None,'start':time.monotonic(),'phase':0,'rows':[],'finished':False,'last_sample':-1}
def finish(error=None):
    if S['finished']:return
    S['finished']=True
    try:
        unreal.unregister_slate_post_tick_callback(S['h']);enc.call_method('ClearBattleActing',())
        assert not gar.get_editor_property('bPlayerContact')
        assert (rig.get_relative_transform().translation-home.translation).length()<.001
        light=gar.get_editor_property('ContactFill')
        assert light.get_editor_property('intensity')==0
        assert not rig.get_editor_property('lighting_channels').get_editor_property('channel1')
        assert rig.get_attach_parent()==gar.root_component and light.get_attach_parent()==gar.root_component
    except Exception:error=traceback.format_exc()
    finally:
        after=rig.get_relative_transform()
        delta=dict(translation_cm=(after.translation-home.translation).length(),scale=(after.scale3d-home.scale3d).length(),rotation_components=max(abs(getattr(after.rotation,k)-getattr(home.rotation,k)) for k in ('x','y','z','w')))
        restored=delta['translation_cm']<1e-6 and delta['scale']<1e-6 and delta['rotation_components']<1e-6
        cap.destroy_actor();(out/'report.json').write_text(json.dumps(dict(error=error,rows=S['rows'],restored=restored,restore_delta=delta,capture_destroyed=True),indent=2))
def shot(name):unreal.RenderingLibrary.export_render_target(w,cc.texture_target,str(out),name+'.png')
def measure():
    surface=unreal.Vector()
    for row in geometry['skin_anchor']:
        t=rig.get_socket_transform(row['bone'],unreal.RelativeTransformSpace.RTS_WORLD)
        surface+=unreal.MathLibrary.transform_location(t,unreal.Vector(*row['local']))*row['weight']
    t=body.get_socket_transform('index_03_l',unreal.RelativeTransformSpace.RTS_WORLD)
    fingertip=unreal.MathLibrary.transform_location(t,unreal.Vector(*geometry['fingertip']['local']))
    elapsed=unreal.GameplayStatics.get_time_seconds(w)-gar.get_editor_property('PlayerContactAt')
    S['rows'].append(dict(t=float(elapsed),error_cm=(surface-fingertip).length(),surface=list(surface.to_tuple()),finger=list(fingertip.to_tuple()),relative=list(rig.get_relative_transform().translation.to_tuple()),active=bool(gar.get_editor_property('bPlayerContact'))))
def tick(dt):
    try:
        t=time.monotonic()-S['start']
        if t>8:return finish('timeout')
        if S['phase']==0 and t>.7:
            shot('before');enc.call_method('PlayBattleReach',());assert gar.get_editor_property('bPlayerContact'),'Contact not started';S['action_at']=unreal.GameplayStatics.get_time_seconds(w);S['phase']=1
        elif S['phase']==1:
            elapsed=unreal.GameplayStatics.get_time_seconds(w)-S['action_at']
            if elapsed-S['last_sample']>.035:measure();S['last_sample']=elapsed
            if elapsed>.56 and not S.get('contact_shot'):shot('contact');S['contact_shot']=True
            if elapsed>1.5:
                shot('returned');assert not gar.get_editor_property('bPlayerContact');assert (rig.get_relative_transform().translation-home.translation).length()<.001
                samples=[r for r in S['rows'] if .45<r['t']<.82];assert len(samples)>=3,samples
                assert max(r['error_cm'] for r in samples)<3, samples
                enc.call_method('PlayBattleReach',());S['interrupt_at']=unreal.GameplayStatics.get_time_seconds(w);S['phase']=2
        elif S['phase']==2 and unreal.GameplayStatics.get_time_seconds(w)-S['interrupt_at']>.25:
            assert (rig.get_relative_transform().translation-home.translation).length()>5
            enc.call_method('ClearBattleActing',());assert not gar.get_editor_property('bPlayerContact');assert (rig.get_relative_transform().translation-home.translation).length()<.001
            finish()
    except Exception:finish(traceback.format_exc())
S['h']=unreal.register_slate_post_tick_callback(tick)
