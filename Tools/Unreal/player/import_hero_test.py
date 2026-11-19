"""Imports the character lane's rigged variant B (mesh + skeleton only, no materials) into a scratch folder so the
hero retarget tooling can be built before SK_Hero lands. Delete /Game/FoA/Characters/Player/_HeroRigTest after."""
import os

import unreal

DEST = "/Game/FoA/Characters/Player/_HeroRigTest"
if not unreal.EditorAssetLibrary.list_assets(DEST):
    pipe = unreal.InterchangeGenericAssetsPipeline()
    mat = pipe.get_editor_property("material_pipeline")
    mat.set_editor_property("import_materials", False)
    mat.get_editor_property("texture_pipeline").set_editor_property("import_textures", False)
    t = unreal.AssetImportTask()
    for k, v in (("filename", os.environ.get("FOA_HERO_GLB", "P:/FoA-Assets/character/v3/hooded_figure_b_retopo_rig/rigged.glb")),
                 ("destination_path", DEST), ("automated", True), ("replace_existing", True), ("save", True),
                 ("options", pipe)):
        t.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
for a in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True):
    print(a, unreal.EditorAssetLibrary.find_asset_data(a).asset_class_path.asset_name)
