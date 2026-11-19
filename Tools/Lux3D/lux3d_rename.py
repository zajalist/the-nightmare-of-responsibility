"""Interchange's Lux3D import names (textured / Designer_Logic_PBR / textured_texture_N) to the house convention, flat in
the item folder: SM_Lux3D_<Item>, MI_Lux3D_<Item>, T_Lux3D_<Item>_BaseColor / _MetallicRoughness (the cleanup lane's
set B layout). Renames carry their referencers (placed actors, the MI) along; run it in its own run, after the import.
  $env:FOA_AREAS='/Game/FoA/Lux3D/<item>'; python Tools/Unreal/ue_remote.py Tools/Lux3D/lux3d_rename.py LUX_ITEMS=cold_coffee_mug:CoffeeMug,...
Then save the level (editor_lock.py save_level) if a renamed mesh is placed."""
import os

import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
for spec in os.environ['LUX_ITEMS'].split(','):
    item, name = spec.split(':')
    root = f'/Game/FoA/Lux3D/{item}'
    found = {}
    for p in EAL.list_assets(root, recursive=True, include_folder=False):
        found.setdefault(EAL.load_asset(p).get_class().get_name(), []).append(p.split('.')[0])
    mi_paths = [p for p in found.get('MaterialInstanceConstant', []) if not p.endswith(f'MI_Lux3D_{name}')]
    if mi_paths:
        mi = EAL.load_asset(mi_paths[0])
        for prm, suffix in (('BaseColorTexture', 'BaseColor'), ('MetallicRoughnessTexture', 'MetallicRoughness')):
            t = MEL.get_material_instance_texture_parameter_value(mi, prm)
            dst = f'{root}/T_Lux3D_{name}_{suffix}'
            if t and t.get_path_name().split('.')[0] != dst:
                print('rename', t.get_name(), EAL.rename_asset(t.get_path_name().split('.')[0], dst))
        print('rename MI', EAL.rename_asset(mi_paths[0], f'{root}/MI_Lux3D_{name}'))
    sm = [p for p in found.get('StaticMesh', []) if not p.endswith(f'SM_Lux3D_{name}')]
    if sm:
        print('rename SM', EAL.rename_asset(sm[0], f'{root}/SM_Lux3D_{name}'))
