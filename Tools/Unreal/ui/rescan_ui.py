"""After an editor restart the asset registry may not list /Game/FoA/UI (does_asset_exist -> False). Rescan it."""
import unreal
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/FoA/UI', '/Game/FoA/Gameplay',
                                                                         '/Game/FoA/PostProcess'], True)
print('rescanned', len(unreal.EditorAssetLibrary.list_assets('/Game/FoA/UI', recursive=True)))
