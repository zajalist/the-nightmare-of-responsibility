"""Reimport one centimetre-native teen FBX, retaining materials and validating root scale before save."""
import json
import os
from pathlib import Path
import unreal


def run():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    root='/Game/FoA/Characters/Teen/Mesh'
    name='SK_Teen_'+os.environ['FOA_PIECE']
    path=root+'/'+name
    mesh=unreal.load_asset(path)
    assert mesh, path
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(mesh)
    old={key:mesh.get_editor_property(key) for key in ('materials','physics_asset','post_process_anim_blueprint',
                                                     'positive_bounds_extension','negative_bounds_extension')}
    before=None
    def reference(asset):
        component=unreal.SkeletalMeshComponent()
        component.set_skeletal_mesh_asset(asset)
        names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
        values=[]
        for i in range(len(names)):
            t=component.get_ref_pose_transform(i)
            values.append([t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,
                           t.scale3d.x,t.scale3d.y,t.scale3d.z])
        return names,values,[str(m.material_slot_name) for m in asset.materials]
    if os.environ.get('FOA_PRESERVE_REFERENCE')=='1':
        before=reference(mesh)
    skeleton=mesh.skeleton
    ui=unreal.FbxImportUI()
    ui.import_mesh=True
    ui.import_as_skeletal=True
    ui.automated_import_should_detect_type=False
    ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_animations=False
    ui.import_materials=False
    ui.import_textures=False
    make_physics=os.environ.get('FOA_CREATE_PHYSICS')=='1'
    ui.create_physics_asset=make_physics
    ui.skeleton=skeleton
    data=ui.skeletal_mesh_import_data
    data.import_uniform_scale=1.0
    data.set_editor_property('update_skeleton_reference_pose',name=='SK_Teen_Body' and before is None)
    data.set_editor_property('import_morph_targets',True)
    data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=unreal.AssetImportTask()
    task.filename=os.environ.get('FOA_SOURCE','P:/FoA-Assets/character/mpfb/export/teen_cm/'+name+'.fbx')
    task.destination_path=root
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.save=False
    task.options=ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=unreal.load_asset(path)
    for key,value in old.items():
        if key=='physics_asset' and make_physics and value is None:
            continue
        mesh.set_editor_property(key,value)
    if make_physics:
        assert mesh.physics_asset, 'Importer did not generate a PhysicsAsset'
        unreal.EditorAssetLibrary.save_loaded_asset(mesh.physics_asset,only_if_is_dirty=False)
    assert mesh.skeleton==skeleton
    comp=unreal.SkeletalMeshComponent()
    comp.set_skeletal_mesh_asset(mesh)
    refs=[comp.get_ref_pose_transform(i) for i in range(comp.get_num_bones())]
    error=max(abs(v-1) for t in refs for v in (t.scale3d.x,t.scale3d.y,t.scale3d.z))
    assert error < .001, (name,'bone reference scale is not 1',error)
    if name=='SK_Teen_Head':
        assert len(mesh.morph_targets)==52, len(mesh.morph_targets)
    names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
    head=unreal.Transform()
    bone='head'
    while bone in names:
        head=unreal.MathLibrary.compose_transforms(head,refs[names.index(bone)])
        bone=str(comp.get_parent_bone(bone))
    assert 160 < head.translation.z < 190, head
    reference_delta=None
    if before:
        after=reference(mesh)
        assert before[0]==after[0] and before[2]==after[2], 'Bone or material slot names changed'
        reference_delta=max(abs(a-b) for row_a,row_b in zip(before[1],after[1]) for a,b in zip(row_a,row_b))
        assert reference_delta<1e-4, reference_delta
    unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
    if name=='SK_Teen_Body':
        unreal.EditorAssetLibrary.save_loaded_asset(skeleton,only_if_is_dirty=False)
    report={'mesh':path,'bones':len(refs),'maximum_reference_scale_error':error,
            'head_reference_z_cm':head.translation.z,'head_scale':[head.scale3d.x,head.scale3d.y,head.scale3d.z],
            'morphs':len(mesh.morph_targets),'material_slots':len(mesh.materials),'reference_delta':reference_delta,
            'physics_asset':mesh.physics_asset.get_path_name() if mesh.physics_asset else None}
    Path('P:/FoA/Saved/CharacterShots/mpfb/'+name+'_cm.json').write_text(json.dumps(report,indent=2))
    print('TEEN_CM_PASS',json.dumps(report))


run()
