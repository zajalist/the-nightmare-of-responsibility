"""Same actual battle camera/pose, transient localized fill comparison; no saved edits."""
import unreal,json,time,os,traceback
from pathlib import Path
assert os.environ.get('FOA_OWNED_PROOF')=='1'
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
enc=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'))
gar=list(enc.get_editor_property('Garments'))[int(enc.get_editor_property('Target'))]
out=Path('P:/FoA/Saved/Integration/cinematic_audit/contact_fill');out.mkdir(exist_ok=True)
S={'h':None,'start':time.monotonic(),'phase':0,'ticks':[],'actors':[],'light':None,'done':False,'rows':[],'channels':None}
rig=gar.get_editor_property('Rig')
enc.call_method('SetBattleShot',('ResolvePlayerAction',));enc.call_method('PlayBattleReach',())
def finish(error=None):
    if S['done']:return
    S['done']=True
    try:
        unreal.unregister_slate_post_tick_callback(S['h'])
        if S['light']:S['light'].destroy_actor()
        for c,flag in S['ticks']:c.set_component_tick_enabled(flag)
        for a,flag in S['actors']:a.set_actor_tick_enabled(flag)
        if S['channels'] is not None:
            rig.set_lighting_channels(*S['channels'])
            channels=rig.get_editor_property('lighting_channels')
            assert tuple(channels.get_editor_property('channel'+str(i)) for i in range(3))==S['channels']
        unreal.SystemLibrary.un_pause_timer(gar,'StepBattleMotion');enc.call_method('ClearBattleActing',())
    except Exception:error=traceback.format_exc()
    finally:(out/'report.json').write_text(json.dumps(dict(error=error,rows=S['rows'],restored=error is None),indent=2))
def shot(label):
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(out/(label+'.png'))+' -nosuffix',pc)
    S['rows'].append(dict(label=label,head=list(p.get_editor_property('Body').get_socket_location('head').to_tuple()),camera=list(pc.player_camera_manager.get_camera_location().to_tuple()),intensity=S['light'].light_component.get_editor_property('intensity')))
def tick(dt):
    try:
        elapsed=time.monotonic()-S['start']
        if elapsed>8:return finish('timeout')
        if S['phase']==0 and elapsed>.55:
            unreal.SystemLibrary.pause_timer(gar,'StepBattleMotion')
            S['ticks']=[(c,c.is_component_tick_enabled()) for a in (p,gar) for c in a.get_components_by_class(unreal.SkeletalMeshComponent)]
            S['actors']=[(a,a.is_actor_tick_enabled()) for a in (p,gar)]
            for c,flag in S['ticks']:c.set_component_tick_enabled(False)
            for a,flag in S['actors']:a.set_actor_tick_enabled(False)
            channels=rig.get_editor_property('lighting_channels')
            S['channels']=tuple(channels.get_editor_property('channel'+str(i)) for i in range(3))
            rig.set_lighting_channels(S['channels'][0],True,S['channels'][2])
            body=p.get_editor_property('Body');point=body.get_socket_location('index_03_l')+unreal.Vector(50,-70,35)
            gs=unreal.get_default_object(unreal.GameplayStatics);xf=unreal.Transform(location=point)
            light=gs.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.PointLight.static_class(),xf,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            # Native transient light, before registration; never edits a Blueprint component.
            c=light.light_component;c.set_mobility(unreal.ComponentMobility.MOVABLE)
            for k,v in [('intensity_units',unreal.LightUnits.LUMENS),('intensity',0.),('attenuation_radius',170.),('source_radius',8.),('cast_shadows',False),('volumetric_scattering_intensity',0.),('specular_scale',.2)]:c.set_editor_property(k,v)
            c.set_lighting_channels(False,True,False)
            S['light']=gs.call_method('FinishSpawningActor',(light,xf,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT));S['phase']=1;S['held_at']=time.monotonic()
        if S['phase']:
            t=time.monotonic()-S['held_at']
            if S['phase']==1 and t>.55:shot('baseline');S['phase']=2
            elif S['phase']==2 and t>.8:S['light'].light_component.set_intensity(15.);S['phase']=3
            elif S['phase']==3 and t>1.5:shot('shirt15');S['phase']=4
            elif S['phase']==4 and t>1.8:S['light'].light_component.set_intensity(40.);S['phase']=5
            elif S['phase']==5 and t>2.5:shot('shirt40');S['phase']=6
            elif S['phase']==6 and t>2.8:S['light'].light_component.set_intensity(0.);S['phase']=7
            elif S['phase']==7 and t>3.5:shot('restored');S['phase']=8
            elif S['phase']==8 and t>3.8:finish()
    except Exception:finish(traceback.format_exc())
S['h']=unreal.register_slate_post_tick_callback(tick)
