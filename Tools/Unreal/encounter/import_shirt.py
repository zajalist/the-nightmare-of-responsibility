"""Imports the Lux3D shirt enemy once (P:/FoA-Assets/lux3d/the_shirt_enemy/textured.glb -> /Game/FoA/Lux3D/the_shirt_enemy)
and prints what Interchange made, so the sway material can point at the right textures.
  $env:FOA_AGENT='mech_encounter'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/import_shirt.py"""
import unreal

EAL = unreal.EditorAssetLibrary
SRC = "P:/FoA-Assets/lux3d/the_shirt_enemy/textured.glb"
DEST = "/Game/FoA/Lux3D/the_shirt_enemy"


def main():
    if not EAL.does_directory_exist(DEST) or not EAL.list_assets(DEST, recursive=True):
        t = unreal.AssetImportTask()
        for k, v in (("filename", SRC), ("destination_path", DEST), ("automated", True), ("replace_existing", True),
                     ("save", True)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    for path in EAL.list_assets(DEST, recursive=True, include_folder=False):
        a = EAL.load_asset(path)
        line = f"{a.get_class().get_name()} {path}"
        if isinstance(a, unreal.StaticMesh):
            b = a.get_bounds()
            line += (f" origin=({b.origin.x:.1f},{b.origin.y:.1f},{b.origin.z:.1f}) size=({2 * b.box_extent.x:.1f},"
                     f"{2 * b.box_extent.y:.1f},{2 * b.box_extent.z:.1f}) tris={a.get_num_triangles(0)}"
                     f" mats={[m.material_interface.get_path_name() for m in a.get_editor_property('static_materials')]}")
        elif isinstance(a, unreal.Texture2D):
            line += (f" {a.blueprint_get_size_x()}x{a.blueprint_get_size_y()} srgb={a.get_editor_property('srgb')}"
                     f" group={a.get_editor_property('lod_group')}")
        elif isinstance(a, unreal.MaterialInstance):
            parent = a.get_editor_property('parent')
            line += f" parent={parent.get_path_name() if parent else None} tex=" + str(
                [(str(p.parameter_info.name), p.parameter_value.get_name() if p.parameter_value else None)
                 for p in a.get_editor_property('texture_parameter_values')])
        print(line)


main()
