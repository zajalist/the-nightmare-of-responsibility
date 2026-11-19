"""Preserve the matching source body's physics and DNA on its geometry-only cut body.
FOA_BODY_SOURCE is required; never guess which MetaHuman physique generated the clothing.
"""
import os
import unreal

source_path=os.environ.get('FOA_BODY_SOURCE')
assert source_path, 'Set FOA_BODY_SOURCE to the exact calibrated body used for this cut mesh'
source = unreal.load_asset(source_path)
target = unreal.load_asset("/Game/FoA/Characters/Player/Clothing/SK_FoA_Body_Suited")
assert source and target and source.get_editor_property("skeleton") == target.get_editor_property("skeleton")
# Shared skeleton names do not establish compatible DNA after body proportion edits.
# Inspect each mesh's own bind pose before copying calibration or physics.
src_component=unreal.SkeletalMeshComponent();src_component.set_skeletal_mesh_asset(source)
dst_component=unreal.SkeletalMeshComponent();dst_component.set_skeletal_mesh_asset(target)
assert src_component.get_num_bones()==dst_component.get_num_bones(), 'Body bone counts differ'
for i in range(src_component.get_num_bones()):
    name=src_component.get_bone_name(i);j=dst_component.get_bone_index(name)
    assert j>=0 and src_component.get_parent_bone(name)==dst_component.get_parent_bone(name), name
    a=src_component.get_ref_pose_transform(i);b=dst_component.get_ref_pose_transform(j)
    assert (a.translation-b.translation).length()<.001, ('Ref translation differs; wrong DNA source',name)
    assert (a.scale3d-b.scale3d).length()<1e-5, ('Ref scale differs',name)
    dot=abs(a.rotation.x*b.rotation.x+a.rotation.y*b.rotation.y+a.rotation.z*b.rotation.z+a.rotation.w*b.rotation.w)
    assert dot>1-1e-6, ('Ref rotation differs; wrong DNA source',name)
assert source.get_editor_property('physics_asset'), 'Build the new source body physics before copying it'
assert source.get_editor_property('post_process_anim_blueprint'), 'Source body requires its correct post process'
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(target)
original_data = source.get_editor_property("asset_user_data")
target_data = target.get_editor_property("asset_user_data")
dna = [d for d in original_data if d.get_class().get_name() == "DNAAssetUserData"]
assert dna, "Inspect the original body's calibration data before proceeding"
for item in dna:
    assert item.get_editor_property("dna_asset"), "Original body must have actual DNA, not only a wrapper"
    clone = next((d for d in target_data if d.get_class() == item.get_class()), None)
    if not clone:
        clone = type(item)(outer=target, name="FoA_BodyDNA")
        target_data.append(clone)
    clone.set_editor_property("dna_asset", item.get_editor_property("dna_asset"))
target.set_editor_property("physics_asset", source.get_editor_property("physics_asset"))
target.set_editor_property('post_process_anim_blueprint',source.get_editor_property('post_process_anim_blueprint'))
target.set_editor_property("asset_user_data", target_data)
assert target.get_editor_property("physics_asset") == source.get_editor_property("physics_asset")
assert any(d.get_class().get_name() == "DNAAssetUserData" and d.get_editor_property("dna_asset") == dna[0].get_editor_property("dna_asset") for d in target.get_editor_property("asset_user_data"))
unreal.EditorAssetLibrary.save_loaded_asset(target, False)
print("Suited body retains matching source physics, post process and DNA calibration",source_path)
