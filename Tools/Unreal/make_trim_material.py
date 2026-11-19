"""Painted-wood trim material: textures, instances and cleanup, run INSIDE the open editor:
  python Tools/Unreal/bake_trim_ornament.py
  python Tools/Unreal/ue_remote.py Tools/Unreal/make_trim_material.py FOA_TRIM_STEP=textures|instances|cleanup

The graph of M_PaintedWoodTrim lives in the asset and is edited ONLY with Hayba's C++ material tools (Python graph
edits crashed the editor three times; see editor-rules.md). It is 19 nodes, 205 PS instructions (213 with Scuffed),
against a 198 floor for any lit material in this project (M_Greybox):
- Paint + grain: Mask (T_TrimPaint_Mask on UV0: R grain, G satin roughness, B blotches) x Paint -> BaseColor.
- Scuffs: Saturate(1 - WorldZ * Scuff.G) x (Mask.B x Scuff.R) darkens by Scuff.B and adds Scuff.A roughness.
- Scuffed static switches (default off) pick plain or scuffed colour and roughness.
- Ornament (T_TrimOrnament_N on UV1) -> Normal.
LAYOUT and COMMENTS below are the node positions and comment boxes, for Hayba material_set_node / material_set_comment.
MI_Trim_PaintedWood (crown, window casings) and MI_Trim_Baseboard (darker, Scuffed on).
"""
import os
import traceback

import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
MAT = "/Game/FoA/Materials/M_PaintedWoodTrim"
TEX_DEST = "/Game/FoA/Procedural/Trims"
SRC = "P:/FoA-Assets/procedural"
LC = unreal.LinearColor
# Paint = target linear albedo / 0.5 (the mask's mean R). Scuff = (amount, 1 / fade height cm, darkening, +roughness).
INSTANCES = {
    "MI_Trim_PaintedWood": {"Paint": LC(1.24, 1.20, 1.12, 1), "Scuffed": False},
    "MI_Trim_Baseboard": {"Paint": LC(1.016, 0.984, 0.92, 1), "Scuffed": True, "Scuff": LC(0.75, 0.1, 0.45, 0.25)},
}
# Left to right: Paint box -> Scuffs box -> switch box -> output; colour along y -330, roughness along y 0.
LAYOUT = {
    "TextureSampleParameter2D_4 (Mask)": (-1960, -190), "VectorParameter_1 (Paint)": (-1960, -470),
    "Multiply_6 (colour)": (-1600, -360), "WorldPosition_1": (-1360, -510), "VectorParameter_2 (Scuff)": (-1360, -380),
    "Multiply_7 (Z x 1/height)": (-1120, -500), "OneMinus_1": (-990, -500), "Saturate_2 (fade)": (-880, -500),
    "Multiply_8 (B x amount)": (-1120, 60), "Multiply_9 (scuff mask)": (-780, -190), "Multiply_10 (x darkening)": (-670, -330),
    "OneMinus_2": (-560, -230), "Multiply_11 (worn colour)": (-470, -280), "Multiply_12 (x roughness)": (-670, -60),
    "Add_2 (scuffed roughness)": (-470, 0), "StaticSwitchParameter_0 (colour)": (-300, -390),
    "StaticSwitchParameter_1 (roughness)": (-300, 0), "TextureCoordinate_2 (UV1)": (-1960, 330),
    "TextureSampleParameter2D_5 (Ornament)": (-1720, 300),
}
# (title, one-line description, top-left, size, colour); Show Bubble When Zoomed + Color Bubble on every box.
COMMENTS = [
    ("Paint + grain (UV0, 1 UV = 1 m)", "One packed mask: R grain x Paint = base colour, G = satin roughness. "
     "Replaces three 2k samples and a Noise node.", (-2000, -620), (580, 780), (0.12, 0.26, 0.16)),
    ("Scuffs (baseboard only)", "Mask B blotches x amount, faded out above the toe-kick zone. Scuff = amount, "
     "1/height (cm), darkening, extra roughness.", (-1400, -620), (1050, 780), (0.30, 0.22, 0.10)),
    ("Scuffed switch", "Static: off for the crown and casings, so they compile without the scuff math.",
     (-330, -620), (290, 780), (0.22, 0.22, 0.22)),
    ("Carved ornament (UV1)", "Egg-and-dart on the crown, bead-and-reel on the baseboard, flat elsewhere.",
     (-2000, 190), (580, 400), (0.10, 0.20, 0.35)),
]
SUPERSEDED = [f"/Game/FoA/Textures/white_planks_clean/T_white_planks_clean_{k}" for k in ("Albedo", "Normal", "Roughness", "AO")]
STEP = os.environ.get("FOA_TRIM_STEP", "")


def textures():
    """Re-import the two baked textures (the material picks them up; no graph edit)."""
    TC = unreal.TextureCompressionSettings
    for name, compression in (("T_TrimPaint_Mask", TC.TC_BC7), ("T_TrimOrnament_N", TC.TC_NORMALMAP)):  # BC7: BC1's
        t = unreal.AssetImportTask()                                                                 # 5-bit red bands
        for k, v in (("filename", f"{SRC}/{name}.png"), ("destination_path", TEX_DEST), ("destination_name", name),
                     ("automated", True), ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        tex = unreal.load_asset(f"{TEX_DEST}/{name}")
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", compression)
        EAL.save_loaded_asset(tex)
        print("texture", name)


def instances():
    for name, p in INSTANCES.items():
        inst = unreal.load_asset(f"/Game/FoA/Materials/{name}")
        MEL.set_material_instance_vector_parameter_value(inst, "Paint", p["Paint"])
        if "Scuff" in p:
            MEL.set_material_instance_vector_parameter_value(inst, "Scuff", p["Scuff"])
        MEL.set_material_instance_static_switch_parameter_value(inst, "Scuffed", p["Scuffed"])
        MEL.update_material_instance(inst)
        EAL.save_loaded_asset(inst)
        print("instance", name, "Scuffed", p["Scuffed"])


def cleanup():
    """Lean content: delete the 2k planks textures this material no longer samples, if nothing else does."""
    for path in SUPERSEDED:
        if not EAL.does_asset_exist(path):
            continue
        refs = EAL.find_package_referencers_for_asset(path, False)
        if refs:
            print("KEEP", path, "referenced by", list(refs))
        else:
            print("deleted" if EAL.delete_asset(path) else "FAILED to delete", path)


try:
    {"textures": textures, "instances": instances, "cleanup": cleanup}[STEP]()
    print("TRIM MATERIAL OK", STEP)
except Exception:
    print("TRIM MATERIAL FAILED\n" + traceback.format_exc())
