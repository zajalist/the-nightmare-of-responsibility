"""mech_flow step 4: one BP_BeatDirector in L_Tutorial_Bedroom at the world origin (folder Gameplay), wired to
PlayerStart_WakeUp and the door actors; GI_FoA becomes the GameInstance class (the CDO here, DefaultEngine.ini on disk).
    python Tools/Unreal/ue_remote.py Tools/Unreal/flow/place_director.py
Then save the level with Hayba level_save."""
exec(open('P:/FoA/Tools/Unreal/flow/flow_common.py').read())

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def main():
    actors = EAS.get_all_level_actors()
    by_label = {a.get_actor_label(): a for a in actors}
    cls = unreal.load_class(None, cls_path(DIR))
    mine = [a for a in actors if a.get_class() == cls]
    if mine:  # placed before: only refresh the references (editor-rules: never re-place over the level)
        d = mine[0]
    else:
        d = EAS.spawn_actor_from_class(cls, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        d.set_actor_label('BeatDirector')
        d.set_folder_path('Gameplay')
    for prop, label in (('WakeUpStart', 'PlayerStart_WakeUp'), ('DoorFrame', 'DoorFrame_Bedroom'), ('Door', 'Door_Bedroom'),
                        ('Ceiling', 'Ceiling'), ('RefillActor', 'Screwdriver_DeskDrawer'),
                        ('ShirtActor', 'Shirt_T7'), ('Wardrobe', 'Wardrobe'), ('WakeBed', 'Bedding_Lux3D')):
        a = by_label.get(label) or (by_label.get('Bed') if prop == 'WakeBed' else None)
        if a:
            d.set_editor_property(prop, a)
        print(prop, '->', a.get_actor_label() if a else 'MISSING ' + label, a.root_component.mobility if a else '')
    print('director', d.get_actor_label(), d.get_actor_location(), 'wakeup', d.get_editor_property('WakeUpStart'))
    gms = unreal.get_default_object(unreal.GameMapsSettings)
    gms.set_editor_property('game_instance_class', unreal.SoftClassPath(cls_path(GI)))
    print('GameInstanceClass', gms.get_editor_property('game_instance_class'))


main()
