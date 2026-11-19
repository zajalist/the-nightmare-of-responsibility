"""Read-only probe: shading-model support (Substrate) and stand-in skinned meshes for the cloth lane."""
import unreal
sl = unreal.SystemLibrary
for cv in ("r.Substrate", "r.Material.EnergyConservation", "r.DynamicGlobalIlluminationMethod"):
    print("CVAR", cv, sl.get_console_variable_int_value(cv))
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for p in ("/Game/Characters/Mannequins/Meshes", "/Game/FoA/Characters"):
    for a in ar.get_assets_by_path(p, recursive=True):
        if str(a.asset_class_path.asset_name) in ("SkeletalMesh", "Skeleton"):
            print("ASSET", a.package_name, a.asset_class_path.asset_name)
