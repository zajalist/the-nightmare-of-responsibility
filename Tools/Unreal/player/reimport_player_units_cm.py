"""Reimport owned garments from true-centimetre FBX and reject mismatched reference scales before save."""
import os,json,math
from pathlib import Path
import unreal
FOLDER='/Game/FoA/Characters/Player/Clothing'
original=unreal.load_asset('/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh')
skeleton=original.get_editor_property('skeleton')
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
ref=unreal.SkeletalMeshComponent();ref.set_skeletal_mesh_asset(original)
reference={str(ref.get_bone_name(i)):ref.get_ref_pose_transform(i)for i in range(ref.get_num_bones())}
mode=os.environ.get('FOA_UNIT_BUNDLE','SuitPair')
names=('Suit','Body_Suited')if mode=='SuitPair'else ('Shirt','Trousers','Tie','Socks','Boots_Worn')
def rotation_error_degrees(a,b):
 av=[a.x,a.y,a.z,a.w];bv=[b.x,b.y,b.z,b.w]
 norm=lambda v:math.sqrt(sum(x*x for x in v))
 return math.degrees(2*math.acos(min(1,abs(sum(x*y for x,y in zip(av,bv))/(norm(av)*norm(bv))))))
report={}
for suffix in names:
 name='SK_FoA_'+suffix;path=FOLDER+'/'+name;mesh=unreal.load_asset(path)
 assert mesh and mesh.get_editor_property('skeleton')==skeleton,path
 unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(mesh)
 metadata={k:mesh.get_editor_property(k)for k in ('materials','physics_asset','post_process_anim_blueprint','asset_user_data')}
 options=unreal.FbxImportUI()
 for key,value in (('import_as_skeletal',True),('import_mesh',True),('import_animations',False),('create_physics_asset',False),
  ('import_materials',False),('import_textures',False),('skeleton',skeleton),('automated_import_should_detect_type',False),
  ('mesh_type_to_import',unreal.FBXImportType.FBXIT_SKELETAL_MESH)):options.set_editor_property(key,value)
 data=options.get_editor_property('skeletal_mesh_import_data')
 data.set_editor_property('import_uniform_scale',1.0);data.set_editor_property('update_skeleton_reference_pose',False)
 data.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
 task=unreal.AssetImportTask()
 for key,value in (('filename',os.environ.get('FOA_CLOTHING_SOURCE','P:/FoA-Assets/character/units_cm')+'/'+name+'.fbx'),('destination_path',FOLDER),
  ('destination_name',name),('automated',True),('replace_existing',True),('save',False),('options',options)):task.set_editor_property(key,value)
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 mesh=unreal.load_asset(path)
 imported_slots=mesh.get_editor_property('materials')
 hidden_slot=next((i for i,slot in enumerate(imported_slots)if 'FoA_CoveredSkin' in str(slot.get_editor_property('material_slot_name'))),None)
 for k,v in metadata.items():
  if k!='materials' or hidden_slot is None:mesh.set_editor_property(k,v)
 if hidden_slot is not None:
  assert suffix=='Body_Suited','Hidden anatomy section belongs only to suited Body'
  hidden=unreal.load_asset('/MetaHumanCharacter/Materials/M_Hide')
  assert hidden,'Use the existing MH invisible material'
  skin=metadata['materials'][0].get_editor_property('material_interface')
  for i,slot in enumerate(imported_slots):slot.set_editor_property('material_interface',hidden if i==hidden_slot else skin)
  mesh.set_editor_property('materials',imported_slots)
 assert mesh.get_editor_property('skeleton')==skeleton
 component=unreal.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
 scales=[];positions=[];angles=[]
 for i in range(component.get_num_bones()):
  bone=str(component.get_bone_name(i));t=component.get_ref_pose_transform(i)
  assert bone in reference,(name,bone)
  r=reference[bone]
  scales.append((t.scale3d-r.scale3d).length())
  positions.append((t.translation-r.translation).length())
  angles.append(rotation_error_degrees(t.rotation,r.rotation))
 assert max(scales)<.001,(name,'reference scale mismatch',max(scales))
 assert max(positions)<.02,(name,'reference translation mismatch cm',max(positions))
 assert max(angles)<.25,(name,'reference rotation mismatch degrees',max(angles))
 assert component.get_num_bones()==len(reference),(name,'bone count')
 if hidden_slot is None:assert mesh.get_editor_property('materials')==metadata['materials']
 else:assert mesh.get_editor_property('materials')[hidden_slot].get_editor_property('material_interface')==hidden
 if suffix=='Body_Suited':
  assert mesh.get_editor_property('physics_asset')==original.get_editor_property('physics_asset')
  assert mesh.get_editor_property('post_process_anim_blueprint')==original.get_editor_property('post_process_anim_blueprint')
  dna=lambda m:next(d.get_editor_property('dna_asset')for d in m.get_editor_property('asset_user_data')if d.get_class().get_name()=='DNAAssetUserData')
  assert dna(mesh)==dna(original)
 report[name]={'bone_count':component.get_num_bones(),'max_scale_error':max(scales),'max_translation_error_cm':max(positions),'max_rotation_error_degrees':max(angles),'import_uniform_scale':1}
 print('VALIDATED',name,report[name])
# Save only after the whole bundle passes original skeleton/bind/metadata checks.
for suffix in names:assert unreal.EditorAssetLibrary.save_asset(FOLDER+'/SK_FoA_'+suffix,False)
Path('P:/FoA/Saved/CharacterShots/units_cm_applied_'+mode+'.json').write_text(json.dumps(report,indent=2))
print('PASS centimetre mesh bundle',mode)
