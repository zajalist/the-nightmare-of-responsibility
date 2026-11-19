"""Audit step A: retarget the real gameplay clips through RTG_Mannequin_to_Teen into a scratch folder (deleted by
clip_cleanup.py). Writes Saved/RigShots/audit/clip_retarget.json (source -> scratch path, length).
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/clip_retarget.py [FOA_CLIPS=a,b]"""
import json
import os

import unreal

E = unreal.EditorAssetLibrary
TMP = "/Game/FoA/Characters/Teen/Anim/TMP_rig"
A = "/Game/FoA/Characters/Player/Anims/"
CLIPS = {
    "idle": A + "GASP/AS_GASP_M_Relaxed_Stand_Idle_Loop",
    "walk": A + "GASP/AS_GASP_M_Relaxed_Walk_Loop_F",
    "interact": A + "UAL/UAL_Interact",
    "pickup": A + "UAL/UAL_PickUp_Table",
    "kneelwork": A + "Hands/AS_FoA_Kneel_Work",
    "tool": A + "Hands/AS_FoA_Grip_Tool_R",
    "key": A + "Hands/AS_FoA_Grip_Key_R",
    "phone": A + "AS_FoA_PhoneHold",
    "wake_reach": "/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach",
}


def run():
    want = [c for c in os.environ.get("FOA_CLIPS", ",".join(CLIPS)).split(",") if c]
    manny = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
    teen = unreal.load_asset("/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body")
    rtg = unreal.load_asset("/Game/FoA/Characters/Player/Retarget/RTG_Mannequin_to_Teen")
    out = {}
    for key in want:
        src = unreal.load_asset(CLIPS[key])
        if not src or src.get_editor_property("skeleton") != manny.skeleton:
            print("skip", key, "skeleton", src and src.get_editor_property("skeleton").get_path_name())
            continue
        inp = unreal.IKRetargetBatchOperationInputs()
        for k, v in (("assets_to_retarget", [E.find_asset_data(src.get_path_name())]), ("source_mesh", manny),
                     ("target_mesh", teen), ("ik_retarget_asset", rtg), ("target_path", TMP),
                     ("include_referenced_assets", False), ("overwrite_existing_files", True), ("suffix", "_" + key)):
            inp.set_editor_property(k, v)
        res = unreal.IKRetargetBatchOperation.run_batch_retarget(inp)
        tgt = res[0].get_asset() if res else None
        if tgt:
            E.save_loaded_asset(tgt, False)
            out[key] = {"source": src.get_path_name(), "target": tgt.get_path_name(), "length": src.get_play_length()}
            print("retargeted", key, tgt.get_path_name(), round(src.get_play_length(), 2))
    path = "P:/FoA/Saved/RigShots/audit/clip_retarget.json"
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(out)
    json.dump(old, open(path, "w"), indent=1)


run()
