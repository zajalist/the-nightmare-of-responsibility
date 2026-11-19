"""SandClock_WakeUp: the bedside alarm clock of LS_WakeUp, made of black sand (Lux3D alarm_clock_splat, 12k splats),
a BP_SandMaterialize with Loop off, formed and still until the wake-up lane calls Dissolve(1.2) at the grab.
  python Tools/Unreal/ue_remote.py Tools/Splats/place_wakeup_clock.py [FOA_CLOCK_FACE=1|-1]
Placed where the cine lane's grab lands (LS_WakeUp v3): base traced onto the nightstand top below (317, -96), dial
facing yaw 120 toward the insert camera. The furniture is only read. Places the actor once; on later runs
it only refreshes the mesh, material and flags, so a hand-adjusted transform is kept."""
import math
import os

import unreal

LABEL = "SandClock_WakeUp"
BP = "/Game/FoA/VFX/Sand/BP_SandMaterialize"
MESH = "/Game/FoA/VFX/Splats/Meshes/SM_AlarmClockSplats/SM_AlarmClockSplats/StaticMeshes/SM_AlarmClockSplats"
MI = "/Game/FoA/VFX/Splats/Instances/MI_Sand_AlarmClock"
SCALE = 0.36          # the capture is 42 cm tall: a 15 cm bedside clock
FACE = float(os.environ.get("FOA_CLOCK_FACE", "1"))   # which local Y the dial faces (+1 / -1), checked by capture


def run():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    clock = by.get(LABEL)
    if not clock:
        # the cine lane's spot: the hand closes on (317, -96, 85.6), the clock's middle; its base sits on the nightstand
        # top straight below (traced), dial toward yaw 120 (the insert camera, north-north-west)
        x, y = float(os.environ.get("FOA_CLOCK_X", "317")), float(os.environ.get("FOA_CLOCK_Y", "-96"))
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 150.0), unreal.Vector(x, y, 0.0),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        z = hit.to_tuple()[4].z if hit and hit.to_tuple()[0] else 79.0
        loc = unreal.Vector(x, y, z)
        yaw = float(os.environ.get("FOA_CLOCK_DIAL_YAW", "120")) - 90.0 * FACE
        clock = eas.spawn_actor_from_object(unreal.load_asset(BP), loc, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
        clock.set_actor_label(LABEL)
        clock.set_folder_path("FX/Sand")
        clock.set_actor_scale3d(unreal.Vector(SCALE, SCALE, SCALE))
        print("placed", LABEL, "at", loc, "yaw", round(yaw, 1))
    comp = next(c for c in clock.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith("Splats"))
    comp.set_static_mesh(unreal.load_asset(MESH))
    comp.set_material(0, unreal.load_asset(MI))
    comp.set_editor_property("render_custom_depth", True)
    comp.set_editor_property("custom_depth_stencil_value", 5)
    if "WakeUpClock" not in [str(t) for t in clock.tags]:   # BP_WakeUpCinematic finds it with GetAllActorsWithTag
        clock.tags = clock.tags + [unreal.Name("WakeUpClock")]
    clock.set_editor_property("BaseMode", 3.0)
    clock.set_editor_property("Loop", False)                 # reruns the construction script: ModeOverride = static
    print(LABEL, clock.get_actor_location(), clock.get_actor_rotation())


run()
