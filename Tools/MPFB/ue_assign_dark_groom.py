"""Material-only assignment; no attachment, pose, morph or sequence key changes."""
import unreal,json
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
root='/Game/FoA/Characters/Teen/Hair'
mi=unreal.load_asset(root+'/MI_Teen_Strands');assert mi
groom=unreal.load_asset(root+'/GR_Teen_Scalp')
groups=list(groom.get_editor_property('hair_groups_materials'))
for group in groups:group.set_editor_property('material',mi)
groom.set_editor_property('hair_groups_materials',groups)
bp=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
lib=unreal.SubobjectDataBlueprintFunctionLibrary
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
hair=next(lib.get_object_for_blueprint(lib.get_data(h),bp) for h in sub.k2_gather_subobject_data_for_blueprint(bp) if str(lib.get_variable_name(lib.get_data(h)))=='Hair')
seq=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
binding=next(b for b in seq.get_bindings() if str(b.get_display_name())=='Player')
template=unreal.MovieSceneBindingExtensions.get_object_template(binding)
seq_hair=next((c for c in template.get_components_by_class(unreal.GroomComponent) if c.get_name().removesuffix('_GEN_VARIABLE')=='Hair'),None)
rows=[]
for c in [c for c in (hair,seq_hair) if c]:
    before=(c.get_relative_transform().export_text(),str(c.get_editor_property('attachment_name')),str(c.get_editor_property('binding_asset')),c.get_editor_property('groom_asset').get_path_name())
    old=c.get_material(0).get_path_name();c.set_material(0,mi)
    after=(c.get_relative_transform().export_text(),str(c.get_editor_property('attachment_name')),str(c.get_editor_property('binding_asset')),c.get_editor_property('groom_asset').get_path_name())
    assert before==after and c.get_material(0)==mi
    rows.append(dict(component=c.get_path_name(),before=old,after=mi.get_path_name(),contract=after))
for asset in (groom,bp):assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
if seq_hair:assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
Path('P:/FoA/Saved/Integration/cinematic_audit/dark_groom_apply.json').write_text(json.dumps(rows,indent=2))
print('DARK_GROOM_ASSIGNED',json.dumps(rows))
