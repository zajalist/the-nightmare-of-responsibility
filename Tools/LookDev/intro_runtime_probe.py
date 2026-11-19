"""Bounded real frontend route. Driver restores the exact Settings.sav bytes."""
import json
import os
import time
import unreal

ART_REVIEW=os.environ.get('FOA_INTRO_ART_REVIEW')=='1'
OUT='P:/FoA/Saved/LookDev/intro_restored/'+('rice_ink/'+os.environ.get('FOA_INTRO_ART_OUTPUT','runtime_absorption') if ART_REVIEW else 'runtime')
W='/Game/FoA/UI/Intro/WBP_IntroStory.WBP_IntroStory_C'
FE='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
S={'start':time.monotonic(),'phase':0,'last':-1.,'rows':[],'handle':None,'story':None,'nextshot':3.,'art_next':5.}
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world,'PIE required'
host=unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,FE))
assert host,'Front end required'
mpc=unreal.load_asset('/Game/FoA/UI/Style/MPC_UI')
original_reduce=unreal.MaterialLibrary.get_scalar_parameter_value(world,mpc,'ReduceMotion')
settings=unreal.GameplayStatics.load_game_from_slot('Settings',0)
assert settings,'Settings fixture requires an existing saved preference file'
# The outer harness snapshots/restores the exact Settings.sav bytes.
assert settings.get_editor_property('bSeenIntro') and settings.get_editor_property('IntroVersionSeen')>=2, 'Returning-player regression needs the already-seen save'
# editor-rules: the real route must never write the player's FoA.sav; progress goes to a QA slot (as pie_play.py)
gi=unreal.GameplayStatics.get_game_instance(world)
S['ctx']=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_UI',set(),[]))
gi.call_method('ResetProgress')
assert str(gi.get_editor_property('SaveSlot'))=='FoA_QA_UI','proof progress context not set: not running the route'
host.call_method('OnSplashFinished')
host.call_method('OnTitleConfirmed')
host.call_method('WakeUp')


def finish(error=None):
    unreal.MaterialLibrary.set_scalar_parameter_value(world,mpc,'ReduceMotion',original_reduce)
    unreal.unregister_slate_post_tick_callback(S['handle'])
    try:  # back to the player's slot, reloaded from disk; never lose the run's outputs over the restore
        gi.call_method('SetProofProgressContext',S['ctx'])
        gi.call_method('LoadProgress')
        unreal.GameplayStatics.delete_game_in_slot('FoA_QA_UI',0)
    except Exception as ex:
        error=(error or '')+f' | restore_error {ex!r}'[:200]
    with open(OUT+'/proof.json','w') as f:json.dump({'error':error,'rows':S['rows']},f,indent=2)


def tick(dt):
    try:
        t=time.monotonic()-S['start']
        if t>32:
            finish()
            return
        if S['phase']==0 and t>=2:
            S['story']=host.get_editor_property('Story')
            if S['story']:S['phase']=1
            elif t>6:raise AssertionError('Real WakeUp route did not create the intro')
        story=S['story']
        if not story:return
        if ART_REVIEW and t>=S['art_next'] and story.get_editor_property('Index')<7 and not story.get_editor_property('bDone'):
            story.call_method('NextPanel');S['art_next']+=3.
        if S['phase']==1 and t>=12:
            unreal.MaterialLibrary.set_scalar_parameter_value(world,mpc,'ReduceMotion',1.)
            S['phase']=2
        if S['phase']==2 and t>=15:
            unreal.MaterialLibrary.set_scalar_parameter_value(world,mpc,'ReduceMotion',0.)
            S['phase']=3
        if t-S['last']>=.5:
            S['last']=t
            def layer(n):
                v=story.get_editor_property(n)
                tr=v.get_editor_property('render_transform')
                material=v.get_editor_property('brush').resource_object
                texture=material.get_texture_parameter_value('Texture') if isinstance(material,unreal.MaterialInstanceDynamic) else material
                return {'x':tr.translation.x,'scale':tr.scale.x,'alpha':v.get_render_opacity(),'texture':texture.get_name() if texture else None,'material':material.get_name() if material else None,'reveal':material.get_scalar_parameter_value('Reveal') if isinstance(material,unreal.MaterialInstanceDynamic) else None,'ink':str(material.get_vector_parameter_value('Ink')) if isinstance(material,unreal.MaterialInstanceDynamic) else None}
            S['rows'].append({'t':round(t,3),'panel':story.get_editor_property('Index'),
                'done':story.get_editor_property('bDone'),'in_viewport':story.is_in_viewport(),
                'motion':story.get_editor_property('Motion'),'reduce':unreal.MaterialLibrary.get_scalar_parameter_value(world,mpc,'ReduceMotion'),
                'far':layer('Img_Panel'),'near':layer('Img_Near'),'figure':layer('Img_Figure'),
                'waking':host.get_editor_property('bWaking'),'gameplay':host.get_editor_property('bInGameplay')})
            with open(OUT+'/live.json','w') as f:json.dump(S['rows'][-1],f)
        if t>=S['nextshot'] and t<27:
            S['nextshot']+=.4
            unreal.SystemLibrary.execute_console_command(world,f'Shot showui -nosuffix filename="{OUT}/frames/f{int(t*10):04d}.bmp"')
    except Exception as ex:
        finish(str(ex))


S['handle']=unreal.register_slate_post_tick_callback(tick)
print('PIE-only intro fixture armed for 32 seconds')

