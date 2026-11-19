"""Dump the Teen skeleton's reference pose (local and component transforms per bone) to Saved/AnimShots/teen_ref_pose.json,
so pose solvers (bake_phone_grip.py) can iterate offline. Read-only.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/export_teen_ref.py FOA_AREAS=Characters"""
import json
from pathlib import Path

import unreal

AP = unreal.AnimPoseExtensions


def xf(t):
    return [[t.translation.x, t.translation.y, t.translation.z], [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
            [t.scale3d.x, t.scale3d.y, t.scale3d.z]]


skel = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body').get_editor_property('skeleton')
ref = AP.get_reference_pose(skel)
names = [str(b) for b in AP.get_bone_names(ref)]
out = dict(names=names, local={b: xf(AP.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL)) for b in names},
           world={b: xf(AP.get_bone_pose(ref, b, unreal.AnimPoseSpaces.WORLD)) for b in names})
Path('P:/FoA/Saved/AnimShots/teen_ref_pose.json').write_text(json.dumps(out))
print('TEEN_REF', len(names))
