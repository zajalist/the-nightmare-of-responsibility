"""Owned-PIE search regression: real scanner/actions, explicit T6 fixture, no forced focus."""
import json,time,os
from pathlib import Path
import unreal
input_diagnostic=os.environ.get('FOA_INPUT_DIAG')=='1'
extract_diagnostic=os.environ.get('FOA_EXTRACT_DIAG')=='1'
camera_only=os.environ.get('FOA_CAMERA_ONLY')=='1'
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
actors={a.get_actor_label():a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)}
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
d=actors['BeatDirector'];fe=next(a for a in actors.values() if a.get_class().get_name()=='BP_FoAFrontEnd_C')
ia=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
bag=ia.get_editor_property('Inventory');gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_Clothing',set(),[]))
S=dict(start=time.time(),phase=0,after=0,rows=[],h=None,done=False,shots={},seen=set(),
       input_id=0,trace=[],last_trace=0,flight_shots=set(),input_trace=[])
key_e=unreal.Key();key_e.import_text('E')
action_e=unreal.load_asset('/Game/Input/Actions/IA_Interact')
input_component=p.get_component_by_class(unreal.EnhancedInputComponent)
sky_first=os.environ.get('FOA_SKY_FIRST')=='1'
out=Path('P:/FoA/Saved/Integration/'+('clothing_camera_final_proof.json' if camera_only else 'clothing_scanner_proof.json'))
inputs=out.with_name('clothing_input_request.json')
class AwaitNaturalScan(Exception):pass
def prop(obj,name,default=None):
    try:return obj.get_editor_property(name)
    except Exception:return default
def shot(name):
    # Multiple Shot commands in one engine frame overwrite one another.
    if time.time()-S.get('last_shot',0)<.22:return False
    if camera_only:name='camera_final_'+name.removeprefix('clothing_')
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename=P:/FoA/Saved/Integration/'+name+'.png -nosuffix',pc)
    S['last_shot']=time.time();return True
def snap(label):
    target=ia.get_editor_property('Target');items=list(bag.get_editor_property('Items'));selected=bag.get_editor_property('Selected')
    row=dict(label=label,seconds=time.time()-S['start'],stage=d.get_editor_property('ClothingSearchStage'),
        beat=d.get_editor_property('BeatIndex'),target=target.get_actor_label() if target else None,
        verb=str(ia.get_editor_property('Verb')),prompt=str(ia.get_editor_property('Prompt')),
        held=str(items[selected]) if 0<=selected<len(items) else 'None',inventory=[str(i) for i in items],
        cinematic=p.get_editor_property('bCinematic'),locked=p.get_editor_property('bInteractionLocked'),
        view=pc.get_view_target().get_class().get_name(),ignored_move=pc.is_move_input_ignored(),ignored_look=pc.is_look_input_ignored(),
        scan_paused=unreal.SystemLibrary.is_timer_paused(ia,'Scan'),
        flight=d.get_editor_property('bClothingFlight'),
        capsule_radius=p.capsule_component.get_unscaled_capsule_radius(),
        pawn=p.get_actor_location().to_tuple(),
        body=p.get_editor_property('Body').get_world_transform().export_text(),
        head=p.get_editor_property('Face').get_socket_location('head').to_tuple(),
        follow_camera=p.get_editor_property('FollowCamera').get_world_location().to_tuple(),
        topdown_return_pending=unreal.SystemLibrary.is_timer_active(d,'ShowCeiling'),
        camera=pc.player_camera_manager.get_camera_location().to_tuple(),
        states={name:str(actors[name].get_editor_property('State')) for name in ('Wardrobe','Desk','Bed','Shirt_T7')})
    S['rows'].append(row);return row
def finish(reason):
    if S['done']:return
    S['done']=True;unreal.unregister_slate_post_tick_callback(S['h'])
    gi.call_method('SetProofProgressContext',original);unreal.GameplayStatics.delete_game_in_slot('FoA_QA_Clothing',0)
    preconditions='Real FE and native E key input; wake skipped only after sequence starts; fixture enters T6 and sends wardrobe Notify HandleOff; navigation teleports only, target focus never forced.'
    if camera_only:preconditions+=' Camera-only fixture prepares the already-verified three clue states directly; extraction and both catches still use real scanner/E. No battle or reset regression claimed here.'
    out.write_text(json.dumps(dict(reason=reason,qa_preconditions=preconditions,rows=S['rows'],trace=S['trace'],input_trace=S['input_trace']),indent=1))
def next_(delay=.2):S['phase']+=1;S['after']=time.time()+delay
def garment_roster():
    rows=[]
    for actor in actors['Encounter_T8'].get_editor_property('Garments'):
        root=actor.root_component
        assert root and root.get_name()=='Root',('Unstable garment root',actor.get_name(),root)
        components={}
        for component in actor.get_components_by_class(unreal.SceneComponent):
            if component.get_name() not in ('Mesh','Rig','ContactFill'):continue
            parent=component.get_attach_parent()
            assert parent==root,('Garment sibling detached',actor.get_name(),component.get_name(),parent)
            components[component.get_name()]=dict(parent=parent.get_name(),relative=component.get_relative_transform().export_text(),world=component.get_world_transform().export_text())
        assert set(components)=={'Mesh','Rig','ContactFill'},('Missing garment components',actor.get_name(),components)
        rows.append(dict(name=actor.get_name(),hidden=prop(actor,'bHidden'),location=actor.get_actor_location().to_tuple(),data=prop(actor,'Data').get_name(),root=root.get_name(),components=components))
    return rows

def aim(label):
    actor=actors[label]
    boxes=[unreal.SystemLibrary.get_component_bounds(c) for c in actor.get_components_by_class(unreal.StaticMeshComponent) if c.get_editor_property('static_mesh')]
    o,e,_=max(boxes,key=lambda b:b[2]);v=unreal.Vector(-o.x,-o.y,0);v.normalize()
    stand=o+v*(max(e.x,e.y)+85);stand.z=85
    if label=='Bed':
        # Aim at the exposed footboard, not the separate opaque bedding actor.
        # The generic diagonal-to-centre ray enters the mattress before the frame.
        # Keep the already verified open-floor approach; the centre footboard
        # approach itself is occupied by another room prop.
        S['bed_aim_candidates']=[unreal.Vector(o.x-e.x+3,y,z) for y in (o.y+e.y-16,o.y,o.y-e.y+16) for z in (55,25,75)]
        S['bed_aim_index']=0;o=S['bed_aim_candidates'][0]
    if label=='Shirt_T7':
        # Search visible points on the actual garment bounds using normal Scan;
        # nearby boots can intercept the single centre ray from this approach.
        S['shirt_aim_candidates']=[o+unreal.Vector(e.x*x,e.y*y,e.z*z) for z in (.7,.35,0,-.35) for x,y in ((0,0),(-.5,0),(.5,0),(0,-.5),(0,.5))]
        S['shirt_aim_index']=0;o=S['shirt_aim_candidates'][0]
    assert p.teleport(stand,p.get_actor_rotation()),('navigation fixture blocked',label,list(stand.to_tuple()))
    S['aim']=o;S['expected']=label;S['aim_after']=time.time()+.18
    S['rows'].append(dict(label='navigation_'+label,stand=stand.to_tuple(),aim=o.to_tuple()))
def use():
    r=snap('focus_'+S['expected'])
    if r['target']!=S['expected'] and S['expected']=='Shirt_T7' and S['shirt_aim_index']+1<len(S['shirt_aim_candidates']):
        S['shirt_aim_index']+=1;S['aim']=S['shirt_aim_candidates'][S['shirt_aim_index']]
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(),S['aim']))
        S['after']=time.time()+.2
        raise AwaitNaturalScan()
    if r['target']!=S['expected'] and S['expected']=='Bed' and S['bed_aim_index']+1<len(S['bed_aim_candidates']):
        # Bounded QA navigation: sweep real exposed frame points from the same
        # collision-verified floor stand, allowing the shipped Scan to choose.
        S['bed_aim_index']+=1;S['aim']=S['bed_aim_candidates'][S['bed_aim_index']]
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(),S['aim']))
        S['after']=time.time()+.25
        S['rows'].append(dict(label='bed_natural_scan_candidate',point=S['aim'].to_tuple(),index=S['bed_aim_index']))
        raise AwaitNaturalScan()
    assert r['target']==S['expected'],r
    assert not r['cinematic'] and not r['locked'],r
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename=P:/FoA/Saved/Integration/clothing_focus_'+S['expected']+'_'+str(r['stage'])+'.png -nosuffix',pc)
    S['input_id']+=1
    inputs.write_text(json.dumps(dict(id=S['input_id'],key='E')))

def released(label):
    row=snap(label)
    assert not row['cinematic'] and not row['ignored_move'] and not row['ignored_look'],row
    assert row['view']=='BP_FoAPlayer_C' and not row['scan_paused'],row
    assert not d.get_editor_property('bClothingInspection'),row
    assert not unreal.SystemLibrary.is_timer_active(d,'TryClothingInspection')
    assert not unreal.SystemLibrary.is_timer_active(d,'FinishClothingInspection')
    mh=p.get_editor_property('Body').get_anim_instance();source=p.mesh.get_anim_instance()
    assert prop(mh,'ToolHandWeight')==0 and prop(mh,'HeldToolWeight')==0
    assert prop(source,'GripWeight')==0 and not prop(source,'KeyGrip')
def tick(dt):
    try:
        t=time.time()-S['start'];phase=S['phase']
        if t>(120 if sky_first else 86):return finish('timeout')
        if phase in (5,6):
            hanger=actors['Hanger_CoatRail'];montage=p.get_current_montage()
            input_component=p.get_component_by_class(unreal.EnhancedInputComponent)
            S['input_trace'].append(dict(t=t,down=pc.is_input_key_down(key_e),held=pc.get_input_key_time_down(key_e),
                action=str(input_component.get_bound_action_value(action_e)) if input_component and hasattr(input_component,'get_bound_action_value') else None,
                hanger_state=str(hanger.get_editor_property('State')),pending=hanger.get_editor_property('bPendingRow'),
                montage=montage.get_name() if montage else None))
        stage=d.get_editor_property('ClothingSearchStage')
        if extract_diagnostic and stage==5 and (d.get_editor_property('bClothingFlight') or S.get('camera_diag')):
            age=unreal.SystemLibrary.get_game_time_in_seconds(w)-d.get_editor_property('ClothingFlightStarted')
            if age<1.05 and not S.get('camera_diag'):return
            if not S.get('camera_diag'):
                S['camera_diag']=True;S['candidate']=0;S['camera_after']=0
                unreal.GameplayStatics.set_global_time_dilation(w,.001)
            if time.time()<S['camera_after']:return
            candidates=[(235,-195,14),(300,-195,14),(270,-205,14),(220,-175,12),(200,-120,18)]
            if S['candidate']>=len(candidates):
                if not S.get('diag_cancelled'):
                    unreal.GameplayStatics.set_global_time_dilation(w,1)
                    d.call_method('CancelClothingInspection',())
                    S['diag_cancelled']=True;S['camera_after']=time.time()+.7;return
                released('diagnostic_cancel_released')
                assert p.capsule_component.get_unscaled_capsule_radius()==S['extraction_radius']
                assert sum((a-b)**2 for a,b in zip(p.get_actor_location().to_tuple(),S['extraction_home']))<.1
                return finish('extraction_camera_candidates_captured')
            if not S.get('candidate_placed'):
                cam=d.get_editor_property('TopDownCamera');pos=unreal.Vector(*candidates[S['candidate']]);focus=unreal.Vector(278,-130,20)
                cam.set_world_location_and_rotation(pos,unreal.MathLibrary.find_look_at_rotation(pos,focus),False,True)
                S['candidate_placed']=True;S['camera_after']=time.time()+.4;return
            if shot('extraction_camera_candidate_'+str(S['candidate'])):
                S['rows'].append(dict(label='camera_candidate',index=S['candidate'],position=candidates[S['candidate']],hand=p.get_editor_property('Body').get_socket_location('hand_r').to_tuple()))
                S['candidate']+=1;S['candidate_placed']=False;S['camera_after']=time.time()+.25
            return
        if stage==8:
            S.setdefault('vase_seen',time.time())
            if time.time()-S['vase_seen']>2.8 and not S.get('boss_shot'):
                S['boss_shot']=True
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename=P:/FoA/Saved/Integration/clothing_boss_formed.png -nosuffix',pc)
        if stage>=4 and t-S['last_trace']>.1:
            S['last_trace']=t
            flight=d.get_editor_property('bClothingFlight')
            mode=d.get_editor_property('ClothingChaseMode')
            body=p.get_editor_property('Body')
            anim=body.get_anim_instance();source=p.mesh.get_anim_instance()
            S['trace'].append(dict(t=t,stage=stage,beat=d.get_editor_property('BeatIndex'),
                flight=flight,mode=mode,shirt=actors['Shirt_T7'].get_actor_location().to_tuple(),
                hand=body.get_socket_location('hand_r').to_tuple(),
                shoulder=body.get_socket_location('upperarm_r').to_tuple(),
                elbow=body.get_socket_location('lowerarm_r').to_tuple(),
                hanger_owned=d.get_editor_property('bClothingHangerOwned'),
                capsule_radius=p.capsule_component.get_unscaled_capsule_radius(),
                anim=anim.get_class().get_name(),hand_weight=prop(anim,'ToolHandWeight'),
                hand_target=prop(anim,'ToolHandTarget').to_tuple(),held_weight=prop(anim,'HeldToolWeight'),
                key_grip=prop(source,'KeyGrip'),grip_weight=prop(source,'GripWeight'),
                montage=p.get_current_montage().get_name() if p.get_current_montage() else None,
                hanger=p.get_editor_property('HeldTool').get_world_transform().export_text(),
                camera=pc.player_camera_manager.get_camera_location().to_tuple(),
                pawn=p.get_actor_location().to_tuple(),velocity=p.get_velocity().to_tuple(),
                view=pc.get_view_target().get_class().get_name(),
                items=[str(i) for i in bag.get_editor_property('Items')]))
            age=unreal.SystemLibrary.get_game_time_in_seconds(w)-d.get_editor_property('ClothingFlightStarted')
            for mark in ((.7,1.4,2.15) if mode==1 else (.3,.65)):
                key=(mode,mark)
                if flight and age>mark and key not in S['flight_shots'] and shot('clothing_flight_'+str(mode)+'_'+str(mark).replace('.','_')):
                    S['flight_shots'].add(key)
        if d.get_editor_property('bClothingInspection'):
            stage=d.get_editor_property('ClothingSearchStage')
            S['shots'].setdefault(stage,time.time())
            if stage in (2,3,4) and stage not in S['seen'] and time.time()-S['shots'][stage]>.55 and shot({2:'wardrobe_refined',4:'bed_refined'}.get(stage,'clothing_clue_'+str(stage))):
                S['seen'].add(stage);snap('physical_clue_'+str(stage))
            if S.get('cancel_probe')=='waiting':
                d.call_method('CancelClothingInspection',());released('active_inspection_cancelled');S['cancel_probe']='passed'
        if 'aim_after' in S and time.time()>=S['aim_after']:
            pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(),S['aim']))
            del S['aim_after']
        if time.time()<S['after']:return
        if 8 <= phase <= 20 and (p.get_editor_property('bCinematic') or p.get_editor_property('bInteractionLocked')
            or d.get_editor_property('bClothingFlight')
            or unreal.SystemLibrary.is_timer_active(d,'TryClothingInspection')):return
        if phase==0:fe.call_method('OnSplashFinished',());next_(.4)
        elif phase==1:fe.call_method('OnTitleConfirmed',());next_(.5)
        elif phase==2:fe.call_method('WakeUp',());next_(.4)
        elif phase==3:
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S.get('story_done'):
                story.call_method('Finish',());S['story_done']=True;return
            if not fe.get_editor_property('bInGameplay') or not d.get_editor_property('SeqPlayer'):return
            if not d.get_editor_property('bWakeDone'):d.call_method('SkipWakeUp',())
            next_(1)
        elif phase==4:
            if not d.get_editor_property('bWakeDone') or d.get_editor_property('BeatIndex')!=1:return
            S['shirt_home']=actors['Shirt_T7'].get_actor_transform().export_text()
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            d.call_method('EnterBeat',(2,))  # Pickup interactions unlock after first steps.
            if input_diagnostic:
                import runpy
                runpy.run_path('P:/FoA/Saved/Integration/read_live_input_route.py')
            unreal.WidgetLibrary.set_focus_to_game_viewport()
            aim('Hanger_CoatRail');next_(.6)
        elif phase==5:use();next_(30 if sky_first else (2 if input_diagnostic else .1))
        elif phase==6:
            if input_diagnostic:
                snap('input_diagnostic_result')
                return finish('input_route_passed' if unreal.Name('Hanger') in bag.get_editor_property('Items') else 'input_route_failed')
            if not S.get('contact_cancel'):
                if not actors['Hanger_CoatRail'].get_editor_property('bPendingRow'):return
                actors['Hanger_CoatRail'].call_method('CancelPendingRow',(True,))
                assert not ia.get_editor_property('PendingContactActor')
                S['contact_cancel']='waiting';S['after']=time.time()+1.35;return
            if S['contact_cancel']=='waiting':
                assert unreal.Name('Hanger') not in bag.get_editor_property('Items')
                assert str(actors['Hanger_CoatRail'].get_editor_property('State'))=='Available'
                assert not ia.get_editor_property('PendingContactActor')
                snap('contact_cancel_no_late_grant')
                # Cancel releases a montage-driven body turn; reacquire the
                # actual hanger from the settled camera before the retry key.
                aim('Hanger_CoatRail');S['contact_cancel']='reaim';S['after']=time.time()+.65;return
            if S['contact_cancel']=='reaim':
                use();S['contact_cancel']='passed';S['after']=time.time()+2.;return
            assert unreal.Name('Hanger') in bag.get_editor_property('Items'),snap('hanger_missing')
            assert not ia.get_editor_property('PendingContactActor')
            before=list(bag.get_editor_property('Items'))
            actors['Hanger_CoatRail'].call_method('OnPendingContact',(unreal.load_asset('/Game/FoA/Characters/Player/Montages/AM_FoA_PickUp_Table'),))
            assert before==list(bag.get_editor_property('Items'))
            d.call_method('EnterBeat',(6,));actors['Wardrobe'].call_method('Interact',('Notify','HandleOff'));next_(.3)
        elif phase==7:
            if d.get_editor_property('bWardrobeTransition') or d.get_editor_property('bTopDown'):return
            # bTopDown is cleared at the START of the 1.5s return blend.
            # GetViewTarget already reports Player while its PCM is still overhead.
            # Do not teleport/aim until the authored blend actually reaches its camera.
            camera=pc.player_camera_manager.get_camera_location()
            follow=p.get_editor_property('FollowCamera').get_world_location()
            if unreal.SystemLibrary.is_timer_active(d,'ShowCeiling') or (camera-follow).length()>5:
                if not S.get('return_blend_observed'):
                    snap('return_blend_pending');S['return_blend_observed']=True
                return
            r=snap('search_ready');assert r['stage']==1 and r['states']['Shirt_T7']=='Hidden',r
            assert 20<camera.z<295,('Post-wardrobe FP camera outside room',r)
            if camera_only:
                # Camera-only QA shortcuts the already verified clue interactions;
                # extraction and both catch attempts still use real scanner/E.
                d.call_method('SearchWardrobeClue',());d.call_method('SearchDeskClue',());d.call_method('SearchBedClue',())
                d.call_method('CancelClothingInspection',());bag.call_method('Select',(-1,))
                S['rows'].append(dict(label='QA_camera_only_clues_prepared'))
                aim('Bed');S['phase']=14;S['after']=time.time()+.6;return
            aim('Wardrobe');next_(.6)
        elif phase==8:use();next_(.8)
        elif phase==9:
            assert d.get_editor_property('ClothingSearchStage')==2,snap('wardrobe_failed')
            released('wardrobe_shot_released')
            aim('Desk');next_(.6)
        elif phase==10:use();next_(2)
        elif phase==11:
            assert d.get_editor_property('ClothingSearchStage')==3,snap('desk_failed')
            released('desk_shot_released')
            aim('Bed');next_(.6)
        elif phase==12:use();next_(2)
        elif phase==13:
            assert d.get_editor_property('ClothingSearchStage')==4,snap('bed_failed')
            if not S.get('cancel_probe'):
                released('bed_shot_released')
                d.call_method('QueueClothingBed',())  # Explicit QA-only replay to test active cancellation.
                S['cancel_probe']='waiting';S['after']=time.time()+.3;return
            if S['cancel_probe']!='passed':return
            bag.call_method('Select',(-1,))  # Owned hanger must work without manually selecting its slot.
            aim('Bed');next_(.6)
        elif phase==14:
            S['extraction_home']=p.get_actor_location().to_tuple();S['extraction_radius']=p.capsule_component.get_unscaled_capsule_radius()
            use();next_(2)
        elif phase==15:
            assert d.get_editor_property('ClothingSearchStage')==5,snap('unhook_failed')
            assert unreal.Name('Shirt') not in bag.get_editor_property('Items')
            released('extraction_released')
            assert p.capsule_component.get_unscaled_capsule_radius()==S['extraction_radius']
            assert sum((a-b)**2 for a,b in zip(p.get_actor_location().to_tuple(),S['extraction_home']))<.1
            extraction=[r for r in S['trace'] if r['mode']==1 and r['flight'] and r['hanger_owned']]
            assert extraction and all(r['capsule_radius']==28 and abs(r['pawn'][0]-269.759)<5 for r in extraction),('Extraction placement failed',extraction)
            aim('Shirt_T7');next_(.6)
        elif phase==16:use();next_(2)
        elif phase==17:
            assert d.get_editor_property('ClothingSearchStage')==6,snap('first_escape_failed')
            released('first_escape_released')
            assert unreal.Name('Shirt') not in bag.get_editor_property('Items')
            aim('Shirt_T7');next_(.6)
        elif phase==18:use();next_(2)
        elif phase==19:
            assert d.get_editor_property('ClothingSearchStage')==7,snap('second_escape_failed')
            released('second_escape_released')
            assert unreal.Name('Shirt') not in bag.get_editor_property('Items')
            if camera_only:return finish('final_camera_shots_captured')
            # the carried set (2026-11-10): a duplicate Add doesn't grow it, and the shirt is always accepted
            before=list(bag.get_editor_property('Items'))
            for item in ('Key','Screwdriver','KeyStub','Hanger'):
                bag.call_method('Add',(item,));bag.call_method('Add',(item,))
            grown=list(bag.get_editor_property('Items'))
            assert len(grown)==len(set(str(i) for i in grown)),('duplicate in the carried set',grown)
            S['rows'].append(dict(label='carried_set_no_duplicates',before=[str(i) for i in before],after=[str(i) for i in grown]))
            aim('Shirt_T7');next_(.6)
        elif phase==20:
            use();next_(.2)
        elif phase==21:
            if d.get_editor_property('ClothingSearchStage')!=9:return
            if not actors['Encounter_T8'].get_editor_property('bPlayerTurn'):return
            if not S.get('battle_settled_at'):
                S['battle_settled_at']=time.time()+.8;return
            if time.time()<S['battle_settled_at']:return
            if not S.get('battle_shot_at'):
                if not shot('clothing_battle_first_command'):return
                S['rows'].append(dict(label='battle_roster',garments=garment_roster()))
                S['battle_shot_at']=time.time()+.2;return
            if time.time()<S['battle_shot_at']:return
            if 9 not in {r['stage'] for r in S['trace']}:return
            r=snap('shirt_taken');assert r['beat']==8 and r['states']['Shirt_T7']=='Taken',r
            assert 25<p.get_actor_location().z<300 and not p.character_movement.is_falling(),('Battle pawn below floor or falling',p.get_actor_location())
            assert 20<r['camera'][2]<295,('Battle camera outside room',r)
            assert {2,3,4} <= S['seen'],S['seen']
            assert {5,6,7,8,9} <= {r['stage'] for r in S['trace']}
            assert all(r['beat']<8 and 'Shirt' not in r['items'] for r in S['trace'] if r['stage']<9)
            for mode in (1,2,3):
                points=[r['shirt'] for r in S['trace'] if r['flight'] and r['mode']==mode]
                assert len(points)>=3,('Missing continuous flight',mode,points)
                assert max(sum((a-b)**2 for a,b in zip(points[0],p)) for p in points)>100,('Flight did not travel',mode)
            assert actors['Encounter_T8'].get_editor_property('bActive')
            d.call_method('ResetHouse',());next_(.5)
        elif phase==22:
            assert d.get_editor_property('ClothingSearchStage')==0,snap('reset_stage_failed')
            assert not actors['Encounter_T8'].get_editor_property('bActive')
            assert actors['Shirt_T7'].get_actor_transform().export_text()==S['shirt_home']
            released('battle_reset_released')
            # Deliberate QA replay: cancel a flight without replaying every earlier puzzle.
            d.call_method('StartClothingSearch',())
            d.call_method('SearchWardrobeClue',())
            d.call_method('SearchDeskClue',())
            d.call_method('SearchBedClue',())
            d.call_method('CancelClothingInspection',())
            S['cancel_home']=p.get_actor_location().to_tuple();S['cancel_radius']=p.capsule_component.get_unscaled_capsule_radius()
            d.call_method('BeginClothingToss',());next_(.45)
        elif phase==23:
            if not d.get_editor_property('bClothingFlight'):return
            d.call_method('CancelClothingInspection',());next_(.35)
        elif phase==24:
            released('active_flight_cancelled')
            assert not d.get_editor_property('bClothingFlight')
            assert not d.get_editor_property('bClothingChaseActive')
            assert p.capsule_component.get_unscaled_capsule_radius()==S['cancel_radius']
            assert sum((a-b)**2 for a,b in zip(p.get_actor_location().to_tuple(),S['cancel_home']))<.1
            assert d.get_editor_property('ClothingSearchStage')==5
            assert str(actors['Shirt_T7'].get_editor_property('State'))=='ChaseOne'
            d.call_method('ResetHouse',());next_(.2)
        elif phase==25:
            assert d.get_editor_property('ClothingSearchStage')==0
            assert actors['Shirt_T7'].get_actor_transform().export_text()==S['shirt_home']
            S['knowledge_before_morning']=set(gi.get_editor_property('Knowledge'))
            S['notebook_before_morning']=list(gi.get_editor_property('Notebook'))
            assert bag.get_editor_property('Items'), 'ResetHouse unexpectedly emptied same-day pockets'
            d.call_method('BeginMorning',());next_(.1)
        elif phase==26:
            assert not bag.get_editor_property('Items'),snap('morning_inventory_not_cleared')
            assert bag.get_editor_property('Selected')==-1
            assert set(gi.get_editor_property('Knowledge'))==S['knowledge_before_morning']
            assert list(gi.get_editor_property('Notebook'))==S['notebook_before_morning']
            snap('new_morning_clears_only_physical_items')
            finish('real_input_shirt_chase_vase_and_battle_passed')
    except AwaitNaturalScan:return
    except Exception as exc:
        snap('failure');S['rows'].append(dict(error=repr(exc)));finish('failed')
S['h']=unreal.register_slate_post_tick_callback(tick)
