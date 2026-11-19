"""Import the Lux3D jumpscare monster (P:/FoA-Assets/lux3d/horror/jumpscare_face_a/textured.glb) into
/Game/FoA/Gameplay/Jumpscare/Monster, Nanite off, textures capped at 1024, and print what Interchange made.
  $env:FOA_AREAS='Gameplay'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/import_monster.py
Idempotent: skips the import when the folder already has assets."""
import unreal

EAL = unreal.EditorAssetLibrary
SRC = 'P:/FoA-Assets/lux3d/horror/jumpscare_face_a/textured.glb'
DEST = '/Game/FoA/Gameplay/Jumpscare/Monster'


def main():
    if not EAL.does_directory_exist(DEST) or not EAL.list_assets(DEST, recursive=True):
        t = unreal.AssetImportTask()
        for k, v in (('filename', SRC), ('destination_path', DEST), ('automated', True), ('replace_existing', True), ('save', False)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for path in EAL.list_assets(DEST, recursive=True, include_folder=False):
        a = EAL.load_asset(path)
        line = f'{a.get_class().get_name()} {path}'
        if isinstance(a, unreal.StaticMesh):
            ns = smes.get_nanite_settings(a)
            ns.set_editor_property('enabled', False)
            smes.set_nanite_settings(a, ns, True)
            b = a.get_bounds()
            line += (f' origin=({b.origin.x:.1f},{b.origin.y:.1f},{b.origin.z:.1f}) size=({2 * b.box_extent.x:.1f},'
                     f'{2 * b.box_extent.y:.1f},{2 * b.box_extent.z:.1f}) tris={a.get_num_triangles(0)}')
        elif isinstance(a, unreal.Texture2D):
            a.set_editor_property('max_texture_size', 1024)
            line += f' {a.blueprint_get_size_x()}x{a.blueprint_get_size_y()} srgb={a.get_editor_property("srgb")}'
        elif isinstance(a, unreal.MaterialInstance):
            line += f' parent={a.get_editor_property("parent").get_path_name()}'
        EAL.save_asset(path, only_if_is_dirty=False)
        print(line)


main()
