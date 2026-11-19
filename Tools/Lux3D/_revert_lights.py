import unreal
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
A = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
for label, props in {'Light_Moon': {'intensity': 700.0}, 'Light_DeskLamp': {'intensity': 12.0, 'attenuation_radius': 900.0},
                     'Light_HallwayLeak': {'intensity': 120.0, 'attenuation_radius': 200.0},
                     'Light_MoonFill_Bay': {'intensity': 0.0}, 'Light_DoorGap': {'intensity': 0.0}}.items():
    c = A[label].get_component_by_class(unreal.LightComponent)
    for k, v in props.items():
        c.set_editor_property(k, v)
    print('restored', label, props)
v = A['ViewFill']
v.set_actor_hidden_in_game(True)   # off until re-tuned at this exposure
print('ViewFill hidden in game')
