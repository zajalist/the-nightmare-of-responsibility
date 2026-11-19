"""Moon-bounce fill so the fireplace reads at night (coordinator-approved). Idempotent: updates the light if it exists.

  $env:FOA_ACTORS_NEW='Light_MoonBounce_Fireplace'; ue_remote.py Tools/Fireplace/place_fireplace_light.py [FOA_LM=40]

Cheap by design (the user feels lag spikes): Stationary, no shadows of any kind (cast, contact, volumetric), no
volumetric scattering, attenuation just past the breast. Cool and faint: moonlight bouncing off the floor, never warm.
"""
import math
import os

import unreal

LABEL = "Light_MoonBounce_Fireplace"
LOC = unreal.Vector(-150.0, -60.0, 60.0)
AIM = unreal.Vector(-330.0, 0.0, 75.0)   # chimney-breast face, insert height


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    d = AIM - LOC
    rot = unreal.Rotator(roll=0.0, pitch=math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))),
                         yaw=math.degrees(math.atan2(d.y, d.x)))
    light = next((a for a in eas.get_all_level_actors() if a.get_actor_label() == LABEL), None)
    if light is None:
        light = eas.spawn_actor_from_class(unreal.RectLight, LOC, rot)
        light.set_actor_label(LABEL)
    light.set_actor_location_and_rotation(LOC, rot, False, False)
    light.set_folder_path("Room/Chimney")
    c = light.get_component_by_class(unreal.RectLightComponent)
    c.set_mobility(unreal.ComponentMobility.STATIONARY)
    for k, v in (("intensity_units", unreal.LightUnits.LUMENS), ("intensity", float(os.environ.get("FOA_LM", "40"))),
                 ("use_temperature", True), ("temperature", 8200.0),          # cool, no warm cast
                 ("source_width", 140.0), ("source_height", 90.0), ("barn_door_angle", 70.0), ("barn_door_length", 20.0),
                 ("attenuation_radius", 260.0),                                 # reaches the breast corners, not the room
                 ("cast_shadows", False), ("cast_volumetric_shadow", False), ("contact_shadow_length", 0.0),
                 ("volumetric_scattering_intensity", 0.0),
                 ("specular_scale", 1.0)):
        c.set_editor_property(k, v)
    print("light", LABEL, "lm", c.get_editor_property("intensity"), "at", LOC, rot)


main()
