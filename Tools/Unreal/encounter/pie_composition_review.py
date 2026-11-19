"""Bounded actual-menu battle review in coordinator-owned PIE; isolated save context."""
import json,time,os
from pathlib import Path
import unreal

OUT=Path('P:/FoA/Saved/PresentationReview/battle_runtime.json')
REQ=OUT.with_name('battle_input.json')
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
enc=find('/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_Presentation',set(),[]))
contact_geometry=json.loads(Path('P:/FoA/Saved/Integration/cinematic_audit/shirt_contact_geometry.json').read_text())
S=dict(start=time.time(),h=None,actions=set(),story=False,skip=False,battle=False,rows=[],seen=set(),last=0,
       commands=0,command_at=0,was_command=False,requested=False,id=0,lastkey=None,end_at=0,done=False,audits=set(),acting=set())

def audit(label):
    previous={k:os.environ.get(k) for k in ('FOA_OWNED_PROOF','FOA_AUDIT_LABEL')}
    try:
        os.environ.update(FOA_OWNED_PROOF='1',FOA_AUDIT_LABEL=label)
        exec(Path('P:/FoA/Tools/Unreal/cine/audit_live_camera_pose.py').read_text(),{'__name__':'__audit__'})
        S['audits'].add(label)
    finally:
        for k,v in previous.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def input_(key):
    S['id']+=1;REQ.write_text(json.dumps({'id':S['id'],'key':key.export_text() if hasattr(key,'export_text') else str(key)}))

def snap(tag):
    cam=pc.player_camera_manager;widget=enc.get_editor_property('Widget')
    row=dict(t=round(time.time()-S['start'],3),tag=tag,state=str(enc.get_editor_property('BattleState')),
        active=enc.get_editor_property('bActive'),pawn=p.get_actor_location().to_tuple(),
        camera=cam.get_camera_location().to_tuple(),rotation=enc.get_actor_rotation().to_tuple(),
        falling=p.character_movement.is_falling(),view=pc.get_view_target().get_class().get_name(),
        locked_move=pc.is_move_input_ignored(),locked_look=pc.is_look_input_ignored(),
        composure=enc.get_editor_property('Composure'),resolve=enc.get_editor_property('Resolve'))
    if widget:
        row['focus']=[name for name in ('Btn_Act0','Btn_Act1','Btn_Breathe','Btn_Mirror','Btn_NextTarget')
            if widget.get_editor_property(name).has_user_focused_descendants(pc)]
        row['command_hints_visible']=widget.get_editor_property('Txt_BattleControls').get_visibility()==unreal.SlateVisibility.VISIBLE
        row['heading_opacity']=widget.get_editor_property('Txt_BattleHelp').get_render_opacity()
    montage=p.get_current_montage()
    row['montage']=montage.get_name() if montage else None
    owned=enc.get_editor_property('BattleActingMontage')
    row['owned_montage']=owned.get_name() if owned else None
    garments=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/FoA/Gameplay/Encounter/BP_Garment.BP_Garment_C'))
    row['contact_lights']=[dict(actor=g.get_name(),active=g.get_editor_property('bPlayerContact'),
        intensity=g.get_editor_property('ContactFill').get_editor_property('intensity'),
        channel1=g.get_editor_property('Rig').get_editor_property('lighting_channels').get_editor_property('channel1')) for g in garments]
    if montage and owned==montage:S['acting'].add(montage.get_name())
    S['rows'].append(row)
    return row

def shot(name):
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename=P:/FoA/Saved/PresentationReview/battle_'+name+'.png -nosuffix',pc)

def finish(reason):
    if S['done']:return
    S['done']=True;unreal.unregister_slate_post_tick_callback(S['h'])
    gi.call_method('SetProofProgressContext',original)
    unreal.GameplayStatics.delete_game_in_slot('FoA_QA_Presentation',0)
    OUT.write_text(json.dumps({'reason':reason,'rows':S['rows'],'screens':sorted(S['seen']),'acting':sorted(S['acting']),
        'preconditions':'Actual FE and Story; isolated direct StartEncounter fixture, native Enter and timing keys; no time dilation.'},indent=1))

def tick(dt):
    try:
        t=time.time()-S['start']
        if t>56:return finish('timeout')
        if not S['battle']:
            screen=fe.get_editor_property('Screen')
            if screen and screen.is_in_viewport():
                for prop,action in [('SplashClass','OnSplashFinished'),('TitleClass','OnTitleConfirmed'),('MainMenuClass','WakeUp')]:
                    if screen.get_class()==fe.get_editor_property(prop) and action not in S['actions']:
                        S['actions'].add(action);fe.call_method(action,());return
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S['story']:
                story.call_method('Finish',());S['story']=True;return
            if fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone') and not S['skip']:
                d.call_method('SkipWakeUp',());S['skip']=True;return
            if d.get_editor_property('bWakeDone') and pc.get_view_target()==p and not p.get_editor_property('bCinematic'):
                assert 'WakeUp' in S['actions'] and S['story']
                r=enc.get_actor_rotation();assert abs(r.roll)<.01 and abs(abs(r.yaw)-180)<.01,r
                unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
                enc.call_method('StartEncounter',('Shirt',));S['battle']=True
            return
        if S['end_at']:
            if t-S['end_at']>.8:
                r=snap('released')
                assert not r['locked_move'] and not r['locked_look'] and r['view']=='BP_FoAPlayer_C',r
                assert r['pawn'][2]>25 and not r['falling'],r
                assert 'PlayerCommand' in S['seen'] and 'EnemyPhase' in S['seen'],S['seen']
                assert S['acting'],'Battle gestures never played on the source mesh'
                assert enc.get_editor_property('BattleActingMontage') is None,'Owned montage not cleared'
                assert all(x['intensity']==0 and not x['channel1'] and not x['active'] for x in r['contact_lights']), 'Contact lighting survived encounter cleanup'
                return finish('battle_presentation_and_native_input_passed')
            return
        state=str(enc.get_editor_property('BattleState'))
        if state!=S.get('observed_state'):
            S['observed_state']=state;S['state_at']=t
        S['seen'].add(state)
        if t-S['last']>.15:
            S['last']=t;r=snap('state')
            if enc.get_editor_property('bActive'):
                assert 25<r['pawn'][2]<300 and 20<r['camera'][2]<295,r
                assert -375<r['camera'][0]<375 and -390<r['camera'][1]<300,r
                if t-S['state_at']>.25 and state in ('PlayerCommand','EnemyPhase'):
                    assert r['command_hints_visible']==(state=='PlayerCommand'),r
                if t-S['state_at']>.25 and state=='ResolvePlayerAction':assert r['heading_opacity']==0,r
        if t-S.get('state_at',t)>.55 and S.get('last_shot')!=state:
            S['last_shot']=state;shot(state)
        if state=='PlayerCommand':
            if not S['was_command']:
                S['commands']+=1;S['command_at']=t;S['requested']=False
            S['was_command']=True
            if 'battle_command' not in S['audits'] and t-S['command_at']>.7:audit('battle_command')
            if S['commands']>=3 and t-S['command_at']>1.5:
                enc.call_method('EndEncounter',());S['end_at']=t;return
            if t-S['command_at']>2 and not S['requested']:
                # First focused action is the real initial command, then use the production ButtonUp action.
                if S['commands']==1:input_('Enter')
                else:enc.call_method('ChooseMove',(unreal.load_asset('/Game/FoA/Gameplay/Encounter/Data/DA_Move_ButtonUp'),))
                S['requested']=True
        else:S['was_command']=False
        montage=p.get_current_montage()
        if montage and montage==enc.get_editor_property('BattleActingMontage') and 'battle_reach' not in S['audits']:
            if S.get('acting_at') is None:S['acting_at']=t
            if t-S['acting_at']>.55:
                r=snap('contact_hold')
                assert any(x['active'] and x['channel1'] and 10<x['intensity']<=15 for x in r['contact_lights']), 'Shirt contact fill did not follow the reach'
                garment=enc.get_editor_property('ContactGarment');assert garment
                rig=garment.get_editor_property('Rig');surface=unreal.Vector()
                for anchor in contact_geometry['skin_anchor']:
                    transform=rig.get_socket_transform(anchor['bone'],unreal.RelativeTransformSpace.RTS_WORLD)
                    surface+=unreal.MathLibrary.transform_location(transform,unreal.Vector(*anchor['local']))*anchor['weight']
                transform=p.get_editor_property('Body').get_socket_transform('index_03_l',unreal.RelativeTransformSpace.RTS_WORLD)
                tip=unreal.MathLibrary.transform_location(transform,unreal.Vector(*contact_geometry['fingertip']['local']))
                r['contact_error_cm']=(surface-tip).length()
                assert r['contact_error_cm']<3, 'Shirt seam lost fingertip contact: '+str(r['contact_error_cm'])
                audit('battle_reach');shot('Acting')
        if enc.get_editor_property('bAwaitingKey'):
            index=enc.get_editor_property('InputIndex')
            key=(S['commands'],index)
            if key!=S['lastkey']:
                S['lastkey']=key;input_(enc.get_editor_property('InputKeys')[index])
    except Exception as exc:
        S['rows'].append({'error':repr(exc)});finish('failed')

S['h']=unreal.register_slate_post_tick_callback(tick)
