"""Read-only: the pelvis and head vertical bob baked into the walk clips the source ABP plays (walk sink diagnosis,
2026-11-10: PIE showed the pelvis swinging ~10 cm per step at 130 cm/s). Prints min/max/span of the component-space
pelvis and head z for each clip, root motion not extracted.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/walk_clip_bob.py FOA_AREAS=Characters"""
import json

import unreal

AL, AP = unreal.AnimationLibrary, unreal.AnimPoseExtensions
G = "/Game/FoA/Characters/Player/Anims/GASP/"
CLIPS = [G + "AS_GASP_M_Relaxed_Walk_Loop_F", G + "AS_GASP_M_Relaxed_Run_Loop_F", G + "AS_GASP_M_Relaxed_Stand_Idle_Loop",
         "/Game/FoA/Characters/Player/Anims/Loco/AS_FoA_Walk_Brisk"]  # the live loops (build_gasp_loco.py) and the old brisk walk
out = {}
o = unreal.AnimPoseEvaluationOptions()
o.set_editor_property("extract_root_motion", False)
for path in CLIPS:
    seq = unreal.load_asset(path)
    if not seq:
        out[path] = "missing"
        continue
    n = AL.get_num_frames(seq)
    zs = {"pelvis": [], "head": [], "foot_l": [], "foot_r": []}
    for f in range(n + 1):
        pose = AP.get_anim_pose_at_frame(seq, f, o)
        for b in zs:
            zs[b].append(AP.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation.z)
    root = AL.get_bone_pose_for_frame(seq, "root", n, False).translation if hasattr(AL, "get_bone_pose_for_frame") else None
    out[path.rsplit("/", 1)[1]] = dict(frames=n, length=round(seq.get_play_length(), 3),
                                       root_end=[round(c, 1) for c in (root.x, root.y, root.z)] if root else None,
                                       **{b: dict(min=round(min(v), 2), max=round(max(v), 2), span=round(max(v) - min(v), 2)) for b, v in zs.items()})
for k, v in out.items():  # one line each: ue_remote cuts long log lines
    print("WALK_CLIP_BOB", k, json.dumps(v))
