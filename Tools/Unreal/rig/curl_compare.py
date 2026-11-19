"""Read-only: per finger phalanx, how far it is rotated relative to the HAND (component space, vs its own reference
pose), in the Manny source clip and in the Teen retarget of it. Equal numbers = the curl reaches the Teen intact.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/curl_compare.py [FOA_CLIPS=phone,tool] [FOA_T=0.5]"""
import json
import math
import os

import unreal

AP = unreal.AnimPoseExtensions
CLIPS = json.load(open("P:/FoA/Saved/RigShots/audit/clip_retarget.json"))
WANT = os.environ.get("FOA_CLIPS", "phone,tool,key").split(",")
T = float(os.environ.get("FOA_T", "0.5"))
opts = unreal.AnimPoseEvaluationOptions()


def qmul(a, b):
    return unreal.Quat(a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y, a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
                       a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w, a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z)


def inv(a):
    return unreal.Quat(-a.x, -a.y, -a.z, a.w)


def ang(a, b):
    d = abs(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w)
    return round(math.degrees(2 * math.acos(min(1.0, d))), 1)


def curls(asset, t):
    ref = AP.get_reference_pose(asset.get_editor_property("skeleton"))
    pose = AP.get_anim_pose_at_time(asset, t * asset.get_play_length(), opts)
    W = unreal.AnimPoseSpaces.WORLD
    out = {}
    for s in "lr":
        h0, h1 = AP.get_bone_pose(ref, f"hand_{s}", W).rotation, AP.get_bone_pose(pose, f"hand_{s}", W).rotation
        for f in ("thumb", "index", "middle", "ring", "pinky"):
            for j in (1, 2, 3):
                b = f"{f}_0{j}_{s}"
                r0 = qmul(inv(h0), AP.get_bone_pose(ref, b, W).rotation)
                r1 = qmul(inv(h1), AP.get_bone_pose(pose, b, W).rotation)
                out[b] = ang(r0, r1)
    return out


report = {}
for key in WANT:
    c = CLIPS[key]
    m = curls(unreal.load_asset(c["source"].split(".")[0]), T)
    t = curls(unreal.load_asset(c["target"].split(".")[0]), T)
    report[key] = {b: [m[b], t[b]] for b in m}
    worst = sorted(report[key].items(), key=lambda kv: -abs(kv[1][0] - kv[1][1]))[:6]
    print("CURL", key, "manny/teen deg (rel. to hand) worst:", worst)
json.dump(report, open("P:/FoA/Saved/RigShots/audit/curl_compare.json", "w"), indent=1)
