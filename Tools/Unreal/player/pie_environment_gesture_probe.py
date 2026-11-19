"""Bounded production-row contact audit; transient cameras and proof-only progress context."""
import datetime,json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
find=lambda path:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
d=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
ia=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
actors={a.get_actor_label():a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)}
gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_EnvironmentGestures',set(),[]))
folder=Path('P:/FoA/Saved/CharacterShots/environment_gestures')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True)
out=Path('P:/FoA/Saved/Integration/environment_gesture_probe.json')
request=Path('P:/FoA/Saved/Integration/environment_gesture_input.json');ack=Path('P:/FoA/Saved/Integration/environment_gesture_input_ack.json')
cam=actors['Door_Bedroom'];cc=next(c for c in cam.get_components_by_class(unreal.CameraComponent) if c.get_name()=='ToolCamera')
camera_original=(cc.get_relative_transform(),cc.field_of_view,cc.is_active())
cc.set_field_of_view(54);cc.set_active(True)
cases=[('door_far','Door_Bedroom','Locked',(280,60,90),(255,-65,155),(365,66,105),.5),
       ('door_handle','Door_Bedroom','Locked',(325,64,90),(315,140,120),(369,48,97),4.3),
       ('wardrobe_open','Wardrobe_GothicCabinet_01_door1','Closed',(210,154,90),(240,130,175),(222,198,140),2.3),
       ('wardrobe_close','Wardrobe_GothicCabinet_01_door1',None,(260,110,90),(340,85,155),(305,130,140),2.3),
       ('drawer_open','Commode_GothicCommode_01_door01','Closed',(-132,198,90),(-20,190,125),(-118,242,100),2.3),
       ('door_push','Door_Bedroom','HandleOff',(325,77,90),(270,10,155),(374,68,134),2.3),
       ('cancel','Door_Bedroom','Locked',(325,64,90),(255,-65,155),(365,66,105),.8)]
S=dict(start=time.time(),h=None,done=False,index=-1,at=0,samples=[],shots=set(),results=[])
def xf(t):return dict(position=list(t.translation.to_tuple()),rotation=list(t.rotation.to_tuple()),scale=list(t.scale3d.to_tuple()))
def finish(reason):
 if S['done']:return
 S['done']=True;unreal.unregister_slate_post_tick_callback(S['h'])
 try:
  a=S.get('actor')
  if a and a.get_editor_property('bPendingRow'):a.call_method('CancelPendingRow',(True,))
  p.stop_anim_montage();p.call_method('EndInteraction',());pc.set_view_target_with_blend(p,0)
  cc.set_relative_transform(camera_original[0],False,True);cc.set_field_of_view(camera_original[1]);cc.set_active(camera_original[2])
 finally:
  gi.call_method('SetProofProgressContext',original);unreal.GameplayStatics.delete_game_in_slot('FoA_QA_EnvironmentGestures',0)
  result=dict(status='complete',reason=reason,folder=str(folder),samples=S['samples'],results=S['results'],input='Native E for far rejection and nearby retry; production row calls for remaining geometry views')
  out.write_text(json.dumps(result,indent=1));(folder/'evidence.json').write_text(json.dumps(result,indent=1))
def begin(i):
 name,label,state,stand,eye,aim,duration=cases[i];a=actors[label]
 if state:a.call_method('SetState',(state,True))
 rot=unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*stand),unreal.Vector(*aim));rot.pitch=0;rot.roll=0
 assert p.teleport(unreal.Vector(*stand),rot),'QA stance collision '+name
 pc.set_control_rotation(rot)
 cc.set_world_location_and_rotation(unreal.Vector(*eye),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye),unreal.Vector(*aim)),False,True)
 pc.set_view_target_with_blend(cam,0)
 if i<2:
  pc.set_view_target_with_blend(p,0)
  follow=p.get_editor_property('FollowCamera');look=unreal.MathLibrary.find_look_at_rotation(follow.get_world_location(),unreal.Vector(367.3,48.5,96.5));pc.set_control_rotation(look)
 S.update(index=i,actor=a,at=unreal.GameplayStatics.get_time_seconds(w),next_sample=0,shots=set(),armed=False)
def tick(dt):
 try:
  now=time.time()
  if now-S['start']>22:return finish('timeout')
  if S['index']<0:
   unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment');d.call_method('EnterBeat',(2,));begin(0);return
  i=S['index'];name=cases[i][0];elapsed=unreal.GameplayStatics.get_time_seconds(w)-S['at'];a=S['actor'];body=p.get_editor_property('Body')
  if not S['armed']:
   if elapsed<.2:return
   ia.call_method('SetFocus',(a,));ia.call_method('Refresh',(True,))
   if i<2:
    if not S.get('requested')==i:
     request.write_text(json.dumps(dict(id=i,key='E')));S['requested']=i;return
    if not ack.exists() or json.loads(ack.read_text())['id']!=i:return
    pc.set_view_target_with_blend(cam,0)
   else:ia.call_method('Interact',())
   S.update(armed=True,at=unreal.GameplayStatics.get_time_seconds(w));return
  if name=='cancel' and elapsed>.4 and not S.get('cancelled'):
   assert a.get_editor_property('bPendingRow'),'Cancel did not start'
   a.call_method('CancelPendingRow',(True,));S['cancelled']=True
  mesh=next(c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='Mesh')
  target=unreal.MathLibrary.transform_location(mesh.get_world_transform(),p.get_editor_property('EnvironmentContactLocal'))
  if now>=S['next_sample']:
   S['next_sample']=now+.05
   hands={n:xf(body.get_socket_transform(n,unreal.RelativeTransformSpace.RTS_WORLD)) for n in ('hand_r','hand_l','upperarm_l','lowerarm_l','index_03_l','thumb_03_l')}
   palm=unreal.MathLibrary.transform_location(body.get_socket_transform('hand_l',unreal.RelativeTransformSpace.RTS_WORLD),unreal.Vector(2.04932173,-6.66835491,.33684314))
   montage=p.get_current_montage()
   weight=body.get_anim_instance().get_editor_property('EnvironmentHandWeight')
   S['samples'].append(dict(case=name,t=elapsed,hands=hands,palm=list(palm.to_tuple()),target=list(target.to_tuple()),palm_error_cm=(palm-target).length(),weight=weight,pawn=xf(p.get_actor_transform()),mesh=xf(mesh.get_world_transform()),state=str(a.get_editor_property('State')),pending=a.get_editor_property('bPendingRow'),montage=montage.get_name() if montage else None,lock=p.get_editor_property('bInteractionLocked')))
  for frame in (.65,1.1):
   if elapsed>=frame and frame not in S['shots']:
    S['shots'].add(frame)
    if frame==.65:
     poses={str(body.get_bone_name(j)):xf(body.get_socket_transform(body.get_bone_name(j),unreal.RelativeTransformSpace.RTS_WORLD)) for j in range(body.get_num_bones())}
     (folder/(name+'_body_pose.json')).write_text(json.dumps(dict(bones=poses,mesh=xf(mesh.get_world_transform()),contact=list(target.to_tuple()))))
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(folder/(name+'_'+str(frame)+'.png'))+' -nosuffix',pc);break
  if elapsed>cases[i][-1]:
   weight=body.get_anim_instance().get_editor_property('EnvironmentHandWeight')
   assert weight==0 and not p.get_editor_property('bInteractionLocked') and not a.get_editor_property('bPendingRow'),(name,'Contact cleanup failed',weight)
   if name not in ('door_far','cancel'):
    settled=[x for x in S['samples'] if x['case']==name and .5<x['t']<.9 and x['weight']>.99]
    assert settled and max(x['palm_error_cm'] for x in settled)<1.5,(name,'Settled contact missed',settled)
   if name=='door_far':
    assert str(a.get_editor_property('State'))=='Locked' and not a.get_editor_property('bPendingRow') and not p.get_editor_property('bInteractionLocked'),'Far rejection changed state'
   S['results'].append(dict(case=name,state=str(a.get_editor_property('State')),locked=p.get_editor_property('bInteractionLocked'),pending=a.get_editor_property('bPendingRow')))
   if i+1==len(cases):return finish('baseline_complete')
   begin(i+1)
 except Exception as exc:finish('failed:'+repr(exc))
S['h']=unreal.register_slate_post_tick_callback(tick)

