"""Rig lane: the hanger-use body clip and the two montages (editor Python, one short run per step).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/rig/hanger_use_anims.py FOA_STEP=bake|montages
bake      AS_FoA_HangerBed_Body: UAL_Fixing_Kneeling (kneel low, head down at the floor) with the effort put in: two tugs
          and the release, each a spine extension pulse with the pelvis rocking back, at the montage times of
          Tools/Rig/hanger_use_keys.py (tugs peak 2.5 / 2.95 s, the snag lets go at 3.35 s).
montages  AM_FoA_HangerBed (that clip) and AM_FoA_HangerDoor (AS_FoA_Kneel_Work, the upright door kneel), 5.2 s each, slot
          DefaultSlot, blends 0.25 / 0.35. Notifies: Gameplay (PlayMontageNotify 'KneelDown' at the settled kneel and
          'Grab' / 'WorkDone' at contact), InteractionContact (AN_FoA_InteractionContact at contact: the row commits there),
          Hanger (AN_FoA_HangerUse at 0.01 s, SpawnClass = BP_FoAHangerUse_Bed / _Door)."""
import json
import math
import os

import unreal

P = "/Game/FoA/Characters/Player"
SRC = P + "/Anims/UAL/UAL_Fixing_Kneeling"
BED = P + "/Anims/Hands/AS_FoA_HangerBed_Body"
DOOR = P + "/Anims/Hands/AS_FoA_Kneel_Work"
OUT = P + "/Montages"
HANGER = P + "/Hanger"
KEYS = json.load(open("P:/FoA/Saved/RigShots/hanger_use/keys.json"))
EAL, AP, AL = unreal.EditorAssetLibrary, unreal.AnimPoseExtensions, unreal.AnimationLibrary
LOCAL, CS = unreal.AnimPoseSpaces.LOCAL, unreal.AnimPoseSpaces.WORLD
SPINE = {"spine_01": 0.2, "spine_02": 0.25, "spine_03": 0.25, "spine_04": 0.15, "spine_05": 0.15}
PULSES = [(2.5, 0.16, 9.0, 3.0), (2.95, 0.16, 12.0, 4.0), (3.5, 0.3, 14.0, 5.0)]  # (peak s, half width s, deg, pelvis back cm)


def controller(seq):
    for get in (lambda s: s.get_editor_property("controller"), lambda s: s.controller, lambda s: s.get_controller()):
        try:
            c = get(seq)
            if c:
                return c
        except Exception:  # noqa: BLE001
            pass
    raise RuntimeError("no AnimDataController on " + seq.get_name())


def axis_angle(axis, deg):
    return unreal.MathLibrary.rotator_from_axis_and_angle(axis.normal(), deg).quaternion()


def effort(t):
    """Lean (deg) and pelvis back (cm) at clip time t: a smooth bump per pulse."""
    deg = back = 0.0
    for peak, half, d, b in PULSES:
        x = abs(t - peak) / half
        if x < 1:
            s = 0.5 * (1 + math.cos(math.pi * x))
            deg, back = max(deg, d * s), max(back, b * s)
    return deg, back


def step_bake():
    src = unreal.load_asset(SRC)
    if not EAL.does_asset_exist(BED):
        assert EAL.duplicate_asset(SRC, BED), "duplicate"
    seq = unreal.load_asset(BED)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("extract_root_motion", False)
    n = AL.get_num_frames(src)
    L = src.get_play_length()
    poses = [AP.get_anim_pose_at_frame(src, f, o) for f in range(n + 1)]
    bones = [str(b) for b in AP.get_bone_names(poses[0])]
    # sign: the extension takes the head back over the pelvis (as bake_kneel_work.py)
    p0 = poses[int(n * 2.5 / L)]
    lat0 = AP.get_bone_pose(p0, "clavicle_l", CS).translation - AP.get_bone_pose(p0, "clavicle_r", CS).translation
    pivot = AP.get_bone_pose(p0, "spine_01", CS).translation
    head = AP.get_bone_pose(p0, "head", CS).translation
    pel = AP.get_bone_pose(p0, "pelvis", CS).translation
    lead = lambda v: ((v - pel).x ** 2 + (v - pel).y ** 2) ** 0.5  # noqa: E731
    sign = 1.0 if lead(axis_angle(lat0, 10.0).rotate_vector(head - pivot) + pivot) < lead(head) else -1.0
    fwd = AP.get_bone_pose(p0, "head", CS).translation - pel
    fwd = unreal.Vector(fwd.x, fwd.y, 0).normal()
    keys = {b: ([], [], []) for b in bones}
    for f, p in enumerate(poses):
        deg, back = effort(f / n * L)
        lat = AP.get_bone_pose(p, "clavicle_l", CS).translation - AP.get_bone_pose(p, "clavicle_r", CS).translation
        for b in bones:
            t = AP.get_bone_pose(p, b, LOCAL)
            q, loc = t.rotation, t.translation
            if b in SPINE and deg:
                q = q * axis_angle(AP.get_bone_pose(p, b, CS).rotation.unrotate_vector(lat), sign * deg * SPINE[b])
            if b == "pelvis" and back:
                loc = loc - fwd * back  # root is the component frame on the Mannequin
            keys[b][0].append(loc)
            keys[b][1].append(q)
            keys[b][2].append(t.scale3d)
    c = controller(seq)
    for b in bones:
        c.set_bone_track_keys(b, keys[b][0], keys[b][1], keys[b][2], True)
    for tr in list(AL.get_animation_notify_track_names(seq)):
        AL.remove_animation_notify_events_by_track(seq, tr)
    EAL.save_loaded_asset(seq, False)
    print("BAKED", BED, n, "frames", round(L, 2), "s, sign", sign, "pulses", PULSES)


def build(name, clip, notifies, spawn):
    path = f"{OUT}/{name}"
    seq = unreal.load_asset(clip)
    m = unreal.load_asset(path)
    if m:
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(m)
        for tr in list(AL.get_animation_notify_track_names(m)):
            AL.remove_animation_notify_events_by_track(m, tr)  # this builder owns every track of its own montages
    else:
        f = unreal.AnimMontageFactory()
        f.set_editor_property("source_animation", seq)
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, OUT, unreal.AnimMontage, f)
    L = seq.get_play_length()
    s = unreal.AnimSegment()
    s.set_editor_property("anim_reference", seq)
    s.set_editor_property("anim_start_time", 0.0)
    s.set_editor_property("anim_end_time", L)
    s.set_editor_property("anim_play_rate", 1.0)
    s.set_editor_property("looping_count", 1)
    s.import_text("(StartPos=0)")
    t0 = m.get_editor_property("slot_anim_tracks")[0]
    at = t0.get_editor_property("anim_track")
    at.set_editor_property("anim_segments", [s])
    t0.set_editor_property("anim_track", at)
    t0.set_editor_property("slot_name", "DefaultSlot")
    m.set_editor_property("slot_anim_tracks", [t0])
    for prop, secs in (("blend_in", 0.25), ("blend_out", 0.35)):
        b = m.get_editor_property(prop)
        b.set_editor_property("blend_time", secs)
        m.set_editor_property(prop, b)
    EAL.save_loaded_asset(m, False)
    unreal.EditorLoadingAndSavingUtils.reload_packages([m.get_outermost()])
    m = unreal.load_asset(path)
    assert abs(m.get_play_length() - L) < 0.05, (name, m.get_play_length(), L)
    for tr in ("Gameplay", "InteractionContact", "Hanger"):
        if tr not in [str(x) for x in AL.get_animation_notify_track_names(m)]:
            AL.add_animation_notify_track(m, tr)
    contact_cls = unreal.load_class(None, "/Game/FoA/Gameplay/AN_FoA_InteractionContact.AN_FoA_InteractionContact_C")
    hanger_cls = unreal.load_class(None, HANGER + "/AN_FoA_HangerUse.AN_FoA_HangerUse_C")
    assert contact_cls and hanger_cls
    for nname, t in notifies:
        n = AL.add_animation_notify_event(m, "Gameplay", t, unreal.AnimNotify_PlayMontageNotify)
        n.set_editor_property("notify_name", nname)
    AL.add_animation_notify_event(m, "InteractionContact", notifies[-1][1], contact_cls)
    n = AL.add_animation_notify_event(m, "Hanger", 0.01, hanger_cls)
    n.set_editor_property("SpawnClass", unreal.load_class(None, f"{HANGER}/{spawn}.{spawn}_C"))
    EAL.save_loaded_asset(m, False)
    got = [(e.get_editor_property("notify").get_class().get_name(), round(AL.get_anim_notify_event_trigger_time(e), 3))
           for e in AL.get_animation_notify_events(m) if e.get_editor_property("notify")]
    print("MONTAGE", name, round(m.get_play_length(), 2), got)


def step_montages():
    build("AM_FoA_HangerBed", BED, [("KneelDown", 0.7), ("Grab", KEYS["bed"]["contact"])], "BP_FoAHangerUse_Bed")
    build("AM_FoA_HangerDoor", DOOR, [("KneelDown", 0.8), ("WorkDone", KEYS["door"]["contact"])], "BP_FoAHangerUse_Door")


assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "PIE running"
{"bake": step_bake, "montages": step_montages}[os.environ.get("FOA_STEP", "bake")]()
