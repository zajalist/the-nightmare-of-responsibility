"""Disable neighbor-finger interpolation in the manual sequence, preserving authored pose channels."""
import unreal,json,datetime
from pathlib import Path
L=unreal.LevelSequenceEditorBlueprintLibrary;s=L.get_current_level_sequence()
assert s and s.get_name()=='LS_WakeUp_ManualPose' and not L.is_playing()
r=unreal.ControlRigSequencerLibrary.get_control_rigs(s)[0].control_rig;h=r.get_hierarchy()
controls=[k for k in h.get_controls() if 'Auto Interpolate' in str(k.name)]
all_channels=[c for b in s.get_bindings() for t in b.get_tracks() if isinstance(t,unreal.MovieSceneControlRigParameterTrack) for sec in t.get_sections() for c in sec.get_all_channels()]
channels=[c for c in all_channels if 'Auto Interpolate' in str(c.get_name())]
assert len(controls)==len(channels)==4
others=[c for c in all_channels if c not in channels]
def authored():return [(str(c.get_default()),[(k.get_time().frame_number.value,str(k.get_value())) for k in c.get_keys()]) for c in others]
before=authored()
with unreal.ScopedEditorTransaction('Make manual fingers independent'):
 for c in channels:
  c.set_default(False)
  for key in c.get_keys():key.set_value(False)
 for k in controls:h.set_control_value(k,unreal.RigHierarchy.make_control_value_from_bool(False))
assert before==authored(),'Existing authored pose channels changed'
assert all(unreal.RigHierarchy.get_int_from_control_value(h.get_control_value(k))==0 for k in controls)
assert unreal.EditorAssetLibrary.save_loaded_asset(s,False)
Path('P:/FoA/Saved/Integration/finger_independence_fix.json').write_text(json.dumps({'disabled':[str(k.name) for k in controls],'existing_pose_channels_preserved':True,'checked_channels':len(others),'interactive_drag_tested':False},indent=2))
