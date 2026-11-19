"""Hero retarget tooling: UE5 mannequin (SK_Mannequin) animation -> the Lux3D hero on its Mixamo 52-bone skeleton.
  setup: python Tools/Unreal/ue_remote.py Tools/Unreal/player/hero_retarget.py FOA_HERO_MESH=/Game/FoA/Characters/Hero/SK_Hero
  batch: ... FOA_MODE=batch FOA_HERO_MESH=... (retargets ABP_FoAPlayer + every montage, remapping all references)
Builds IK_Hero (auto-characterized; explicit Mixamo chain table as fallback) and RTG_Mannequin_to_Hero with the
full op stack: pelvis motion, FK chains, IK goals (feet + hands), FBIK, root motion."""
import os

import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import importlib  # noqa: E402

import finger_chains  # noqa: E402

importlib.reload(finger_chains)  # the editor's Python keeps modules cached across runs
fix_fingers = finger_chains.fix_fingers

P = "/Game/FoA/Characters/Player"
RIGS = P + "/Retarget"
OUT = "/Game/FoA/Characters/Hero/Anims"
SRC_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
SOT = unreal.RetargetSourceOrTarget
# Mixamo chain table, named like the auto-generated Manny rig so chains map by name (Manny-only chains such as
# the metacarpals stay unmapped: Mixamo has no metacarpal bones).
CHAINS = [("Spine", "Spine", "Spine2", None), ("Neck", "Neck", "Neck", None), ("Head", "Head", "Head", None)]
for side in ("Left", "Right"):
    CHAINS += [(f"{side}Clavicle", f"{side}Shoulder", f"{side}Shoulder", None),
               (f"{side}Arm", f"{side}Arm", f"{side}Hand", f"{side}HandIK"),
               (f"{side}Leg", f"{side}UpLeg", f"{side}ToeBase", f"{side}FootIK")]
    CHAINS += [(f"{side}{f}", f"{side}Hand{f}1", f"{side}Hand{f}3", None)
               for f in ("Thumb", "Index", "Middle", "Ring", "Pinky")]


def bone_names(mesh):
    ref = unreal.AnimPoseExtensions.get_reference_pose(mesh.get_editor_property("skeleton"))
    return [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(ref)]


def asset(name, cls, factory):
    return unreal.load_asset(f"{RIGS}/{name}") or AT.create_asset(name, RIGS, cls, factory)


def build_hero_rig(mesh):
    rig = asset("IK_Hero", unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    auto = c.apply_auto_generated_retarget_definition()
    have = {str(ch.chain_name) for ch in c.get_retarget_chains()}
    if not auto or len(have) < 15:
        names = bone_names(mesh)

        def bone(suffix):  # "mixamorig:Hips" may import with its namespace kept or mangled; match the suffix
            hits = [n for n in names if n.split(":")[-1] == suffix or n.endswith("_" + suffix) or n == suffix]
            assert hits, "no bone named like " + suffix
            return hits[0]
        for ch in list(have):
            c.remove_retarget_chain(ch)
        c.set_retarget_root(bone("Hips"))
        for chain, start, end, goal in CHAINS:
            c.add_retarget_chain(chain, bone(start), bone(end), "")
            if goal:
                g = c.add_new_goal(goal, bone(end if "Hand" in goal else end.replace("ToeBase", "Foot")))
                c.set_retarget_chain_goal(chain, g)
    while c.get_num_solvers() > 1:  # re-runs must not stack FBIK solvers
        c.remove_solver(c.get_num_solvers() - 1)
    if c.get_num_solvers() == 0:
        c.apply_auto_fbik()
    print("IK_Hero auto:", auto, "root:", c.get_retarget_root())
    print("chains:", [(str(n), str(c.get_retarget_chain_start_bone(n)), str(c.get_retarget_chain_end_bone(n)),
                       str(c.get_retarget_chain_goal(n))) for n in (ch.chain_name for ch in c.get_retarget_chains())])
    print("goals:", [(str(g.goal_name), str(g.bone_name)) for g in c.get_all_goals()])
    EAL.save_loaded_asset(rig, False)
    return rig


def build_retargeter(hero_mesh, hero_rig):
    src_mesh = unreal.load_asset(SRC_MESH)
    src_rig = unreal.load_asset(RIGS + "/IK_FoA_Mannequin")
    rtg = asset("RTG_Mannequin_to_Hero", unreal.IKRetargeter, unreal.IKRetargetFactory())
    c = unreal.IKRetargeterController.get_controller(rtg)
    c.set_ik_rig(SOT.SOURCE, src_rig)
    c.set_ik_rig(SOT.TARGET, hero_rig)
    c.set_preview_mesh(SOT.SOURCE, src_mesh)
    c.set_preview_mesh(SOT.TARGET, hero_mesh)
    if c.get_num_retarget_ops() == 0:
        c.add_default_ops()
    names = [str(c.get_op_name(i)) for i in range(c.get_num_retarget_ops())]
    if "Retarget IK Goals" not in names:  # without it Run IK Rig solves toward unset goals (see retarget_ual.py)
        idx = c.add_retarget_op("/Script/IKRig.IKRetargetIKChainsOp")
        assert idx >= 0, "could not add the IK goals op"
        c.move_retarget_op_in_stack(idx, names.index("FK Chains") + 1)
    # Mixamo has no root bone: mixamorig_Hips is both root and pelvis, so the Root Motion op would overwrite the
    # pelvis motion with Manny's stationary root (measured: hips frozen at the origin, even when lying down).
    for i in range(c.get_num_retarget_ops()):
        c.set_retarget_op_enabled(i, str(c.get_op_name(i)) != "Root Motion")
    c.assign_ik_rig_to_all_ops(SOT.SOURCE, src_rig)
    c.assign_ik_rig_to_all_ops(SOT.TARGET, hero_rig)
    c.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    print("finger chains one-to-one:", fix_fingers(c))
    # Lux3D rigs in a T pose; pose the hero into Manny's A pose so the FK deltas start from matching poses.
    if "FoA_APose" not in [str(k) for k in c.get_retarget_poses(SOT.TARGET)]:
        c.create_retarget_pose("FoA_APose", SOT.TARGET)
    c.set_current_retarget_pose("FoA_APose", SOT.TARGET)
    c.auto_align_all_bones(SOT.TARGET)
    print("RTG ops:", [str(c.get_op_name(i)) for i in range(c.get_num_retarget_ops())])
    print("mapping:", [(str(s.target_chain), str(c.get_source_chain(s.target_chain))) for s in c.get_all_chain_settings()])
    EAL.save_loaded_asset(rtg, False)
    return rtg


mesh = unreal.load_asset(os.environ["FOA_HERO_MESH"])
assert mesh, "hero mesh not found: " + os.environ["FOA_HERO_MESH"]
if os.environ.get("FOA_MODE", "setup") == "setup":
    build_retargeter(mesh, build_hero_rig(mesh))
else:
    rtg = unreal.load_asset(RIGS + "/RTG_Mannequin_to_Hero")
    roots = [EAL.find_asset_data(P + "/ABP_FoAPlayer")] + [EAL.find_asset_data(a) for a in EAL.list_assets(P + "/Montages")]
    inputs = unreal.IKRetargetBatchOperationInputs()
    for k, v in (("assets_to_retarget", [r for r in roots if r.is_valid()]), ("source_mesh", unreal.load_asset(SRC_MESH)),
                 ("target_mesh", mesh), ("ik_retarget_asset", rtg), ("suffix", "_Hero"), ("target_path", OUT),
                 ("include_referenced_assets", True), ("overwrite_existing_files", True)):
        inputs.set_editor_property(k, v)
    out = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    for ad in out:
        EAL.save_loaded_asset(ad.get_asset(), False)
    print("retargeted", len(out), sorted(str(a.asset_name) for a in out))
