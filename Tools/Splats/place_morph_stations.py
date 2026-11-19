"""Sand morph stations in the bedroom (make_sand_morph.py, build_sand_morph_bp.py, MF_SplatMorph in M_SplatMesh).
Phases, each a short run (Python never compiles a Blueprint after touching its instances):
  python Tools/Unreal/ue_remote.py Tools/Splats/place_morph_stations.py FOA_MORPH=import   # textures (+ meshes via import_sand_vfx)
  python Tools/Unreal/ue_remote.py Tools/Splats/place_morph_stations.py FOA_MORPH=instances
  python Tools/Unreal/ue_remote.py Tools/Splats/place_morph_stations.py FOA_MORPH=place    # then Hayba level_save
Stations: the commode (where the sand clock looped; that actor is hidden), the desk top away from the lamp, and the
floor beside the bed. Staggered cycles (StartDelay 0 / 4 / 8 s) so something is always materializing somewhere."""
import json
import math
import os

import unreal

PHASE = os.environ.get("FOA_MORPH", "import")
EAL, MEL = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
P = json.load(open("P:/FoA-Assets/splatmesh/sand_morph_params.json"))
TEX_DIR, MI_DIR = "/Game/FoA/VFX/Sand/Textures", "/Game/FoA/VFX/Splats/Instances"
CURL = {"Commode": 2.5, "Desk": 2.0, "Floor": 4.0}
DELAY = {"Commode": 0.0, "Desk": 4.0, "Floor": 8.0}
RIM = {"Commode": (-330.5, 151.0, 123.0, 8.0), "Desk": (-330.5, 151.0, 123.0, 6.0), "Floor": (-60.0, -560.0, 160.0, 30.0)}


def do_import():
    for st in P:
        path = f"{TEX_DIR}/T_SandMorph_{st}"
        if not EAL.does_asset_exist(path) or os.environ.get("FOA_MORPH_REIMPORT") == "1":
            task = unreal.AssetImportTask()
            for prop, v in (("filename", f"P:/FoA-Assets/procedural/T_SandMorph_{st}.exr"), ("destination_path", TEX_DIR),
                            ("automated", True), ("replace_existing", True), ("save", False)):
                task.set_editor_property(prop, v)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        t = unreal.load_asset(path)
        for prop, v in (("srgb", False), ("compression_settings", unreal.TextureCompressionSettings.TC_HDR),
                        ("filter", unreal.TextureFilter.TF_NEAREST), ("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS),
                        ("never_stream", True), ("address_x", unreal.TextureAddress.TA_CLAMP), ("address_y", unreal.TextureAddress.TA_CLAMP)):
            t.set_editor_property(prop, v)
        EAL.save_asset(path, only_if_is_dirty=False)
        print("morph texture", path, t.blueprint_get_size_x(), t.blueprint_get_size_y())


def do_instances():
    parent = unreal.load_asset("/Game/FoA/VFX/Splats/M_SplatMesh")
    for st, info in P.items():
        name = f"MI_SandMorph_{st}"
        path = f"{MI_DIR}/{name}"
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, MI_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        MEL.set_material_instance_static_switch_parameter_value(mi, "Morph", True)
        MEL.set_material_instance_texture_parameter_value(mi, "MorphTex", unreal.load_asset(f"{TEX_DIR}/T_SandMorph_{st}"))
        for k, v in (("MorphCfg", (len(info["rows"]), info["side"], info["height_cm"], CURL[st])), ("Splat", (1.0, 1.0, 1.8, 1.0)),
                     ("Sand", (0.015, 0.003, 0.42, 0.3)), ("Light", RIM[st])):
            MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
        MEL.set_material_instance_scalar_parameter_value(mi, "Specular", 0.5)
        o = mi.get_editor_property("base_property_overrides")
        o.set_editor_property("override_blend_mode", True)
        o.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        mi.set_editor_property("base_property_overrides", o)
        MEL.update_material_instance(mi)
        EAL.save_asset(path, only_if_is_dirty=False)
        mesh = f"/Game/FoA/VFX/Splats/Meshes/SM_SandMorph_{st}/SM_SandMorph_{st}/StaticMeshes/SM_SandMorph_{st}"
        if EAL.does_asset_exist(mesh):
            m = unreal.load_asset(mesh)
            m.set_material(0, mi)
            EAL.save_asset(mesh, only_if_is_dirty=False)
        print(name, "ok")


def spots(by):
    """World locations of the three stations, from the hand-placed furniture's bounds (read only)."""
    out = {"Commode": unreal.Vector(-150.0, 266.0, 124.0)}       # on the commode mound, where the sand clock looped
    desk, lamp = by.get("Desk"), by.get("DeskLamp")
    if desk:
        o, e = desk.get_actor_bounds(True)
        away = -1.0 if lamp and lamp.get_actor_location().y > o.y else 1.0     # the desk half away from the lamp
        out["Desk"] = unreal.Vector(o.x, o.y + away * 0.35 * e.y, o.z + e.z)
    bed = by.get("Bed")
    if bed:
        o, e = bed.get_actor_bounds(True)
        d = unreal.Vector(-o.x, -o.y, 0.0)                        # toward the room centre
        n = max(math.hypot(d.x, d.y), 1.0)
        reach = (abs(d.x) / n) * e.x + (abs(d.y) / n) * e.y + 45.0
        out["Floor"] = unreal.Vector(o.x + d.x / n * reach, o.y + d.y / n * reach, 0.2)
    return out


def do_place():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    bp = unreal.load_asset("/Game/FoA/VFX/Sand/BP_SandMorph")
    for st, loc in spots(by).items():
        label = f"SandMorph_{st}"
        a = by.get(label)
        if not a:
            a = eas.spawn_actor_from_object(bp, loc, unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))
            a.set_actor_label(label)
            a.set_folder_path("FX/Sand")
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        c.set_static_mesh(unreal.load_asset(f"/Game/FoA/VFX/Splats/Meshes/SM_SandMorph_{st}/SM_SandMorph_{st}/StaticMeshes/SM_SandMorph_{st}"))
        c.set_material(0, unreal.load_asset(f"{MI_DIR}/MI_SandMorph_{st}"))
        for k, v in (("Rows", len(P[st]["rows"])), ("Hold", 6.0), ("MorphSeconds", 4.0), ("StartDelay", DELAY[st])):
            a.set_editor_property(k, v)
        print(label, a.get_actor_location())
    clock = by.get("SandClock_Commode")
    if clock:                                                     # the commode station takes over from the looping clock
        clock.get_component_by_class(unreal.StaticMeshComponent).set_visibility(False)


{"import": do_import, "instances": do_instances, "place": do_place}[PHASE]()
