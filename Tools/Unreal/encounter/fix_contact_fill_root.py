"""Restore stable garment root after native component creation replaced DefaultSceneRoot."""
import unreal,json
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
bp=unreal.load_asset('/Game/FoA/Gameplay/Encounter/BP_Garment')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
handles=sds.k2_gather_subobject_data_for_blueprint(bp)
names={str(lib.get_variable_name(lib.get_data(h))):h for h in handles}
obj=lambda n:lib.get_object(lib.get_data(names[n]))
before={n:obj(n).get_relative_transform() for n in ('Mesh','Rig','ContactFill')}
if 'Root' not in names:
    h,fail=sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles[0],new_class=unreal.SceneComponent,blueprint_context=bp))
    assert not str(fail),fail
    sds.rename_subobject(h,unreal.Text('Root'));names['Root']=h
assert sds.make_new_scene_root(handles[0],names['Root'],bp)
for n in ('Mesh','Rig','ContactFill'):
    assert sds.attach_subobject(names['Root'],names[n]),n
    obj(n).set_relative_transform(before[n],False,True)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,only_if_is_dirty=False)
# Verify actual constructed runtime-like hierarchy in editor transient actor, then remove immediately.
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actor=sub.spawn_actor_from_class(bp.generated_class(),unreal.Vector(0,0,-10000),transient=True)
try:
    root=actor.root_component;assert root.get_name()=='Root',root.get_name()
    rows={}
    for c in actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() in before:
            assert c.get_attach_parent()==root,(c.get_name(),c.get_attach_parent())
            rows[c.get_name()]=dict(parent=root.get_name(),relative=str(c.get_relative_transform()))
    Path('P:/FoA/Saved/Integration/cinematic_audit/contact_fill/root_verified.json').write_text(json.dumps(rows,indent=2))
finally:sub.destroy_actor(actor)
print('Contact fill sibling hierarchy verified')
