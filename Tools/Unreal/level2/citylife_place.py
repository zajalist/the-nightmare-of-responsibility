"""City life lane: one BP_L2CityLife in the open (persistent) map, idempotent. ue_remote with FOA_ACTORS_NEW=CityLife.
It is never spatially loaded (its pool follows the car across the city, far from where the actor stands) and sits
below the bedroom so nothing of it shows in the editor (every pooled component starts hidden anyway)."""
import unreal

BP = '/Game/FoA/Level2/CityLife/BP_L2CityLife'
LABEL = 'CityLife_Manager'
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cls = unreal.EditorAssetLibrary.load_blueprint_class(BP)
mine = [a for a in eas.get_all_level_actors() if a.get_class() == cls]
actor = mine[0] if mine else eas.spawn_actor_from_class(cls, unreal.Vector(0, 0, -3000), unreal.Rotator())
for extra in mine[1:]:
    eas.destroy_actor(extra)
actor.set_actor_label(LABEL)
actor.set_folder_path('Level2/CityLife')
try:
    actor.set_editor_property('is_spatially_loaded', False)
except Exception as err:  # not a World Partition map: nothing to unload
    print('spatial loading:', err)
print('placed', actor.get_actor_label(), actor.get_path_name(), 'copies removed', len(mine[1:]))
