"""Five isolated source pose holds through the real Teen retargeter; never opens a sequence."""
import unreal,json
from pathlib import Path
E=unreal.EditorAssetLibrary;AP=unreal.AnimPoseExtensions
root='/Game/FoA/Characters/Teen/_FingerQA'
src=unreal.load_asset(root+'/AS_FingerSource') or E.duplicate_asset('/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle',root+'/AS_FingerSource')
assert src
ref=AP.get_reference_pose(src.get_editor_property('skeleton'));names=[str(n) for n in AP.get_bone_names(ref)]
data=json.loads(Path('P:/FoA/Saved/Integration/finger_transient_test.json').read_text())
cases=['baseline','hips_translate','hips_rotate','index_rotate','neutral','relaxed'];frames=[]
for case in cases:frames += [data[case]['local_bones']]*30
c=src.get_editor_property('controller')
if __import__('os').environ.get('FOA_CLOSE_BRACKET')=='1':c.close_bracket(False)
c.open_bracket('Isolated manual finger diagnostic',False)
c.set_frame_rate(unreal.FrameRate(30,1),False);c.set_number_of_frames(unreal.FrameNumber(len(frames)-1),False)
for b in names:
    fallback=AP.get_bone_pose(ref,b,unreal.AnimPoseSpaces.LOCAL)
    ps=[unreal.Vector(*f[b]['p']) if b in f else fallback.translation for f in frames]
    qs=[unreal.Quat(*f[b]['q']) if b in f else fallback.rotation for f in frames]
    ss=[unreal.Vector(*f[b]['s']) if b in f else fallback.scale3d for f in frames]
    c.set_bone_track_keys(b,ps,qs,ss,False)
c.close_bracket(False);src.set_editor_property('enable_root_motion',False)
unreal.AnimationLibrary.remove_all_animation_notify_tracks(src);E.save_loaded_asset(src,False)
inputs=unreal.IKRetargetBatchOperationInputs()
for key,value in [('assets_to_retarget',[E.find_asset_data(src.get_path_name())]),('source_mesh',unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')),('target_mesh',unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')),('ik_retarget_asset',unreal.load_asset('/Game/FoA/Characters/Player/Retarget/RTG_Mannequin_to_Teen')),('target_path',root+'/Target'),('include_referenced_assets',False),('overwrite_existing_files',True)]:inputs.set_editor_property(key,value)
out=unreal.IKRetargetBatchOperation.run_batch_retarget(inputs);assert len(out)==1
target=out[0].get_asset();E.save_loaded_asset(target,False)
opts=unreal.AnimPoseEvaluationOptions();opts.evaluation_type=unreal.AnimDataEvalType.RAW
report={'source':src.get_path_name(),'target':target.get_path_name(),'cases':{}}
for i,case in enumerate(cases):
    pose=AP.get_anim_pose_at_time(target,i+.8,opts)
    report['cases'][case]={str(b):{'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())} for b in AP.get_bone_names(pose) for t in [AP.get_bone_pose(pose,b,unreal.AnimPoseSpaces.WORLD)]}
Path('P:/FoA/Saved/Integration/finger_retarget_test.json').write_text(json.dumps(report,indent=1));print('FINGER_RETARGET_TEST',target.get_path_name(),cases)
