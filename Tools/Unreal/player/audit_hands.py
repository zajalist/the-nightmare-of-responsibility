"""Hand audit for the retargeted UAL clips: finger chain mapping, per-joint curl fidelity vs the source clip,
sideways (abduction) drift, and forearm roll (the candy-wrap risk for Manny's undriven twist bones).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/audit_hands.py [FOA_CLIPS=PickUp_Table,Interact]"""
import math
import os

import unreal

P = "/Game/FoA/Characters/Player"
AP = unreal.AnimPoseExtensions
W = unreal.AnimPoseSpaces.WORLD
SRC = {"UAL1": (P + "/Source/UAL1/AL_StandardRig_", "_end"), "UAL2": (P + "/Source/UAL2/UAL2_Standard/SkeletalMeshes/UAL2_Standard", "_leaf")}
PACK2 = {"LayToIdle", "Farm_Harvest", "Farm_PlantSeed", "Chest_Open", "Hit_Knockback", "Idle_No_Loop", "Idle_FoldArms_Loop", "Consume", "Yes"}
FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def sub(a, b):
    return (a.x - b.x, a.y - b.y, a.z - b.z)


def ang(u, v):
    nu, nv = math.sqrt(sum(c * c for c in u)), math.sqrt(sum(c * c for c in v))
    if nu < 1e-6 or nv < 1e-6:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(u, v)) / (nu * nv)))))


def curls(pose, side):
    """Flexion at the 2 inner joints of each finger + angle of the proximal phalanx to the hand bone axis."""
    out = {}
    hand = AP.get_bone_pose(pose, f"hand_{side}", W).translation
    for f in FINGERS:
        pts = [AP.get_bone_pose(pose, f"{f}_0{i}_{side}", W).translation for i in (1, 2, 3)]
        out[f] = (ang(sub(pts[1], pts[0]), sub(pts[2], pts[1])), ang(sub(pts[0], hand), sub(pts[1], pts[0])))
    return out


def roll(pose, side):
    """Hand twist about the forearm axis relative to the ref pose would need the ref; report the angle between the
    hand's local X/Z plane and the forearm instead via the palm normal (index->pinky across the knuckles)."""
    k1 = AP.get_bone_pose(pose, f"index_01_{side}", W).translation
    k2 = AP.get_bone_pose(pose, f"pinky_01_{side}", W).translation
    el = AP.get_bone_pose(pose, f"lowerarm_{side}", W).translation
    wr = AP.get_bone_pose(pose, f"hand_{side}", W).translation
    return ang(sub(k2, k1), sub(wr, el))


for tag in ("IK_FoA_Mannequin", "IK_UAL1", "IK_UAL2"):
    c = unreal.IKRigController.get_controller(unreal.load_asset(f"{P}/Retarget/{tag}"))
    fing = [(str(ch.chain_name), str(c.get_retarget_chain_start_bone(ch.chain_name)), str(c.get_retarget_chain_end_bone(ch.chain_name)))
            for ch in c.get_retarget_chains() if any(k in str(ch.chain_name) for k in ("Thumb", "Index", "Middle", "Ring", "Pinky", "Arm"))
            and str(ch.chain_name).startswith("Left")]
    print(tag, fing)
for pack in ("UAL1", "UAL2"):
    c = unreal.IKRetargeterController.get_controller(unreal.load_asset(f"{P}/Retarget/RTG_{pack}_to_Mannequin"))
    print(pack, "FK map:", [(t, str(c.get_source_chain(t, "FK Chains"))) for t in ("LeftThumb", "LeftIndex", "LeftIndexMetacarpal", "LeftPinky", "LeftArm")])

clips = [c for c in os.environ.get("FOA_CLIPS", "PickUp_Table,Interact,Farm_Harvest,Fixing_Kneeling,Idle_Loop,Walk_Loop").split(",") if c]
for clip in clips:
    pack = "UAL2" if clip in PACK2 else "UAL1"
    src = unreal.load_asset(SRC[pack][0] + clip)
    dst = unreal.load_asset(f"{P}/Anims/UAL/UAL_{clip}")
    n = unreal.AnimationLibrary.get_num_frames(dst)
    worst = {}
    rolls = []
    opts = unreal.AnimPoseEvaluationOptions()
    for fr in range(0, n + 1, max(1, n // 12)):
        ps, pd = AP.get_anim_pose_at_frame(src, fr, opts), AP.get_anim_pose_at_frame(dst, fr, opts)
        for side in ("l", "r"):
            cs, cd = curls(ps, side), curls(pd, side)
            for f in FINGERS:
                d = max(abs(cs[f][0] - cd[f][0]), abs(cs[f][1] - cd[f][1]))
                key = f"{f}_{side}"
                if d > worst.get(key, (0, 0, 0, 0))[0]:
                    worst[key] = (d, fr, cs[f], cd[f])
            rolls.append((abs(roll(ps, side) - roll(pd, side)), side, fr))
    bad = {k: v for k, v in worst.items() if v[0] > 12}
    print(f"\n{clip}: worst finger curl/deviation mismatch (deg) "
          + ", ".join(f"{k}={v[0]:.0f}@f{v[1]}" for k, v in sorted(worst.items())))
    for k, v in bad.items():
        print(f"   {k}: src (curl {v[2][0]:.0f}, base {v[2][1]:.0f}) vs retarget (curl {v[3][0]:.0f}, base {v[3][1]:.0f})")
    print(f"   palm/forearm angle drift max {max(rolls)[0]:.0f} deg ({max(rolls)[1]} f{max(rolls)[2]})")
