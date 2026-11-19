"""Read-only: component-space positions of a few bones per frame of a clip -> Saved/AnimShots/clip_motion_<name>.json.
  FOA_CLIP=/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach python Tools/Unreal/ue_remote.py Tools/Unreal/wakeup/clip_motion.py"""
import json
import os

import unreal

AP = unreal.AnimPoseExtensions
clip = unreal.load_asset(os.environ['FOA_CLIP'])
bones = os.environ.get('FOA_BONES', 'pelvis,spine_03,head,hand_r,hand_l,foot_l,foot_r').split(',')
opts = unreal.AnimPoseEvaluationOptions()
n = clip.get_editor_property('number_of_sampled_frames') if hasattr(clip, 'number_of_sampled_frames') else None
length = clip.get_play_length()
step = int(os.environ.get('FOA_STEP', '1'))
rows = []
f = 0
while f / 30.0 <= length + 1e-4:
    pose = AP.get_anim_pose_at_time(clip, f / 30.0, opts)
    rows.append([f] + [[round(v, 2) for v in AP.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation.to_tuple()] for b in bones])
    f += step
out = 'P:/FoA/Saved/AnimShots/clip_motion_' + clip.get_name() + '.json'
with open(out, 'w') as fh:
    json.dump(dict(clip=clip.get_path_name(), length=length, bones=bones, rows=rows), fh)
print('CLIP_MOTION', out, length, len(rows))
