"""QA only: re-creates the pre-fix finger retarget (metacarpals fed by the finger chains, Interpolated rotation) into
/Game/FoA/Characters/Player/_QA so before/after hand captures can sit side by side. Delete _QA when QA is done.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/qa_hands_before.py"""
import unreal

P = "/Game/FoA/Characters/Player"
QA = P + "/_QA"
CLIPS = ["PickUp_Table", "Interact", "Fixing_Kneeling"]
EAL = unreal.EditorAssetLibrary


def run():
    src_rtg = P + "/Retarget/RTG_UAL1_to_Mannequin"
    rtg = unreal.load_asset(QA + "/RTG_UAL1_Before") or EAL.duplicate_asset(src_rtg, QA + "/RTG_UAL1_Before")
    c = unreal.IKRetargeterController.get_controller(rtg)
    for side in ("Left", "Right"):
        for f in ("Index", "Middle", "Ring", "Pinky"):
            c.set_source_chain(f"{side}{f}", f"{side}{f}Metacarpal")  # the old FUZZY mapping
    fk = c.get_op_controller(c.get_index_of_op_by_name("FK Chains"))
    s = fk.get_settings()
    chains = list(s.get_editor_property("chains_to_retarget"))
    for ch in chains:
        if any(k in str(ch.get_editor_property("target_chain_name")) for k in ("Thumb", "Index", "Middle", "Ring", "Pinky")):
            ch.set_editor_property("rotation_mode", unreal.FKChainRotationMode.INTERPOLATED)
    s.set_editor_property("chains_to_retarget", chains)
    fk.set_settings(s)
    EAL.save_loaded_asset(rtg, False)
    inputs = unreal.IKRetargetBatchOperationInputs()
    srcs = [EAL.find_asset_data(f"{P}/Source/UAL1/AL_StandardRig_{n}") for n in CLIPS]
    for k, v in (("assets_to_retarget", srcs), ("source_mesh", unreal.load_asset(P + "/Source/UAL1/AL_Standard")),
                 ("target_mesh", unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")),
                 ("ik_retarget_asset", rtg), ("search", "AL_StandardRig_"), ("replace", "UAL_"), ("target_path", QA + "/Before"),
                 ("include_referenced_assets", False), ("overwrite_existing_files", True)):
        inputs.set_editor_property(k, v)
    out = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    for ad in out:
        EAL.save_loaded_asset(ad.get_asset(), False)
    print("before clips:", [str(a.asset_name) for a in out])


run()
