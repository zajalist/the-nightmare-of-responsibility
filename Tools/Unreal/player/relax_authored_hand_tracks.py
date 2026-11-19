"""Correct authored clenched/pointing digits only; accepted sleep is the read-only pose reference."""
import hashlib,json,os,unreal
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
A=unreal.AnimPoseExtensions;L=unreal.AnimPoseSpaces.LOCAL;O=unreal.AnimPoseEvaluationOptions();O.evaluation_type=unreal.AnimDataEvalType.RAW
P='/Game/FoA/Characters/Player/Anims/'
sleep=unreal.load_asset('/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying');relax=A.get_anim_pose_at_time(sleep,0.,O)
paths=[P+x for x in ('UAL/UAL_Idle_Loop','UAL/UAL_Interact','UAL/UAL_Idle_No_Loop','AS_FoA_PhoneHold','Hands/AS_FoA_Grip_Key_R')]
def digits(n):return n.startswith(('thumb','index','middle','ring','pinky'))
def chosen(path,n):
 if not digits(n):return False
 # The right phone fingers have a separately verified case-specific grip.
 if path.endswith('AS_FoA_PhoneHold'):return n.endswith('_l')
 if path.endswith('AS_FoA_Grip_Key_R'):return n.endswith('_r') and n.startswith(('middle','ring','pinky'))
 return True
protected=['Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset','Content/FoA/Characters/Player/Retarget/RTG_Mannequin_to_Teen.uasset','Content/FoA/Characters/Teen/Mesh/SK_Teen_Body.uasset']
hashes={p:hashlib.sha256(Path('P:/FoA',p).read_bytes()).hexdigest() for p in protected};report=[]
for path in paths:
 seq=unreal.load_asset(path);assert seq,path
 count=unreal.AnimationLibrary.get_num_frames(seq)+1;length=seq.get_play_length();times=sorted(set((0.,length*.25,length*.5,length*.75,length)))
 pose=A.get_anim_pose_at_time(seq,0.,O);names=[str(n) for n in A.get_bone_names(pose)];selected=[n for n in names if chosen(path,n)];assert selected
 def invariants():
  return [[A.get_bone_pose(p,n,L).export_text() for n in names if n not in selected] for t in times for p in [A.get_anim_pose_at_time(seq,t,O)]]
 before=invariants();notifies=[str(x) for x in unreal.AnimationLibrary.get_animation_notify_track_names(seq)]
 unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
 c=seq.get_editor_property('controller');c.open_bracket('Relax only unrelated curled digits',False)
 for n in selected:
  original=A.get_bone_pose(pose,n,L);target=A.get_bone_pose(relax,n,L)
  rotations=[target.rotation]*count
  if path.endswith('UAL_Interact') and n.endswith('_l') and '_0' in n:
   # A gentle grasp replaces the original pointing fist only during the reach.
   digit=n.split('_')[0];joint=int(n.split('_')[1]);extra=(5.,8.,5.)[joint-1] if digit=='thumb' else (35.,45.,25.)[joint-1]
   rotations=[]
   for frame in range(count):
    t=length*frame/max(1,count-1);a=min(max((t-.15)/.3,0.),max((1.55-t)/.4,0.),1.);a=a*a*(3-2*a)
    curl=unreal.MathLibrary.rotator_from_axis_and_angle(unreal.Vector(0,0,1),-extra*a).quaternion()
    rotations.append(unreal.MathLibrary.multiply_quat_quat(target.rotation,curl))
  c.set_bone_track_keys(n,[original.translation]*count,rotations,[original.scale3d]*count,False)
 c.close_bracket(False)
 assert before==invariants(),path+' non-finger/contact tracks changed'
 assert count==unreal.AnimationLibrary.get_num_frames(seq)+1 and length==seq.get_play_length()
 assert notifies==[str(x) for x in unreal.AnimationLibrary.get_animation_notify_track_names(seq)]
 assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
 report.append(dict(path=path,changed=selected,preserved=len(names)-len(selected),frames=count,non_selected_pose_samples_exact=True))
assert all(hashlib.sha256(Path('P:/FoA',p).read_bytes()).hexdigest()==v for p,v in hashes.items()),'Protected sleep/rig/mesh changed'
Path('P:/FoA/Saved/Integration/authored_hand_relaxation.json').write_text(json.dumps(dict(clips=report,protected_hashes=hashes),indent=1));print('Finger-only relaxation saved',[(r['path'],len(r['changed'])) for r in report])

