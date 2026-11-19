"""Read animation/reference finger transforms and both retarget stages without evaluating any live rig."""
import json,unreal
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
A=unreal.AnimPoseExtensions;opt=unreal.AnimPoseEvaluationOptions();opt.evaluation_type=unreal.AnimDataEvalType.RAW
P='/Game/FoA/Characters/Player';out={'clips':{},'retargets':{},'references':{}}
def xf(t):return dict(p=list(t.translation.to_tuple()),q=list(t.rotation.to_tuple()),s=list(t.scale3d.to_tuple()))
def bones(pose):
 return {str(n):{space.name:xf(A.get_bone_pose(pose,n,space)) for space in (unreal.AnimPoseSpaces.LOCAL,unreal.AnimPoseSpaces.WORLD)} for n in A.get_bone_names(pose)}
for name,path in [('original',P+'/Source/UAL1/AL_StandardRig_Interact'),('manny',P+'/Anims/UAL/UAL_Interact'),('idle',P+'/Anims/UAL/UAL_Idle_Loop')]:
 seq=unreal.load_asset(path);assert seq,path
 out['clips'][name]={'path':path,'length':seq.get_play_length(),'reference':bones(A.get_reference_pose(seq.get_editor_property('skeleton'))),'poses':{str(t):bones(A.get_anim_pose_at_time(seq,t,opt)) for t in (0.,.3,.6,1.,1.5)}}
for name in ('RTG_UAL1_to_Mannequin','RTG_Mannequin_to_Teen'):
 c=unreal.IKRetargeterController.get_controller(unreal.load_asset(P+'/Retarget/'+name));r={'ops':[],'poses':{}}
 for i in range(c.get_num_retarget_ops()):r['ops'].append(dict(name=str(c.get_op_name(i)),settings=c.get_op_controller(i).get_settings().export_text()))
 for side in (unreal.RetargetSourceOrTarget.SOURCE,unreal.RetargetSourceOrTarget.TARGET):
  r['poses'][side.name]={str(k):v.export_text() for k,v in c.get_retarget_poses(side).items()}
 out['retargets'][name]=r
mesh=unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
out['references']['teen']=bones(A.get_reference_pose(mesh.get_editor_property('skeleton')))
Path('P:/FoA/Saved/Integration/environment_finger_audit.json').write_text(json.dumps(out,indent=1));print('Read source, Manny and Teen finger reference contracts')
