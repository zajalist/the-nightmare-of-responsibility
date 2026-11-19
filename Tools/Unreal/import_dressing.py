"""Imports the bedroom set-dressing props, run INSIDE the open editor:
  python Tools/Unreal/ue_remote.py Tools/Unreal/import_dressing.py [FOA_ONLY=a,b]

- Rugs built by make_rugs.py (P:/FoA-Assets/dressing/<Rug>/) -> /Game/FoA/Dressing/<Rug>   (re-imported every run)
- Poly Haven CC0 models (P:/FoA-Assets/polyhaven/models/<id>, the 2k glTF when present) -> /Game/FoA/Props/<id>
- Lux3D outputs (P:/FoA-Assets/lux3d/<name>/textured.glb) -> /Game/FoA/Lux3D/<name>
Poly Haven and Lux3D props are imported once; delete the folder to re-import. Prints every mesh's bounds for placement.
"""
import glob
import os

import unreal

EAL = unreal.EditorAssetLibrary
RUGS = ["Rug_Bedside", "Rug_Door"]
PH = ["potted_plant_02", "potted_plant_04", "lantern_chandelier_01", "brass_candleholders", "book_encyclopedia_set_01",
      "mantel_clock_01", "jug_01", "CheeseBox_01", "wicker_basket_02", "wooden_crate_01", "tea_set_01",
      "potted_plant_01", "fishermans_hat"]
LUX = ["curtains", "radiator", "bedside_book_stack", "glass_of_water", "coat_hook_rail"]


def meshes_in(folder):
    found = []
    for path in EAL.list_assets(folder, recursive=True, include_folder=False):
        obj = EAL.load_asset(path)
        if isinstance(obj, unreal.StaticMesh):
            found.append(obj)
    return found


def import_file(src, dest, always=False):
    if not always and EAL.does_directory_exist(dest) and meshes_in(dest):
        return "kept"
    t = unreal.AssetImportTask()
    for k, v in (("filename", src), ("destination_path", dest), ("automated", True), ("replace_existing", True),
                 ("save", True)):
        t.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return "imported"


def jobs():
    for name in RUGS:
        yield name, f"P:/FoA-Assets/dressing/{name}/SM_{name}.gltf", f"/Game/FoA/Dressing/{name}", True
    for asset_id in PH:
        files = sorted(glob.glob(f"P:/FoA-Assets/polyhaven/models/{asset_id}/*.gltf"))
        two_k = [f for f in files if f.endswith("_2k.gltf")]
        yield asset_id, (two_k or files or [""])[0], f"/Game/FoA/Props/{asset_id}", False
    for name in LUX:
        yield name, f"P:/FoA-Assets/lux3d/{name}/textured.glb", f"/Game/FoA/Lux3D/{name}", False


only = [s.strip() for s in os.environ.get("FOA_ONLY", "").split(",") if s.strip()]
for key, src, dest, always in jobs():
    if only and key not in only:
        continue
    if not os.path.exists(src):
        print("MISSING", key, src)
        continue
    status = import_file(src.replace("\\", "/"), dest, always)
    for m in meshes_in(dest):
        b = m.get_bounds()
        o, e = b.origin, b.box_extent
        tris = m.get_num_triangles(0) if hasattr(m, "get_num_triangles") else -1
        mats = [s.get_editor_property("material_slot_name") for s in m.static_materials]
        print(f"{status:<8} {m.get_path_name()} | origin=({o.x:.1f},{o.y:.1f},{o.z:.1f}) "
              f"size=({2 * e.x:.1f},{2 * e.y:.1f},{2 * e.z:.1f}) tris={tris} slots={[str(s) for s in mats]}")
