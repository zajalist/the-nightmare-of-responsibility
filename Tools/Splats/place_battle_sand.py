"""Places BattleSand_T8 (BP_BattleSand) on Encounter_T8 in the open bedroom, re-run safe (world lane):
  $env:FOA_ACTORS='BattleSand_T8'; python Tools/Unreal/ue_remote.py Tools/Splats/place_battle_sand.py
then: python Tools/Unreal/editor_lock.py save_level world"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
enc = acts['Encounter_T8']
a = acts.get('BattleSand_T8') or EAS.spawn_actor_from_class(unreal.load_class(None, '/Game/FoA/VFX/Sand/BP_BattleSand.BP_BattleSand_C'),
                                                            enc.get_actor_location(), unreal.Rotator(0.0, 0.0, 0.0))
a.set_actor_label('BattleSand_T8')
a.set_actor_location(enc.get_actor_location(), False, False)
a.set_folder_path('FX/Battle')
print('BATTLESAND placed', a.get_actor_location(), a.get_folder_path())
