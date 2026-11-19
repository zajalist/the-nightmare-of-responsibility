"""Actual menu/intro readiness before the isolated screwdriver fixture. Never owns PIE."""
import json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
pc=unreal.GameplayStatics.get_player_controller(w,0);p=unreal.GameplayStatics.get_player_character(w,0)
S=dict(start=time.time(),h=None,story=False,skip=False,actions=set(),screens=[])
out=Path('P:/FoA/Saved/Integration/screwdriver_bootstrap.json')
def finish(reason):
    unreal.unregister_slate_post_tick_callback(S['h'])
    out.write_text(json.dumps(dict(reason=reason,elapsed=time.time()-S['start'],screens=S['screens'])))
def tick(dt):
    try:
        if time.time()-S['start']>17:return finish('timeout')
        screen=fe.get_editor_property('Screen')
        if screen and screen.is_in_viewport():
            name=screen.get_class().get_name()
            if not S['screens'] or S['screens'][-1]!=name:S['screens'].append(name)
            for prop,action in [('SplashClass','OnSplashFinished'),('TitleClass','OnTitleConfirmed'),('MainMenuClass','WakeUp')]:
                if screen.get_class()==fe.get_editor_property(prop) and action not in S['actions']:
                    S['actions'].add(action);fe.call_method(action,());return
        story=fe.get_editor_property('Story')
        if story and story.is_in_viewport() and not S['story']:
            story.call_method('Finish',());S['story']=True
        elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone') and not S['skip']:
            d.call_method('SkipWakeUp',());S['skip']=True
        elif d.get_editor_property('bWakeDone') and pc.get_view_target()==p and not p.get_editor_property('bCinematic'):
            assert 'WakeUp' in S['actions'] and S['story'],'Did not traverse actual menu and Story'
            finish('actual_FE_ready')
            path=Path('P:/FoA/Tools/Unreal/player/pie_screwdriver_contact.py')
            exec(compile(path.read_text(),str(path),'exec'),{'__builtins__':__builtins__})
    except Exception as exc:finish('failed:'+repr(exc))
S['h']=unreal.register_slate_post_tick_callback(tick)
