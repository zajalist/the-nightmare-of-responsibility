import unreal
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/FoA/Characters/Teen'],True)
print('TEEN_SCANNED',len(unreal.EditorAssetLibrary.list_assets('/Game/FoA/Characters/Teen')))
