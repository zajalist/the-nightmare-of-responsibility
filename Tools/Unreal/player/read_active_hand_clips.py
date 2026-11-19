"""Inventory used animation finger poses, including the accepted sleep and phone grip."""
import json,unreal
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
A=unreal.AnimPoseExtensions;L=unreal.AnimPoseSpaces.LOCAL;O=unreal.AnimPoseEvaluationOptions();O.evaluation_type=unreal.AnimDataEvalType.RAW
root='/Game/FoA/Characters/Player/Anims/'
paths=[root+x for x in ('AS_FoA_PhoneHold','Hands/AS_FoA_Grip_Key_R','Hands/AS_FoA_Grip_Tool_R','GASP/AS_GASP_M_Relaxed_Stand_Idle_Loop','GASP/AS_GASP_M_Relaxed_Walk_Loop_F','Loco/AS_FoA_Walk_Brisk')]+['/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying']
out={}
for path in paths:
 s=unreal.load_asset(path);p=A.get_anim_pose_at_time(s,0.,O);ref=A.get_reference_pose(s.get_editor_property('skeleton'))
 out[path]={'length':s.get_play_length(),'bones':{str(n):{'local':A.get_bone_pose(p,n,L).export_text(),'ref':A.get_bone_pose(ref,n,L).export_text()} for n in A.get_bone_names(p) if str(n).startswith(('thumb','index','middle','ring','pinky'))}}
Path('P:/FoA/Saved/Integration/active_hand_clips.json').write_text(json.dumps(out,indent=1));print('Read',len(out),'active clip finger poses')
