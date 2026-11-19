import unreal,json
from pathlib import Path
s=unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence();assert s.get_name()=='LS_WakeUp_ManualPose'
channels=[c for b in s.get_bindings() for t in b.get_tracks() if isinstance(t,unreal.MovieSceneControlRigParameterTrack) for sec in t.get_sections() for c in sec.get_all_channels()]
report={'frame':unreal.LevelSequenceEditorBlueprintLibrary.get_current_time(),'channels':[{'name':str(c.get_name()),'default':str(c.get_default()),'keys':[{'frame':k.get_time().frame_number.value,'value':str(k.get_value())} for k in c.get_keys()]} for c in channels if 'thumb_01_l' in str(c.get_name()) or 'middle_metacarpal_l' in str(c.get_name())]}
Path('P:/FoA/Saved/Integration/manual_finger_channels.json').write_text(json.dumps(report,indent=1));print(json.dumps(report))
