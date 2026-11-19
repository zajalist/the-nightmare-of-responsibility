"""Editor B: end any open MetaHuman Creator edit session or asset editor on the face copies, save them, collect garbage."""
import unreal
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
root = "/Game/FoA/Characters/Protagonist/Faces/"
for n in ["MHC_Face_" + f for f in "ABCDEFGHIJKL"] + ["MHC_Protagonist_Backup"]:
    ch = unreal.load_asset(root + n)
    if ch is None:
        continue
    was = SUB.is_object_added_for_editing(ch)
    if was:
        SUB.remove_object_to_edit(ch)
    AES.close_all_editors_for_asset(ch)
    ok = unreal.EditorAssetLibrary.save_asset(root + n, only_if_is_dirty=True)
    print("MH_CLOSE", n, "was_editing", was, "saved", ok)
unreal.SystemLibrary.collect_garbage()
print("MH_CLOSE gc done")
