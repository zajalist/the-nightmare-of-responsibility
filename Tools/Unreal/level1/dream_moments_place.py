"""level1 lane: place BP_L1DreamMoments once (label L1_DreamMoments, folder Gameplay) and point it at the backpack and
the wardrobe. Idempotent: an existing one is updated, never duplicated. The backpack itself is not moved or edited.
  FOA_ACTORS_NEW=L1_DreamMoments FOA_ACTORS=L1_DreamMoments python Tools/Unreal/ue_remote.py Tools/Unreal/level1/dream_moments_place.py"""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
cls = unreal.load_class(None, '/Game/FoA/Gameplay/Ambient/BP_L1DreamMoments.BP_L1DreamMoments_C')
assert cls, 'BP_L1DreamMoments missing'
m = acts.get('L1_DreamMoments') or eas.spawn_actor_from_class(cls, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
m.set_actor_label('L1_DreamMoments')
m.set_folder_path('Gameplay')
m.set_editor_property('Backpack', acts['Dress_Lux3D_Backpack'])
m.set_editor_property('Wardrobe', acts['Wardrobe'])
print('PLACED', m.get_actor_label(), m.get_editor_property('Backpack').get_actor_label(), m.get_editor_property('Wardrobe').get_actor_label())
