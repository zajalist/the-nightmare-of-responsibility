"""Wire the existing wardrobe and new director blockers without changing any placed transform."""
import json

import unreal

path = '/Game/FoA/Gameplay/BP_BeatDirector'
bp = unreal.load_asset(path)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
by_label = {a.get_actor_label(): a for a in actors}
director, wardrobe = by_label['BeatDirector'], by_label['Wardrobe']
before = {name: by_label[name].get_actor_transform().export_text()
          for name in ('Wardrobe', 'Door_Bedroom', 'DoorFrame_Bedroom')}
director.set_editor_property('Wardrobe', wardrobe)
director.set_editor_property('WakeBed', by_label.get('Bedding_Lux3D') or by_label['Bed'])

sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for handle in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(handle)
    name = str(lib.get_variable_name(data))
    if name == 'WardrobeKeyLight':
        template = lib.get_object_for_blueprint(data, bp)
        for key, value in dict(relative_location=unreal.Vector(195, 70, 240), visible=False,
                               intensity_units=unreal.LightUnits.LUMENS, intensity=100.0,
                               attenuation_radius=350.0, use_inverse_squared_falloff=True, cast_shadows=False).items():
            template.set_editor_property(key, value)
        del template
    if name not in ('FallenWardrobeBlocker', 'OldDoorBlocker'):
        continue
    template = lib.get_object_for_blueprint(data, bp)
    template.set_collision_profile_name('BlockAll')
    template.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    template.set_editor_property('hidden_in_game', True)
    template.set_editor_property('generate_overlap_events', False)
    if name == 'OldDoorBlocker':
        template.set_editor_property('box_extent', unreal.Vector(20, 58, 150))
    del template
for component in director.get_components_by_class(unreal.BoxComponent):
    if component.get_name() in ('FallenWardrobeBlocker', 'OldDoorBlocker'):
        component.set_collision_profile_name('BlockAll')
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_editor_property('hidden_in_game', True)
        component.set_editor_property('generate_overlap_events', False)
        if component.get_name() == 'OldDoorBlocker':
            component.set_box_extent(unreal.Vector(20, 58, 150), False)
        print('blocker', component.get_name(), component.get_collision_enabled())
for component in director.get_components_by_class(unreal.PointLightComponent):
    if component.get_name() == 'WardrobeKeyLight':
        component.set_relative_location(unreal.Vector(195, 70, 240), False, True)
        for key, value in dict(visible=False, intensity_units=unreal.LightUnits.LUMENS, intensity=100.0,
                               attenuation_radius=350.0, use_inverse_squared_falloff=True, cast_shadows=False).items():
            component.set_editor_property(key, value)
        print('wardrobe light', component.get_name(), component.intensity, component.intensity_units, component.is_visible())

table = unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
rows = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
matches = [r for r in rows if r['Interactable'] == 'Wardrobe' and r['State'] == 'Standing'
           and r['Verb'] == 'Notify' and r['Item'] == 'HandleOff']
assert len(matches) == 1, matches
matches[0]['Event'] = 'WardrobeFalling'
assert any(r['Event'] == 'WardrobeLanded' for r in rows)
assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table, json.dumps(rows))
assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
for name, transform in before.items():
    assert transform == by_label[name].get_actor_transform().export_text(), name
assert director.get_editor_property('Wardrobe') == wardrobe
print('WARDROBE SETUP OK; one falling event, landing preserved, three placed transforms unchanged')
