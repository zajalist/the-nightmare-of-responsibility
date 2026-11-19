"""Anim lane: retarget the staged GASP clips (gasp_copy.py) onto our hidden Mannequin, which drives the Teen.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/gasp_retarget.py FOA_AREAS=/Game/FoA/Characters/Player FOA_STEP=rig|clips|post
rig    IK_FoA_GASP on the staged GASP mesh (auto chains + full-body IK) and RTG_GASP_to_Mannequin to IK_FoA_Mannequin
       (both A-pose rigs from Epic: chains auto-mapped, target pose aligned). A retargeter GASP ships for the UE5
       Mannequin is preferred when staged (FOA_RTG=/Game/... overrides).
clips  batch retarget into /Game/FoA/Characters/Player/Anims/GASP as AS_GASP_<clip> (root motion kept).
post   on every AS_GASP_*: drop GASP's notifies (their classes are not shipped), foot sync markers (L/R mid-stance),
       a 'Distance' curve on starts and stops (root distance travelled, negative to the stop: what distance matching
       reads), wood footsteps on the loops, starts, stops and pivots.
Chain: GASP skeleton -> RTG_GASP_to_Mannequin (offline, this script) -> SK_Mannequin clips -> ABP_FoAPlayer on the hidden
Mannequin -> RTG_Mannequin_to_Teen (runtime, retained ABP_FoAPlayer_MH class name) -> the visible Teen."""
import json
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
P = "/Game/FoA/Characters/Player"
RIGS, OUT = P + "/Retarget", P + "/Anims/GASP"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
EAL, AL, AP = unreal.EditorAssetLibrary, unreal.AnimationLibrary, unreal.AnimPoseExtensions
AT = unreal.AssetToolsHelpers.get_asset_tools()
SOT = unreal.RetargetSourceOrTarget
CS = unreal.AnimPoseSpaces.WORLD
STEP_SOUND = "/Game/FoA/Audio/MetaSounds/Footsteps/S_Footsteps_WoodWalk"
pick = json.load(open("P:/FoA/Saved/AnimShots/gasp_pick.json"))
staged = json.load(open("P:/FoA/Saved/AnimShots/gasp_staged.json"))


def fresh(name, cls, factory):
    return unreal.load_asset(f"{RIGS}/{name}") or AT.create_asset(name, RIGS, cls, factory)


def source_mesh():
    """The staged GASP skeletal mesh whose skeleton the clips use."""
    clip = unreal.load_asset(pick["clips"][0]["package"])
    skel = clip.get_editor_property("skeleton")
    for s in staged:
        a = unreal.load_asset(s["package"])
        if isinstance(a, unreal.SkeletalMesh) and a.get_editor_property("skeleton") == skel:
            return a, skel
    raise RuntimeError(f"no staged SkeletalMesh on {skel.get_path_name()}: stage one (gasp_copy.py) first")


def step_rig():
    mesh, skel = source_mesh()
    rig = fresh("IK_FoA_GASP", unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    ok = c.apply_auto_generated_retarget_definition()
    while c.get_num_solvers() > 1:
        c.remove_solver(c.get_num_solvers() - 1)
    if c.get_num_solvers() == 0:
        c.apply_auto_fbik()
    EAL.save_loaded_asset(rig, False)
    target = unreal.load_asset(RIGS + "/IK_FoA_Mannequin")
    rtg = fresh("RTG_GASP_to_Mannequin", unreal.IKRetargeter, unreal.IKRetargetFactory())
    r = unreal.IKRetargeterController.get_controller(rtg)
    r.set_ik_rig(SOT.SOURCE, rig)
    r.set_ik_rig(SOT.TARGET, target)
    r.set_preview_mesh(SOT.SOURCE, mesh)
    r.set_preview_mesh(SOT.TARGET, unreal.load_asset(MANNY))
    if r.get_num_retarget_ops() == 0:
        r.add_default_ops()
    r.assign_ik_rig_to_all_ops(SOT.SOURCE, rig)
    r.assign_ik_rig_to_all_ops(SOT.TARGET, target)
    r.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    pose = "FoA_Aligned"
    if pose not in [str(k) for k in r.get_retarget_poses(SOT.TARGET)]:
        pose = r.create_retarget_pose(pose, SOT.TARGET)
    r.set_current_retarget_pose(pose, SOT.TARGET)
    r.auto_align_all_bones(SOT.TARGET)
    EAL.save_loaded_asset(rtg, False)
    print("rig:", mesh.get_path_name(), "auto", ok, "chains", [str(ch.chain_name) for ch in c.get_retarget_chains()][:8], "...")


def step_clips():
    mesh, _ = source_mesh()
    rtg = unreal.load_asset(os.environ.get("FOA_RTG", RIGS + "/RTG_GASP_to_Mannequin"))
    lo, hi = (int(x) for x in os.environ.get("FOA_SLICE", "0:999").split(":"))  # chunk the batch: runs stay under 30 s
    srcs = [EAL.find_asset_data(c["package"]) for c in pick["clips"][lo:hi]]
    srcs = [a for a in srcs if a.is_valid()]
    inputs = unreal.IKRetargetBatchOperationInputs()
    for k, v in (("assets_to_retarget", srcs), ("source_mesh", mesh), ("target_mesh", unreal.load_asset(MANNY)),
                 ("ik_retarget_asset", rtg), ("prefix", "AS_GASP_"), ("target_path", OUT),
                 ("include_referenced_assets", False), ("overwrite_existing_files", True)):
        inputs.set_editor_property(k, v)
    out = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    for ad in out:
        EAL.save_loaded_asset(ad.get_asset(), False)
    print("retargeted", len(out), [str(a.asset_name) for a in out])


def distance_curve(seq, to_stop):
    """'Distance' float curve from the root's horizontal travel: from the start for starts, minus the remaining
    distance for stops (0 at the end). Distance matching reads it."""
    n, length = AL.get_num_frames(seq), seq.get_play_length()
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("extract_root_motion", False)
    roots = [AP.get_bone_pose(AP.get_anim_pose_at_frame(seq, f, o), "root", CS).translation for f in range(n + 1)]
    d, acc = [0.0], 0.0
    for a, b in zip(roots, roots[1:]):
        acc += ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5
        d.append(acc)
    vals = [v - acc for v in d] if to_stop else d
    if AL.does_curve_exist(seq, "Distance", unreal.RawCurveTrackTypes.RCT_FLOAT):
        AL.remove_curve(seq, "Distance", False)
    AL.add_curve(seq, "Distance", unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, "Distance", [length * f / n for f in range(n + 1)], vals)
    import dm_compression
    dm_compression.assign(seq)
    return round(acc, 1)


def step_post():
    import importlib
    import build_loco
    importlib.reload(build_loco)  # mid_stance_times / plant_times (its module body only runs a step when FOA_STEP is set)
    sound = unreal.load_asset(STEP_SOUND)
    slots = {c["package"].split("/")[-1]: c["slot"] for c in pick["clips"]}
    for path in EAL.list_assets(OUT, recursive=False):
        seq = unreal.load_asset(path.split(".")[0])
        if not isinstance(seq, unreal.AnimSequence):
            continue
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
        slot = slots.get(seq.get_name().replace("AS_GASP_", ""), "")
        for t in list(AL.get_animation_notify_track_names(seq)):
            AL.remove_animation_notify_events_by_track(seq, t)
        info = {}
        if slot in ("walk_loop", "jog_loop", "walk_start", "walk_stop", "walk_pivot", "jog_start", "jog_stop"):
            times = build_loco.mid_stance_times(seq)
            if "Sync" not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
                AL.add_animation_notify_track(seq, "Sync")
            for name, ts in times.items():
                for t in ts:
                    AL.add_animation_sync_marker(seq, name, t, "Sync")
            if "Footsteps" not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
                AL.add_animation_notify_track(seq, "Footsteps")
            for side, ts in build_loco.plant_times(seq).items():
                for t in ts:
                    n = AL.add_animation_notify_event(seq, "Footsteps", t, unreal.AnimNotify_PlaySound)
                    for k, v in (("sound", sound), ("follow", True), ("attach_name", f"foot_{side}")):
                        n.set_editor_property(k, v)
            info["markers"] = {k: len(v) for k, v in times.items()}
        if slot in ("walk_start", "walk_stop", "jog_start", "jog_stop"):
            info["distance_cm"] = distance_curve(seq, slot.endswith("_stop"))
        EAL.save_loaded_asset(seq, False)
        print(f"{seq.get_name():48s} {slot:14s} {seq.get_play_length():5.2f}s {info}")


{"rig": step_rig, "clips": step_clips, "post": step_post}[os.environ["FOA_STEP"]]()
