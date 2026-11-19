"""Parent-controlled ONE exclusive map trip. Never run while bedroom has unsaved changes."""
import os
import unreal
assert os.environ.get('FOA_LEASE'),'Parent exclusive lease required'
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert editor.get_game_world() is None
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bedroom='/Game/FoA/Maps/L_Tutorial_Bedroom';dream='/Game/FoA/Level2/Maps/L_L2_DreamTest'
def current():return editor.get_editor_world().get_path_name().split('.')[0]
def inventory():return sorted((a.get_actor_label(),a.get_class().get_name()) for a in actors.get_all_level_actors())
assert current()==bedroom,current()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Save/resolve dirty map deliberately before this trip'
baseline=inventory();assert len(baseline)==236,len(baseline)
assert any(label=='Encounter_T8' for label,cls in baseline)
assert any(cls.startswith('BP_BeatDirector') for label,cls in baseline)
material=unreal.load_asset('/Game/FoA/Level2/M_SplatWorld_Aniso');assert material
try:
    assert levels.load_level(dream)
    targets=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='DreamA_Splats']
    assert len(targets)==1
    component=targets[0].static_mesh_component
    assert component.static_mesh.get_name()=='SM_DreamA'
    component.set_material(0,material)
    assert levels.save_current_level()
finally:
    assert levels.load_level(bedroom)
    assert current()==bedroom and inventory()==baseline,'Bedroom restoration differs'
print('DreamA aniso override saved; bedroom236 restored')
