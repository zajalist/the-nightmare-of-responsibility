"""Native Hayba lacks SCS parenting. Give the takeover a stable, non-rendering root."""
import unreal
P='/Game/FoA/Gameplay/Ambient/BP_RoomTakeover'
bp=unreal.load_asset(P)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
s=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
l=unreal.SubobjectDataBlueprintFunctionLibrary
allh=s.k2_gather_subobject_data_for_blueprint(bp)
by={str(l.get_variable_name(l.get_data(h))):h for h in allh}
print(s.make_new_scene_root.__doc__)
assert s.make_new_scene_root(allh[0],by['Root'],bp)
for name,handle in by.items():
    if name not in ('Root','None','') and isinstance(l.get_object_for_blueprint(l.get_data(handle),bp),unreal.SceneComponent):
        assert s.attach_subobject(by['Root'],handle),name
print('Stable root installed')
