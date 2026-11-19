"""Locomotion assets for BP_FoAPlayer: foot sync markers on the in-place UAL cycles + walk and jog 1D blend spaces.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_locomotion.py
Sample speeds are the clips' measured natural paces (planted-foot travel): UAL walk ~100 cm/s, UAL jog ~337 cm/s.
The template MF_ walk/jog are 300/600 cm/s root-motion cycles: too brisk for a slow bedroom walk, so not used here."""
import unreal

P = "/Game/FoA/Characters/Player"
UAL = P + "/Anims/UAL"
EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
AP = unreal.AnimPoseExtensions
SKEL = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
IDLE = unreal.load_asset("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle")
WALK = unreal.load_asset(UAL + "/UAL_Walk_Loop")
JOG = unreal.load_asset(UAL + "/UAL_Jog_Fwd_Loop")
SPEED = {"walk": 100.0, "jog": 337.0}


def add_foot_markers(seq):
    """L/R markers at each heel strike (foot farthest forward, +Y), so blended cycles keep their feet in phase."""
    AL.remove_all_animation_sync_markers(seq)
    if "FootSync" not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, "FootSync")
    n = AL.get_num_frames(seq)
    opts = unreal.AnimPoseEvaluationOptions()
    poses = [AP.get_anim_pose_at_frame(seq, f, opts) for f in range(n)]
    for marker, bone in (("L", "foot_l"), ("R", "foot_r")):
        ys = [AP.get_bone_pose(p, bone, unreal.AnimPoseSpaces.WORLD).translation.y for p in poses]
        f = max(range(n), key=lambda i: ys[i])
        AL.add_animation_sync_marker(seq, marker, AL.get_time_at_frame(seq, f), "FootSync")
    print(seq.get_name(), "markers", [(str(m.marker_name), round(m.time, 2)) for m in AL.get_animation_sync_markers(seq)])
    EAL.save_loaded_asset(seq, False)


def blend_space(name, lo, hi, grid, samples):
    path = f"{P}/Anims/{name}"
    bs = unreal.load_asset(path)
    if not bs:
        f = unreal.BlendSpaceFactory1D()
        f.set_editor_property("target_skeleton", SKEL)
        bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, P + "/Anims", unreal.BlendSpace1D, f)
    params = list(bs.get_editor_property("blend_parameters"))
    params[0].set_editor_property("display_name", "Speed")
    params[0].set_editor_property("min", lo)
    params[0].set_editor_property("max", hi)
    params[0].set_editor_property("grid_num", grid)
    bs.set_editor_property("blend_parameters", params)
    interp = list(bs.get_editor_property("interpolation_param"))
    interp[0].set_editor_property("interpolation_time", 0.25)  # smooth speed changes: no snapping between gaits
    bs.set_editor_property("interpolation_param", interp)
    out = []
    for anim, speed in samples:
        s = unreal.BlendSample()
        s.set_editor_property("animation", anim)
        s.set_editor_property("sample_value", unreal.Vector(speed, 0.0, 0.0))
        s.set_editor_property("rate_scale", 1.0)
        out.append(s)
    bs.set_editor_property("sample_data", out)
    # Past the last sample, speed the cycle up instead of sliding the feet.
    bs.set_editor_property("axis_to_scale_animation", unreal.BlendSpaceAxis.BSA_X)
    EAL.save_loaded_asset(bs, False)
    got = [(s.get_editor_property("animation").get_name(), s.get_editor_property("sample_value").x)
           for s in bs.get_editor_property("sample_data")]
    print(name, "axis", lo, hi, "samples", got)


ed = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
for a in (WALK, JOG):
    ed.close_all_editors_for_asset(a)
    add_foot_markers(a)
blend_space("BS_FoA_Walk", 0.0, 150.0, 3, [(IDLE, 0.0), (WALK, SPEED["walk"])])
blend_space("BS_FoA_Jog", 100.0, 340.0, 4, [(WALK, SPEED["walk"]), (JOG, SPEED["jog"])])
