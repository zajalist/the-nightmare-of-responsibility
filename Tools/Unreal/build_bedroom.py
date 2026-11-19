"""Builds the tutorial bedroom greybox, the dream post process and the base materials.

Run from a shell (the editor opens, builds, saves and quits):
  UnrealEditor.exe P:/FoA/FoA.uproject -ExecutePythonScript="P:/FoA/Tools/Unreal/build_bedroom.py"

Re-running deletes and rebuilds /Game/FoA/Maps/L_Tutorial_Bedroom and every asset this script makes.
Hand-made changes to those assets are lost on a re-run, so once the level is being edited by hand, stop re-running this.

Units: centimeters. Room interior is X -300..300 (6 m), Y -250..250 (5 m), height 280.
+X wall has the bedroom door, -Y wall has the window, +Y wall has the dresser, -X wall has the desk.
"""
import math
import os
import traceback

import unreal

LINES = []


def log(*parts):
    msg = " ".join(str(p) for p in parts)
    LINES.append(msg)
    unreal.log("[FoA] " + msg)


AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

ROOT = "/Game/FoA"
MATS = ROOT + "/Materials"
PPDIR = ROOT + "/PostProcess"
MAPS = ROOT + "/Maps"
LEVEL = MAPS + "/L_Tutorial_Bedroom"
FALLBACK_LEVEL = "/Game/ThirdPerson/Lvl_ThirdPerson"
MP = unreal.MaterialProperty


# ---------- helpers ----------

def setp(obj, names, value, quiet=False):
    names = [names] if isinstance(names, str) else names
    err = None
    for n in names:
        try:
            obj.set_editor_property(n, value)
            return True
        except Exception as e:  # property names drift between engine versions
            err = e
    if not quiet:
        log("WARN could not set", names, "on", obj.get_name(), "->", err)
    return False


def enum(enum_cls, *names):
    for n in names:
        if hasattr(enum_cls, n):
            return getattr(enum_cls, n)
    members = [m for m in dir(enum_cls) if m.isupper()]
    raise AttributeError(f"{enum_cls.__name__} has none of {names}; members: {members}")


def fresh(name, path, cls, factory):
    full = f"{path}/{name}"
    if EAL.does_asset_exist(full) and not EAL.delete_asset(full):
        raise RuntimeError("could not delete " + full)
    asset = AT.create_asset(name, path, cls, factory)
    if asset is None:
        raise RuntimeError("create_asset failed for " + full)
    return asset


def expr(mat, cls, x, y, **props):
    e = MEL.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        setp(e, k, v)
    return e


def link(a, a_out, b, b_in):
    if not MEL.connect_material_expressions(a, a_out, b, b_in):
        log("WARN link failed", a.get_name(), repr(a_out), "->", b.get_name(), repr(b_in))


def out(e, prop):
    if not MEL.connect_material_property(e, "", prop):
        log("WARN property link failed", e.get_name(), "->", prop)


def rgb_mask(mat, src, src_out, x, y):
    m = expr(mat, unreal.MaterialExpressionComponentMask, x, y, r=True, g=True, b=True, a=False)
    link(src, src_out, m, "")
    return m


# ---------- materials ----------

def make_mpc():
    name, full = "MPC_Dream", PPDIR + "/MPC_Dream"
    if EAL.does_asset_exist(full):
        EAL.delete_asset(full)
    factory = getattr(unreal, "MaterialParameterCollectionFactoryNew", None)
    mpc = AT.create_asset(name, PPDIR, unreal.MaterialParameterCollection, factory() if factory else None)
    scalars = []
    for pname, value in [("ColorReveal", 0.0)]:
        p = unreal.CollectionScalarParameter()
        p.set_editor_property("parameter_name", pname)
        p.set_editor_property("default_value", value)
        scalars.append(p)
    vectors = []
    # Tutorial starts as a cold night: blue-grey shadows, faintly warm (lamp) highlights.
    # The story drifts these two tints a little per beat; keep them close to white.
    for pname, value in [("ShadowTint", unreal.LinearColor(0.90, 0.95, 1.00, 1.0)),
                         ("HighlightTint", unreal.LinearColor(1.00, 0.98, 0.94, 1.0))]:
        p = unreal.CollectionVectorParameter()
        p.set_editor_property("parameter_name", pname)
        p.set_editor_property("default_value", value)
        vectors.append(p)
    mpc.set_editor_property("scalar_parameters", scalars)
    mpc.set_editor_property("vector_parameters", vectors)
    log("MPC_Dream created")
    return mpc


def make_pp_material(mpc):
    m = fresh("M_PP_DreamMono", PPDIR, unreal.Material, unreal.MaterialFactoryNew())
    setp(m, "material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    setp(m, "blendable_location", enum(unreal.BlendableLocation,
                                       "BL_SCENE_COLOR_AFTER_TONEMAPPING", "BL_AFTER_TONEMAPPING"))

    ppi = expr(m, unreal.MaterialExpressionSceneTexture, -1400, -300,
               scene_texture_id=enum(unreal.SceneTextureId, "PPI_POST_PROCESS_INPUT0"))
    scene_rgb = rgb_mask(m, ppi, "Color", -1150, -300)

    weights = expr(m, unreal.MaterialExpressionConstant3Vector, -1150, -150,
                   constant=unreal.LinearColor(0.2126, 0.7152, 0.0722, 1.0))
    lum = expr(m, unreal.MaterialExpressionDotProduct, -950, -220)
    link(scene_rgb, "", lum, "A")
    link(weights, "", lum, "B")
    lum01 = expr(m, unreal.MaterialExpressionSaturate, -800, -120)
    link(lum, "", lum01, "")

    shadow = expr(m, unreal.MaterialExpressionCollectionParameter, -1150, 50,
                  collection=mpc, parameter_name="ShadowTint")
    high = expr(m, unreal.MaterialExpressionCollectionParameter, -1150, 170,
                collection=mpc, parameter_name="HighlightTint")
    tint = expr(m, unreal.MaterialExpressionLinearInterpolate, -800, 80)
    link(rgb_mask(m, shadow, "", -950, 50), "", tint, "A")
    link(rgb_mask(m, high, "", -950, 170), "", tint, "B")
    link(lum01, "", tint, "Alpha")
    mono = expr(m, unreal.MaterialExpressionMultiply, -600, -100)
    link(lum, "", mono, "A")
    link(tint, "", mono, "B")

    stencil = expr(m, unreal.MaterialExpressionSceneTexture, -1400, 350,
                   scene_texture_id=enum(unreal.SceneTextureId, "PPI_CUSTOM_STENCIL"))
    stencil_r = expr(m, unreal.MaterialExpressionComponentMask, -1150, 350, r=True, g=False, b=False, a=False)
    link(stencil, "Color", stencil_r, "")
    keep_color = expr(m, unreal.MaterialExpressionSaturate, -950, 350)
    link(stencil_r, "", keep_color, "")
    reveal = expr(m, unreal.MaterialExpressionCollectionParameter, -1150, 480,
                  collection=mpc, parameter_name="ColorReveal")
    mask = expr(m, unreal.MaterialExpressionMax, -800, 400)
    link(keep_color, "", mask, "A")
    link(reveal, "", mask, "B")

    final = expr(m, unreal.MaterialExpressionLinearInterpolate, -400, 0)
    link(mono, "", final, "A")
    link(scene_rgb, "", final, "B")
    link(mask, "", final, "Alpha")
    out(final, MP.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    log("M_PP_DreamMono created")
    return m


def make_greybox_master():
    m = fresh("M_Greybox", MATS, unreal.Material, unreal.MaterialFactoryNew())
    col = expr(m, unreal.MaterialExpressionVectorParameter, -700, -200,
               parameter_name="Color", default_value=unreal.LinearColor(0.3, 0.3, 0.3, 1.0))
    rough = expr(m, unreal.MaterialExpressionScalarParameter, -700, 0, parameter_name="Roughness", default_value=0.7)
    metal = expr(m, unreal.MaterialExpressionScalarParameter, -700, 100, parameter_name="Metallic", default_value=0.0)
    emis = expr(m, unreal.MaterialExpressionScalarParameter, -700, 200, parameter_name="Emissive", default_value=0.0)
    glow = expr(m, unreal.MaterialExpressionMultiply, -400, 200)
    link(col, "", glow, "A")
    link(emis, "", glow, "B")
    out(col, MP.MP_BASE_COLOR)
    out(rough, MP.MP_ROUGHNESS)
    out(metal, MP.MP_METALLIC)
    out(glow, MP.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    return m


def make_sand_master():
    m = fresh("M_DarkSand", MATS, unreal.Material, unreal.MaterialFactoryNew())
    black = expr(m, unreal.MaterialExpressionVectorParameter, -1000, -300,
                 parameter_name="SandColor", default_value=unreal.LinearColor(0.006, 0.0055, 0.005, 1.0))
    sandy = expr(m, unreal.MaterialExpressionVectorParameter, -1000, -150,
                 parameter_name="SandyColor", default_value=unreal.LinearColor(0.50, 0.38, 0.22, 1.0))
    amount = expr(m, unreal.MaterialExpressionScalarParameter, -1000, 0, parameter_name="Sandy", default_value=0.0)
    base = expr(m, unreal.MaterialExpressionLinearInterpolate, -700, -200)
    link(black, "", base, "A")
    link(sandy, "", base, "B")
    link(amount, "", base, "Alpha")
    grain = expr(m, unreal.MaterialExpressionNoise, -1000, 150, scale=1.6, levels=1, output_min=0.55, output_max=1.45)
    col = expr(m, unreal.MaterialExpressionMultiply, -450, -150)
    link(base, "", col, "A")
    link(grain, "", col, "B")
    wet = expr(m, unreal.MaterialExpressionNoise, -1000, 380, scale=0.02, levels=3, output_min=0.15, output_max=0.65)
    spec = expr(m, unreal.MaterialExpressionConstant, -450, 150, r=0.65)
    out(col, MP.MP_BASE_COLOR)
    out(wet, MP.MP_ROUGHNESS)
    out(spec, MP.MP_SPECULAR)
    MEL.recompile_material(m)
    return m


def make_instance(name, parent, vectors=None, scalars=None, textures=None):
    inst = fresh(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(inst, parent)
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(inst, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(inst, k, v)
    for k, v in (textures or {}).items():
        MEL.set_material_instance_texture_parameter_value(inst, k, v)
    MEL.update_material_instance(inst)
    return inst


TEX_SRC = "P:/FoA-Assets/polyhaven/textures"  # CC0, see MANIFEST.md there


def import_texture_set(set_id, max_size=0):
    """Imports a Poly Haven 2k texture set (diff / nor_gl / rough / ao) as T_<set>_<Kind> with correct settings."""
    folder = f"{ROOT}/Textures/{set_id}"
    tasks = []
    for kind, suffix in (("Albedo", "diff"), ("Normal", "nor_gl"), ("Roughness", "rough"), ("AO", "ao")):
        src = f"{TEX_SRC}/{set_id}/{set_id}_{suffix}_2k.jpg"
        if not os.path.exists(src):
            log("WARN missing texture", src)
            continue
        t = unreal.AssetImportTask()
        for k, v in (("filename", src), ("destination_path", folder), ("destination_name", f"T_{set_id}_{kind}"),
                     ("automated", True), ("replace_existing", True), ("save", True)):
            t.set_editor_property(k, v)
        tasks.append((kind, t))
    AT.import_asset_tasks([t for _, t in tasks])
    TC = unreal.TextureCompressionSettings
    out = {}
    for kind, t in tasks:
        paths = t.get_editor_property("imported_object_paths")
        if not paths:
            log("WARN texture import failed", set_id, kind)
            continue
        tex = unreal.load_asset(paths[0])
        if kind == "Normal":
            setp(tex, "srgb", False)
            setp(tex, "compression_settings", enum(TC, "TC_NORMALMAP"))
            setp(tex, "flip_green_channel", True)  # Poly Haven nor_gl is OpenGL (Y+); Unreal wants DirectX (Y-)
        elif kind in ("Roughness", "AO"):
            setp(tex, "srgb", False)
            setp(tex, "compression_settings", enum(TC, "TC_GRAYSCALE"))
        if max_size:
            setp(tex, "max_texture_size", max_size)  # budget: < 1 GB build
        EAL.save_loaded_asset(tex)
        out[kind] = tex
    return out


def make_world_aligned_master(defaults):
    """Textures projected in world space by the dominant normal axis, so scaled boxes never stretch UVs."""
    m = fresh("M_WorldAligned", MATS, unreal.Material, unreal.MaterialFactoryNew())
    wp = expr(m, unreal.MaterialExpressionWorldPosition, -1700, 0)
    tile = expr(m, unreal.MaterialExpressionScalarParameter, -1700, 150, parameter_name="TileSize", default_value=200.0)
    scaled = expr(m, unreal.MaterialExpressionDivide, -1500, 0)
    link(wp, "", scaled, "A")
    link(tile, "", scaled, "B")

    def mask(src, r, g, b, x, y):
        e = expr(m, unreal.MaterialExpressionComponentMask, x, y, r=r, g=g, b=b, a=False)
        link(src, "", e, "")
        return e

    uv_x = mask(scaled, False, True, True, -1300, -150)   # faces pointing along X use YZ
    uv_y = mask(scaled, True, False, True, -1300, 0)      # faces pointing along Y use XZ
    uv_z = mask(scaled, True, True, False, -1300, 150)    # floors and ceilings use XY
    normal_ws = expr(m, unreal.MaterialExpressionVertexNormalWS, -1700, 350)

    def axis_pick(r, g, b, x, y):  # 1 when that axis dominates (geometry here is axis-aligned)
        c = mask(normal_ws, r, g, b, x, y)
        a = expr(m, unreal.MaterialExpressionAbs, x + 150, y)
        link(c, "", a, "")
        rnd = expr(m, unreal.MaterialExpressionRound, x + 300, y)
        link(a, "", rnd, "")
        return rnd

    pick_y = axis_pick(False, True, False, -1500, 300)
    pick_z = axis_pick(False, False, True, -1500, 420)
    side = expr(m, unreal.MaterialExpressionLinearInterpolate, -1000, -60)
    link(uv_x, "", side, "A")
    link(uv_y, "", side, "B")
    link(pick_y, "", side, "Alpha")
    uv = expr(m, unreal.MaterialExpressionLinearInterpolate, -850, 60)
    link(side, "", uv, "A")
    link(uv_z, "", uv, "B")
    link(pick_z, "", uv, "Alpha")

    S = unreal.MaterialSamplerType
    samplers = {"Albedo": enum(S, "SAMPLERTYPE_COLOR"), "Normal": enum(S, "SAMPLERTYPE_NORMAL"),
                "Roughness": enum(S, "SAMPLERTYPE_LINEAR_GRAYSCALE", "SAMPLERTYPE_GRAYSCALE"),
                "AO": enum(S, "SAMPLERTYPE_LINEAR_GRAYSCALE", "SAMPLERTYPE_GRAYSCALE")}
    samples = {}
    for i, (name, sampler) in enumerate(samplers.items()):
        e = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, -300 + 250 * i,
                 parameter_name=name, texture=defaults[name], sampler_type=sampler)
        link(uv, "", e, "UVs")
        samples[name] = e
    tint = expr(m, unreal.MaterialExpressionVectorParameter, -600, -550,
                parameter_name="Tint", default_value=unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    col = expr(m, unreal.MaterialExpressionMultiply, -300, -400)
    link(samples["Albedo"], "RGB", col, "A")
    link(tint, "", col, "B")
    out(col, MP.MP_BASE_COLOR)
    MEL.connect_material_property(samples["Normal"], "RGB", MP.MP_NORMAL)
    MEL.connect_material_property(samples["Roughness"], "R", MP.MP_ROUGHNESS)
    MEL.connect_material_property(samples["AO"], "R", MP.MP_AMBIENT_OCCLUSION)
    MEL.recompile_material(m)
    return m


def make_materials():
    grey = make_greybox_master()
    sand = make_sand_master()

    def g(name, value, rough, metal=0.0, emissive=0.0, tint=(1.0, 1.0, 1.0)):
        return make_instance(name, grey, {"Color": (value * tint[0], value * tint[1], value * tint[2])},
                             {"Roughness": rough, "Metallic": metal, "Emissive": emissive})

    floor_tex = import_texture_set("old_wooden_floor_02")            # seen up close in third person: keep 2k
    wall_tex = import_texture_set("beige_wall_002", max_size=1024)   # plaster reads fine at 1k
    world = make_world_aligned_master(floor_tex)
    mats = {
        "wall": make_instance("MI_Wall_Plaster", world, {"Tint": (0.8, 0.8, 0.8)}, {"TileSize": 250.0}, wall_tex),
        "ceiling": make_instance("MI_Ceiling_Plaster", world, {"Tint": (0.9, 0.9, 0.9)}, {"TileSize": 250.0}, wall_tex),
        "floor": make_instance("MI_Floor_OldWood", world, {"Tint": (0.85, 0.85, 0.85)}, {"TileSize": 200.0}, floor_tex),
        "wood": g("MI_Wood_Dark", 0.07, 0.6),
        "wood_light": g("MI_Wood_Mid", 0.16, 0.55),
        "metal": g("MI_Metal", 0.6, 0.35, metal=1.0),
        "sand_black": make_instance("MI_DarkSand_Black", sand, scalars={"Sandy": 0.0}),
        "sand_sandy": make_instance("MI_DarkSand_Sandy", sand, scalars={"Sandy": 1.0}),
    }
    log("materials created:", len(mats))
    return mats


# ---------- level ----------

CUBE = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
CYL = unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
SPH = unreal.load_asset("/Engine/BasicShapes/Sphere.Sphere")


def place(label, folder, center, size, mat, mesh=None, yaw=0.0, pitch=0.0, roll=0.0, movable=False):
    """Spawn a mesh scaled so its bounds match `size` (cm) and centered on `center`."""
    mesh = mesh or CUBE
    bounds = mesh.get_bounds()
    ext = bounds.box_extent
    actor = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*center),
                                       unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw))
    smc = actor.get_editor_property("static_mesh_component")
    if movable:
        smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(mesh)
    actor.set_actor_scale3d(unreal.Vector(size[0] / (2 * ext.x), size[1] / (2 * ext.y), size[2] / (2 * ext.z)))
    smc.set_material(0, mat)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    return actor


def prop(label, folder, mesh_paths, center_xy, yaw=0.0, floor_z=0.0, center_z=None, movable=False, movable_parts=False):
    """Place an imported (possibly multi-part) mesh: the first mesh's bounds center lands on center_xy and its
    bottom on floor_z (or its center on center_z). All parts share the first mesh's pivot frame."""
    meshes = [unreal.load_asset(p) for p in mesh_paths]
    if not meshes[0]:
        log("WARN missing mesh", mesh_paths[0])
        return []
    b = meshes[0].get_bounds()
    o, e = b.origin, b.box_extent
    t = math.radians(yaw)
    rx, ry = o.x * math.cos(t) - o.y * math.sin(t), o.x * math.sin(t) + o.y * math.cos(t)
    z = (center_z - o.z) if center_z is not None else (floor_z - (o.z - e.z))
    loc = unreal.Vector(center_xy[0] - rx, center_xy[1] - ry, z)
    actors = []
    for i, m in enumerate(meshes):
        if not m:
            log("WARN missing mesh", mesh_paths[i])
            continue
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
        smc = a.get_editor_property("static_mesh_component")
        if movable or (movable_parts and i > 0):
            smc.set_mobility(unreal.ComponentMobility.MOVABLE)
        smc.set_static_mesh(m)
        a.set_actor_label(label if i == 0 else f"{label}_{m.get_name()}")
        a.set_folder_path(folder)
        actors.append(a)
    return actors


def light_common(comp, label, actor, folder="Lighting"):
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)


def point_light(label, loc, lumens, temp, radius, src=4.0, shadows=True, vol=1.0):
    a = EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*loc))
    c = a.get_editor_property("point_light_component")
    light_common(c, label, a)
    setp(c, "intensity_units", enum(unreal.LightUnits, "LUMENS"))
    setp(c, "intensity", lumens)
    setp(c, "use_temperature", True)
    setp(c, "temperature", temp)
    setp(c, "attenuation_radius", radius)
    setp(c, "source_radius", src)
    setp(c, "cast_shadows", shadows)
    setp(c, "volumetric_scattering_intensity", vol)
    return a


def rect_light(label, loc, rot, lumens, temp, w, h, radius, vol=3.0):
    a = EAS.spawn_actor_from_class(unreal.RectLight, unreal.Vector(*loc), rot)
    c = a.get_editor_property("rect_light_component")
    light_common(c, label, a)
    setp(c, "intensity_units", enum(unreal.LightUnits, "LUMENS"))
    setp(c, "intensity", lumens)
    setp(c, "use_temperature", True)
    setp(c, "temperature", temp)
    setp(c, "source_width", w)
    setp(c, "source_height", h)
    setp(c, "attenuation_radius", radius)
    setp(c, "barn_door_angle", 80.0)
    setp(c, "volumetric_scattering_intensity", vol)
    return a


def camera(label, loc, pitch, yaw, fov=80.0):
    a = EAS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
    setp(a.get_editor_property("camera_component"), "field_of_view", fov)
    a.set_actor_label(label)
    a.set_folder_path("Dev/ShotCameras")
    return a


def build_room(M):
    W, R, F = "Room/Walls", "Room", "Room/Furniture"
    # shell: 30 cm walls running past the 20 cm floor and 30 cm ceiling, so Lumen doesn't leak at the seams
    place("Floor", R, (0, 0, -10), (660, 560, 20), M["floor"])
    place("Ceiling", R, (0, 0, 295), (660, 560, 30), M["ceiling"])
    place("Wall_S_Desk", W, (-315, 0, 145), (30, 560, 310), M["wall"])
    place("Wall_E_Dresser", W, (0, 265, 145), (660, 30, 310), M["wall"])
    # +X wall with the bedroom door (opening y 20..115, height 215)
    place("Wall_N_Left", W, (315, -130, 145), (30, 300, 310), M["wall"])
    place("Wall_N_Right", W, (315, 197.5, 145), (30, 165, 310), M["wall"])
    place("Wall_N_Lintel", W, (315, 67.5, 257.5), (30, 95, 85), M["wall"])
    # -Y wall with the window (opening x -150..-30, z 95..205)
    place("Wall_W_A", W, (-240, -265, 145), (180, 30, 310), M["wall"])
    place("Wall_W_B", W, (150, -265, 145), (360, 30, 310), M["wall"])
    place("Wall_W_BelowWindow", W, (-90, -265, 42.5), (120, 30, 105), M["wall"])
    place("Wall_W_AboveWindow", W, (-90, -265, 252.5), (120, 30, 95), M["wall"])
    place("Window_Mullion_V", W, (-90, -262, 150), (5, 5, 110), M["wood"])
    place("Window_Mullion_H", W, (-90, -262, 150), (120, 5, 5), M["wood"])
    place("Window_Sill", W, (-90, -246, 95), (132, 26, 4), M["wood"])

    # door (interactive: movable)
    place("Door_Bedroom", "Interactables/Door", (302.5, 67.5, 106.5), (5, 93, 213), M["wood_light"], movable=True)
    place("Door_Handle", "Interactables/Door", (297, 104, 100), (6, 6, 6), M["metal"], mesh=SPH, movable=True)
    place("Door_Keyhole", "Interactables/Door", (299, 104, 89), (1.5, 3, 7), M["metal"], movable=True)

    # ---- real furniture: Poly Haven CC0, imported by import_props.py (license list: P:/FoA-Assets/polyhaven/MANIFEST.md)
    # Poly Haven meshes face +Y after import; multi-part assets share one pivot frame, so parts go at the body's transform.
    PH = "/Game/FoA/Props"
    bed = PH + "/old_bed_frame/old_bed_frame_1k/StaticMeshes/old_bed_frame_1k"
    prop("Bed", F, [bed], (195, -200), yaw=90)  # along the window wall
    com = PH + "/GothicCommode_01/GothicCommode_01_1k/StaticMeshes/GothicCommode_01"
    prop("Commode", "Interactables/Commode", [com] + [f"{com}_door0{i}" for i in (1, 2, 3)],
         (-110, 219), yaw=180, movable_parts=True)  # drawers are separate meshes
    cab = PH + "/GothicCabinet_01/GothicCabinet_01_1k/StaticMeshes/GothicCabinet_01"
    prop("Wardrobe", "Interactables/Wardrobe", [cab + "_cabinet"] + [f"{cab}_door{i}" for i in (1, 2, 3, 4)],
         (150, 197), yaw=180, movable_parts=True)
    desk = PH + "/wooden_table_02/wooden_table_02_1k/StaticMeshes/wooden_table_02_1k"
    prop("Desk", F, [desk], (-262, 0), yaw=90)
    chair = PH + "/painted_wooden_chair_01/painted_wooden_chair_01_1k/StaticMeshes/painted_wooden_chair_01_1k"
    prop("Chair", F, [chair], (-195, 10), yaw=90)
    lamp = PH + "/desk_lamp_arm_01/desk_lamp_arm_01_1k/StaticMeshes/desk_lamp_arm_01_1k"
    prop("DeskLamp", F, [lamp], (-280, -38), yaw=0, floor_z=80.0)
    clk = PH + "/wall_clock/wall_clock_1k/StaticMeshes/wall_clock"
    prop("WallClock", F, [clk, clk + "_hours_hand", clk + "_minute_hand", clk + "_second_hand"],
         (-297, 0), yaw=-90, center_z=185.0)
    boots = PH + "/rubber_boots/rubber_boots_1k/StaticMeshes/rubber_boots"
    prop("Boot_L", "Interactables/Items", [boots + "_dirty_l"], (78, -140), yaw=20, movable=True)
    prop("Boot_R", "Interactables/Items", [boots + "_dirt_r"], (64, -116), yaw=-10, movable=True)

    # where the small tutorial items go; markers only until their real meshes exist (Lux3D / Poly Haven)
    for label, loc in [("Spot_Key_InBoot", (78, -140, 20)), ("Spot_Screwdriver_DeskDrawer", (-262, 30, 70)),
                       ("Spot_Hanger_WardrobeSide", (150, 145, 150))]:
        tp = EAS.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*loc))
        tp.set_actor_label(label)
        tp.set_folder_path("Interactables/ItemSpots")
    # Stencil color exception verified 2026-11-05 (sandy pile rendered in color, rest monochrome). To keep an
    # object's color: set_render_custom_depth(True) + set_custom_depth_stencil_value(1) on its mesh component.
    log("room built")


def build_lighting_and_post(ppmat):
    point_light("Light_DeskLamp", (-280, -25, 140), 450.0, 2700.0, 900.0, src=6.0)  # near the arm lamp's head
    # moonlight through the window, from outside
    # below ceiling height, angled so the beam crosses the window opening and pools on the floor mid-room
    rect_light("Light_Moon", (-90, -380, 230), unreal.Rotator(roll=0.0, pitch=-30.0, yaw=90.0),
               6000.0, 9000.0, 160.0, 120.0, 1600.0, vol=4.0)
    # faint light leaking under/around the door from the hallway
    point_light("Light_HallwayLeak", (400, 67, 40), 120.0, 3200.0, 400.0, src=10.0, vol=0.5)

    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 200))
    sc = sky.get_editor_property("light_component")
    light_common(sc, "Light_SkyFill", sky)
    cube = unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap")
    if cube:
        setp(sc, "source_type", enum(unreal.SkyLightSourceType, "SLS_SPECIFIED_CUBEMAP"))
        setp(sc, "cubemap", cube)
    setp(sc, "intensity", 0.02)
    try:
        sc.recapture_sky()
    except Exception as e:
        log("WARN recapture_sky", e)

    fog = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    fc = fog.get_editor_property("component")
    fog.set_actor_label("HeightFog")
    fog.set_folder_path("Lighting")
    setp(fc, "fog_density", 0.012)
    setp(fc, ["enable_volumetric_fog", "volumetric_fog"], True)
    setp(fc, "volumetric_fog_scattering_distribution", 0.6)

    ppv = EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 140))
    ppv.set_actor_label("PP_DreamMono")
    ppv.set_folder_path("Lighting")
    setp(ppv, "unbound", True)
    s = ppv.get_editor_property("settings")
    wb = unreal.WeightedBlendable()
    wb.set_editor_property("weight", 1.0)
    wb.set_editor_property("object", ppmat)
    wbs = unreal.WeightedBlendables()
    wbs.set_editor_property("array", [wb])
    setp(s, "weighted_blendables", wbs)
    for flag, prop, value in [
        ("override_auto_exposure_method", "auto_exposure_method", enum(unreal.AutoExposureMethod, "AEM_HISTOGRAM")),
        # min == max locks exposure (EV100), so the room stays a dark night instead of adapting to daylight
        ("override_auto_exposure_min_brightness", "auto_exposure_min_brightness", 2.5),
        ("override_auto_exposure_max_brightness", "auto_exposure_max_brightness", 2.5),
        ("override_auto_exposure_bias", "auto_exposure_bias", 0.0),
        ("override_color_contrast", "color_contrast", unreal.Vector4(1.15, 1.15, 1.15, 1.15)),
        ("override_vignette_intensity", "vignette_intensity", 0.55),
        ("override_film_grain_intensity", "film_grain_intensity", 0.3),
        ("override_bloom_intensity", "bloom_intensity", 0.5),
    ]:
        if setp(s, flag, True):
            setp(s, prop, value)
    ppv.set_editor_property("settings", s)

    ps = EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(60, -80, 100), unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))
    ps.set_actor_label("PlayerStart_WakeUp")

    # reference shot cameras (not used in game)
    camera("Shot_ThirdPerson", (-200, -100, 190), -9.0, 18.5)
    camera("Shot_Wide", (-280, 230, 250), -18.0, -41.5, fov=90.0)
    camera("Shot_Window", (270, 100, 160), -2.0, -134.6, fov=85.0)
    camera("Shot_TopDown", (0, 0, 1150), -89.9, 0.0, fov=40.0)
    log("lighting, post and cameras placed")


def main():
    for d in (ROOT, MATS, PPDIR, MAPS):
        EAL.make_directory(d)
    world = UES.get_editor_world()
    if world and "L_Tutorial_Bedroom" in world.get_path_name():
        LES.load_level(FALLBACK_LEVEL)  # release the level's references before its materials are rebuilt
        unreal.SystemLibrary.collect_garbage()
    for stale in ("MI_Linen", "MI_Fabric_Blanket", "MI_Rug", "MI_Mirror", "MI_LampShade",  # from v1, now unused
                  "MI_Floor_Wood", "MI_Ceiling"):
        if EAL.does_asset_exist(f"{MATS}/{stale}"):
            EAL.delete_asset(f"{MATS}/{stale}")

    mpc = make_mpc()
    ppmat = make_pp_material(mpc)
    mats = make_materials()

    if EAL.does_asset_exist(LEVEL):
        # Reuse the level asset (deleting a level that was loaded this session fails silently); clear its actors.
        if not LES.load_level(LEVEL):
            raise RuntimeError("could not open " + LEVEL)
        doomed = [a for a in EAS.get_all_level_actors() if not isinstance(a, (unreal.WorldSettings, unreal.Brush))]
        EAS.destroy_actors(doomed)
        log("cleared", len(doomed), "actors from the existing level")
    elif not LES.new_level(LEVEL):
        raise RuntimeError("new_level failed for " + LEVEL)
    build_room(mats)
    build_lighting_and_post(ppmat)
    LES.save_current_level()
    EAL.save_directory(ROOT, only_if_is_dirty=False, recursive=True)
    log("saved", LEVEL)


if __name__ == "__main__":  # importable as a helper library (bedroom_v3.py) without rebuilding anything
    try:
        main()
        log("BUILD OK")
    except Exception:
        log("BUILD FAILED\n" + traceback.format_exc())
    finally:
        path = os.path.join(unreal.Paths.project_saved_dir(), "FoA_build_bedroom.log")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(LINES) + "\n")
        # Quit only when launched headless for the build; never inside someone's open editor (remote execution).
        if "-ExecutePythonScript" in unreal.SystemLibrary.get_command_line():
            unreal.SystemLibrary.quit_editor()
