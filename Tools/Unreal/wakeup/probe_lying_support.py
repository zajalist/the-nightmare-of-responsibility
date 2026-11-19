"""Read the actual bedding directly below previously skinned contact points; no scene edits."""
import json,sys
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
path=Path('P:/FoA/Saved/WakeUp/sleep_support_points.json');data=json.loads(path.read_text())
for row in data['points']:
    x,y,z=row['position'];surface=W.trace_down(x,y)
    row['bedding_z']=surface;row['gap_cm']=None if surface is None else z-surface
Path('P:/FoA/Saved/WakeUp/sleep_support_traced.json').write_text(json.dumps(data,indent=1))
print('SUPPORT',json.dumps(data))
