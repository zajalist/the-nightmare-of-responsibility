"""Audio lane bed budget: Amb_NightWind no longer auto-plays (the bay already carries BP_RoomAudio's rain on the glass;
au3 measured five beds at once). Only its AudioComponent's auto-activate changes; the actor stays where it is.
  $env:FOA_ACTORS='Amb_NightWind'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/mute_nightwind.py"""
import unreal


def main():
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() == 'Amb_NightWind':
            c = a.get_component_by_class(unreal.AudioComponent)
            c.set_editor_property('auto_activate', False)
            print('Amb_NightWind auto_activate', c.get_editor_property('auto_activate'))


main()
