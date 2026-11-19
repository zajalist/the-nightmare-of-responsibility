"""Read-only: in the Teen's retargeted clips (TMP_rig), how much forearm roll sits on lowerarm vs hand? Swing-twist
about each bone's along-bone axis (local Y on the Teen), relative to the reference pose, max over the clip.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/twist_source.py"""
import json
import math

import unreal

AP = unreal.AnimPoseExtensions
CLIPS = json.load(open("P:/FoA/Saved/RigShots/audit/clip_retarget.json"))
opts = unreal.AnimPoseEvaluationOptions()


def twist(q, axis):
    """Signed twist angle (deg) of quaternion q about unit axis (x, y, z)."""
    p = q.x * axis[0] + q.y * axis[1] + q.z * axis[2]
    return math.degrees(2 * math.atan2(p, q.w))


def rel(q0, q1):  # q0^-1 * q1
    x0, y0, z0, w0 = -q0.x, -q0.y, -q0.z, q0.w
    return unreal.Quat(w0 * q1.x + x0 * q1.w + y0 * q1.z - z0 * q1.y, w0 * q1.y - x0 * q1.z + y0 * q1.w + z0 * q1.x,
                       w0 * q1.z + x0 * q1.y - y0 * q1.x + z0 * q1.w, w0 * q1.w - x0 * q1.x - y0 * q1.y - z0 * q1.z)


out = {}
for key, c in CLIPS.items():
    a = unreal.load_asset(c["target"].split(".")[0])
    ref = AP.get_reference_pose(a.get_editor_property("skeleton"))
    rows = {}
    for i in range(12):
        pose = AP.get_anim_pose_at_time(a, a.get_play_length() * i / 11, opts)
        for b in ("lowerarm_r", "hand_r", "lowerarm_l", "hand_l"):
            q = rel(AP.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL).rotation, AP.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL).rotation)
            t = twist(q, (0, 1, 0))
            lo, hi = rows.get(b, (999, -999))
            rows[b] = (min(lo, round(t, 1)), max(hi, round(t, 1)))
    out[key] = rows
json.dump(out, open("P:/FoA/Saved/RigShots/audit/twist_source.json", "w"), indent=1)
print("TWIST_SOURCE", json.dumps(out))
