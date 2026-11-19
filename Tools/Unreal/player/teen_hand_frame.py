"""Read Teen hand-local joint positions for grip calibration."""
import json
from pathlib import Path
import unreal
P='/Game/FoA/Characters/Player'
body=unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
pose=unreal.AnimPoseExtensions.get_reference_pose(body.get_editor_property('skeleton'))
W=unreal.AnimPoseSpaces.WORLD
hand=unreal.AnimPoseExtensions.get_bone_pose(pose,'hand_r',W)
rows={}
for name in ('hand_r','lowerarm_r','index_01_r','middle_01_r','pinky_01_r','thumb_01_r','thumb_02_r','thumb_03_r'):
    t=unreal.AnimPoseExtensions.get_bone_pose(pose,name,W)
    local=unreal.MathLibrary.inverse_transform_location(hand,t.translation)
    rows[name]=dict(world=list(t.translation.to_tuple()),local=list(local.to_tuple()))
Path('P:/FoA/Saved/AnimShots/teen_hand_frame.json').write_text(json.dumps(dict(hand=hand.export_text(),bones=rows),indent=1))
print('Teen hand frame saved')
