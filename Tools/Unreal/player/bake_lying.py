"""Anim lane, wake-up: bakes AS_FoA_Lie_Breathe, a lying-on-the-back breathing loop on the Mannequin skeleton.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/bake_lying.py FOA_AREAS=/Game/FoA/Characters/Player [FOA_STEP=api|bake]
Source pose: UAL_LayToIdle frame 0 (on his back). Its neck and head are cranked back (a retarget artifact), so neck_01,
neck_02 and head take their reference-pose local rotations (neck in line with the spine, head resting on the pillow),
plus FOA_CHIN deg of chin-to-chest. Breathing: a slow chest rise on spine_03/04 (extension about each bone's own lateral
axis, measured from the clavicles in this pose) and the clavicles lifting with it, FOA_PERIOD s per breath, looping.
api: prints the AnimDataController methods this 5.8 build exposes (first run only)."""
import math
import os

import unreal

P = "/Game/FoA/Characters/Player"
SRC = P + "/Anims/UAL/UAL_LayToIdle"
OUT = P + "/Anims/Wake/AS_FoA_Lie_Breathe"
FPS = 30
PERIOD = float(os.environ.get("FOA_PERIOD", "4.0"))
CHIN = float(os.environ.get("FOA_CHIN", "10.0"))
BREATH = {"spine_03": 1.2, "spine_04": 1.6, "clavicle_l": 1.0, "clavicle_r": 1.0}  # degrees at the top of a breath
EAL, AP = unreal.EditorAssetLibrary, unreal.AnimPoseExtensions
LOCAL, CS = unreal.AnimPoseSpaces.LOCAL, unreal.AnimPoseSpaces.WORLD


def controller(seq):
    for get in (lambda s: s.get_editor_property("controller"), lambda s: s.controller, lambda s: s.get_controller()):
        try:
            c = get(seq)
            if c:
                return c
        except Exception:
            pass
    raise RuntimeError("no AnimDataController on " + seq.get_name())


def axis_angle(axis, deg):
    return unreal.MathLibrary.rotator_from_axis_and_angle(axis.normal(), deg).quaternion()


def mul(a, b):
    """Quaternion product a*b (apply b, then a)."""
    return unreal.MathLibrary.multiply_quat_quat(a, b) if hasattr(unreal.MathLibrary, "multiply_quat_quat") else a * b


def step_api():
    seq = unreal.load_asset(SRC)
    c = controller(seq)
    print("API", type(c).__name__, [m for m in dir(c) if not m.startswith("_") and m.islower()][:80])


def step_bake():
    src = unreal.load_asset(SRC)
    if not EAL.does_asset_exist(OUT):
        assert EAL.duplicate_asset(SRC, OUT), "duplicate"
    seq = unreal.load_asset(OUT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("extract_root_motion", False)
    pose = AP.get_anim_pose_at_frame(src, 0, o)
    ref = AP.get_reference_pose(src.get_editor_property("skeleton"))
    bones = [str(b) for b in AP.get_bone_names(pose)]
    local = {b: AP.get_bone_pose(pose, b, LOCAL) for b in bones}
    for b in ("neck_01", "neck_02", "head"):  # neutral neck: the reference pose's own local rotation
        t = local[b]
        local[b] = unreal.Transform(t.translation, AP.get_bone_pose(ref, b, LOCAL).rotation.rotator(), t.scale3d)
    # the lateral axis (his left-right) in component space, from the clavicles of this lying pose
    lat = AP.get_bone_pose(pose, "clavicle_l", CS).translation - AP.get_bone_pose(pose, "clavicle_r", CS).translation

    def in_bone(bone, v):
        return AP.get_bone_pose(pose, bone, CS).rotation.unrotate_vector(v)

    chin = axis_angle(in_bone("neck_01", lat), CHIN)
    t = local["neck_01"]
    local["neck_01"] = unreal.Transform(t.translation, mul(t.rotation, chin).rotator(), t.scale3d)
    n = int(round(PERIOD * FPS))
    keys = {b: ([], [], []) for b in bones}
    for f in range(n + 1):
        s = 0.5 - 0.5 * math.cos(2.0 * math.pi * f / n)  # 0..1..0: inhale, exhale, loops cleanly
        for b in bones:
            t = local[b]
            q = t.rotation
            if b in BREATH:
                sign = -1.0 if b == "clavicle_r" else 1.0
                q = mul(q, axis_angle(in_bone(b, lat), sign * BREATH[b] * s))
            keys[b][0].append(t.translation)
            keys[b][1].append(q)
            keys[b][2].append(t.scale3d)
    c = controller(seq)
    c.open_bracket(unreal.Text("FoA lying breath"), True) if hasattr(c, "open_bracket") else None
    try:
        fr = unreal.FrameRate()  # 5.8 struct constructors take no arguments
        fr.set_editor_property("numerator", FPS)
        fr.set_editor_property("denominator", 1)
        c.set_frame_rate(fr, True)
        fn = unreal.FrameNumber()
        fn.set_editor_property("value", n)
        c.set_number_of_frames(fn, True)
        for b in bones:
            c.set_bone_track_keys(b, keys[b][0], keys[b][1], keys[b][2], True)
    finally:
        c.close_bracket(True) if hasattr(c, "close_bracket") else None
    for tr in list(unreal.AnimationLibrary.get_animation_notify_track_names(seq)):
        unreal.AnimationLibrary.remove_animation_notify_events_by_track(seq, tr)
    seq.set_editor_property("enable_root_motion", False)
    EAL.save_loaded_asset(seq, False)
    print("baked", OUT, n, "frames", round(seq.get_play_length(), 2), "s, bones", len(bones))


{"api": step_api, "bake": step_bake}[os.environ.get("FOA_STEP", "bake")]()
