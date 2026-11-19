"""After an editor restart the asset registry may not list newer folders: rescan the encounter's (editor-rules)."""
import unreal

unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
    ['/Game/FoA/Gameplay', '/Game/FoA/Lux3D/the_shirt_enemy', '/Game/FoA/Characters/Garments', '/Game/FoA/VFX/Sand',
     '/Game/FoA/Characters/Player', '/Game/FoA/PostProcess'], True)
print('scanned')
