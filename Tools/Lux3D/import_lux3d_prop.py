"""Import one Lux3D textured GLB as a prop (world lane): P:/FoA-Assets/lux3d/<item>/textured.glb -> /Game/FoA/Props/<Dest>.
  $env:FOA_AREAS='/Game/FoA/Props'; python Tools/Unreal/ue_remote.py Tools/Lux3D/import_lux3d_prop.py LUX_ITEM=door_lock_plate LUX_DEST=DoorLock/Plate [LUX_TEX=512]
Small props: textures capped at LUX_TEX px (editor rules: 512 for small items), Nanite off. Prints what Interchange made."""
import os

import unreal

EAL = unreal.EditorAssetLibrary


def main():
    item, dest = os.environ['LUX_ITEM'], os.environ['LUX_DEST']
    dest = dest if dest.startswith('/Game/') else '/Game/FoA/Props/' + dest   # a full path, e.g. /Game/FoA/Lux3D/<item>
    cap = int(os.environ.get('LUX_TEX', '512'))
    if not EAL.does_directory_exist(dest) or not EAL.list_assets(dest, recursive=True):
        t = unreal.AssetImportTask()
        for k, v in (('filename', f'P:/FoA-Assets/lux3d/{item}/textured.glb'), ('destination_path', dest), ('automated', True),
                     ('replace_existing', True), ('save', False)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for path in EAL.list_assets(dest, recursive=True, include_folder=False):
        a = EAL.load_asset(path)
        line = f'{a.get_class().get_name()} {path}'
        if isinstance(a, unreal.StaticMesh):
            ns = smes.get_nanite_settings(a)
            ns.set_editor_property('enabled', False)
            smes.set_nanite_settings(a, ns, True)
            b = a.get_bounds()
            line += (f' origin=({b.origin.x:.2f},{b.origin.y:.2f},{b.origin.z:.2f}) size=({2 * b.box_extent.x:.2f},'
                     f'{2 * b.box_extent.y:.2f},{2 * b.box_extent.z:.2f}) tris={a.get_num_triangles(0)}')
        elif isinstance(a, unreal.Texture2D):
            a.set_editor_property('max_texture_size', cap)
            line += f' {a.blueprint_get_size_x()}x{a.blueprint_get_size_y()} srgb={a.get_editor_property("srgb")} cap={cap}'
        elif isinstance(a, unreal.MaterialInstance):
            line += f' parent={a.get_editor_property("parent").get_path_name()}'
        EAL.save_asset(path, only_if_is_dirty=False)
        print(line)


main()
