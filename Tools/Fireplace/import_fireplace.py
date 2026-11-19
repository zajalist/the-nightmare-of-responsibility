"""Brings the fireplace into the open editor (run through ue_remote; never touches actors).

  python Tools/Unreal/ue_remote.py Tools/Fireplace/import_fireplace.py FOA_STEPS=textures,material,meshes

- textures: medieval_red_brick 2k (Poly Haven, CC0) + generated/baked T_FP_* -> /Game/FoA/Fireplace/Textures
- material: ONLY the instances MI_FP_{Paint,Iron,Brick,Soot,Tiles,Slate,Coal,Ash}: parent M_Fireplace + parameters.
            The master M_Fireplace itself is built with Hayba's C++ material tools (editor-rules: Python never mutates
            a material graph); this step skips itself until that master exists.
- meshes:   SM_FP_* glTFs (Tools/Fireplace/build_fireplace_blender.py) -> /Game/FoA/Fireplace/Meshes/<name>;
            slots wired to the MIs by slot name, Nanite off, box collision on surround + hearth.
- cleanup:  (run on its own) deletes the importer's unreferenced glTF materials/textures under Meshes/.
Every asset is saved as soon as it is made (crash safety).
"""
import os

import unreal

ROOT = "/Game/FoA/Fireplace"
TEXD, MATD, MESHD = ROOT + "/Textures", ROOT + "/Materials", ROOT + "/Meshes"
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TC = unreal.TextureCompressionSettings
ST = unreal.MaterialSamplerType
MP = unreal.MaterialProperty
STEPS = os.environ.get("FOA_STEPS", "textures,material,meshes").split(",")
BRICK = "P:/FoA-Assets/polyhaven/textures/medieval_red_brick/medieval_red_brick_{}_2k.jpg"
GEN = "P:/FoA-Assets/procedural/fireplace/{}.png"
TEXTURES = [(BRICK.format("diff"), "T_FP_Brick_BaseColor", "color"), (BRICK.format("nor_gl"), "T_FP_Brick_Normal", "normal_gl"),
            (BRICK.format("rough"), "T_FP_Brick_Roughness", "gray")] + \
           [(GEN.format(n), n, k) for n, k in (
               ("T_FP_Hearth_BaseColor", "color"), ("T_FP_Hearth_Normal", "normal"), ("T_FP_Hearth_Roughness", "gray"),
               ("T_FP_Grunge", "mask"), ("T_FP_GrungeNormal", "normal"), ("T_FP_IronNormal", "normal"), ("T_FP_White", "gray"), ("T_FP_MaskNeutral", "mask"),
               ("T_FP_Mask_Surround", "mask"), ("T_FP_Mask_Insert", "mask"), ("T_FP_Mask_Hearth", "mask"))]
MESHES = {"SM_FP_Surround": True, "SM_FP_Hearth": True, "SM_FP_Insert": False, "SM_FP_Firebox": False, "SM_FP_Coal": False}
# slot name -> M_Fireplace parameters. Vectors are (r, g, b, a):
#   Tint a = roughness | WearColor / GrimeColor / SootColor a = their roughness
#   Shape = dirt amount, roughness variation, baked-AO strength, metallic of the worn areas
# The wear/grime/stain themselves are baked into MaskTex (R AO, G wear, B grime, A 1 - stain) per mesh.
GN = "T_FP_GrungeNormal"   # paint: vertical brush marks
IN = "T_FP_IronNormal"     # iron, cinders, slate: casting pits, no streaks
INSTANCES = {
    "Paint": {"Tint": (0.50, 0.485, 0.45, 0.42), "WearColor": (0.11, 0.08, 0.055, 0.75), "GrimeColor": (0.19, 0.15, 0.085, 0.7),
              "Shape": (0.25, 0.15, 0.6, 0.0), "Metallic": 0.0, "NormalTex": GN, "MaskTex": "T_FP_Mask_Surround"},
    "Iron": {"Tint": (0.04, 0.04, 0.042, 0.48), "WearColor": (0.72, 0.72, 0.73, 0.18), "GrimeColor": (0.07, 0.035, 0.018, 0.92),
             "Shape": (0.3, 0.0, 0.7, 1.0), "Metallic": 0.75, "NormalTex": IN, "MaskTex": "T_FP_Mask_Insert"},
    "Slate": {"Tint": (0.034, 0.035, 0.038, 0.5), "WearColor": (0.12, 0.12, 0.13, 0.4), "GrimeColor": (0.02, 0.02, 0.02, 0.8),
              "Shape": (0.3, 0.0, 0.5, 0.0), "NormalTex": IN, "MaskTex": "T_FP_Mask_Hearth"},
    "Tiles": {"BaseColorTex": "T_FP_Hearth_BaseColor", "NormalTex": "T_FP_Hearth_Normal", "RoughnessTex": "T_FP_Hearth_Roughness",
              "MaskTex": "T_FP_Mask_Hearth", "Tint": (1.0, 1.0, 1.0, 1.0), "GrimeColor": (0.02, 0.018, 0.015, 0.85),
              "Shape": (0.12, 0.06, 0.6, 0.0)},
    "Brick": {"BaseColorTex": "T_FP_Brick_BaseColor", "NormalTex": "T_FP_Brick_Normal", "RoughnessTex": "T_FP_Brick_Roughness",
              "Tint": (1.0, 1.0, 1.0, 1.0), "Shape": (0.2, 0.0, 0.0, 0.0), "SootColor": (0.006, 0.0055, 0.005, 0.97)},
    "Soot": {"Tint": (0.004, 0.004, 0.004, 1.0), "Shape": (0.0, 0.0, 0.0, 0.0)},
    "Coal": {"Tint": (0.018, 0.017, 0.016, 0.55), "Shape": (0.4, 0.0, 0.0, 0.0), "NormalTex": IN},
    "Ash": {"Tint": (0.30, 0.29, 0.275, 1.0), "Shape": (0.45, 0.0, 0.0, 0.0)},
}


def log(*a):
    print("[FP]", *a)


def setp(obj, name, value):
    obj.set_editor_property(name, value)


# ------------------------------------------------------------------ textures
def import_textures():
    only = {n for n in os.environ.get("FOA_TEX_ONLY", "").split(",") if n}
    todo = [t for t in TEXTURES if not only or t[1] in only]
    tasks = []
    for src, name, _ in todo:
        t = unreal.AssetImportTask()
        for k, v in (("filename", src), ("destination_path", TEXD), ("destination_name", name), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        tasks.append(t)
    AT.import_asset_tasks(tasks)
    for (src, name, kind), t in zip(todo, tasks):
        tex = unreal.load_asset(f"{TEXD}/{name}")
        if not tex:
            raise RuntimeError("texture import failed: " + src)
        if kind.startswith("normal"):
            setp(tex, "srgb", False)
            setp(tex, "compression_settings", TC.TC_NORMALMAP)
            setp(tex, "flip_green_channel", kind == "normal_gl")  # Poly Haven ships OpenGL normals; ours are DirectX
        elif kind == "gray":
            setp(tex, "srgb", False)
            setp(tex, "compression_settings", TC.TC_GRAYSCALE)
        elif kind == "mask":
            setp(tex, "srgb", False)
            setp(tex, "compression_settings", TC.TC_MASKS)
        EAL.save_loaded_asset(tex)
    log("textures", len(tasks))


# ------------------------------------------------------------------ material instances (Python may set MI parameters only)
MASTER = MATD + "/M_Fireplace"


def build_instances(parent):
    for slot, params in INSTANCES.items():
        name = "MI_FP_" + slot
        full = f"{MATD}/{name}"
        mi = unreal.load_asset(full) if EAL.does_asset_exist(full) else \
            AT.create_asset(name, MATD, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        MEL.clear_all_material_instance_parameters(mi)
        for k, v in params.items():
            if isinstance(v, str):
                MEL.set_material_instance_texture_parameter_value(mi, k, unreal.load_asset(f"{TEXD}/{v}"))
            elif isinstance(v, tuple):
                MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
            else:
                MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
        MEL.update_material_instance(mi)
        EAL.save_loaded_asset(mi)
    log("instances", len(INSTANCES))


# ------------------------------------------------------------------ meshes
def import_meshes():
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for name, solid in MESHES.items():
        dest = f"{MESHD}/{name}"
        t = unreal.AssetImportTask()
        for k, v in (("filename", f"P:/FoA-Assets/blender/Fireplace/{name}.gltf"), ("destination_path", dest),
                     ("automated", True), ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        AT.import_asset_tasks([t])
        assets = EAL.list_assets(dest, recursive=True, include_folder=False)
        sm = next((unreal.load_asset(p) for p in assets if p.split(".")[-1] == name
                   and isinstance(unreal.load_asset(p), unreal.StaticMesh)), None)
        if not sm:
            raise RuntimeError("mesh import failed: " + name + " " + str(assets))
        for i, s in enumerate(sm.get_editor_property("static_materials")):
            slot = str(s.get_editor_property("material_slot_name"))
            mi = unreal.load_asset(f"{MATD}/MI_FP_{slot}")
            if not mi:
                raise RuntimeError(f"no MI for slot {slot} on {name}")
            sm.set_material(i, mi)
        ns = sm.get_editor_property("nanite_settings")  # ~50k tris in all: plain meshes run on low-end PCs too
        if ns.get_editor_property("enabled"):
            ns.set_editor_property("enabled", False)
            sm.set_editor_property("nanite_settings", ns)  # PostEditChange rebuilds LOD0 as the full mesh
        smes.remove_collisions(sm)
        if solid:
            smes.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
        EAL.save_loaded_asset(sm)
        b = sm.get_bounds()
        log(name, "tris", sm.get_num_triangles(0), "uv channels", smes.get_num_uv_channels(sm, 0), "bounds",
            [round(b.origin.x - b.box_extent.x, 1), round(b.origin.y - b.box_extent.y, 1), round(b.origin.z - b.box_extent.z, 1)],
            [round(b.origin.x + b.box_extent.x, 1), round(b.origin.y + b.box_extent.y, 1), round(b.origin.z + b.box_extent.z, 1)])


def cleanup():
    """Separate run (single-writer rule): delete the importer's own glTF materials/textures once nothing references them."""
    for p in EAL.list_assets(MESHD, recursive=True, include_folder=False):
        cls = str(EAL.find_asset_data(p).asset_class_path.asset_name)
        if cls in ("Material", "MaterialInstanceConstant", "Texture2D"):
            pkg = p.split(".")[0]
            refs = [r for r in EAL.find_package_referencers_for_asset(pkg) if r != pkg]
            if refs:
                log("KEEP (referenced)", pkg, refs)
            else:
                log("deleted", pkg, EAL.delete_asset(pkg))


unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([ROOT], True)  # editor may have just relaunched
for d in (ROOT, TEXD, MATD, MESHD):
    EAL.make_directory(d)
if "textures" in STEPS:
    import_textures()
if "material" in STEPS:
    if EAL.does_asset_exist(MASTER):
        build_instances(unreal.load_asset(MASTER))
    else:
        log("SKIP material instances: build", MASTER, "with Hayba first")
if "meshes" in STEPS:
    import_meshes()
if "cleanup" in STEPS:
    cleanup()
log("done", STEPS)
