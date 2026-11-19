"""Restore the prior phone support curl while a full case-shaped grasp is calibrated."""
import json,re,unreal
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
path='/Game/FoA/Characters/Player/Anims/AS_FoA_PhoneHold'
old=json.loads(Path('P:/FoA/Saved/Integration/active_hand_clips.json').read_text())[path]['bones']
s=unreal.load_asset(path);a=unreal.AnimPoseExtensions;o=unreal.AnimPoseEvaluationOptions();p=a.get_anim_pose_at_time(s,0.,o)
c=s.get_editor_property('controller');n=unreal.AnimationLibrary.get_num_frames(s)+1
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(s)
c.open_bracket('Restore phone support fingers',False)
changed=[]
for name,record in old.items():
 if not(name.endswith('_r') and name.startswith(('middle','ring','pinky'))):continue
 q=unreal.Quat(*map(float,re.search(r'Rotation=\(X=([^,]+),Y=([^,]+),Z=([^,]+),W=([^)]+)',record['local']).groups()))
 t=a.get_bone_pose(p,name,unreal.AnimPoseSpaces.LOCAL);c.set_bone_track_keys(name,[t.translation]*n,[q]*n,[t.scale3d]*n,False);changed.append(name)
c.close_bracket(False);assert unreal.EditorAssetLibrary.save_loaded_asset(s,False)
print('Restored phone right support curl only',changed)
