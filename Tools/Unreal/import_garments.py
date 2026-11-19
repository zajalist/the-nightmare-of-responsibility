"""Import rigged garment FBXs (own skeleton + physics asset + their animation takes) and save them.

  python Tools/Unreal/ue_remote.py Tools/Unreal/import_garments.py FOA_FBX=<a.fbx>,<b.fbx> [FOA_DEST=/Game/...]
      [FOA_SKELETON=/Game/.../Skeleton]   (worn layers: bind to the body's skeleton, no physics asset)

Each FBX becomes <dest>/<Name> (SkeletalMesh) + <Name>_Skeleton + <Name>_PhysicsAsset + one AnimSequence per take
(Lash / Kick / CoilStrike / Hop). Existing assets are skipped, never overwritten. Run inside the editor lock.
"""
import os
import unreal


def body_skeleton():
    """FOA_SKELETON: a Skeleton path, or auto:<folder> = the skeleton of the first SkeletalMesh named *Body* there."""
    skel = os.environ.get("FOA_SKELETON", "")
    if not skel.startswith("auto:"):
        return unreal.load_asset(skel) if skel else None
    folder = skel[5:]
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([folder], True)
    for a in unreal.EditorAssetLibrary.list_assets(folder, recursive=True):
        if "body" in os.path.basename(a).lower():
            o = unreal.load_asset(a)
            if isinstance(o, unreal.SkeletalMesh):
                print("FOA_GARMENT skeleton from", a, o.skeleton.get_path_name())
                return o.skeleton
    raise RuntimeError(f"no *Body* SkeletalMesh in {folder}")


def import_one(fbx, dest):
    name = os.path.splitext(os.path.basename(fbx))[0]
    if unreal.EditorAssetLibrary.does_asset_exist(f"{dest}/{name}"):
        print("FOA_GARMENT skip: exists", f"{dest}/{name}")
        return
    ui = unreal.FbxImportUI()
    ui.import_mesh = True
    ui.import_as_skeletal = True
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_animations = True
    ui.import_materials = True
    ui.import_textures = True
    ui.create_physics_asset = not os.environ.get("FOA_SKELETON")  # worn layers follow the body: no physics
    ui.skeleton = body_skeleton()  # worn garments: the protagonist's body skeleton, for Leader Pose
    ui.skeletal_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    # 5.8: bone tracks always import (import_bone_tracks was removed)
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
    print("FOA_GARMENT", name, paths)


def run():
    dest = os.environ.get("FOA_DEST", "/Game/FoA/Characters/Garments")
    for fbx in os.environ["FOA_FBX"].split(","):
        import_one(fbx, dest)


run()
