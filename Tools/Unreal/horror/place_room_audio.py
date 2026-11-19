"""Places the one BP_RoomAudio (label FOA_RoomAudio, outliner folder Audio) at the room origin. Idempotent: an existing
FOA_RoomAudio is left where it is.
  $env:FOA_ACTORS_NEW='FOA_RoomAudio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/place_room_audio.py"""
import unreal


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = next((x for x in eas.get_all_level_actors() if x.get_actor_label() == 'FOA_RoomAudio'), None)
    if not a:
        cls = unreal.EditorAssetLibrary.load_blueprint_class('/Game/FoA/Audio/BP_RoomAudio')
        a = eas.spawn_actor_from_class(cls, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        a.set_actor_label('FOA_RoomAudio')
    a.set_folder_path('Audio')
    print('FOA_RoomAudio', a.get_actor_location())


main()
