"""IK-retargets the chosen Quaternius UAL clips onto the UE5 mannequin (SK_Mannequin), with auto-generated IK rigs.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/retarget_ual.py
Re-running rebuilds the rigs/retargeters and overwrites the retargeted clips."""
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import importlib  # noqa: E402

import finger_chains  # noqa: E402

importlib.reload(finger_chains)  # the editor's Python keeps modules cached across runs
fix_fingers = finger_chains.fix_fingers

P = "/Game/FoA/Characters/Player"
RIGS = P + "/Retarget"
OUT = P + "/Anims/UAL"
TARGET_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
# UAL1's FBX skeleton stores meter-scale local translations under a 100x root scale (UAL2's glTF is plain cm).
# FK + pelvis retargeting handles that, but the IK goal ops mix the spaces and fling the body ~80 m away, so UAL1
# runs FK-only (proportions match Manny within 5%; in-game foot contact comes from the ABP's foot-IK control rig).
FK_ONLY = {"UAL1"}
SRC = {  # pack -> (source mesh, asset-name prefix, clips to retarget)
    "UAL1": (P + "/Source/UAL1/AL_Standard", "AL_StandardRig_",
             ["Walk_Loop", "Walk_Formal_Loop", "Jog_Fwd_Loop", "Idle_Loop", "PickUp_Table", "Interact",
              "Fixing_Kneeling", "Hit_Chest", "Hit_Head", "Sitting_Enter", "Sitting_Exit", "Sitting_Idle_Loop",
              "Push_Loop", "Crouch_Idle_Loop", "Crouch_Fwd_Loop"]),
    "UAL2": (P + "/Source/UAL2/UAL2_Standard/SkeletalMeshes/UAL2_Standard", "UAL2_Standard",
             ["LayToIdle", "Farm_Harvest", "Farm_PlantSeed", "Chest_Open", "Hit_Knockback", "Idle_No_Loop",
              "Idle_FoldArms_Loop", "Consume", "Yes"]),
}
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
SOT = unreal.RetargetSourceOrTarget


def fresh(name, path, cls, factory):
    """Reuses the asset when it exists (deleting a referenced rig fails), else creates it."""
    return unreal.load_asset(f"{path}/{name}") or AT.create_asset(name, path, cls, factory)


def ik_rig(name, mesh):
    rig = fresh(name, RIGS, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    ok = c.apply_auto_generated_retarget_definition()
    while c.get_num_solvers() > 1:  # earlier runs stacked one FBIK solver per run
        c.remove_solver(c.get_num_solvers() - 1)
    if c.get_num_solvers() == 0:
        c.apply_auto_fbik()
    print(name, "auto retarget definition:", ok, "chains:", [str(ch.chain_name) for ch in c.get_retarget_chains()])
    return rig


import os
target_mesh = unreal.load_asset(TARGET_MESH)
target_rig = unreal.load_asset(RIGS + "/IK_FoA_Mannequin") or ik_rig("IK_FoA_Mannequin", target_mesh)
packs = [p.strip() for p in os.environ.get("FOA_PACKS", "").split(",") if p.strip()] or list(SRC)
for pack in packs:
    mesh_path, prefix, clips = SRC[pack]
    mesh = unreal.load_asset(mesh_path)
    assert mesh, "missing source mesh " + mesh_path
    src_rig = ik_rig(f"IK_{pack}", mesh)
    rtg = fresh(f"RTG_{pack}_to_Mannequin", RIGS, unreal.IKRetargeter, unreal.IKRetargetFactory())
    c = unreal.IKRetargeterController.get_controller(rtg)
    c.set_ik_rig(SOT.SOURCE, src_rig)
    c.set_ik_rig(SOT.TARGET, target_rig)
    c.set_preview_mesh(SOT.SOURCE, mesh)
    c.set_preview_mesh(SOT.TARGET, target_mesh)
    if c.get_num_retarget_ops() == 0:
        c.add_default_ops()
    names = [str(c.get_op_name(i)) for i in range(c.get_num_retarget_ops())]
    for i in reversed(range(len(names))):  # drop duplicates of the goals op left by earlier runs
        if names[i].startswith("Retarget IK Goals_"):
            c.remove_retarget_op(i)
    names = [str(c.get_op_name(i)) for i in range(c.get_num_retarget_ops())]
    if "Retarget IK Goals" not in names:
        # The default stack here has no IK Chains op, so Run IK Rig solved toward unset goals and flung the
        # body ~80 m away. IK Chains must feed the goals, right after FK Chains.
        idx = c.add_retarget_op("/Script/IKRig.IKRetargetIKChainsOp")
        assert idx >= 0, "could not add the IK Chains op"
        c.move_retarget_op_in_stack(idx, names.index("FK Chains") + 1)
    for i in range(c.get_num_retarget_ops()):
        c.set_retarget_op_enabled(i, not (pack in FK_ONLY and str(c.get_op_name(i)) in ("Retarget IK Goals", "Run IK Rig")))
    c.assign_ik_rig_to_all_ops(SOT.SOURCE, src_rig)
    c.assign_ik_rig_to_all_ops(SOT.TARGET, target_rig)
    c.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    print("finger chains one-to-one:", fix_fingers(c))
    # UAL is authored in a T pose, Manny's ref pose is an A pose: pose the target to match before retargeting.
    pose = "FoA_TPose" if "FoA_TPose" in [str(k) for k in c.get_retarget_poses(SOT.TARGET)] else c.create_retarget_pose("FoA_TPose", SOT.TARGET)
    c.set_current_retarget_pose(pose, SOT.TARGET)
    c.auto_align_all_bones(SOT.TARGET)
    print(pack, "ops:", [str(c.get_op_name(i)) for i in range(c.get_num_retarget_ops())])
    EAL.save_loaded_asset(rtg)
    srcs = []
    for clip in clips:
        ad = EAL.find_asset_data(mesh_path.rsplit("/", 1)[0] + f"/{prefix}{clip}")
        if ad.is_valid():
            srcs.append(ad)
        else:
            print("MISSING", pack, clip)
    # Overwrite in place: blend spaces and montages keep their references and nothing is deleted mid-run
    # (single-writer protocol: never delete assets in a run that loads or edits them).
    inputs = unreal.IKRetargetBatchOperationInputs()
    for k, v in (("assets_to_retarget", srcs), ("source_mesh", mesh), ("target_mesh", target_mesh), ("ik_retarget_asset", rtg),
                 ("search", prefix), ("replace", "UAL_"), ("target_path", OUT), ("include_referenced_assets", False),
                 ("overwrite_existing_files", True)):
        inputs.set_editor_property(k, v)
    out = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    # Keep the project's ACL codec. Swapping codecs from Python left stale ACL data in the saved clips and the next
    # duplicate (hero retarget) crashed the editor in FDuplicateDataReader (17:15). If a clip jitters, raise its
    # compression error threshold in the editor instead.
    for ad in out:
        EAL.save_loaded_asset(ad.get_asset(), False)
    print(pack, "retargeted", len(out), [str(a.asset_name) for a in out])
for rig in (target_rig,):
    EAL.save_loaded_asset(rig)
EAL.save_directory(P, only_if_is_dirty=True, recursive=True)
