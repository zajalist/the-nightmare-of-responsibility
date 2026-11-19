"""Door-tool lane: BP_Door's ToolScrewHoles, one InstancedStaticMeshComponent under Pivot (Engine cylinder, the
keyhole's MI_DarkSand_Black, no collision, no shadow). DropToolScrew adds a dark disc over the plate's modelled flat
head at each emptied hole; HomeToolScrews clears them; RestoreDoorTool hides them with the plate. Idempotent.
Structural edit: deselect, close BP_Door's editors, add, compile once, save.
  $env:FOA_AREAS='Gameplay'; python Tools/Unreal/ue_remote.py Tools/Unreal/doortool/hole_component.py"""
import unreal

DOOR = '/Game/FoA/Gameplay/BP_Door'
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
bp = unreal.load_asset(DOOR)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
parts = {str(lib.get_variable_name(lib.get_data(h))): h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
if 'ToolScrewHoles' not in parts:
    h, err = sub.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=parts['Pivot'], new_class=unreal.InstancedStaticMeshComponent,
                                                                blueprint_context=bp))
    assert not str(err), err
    sub.rename_subobject(h, 'ToolScrewHoles')
    parts['ToolScrewHoles'] = h
c = lib.get_object_for_blueprint(lib.get_data(parts['ToolScrewHoles']), bp)
c.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/Cylinder'))
c.set_editor_property('override_materials', [unreal.load_asset('/Game/FoA/Materials/MI_DarkSand_Black')])
c.set_collision_profile_name('NoCollision')
c.set_editor_property('cast_shadow', False)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
print('HOLES', c.get_name(), c.get_editor_property('static_mesh').get_name(), [m.get_name() for m in c.get_editor_property('override_materials')],
      'saved', unreal.EditorAssetLibrary.save_asset(DOOR, only_if_is_dirty=False))
