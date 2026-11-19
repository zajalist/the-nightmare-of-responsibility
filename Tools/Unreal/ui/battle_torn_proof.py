"""Bounded real-fight proof, installed only inside battle-ui's own guarded PIE.

Uses story's defeat_respace boot fixture and real keyboard/pad inputs relayed by the runner.
Never reads/broadcasts delegates. A callback is bound to this PIE session and unregisters on every exit.
"""
import json
import os
from pathlib import Path
import sys
import time
import unreal

sys.path[:0]=['P:/FoA/Tools/Unreal/flow','P:/FoA/Tools/Unreal/player']
import proof_guard
import proof_save

OUT=Path(os.environ['FOA_TORN_OUT']);OUT.mkdir(parents=True,exist_ok=True)
(OUT/'raw').mkdir(exist_ok=True)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world
CONTEXT=proof_save.isolate(world)
S=dict(t0=time.monotonic(),phase=0,rows=[],frames=[],shot=0.,done=False,request=0,waiting=0,
       turn=0,action=0,turn_started=0.,keyidx=-1,laststate='',inputs=[],completed=[],targeted=False)
PLAN=tuple(os.environ.get('FOA_TORN_PLAN','Act0,Act1').split(','))
ROOT='/Game/FoA/'


def actor(w,path):
    return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,ROOT+path))


def prop(o,n,default=None):
    try:return o.get_editor_property(n)
    except Exception:return default


def widget(w):
    cls=unreal.load_class(None,ROOT+'Gameplay/Encounter/WBP_Encounter.WBP_Encounter_C')
    widgets=unreal.ObjectIterator(cls)
    return next((x for x in widgets if x.is_in_viewport()),None)


def snapshot(enc,ui):
    pc=unreal.GameplayStatics.get_player_controller(world,0)
    cam=prop(enc,'BattleCam')
    buttons={}
    for n in ('Act0','Act1','Act2','Breathe','Mirror','Items','Flee','NextTarget'):
        b=prop(ui,'Btn_'+n)
        if b:buttons[n]=dict(enabled=b.get_is_enabled(),visible=b.is_visible(),focus=bool(prop(b,'bHovered')),
                            label=str(prop(b,'Label')))
        card=prop(ui,'TornCard_'+n)
        if card:
            transform=card.get_editor_property('render_transform')
            buttons[n].update(lift_y=transform.translation.y,angle=transform.angle,
                              scale=transform.scale.x,opacity=card.get_render_opacity())
    intent=prop(ui,'TornIntent');intent_position=None
    if intent:
        p=unreal.WidgetLayoutLibrary.slot_as_canvas_slot(intent).get_position()
        intent_position=[p.x,p.y]
    pending=prop(enc,'PendingMove')
    return dict(t=round(time.monotonic()-S['t0'],3),state=str(prop(enc,'BattleState')),
                pending_move=pending.get_name() if pending else None,
                composure=prop(enc,'Composure'),resolve=prop(enc,'Resolve'),target=prop(enc,'Target'),
                view_target=pc.get_view_target().get_name(),battle_camera_active=bool(cam and cam.is_active()),
                buttons=buttons,intent_position=intent_position,
                target_projection=[prop(ui,'TornTargetX'),prop(ui,'TornTargetY')],
                viewport_units=[prop(ui,'TornViewX'),prop(ui,'TornViewY')],
                description=str(prop(ui,'Txt_TornDetail').get_text()) if prop(ui,'Txt_TornDetail') else None)


def request(key,kind='key',**extra):
    assert not S['waiting']
    S['request']+=1;S['waiting']=S['request']
    (OUT/'input.json').write_text(json.dumps(dict(id=S['request'],key=key,kind=kind,**extra)))


def finish(reason,w=None):
    if S['done']:return
    S['done']=True;proof_guard.done(S)
    if w:
        unreal.GameplayStatics.set_global_time_dilation(w,1.)
        proof_save.restore(w,CONTEXT)
    (OUT/'result.json').write_text(json.dumps(dict(reason=reason,completed=S['completed'],rows=S['rows'],
         frames=S['frames'],inputs=S['inputs']),indent=2,default=str))
    print('battle-ui proof',reason,len(S['completed']))


def tick(dt):
    w=proof_guard.live(S)
    if not w:return finish('pie_ended')
    try:
        t=time.monotonic()-S['t0']
        if t>43:return finish('cap',w)
        d=actor(w,'Gameplay/BP_BeatDirector.BP_BeatDirector_C')
        fe=actor(w,'UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
        enc=actor(w,'Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
        pc=unreal.GameplayStatics.get_player_controller(w,0)
        pawn=unreal.GameplayStatics.get_player_character(w,0)
        phase=S['phase']
        if phase==0 and t>.1:fe.call_method('OnSplashFinished');S['phase']=1
        elif phase==1 and t>.4:fe.call_method('OnTitleConfirmed');S['phase']=2
        elif phase==2 and t>.7:fe.call_method('WakeUp');S['phase']=3
        elif phase==3:
            story=prop(fe,'Story')
            if story and story.is_in_viewport():story.call_method('Finish')
            elif prop(fe,'bInGameplay') and prop(d,'SeqPlayer') and not prop(d,'bWakeDone'):
                d.call_method('SkipWakeUp');S['phase']=4
        elif phase==4 and prop(d,'bWakeDone') and prop(d,'BeatIndex')>=0 and pc.get_view_target()==pawn and not prop(pawn,'bCinematic'):
            unreal.SystemLibrary.execute_console_command(w,'ke * ClosePhone',pc)
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            d.call_method('EnterBeat',(8,));S['intro_at']=t;S['phase']=5
        elif phase==5:
            if prop(enc,'bActive'):S['phase']=6
            elif t>S['intro_at']+1 and not S.get('skipped'):
                d.call_method('BattleIntroDone');S['skipped']=True
        if S['phase']!=6:return
        ui=widget(w)
        if not ui:return
        row=snapshot(enc,ui)
        if t-S['shot']>=.1:
            n=len(S['frames']);S['shot']=t
            unreal.SystemLibrary.execute_console_command(w,f'Shot showui filename="{OUT.as_posix()}/raw/f{n:04d}.png" -nosuffix',pc)
            S['frames'].append(dict(frame=n,**row))
        if row['state']!=S['laststate']:
            S['rows'].append(dict(kind='state',**row));S['laststate']=row['state']
        if S['waiting']:
            ack=OUT/'ack.json'
            if ack.exists():
                data=json.loads(ack.read_text())
                if data['id']==S['waiting']:
                    S['inputs'].append(dict(request=data,observed=row));S['waiting']=0;S['next_at']=t+.4
            return
        if t<S.get('next_at',0):return
        if prop(enc,'bAwaitingKey'):
            idx=prop(enc,'InputIndex')
            if idx!=S['keyidx']:
                S['keyidx']=idx;enc.call_method('SubmitKey',(prop(enc,'InputKeys')[idx],))
            return
        if not prop(enc,'bPlayerTurn'):
            if S.get('confirmed'):
                assert row['pending_move']==S['expected'],('Wrong command resolved',S['expected'],row)
                S['completed'].append(dict(command=S['confirmed'],expected_move=S['expected'],**row))
                S['confirmed']=None;S['turn']+=1;S['action']=0
                if S['turn']>=len(PLAN):return finish('done',w)
            return
        if not S['targeted']:
            if not S.get('target_step'):
                S['target_before']=row['target'];prop(ui,'Btn_NextTarget').call_method('FocusButton')
                request('Enter');S['target_step']=1;return
            S['rows'].append(dict(kind='target_change',before=S['target_before'],**row))
            assert row['target']!=S['target_before'],'Change target did not act'
            S['targeted']=True
        if S['turn']>=len(PLAN):return finish('done',w)
        if S['action']==0:
            name=PLAN[S['turn']];button=prop(ui,'Btn_'+name)
            if not button.get_is_enabled():
                S['rows'].append(dict(kind='unavailable',command=name,**row))
                # Retain the real rules: record unavailable commands rather than force-enabling them.
                name=next((n for n in ('Act0','Act1','Mirror','Breathe') if row['buttons'][n]['enabled']),None)
                assert name,'No available command'
                button=prop(ui,'Btn_'+name)
            S['command']=name;button.call_method('FocusButton');S['action']=1;S['next_at']=t+.35;return
        if S['action']==1:
            request('Right' if S['turn']%2==0 else 'Gamepad_DPad_Right');S['action']=2;return
        if S['action']==2:
            request('Left' if S['turn']%2==0 else 'Gamepad_DPad_Left');S['action']=3;return
        if S['action']==3:
            # Re-establish the intended command after logging actual navigation outcomes.
            button=prop(ui,'Btn_'+S['command']);button.call_method('FocusButton')
            if S['turn']==2:
                geo=button.get_cached_geometry();size=unreal.SlateBlueprintLibrary.get_local_size(geo)
                pixel,_=unreal.SlateBlueprintLibrary.local_to_viewport(w,geo,unreal.Vector2D(size.x*.5,size.y*.5))
                S['mouse']=dict(x=pixel.x,y=pixel.y)
                request('',kind='mouse',action='move',**S['mouse'])
            S['action']=4;S['next_at']=t+.45;return
        if S['action']==4:
            if S['command'].startswith('Act'):
                target=enc.call_method('TargetGarment')
                if isinstance(target,tuple):target=target[0]
                move=prop(prop(target,'Data'),'ActMoves')[int(S['command'][-1])]
            else:move=prop(enc,S['command']+'Move')
            S['expected']=move.get_name()
            S['rows'].append(dict(kind='confirm_before',command=S['command'],**row))
            if S['turn']==2:request('',kind='mouse',action='click',**S['mouse'])
            else:request('Enter' if S['turn']%2==0 else 'Gamepad_FaceButton_Bottom')
            S['confirmed']=S['command'];S['action']=5;S['keyidx']=-1
    except Exception as exc:
        S['rows'].append(dict(kind='error',error=repr(exc)));finish('error',w)


assert proof_guard.arm(S,tick,'battle-ui'), 'No own PIE session'
