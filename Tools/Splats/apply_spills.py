"""Floor sand as opaque spills (the sand direction page): imports the spill meshes from make_sand_spill.py, makes their
instances of M_SandSpill (built with Hayba's material tools), and puts them on the floor sand actors. Phases, each a
short run inside one editor-lock hold:
  python Tools/Unreal/ue_remote.py Tools/Splats/apply_spills.py FOA_SPILL=import     # one mesh per call is not needed: 3 small meshes
  python Tools/Unreal/ue_remote.py Tools/Splats/apply_spills.py FOA_SPILL=instances  # after M_SandSpill compiles
  python Tools/Unreal/ue_remote.py Tools/Splats/apply_spills.py FOA_SPILL=actors     # then Hayba level_save
  python Tools/Unreal/ue_remote.py Tools/Splats/apply_spills.py FOA_SPILL=crumbs     # after import_sand_vfx.py SM_SandCrumbs_<x>
  python Tools/Unreal/ue_remote.py Tools/Splats/apply_spills.py FOA_SPILL=pour       # the commode pour's own spill
  python Tools/Unreal/ue_remote.py Tools/Splats/apply_spills.py FOA_SPILL=pourlight  # SandRim_Pour, the pour's grazing light
  python Tools/Unreal/ue_remote.py Tools/Splats/apply_spills.py FOA_SPILL=grain      # T_SandGrain, linear RGBA8 with mips
actors: SandMound_<Path|Hearth|Bay> take SM_SandSpill_<x> at scale 1 and yaw 0 (location kept), the old mound-shaped
splat layers SandSplats_<x> are hidden (loose grains come back as their own crumb layer), and every sand actor joins
lighting channel 2 (plus 0) for SandRim_Light, the sand-only grazing rim light (channel 2 only, no shadows, warm)."""
import os

import unreal

PHASE = os.environ.get("FOA_SPILL", "import")
SRC = "P:/FoA-Assets/procedural"
DST = "/Game/FoA/VFX/Sand/Spill"
NAMES = ("Path", "Hearth", "Bay")
POUR_LAND = (-145.681, 227.149, 0.0)   # where the commode pour lands (make_sand_splats.py stream layout)
EAL, MEL = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
MOON_SIDE = (-60.0, -900.0, 140.0)    # rim key for the Fresnel term: low, out past the bay windows
# SandRim_Light: the prototype's moon angle relative to the ThirdPerson camera (light runs towards the camera from the
# front left, 30 deg up), so spill edges and strands are back-lit and the rim reads; dim and warm, channel 2 only.
RIM_ROT = unreal.Rotator(roll=0.0, pitch=-30.0, yaw=153.0)
RIM_LUX = float(os.environ.get("FOA_RIM_LUX", "1.2"))   # the placed SandRim_Light runs at 1.2 (every approved sand shot); 0.6 was the first pass


def mesh_path(name):
    for p in (f"{DST}/{name}", f"{DST}/{name}/{name}/StaticMeshes/{name}"):
        if EAL.does_asset_exist(p):
            return p
    return None


def do_import():
    for k in NAMES + ("Pour",):
        name = f"SM_SandSpill_{k}"
        full = mesh_path(name)
        if not full or os.environ.get("FOA_SPILL_REIMPORT") == "1":       # reimport replaces the mesh in place
            task = unreal.AssetImportTask()
            for prop, v in (("filename", f"{SRC}/{name}.gltf"), ("destination_path", f"{DST}/{name}"), ("automated", True),
                            ("replace_existing", True), ("save", False)):
                task.set_editor_property(prop, v)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            full = mesh_path(name)
        if not full:
            print("IMPORT FAILED", name)
            continue
        mesh = unreal.load_asset(full)
        ns = SMES.get_nanite_settings(mesh)
        ns.set_editor_property("enabled", False)
        SMES.set_nanite_settings(mesh, ns, True)
        bs = SMES.get_lod_build_settings(mesh, 0)
        for prop, v in (("recompute_normals", False), ("recompute_tangents", True), ("generate_lightmap_u_vs", False)):
            bs.set_editor_property(prop, v)
        SMES.set_lod_build_settings(mesh, 0, bs)
        EAL.save_asset(full, only_if_is_dirty=False)
        print(name, full, "tris", mesh.get_num_triangles(0))


def do_instances():
    parent = unreal.load_asset("/Game/FoA/VFX/Sand/M_SandSpill")
    for name, spill, rim in (("MI_SandSpill_Floor", (0.015, 0.009, 0.5, 1.3), (*MOON_SIDE, 10.0)),
                             ("MI_SandSpill_Mound", (0.015, 0.009, 0.45, 1.3), (-330.5, 151.0, 123.0, 8.0))):
        path = f"/Game/FoA/VFX/Sand/{name}"
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, "/Game/FoA/VFX/Sand", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        MEL.set_material_instance_vector_parameter_value(mi, "Spill", unreal.LinearColor(*spill))
        MEL.set_material_instance_vector_parameter_value(mi, "Rim", unreal.LinearColor(*rim))
        gap = os.environ.get("FOA_SPILL_GAP")      # yaw rad, pitch cm, offset cm, strength: measured from a top-down capture
        if gap:
            MEL.set_material_instance_vector_parameter_value(mi, "Gap", unreal.LinearColor(*[float(v) for v in gap.split(",")]))
        MEL.update_material_instance(mi)
        EAL.save_asset(path, only_if_is_dirty=False)
        print(name, "ok")


def channels(c, zero=True):
    lc = c.get_editor_property("lighting_channels")
    lc.set_editor_property("channel0", zero)
    lc.set_editor_property("channel2", True)
    c.set_editor_property("lighting_channels", lc)


def do_actors():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    mi = unreal.load_asset("/Game/FoA/VFX/Sand/MI_SandSpill_Floor")
    for k in NAMES:
        a = by.get(f"SandMound_{k}")
        if a:
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            c.set_static_mesh(unreal.load_asset(mesh_path(f"SM_SandSpill_{k}")))
            c.set_material(0, mi)
            a.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
            a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0), False)
            a.tags = [t for t in a.tags if not str(t).startswith("Spill")]
            print("spill", k, a.get_actor_location())
        s = by.get(f"SandSplats_{k}")
        if s:
            s.get_component_by_class(unreal.StaticMeshComponent).set_visibility(False)   # mound-shaped grains: retired here
    n = 0
    for label, a in by.items():
        if label.startswith("Sand") and label != "SandRim_Light":
            for c in a.get_components_by_class(unreal.PrimitiveComponent):
                channels(c)
                n += 1
    rim = by.get("SandRim_Light")
    if not rim:
        rim = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0.0, 0.0, 260.0), RIM_ROT)
        rim.set_actor_label("SandRim_Light")
        rim.set_folder_path("FX/Sand")
    rim.set_actor_rotation(RIM_ROT, False)
    lc = rim.light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for prop, v in (("intensity", RIM_LUX), ("light_color", unreal.Color(r=255, g=214, b=160, a=255)), ("cast_shadows", False),
                    ("atmosphere_sun_light", False), ("affects_world", True)):
        lc.set_editor_property(prop, v)
    channels(lc, zero=False)                     # sand only
    print("sand primitives on channel 2:", n, "rim", RIM_LUX, "lux", RIM_ROT)


def do_crumbs():
    """The hidden mound-shaped splat layers come back as crumb layers: loose grains around each spill's rim."""
    mi = unreal.load_asset("/Game/FoA/VFX/Splats/Instances/MI_Sand_Crumbs")
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("SandSplats_") and lab.split("_")[1] in NAMES:
            k = lab.split("_")[1]
            mesh = f"/Game/FoA/VFX/Splats/Meshes/SM_SandCrumbs_{k}/SM_SandCrumbs_{k}/StaticMeshes/SM_SandCrumbs_{k}"
            if not EAL.does_asset_exist(mesh):
                print("missing", mesh)
                continue
            spill = next(x for x in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                         if x.get_actor_label() == f"SandMound_{k}")
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            c.set_static_mesh(unreal.load_asset(mesh))
            c.set_material(0, mi)
            c.set_visibility(True)
            a.set_actor_location(spill.get_actor_location(), False, False)
            a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0), False)
            a.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
            a.tags = [t for t in a.tags if not str(t).startswith("Spill")]
            print("crumbs", lab)


def do_pour():
    """The pour lands in its own small spill (SandSpill_Pour) and its impact pile (SandSpill_Pile) takes the spill's
    mound material, so the stream's base, the pile and the floor read as one black sand."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    a = by.get("SandSpill_Pour")
    if not a:
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*POUR_LAND), unreal.Rotator(0.0, 0.0, 0.0))
        a.set_actor_label("SandSpill_Pour")
        a.set_folder_path("FX/Sand")
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset(mesh_path("SM_SandSpill_Pour")))
    c.set_material(0, unreal.load_asset("/Game/FoA/VFX/Sand/MI_SandSpill_Floor"))
    c.set_collision_profile_name("NoCollision")
    c.set_editor_property("custom_depth_stencil_value", 5)
    c.set_editor_property("render_custom_depth", False)      # off until the PP's depth-gated stencil fix lands (hotfix)
    channels(c)
    print("pour spill", a.get_actor_location())


def do_pourlight():
    """SandRim_Pour: a small grazing light that only the sand sees (channel 2, no shadows, warm), low beside the pour,
    so the black stream gets lit edges down its length and reads against the room instead of vanishing."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    loc = unreal.Vector(-100.0, 205.0, 40.0)
    a = by.get("SandRim_Pour") or eas.spawn_actor_from_class(unreal.PointLight, loc, unreal.Rotator(0.0, 0.0, 0.0))
    a.set_actor_label("SandRim_Pour")
    a.set_folder_path("FX/Sand")
    a.set_actor_location(loc, False, False)
    lc = a.light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for prop, v in (("intensity", float(os.environ.get("FOA_POUR_LUX", "4.0"))), ("attenuation_radius", 140.0),
                    ("light_color", unreal.Color(r=255, g=214, b=160, a=255)), ("cast_shadows", False)):
        lc.set_editor_property(prop, v)
    channels(lc, zero=False)
    print("pour light", loc)


def do_grain():
    """T_SandGrain (make_sand_grain_tex.py): linear data, uncompressed RGBA8 (BC artefacts would show as blocks in the
    grain tilt), full mip chain (the mips are the per-octave fade)."""
    path = "/Game/FoA/VFX/Sand/Textures/T_SandGrain"
    if not EAL.does_asset_exist(path) or os.environ.get("FOA_SPILL_REIMPORT") == "1":
        task = unreal.AssetImportTask()
        for prop, v in (("filename", f"{SRC}/T_SandGrain.png"), ("destination_path", "/Game/FoA/VFX/Sand/Textures"),
                        ("automated", True), ("replace_existing", True), ("save", False)):
            task.set_editor_property(prop, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    t = unreal.load_asset(path)
    for prop, v in (("srgb", False), ("compression_settings", unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP),
                    ("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD), ("address_x", unreal.TextureAddress.TA_WRAP),
                    ("address_y", unreal.TextureAddress.TA_WRAP)):
        t.set_editor_property(prop, v)
    EAL.save_asset(path, only_if_is_dirty=False)
    print("grain texture", path, t.blueprint_get_size_x(), t.blueprint_get_size_y())


{"import": do_import, "instances": do_instances, "actors": do_actors, "crumbs": do_crumbs, "pour": do_pour,
 "pourlight": do_pourlight, "grain": do_grain}[PHASE]()
