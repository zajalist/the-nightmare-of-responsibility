"""Bounded actual-player cloth pulse and smoke check; coordinator owns PIE."""
import json,time,traceback
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0)
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
cloth=p.get_editor_property('StartOutfit');smoke=p.get_editor_property('ClothSmoke')
out=Path('P:/FoA/Saved/ClothShots/runtime');out.mkdir(parents=True,exist_ok=True)
gs=unreal.get_default_object(unreal.GameplayStatics);xf=unreal.Transform()
cap=gs.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.SceneCapture2D.static_class(),xf,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cap=gs.call_method('FinishSpawningActor',(cap,xf,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
cc=cap.capture_component2d;cc.fov_angle=32;cc.capture_every_frame=True;cc.always_persist_rendering_state=True
cc.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
cc.texture_target=unreal.RenderingLibrary.create_render_target2d(w,960,960,unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
S={'start':time.monotonic(),'phase':0,'rows':[],'h':None,'last':0,'shots':[]}
def finish(error=None):
    unreal.unregister_slate_post_tick_callback(S['h']);cap.destroy_actor()
    (out/'report.json').write_text(json.dumps({'error':error,'rows':S['rows'],'shots':S['shots']},indent=1))
def shot(name):
    unreal.RenderingLibrary.export_render_target(w,cc.texture_target,str(out),name+'.png');S['shots'].append(name)
def tick(dt):
    try:
        t=time.monotonic()-S['start'];gt=unreal.SystemLibrary.get_game_time_in_seconds(w)
        if t>32:return finish('timeout')
        if S['phase']==0 and t>.2:fe.call_method('OnSplashFinished');S['phase']=1
        elif S['phase']==1 and t>.6:fe.call_method('OnTitleConfirmed');S['phase']=2
        elif S['phase']==2 and t>1:fe.call_method('WakeUp');S['phase']=3
        elif S['phase']==3:
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport():story.call_method('Finish');return
            if not d.get_editor_property('SeqPlayer'):return
            if not d.get_editor_property('bWakeDone'):d.call_method('SkipWakeUp');return
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            S['phase']=4;S['settle']=t+.25
        if S['phase']>=4:
            if t<S['settle']:return
            aim=p.get_editor_property('Body').get_socket_location('spine_03')+unreal.Vector(0,0,5)
            eye=aim+p.get_actor_forward_vector()*100+unreal.Vector(0,0,10)
            cap.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
            if t-S['last']>.1:
                S['last']=t;mat=cloth.get_material(0)
                assert isinstance(mat,unreal.MaterialInstanceDynamic), (gt,mat.get_path_name() if mat else None)
                pulse=mat.get_scalar_parameter_value('CorruptionPulse');center=mat.get_vector_parameter_value('CorruptionCenter')
                pos=smoke.get_world_location()
                assert (pos-unreal.Vector(center.r,center.g,center.b)).length()<.02,(gt,str(pos),str(center))
                assert -1e-5<=pulse<=1.00001 and 0<center.a<=10.01,(pulse,center)
                S['rows'].append(dict(time=gt,pulse=pulse,smoke=smoke.is_active(),radius=center.a))
            if gt>16 and 'before' not in S['shots']:shot('before')
            if gt>20.3 and 'peak' not in S['shots']:shot('peak')
            if gt>24.5:
                shot('after');rows=S['rows']
                assert max(r['pulse'] for r in rows)>.9 and any(r['smoke'] for r in rows)
                assert rows[-1]['pulse']<.01 and not rows[-1]['smoke'],rows[-1]
                finish()
    except Exception:finish(traceback.format_exc())
S['h']=unreal.register_slate_post_tick_callback(tick)
