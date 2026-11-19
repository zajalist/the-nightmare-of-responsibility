"""Bounded closet, headache and clothing-search regression, with explicit T7 preconditions.
QA enters T7 directly after the closet/headache checks; every search action uses the real interactor.
"""
import time,json,math
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
def one(path):return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/'+path))
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
d=one('Gameplay/BP_BeatDirector.BP_BeatDirector_C');fe=one('UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
enc=one('Gameplay/Encounter/BP_Encounter.BP_Encounter_C');assert enc,'Missing encounter controller'
dream=one('PostProcess/BP_DreamDirector.BP_DreamDirector_C');assert dream
mpc=unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
old_motion=unreal.MaterialLibrary.get_scalar_parameter_value(w,mpc,'ReduceMotion')
actors={a.get_actor_label():a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)}
closet=actors['Wardrobe_GothicCabinet_01_door1'];shirt=actors['Shirt_T7']
wardrobe=actors['Wardrobe'];desk=actors['Desk'];bed=actors['Bed'];hanger=actors['Hanger_CoatRail']
shirt_home=shirt.get_actor_transform().export_text()
ia=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_RoomBlockers',set(),[]))
S=dict(start=time.time(),phase=0,at=0,rows=[],failures=[],h=None,done=False)
def snap(label):
 pivot=next(c for c in closet.get_components_by_class(unreal.SceneComponent) if c.get_name()=='Pivot')
 row=dict(label=label,t=round(time.time()-S['start'],2),beat=d.get_editor_property('BeatIndex'),
  closet=str(closet.get_editor_property('State')),yaw=round(pivot.get_editor_property('relative_rotation').yaw,2),
  pending=closet.get_editor_property('bPendingRow'),shirt=str(shirt.get_editor_property('State')),
  shirt_pending=shirt.get_editor_property('bPendingRow'),fight=enc.get_editor_property('bActive'),
  battle=str(enc.get_editor_property('BattleState')),view=pc.get_view_target().get_class().get_name(),
  move=pc.is_move_input_ignored(),look=pc.is_look_input_ignored(),z=p.get_actor_location().z,vz=p.get_velocity().z,
  headache=d.get_editor_property('bHeadacheActive'),echo=dream.get_editor_property('BaseEcho'),
  search=d.get_editor_property('ClothingSearchStage'),wardrobe=str(wardrobe.get_editor_property('State')),
  desk=str(desk.get_editor_property('State')),bed=str(bed.get_editor_property('State')))
 row.update(can_jump=p.can_jump(),jump_max=p.get_editor_property('jump_max_count'),jump_count=p.get_editor_property('jump_current_count'),
  movement_mode=str(p.get_character_movement().get_editor_property('movement_mode')),
  cinematic=p.get_editor_property('bCinematic'),interaction=p.get_editor_property('bInteractionLocked'))
 S['rows'].append(row);return row
def interact(a):
 loc=a.get_actor_location();v=unreal.Vector(-loc.x,-loc.y,0);v.normalize()
 stand=loc+v*95;stand.z=p.get_actor_location().z
 assert p.teleport(stand,p.get_actor_rotation())
 pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(stand+unreal.Vector(0,0,60),loc))
 ia.call_method('SetFocus',(a,));ia.call_method('Refresh',(True,));ia.call_method('Interact',())
def advance(delay=0):S['phase']+=1;S['at']=time.time()+delay
def finish(reason):
 if S['done']:return
 S['done']=True
 if S['h']:unreal.unregister_slate_post_tick_callback(S['h'])
 gi.call_method('SetProofProgressContext',original)
 unreal.MaterialLibrary.set_scalar_parameter_value(w,mpc,'ReduceMotion',old_motion)
 unreal.GameplayStatics.delete_game_in_slot('FoA_QA_RoomBlockers',0)
 Path('P:/FoA/Saved/Integration/room_blockers_runtime.json').write_text(json.dumps(dict(reason=reason,rows=S['rows'],failures=S['failures']),indent=2))
 print('ROOM_BLOCKERS',reason)
def tick(dt):
 try:
  t=time.time()-S['start'];i=S['phase']
  if t>44:return finish('timeout')
  if time.time()<S['at']:return
  if i==0:fe.call_method('OnSplashFinished',());advance(.4)
  elif i==1:fe.call_method('OnTitleConfirmed',());advance(.5)
  elif i==2:fe.call_method('WakeUp',());advance(.4)
  elif i==3:
   story=fe.get_editor_property('Story')
   if story and story.is_in_viewport():story.call_method('Finish',());return
   if pc.get_view_target().get_class().get_name()=='CineCameraActor':d.call_method('SkipWakeUp',());advance(1)
  elif i==4:
   if d.get_editor_property('BeatIndex')!=1:return
   unreal.SystemLibrary.pause_timer(d,'PollStoryMoment')
   unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
   d.call_method('EnterBeat',(2,));interact(closet);advance(1.8)
  elif i==5:
   r=snap('opened');assert r['closet']=='Open' and abs(r['yaw'])>90,r
   interact(closet);advance(3)
  elif i==6:
   r=snap('closed');assert r['closet']=='Closed' and abs(r['yaw'])<.1,r
   interact(closet);advance(3)
  elif i==7:
   r=snap('reopened');assert r['closet']=='Open' and abs(r['yaw'])>90,r
   p.call_method('SetInteractionLocked',(True,))
   Path('P:/FoA/Saved/Integration/room_jump_request.json').write_text(json.dumps(dict(id=1)))
   advance(.8)
  elif i==8:
   r=snap('jump_while_locked');assert abs(r['vz'])<.1,r
   p.call_method('SetInteractionLocked',(False,))
   Path('P:/FoA/Saved/Integration/room_jump_request.json').write_text(json.dumps(dict(id=2)))
   advance(.3)
  elif i==9:
   r=snap('jump_after_unlock')
   if abs(r['vz'])>.1 or r['can_jump'] or r['jump_max']!=0:S['failures'].append('Jump must remain disabled during exploration')
   advance(1)
  elif i==10:
   d.call_method('EnterBeat',(2,))
   unreal.MaterialLibrary.set_scalar_parameter_value(w,mpc,'ReduceMotion',0)
   S['echo']=dream.get_editor_property('BaseEcho')
   S['pos']=p.get_actor_location()
   d.call_method('ResetStoryMoments',())
   unreal.SystemLibrary.un_pause_timer(d,'PollStoryMoment')
   advance(.1)
  elif i==11:
   if not d.get_editor_property('bHeadacheActive'):return
   r=snap('headache_started');assert r['move'] and r['look'],r
   advance(1.5)
  elif i==12:
   r=snap('headache_peak');assert r['headache'] and r['echo']>S['echo']+.1,r
   assert math.dist(p.get_actor_location().to_tuple(),S['pos'].to_tuple())<.1,'Headache moved pawn'
   montage=p.get_current_montage()
   assert montage and montage.get_name()=='AM_FoA_Headache',str(montage)
   unreal.SystemLibrary.execute_console_command(w,'Shot showui filename=P:/FoA/Saved/Integration/headache_after.png -nosuffix',pc)
   advance(3)
  elif i==13:
   r=snap('headache_released');assert not r['headache'] and not r['move'] and not r['look'],r
   assert abs(r['echo']-S['echo'])<.001,r
   unreal.SystemLibrary.pause_timer(d,'PollStoryMoment')
   d.call_method('ReportEvent',('WardrobeLanded',));snap('explicit_T7_fixture');advance(.5)
  elif i==14:
   if d.get_editor_property('BeatIndex')!=7 or d.get_editor_property('bWardrobeTransition'):return
   if d.get_editor_property('bTopDown'):return
   r=snap('search_started');assert r['search']==1 and r['shirt']=='Hidden',r
   d.call_method('ReportEvent',('ShirtTaken',))
   assert d.get_editor_property('BeatIndex')==7,'Early ShirtTaken bypassed search'
   interact(wardrobe);advance(.3)
  elif i==15:
   r=snap('wardrobe_clue');assert r['search']==2 and r['shirt']=='Hidden',r
   interact(wardrobe);assert d.get_editor_property('ClothingSearchStage')==2,'Repeated clue advanced twice'
   interact(desk);advance(2)
  elif i==16:
   r=snap('desk_trail');assert r['search']==3 and r['shirt']=='Hidden',r
   interact(bed);advance(2)
  elif i==17:
   r=snap('bed_snag');assert r['search']==4 and r['shirt']=='Hidden',r
   bed.call_method('Interact',(unreal.Name('Use'),unreal.Name('KeyStub')))
   assert d.get_editor_property('ClothingSearchStage')==4,'Wrong item advanced search'
   interact(hanger);advance(2)
  elif i==18:
   bag=ia.get_editor_property('Inventory');assert unreal.Name('Hanger') in bag.get_editor_property('Items')
   interact(bed);advance(2)
  elif i==19:
   r=snap('shirt_freed');assert r['search']==5 and r['shirt']=='Available',r
   assert len([n for n in gi.get_editor_property('Knowledge') if str(n).startswith('Knows.Clothing')])==3
   interact(shirt);snap('real_shirt_interact');advance(2)
  elif i==20:
   r=snap('fight_started');assert r['beat']==8 and r['fight'] and r['view']=='BP_Encounter_C',r
   assert len(enc.get_editor_property('Garments'))>0,'No opponents'
   unreal.SystemLibrary.execute_console_command(w,'Shot showui filename=P:/FoA/Saved/Integration/room_fight_after.png -nosuffix',pc)
   d.call_method('ResetHouse',());advance(.3)
  elif i==21:
   r=snap('search_reset');assert r['search']==0 and r['shirt']=='Hidden',r
   assert shirt.get_actor_transform().export_text()==shirt_home,'Shirt transform did not reset'
   assert all(a.get_editor_property('State')==a.get_editor_property('MorningState') for a in (wardrobe,desk,bed))
   return finish('closet_jump_headache_clothing_search_and_fight_passed' if not S['failures'] else 'partial_failure')
 except Exception as e:
  S['rows'].append(dict(error=repr(e)));finish('error')
S['h']=unreal.register_slate_post_tick_callback(tick)
