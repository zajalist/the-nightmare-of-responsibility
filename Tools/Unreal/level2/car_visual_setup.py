"""Owned sedan import/template setup; run only inside the parent's granted asset lease.

No PIE, map changes, deletes or Blueprint compilation. Parent native-compiles and
saves BP_L2Car immediately after this script, before releasing the lease.
"""
import json
import os
from pathlib import Path
import unreal

ROOT='/Game/FoA/Level2/Drive'
DEST=ROOT+'/SM_L2Sedan'
CAR=ROOT+'/BP_L2Car'
SOURCE='P:/FoA/Saved/Codex/l2_drive/generated/SM_L2Sedan.gltf'
MATERIALS=(ROOT+'/MI_L2CarPaint',ROOT+'/MI_L2CarTrim')
EAL=unreal.EditorAssetLibrary


def find_sedan():
    # The Interchange importer may retain a scene-name/StaticMeshes subfolder.
    paths=EAL.list_assets(DEST,recursive=True,include_folder=False) if EAL.does_directory_exist(DEST) else []
    if EAL.does_asset_exist(DEST):paths.append(DEST)
    meshes=[]
    for path in paths:
        if str(EAL.find_asset_data(path).asset_class_path.asset_name)=='StaticMesh':
            meshes.append(EAL.load_asset(path))
    assert len(meshes)<=1,('Expected one owned sedan mesh',paths)
    return meshes[0] if meshes else None


def assign_materials(mesh):
    slots=mesh.get_editor_property('static_materials')
    assert len(slots)==2,('Sedan needs two material slots',len(slots))
    resolved=[]
    for i,slot in enumerate(slots):
        name=str(slot.get_editor_property('material_slot_name'))
        index=1 if 'MI_L2Dark' in name else 0 if 'M_L2Flat' in name else i
        material=unreal.load_asset(MATERIALS[index]);assert material,MATERIALS[index]
        mesh.set_material(i,material);resolved.append(material)
    assert len({m.get_path_name() for m in resolved})==2,'Importer collapsed light/dark slot identity'
    return resolved


def apply_to_components(components,mesh):
    materials=assign_materials(mesh)
    body=components['Body'];body.set_static_mesh(mesh)
    for name,value in [('relative_location',unreal.Vector(0,0,0)),('relative_rotation',unreal.Rotator(0,0,0)),
                       ('relative_scale3d',unreal.Vector(1,1,1)),('cast_shadow',True),
                       ('visible',True),('hidden_in_game',False)]:body.set_editor_property(name,value)
    body.set_collision_profile_name('NoCollision')
    for slot,material in enumerate(materials):body.set_material(slot,material)
    roof=components['Roof'];roof.set_static_mesh(None)
    roof.set_editor_property('visible',False);roof.set_editor_property('hidden_in_game',True)
    roof.set_editor_property('cast_shadow',False);roof.set_collision_profile_name('NoCollision')


def main():
    assert os.environ.get('FOA_LEASE'),'Parent asset lease required'
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(),'Stop PIE first'
    mesh=find_sedan()
    before=set(EAL.list_assets(DEST,recursive=True,include_folder=False)) if EAL.does_directory_exist(DEST) else set()
    if mesh is None:
        assert Path(SOURCE).is_file(),SOURCE
        # Same tested project pipeline as player/import_hero_test.py; reuse materials.
        pipe=unreal.InterchangeGenericAssetsPipeline()
        material=pipe.get_editor_property('material_pipeline')
        material.set_editor_property('import_materials',False)
        material.get_editor_property('texture_pipeline').set_editor_property('import_textures',False)
        task=unreal.AssetImportTask()
        for key,value in [('filename',SOURCE),('destination_path',DEST),('automated',True),
                          ('replace_existing',False),('save',True),('options',pipe)]:task.set_editor_property(key,value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=find_sedan();assert mesh,task.get_editor_property('imported_object_paths')
    bounds=mesh.get_bounds();size=[2*v for v in bounds.box_extent.to_tuple()]
    assert 400<size[0]<500 and 180<size[1]<240 and 130<size[2]<170,('Unexpected import axes/units',size)
    bp=unreal.load_asset(CAR);assert bp,CAR
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    components={str(lib.get_variable_name(lib.get_data(h))):lib.get_object_for_blueprint(lib.get_data(h),bp)
                for h in subsystem.k2_gather_subobject_data_for_blueprint(bp)}
    apply_to_components(components,mesh)
    assert EAL.save_loaded_asset(mesh)
    after=set(EAL.list_assets(DEST,recursive=True,include_folder=False))
    report=dict(mesh=mesh.get_path_name(),size_cm=size,materials=[mesh.get_material(i).get_path_name() for i in range(2)],
                imported=[dict(path=p,kind=str(EAL.find_asset_data(p).asset_class_path.asset_name)) for p in sorted(after-before)],
                blueprint=CAR,blueprint_compile_save_required=True)
    output=Path('P:/FoA/Saved/Integration/sedan_import.json');output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
