"""Import the hero skeletal FBX (Manny-named skeleton, own Skeleton asset + physics asset) and save it.

  $env:FOA_AGENT='character'; python Tools/Unreal/editor_lock.py acquire character --ttl 600
  python Tools/Unreal/ue_remote.py Tools/Unreal/import_hero.py FOA_FBX=P:/FoA-Assets/character/v3/hero/SK_Hero.fbx
  python Tools/Unreal/editor_lock.py release character

Creates /Game/FoA/Characters/Hero/SK_Hero (+ SK_Hero_Skeleton, SK_Hero_PhysicsAsset, materials, textures).
Refuses to run if SK_Hero already exists (re-import or delete it in a separate run first).
"""
import os
import unreal


def run():
    fbx = os.environ["FOA_FBX"]
    dest = os.environ.get("FOA_DEST", "/Game/FoA/Characters/Hero")
    name = os.path.splitext(os.path.basename(fbx))[0]
    if unreal.EditorAssetLibrary.does_asset_exist(f"{dest}/{name}"):
        print("FOA_IMPORT skip: exists", f"{dest}/{name}")
        return
    ui = unreal.FbxImportUI()
    ui.import_mesh = True
    ui.import_as_skeletal = True
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_animations = False
    ui.import_materials = True
    ui.import_textures = True
    ui.create_physics_asset = True
    ui.skeleton = None  # its own skeleton, Manny-named
    smd = ui.skeletal_mesh_import_data
    for k in ("update_skeleton_reference_pose", "use_t0_as_ref_pose", "import_morph_targets"):
        try:  # names differ between engine versions (5.8 dropped import_morph_targets)
            smd.set_editor_property(k, False)
        except Exception:
            pass
    smd.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = dest
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    for p in paths:
        unreal.EditorAssetLibrary.save_asset(p.split(".")[0], only_if_is_dirty=False)
    sk = unreal.load_asset(f"{dest}/{name}")
    skel = sk.get_editor_property("skeleton") if sk else None
    pa = sk.get_editor_property("physics_asset") if sk else None
    print("FOA_IMPORT", paths)
    print("FOA_IMPORT skeleton", skel.get_path_name() if skel else None,
          "physics", pa.get_path_name() if pa else None,
          "bounds", sk.get_bounds() if sk else None)


run()
