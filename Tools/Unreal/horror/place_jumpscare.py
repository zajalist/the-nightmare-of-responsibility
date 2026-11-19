"""Places the one BP_Jumpscare (label FOA_Jumpscare, outliner folder Gameplay) over the door approach. Idempotent: an
existing FOA_Jumpscare is left where it is (the user may have moved it).
  $env:FOA_ACTORS_NEW='FOA_Jumpscare'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/place_jumpscare.py"""
import unreal


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = next((x for x in eas.get_all_level_actors() if x.get_actor_label() == 'FOA_Jumpscare'), None)
    if not a:
        cls = unreal.EditorAssetLibrary.load_blueprint_class('/Game/FoA/Gameplay/Jumpscare/BP_Jumpscare')
        a = eas.spawn_actor_from_class(cls, unreal.Vector(305, 80, 100), unreal.Rotator(0, 0, 0))
        a.set_actor_label('FOA_Jumpscare')
    a.set_folder_path('Gameplay')
    l = a.get_actor_location()
    print('FOA_Jumpscare', round(l.x), round(l.y), round(l.z))


main()
