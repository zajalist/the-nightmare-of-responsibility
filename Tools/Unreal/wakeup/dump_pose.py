"""Read-only: component-space bone positions of clips at given times -> Saved/WakeUp/pose_<name>.json (for stick plots).
  FOA_AREAS=Cinematics python Tools/Unreal/ue_remote.py Tools/Unreal/wakeup/dump_pose.py FOA_CLIPS=/Game/...@t,/Game/...@t"""
import json
import os
import unreal
AP = unreal.AnimPoseExtensions
W = unreal.AnimPoseSpaces.WORLD
o = unreal.AnimPoseEvaluationOptions()
o.set_editor_property('extract_root_motion', False)
for spec in os.environ['FOA_CLIPS'].split(','):
    path, t = spec.split('@')
    seq = unreal.load_asset(path)
    pose = AP.get_anim_pose_at_time(seq, float(t), o)
    names = [str(b) for b in AP.get_bone_names(pose)]
    out = {}
    for b in names:
        x = AP.get_bone_pose(pose, b, W)
        out[b] = [x.translation.x, x.translation.y, x.translation.z]
    name = path.split('/')[-1] + '_' + t.replace('.', 'p')
    open(f'P:/FoA/Saved/WakeUp/pose_{name}.json', 'w').write(json.dumps(out))
    print('dumped', name, len(out))
