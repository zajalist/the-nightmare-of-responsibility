"""Import one SK_Teen_* FBX (from Tools/MPFB/export_ue.py) into /Game/FoA/Characters/Teen/Mesh/.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/MPFB/ue_import_teen.py FOA_FBX=<SK_Teen_X.fbx>
SK_Teen_Body goes first: it creates SK_Teen_Body_Skeleton (+ physics asset). Every other piece imports onto that
skeleton, so the head, hair and garments can follow the body. Morph targets are kept (the head's face units),
normals come from the FBX (no seam at the neck split), and placeholder materials/textures come from the FBX.
Existing assets are skipped, never overwritten."""
import os

import unreal

DEST = "/Game/FoA/Characters/Teen/Mesh"
BODY = DEST + "/SK_Teen_Body"


def run():
    fbx = os.environ["FOA_FBX"]
    name = os.path.splitext(os.path.basename(fbx))[0]
    if unreal.EditorAssetLibrary.does_asset_exist(f"{DEST}/{name}"):
        print("FOA_TEEN skip: exists", f"{DEST}/{name}")
        return
    is_body = name == "SK_Teen_Body"
    ui = unreal.FbxImportUI()
    ui.import_mesh = True
    ui.import_as_skeletal = True
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_animations = False
    ui.import_materials = True
    ui.import_textures = True
    ui.create_physics_asset = is_body
    if not is_body:
        body = unreal.load_asset(BODY)
        if body is None:
            raise RuntimeError("import SK_Teen_Body first")
        ui.skeleton = body.skeleton
    data = ui.skeletal_mesh_import_data
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property("import_morph_targets", True)
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = DEST
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    for p in paths:
        unreal.EditorAssetLibrary.save_asset(p.split(".")[0], only_if_is_dirty=False)
    mesh = unreal.load_asset(f"{DEST}/{name}")
    info = ""
    if isinstance(mesh, unreal.SkeletalMesh):
        info = f"skeleton={mesh.skeleton.get_path_name()} morphs={len(mesh.morph_targets)} materials={len(mesh.materials)}"
    print("FOA_TEEN", name, info, paths)


run()
