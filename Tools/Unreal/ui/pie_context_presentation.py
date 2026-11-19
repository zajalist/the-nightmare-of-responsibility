"""Bounded actual-FE HUD proof. QA enters key beat; native inputs drive turn/ease/cancel."""
import json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
door=find('/Game/FoA/Gameplay/BP_Door.BP_Door_C')
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
bag=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
root=Path('P:/FoA/Saved/PresentationReview');out=root/'context_runtime.json';request=root/'context_input.json'
S=dict(start=time.time(),phase=0,after=0,h=None,rows=[],id=0,done=False,inputs=[])
def key(name):
    value=unreal.Key();value.import_text(name);return value

def child(hud,name):
    trees=[t for t in unreal.ObjectIterator(unreal.load_class(None,'/Script/UMG.WidgetTree')) if t.get_outer()==hud]
    found=[o for t in trees for o in [unreal.find_object(t,name)] if o];assert len(found)==1,name
    return found[0]

def commands(*events):
    S['id']+=1;request.write_text(json.dumps(dict(id=S['id'],events=list(events))))

def sample(label,shot=False):
    hud=fe.get_editor_property('HUD');names=('Txt_Prompt','Txt_ContextSecondary','Txt_ToolControls','Progress_Tool','Size_ToolProgress','Size_ContextPrompt','Txt_Narration')
    widgets={n:child(hud,n) for n in names};row=dict(label=label,t=time.time()-S['start'],step=door.get_editor_property('ToolStepIndex'),
        angle=door.get_editor_property('ToolAngle'),active=door.get_editor_property('bToolActive'),
        pad=hud.get_editor_property('bToolPadInput'),tool_status=hud.get_editor_property('bToolStatus'),
        hud_visible=hud.is_visible(),hud_in_viewport=hud.is_in_viewport(),
        controls_visible=widgets['Txt_ToolControls'].is_visible(),
        prompt=str(widgets['Txt_Prompt'].get_text()),controls=str(widgets['Txt_ToolControls'].get_text()),
        subtitle=str(widgets['Txt_Narration'].get_text()),percent=widgets['Progress_Tool'].get_editor_property('percent'),
        tint=[getattr(widgets['Progress_Tool'].get_editor_property('fill_color_and_opacity'),c) for c in ('r','g','b','a')],
        width_override=widgets['Size_ContextPrompt'].get_editor_property('override_width_override'),
        cluster_width=widgets['Size_ContextPrompt'].get_editor_property('width_override'),
        bar_height=widgets['Size_ToolProgress'].get_editor_property('height_override'),
        bar_height_override=widgets['Size_ToolProgress'].get_editor_property('override_height_override'),
        bar_visible=str(widgets['Size_ToolProgress'].get_visibility()),rects={})
    for n,obj in widgets.items():
        size=unreal.SlateLibrary.get_local_size(obj.get_cached_geometry())
        row['rects'][n]=[size.x,size.y]
    S['rows'].append(row)
    if shot:unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(root/('context_'+label+'.png'))+' -nosuffix',pc)
    return row

def finish(reason,error=None):
    if S['done']:return
    S['done']=True;unreal.unregister_slate_post_tick_callback(S['h'])
    out.write_text(json.dumps(dict(reason=reason,error=error,rows=S['rows'],inputs=S['inputs'],qa_preconditions='Actual FE/intro/wake route; QA EnterBeat4 + AddKey + Door.Interact. Real native right-stick/D/A/Q drives all turning and cancellation. No inputmode override.'),indent=1))

def advance(delay=.2):S['phase']+=1;S['after']=time.time()+delay

def tick(dt):
    try:
        now=time.time()
        if now-S.get('last_input',0)>.1 and S['phase']>=5:
            hud=fe.get_editor_property('HUD')
            S['inputs'].append(dict(t=now-S['start'],D=pc.is_input_key_down(key('D')),A=pc.is_input_key_down(key('A')),axis=pc.get_input_analog_key_state(key('Gamepad_RightX')),pad=hud.get_editor_property('bToolPadInput')))
            S['last_input']=now
        if now-S['start']>38:return finish('timeout')
        if now<S['after']:return
        phase=S['phase']
        if phase==0:fe.call_method('OnSplashFinished',());advance(.4)
        elif phase==1:fe.call_method('OnTitleConfirmed',());advance(.5)
        elif phase==2:fe.call_method('WakeUp',());advance(.4)
        elif phase==3:
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S.get('story'):
                story.call_method('Finish',());S['story']=True;return
            if not fe.get_editor_property('bInGameplay') or not d.get_editor_property('SeqPlayer'):return
            if not d.get_editor_property('bWakeDone'):d.call_method('SkipWakeUp',())
            advance(.8)
        elif phase==4:
            if p.get_editor_property('bCinematic'):return
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            d.call_method('EnterBeat',(4,));bag.call_method('Add',('Key',));door.call_method('Interact',('Use','Key'));advance(.2)
        elif phase==5:
            if not door.get_editor_property('bToolReady'):return
            sample('seated',True)
            commands(dict(key='Gamepad_RightX',axis=1.,seconds=.45));advance(.7)
        elif phase==6:
            row=sample('gamepad',True);assert row['pad'] and 'Right stick' in row['controls'],row
            commands(dict(key='D',event='pressed'));advance(.2)
        elif phase==7:
            if door.get_editor_property('ToolStepIndex')!=2:return
            commands(dict(key='D',event='released'))
            hud=fe.get_editor_property('HUD');hud.call_method('HandleNarration',('The key catches against the old metal. I can feel it give when I ease the pressure.',))
            advance(.3)
        elif phase==8:
            row=sample('bound_subtitle',True)
            assert row['prompt']=='Ease back' and not row['pad'],row
            assert .74<row['percent']<.79 and row['tint'][0]>row['tint'][1],row
            # Python geometry is zero here even for visibly rendered widgets.
            # Assert live visibility + effective explicit sizing; review the actual shot.
            assert row['subtitle'] and row['bar_height_override'] and row['bar_height']==5,row
            assert row['width_override'] and row['cluster_width']==320,row
            assert row['hud_visible'] and row['hud_in_viewport'] and row['controls_visible'],row
            commands(dict(key='A',event='pressed'));advance(.2)
        elif phase==9:
            if door.get_editor_property('ToolStepIndex')!=3:return
            commands(dict(key='A',event='released'));advance(.2)
        elif phase==10:
            row=sample('ease_retry',True);assert row['prompt']=='Turn again',row
            commands(dict(key='Q',event='pressed_and_released',held_ms=200));advance(.6)
        elif phase==11:
            row=sample('cancel_restored',True)
            assert not row['active'] and not row['tool_status'] and not row['width_override'],row
            assert 'COLLAPSED' in row['bar_visible'].upper(),row
            assert not p.get_editor_property('bCinematic') and not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
            assert unreal.Name('Key') in bag.get_editor_property('Items')
            door.call_method('Interact',('Use','Key'));advance(.2)
        elif phase==12:
            if not door.get_editor_property('bToolReady'):return
            commands(dict(key='Gamepad_FaceButton_Right',event='pressed_and_released',held_ms=200));advance(.5)
        elif phase==13:
            row=sample('gamepad_cancel',True)
            assert not row['active'] and not row['tool_status'] and not row['controls_visible'],row
            assert not p.get_editor_property('bCinematic') and not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
            assert unreal.Name('Key') in bag.get_editor_property('Items')
            finish('context_real_input_passed')
    except Exception as exc:finish('failed',repr(exc))
S['h']=unreal.register_slate_post_tick_callback(tick)
