"""Nine phone-only support tracks; all anchors and every other track preserved."""
import unreal,json,shutil,datetime
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
P='/Game/FoA/Characters/Player/Anims/AS_FoA_PhoneHold';s=unreal.load_asset(P);A=unreal.AnimPoseExtensions;L=unreal.AnimPoseSpaces.LOCAL
O=unreal.AnimPoseEvaluationOptions();O.evaluation_type=unreal.AnimDataEvalType.RAW
fit=json.loads(Path('P:/FoA/Saved/UIShots/phone_support_candidate.json').read_text())
chosen=[f'{digit}_0{j}_r' for digit in fit['digits'] for j in (1,2,3)]
pose=A.get_anim_pose_at_time(s,0.,O);names=list(map(str,A.get_bone_names(pose)));length=s.get_play_length();frames=unreal.AnimationLibrary.get_num_frames(s)+1
ref=A.get_reference_pose(s.get_editor_property('skeleton'));times=[0.,length*.25,length*.5,length*.75,length]
def untouched():return [[A.get_bone_pose(p,n,L).export_text() for n in names if n not in chosen] for t in times for p in [A.get_anim_pose_at_time(s,t,O)]]
before=untouched();old={n:A.get_bone_pose(pose,n,L).export_text() for n in chosen}
backup=Path('P:/FoA/Saved/Backups/phone_support')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
assert unreal.EditorAssetLibrary.save_loaded_asset(s,False);shutil.copy2('P:/FoA/Content/FoA/Characters/Player/Anims/AS_FoA_PhoneHold.uasset',backup/'AS_FoA_PhoneHold.uasset')
(backup/'tracks.json').write_text(json.dumps(old,indent=2))
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(s)
c=s.get_editor_property('controller');c.open_bracket('Support the phone case',False)
for digit,row in fit['digits'].items():
 for j,curl in enumerate(row['curls'],1):
  n=f'{digit}_0{j}_r';t=A.get_bone_pose(pose,n,L);q=A.get_bone_pose(ref,n,L).rotation
  delta=unreal.MathLibrary.rotator_from_axis_and_angle(unreal.Vector(0,0,1),-curl).quaternion();q=unreal.MathLibrary.multiply_quat_quat(q,delta)
  c.set_bone_track_keys(n,[t.translation]*frames,[q]*frames,[t.scale3d]*frames,False)
c.close_bracket(False)
assert before==untouched(),'A non-support phone track changed'
assert s.get_play_length()==length and unreal.AnimationLibrary.get_num_frames(s)+1==frames
assert unreal.EditorAssetLibrary.save_loaded_asset(s,False)
Path('P:/FoA/Saved/UIShots/phone_support_preservation.json').write_text(json.dumps(dict(asset=P,changed=chosen,preserved_bones=len(names)-9,samples=times,all_other_tracks_exact=True,backup=str(backup),candidate=fit),indent=2))
print('Nine phone support tracks saved; every other track preserved',len(names)-9)
