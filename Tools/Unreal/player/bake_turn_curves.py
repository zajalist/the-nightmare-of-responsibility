"""Anim lane: a 'TurnYaw' float curve on the GASP turn-in-place clips: the root's cumulative yaw (deg, unwrapped) from 0.
ABP_FoAPlayer reads it (un-blended by the TurnYawWeight curve) while a turn plays and moves RootYawOffset by its change, so the body turns exactly as far as
the feet step (root motion itself is discarded: RootMotionMode IgnoreRootMotion).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/bake_turn_curves.py"""
import unreal
AL, AP, EAL = unreal.AnimationLibrary, unreal.AnimPoseExtensions, unreal.EditorAssetLibrary
CS = unreal.AnimPoseSpaces.WORLD
G = '/Game/FoA/Characters/Player/Anims/GASP/AS_GASP_M_Relaxed_Stand_Turn_'
for name in ('090_L', '090_R', '180_L', '180_R'):
    seq = unreal.load_asset(G + name)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    n, length = AL.get_num_frames(seq), seq.get_play_length()
    o = unreal.AnimPoseEvaluationOptions(); o.set_editor_property('extract_root_motion', False)
    yaws = [AP.get_bone_pose(AP.get_anim_pose_at_frame(seq, f, o), 'root', CS).rotation.rotator().yaw for f in range(n + 1)]
    acc, vals = 0.0, [0.0]
    for a, b in zip(yaws, yaws[1:]):
        acc += (b - a + 540.0) % 360.0 - 180.0
        vals.append(acc)
    if AL.does_curve_exist(seq, 'TurnYaw', unreal.RawCurveTrackTypes.RCT_FLOAT):
        AL.remove_curve(seq, 'TurnYaw', False)
    AL.add_curve(seq, 'TurnYaw', unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, 'TurnYaw', [length * f / n for f in range(n + 1)], vals)
    # TurnYawWeight = 1 throughout: its evaluated value is the turn clips' blend weight, so the ABP can un-blend TurnYaw
    # (TurnYaw / weight) and a blend-out never hands the consumed yaw back
    if AL.does_curve_exist(seq, 'TurnYawWeight', unreal.RawCurveTrackTypes.RCT_FLOAT):
        AL.remove_curve(seq, 'TurnYawWeight', False)
    AL.add_curve(seq, 'TurnYawWeight', unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, 'TurnYawWeight', [0.0, length], [1.0, 1.0])
    EAL.save_loaded_asset(seq, False)
    print(name, 'TurnYaw 0 ->', round(acc, 1), 'over', round(length, 2), 's; half at', round(length * next(i for i, v in enumerate(vals) if abs(v) >= abs(acc) / 2) / n, 2), 's')
