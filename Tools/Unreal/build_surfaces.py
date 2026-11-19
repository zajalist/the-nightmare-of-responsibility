"""Room surface material instances on M_Surface. Runs INSIDE the open editor, holding the editor lock:

  python Tools/Unreal/ue_remote.py Tools/Unreal/build_surfaces.py FOA_PHASE=instances
      points MI_Wall_Plaster, MI_Ceiling_Plaster and MI_Floor_OldWood at M_Surface with calibrated values
      (MI_Brick was dropped: the fireplace lane uses its own T_FP_Brick_* set).
  python Tools/Unreal/ue_remote.py Tools/Unreal/build_surfaces.py FOA_PHASE=revert_walls
      puts MI_Wall_Plaster back on M_WorldAligned exactly as the user accepted it.

The graphs (/Game/FoA/Materials/M_Surface, /Game/FoA/Materials/Functions/MF_BoxProjectUV) are edited ONLY with Hayba's
C++ material tools (editor-rules.md): emptying a live function from Python recompiled its materials mid-edit and crashed
the shared editor. Why M_Surface exists: M_WorldAligned picked a WORLD axis with Round(abs(normal)), so on the bay walls
(yaw +-123.7) two axes won and the texture smeared, and its normal maps went into a mismatched tangent frame.
MF_BoxProjectUV projects in the object's own axes (exact cm on any rotated box) and M_Surface transforms the normal map
through that same frame. Texel density: 2k maps of ~2 m real tiles, TileSize = tile mm / 10 -> ~1024 px/m.
"""
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import build_bedroom as B  # noqa: E402  (helper library; importing does not rebuild anything)

EAL, AT, MEL = B.EAL, B.AT, B.MEL
MATS = "/Game/FoA/Materials"
TEX = "/Game/FoA/Textures"
LOG = []


def log(*p):
    LOG.append(" ".join(str(x) for x in p))

# ---------- instances ----------

SETS = {  # Poly Haven set -> (TileSize cm = API real-world tile, measured mean linear luminance of the 2k diffuse)
    "plastered_wall": (200.0, 0.397),
    "white_stucco": (199.8, 0.656),
    "old_wooden_floor_02": (203.0, 0.042),
}
# name: (set, Tint = target mean linear albedo, AlbedoDetail, Microsurface, Breakup, Projection G/B)
# Walls/ceiling match the look the user accepted on M_WorldAligned (0.8 / 0.9 x texture mean, authored contrast and
# roughness): stronger contrast + macro blotches read as "messed up" plaster in B&W, so they stay near neutral.
INSTANCES = {
    "MI_Wall_Plaster": ("plastered_wall", 0.318, (1.0, 0, 0), (0.0, 1.0, 0.0, 1.0), (0.06, 0.03, 50.0, 0.0), (0, 0)),
    "MI_Ceiling_Plaster": ("white_stucco", 0.59, (1.0, 0, 0), (0.0, 1.0, 0.0, 1.0), (0.05, 0.03, 40.0, 0.0), (0, 0)),
    "MI_Floor_OldWood": ("old_wooden_floor_02", 0.075, (1.1, 0, 0), (0.0, 0.85, -0.2, 1.0), (0.3, 0.2, 40.0, 0.0), (0, 0)),
}


def instances():
    parent = unreal.load_asset(f"{MATS}/M_Surface")
    if not parent:
        raise RuntimeError("M_Surface missing (it is built with Hayba's material tools)")
    for s in SETS:  # Poly Haven ships OpenGL (Y+) normals; Unreal expects DirectX (Y-): flip with Hayba texture_set_settings
        t = unreal.load_asset(f"{TEX}/{s}/T_{s}_Normal")
        if t and not t.get_editor_property("flip_green_channel"):
            log("WARN not flipped yet (use Hayba texture_set_settings):", t.get_name())
    LC = unreal.LinearColor
    for name, (s, tint, det, mic, brk, prj) in INSTANCES.items():
        full = f"{MATS}/{name}"
        mi = unreal.load_asset(full) if EAL.does_asset_exist(full) else \
            AT.create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        MEL.clear_all_material_instance_parameters(mi)  # drop M_WorldAligned's stale TileSize/Tint scalars
        tile, mean = SETS[s]
        for k in ("Albedo", "Normal", "Roughness", "AO"):
            MEL.set_material_instance_texture_parameter_value(mi, k, unreal.load_asset(f"{TEX}/{s}/T_{s}_{k}"))
        for k, v in (("Projection", LC(tile, prj[0], prj[1], 0)), ("Tint", LC(tint, tint, tint, 1)),
                     ("AlbedoDetail", LC(mean, det[0], 0, 0)), ("Microsurface", LC(*mic)), ("Breakup", LC(*brk))):
            MEL.set_material_instance_vector_parameter_value(mi, k, v)
        MEL.update_material_instance(mi)
        EAL.save_loaded_asset(mi)
        log("instance", name, "->", s, f"TileSize {tile} = {2048 / (tile / 100):.0f} px/m")


def revert_walls():
    """Fallback: MI_Wall_Plaster exactly as the user accepted it (M_WorldAligned, plastered_wall 2k, TileSize 200, Tint 0.8)."""
    mi = unreal.load_asset(f"{MATS}/MI_Wall_Plaster")
    MEL.set_material_instance_parent(mi, unreal.load_asset(f"{MATS}/M_WorldAligned"))
    MEL.clear_all_material_instance_parameters(mi)
    for k in ("Albedo", "Normal", "Roughness", "AO"):
        MEL.set_material_instance_texture_parameter_value(mi, k, unreal.load_asset(f"{TEX}/plastered_wall/T_plastered_wall_{k}"))
    MEL.set_material_instance_scalar_parameter_value(mi, "TileSize", 200.0)
    MEL.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(0.8, 0.8, 0.8, 1.0))
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    log("MI_Wall_Plaster reverted to M_WorldAligned (for the exact accepted look also unflip T_plastered_wall_Normal with Hayba)")


def main():  # asset references stay inside functions (single-writer protocol)
    phase = os.environ.get("FOA_PHASE", "instances")
    if phase == "instances":
        instances()
    elif phase == "revert_walls":
        revert_walls()


main()
print("\n".join(LOG) or "ok")
