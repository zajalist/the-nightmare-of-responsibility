"""BP_FoAPlayer.CharacterLight off (face lane's A/B, 2026-11-09: the 3 cd character-only point light on the camera boom
flattened his skin to a white mask, mean luma 0.63-0.66 vs 0.30-0.41 without it, and it whitens the first-person arm).
The component stays (not Visible) for a possible authored-camera rim later. Refuses if a level sequence keys it.
Compile and save through Hayba afterwards.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/character_light_off.py FOA_AREAS=Characters"""
import unreal

keyed = []
for path in unreal.EditorAssetLibrary.list_assets('/Game/FoA/Cinematics', recursive=True):
    a = unreal.load_asset(path)
    if isinstance(a, unreal.LevelSequence):
        stack = list(a.get_bindings())
        while stack:
            b = stack.pop()
            if 'CharacterLight' in str(b.get_display_name()):
                keyed.append(a.get_name())
            stack.extend(b.get_child_possessables())
assert not keyed, ('CharacterLight is keyed in', keyed)
bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
light = lib.get_object_for_blueprint(lib.get_data(handles['CharacterLight']), bp)
before = (light.get_editor_property('visible'), light.get_editor_property('intensity'))
light.set_editor_property('visible', False)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print('CHARACTER_LIGHT', light.get_path_name(), 'visible/intensity before', before, 'after', light.get_editor_property('visible'))
