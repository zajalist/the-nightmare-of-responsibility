"""Lean content: deletes this lane's superseded assets, each only if nothing references it any more (checked in this run,
editors closed first). Run alone, EXCLUSIVE (deletes), never in the run that edits them.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/delete_superseded.py FOA_EXCLUSIVE=1
BS_FoA_Walk / BS_FoA_Jog: blend spaces whose Python-set samples evaluated the reference pose (replaced by a rate-driven
sequence player). UAL_Walk_Loop / UAL_Jog_Fwd_Loop: used only by BS_FoA_Jog."""
import unreal

EAL = unreal.EditorAssetLibrary
D = "/Game/FoA/Characters/Player/Anims"
ORDER = [D + "/BS_FoA_Walk", D + "/BS_FoA_Jog", D + "/UAL/UAL_Walk_Loop", D + "/UAL/UAL_Jog_Fwd_Loop"]
gone = set()
for p in ORDER:
    if not EAL.does_asset_exist(p):
        continue
    refs = [r for r in EAL.find_package_referencers_for_asset(p, False) if r not in gone]
    if refs:
        print("KEEP", p, "referenced by", refs)
        continue
    a = unreal.load_asset(p)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
    a = None
    ok = EAL.delete_asset(p)
    print("DELETE", p, ok)
    if ok:
        gone.add(p)
