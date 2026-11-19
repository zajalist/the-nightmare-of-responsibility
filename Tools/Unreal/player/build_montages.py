"""Interaction montages for BP_FoAPlayer (slot DefaultSlot, which ABP_FoAPlayer's AnimGraph already has).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_montages.py
Each montage is a list of clip segments; gameplay notifies (PlayMontageNotify, read with "Play Montage" -> On Notify
Begin) mark the contact frames, found from the hand/pelvis motion rather than hand-typed times."""
import unreal

P = "/Game/FoA/Characters/Player"
UAL = P + "/Anims/UAL/"
OUT = P + "/Montages"
EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
AP = unreal.AnimPoseExtensions
W = unreal.AnimPoseSpaces.WORLD


def track(seq, bone):
    n = AL.get_num_frames(seq)
    opts = unreal.AnimPoseEvaluationOptions()
    return [(AL.get_time_at_frame(seq, f), AP.get_bone_pose(AP.get_anim_pose_at_frame(seq, f, opts), bone, W).translation)
            for f in range(n + 1)]


def t_min(seq, bone, axis="z"):
    return min(track(seq, bone), key=lambda tv: getattr(tv[1], axis))[0]


def t_max(seq, bone, axis="y"):
    return max(track(seq, bone), key=lambda tv: getattr(tv[1], axis))[0]


def t_reach(seq):
    """Contact time: the moment the hand that travels farthest from its start pose is at its peak displacement."""
    best = (0.0, 0.0)
    for bone in ("hand_l", "hand_r"):
        tr = track(seq, bone)
        p0 = tr[0][1]
        for t, v in tr:
            d = (v - p0).length()
            if d > best[0]:
                best = (d, t)
    return best[1]


def t_lowest_hand(seq):
    return min((tv for b in ("hand_l", "hand_r") for tv in track(seq, b)), key=lambda tv: tv[1].z)[0]


def kneel_window(seq, below=60.0):
    """First and last time the pelvis is below `below` cm: the settled kneel, used as the loopable work section."""
    low = [t for t, v in track(seq, "pelvis") if v.z < below]
    return (low[0], low[-1]) if low else (0.0, seq.get_play_length())


def build(name, segments, notifies, blend_out=0.35):
    """segments: (clip, start, end, rate, loops). notifies: (name, montage time)."""
    path = f"{OUT}/{name}"
    first = segments[0][0]
    m = unreal.load_asset(path)
    if m:  # update in place: deleting in the same run that edits is banned (single-writer protocol)
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(m)
        # Clear only the track this builder owns. InteractionContact (story's commit notify, contact_notify_assets.py)
        # and Audio (audio_wiring_assets.py) belong to other passes: clearing them silently broke every interaction
        # (2026-11-09). If segment times change, re-run those two passes so their notifies follow the new markers.
        if "Gameplay" in [str(t) for t in AL.get_animation_notify_track_names(m)]:
            AL.remove_animation_notify_events_by_track(m, "Gameplay")
    else:
        f = unreal.AnimMontageFactory()
        f.set_editor_property("source_animation", first)
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, OUT, unreal.AnimMontage, f)
    segs, pos = [], 0.0
    for clip, start, end, rate, loops in segments:
        s = unreal.AnimSegment()
        s.set_editor_property("anim_reference", clip)
        s.set_editor_property("anim_start_time", start)
        s.set_editor_property("anim_end_time", end)
        s.set_editor_property("anim_play_rate", rate)
        s.set_editor_property("looping_count", loops)
        s.import_text(f"(StartPos={pos})")  # StartPos is read-only to set_editor_property
        segs.append(s)
        pos += (end - start) / rate * loops
    tracks = m.get_editor_property("slot_anim_tracks")
    t0 = tracks[0]
    at = t0.get_editor_property("anim_track")
    at.set_editor_property("anim_segments", segs)
    t0.set_editor_property("anim_track", at)
    t0.set_editor_property("slot_name", "DefaultSlot")
    m.set_editor_property("slot_anim_tracks", [t0])
    for prop, secs in (("blend_in", 0.3), ("blend_out", blend_out)):
        b = m.get_editor_property(prop)
        b.set_editor_property("blend_time", secs)
        m.set_editor_property(prop, b)
    # The montage keeps its source clip's length until PostLoad runs ValidateSegmentTimes + SetCompositeLength
    # (both C++-only), so save, reload the package, then add notifies against the true length.
    EAL.save_loaded_asset(m, False)
    unreal.EditorLoadingAndSavingUtils.reload_packages([m.get_outermost()])
    m = unreal.load_asset(path)
    assert abs(m.get_play_length() - pos) < 0.05, f"{name}: length {m.get_play_length():.2f} != {pos:.2f}"
    if "Gameplay" not in [str(t) for t in AL.get_animation_notify_track_names(m)]:
        AL.add_animation_notify_track(m, "Gameplay")
    for nname, t in notifies:
        n = AL.add_animation_notify_event(m, "Gameplay", min(t, pos - 0.05), unreal.AnimNotify_PlayMontageNotify)
        n.set_editor_property("notify_name", nname)
    EAL.save_loaded_asset(m, False)
    print(f"{name:28s} {m.get_play_length():5.2f}s segs={len(segs)} notifies={[(n, round(t, 2)) for n, t in notifies]}")
    return m


def L(name):
    return unreal.load_asset(UAL + name)


harvest, table, interact = L("UAL_Farm_Harvest"), L("UAL_PickUp_Table"), L("UAL_Interact")
no, kneel, hit = L("UAL_Idle_No_Loop"), L("UAL_Fixing_Kneeling"), L("UAL_Hit_Chest")
lay, push = L("UAL_LayToIdle"), L("UAL_Push_Loop")

# Floor pickup: bend, grab at the lowest right-hand point, straighten (played a touch slow: a tired body).
r = 0.9
build("AM_FoA_PickUp_Floor", [(harvest, 0.0, harvest.get_play_length(), r, 1)],
      [("Grab", t_lowest_hand(harvest) / r)])
# Table-height pickup: the source clip is a brisk 0.83 s; slowed to read as careful.
r = 0.75
build("AM_FoA_PickUp_Table", [(table, 0.0, table.get_play_length(), r, 1)],
      [("Grab", t_reach(table) / r)])
# Drawer / door: reach out, grip at full reach, pull back.
build("AM_FoA_OpenDrawer", [(interact, 0.0, interact.get_play_length(), 1.0, 1)],
      [("Grip", t_reach(interact)), ("Pull", t_reach(interact) + 0.35)])
# Locked handle: reach and rattle twice (the grip window of the reach, looped), then a small head shake.
g = t_reach(interact)
reach_end = min(g + 0.3, interact.get_play_length())
build("AM_FoA_TryLockedHandle",
      [(interact, 0.0, g, 1.0, 1), (interact, max(0.0, g - 0.15), reach_end, 1.6, 2), (interact, reach_end, interact.get_play_length(), 1.0, 1),
       (no, 0.0, 1.6, 1.0, 1)],
      [("Rattle", g), ("Locked", g + 0.5)])
# Kneel at the door with a screwdriver: kneel in, work (the settled kneel looped), stand.
k0, k1 = kneel_window(kneel)
build("AM_FoA_KneelScrewdriver",
      [(kneel, 0.0, k0, 1.0, 1), (kneel, k0, k1, 1.0, 2), (kneel, k1, kneel.get_play_length(), 1.0, 1)],
      [("KneelDown", k0), ("WorkDone", k0 + 2 * (k1 - k0))])
# Equip beat: a garment snaps on - a slowed chest jolt as it lands ("Snap" = where the layer appears).
build("AM_FoA_Equip", [(hit, 0.0, hit.get_play_length(), 0.5, 1)], [("Snap", 0.08)], blend_out=0.5)
# Startle / recoil: a sharp chest flinch, slowed, with a long recovery blend.
build("AM_FoA_Startle", [(hit, 0.0, hit.get_play_length(), 0.7, 1)], [("Startle", 0.0)], blend_out=0.6)
# Wake-up (tutorial beat 1): held lying pose, then the get-up played slow. "SitUp" marks where the BP cuts from
# the bed to the bed's edge (time-shift blur); "Standing" is where control can return.
up = lay.get_play_length()
sit = next((t for t, v in track(lay, "head") if v.z > 100.0), up * 0.5)
build("AM_FoA_WakeUp", [(lay, 0.0, 1.0 / 30.0, 1.0, 60), (lay, 0.0, up, 0.6, 1)],
      [("WakeStir", 1.6), ("SitUp", 2.0 + sit / 0.6), ("Standing", 2.0 + up / 0.6 - 0.2)], blend_out=0.5)
