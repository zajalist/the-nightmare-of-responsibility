"""Use the engine's reference-compensated head-bone binding for short01 strands."""
import json,shutil,datetime
from pathlib import Path
import unreal

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
root='/Game/FoA/Characters/Teen'
groom=unreal.load_asset(root+'/Hair/GR_Teen_Scalp')
bp=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
parts={str(lib.get_variable_name(lib.get_data(h))):lib.get_object_for_blueprint(lib.get_data(h),bp)
       for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
hair=parts['Hair'];face=parts['Face']
assert face.get_skinned_asset()==unreal.load_asset(root+'/Mesh/SK_Teen_Head')
assert hair.get_editor_property('groom_asset')==groom
backup=Path('P:/FoA/Saved/Backups/rigid_groom')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup.mkdir(parents=True)
for path in ('Content/FoA/Characters/Teen/Hair/GR_Teen_Scalp.uasset','Content/FoA/Characters/Player/BP_FoAPlayer.uasset'):
    shutil.copy2(Path('P:/FoA')/path,backup/Path(path).name)
before={'binding':str(hair.get_editor_property('binding_asset')),'attachment_name':str(hair.get_editor_property('attachment_name')),
        'head':face.get_skinned_asset().get_path_name(),'head_transform':face.get_relative_transform().export_text(),
        'head_materials':[str(face.get_material(i)) for i in range(face.get_num_materials())]}
groups=list(groom.get_editor_property('hair_groups_lod'))
before['lod_bindings']=[[str(l.get_editor_property('binding_type')) for l in g.get_editor_property('lods')] for g in groups]
for group in groups:
    lods=list(group.get_editor_property('lods'))
    for lod in lods:lod.set_editor_property('binding_type',unreal.GroomBindingType.RIGID)
    group.set_editor_property('lods',lods)
groom.set_editor_property('hair_groups_lod',groups)
hair.set_binding_asset(None)
hair.set_editor_property('attachment_name','head')
# GroomComponent's native tick attaches to this bone and applies the inverse reference-head transform.
# This preserves the original full-character-space strand coordinates and follows the animated bone.
assert face.get_relative_transform().export_text()==before['head_transform']
assert [str(face.get_material(i)) for i in range(face.get_num_materials())]==before['head_materials']
assert unreal.EditorAssetLibrary.save_loaded_asset(groom,False)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
report={'backup':str(backup),'before':before,'attachment_name':'head','binding':None,'groom':groom.get_path_name()}
Path('P:/FoA/Saved/CharacterShots/groom_pose/rigid_applied.json').write_text(json.dumps(report,indent=1))
print('RIGID_GROOM_APPLIED',json.dumps(report))
