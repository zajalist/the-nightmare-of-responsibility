"""Bounded real-front-end camera proof, including an animated head pose."""
import json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
def actor(path):return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
d=actor('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
fe=actor('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
parts={c.get_name():c for c in p.get_components_by_class(unreal.SceneComponent)}
face=parts['Face'];cam=parts['FollowCamera'];start=time.time()
S=dict(i=0,at=0,h=None,rows=[],done=False)
out=Path('P:/FoA/Saved/Integration')
def finish(reason):
 if S['done']:return
 S['done']=True
 if S['h']:unreal.unregister_slate_post_tick_callback(S['h'])
 (out/'first_person_runtime.json').write_text(json.dumps(dict(reason=reason,rows=S['rows']),indent=2))
def step(delay=.4):S['i']+=1;S['at']=time.time()+delay
def snap(label):
 target=unreal.MathLibrary.transform_location(face.get_socket_transform('head',unreal.RelativeTransformSpace.RTS_WORLD),unreal.Vector(0,-3.530588955620998,11.768322164387774))
 loc=cam.get_world_location()
 row=dict(label=label,t=time.time()-start,camera=[loc.x,loc.y,loc.z],target=[target.x,target.y,target.z],
  error=(loc-target).length(),parent=cam.get_attach_parent().get_name(),socket=str(cam.get_attach_socket_name()),
  face_visible=face.is_visible(),hair_visible=parts['Hair'].is_visible(),can_jump=p.can_jump(),jump_max=p.get_editor_property('jump_max_count'))
 cr=cam.get_world_rotation();pr=pc.get_control_rotation()
 row.update(camera_rot=[cr.pitch,cr.yaw,cr.roll],control_rot=[pr.pitch,pr.yaw,pr.roll])
 across=parts['Body'].get_socket_location('upperarm_r')-parts['Body'].get_socket_location('upperarm_l')
 forward=unreal.MathLibrary.cross_vector_vector(across,unreal.Vector(0,0,1))
 torso=unreal.MathLibrary.make_rot_from_x(forward)
 relative=unreal.MathLibrary.normalized_delta_rotator(cr,torso)
 row['torso_yaw']=torso.yaw;row['neck_yaw']=relative.yaw
 S['rows'].append(row)
 assert row['parent']=='Face' and row['socket']=='head' and row['error']<.2,row
 assert not row['face_visible'] and not row['hair_visible'] and not row['can_jump'] and row['jump_max']==0,row
 assert abs(cr.pitch-pr.pitch)<1 and abs(cr.yaw-pr.yaw)<1 and abs(cr.roll)<1,row
 assert abs(relative.yaw)<=60.5 and -65.5<=cr.pitch<=65.5,row
 (out/'fp_capture_request.json').write_text(json.dumps(dict(name=label)))
def tick(dt):
 try:
  if time.time()-start>28:return finish('timeout')
  if time.time()<S['at']:return
  i=S['i']
  if i==0:fe.call_method('OnSplashFinished',());step()
  elif i==1:fe.call_method('OnTitleConfirmed',());step()
  elif i==2:fe.call_method('WakeUp',());step()
  elif i==3:
   story=fe.get_editor_property('Story')
   if story and story.is_in_viewport():story.call_method('Finish',());return
   if not fe.get_editor_property('bInGameplay') or not d.get_editor_property('SeqPlayer'):return
   if not d.get_editor_property('bWakeDone'):d.call_method('SkipWakeUp',())
   step(.2)
  elif i==4:
   if not d.get_editor_property('bWakeDone') or d.get_editor_property('BeatIndex')!=1:return
   unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
   pc.set_control_rotation(unreal.Rotator(0,0,0));step(.5)
  elif i==5:snap('fp_forward');step(.6)
  elif i==6:pc.set_control_rotation(unreal.Rotator(pitch=-65,yaw=0,roll=0));step(.6)
  elif i==7:snap('fp_down');step(.6)
  elif i==8:pc.set_control_rotation(unreal.Rotator(0,0,0));p.call_method('SetCinematic',(True,));p.play_anim_montage(unreal.load_asset('/Game/FoA/Characters/Player/Montages/AM_FoA_Headache'));step(1.5)
  elif i==9:snap('fp_head_motion');step(1.2)
  elif i==10:snap('fp_head_return');step(.5)
  elif i==11:
   p.stop_anim_montage();p.call_method('SetCinematic',(True,))
   S['fixed_yaw']=p.get_actor_rotation().yaw
   pc.set_control_rotation(unreal.Rotator(pitch=-89,yaw=S['fixed_yaw']+180,roll=0));step(.6)
  elif i==12:snap('fp_locked_back_down');step(.3)
  elif i==13:pc.set_control_rotation(unreal.Rotator(pitch=89,yaw=S['fixed_yaw']-170,roll=0));step(.6)
  elif i==14:snap('fp_locked_back_up');step(.3)
  elif i==15:
   p.call_method('SetCinematic',(False,))
   pc.set_control_rotation(unreal.Rotator(pitch=-65,yaw=S['fixed_yaw']+160,roll=0));step(2.5)
  elif i==16:snap('fp_turn_body');step(.3)
  elif i==17:return finish('head_follow_visibility_neck_limits_and_no_jump_passed')
 except Exception as err:finish(str(err))
S['h']=unreal.register_slate_post_tick_callback(tick)
