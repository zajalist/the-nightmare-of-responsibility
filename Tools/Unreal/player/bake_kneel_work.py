"""Anim lane: bakes AS_FoA_Kneel_Work, UAL_Fixing_Kneeling with the torso brought upright for work at a door.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/bake_kneel_work.py [FOA_LEAN=26] [FOA_STEP=bake|montage]
The UAL clip fixes something on the floor: kneeling 50 cm from the door its head lands on the door handle. Every frame
gets FOA_LEAN degrees of spine extension (spread over spine_01..05, about the body's own lateral axis from the clavicles)
weighted by how deep the kneel is (pelvis height), so the stand-up blends back to the source. The neck takes back a
third of it so he still looks down at his hands.
montage: points AM_FoA_KneelScrewdriver's segments at the new clip; times and notifies are unchanged, so BP_Door's
cached contact and release times stay valid."""
import os

import unreal

P = "/Game/FoA/Characters/Player"
SRC = P + "/Anims/UAL/UAL_Fixing_Kneeling"
OUT = P + "/Anims/Hands/AS_FoA_Kneel_Work"
MONTAGE = P + "/Montages/AM_FoA_KneelScrewdriver"
LEAN = float(os.environ.get("FOA_LEAN", "26"))
SPINE = {"spine_01": 0.15, "spine_02": 0.2, "spine_03": 0.25, "spine_04": 0.2, "spine_05": 0.2}
NECK = {"neck_01": -0.2, "neck_02": -0.13}
EAL, AP, AL = unreal.EditorAssetLibrary, unreal.AnimPoseExtensions, unreal.AnimationLibrary
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


def mul(a, b):
    return unreal.MathLibrary.multiply_quat_quat(a, b) if hasattr(unreal.MathLibrary, "multiply_quat_quat") else a * b


def axis_angle(axis, deg):
    return unreal.MathLibrary.rotator_from_axis_and_angle(axis.normal(), deg).quaternion()


def step_bake():
    src = unreal.load_asset(SRC)
    if not EAL.does_asset_exist(OUT):
        assert EAL.duplicate_asset(SRC, OUT), "duplicate"
    seq = unreal.load_asset(OUT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("extract_root_motion", False)
    n = AL.get_num_frames(src)
    poses = [AP.get_anim_pose_at_frame(src, f, o) for f in range(n + 1)]
    bones = [str(b) for b in AP.get_bone_names(poses[0])]
    hips = [AP.get_bone_pose(p, "pelvis", CS).translation.z for p in poses]
    top, low = max(hips), min(hips)
    # Sign: the extension must take the head back over the pelvis (shrink the head's horizontal lead).
    p0 = poses[hips.index(low)]
    lat0 = AP.get_bone_pose(p0, "clavicle_l", CS).translation - AP.get_bone_pose(p0, "clavicle_r", CS).translation
    pivot = AP.get_bone_pose(p0, "spine_01", CS).translation
    head = AP.get_bone_pose(p0, "head", CS).translation
    pel = AP.get_bone_pose(p0, "pelvis", CS).translation

    def lead(v):
        d = v - pel
        return (d.x ** 2 + d.y ** 2) ** 0.5

    test = axis_angle(lat0, 10.0).rotate_vector(head - pivot) + pivot
    sign = 1.0 if lead(test) < lead(head) else -1.0
    keys = {b: ([], [], []) for b in bones}
    for p, z in zip(poses, hips):
        w = min(1.0, max(0.0, (top - z) / max(1.0, top - low)))
        w = w * w * (3 - 2 * w)
        lat = AP.get_bone_pose(p, "clavicle_l", CS).translation - AP.get_bone_pose(p, "clavicle_r", CS).translation
        for b in bones:
            t = AP.get_bone_pose(p, b, LOCAL)
            q = t.rotation
            share = SPINE.get(b, 0.0) + NECK.get(b, 0.0)
            if share:
                q = mul(q, axis_angle(AP.get_bone_pose(p, b, CS).rotation.unrotate_vector(lat), sign * LEAN * share * w))
            keys[b][0].append(t.translation)
            keys[b][1].append(q)
            keys[b][2].append(t.scale3d)
    c = controller(seq)
    for b in bones:
        c.set_bone_track_keys(b, keys[b][0], keys[b][1], keys[b][2], True)
    for tr in list(AL.get_animation_notify_track_names(seq)):
        AL.remove_animation_notify_events_by_track(seq, tr)
    EAL.save_loaded_asset(seq, False)
    print("baked", OUT, n, "frames, lean", LEAN, "sign", sign, "pelvis", round(top, 1), "->", round(low, 1))


def step_montage():
    m = unreal.load_asset(MONTAGE)
    seq = unreal.load_asset(OUT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(m)
    tracks = m.get_editor_property("slot_anim_tracks")
    t0 = tracks[0]
    at = t0.get_editor_property("anim_track")
    segs = list(at.get_editor_property("anim_segments"))
    for s in segs:
        assert s.get_editor_property("anim_reference").get_name() in ("UAL_Fixing_Kneeling", "AS_FoA_Kneel_Work")
        s.set_editor_property("anim_reference", seq)
    at.set_editor_property("anim_segments", segs)
    t0.set_editor_property("anim_track", at)
    m.set_editor_property("slot_anim_tracks", [t0])
    EAL.save_loaded_asset(m, False)
    print("montage", MONTAGE, "now plays", OUT, "length", round(m.get_play_length(), 3))


{"bake": step_bake, "montage": step_montage}[os.environ.get("FOA_STEP", "bake")]()
