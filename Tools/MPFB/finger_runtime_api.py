"""Read-only API and current finger-space inventory; never evaluates the user's rig."""
import unreal,json
from pathlib import Path
s=unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence();assert s and s.get_name()=='LS_WakeUp_ManualPose'
r=unreal.ControlRigSequencerLibrary.get_control_rigs(s)[0].control_rig;h=r.get_hierarchy()
bp=unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')
report={'rig':r.get_path_name(),'class':r.get_class().get_path_name(),'asset':str(bp)}
for name,obj in [('rig',r),('asset',bp),('hierarchy',h),('retarget_class',unreal.IKRetargeterController)]:
    report[name+'_api']={n:str(getattr(obj,n).__doc__)[:3000] for n in dir(obj) if any(t in n for t in ('create','duplicate','execute','initialize','evaluate','request','copy','retarget_pose','rotation_offset')) and callable(getattr(obj,n))}
report['controls']={str(k.name):{'value':h.get_control_value(k).export_text(),'global':h.get_global_transform(k).export_text(),'local':h.get_local_transform(k).export_text(),'initial':h.get_global_transform(k,True).export_text()} for k in h.get_controls() if any(t in str(k.name) for t in ('thumb','finger','pelvis','hip','hand_','arm_','Auto Interpolate'))}
Path('P:/FoA/Saved/Integration/finger_runtime_api.json').write_text(json.dumps(report,indent=1));print('FINGER_READ_ONLY',r.get_path_name())
