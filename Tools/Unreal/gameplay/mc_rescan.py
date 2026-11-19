"""mech_core: rescan the asset registry for the folders the builders read, after an editor relaunch."""
import unreal

unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
    ["/Game/FoA/Gameplay", "/Game/Input", "/Game/FoA/Characters/Player", "/Game/ThirdPerson"], True)
for p in ("/Game/FoA/Gameplay/BP_BeatDirector", "/Game/FoA/Gameplay/GI_FoA", "/Game/FoA/Characters/Player/BP_FoAPlayer"):
    print(p, unreal.EditorAssetLibrary.does_asset_exist(p))
