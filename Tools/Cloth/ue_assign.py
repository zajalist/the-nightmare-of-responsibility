"""Assign the compiled cloth instances to every section of the five teen garments, save, and read back."""
import json
import unreal


def run():
    root = '/Game/FoA/Characters/Teen/'
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([root], True)
    rows = []
    for piece in ('Polo', 'Pants', 'Suit', 'Socks', 'Shoes'):
        path = root + 'Mesh/SK_Teen_' + piece
        mesh = unreal.load_asset(path)
        mat = unreal.load_asset(root + 'Cloth/MI_Teen_' + piece)
        assert mesh and mat, piece
        slots = list(mesh.materials)
        for slot in slots:
            slot.material_interface = mat
        mesh.set_editor_property('materials', slots)
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
        assert all(s.material_interface == mat for s in mesh.materials)
        rows.append({'mesh': path, 'slots': [str(s.material_slot_name) for s in mesh.materials], 'material': mat.get_path_name()})
    for path in unreal.EditorAssetLibrary.list_assets(root + 'Cloth', recursive=True, include_folder=False):
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=True)
    with open('P:/FoA/Saved/ClothShots/teen_material_assignment.json', 'w') as f:
        json.dump(rows, f, indent=2)
    print('TEEN_CLOTH', json.dumps(rows))


run()
