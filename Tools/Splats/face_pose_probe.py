"""Read-only reference head calibration; prints only transforms used by the face-front mask."""
import unreal
import json
from pathlib import Path

mesh = unreal.load_asset('/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/SKM_MHC_Protagonist_FaceMesh')
pose = unreal.AnimPoseExtensions.get_reference_pose(mesh.get_editor_property('skeleton'))
names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)]
rows = {}
for n in names:
    if n in ('head', 'neck_02') or ('facial_' in n.lower() and any(x in n.lower() for x in ('nose', 'forehead', 'chin', 'eye', 'facialroot'))):
        t = unreal.AnimPoseExtensions.get_bone_pose(pose, n, unreal.AnimPoseSpaces.WORLD)
        rows[n] = dict(pos=[t.translation.x, t.translation.y, t.translation.z],
                       quat=[t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w])
out = Path('P:/FoA/Saved/PPShots/face_pose_reference.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(rows, indent=1), encoding='utf-8')
print('FACE_POSE wrote', len(rows), 'landmarks', str(out))
