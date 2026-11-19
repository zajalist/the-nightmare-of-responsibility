"""Animations-only import of one garment's takes onto its EXISTING skeleton, one FBX per take
(Tools/Rig/garment_take_fbx.py: P:/FoA-Assets/character/garments/rig/anim/takes/SK_Garment_<G>Armature_<Take>.fbx).
The classic FBX importer names a single-take anim after its file, so each lands as /Game/FoA/Characters/Garments/
SK_Garment_<G>Armature_<Take>: the existing attack clip is replaced in place (its references hold), the other five are new.
Mesh, skeleton and physics asset are never touched. One garment per run.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/import_garment_anims.py FOA_GARMENT=Shirt"""
import os

import unreal

D = "/Game/FoA/Characters/Garments"
G = os.environ["FOA_GARMENT"]
SRC = "P:/FoA-Assets/character/garments/rig/anim/takes"
TAKES = ["Idle", "Telegraph", {"Shirt": "Lash", "Trousers": "Kick", "Sock": "Hop", "Tie": "CoilStrike"}[G], "HitReact", "Stun", "Defeat"]


def task_for(take, skel):
    ui = unreal.FbxImportUI()
    ui.import_mesh = False
    ui.import_as_skeletal = False
    ui.set_editor_property("original_import_type", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    ui.import_animations = True
    ui.import_materials = False
    ui.import_textures = False
    ui.create_physics_asset = False
    ui.skeleton = skel
    ui.anim_sequence_import_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    t = unreal.AssetImportTask()
    t.filename = f"{SRC}/SK_Garment_{G}Armature_{take}.fbx"
    t.destination_path = D
    t.automated = True
    t.replace_existing = True
    t.save = True
    t.options = ui
    return t


def run():
    skel = unreal.load_asset(f"{D}/SK_Garment_{G}_Skeleton")
    mesh_file = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + f"FoA/Characters/Garments/SK_Garment_{G}.uasset"
    before = os.path.getmtime(mesh_file)
    tasks = [task_for(t, skel) for t in TAKES]
    # Interchange ignores the animation-only options; the classic importer for these tasks only, flag put straight back
    cv = "Interchange.FeatureFlags.Import.FBX"
    unreal.SystemLibrary.execute_console_command(None, f"{cv} 0")
    try:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    finally:
        unreal.SystemLibrary.execute_console_command(None, f"{cv} 1")
    made, wrong = [], []
    for t, task in zip(TAKES, tasks):
        p = f"{D}/SK_Garment_{G}Armature_{t}"
        a = unreal.EditorAssetLibrary.load_asset(p) or (unreal.load_asset(str(task.imported_object_paths[0])) if task.imported_object_paths else None)
        if a and isinstance(a, unreal.AnimSequenceBase):
            made.append((t, round(a.get_play_length(), 2)))
        else:
            wrong.append((t, [str(x) for x in task.imported_object_paths]))
    assert os.path.getmtime(mesh_file) == before, "the mesh was touched"
    print("GARMENT_ANIM_IMPORT", G, made, "problems", wrong)


run()
