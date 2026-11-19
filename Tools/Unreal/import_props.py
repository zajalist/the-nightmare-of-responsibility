"""Imports sourced glTF props into /Game/FoA/Props/<asset_id>/ and logs every static mesh's bounds.
  UnrealEditor.exe P:/FoA/FoA.uproject -ExecutePythonScript="P:/FoA/Tools/Unreal/import_props.py"
Source files live outside the repo in P:/FoA-Assets (see its MANIFEST.md for licenses: Poly Haven = CC0).
Pass a subset with the FOA_PROPS env var, comma-separated; default is every folder under the source root."""
import os
import traceback

import unreal

SRC_ROOT = "P:/FoA-Assets/polyhaven/models"
DEST_ROOT = "/Game/FoA/Props"
LINES = []


def log(*parts):
    msg = " ".join(str(p) for p in parts)
    LINES.append(msg)
    unreal.log("[FoA] " + msg)


def gltf_for(asset_dir):
    files = [f for f in os.listdir(asset_dir) if f.lower().endswith((".gltf", ".glb"))]
    return os.path.join(asset_dir, sorted(files)[0]).replace("\\", "/") if files else None


def main():
    wanted = [p.strip() for p in os.environ.get("FOA_PROPS", "").split(",") if p.strip()]
    ids = wanted or sorted(d for d in os.listdir(SRC_ROOT) if os.path.isdir(os.path.join(SRC_ROOT, d)))
    tasks = []
    for asset_id in ids:
        src = gltf_for(os.path.join(SRC_ROOT, asset_id))
        if not src:
            log("SKIP no gltf for", asset_id)
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", src)
        t.set_editor_property("destination_path", f"{DEST_ROOT}/{asset_id}")
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", True)
        tasks.append((asset_id, t))
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t for _, t in tasks])

    for asset_id, t in tasks:
        folder = f"{DEST_ROOT}/{asset_id}"
        meshes = []
        for path in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
            obj = unreal.EditorAssetLibrary.load_asset(path)
            if isinstance(obj, unreal.StaticMesh):
                b = obj.get_bounds()
                o, e = b.origin, b.box_extent
                meshes.append(obj)
                log(f"MESH {asset_id} | {obj.get_path_name()} | origin=({o.x:.1f},{o.y:.1f},{o.z:.1f}) "
                    f"size=({2*e.x:.1f},{2*e.y:.1f},{2*e.z:.1f}) mats={len(obj.static_materials)}")
        log(f"IMPORTED {asset_id}: {len(meshes)} static mesh(es)")
    unreal.EditorAssetLibrary.save_directory(DEST_ROOT, only_if_is_dirty=False, recursive=True)


try:
    main()
    log("IMPORT OK")
except Exception:
    log("IMPORT FAILED\n" + traceback.format_exc())
finally:
    with open(os.path.join(unreal.Paths.project_saved_dir(), "FoA_import_props.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
