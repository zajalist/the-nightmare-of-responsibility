"""Audit step C: delete the scratch retargets in Teen/Anim/TMP_rig (nothing references them) and any TMP_rig_ actor.
  $env:FOA_EXCLUSIVE='1'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/clip_cleanup.py   (in a PIE window)"""
import unreal

TMP = "/Game/FoA/Characters/Teen/Anim/TMP_rig"
E = unreal.EditorAssetLibrary
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if a.get_actor_label().startswith("TMP_rig_"):
        a.destroy_actor()
gone = []
if E.does_directory_exist(TMP):
    for p in E.list_assets(TMP, recursive=True):
        path = p.split(".")[0]
        # registry-gated (editor-rules): find_package_referencers_for_asset returns [] since the 21:50 relaunch
        refs = [str(r) for r in (unreal.AssetRegistryHelpers.get_asset_registry().get_referencers(
            path, unreal.AssetRegistryDependencyOptions()) or []) if not str(r).startswith(TMP)]
        if refs:
            print("KEEP (referenced)", path, refs)
            continue
        if E.delete_asset(path):
            gone.append(path)
    if not E.list_assets(TMP, recursive=True):
        E.delete_directory(TMP)
print("CLIP_CLEANUP deleted", len(gone), gone)
