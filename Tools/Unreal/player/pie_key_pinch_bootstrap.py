"""Real FE bootstrap for the coordinator's key-only capture; no PIE start/stop."""
import json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
pc=unreal.GameplayStatics.get_player_controller(w,0);p=unreal.GameplayStatics.get_player_character(w,0)
S=dict(start=time.time(),phase=0,after=0,h=None,story=False,skip=False)
out=Path('P:/FoA/Saved/Integration/key_pinch_bootstrap.json')
def finish(reason):
    unreal.unregister_slate_post_tick_callback(S['h'])
    out.write_text(json.dumps(dict(reason=reason,elapsed=time.time()-S['start'])))
def tick(dt):
    try:
        now=time.time()
        if now-S['start']>17:return finish('timeout')
        if now<S['after']:return
        if S['phase']==0:fe.call_method('OnSplashFinished',());S['phase']=1;S['after']=now+.4
        elif S['phase']==1:fe.call_method('OnTitleConfirmed',());S['phase']=2;S['after']=now+.5
        elif S['phase']==2:fe.call_method('WakeUp',());S['phase']=3
        elif S['phase']==3:
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S['story']:
                story.call_method('Finish',());S['story']=True
            elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone') and not S['skip']:
                d.call_method('SkipWakeUp',());S['skip']=True
            elif d.get_editor_property('bWakeDone') and pc.get_view_target()==p and not p.get_editor_property('bCinematic'):
                finish('actual_FE_ready')
                namespace={'__builtins__':__builtins__}
                exec(compile(Path('P:/FoA/Tools/Unreal/player/pie_key_pinch_capture.py').read_text(),
                             'pie_key_pinch_capture.py','exec'),namespace)
    except Exception as exc:finish('failed:'+repr(exc))
S['h']=unreal.register_slate_post_tick_callback(tick)
