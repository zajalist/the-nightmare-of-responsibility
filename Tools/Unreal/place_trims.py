"""Imports and places the mitered bedroom trim runs, run INSIDE the open editor:
  python Tools/Unreal/make_procedural_meshes.py          (writes P:/FoA-Assets/procedural/trims/*.gltf + trims.json)
  python Tools/Unreal/ue_remote.py Tools/Unreal/place_trims.py FOA_TRIM_STEP=import,place
  python Tools/Unreal/ue_remote.py Tools/Unreal/place_trims.py FOA_TRIM_STEP=cleanup     (deletes the old straight trims)
  then: python Tools/Unreal/editor_lock.py save_level <owner>   (the script does not save the level)

Meshes are authored in world space, so each actor sits at its run's pivot with identity rotation and scale 1.
Door casings belong to the door lane and are never touched here.
"""
import json
import os
import traceback

import unreal

SRC = "P:/FoA-Assets/procedural/trims"
DEST = "/Game/FoA/Procedural/Trims"
FOLDER = "Room/Trim"
MATS = {"Base": "/Game/FoA/Materials/MI_Trim_Baseboard", "Crown": "/Game/FoA/Materials/MI_Trim_PaintedWood",
        "WinCasing": "/Game/FoA/Materials/MI_Trim_PaintedWood", "WinSill": "/Game/FoA/Materials/MI_Trim_PaintedWood",
        "WinSash": "/Game/FoA/Materials/MI_Trim_PaintedWood", "WinMuntin": "/Game/FoA/Materials/MI_Trim_PaintedWood"}
FALLBACK_MAT = "/Game/FoA/Materials/MI_Trim_Paint"
COLLIDE = {"WinSill", "WinSash", "WinMuntin"}  # the parts they replace blocked queries (BlockAll, QueryOnly): capsule, traces
OLD_PREFIXES = ("Base_", "Crown_", "Casing_window_", "Chimney_Base_", "Chimney_Crown_",
                "Sill_window_", "Sash_window_", "Muntin_window_")   # scaled SM_Sill/FrameBar/Muntin: no UV1, carving on flat faces
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
STEPS = os.environ.get("FOA_TRIM_STEP", "import,place").split(",")
ONLY = [s for s in os.environ.get("FOA_TRIM_ONLY", "").split(",") if s]  # optional mesh-name filter (lane-prefixed: os.environ is shared by every lane's runs)


def manifest():
    runs = json.load(open(f"{SRC}/trims.json", encoding="utf-8"))
    return [r for r in runs if not ONLY or r["mesh"] in ONLY]


def trim_meshes():
    out = {}
    for path in EAL.list_assets(DEST, recursive=True, include_folder=False):
        obj = EAL.load_asset(path)
        if isinstance(obj, unreal.StaticMesh):
            out[obj.get_name()] = obj
    return out


def do_import(runs):
    tasks = []
    for r in runs:
        t = unreal.AssetImportTask()
        for k, v in (("filename", f"{SRC}/{r['mesh']}.gltf"), ("destination_path", DEST), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    meshes = trim_meshes()
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for r in runs:
        sm = meshes.get(r["mesh"])
        if not sm:
            print("WARN import failed", r["mesh"])
            continue
        nanite = sm.get_editor_property("nanite_settings")
        if nanite.get_editor_property("enabled"):
            nanite.set_editor_property("enabled", False)
            sm.set_editor_property("nanite_settings", nanite)
        bs = smes.get_lod_build_settings(sm, 0)
        if bs.get_editor_property("generate_lightmap_u_vs"):  # would overwrite UV1 (the ornament UVs); Lumen needs none
            bs.set_editor_property("generate_lightmap_u_vs", False)
            smes.set_lod_build_settings(sm, 0, bs)
        if r["kind"] in COLLIDE:  # authored meshes carry no simple shapes; bay sides are diagonal, so no AABB box
            sm.get_editor_property("body_setup").set_editor_property(
                "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if smes.get_num_uv_channels(sm, 0) < 2:
            print("WARN no UV1 (ornament) on", r["mesh"])
        EAL.save_loaded_asset(sm)
    print("imported", sum(1 for r in runs if r["mesh"] in meshes), "of", len(runs), "->", DEST)


def material(kind):
    path = MATS.get(kind)
    return (EAL.does_asset_exist(path) and unreal.load_asset(path)) or unreal.load_asset(FALLBACK_MAT)


def do_place(runs):
    meshes = trim_meshes()
    labels = {r["label"] for r in runs}
    EAS.destroy_actors([a for a in EAS.get_all_level_actors() if a.get_actor_label() in labels])  # re-run safe
    placed = 0
    for r in runs:
        sm = meshes.get(r["mesh"])
        if not sm:
            print("WARN missing mesh", r["mesh"])
            continue
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*r["pivot"]), unreal.Rotator(0.0, 0.0, 0.0))
        smc = a.get_editor_property("static_mesh_component")
        smc.set_static_mesh(sm)
        smc.set_material(0, material(r["kind"]))
        if r["kind"] in COLLIDE:
            smc.set_collision_profile_name("BlockAll")
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        else:
            smc.set_collision_profile_name("NoCollision")
        a.set_actor_label(r["label"])
        a.set_folder_path(FOLDER)
        placed += 1
    print("placed", placed, "trim runs in", FOLDER)


def do_cleanup():
    old = [a for a in EAS.get_all_level_actors()
           if str(a.get_folder_path()) in ("Room/Trim", "Room/Chimney", "Room/Windows") and a.get_actor_label().startswith(OLD_PREFIXES)]
    print("deleting", len(old), "old trims:", sorted(a.get_actor_label() for a in old))
    EAS.destroy_actors(old)


try:
    runs = manifest()
    if "import" in STEPS:
        do_import(runs)
    if "place" in STEPS:
        do_place(runs)
    if "cleanup" in STEPS:
        do_cleanup()
    print("TRIMS OK", STEPS)
except Exception:
    print("TRIMS FAILED\n" + traceback.format_exc())
