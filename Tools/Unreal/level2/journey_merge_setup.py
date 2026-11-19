"""Structural setup for the new visual-only shell; never changes the Nightmare or player CDO."""
import json
from pathlib import Path
import unreal

BP = '/Game/FoA/Level2/Journey/BP_L2Merge'
MAT = '/Game/FoA/Level2/Journey/M_L2MergeShell'
bp = unreal.load_asset(BP)
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)
shell_handle = next(h for h in handles if str(lib.get_variable_name(lib.get_data(h))) == 'Shell')
if not lib.is_root_component(lib.get_data(shell_handle)):
    assert sds.make_new_scene_root(handles[0], shell_handle, bp)
shells = {str(lib.get_variable_name(lib.get_data(h))):lib.get_object_for_blueprint(lib.get_data(h), bp) for h in handles}
player = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
sources = {str(lib.get_variable_name(lib.get_data(h))):lib.get_object_for_blueprint(lib.get_data(h), player)
           for h in sds.k2_gather_subobject_data_for_blueprint(player)}
material = unreal.load_asset(MAT)
assert material
rows = []
for name, leader in (('Shell','Body'),('HeadShell','Face')):
    shell = shells[name]
    mesh = sources[leader].get_editor_property('skeletal_mesh_asset')
    assert mesh and mesh.get_path_name().startswith('/Game/FoA/Characters/Teen/Mesh/'), (leader,mesh)
    shell.set_skeletal_mesh_asset(mesh)
    # Copy the rendered teen's final pose; hidden Manny has different retargeted proportions.
    shell.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    shell.set_editor_property('generate_overlap_events', False)
    for prop, value in (('relative_location', unreal.Vector(0, 0, 0)), ('relative_rotation', unreal.Rotator(0, 0, 0)),
                        ('relative_scale3d', unreal.Vector(1.02, 1.02, 1)), ('render_custom_depth', True),
                        ('custom_depth_stencil_value', 2), ('cast_shadow', False), ('can_character_step_up_on', unreal.CanBeCharacterBase.ECB_NO)):
        shell.set_editor_property(prop, value)
    # Do not evaluate the copied asset's post-process a second time on a leader-pose follower.
    shell.set_editor_property('disable_post_process_blueprint', True)
    for index in range(shell.get_num_materials()):shell.set_material(index, material)
    rows.append(dict(component=name,leader=leader,mesh=mesh.get_path_name(),material_slots=shell.get_num_materials()))
cdo = unreal.get_default_object(bp.generated_class())
cdo.set_actor_enable_collision(False)
cdo.set_actor_hidden_in_game(True)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
out = Path('P:/FoA/Saved/Integration/journey_merge_setup.json')
out.write_text(json.dumps(dict(surfaces=rows,material=material.get_path_name(),collision='NoCollision',stencil=2), indent=2))
print('Visual shell configured; native compile/save required')
