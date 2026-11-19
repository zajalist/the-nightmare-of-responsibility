"""Only the active left finger grasp; preserve wrist, thumb, body, right hand and sleep."""
import json,datetime,shutil,unreal
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
path='/Game/FoA/Characters/Player/Anims/UAL/UAL_Interact';seq=unreal.load_asset(path)
dst=Path('P:/FoA/Saved/Backups/environment_grasp')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');dst.mkdir(parents=True)
shutil.copy2('P:/FoA/Content/FoA/Characters/Player/Anims/UAL/UAL_Interact.uasset',dst/'UAL_Interact.uasset')
A=unreal.AnimPoseExtensions;L=unreal.AnimPoseSpaces.LOCAL;O=unreal.AnimPoseEvaluationOptions();O.evaluation_type=unreal.AnimDataEvalType.RAW
sleep=A.get_anim_pose_at_time(unreal.load_asset('/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying'),0.,O)
pose=A.get_anim_pose_at_time(seq,0.,O);names=[str(n) for n in A.get_bone_names(pose)]
chosen=[n for n in names if n.endswith('_l') and n.startswith(('index_0','middle_0','ring_0','pinky_0'))]
length=seq.get_play_length();count=unreal.AnimationLibrary.get_num_frames(seq)+1
def preserved():return [[A.get_bone_pose(A.get_anim_pose_at_time(seq,t,O),n,L).export_text() for n in names if n not in chosen] for t in [0,.5,1,1.5,2]]
before=preserved();c=seq.get_editor_property('controller');c.open_bracket('Shape the opening grasp',False)
for n in chosen:
 old=A.get_bone_pose(pose,n,L);base=A.get_bone_pose(sleep,n,L);joint=int(n.split('_')[1]);extra=(35.,45.,25.)[joint-1];rots=[]
 for i in range(count):
  t=length*i/(count-1);a=min(max((t-.15)/.3,0.),max((1.55-t)/.4,0.),1.);a=a*a*(3-2*a)
  q=unreal.MathLibrary.rotator_from_axis_and_angle(unreal.Vector(0,0,1),-extra*a).quaternion();rots.append(unreal.MathLibrary.multiply_quat_quat(base.rotation,q))
 c.set_bone_track_keys(n,[old.translation]*count,rots,[old.scale3d]*count,False)
c.close_bracket(False);assert preserved()==before;assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
Path('P:/FoA/Saved/Integration/environment_grasp.json').write_text(json.dumps(dict(asset=path,changed=chosen,protected_tracks_exact=True,backup=str(dst)),indent=1))
print('Only12 left grasp phalanges changed; all other tracks exact')
