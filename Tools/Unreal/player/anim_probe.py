"""Anim lane read-only probe (writes only Saved/AnimShots/probe.txt): pawn setup, camera boom, grooms, and the true
ground speed of every locomotion clip (root motion, else the planted foot's backward speed).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/anim_probe.py FOA_AREAS=/Game/FoA/Characters/Player"""
import statistics

import unreal

OUT = "P:/FoA/Saved/AnimShots/probe.txt"
L = []
say = lambda *a: L.append(" ".join(str(x) for x in a))  # noqa: E731
EAL, AL, AP = unreal.EditorAssetLibrary, unreal.AnimationLibrary, unreal.AnimPoseExtensions
CS = unreal.AnimPoseSpaces.WORLD  # component space for a sequence pose


def clip_speed(path):
    seq = unreal.load_asset(path)
    if not seq:
        return say("missing", path)
    n, length = AL.get_num_frames(seq), seq.get_play_length()
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("extract_root_motion", False)
    poses = [AP.get_anim_pose_at_frame(seq, f, o) for f in range(n + 1)]
    root = [AP.get_bone_pose(p, "root", CS).translation for p in poses]
    rm = (root[-1] - root[0])
    rms = (rm.x ** 2 + rm.y ** 2) ** 0.5 / length
    feet = []
    for bone in ("ball_l", "ball_r"):
        tr = [AP.get_bone_pose(p, bone, CS).translation - r for p, r in zip(poses, root)]
        zmin = min(v.z for v in tr)
        dt = length / n
        for a, b in zip(tr, tr[1:]):
            if a.z < zmin + 2.5 and b.z < zmin + 2.5:
                feet.append(((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5 / dt)
    fs = statistics.median(feet) if feet else 0
    say(f"clip {path.split('/')[-1]:32s} len={length:5.2f}s frames={n} rootmotion={seq.get_editor_property('enable_root_motion')} "
        f"root_speed={rms:6.1f} planted_foot_speed={fs:6.1f} cm/s")


bp = unreal.load_asset("/Game/FoA/Characters/Player/BP_FoAPlayer")
cdo = unreal.get_default_object(bp.generated_class())
m = cdo.get_editor_property("mesh")
sk = m.get_editor_property("skeletal_mesh_asset")
say("mesh:", sk.get_path_name() if sk else None)
say("anim:", m.get_editor_property("anim_class"))
skel = sk.get_editor_property("skeleton")
say("skeleton:", skel.get_path_name())
say("compatible:", [s.get_path_name() for s in skel.get_editor_property("compatible_skeletons")])
cm = cdo.get_editor_property("character_movement")
for k in ("max_walk_speed", "max_acceleration", "braking_deceleration_walking", "braking_friction_factor", "ground_friction",
          "use_separate_braking_friction", "braking_friction", "rotation_rate", "orient_rotation_to_movement",
          "use_controller_desired_rotation"):
    say(" cmc", k, cm.get_editor_property(k))
say("use_controller_rotation_yaw", cdo.get_editor_property("use_controller_rotation_yaw"))
for n in ("WalkSpeed", "JogSpeed", "LookAtRadius", "LookAtTag", "bStartCinematic"):
    say(n, cdo.get_editor_property(n))
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = lib.get_data(h)
    o = lib.get_object_for_blueprint(d, bp)
    name = str(lib.get_variable_name(d))
    if name in ("CameraBoom", "FollowCamera"):
        for k in ("target_arm_length", "socket_offset", "target_offset", "relative_location", "enable_camera_lag",
                  "camera_lag_speed", "enable_camera_rotation_lag", "do_collision_test", "probe_size", "field_of_view"):
            try:
                say(" ", name, k, o.get_editor_property(k))
            except Exception:
                pass
    if isinstance(o, unreal.GroomComponent):
        say(" groom", name, o.get_editor_property("groom_asset"), o.get_editor_property("binding_asset"),
            "attach:", o.get_attach_parent().get_name() if o.get_attach_parent() else None)
    if isinstance(o, unreal.SkeletalMeshComponent):
        a = o.get_editor_property("skeletal_mesh_asset")
        say(" skm", name, a.get_path_name() if a else None, "visible", o.get_editor_property("visible"))
for p in ("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle",
          "/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd",
          "/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Left",
          "/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd",
          "/Game/FoA/Characters/Player/Anims/UAL/UAL_Walk_Loop",
          "/Game/FoA/Characters/Player/Anims/UAL/UAL_Walk_Formal_Loop",
          "/Game/FoA/Characters/Player/Anims/UAL/UAL_Jog_Fwd_Loop",
          "/Game/FoA/Characters/Player/Anims/UAL/UAL_LayToIdle"):
    clip_speed(p)
for bs in ("/Game/FoA/Characters/Player/Anims/BS_FoA_Walk", "/Game/FoA/Characters/Player/Anims/BS_FoA_Jog",
           "/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run"):
    b = unreal.load_asset(bs)
    say("bs", bs.split("/")[-1], b.get_class().get_name(),
        [(s.get_editor_property("animation").get_name() if s.get_editor_property("animation") else None,
          round(s.get_editor_property("sample_value").x, 1), round(s.get_editor_property("sample_value").y, 1))
         for s in b.get_editor_property("sample_data")])
open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("probe ->", OUT, len(L), "lines")
