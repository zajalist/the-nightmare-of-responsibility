"""Place the one BP_SandAmbience at the world origin (label SandAmbience, outliner FX/Sand); idempotent.
  $env:FOA_ACTORS_NEW='SandAmbience'; python Tools/Unreal/ue_remote.py Tools/Splats/place_sand_ambience.py
Its parts and sites are world positions because the actor sits at the origin with no rotation or scale."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
have = [a for a in EAS.get_all_level_actors() if a.get_actor_label() == 'SandAmbience']
if have:
    print('already placed', have[0].get_actor_location())
else:
    a = EAS.spawn_actor_from_class(unreal.load_class(None, '/Game/FoA/Gameplay/Ambient/BP_SandAmbience.BP_SandAmbience_C'),
                                   unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    a.set_actor_label('SandAmbience')
    a.set_folder_path('FX/Sand')
    print('placed', a.get_actor_label(), a.get_path_name())
