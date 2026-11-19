"""Gameplay lighting pass (world lane, approved plan 2026-11-09): the room reads in first person, monochrome, scary.
  $env:FOA_ACTORS='Light_Moon,Light_DeskLamp,Light_HallwayLeak,PP_DreamMono,Light_MoonFill_Bay,Light_DoorGap,ViewFill'
  $env:FOA_ACTORS_NEW='Light_MoonFill_Bay,Light_DoorGap,ViewFill'; python Tools/Unreal/ue_remote.py Tools/Lux3D/gameplay_lights.py
Idempotent: finds each light by label (spawns the new ones once), then sets the values in LIGHTS. Existing lights are
only retuned (the user's placements are kept). PP_DreamMono: only the local-exposure fields; the blendables array is
read and written back untouched (the face lane owns the third blendable).
Before/after: Saved/WorldShots/light/fp_before_sheet.png / fp_after_sheet.png (Tools/Lux3D/shot_sheet.py)."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
NEW = {  # label: (class, location, (pitch, yaw))
    'Light_MoonFill_Bay': (unreal.RectLight, (-60.0, -330.0, 115.0), (8.0, 90.0)),   # moonlight bounced off the bay back into the room
    'Light_DoorGap': (unreal.RectLight, (373.0, 87.5, 1.5), (0.0, 180.0)),          # the hallway light under the door
    'ViewFill': (unreal.load_class(None, '/Game/FoA/Gameplay/Ambient/BP_ViewFill.BP_ViewFill_C'), (0.0, 0.0, 160.0), (0.0, 0.0)),
}
LIGHTS = {  # label: component properties (lumens for local lights)
    'Light_Moon': {'intensity': 1000.0},
    'Light_DeskLamp': {'intensity': 160.0, 'attenuation_radius': 650.0},
    'Light_HallwayLeak': {'intensity': 220.0, 'attenuation_radius': 300.0},
    'Light_MoonFill_Bay': {'intensity_units': unreal.LightUnits.LUMENS, 'intensity': 80.0, 'use_temperature': True,
                           'temperature': 8500.0, 'source_width': 220.0, 'source_height': 120.0, 'barn_door_angle': 88.0,
                           'attenuation_radius': 1000.0, 'cast_shadows': False, 'specular_scale': 0.3,
                           'volumetric_scattering_intensity': 0.0},
    'Light_DoorGap': {'intensity_units': unreal.LightUnits.LUMENS, 'intensity': 40.0, 'use_temperature': True,
                      'temperature': 3200.0, 'source_width': 95.0, 'source_height': 2.0, 'barn_door_angle': 30.0,
                      'barn_door_length': 10.0, 'attenuation_radius': 700.0, 'cast_shadows': True,
                      'volumetric_scattering_intensity': 0.5},
}
PP = {'local_exposure_shadow_contrast_scale': 0.7, 'local_exposure_highlight_contrast_scale': 0.85}


def by_label():
    return {a.get_actor_label(): a for a in EAS.get_all_level_actors()}


A = by_label()
for label, (cls, loc, (p, y)) in NEW.items():
    if label not in A:
        a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=p, yaw=y))
        a.set_actor_label(label)
        a.set_folder_path('Lighting')
        A[label] = a
        print('spawned', label)
for label, props in LIGHTS.items():
    c = A[label].get_component_by_class(unreal.LightComponent)
    for k, v in props.items():
        c.set_editor_property(k, v)
    print('lit', label, {k: c.get_editor_property(k) for k in props if k in ('intensity', 'attenuation_radius')})
ppv = A['PP_DreamMono']
s = ppv.get_editor_property('settings')
for k, v in PP.items():
    s.set_editor_property('override_' + k, True)
    s.set_editor_property(k, v)
ppv.set_editor_property('settings', s)
print('pp', {k: ppv.get_editor_property('settings').get_editor_property(k) for k in PP},
      'blendables', [w.object.get_name() if w.object else None for w in s.get_editor_property('weighted_blendables').array])
