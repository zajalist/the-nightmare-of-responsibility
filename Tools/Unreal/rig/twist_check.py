"""Read-only: do the Manny source clips animate the twist bones? Max local deviation from the reference pose of
lowerarm_twist_01_r/l and of hand_r about the forearm, over each clip.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/twist_check.py"""
import json

import unreal

AP = unreal.AnimPoseExtensions
CLIPS = json.load(open("P:/FoA/Saved/RigShots/audit/clip_retarget.json"))
out = {}
opts = unreal.AnimPoseEvaluationOptions()
for key, c in CLIPS.items():
    a = unreal.load_asset(c["source"].split(".")[0])
    ref = AP.get_reference_pose(a.get_editor_property("skeleton"))
    worst = {}
    n = 8
    for i in range(n):
        pose = AP.get_anim_pose_at_time(a, a.get_play_length() * i / (n - 1), opts)
        for b in ("lowerarm_twist_01_r", "lowerarm_twist_01_l", "lowerarm_twist_02_r", "upperarm_twist_01_r"):
            q0 = AP.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL).rotation
            q1 = AP.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL).rotation
            dot = min(1.0, abs(q0.x * q1.x + q0.y * q1.y + q0.z * q1.z + q0.w * q1.w))
            ang = 2 * __import__("math").degrees(__import__("math").acos(dot))
            worst[b] = max(worst.get(b, 0), round(ang, 1))
    out[key] = worst
json.dump(out, open("P:/FoA/Saved/RigShots/audit/twist_check.json", "w"), indent=1)
print("TWIST_CHECK", json.dumps(out))
