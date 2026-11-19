"""Places (or updates) the sand VFX actors in the open level, outliner folder FX/Sand, then saves the level.
Idempotent by actor label; transforms come from P:/FoA-Assets/splatmesh/sand_vfx_params.json (make_sand_splats.py),
so the splat layers sit exactly on the SandMound_* actors they animate.

  python Tools/Unreal/ue_remote.py Tools/Splats/place_sand_vfx.py
"""
import json

import unreal

P = json.load(open("P:/FoA-Assets/splatmesh/sand_vfx_params.json", encoding="utf-8"))
EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MESHES = "/Game/FoA/VFX/Splats/Meshes"
MI = "/Game/FoA/VFX/Splats/Instances"


def mesh(name):
    for p in (f"{MESHES}/{name}", f"{MESHES}/{name}/{name}/StaticMeshes/{name}", name):
        if EAL.does_asset_exist(p):
            return unreal.load_asset(p)
    raise RuntimeError("missing mesh " + name)


def place(label, mesh_name, mat, loc, yaw, scale, splats=True):
    a = next((x for x in EAS.get_all_level_actors() if x.get_actor_label() == label), None)
    if a is None:
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc))
        a.set_actor_label(label)
    a.set_folder_path("FX/Sand")
    a.set_actor_location(unreal.Vector(*loc), False, False)
    a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), False)
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    c = a.static_mesh_component
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_static_mesh(mesh(mesh_name))
    c.set_material(0, unreal.load_asset(mat))
    if splats:  # pure VFX: no shadows (unlit splats), no collision, no decals, not in distance fields / Lumen
        c.set_cast_shadow(False)
        c.set_collision_profile_name("NoCollision")
        for k, v in (("receives_decals", False), ("affect_distance_field_lighting", False),
                     ("affect_dynamic_indirect_lighting", False)):
            c.set_editor_property(k, v)
    return label


def run():
    done = []
    s = P["stream"]
    done.append(place("SandStream_Commode", "SM_SandStream", f"{MI}/MI_Sand_Stream", s["loc"], s["yaw"], 1.0))
    p = P["pile"]
    done.append(place("SandSpill_Pile", "/Game/FoA/Procedural/SM_SandMound_C/SM_SandMound_C/StaticMeshes/SM_SandMound_C",
                      "/Game/FoA/Materials/MI_DarkSand_Black", p["loc"], p["yaw"], p["scale"], splats=False))
    for label, m in P["mounds"].items():
        done.append(place(f"SandSplats_{label}", m["mesh"], f"{MI}/MI_Sand_Mound_{label}", m["loc"], m["yaw"], m["scale"]))
    c = P["clock"]
    done.append(place("SandClock_Commode", "fear_of_adulthood_clock", f"{MI}/MI_Sand_Clock", c["loc"], c["yaw"], 1.0))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print("placed", done)


run()  # in a function: no actor/asset wrappers left behind
