"""Anim lane locomotion for ABP_FoAPlayer (re-runnable, edits in place):
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_loco.py FOA_AREAS=/Game/FoA/Characters/Player FOA_STEP=<step>
markers  foot sync markers (L/R at mid-stance: the foot passes under the pelvis) on the walk clips, so blends and
         transitions keep the feet in phase. The template's brisk walk is duplicated into Player/Anims/Loco first.
walk     Walk / Run: one looping Sequence Player of the template walk, PlayRate from GroundSpeed (MapRangeClamped);
         Stride Warping matches the stride to the capsule exactly (no sliding); walkpin wires the pin after a reload.
states   Idle plays MM_Idle a touch slow (tired); every Locomotion transition
         is inertialized (0.3 s; build_abp.py FOA_STEP=animgraph adds the Inertialization node).
move     BP_FoAPlayer movement: walk 130, hurry 280, braking that stops him in under 0.2 s, 300 deg/s turning.
footsteps wood footstep sounds on the walk clip's foot plants."""
import os

import unreal

P = "/Game/FoA/Characters/Player"
LOCO = P + "/Anims/Loco"
BRISK_SRC = "/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd"
BRISK = LOCO + "/AS_FoA_Walk_Brisk"
ABP = P + "/ABP_FoAPlayer"
EAL, AL, AP = unreal.EditorAssetLibrary, unreal.AnimationLibrary, unreal.AnimPoseExtensions
BEL, BGE = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
CS = unreal.AnimPoseSpaces.WORLD  # component space for a sequence pose
# (clip, ground speed cm/s, rate scale): rate = speed / the clip's native speed (measured: anim_probe.py)
# One clip, the template's mocap walk, at three rate scales: the cadence slows with the speed and Stride Warping
# (build_abp.py FOA_STEP=stride) shortens the stride to the exact capsule speed, a tired, heavy walk at 130 cm/s.
# (UAL's walk was dropped: its retarget holds the arms ~35 deg out from the body.)
WALK_SPEED, HURRY_SPEED = 130.0, 280.0


def closed(asset):
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    return asset


def mid_stance_times(seq):
    """{'L': [t...], 'R': [t...]}: times the foot crosses under the pelvis front-to-back (forward is +Y)."""
    n, length = AL.get_num_frames(seq), seq.get_play_length()
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("extract_root_motion", False)
    poses = [AP.get_anim_pose_at_frame(seq, f, o) for f in range(n + 1)]
    out = {}
    for side in ("l", "r"):
        rel = [AP.get_bone_pose(p, f"foot_{side}", CS).translation.y - AP.get_bone_pose(p, "pelvis", CS).translation.y
               for p in poses]
        ts = []
        for f in range(n):
            if rel[f] > 0.0 >= rel[f + 1]:
                ts.append(length * (f + rel[f] / (rel[f] - rel[f + 1])) / n)
        out[side.upper()] = ts
    return out


def step_markers():
    if not EAL.does_asset_exist(BRISK):
        assert EAL.duplicate_asset(BRISK_SRC, BRISK), "duplicate brisk walk"
    for path in (BRISK,):
        seq = closed(unreal.load_asset(path))
        AL.remove_animation_sync_markers_by_track(seq, "Sync") if "Sync" in [str(t) for t in AL.get_animation_notify_track_names(seq)] else None
        if "Sync" not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
            AL.add_animation_notify_track(seq, "Sync")
        times = mid_stance_times(seq)
        assert times["L"] and times["R"], f"{path}: no foot crossing found {times}"
        for name, ts in times.items():
            for t in ts:
                AL.add_animation_sync_marker(seq, name, t, "Sync")
        EAL.save_loaded_asset(seq, False)
        print("markers", path.split("/")[-1], {k: [round(t, 3) for t in v] for k, v in times.items()},
              "len", round(seq.get_play_length(), 3))


def state_graph(a, name):
    return next(g for g in BEL.list_graphs(a) if g.get_class().get_name() == "AnimationStateGraph" and g.get_name() == name)


def step_states():
    a = closed(unreal.load_asset(ABP))
    # Idle: the template's breathing idle, a touch slow for a tired body.
    ied = BGE.get_graph_editor(state_graph(a, "Idle"))
    idle = next(n for n in ied.list_all_nodes() if BEL.get_node_title(n).startswith("Sequence Player"))
    node = idle.get_editor_property("node")
    node.set_editor_property("play_rate", 0.85)
    idle.set_editor_property("node", node)
    for g in BEL.list_graphs(a):
        if g.get_class().get_name() != "AnimationTransitionGraph":
            continue
        t = g.get_outer()
        if t.get_outer().get_name() != "Locomotion":  # the Locomotion state machine graph only (not Main States)
            continue
        t.set_editor_property("logic_type", unreal.TransitionLogicType.TLT_INERTIALIZATION)
        t.set_editor_property("crossfade_duration", 0.3)
    EAL.save_loaded_asset(a, False)
    print("states: Idle MM_Idle x0.85; Locomotion transitions inertialized (Walk / Run: FOA_STEP=walk)")


def step_move():
    bp = closed(unreal.load_asset(P + "/BP_FoAPlayer"))
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("WalkSpeed", WALK_SPEED)
    cdo.set_editor_property("JogSpeed", HURRY_SPEED)
    cm = cdo.get_editor_property("character_movement")
    for k, v in (("max_walk_speed", WALK_SPEED), ("max_acceleration", 600.0), ("braking_deceleration_walking", 900.0),
                 ("ground_friction", 8.0), ("rotation_rate", unreal.Rotator(roll=0.0, pitch=0.0, yaw=300.0))):
        cm.set_editor_property(k, v)
    EAL.save_loaded_asset(bp, False)
    print("move", {k: cm.get_editor_property(k) for k in ("max_walk_speed", "max_acceleration", "braking_deceleration_walking")})


RATE_MAP = (60.0, 300.0, 0.55, 1.0)  # GroundSpeed range -> walk play rate (the cadence slows with the speed)


def step_walk():
    """Walk / Run = one looping Sequence Player of the template walk whose PlayRate pin reads WalkPlayRate, set every
    update from GroundSpeed (MapRangeClamped). Replaces BS_FoA_Walk: a blend space whose samples are set from Python
    is never resampled and evaluates the reference pose (he slid in an A-pose). Stride Warping fits the stride to the
    exact speed. Then FOA_STEP=walkpin wires the pin after a reload."""
    a = closed(unreal.load_asset(ABP))
    # apply_locomotion_root_motion.py inserts the safe initialization setter.
    # The authored clip contains300cm/s root motion; do not drive the capsule from it.
    import sys
    sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
    import importlib
    import graph_style
    importlib.reload(graph_style)
    graph_style.ensure_variable(a, "WalkPlayRate", BEL.get_basic_type_by_name("real"), "1.0")
    BEL.set_blueprint_variable_category(a, "WalkPlayRate", "FoA")
    ed = BGE.get_graph_editor(state_graph(a, "Walk / Run"))
    for n in ed.list_all_nodes():
        if not BEL.get_node_title(n).startswith("Output Animation Pose"):
            ed.remove_nodes([n])
    result = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Output Animation Pose"))
    BEL.set_node_pos(result, unreal.IntPoint(0, 0))
    entry = next(str(e) for e in ed.list_available_nodes([]) if str(e).endswith("Play'AS_FoA_Walk_Brisk'"))
    player = ed.create_node_from_name(entry, unreal.Vector2D(-320, -16), [])
    BEL.set_node_pos(player, unreal.IntPoint(-320, -16))
    PIN = unreal.BlueprintGraphPinLibrary
    assert PIN.try_create_connection(BEL.find_output_pin(player, "Pose"), BEL.find_input_pin(result, "Result"))
    pins = []
    for q in player.get_editor_property("show_pin_for_properties"):
        if str(q.get_editor_property("property_name")) == "PlayRate":
            q.set_editor_property("show_pin", True)
        pins.append(q)
    player.set_editor_property("show_pin_for_properties", pins)
    # EventGraph: WalkPlayRate from GroundSpeed, on a spare Sequence pin of the update.
    eg = BGE.get_graph_editor_by_name(a, "EventGraph")
    for n in list(eg.list_all_nodes()):
        t = BEL.get_node_title(n).replace(" ", "")
        if t in ("SetWalkPlayRate", "MapRangeClamped") or (t == "GetGroundSpeed" and BEL.get_node_pos(n).y >= 1500):
            eg.remove_nodes([n])
    seq = next(n for n in eg.list_all_nodes() if BEL.get_node_title(n) == "Sequence")
    free_pins = [q for q in BEL.list_output_pins(seq) if not PIN.list_connected_pins(q)]
    if not free_pins:
        eg.add_node_pin(seq)
        free_pins = [BEL.list_output_pins(seq)[-1]]
    X, Y = -400, 1600
    g = eg.add_get_member_variable_node("GroundSpeed", "")
    BEL.set_node_pos(g, unreal.IntPoint(X, Y + 120))
    m = eg.add_call_function_node("/Script/Engine.KismetMathLibrary:MapRangeClamped")
    BEL.set_node_pos(m, unreal.IntPoint(X + 220, Y + 80))
    st = eg.add_set_member_variable_node("WalkPlayRate", "")
    BEL.set_node_pos(st, unreal.IntPoint(X + 520, Y))
    assert PIN.try_create_connection(free_pins[0], BEL.find_execute_pin(st))
    assert PIN.try_create_connection(BEL.find_output_pin(g, "GroundSpeed"), BEL.find_input_pin(m, "Value"))
    for pin, v in zip(("InRangeA", "InRangeB", "OutRangeA", "OutRangeB"), RATE_MAP):
        PIN.set_pin_value(BEL.find_input_pin(m, pin), str(v))
    assert PIN.try_create_connection(BEL.find_output_pin(m, "ReturnValue"), BEL.find_input_pin(st, "WalkPlayRate"))
    graph_style.box(eg, "FoA: walk cadence", "", [g, m, st], "anim")
    EAL.save_loaded_asset(a, False)
    print("walk: Sequence Player", entry, "PlayRate <- WalkPlayRate = MapRangeClamped(GroundSpeed", RATE_MAP, ")")


def step_walkpin():
    a = closed(unreal.load_asset(ABP))
    pkg = a.get_outermost()
    dirty = [x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    assert pkg.get_name() not in dirty, f"{pkg.get_name()} has unsaved edits: fix and save first"
    unreal.EditorLoadingAndSavingUtils.reload_packages([pkg])  # reconstructs the player -> PlayRate pin
    a = closed(unreal.load_asset(ABP))
    ed = BGE.get_graph_editor(state_graph(a, "Walk / Run"))
    player = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Sequence Player"))
    g = ed.add_get_member_variable_node("WalkPlayRate", "")
    BEL.set_node_pos(g, unreal.IntPoint(-560, 40))
    assert unreal.BlueprintGraphPinLibrary.try_create_connection(BEL.find_output_pin(g, "WalkPlayRate"),
                                                                 BEL.find_input_pin(player, "PlayRate")), "PlayRate pin"
    EAL.save_loaded_asset(a, False)
    print("walkpin: WalkPlayRate -> PlayRate")


STEP_SOUND = "/Game/FoA/Audio/MetaSounds/Footsteps/S_Footsteps_WoodWalk"


def plant_times(seq):
    """{'l': [t], 'r': [t]}: heel strike, the moment a swinging foot drops to within 2 cm of its lowest height."""
    n, length = AL.get_num_frames(seq), seq.get_play_length()
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("extract_root_motion", False)
    poses = [AP.get_anim_pose_at_frame(seq, f, o) for f in range(n + 1)]
    mids = mid_stance_times(seq)
    out = {}
    for side in ("l", "r"):
        z = [AP.get_bone_pose(p, f"foot_{side}", CS).translation.z for p in poses]
        low = min(z) + 2.0
        drops = [length * (f + 1) / n for f in range(n) if z[f] > low >= z[f + 1]]
        # heel then toe both cross the threshold: one plant per step, the last drop before that foot's mid-stance
        out[side] = sorted({max((d for d in drops if d <= m), default=drops[-1] if drops else m) for m in mids[side.upper()]})
    return out


def step_footsteps():
    """Wood footsteps on the walk cycle's foot plants (PlaySound notifies attached to each foot). The same clip covers
    walk and hurry, so one sound; shortcut: no sand surface check, upgrade with a surface trace notify when sand floors
    are walkable."""
    seq = closed(unreal.load_asset(BRISK))
    if "Footsteps" in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, "Footsteps")
    else:
        AL.add_animation_notify_track(seq, "Footsteps")
    sound = unreal.load_asset(STEP_SOUND)
    assert sound, STEP_SOUND
    times = plant_times(seq)
    for side, ts in times.items():
        for t in ts:
            n = AL.add_animation_notify_event(seq, "Footsteps", t, unreal.AnimNotify_PlaySound)
            for k, v in (("sound", sound), ("follow", True), ("attach_name", f"foot_{side}")):
                n.set_editor_property(k, v)
    EAL.save_loaded_asset(seq, False)
    print("footsteps", {k: [round(t, 3) for t in v] for k, v in times.items()}, "len", round(seq.get_play_length(), 3))


GASP = P + "/Anims/GASP/AS_GASP_M_"
IDLE = GASP + "Relaxed_Stand_Idle_Loop"
BREAKS = [  # (clip, chance, loops min..max, play rate min..max): GASP's relaxed idle most of the time, a break now and then
    (IDLE, 0.58, 1, 2, 0.85, 0.92),  # 10 s of slow breathing and weight shifts
] + [(GASP + f"Relaxed_Stand_Idle_Break_v{i:02d}", 0.07, 1, 1, 0.85, 0.95) for i in (1, 2, 4, 5, 6, 7)]


def step_idlebreaks():
    """Idle = a Random Sequence Player: the tired breathing idle most of the time, a weary head shake or a stance shift
    now and then, 0.5 s blends between them (replaces the single MM_Idle player). GASP idle breaks replace these."""
    a = closed(unreal.load_asset(ABP))
    ed = BGE.get_graph_editor(state_graph(a, "Idle"))
    for n in ed.list_all_nodes():
        if not BEL.get_node_title(n).startswith("Output Animation Pose"):
            ed.remove_nodes([n])
    result = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Output Animation Pose"))
    BEL.set_node_pos(result, unreal.IntPoint(0, 0))
    rp = ed.create_node_from_name("Animation|Sequences|RandomSequencePlayer", unreal.Vector2D(-320, -16), [])
    BEL.set_node_pos(rp, unreal.IntPoint(-320, -16))
    assert unreal.BlueprintGraphPinLibrary.try_create_connection(BEL.find_output_pin(rp, "Pose"), BEL.find_input_pin(result, "Result"))
    node = rp.get_editor_property("node")
    entries = []
    for clip, chance, lo, hi, r0, r1 in BREAKS:
        e = unreal.RandomPlayerSequenceEntry()
        for k, v in (("sequence", unreal.load_asset(clip)), ("chance_to_play", chance), ("min_loop_count", lo),
                     ("max_loop_count", hi), ("min_play_rate", r0), ("max_play_rate", r1)):
            e.set_editor_property(k, v)
        b = e.get_editor_property("blend_in")
        b.set_editor_property("blend_time", 0.5)
        e.set_editor_property("blend_in", b)
        entries.append(e)
    node.set_editor_property("entries", entries)
    rp.set_editor_property("node", node)
    EAL.save_loaded_asset(a, False)
    print("idle breaks:", [(c.split("/")[-1], ch) for c, ch, *_ in BREAKS])


if __name__ == "__main__":  # importable (gasp_retarget.py reuses mid_stance_times / plant_times)
    {"markers": step_markers, "states": step_states, "move": step_move, "walk": step_walk,
     "walkpin": step_walkpin, "footsteps": step_footsteps,
     "idlebreaks": step_idlebreaks}[os.environ["FOA_STEP"]]()
