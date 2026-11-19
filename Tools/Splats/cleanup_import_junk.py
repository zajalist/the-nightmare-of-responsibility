"""Interchange makes a material asset for every glTF material it imports, so each sand mesh grew a stray
<mesh>/Materials/M_SplatMesh or M_SandSpill (11 assets, unused: the actors override them). Lean-content rule: delete them.
  python Tools/Unreal/ue_remote.py Tools/Splats/cleanup_import_junk.py FOA_JUNK=retarget   # VFX lease: slots -> real MIs
  python Tools/Unreal/ue_remote.py Tools/Splats/cleanup_import_junk.py FOA_JUNK=delete     # EXCLUSIVE: referencer check, delete
Never both in one run (editor rules: no delete in the run that loads or edits the assets)."""
import os

import unreal

EAL = unreal.EditorAssetLibrary
V, S = "/Game/FoA/VFX/Splats", "/Game/FoA/VFX/Sand"
MESHES = {  # mesh folder -> (mesh path, the material instance its slot should hold)
    f"{S}/Spill/SM_SandSpill_{k}/SM_SandSpill_{k}": f"{S}/MI_SandSpill_Floor" for k in ("Path", "Hearth", "Bay", "Pour")}
MESHES.update({f"{V}/Meshes/SM_SandCrumbs_{k}/SM_SandCrumbs_{k}": f"{V}/Instances/MI_Sand_Crumbs" for k in ("Path", "Hearth", "Bay")})
MESHES.update({f"{V}/Meshes/SM_SandBurst/SM_SandBurst": f"{V}/Instances/MI_Sand_Burst",
               f"{V}/Meshes/SM_SandFaceDrift/SM_SandFaceDrift": f"{V}/Instances/MI_Sand_FaceDrift",
               f"{V}/Meshes/SM_SandMoundSplats_C/SM_SandMoundSplats_C": f"{V}/Instances/MI_Sand_Mound_OnCommode"})
# (the night mare's importer leftover goes with the cleanup lane's batch; its mesh already uses MI_Splat_NightMare)


def junk(folder):
    return [a for a in EAL.list_assets(f"{folder}/Materials", recursive=False) if a.split(".")[0].rsplit("/", 1)[1] in ("M_SplatMesh", "M_SandSpill")]


def retarget():
    for folder, mi in MESHES.items():
        name = folder.rsplit("/", 1)[1]
        mesh_path = f"{folder}/StaticMeshes/{name}"
        if folder.endswith("_import_SM_TheNightMare/SM_TheNightMare"):
            mesh_path = f"{V}/Meshes/SM_TheNightMare"                       # moved by rename_sand_vfx.py
        if not EAL.does_asset_exist(mesh_path) or not EAL.does_asset_exist(mi):
            print("skip", mesh_path)
            continue
        m = unreal.load_asset(mesh_path)
        m.set_material(0, unreal.load_asset(mi))
        EAL.save_asset(mesh_path, only_if_is_dirty=False)
        print("slot", name, "->", mi.rsplit("/", 1)[1])


def delete():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for folder in MESHES:
        for a in junk(folder):
            p = a.split(".")[0]
            refs = [r for r in EAL.find_package_referencers_for_asset(p, False) if r != p]
            if refs:
                print("KEEP (referenced)", p, refs[:3])
                continue
            print("delete", p, EAL.delete_asset(p))
    reg.scan_paths_synchronous([S, V], True)


{"retarget": retarget, "delete": delete}[os.environ.get("FOA_JUNK", "retarget")]()
