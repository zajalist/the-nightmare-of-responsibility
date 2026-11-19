"""Actual menu/intro route to a held battle command for the bounded surface probe."""
import unreal,json,time,os,traceback
from pathlib import Path
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C');d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
enc=find('/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C');p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
gi=unreal.GameplayStatics.get_game_instance(w);old=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_ContactFill',set(),[]))
folder=Path('P:/FoA/Saved/Integration/cinematic_audit/contact_fill');folder.mkdir(exist_ok=True)
S={'start':time.monotonic(),'h':None,'actions':set(),'story':False,'skip':False,'battle':False,'launched':False,'finished':False}
def finish(error=None):
    if S['finished']:return
    S['finished']=True;unreal.unregister_slate_post_tick_callback(S['h'])
    if enc.get_editor_property('bActive'):enc.call_method('EndEncounter',())
    gi.call_method('SetProofProgressContext',old);unreal.GameplayStatics.delete_game_in_slot('FoA_QA_ContactFill',0)
    (folder/'boot.json').write_text(json.dumps({'error':error,'story_finished':S['story'],'battle':S['battle'],'probe':S['launched']}))
def tick(dt):
    try:
        if time.monotonic()-S['start']>20:return finish('timeout')
        if S['launched']:
            if (folder/'report.json').exists():
                error=json.loads((folder/'report.json').read_text())['error']
                if error:return finish(error)
                return finish()
            return
        if not S['battle']:
            screen=fe.get_editor_property('Screen')
            if screen and screen.is_in_viewport():
                for prop,action in [('SplashClass','OnSplashFinished'),('TitleClass','OnTitleConfirmed'),('MainMenuClass','WakeUp')]:
                    if screen.get_class()==fe.get_editor_property(prop) and action not in S['actions']:
                        S['actions'].add(action);fe.call_method(action,());return
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S['story']:story.call_method('Finish',());S['story']=True;return
            if fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone') and not S['skip']:
                d.call_method('SkipWakeUp',());S['skip']=True;return
            if d.get_editor_property('bWakeDone') and pc.get_view_target()==p and not p.get_editor_property('bCinematic'):
                unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
                enc.call_method('StartEncounter',('Shirt',));S['battle']=True
            return
        if str(enc.get_editor_property('BattleState'))=='PlayerCommand':
            S['launched']=True;os.environ['FOA_OWNED_PROOF']='1'
            exec(Path('P:/FoA/Tools/Unreal/encounter/pie_contact_fill_probe.py').read_text(),{'__name__':'__hair_probe__'})
    except Exception:finish(traceback.format_exc())
S['h']=unreal.register_slate_post_tick_callback(tick)
