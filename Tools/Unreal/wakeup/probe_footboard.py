"""Read actual footboard height and sleeping source feet without touching furniture or poses."""
import json,sys,os
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
bed=W.native_bounds(W.room_actors()['Bed']);lo=bed[0][0]-bed[1][0]
samples={str(y):[(round(lo+i,2),W.trace_down(lo+i,y)) for i in range(0,37,2)] for y in (-173,-206)}
placement=W.load_placement();lay=placement['lay'];rig=placement['rig']
adapter=W.UeAdapter({'lying':unreal.load_asset(W.WAKE+'/AS_FoA_Wake_Lying')})
pose=adapter.pose_at('lying',0)
feet={b:W.comp_to_world(adapter.wget(pose,b)[0],lay['loc'],lay['yaw'],rig) for b in ('foot_l','ball_l','foot_r','ball_r')}
head_samples={str(y):[(x,W.trace_down(x,y)) for x in range(330,373,2)] for y in (-190,-200,-182)}
data=dict(bed=bed,surface_samples=samples,head_samples=head_samples,source_feet=feet)
Path('P:/FoA/Saved/WakeUp/'+os.environ.get('FOA_FOOT_PROBE','footboard_before.json')).write_text(json.dumps(data,indent=2))
print('FOOTBOARD',json.dumps(data))
