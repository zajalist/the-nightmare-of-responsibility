"""Spawns Encounter_T8 (BP_Encounter) at FOA_X, FOA_Y, FOA_YAW in the open level, once (Hayba actor_spawn couldn't
resolve the Blueprint class after the restart). Folder Gameplay. Save afterwards with editor_lock.py save_level."""
import os

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LABEL = 'Encounter_T8'


def main():
    if any(a.get_actor_label() == LABEL for a in EAS.get_all_level_actors()):
        print(LABEL, 'already placed')
        return
    cls = unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
    assert cls, 'BP_Encounter class not found'
    loc = unreal.Vector(float(os.environ['FOA_X']), float(os.environ['FOA_Y']), 0.0)
    a = EAS.spawn_actor_from_class(cls, loc, unreal.Rotator(roll=0, pitch=0, yaw=float(os.environ['FOA_YAW'])))
    a.set_actor_label(LABEL)
    a.set_folder_path('Gameplay')
    print('placed', LABEL, a.get_actor_location(), a.get_actor_rotation().yaw)


main()
