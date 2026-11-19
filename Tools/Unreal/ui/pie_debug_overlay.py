"""Actual F9 input proof; no diagnostic function calls or input-mode overrides."""
import unreal,json,time
from pathlib import Path
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path+'.'+path.rsplit('/',1)[1]+'_C'))
fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd');d=find('/Game/FoA/Gameplay/BP_BeatDirector');door=find('/Game/FoA/Gameplay/BP_Door');phone=find('/Game/FoA/UI/Game/BP_Phone')
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0);gi=unreal.GameplayStatics.get_game_instance(w)
bag=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_Debug',set(),[]))
root=Path('P:/FoA/Saved/PresentationReview');out=root/'debug_runtime.json';request=root/'debug_input.json'
S=dict(start=time.time(),phase=0,after=0,h=None,rows=[],id=0,done=False)

def child(widget,name):
    trees=[t for t in unreal.ObjectIterator(unreal.load_class(None,'/Script/UMG.WidgetTree')) if t.get_outer()==widget]
    found=[o for t in trees for o in [unreal.find_object(t,name)] if o];assert len(found)==1,name
    return found[0]
def key(name):
    S['id']+=1;request.write_text(json.dumps(dict(id=S['id'],events=[dict(key=name,event='pressed_and_released',held_ms=120)])))
def snapshot():
    return dict(beat=d.get_editor_property('BeatIndex'),day=gi.get_editor_property('DayCount'),knowledge=sorted(map(str,gi.get_editor_property('Knowledge'))),inventory=list(map(str,bag.get_editor_property('Items'))),selected=bag.get_editor_property('Selected'),cinematic=p.get_editor_property('bCinematic'),locked=p.get_editor_property('bInteractionLocked'),move_ignored=pc.is_move_input_ignored(),look_ignored=pc.is_look_input_ignored(),cursor=pc.get_editor_property('bShowMouseCursor'),view=pc.get_view_target().get_path_name(),paused=unreal.GameplayStatics.is_game_paused(w),phone=phone.get_editor_property('bOpen'),tool_active=door.get_editor_property('bToolActive'),tool_step=door.get_editor_property('ToolStepIndex'))
def opened(label):
    assert snapshot()==S['baseline'],(label,S['baseline'],snapshot())
    widget=fe.get_editor_property('DebugPanel');assert widget and widget.is_in_viewport(),label
    texts={n:str(child(widget,n).get_text()) for n in ('Txt_Story','Txt_Interaction','Txt_Camera','Txt_Locks','Txt_Inventory','Txt_Battle','Txt_Controls')}
    assert str(S['baseline']['beat']) in texts['Txt_Story'] and 'View' in texts['Txt_Camera'],texts
    assert 'Hold Ctrl' in texts['Txt_Controls'] and 'F9' in str(child(widget,'Txt_Title').get_text())
    assert unreal.SystemLibrary.is_timer_active(widget,'RefreshDebug')
    S['last_widget']=widget;S['rows'].append(dict(label=label,state=snapshot(),texts=texts))
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(root/('debug_'+label+'.png'))+' -nosuffix',pc)
def closed(label):
    assert snapshot()==S['baseline'],(label,S['baseline'],snapshot())
    assert not fe.get_editor_property('DebugPanel')
    assert not S['last_widget'].is_in_viewport()
    assert not unreal.SystemLibrary.is_timer_active(S['last_widget'],'RefreshDebug')
    S['rows'].append(dict(label=label,state=snapshot(),timer_cleared=True))
def advance(delay=.45):S['phase']+=1;S['after']=time.time()+delay
def finish(reason,error=None):
    if S['done']:return
    S['done']=True;unreal.unregister_slate_post_tick_callback(S['h']);gi.call_method('SetProofProgressContext',original);unreal.GameplayStatics.delete_game_in_slot('FoA_QA_Debug',0)
    out.write_text(json.dumps(dict(reason=reason,error=error,phase=S['phase'],rows=S['rows'],qa_preconditions='Actual FE boot, explicit intro finish and wake skip after sequence start. Native F9/P/Q keys. QA pauses ambient story timer and enters key beat4 with AddKey+BootsWorn+Door.Interact only for locked-interaction coverage. No diagnostic method calls or input mode overrides.'),indent=1))
def tick(dt):
    try:
        if time.time()-S['start']>36:return finish('timeout')
        if time.time()<S['after']:return
        phase=S['phase']
        if phase==0:fe.call_method('OnSplashFinished',());advance()
        elif phase==1:fe.call_method('OnTitleConfirmed',());advance()
        elif phase==2:fe.call_method('WakeUp',());advance()
        elif phase==3:
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S.get('story'):story.call_method('Finish',());S['story']=True;return
            if not fe.get_editor_property('bInGameplay') or not d.get_editor_property('SeqPlayer'):return
            if not d.get_editor_property('bWakeDone'):d.call_method('SkipWakeUp',())
            advance(1)
        elif phase==4:
            if p.get_editor_property('bCinematic') or d.get_editor_property('BeatIndex')<0:return
            if phone.get_editor_property('bOpen'):
                if not S.get('boot_phone_closed'):
                    key('P');S['boot_phone_closed']=True;S['after']=time.time()+.6
                return
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            S['baseline']=snapshot();key('F9');advance()
        elif phase==5:opened('gameplay');key('F9');advance()
        elif phase==6:closed('gameplay_closed');key('F9');advance()
        elif phase==7:opened('reopened');key('F9');advance()
        elif phase==8:closed('reclosed');key('P');advance(1.2)
        elif phase==9:
            assert phone.get_editor_property('bOpen'),'P did not open phone'
            S['baseline']=snapshot();key('F9');advance()
        elif phase==10:opened('phone');key('F9');advance()
        elif phase==11:closed('phone_closed');key('P');advance(1)
        elif phase==12:
            assert not phone.get_editor_property('bOpen')
            d.call_method('EnterBeat',(4,));bag.call_method('Add',('Key',))
            boot=door.get_editor_property('BootProgressionSource')
            if boot:boot.call_method('SetState',('Worn',True));d.call_method('ReportEvent',('BootsWorn',))
            door.call_method('Interact',('Use','Key'));assert door.get_editor_property('bToolActive'),'QA key precondition rejected';advance(.2)
        elif phase==13:
            if not door.get_editor_property('bToolReady'):return
            S['baseline']=snapshot();key('F9');advance()
        elif phase==14:opened('interaction');assert 'Key' in S['rows'][-1]['texts']['Txt_Inventory'];key('F9');advance()
        elif phase==15:closed('interaction_closed');key('Q');advance(.7)
        elif phase==16:
            assert not door.get_editor_property('bToolActive')
            bag.call_method('Remove',('Key',))
            d.call_method('EnterBeat',(2,))
            S['baseline']=snapshot();key('F6');advance()
        elif phase==17:
            assert snapshot()==S['baseline'],'F6 changed gameplay while diagnostics were closed'
            key('F9');advance()
        elif phase==18:
            opened('before_skip')
            d.call_method('DebugNextStep',())
            S['rows'].append(dict(label='direct_skip',state=snapshot()))
            assert d.get_editor_property('BeatIndex')==3,('director advanced multiple steps',S['rows'][-1])
            d.call_method('EnterBeat',(2,))
            key('F6');advance()
        elif phase==19:
            S['rows'].append(dict(label='after_f6',state=snapshot(),slot=str(gi.get_editor_property('SaveSlot'))))
            assert d.get_editor_property('BeatIndex')==3,('F6 did not advance one objective',S['rows'][-1])
            assert str(gi.get_editor_property('SaveSlot'))=='FoA_QA_DebugSkip','skip wrote into player progress'
            key('F6');advance()
        elif phase==20:
            assert d.get_editor_property('BeatIndex')==4 and 'Key' in map(str,bag.get_editor_property('Items')),'skip omitted the key prerequisite'
            S['rows'].append(dict(label='debug_skip_two_steps',state=snapshot()))
            fe.call_method('ReturnToTitle',());advance(.5)
        elif phase==21:
            assert not fe.get_editor_property('DebugPanel');assert not unreal.SystemLibrary.is_timer_active(S['last_widget'],'RefreshDebug')
            S['rows'].append(dict(label='title_transition_cleanup',timer_cleared=True));finish('debug_real_f9_preservation_passed')
    except Exception as e:finish('failed',repr(e))
S['h']=unreal.register_slate_post_tick_callback(tick)
