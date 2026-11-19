"""Import the owned paper and merge one item row, inside a granted editor lease.

python Tools/Unreal/ue_remote.py Tools/Unreal/level2/cv_paper_setup.py
Lease resources: /Game/FoA/Level2/Journey/Paper and /Game/FoA/Gameplay/DT_Items.
No map/actor edits, Blueprint edits, material-graph edits, deletes or reimports.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT='/Game/FoA/Level2/Journey/Paper'
PRINT_MATERIAL=ROOT+'/M_L2CVPrintReadable'
TABLE='/Game/FoA/Gameplay/DT_Items'
ROW='L2CVPaper'
SOURCE=Path('P:/FoA/Saved/Codex/l2_cv_paper/generated')
FIELDS={'Name','DisplayName','LookLine','Mesh','Icon','UsedBecomes','CombineWith','CombineInto'}


def merge_row(rows,mesh):
    assert rows and all(FIELDS<=set(row) for row in rows),'Unexpected item table schema'
    assert len({row['Name'] for row in rows})==len(rows),'Duplicate item rows'
    result=copy.deepcopy(rows)
    existing=next((r for r in result if r['Name']==ROW),None)
    if existing is None:
        assert set(rows[0])==FIELDS,'New item fields need explicit neutral defaults'
        existing=dict(Name=ROW,DisplayName='',LookLine='',Mesh=mesh,Icon='None',
                      UsedBecomes='None',CombineWith='None',CombineInto='None')
        result.append(existing)
    else:
        existing.update(DisplayName='',LookLine='',Mesh=mesh)
    assert [r for r in result if r['Name']!=ROW]==[r for r in rows if r['Name']!=ROW]
    return result


def validate_bounds(size):
    # Real Unreal bounds, cm; catches wrong up axis/import unit scaling.
    assert .01<size[0]<.25 and abs(size[1]-21)<.03 and abs(size[2]-29.7)<.03,('Paper axes/size',size)


def main():
    import unreal as u
    assert os.environ.get('FOA_LEASE'),'Granted parent lease required'
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(),'User/PIE session active'
    eal=u.EditorAssetLibrary
    gltf=SOURCE/'SM_L2CVPaper.gltf';png=SOURCE/'T_L2CVPaper.png'
    assert gltf.is_file() and png.is_file(),'Generate paper offline first'
    doc=json.loads(gltf.read_text());manifest=json.loads((SOURCE/'manifest.json').read_text())
    assert doc['images']==[{'uri':png.name}] and manifest['text']==[
        'Curriculum vitae','Experience','I have no job experience.','Skills','Availability']
    signature=hashlib.sha256(gltf.read_bytes()+png.read_bytes()).hexdigest()
    def owned():
        return [eal.load_asset(p) for p in eal.list_assets(ROOT,recursive=True,include_folder=False)] if eal.does_directory_exist(ROOT) else []
    assets=owned();meshes=[a for a in assets if isinstance(a,u.StaticMesh)]
    assert len(meshes)<=1,'Unexpected extra mesh in owned paper folder'
    if not meshes:
        assert not assets,'Partial prior paper import requires inspection, not duplicates'
        pipe=u.InterchangeGenericAssetsPipeline()
        material=pipe.get_editor_property('material_pipeline')
        material.set_editor_property('import_materials',True)
        material.get_editor_property('texture_pipeline').set_editor_property('import_textures',True)
        task=u.AssetImportTask()
        for key,value in [('filename',str(gltf)),('destination_path',ROOT),('automated',True),
                          ('replace_existing',False),('save',True),('options',pipe)]:task.set_editor_property(key,value)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assets=owned();meshes=[a for a in assets if isinstance(a,u.StaticMesh)]
        assert len(meshes)==1,task.get_editor_property('imported_object_paths')
    mesh=meshes[0]
    prior=str(eal.get_metadata_tag(mesh,'FoA.PaperSourceSHA256'))
    assert prior in ('','None',signature),'Generated source changed; explicit reviewed reimport needed'
    # Interchange enables Nanite; its simplified fallback is not the source sheet.
    # Disable it before inspecting triangles, preserving the thin authored edge.
    smes=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    nanite=smes.get_nanite_settings(mesh)
    if nanite.get_editor_property('enabled'):
        nanite.set_editor_property('enabled',False);smes.set_nanite_settings(mesh,nanite,True)
    assert not smes.get_nanite_settings(mesh).get_editor_property('enabled')
    size=[2*v for v in mesh.get_bounds().box_extent.to_tuple()];validate_bounds(size)
    assert mesh.get_num_triangles(0)==manifest['triangles'],'Imported paper triangle count changed'
    assert len(mesh.get_editor_property('static_materials'))==2,'Printed front/back slots missing'
    textures=[a for a in assets if isinstance(a,u.Texture2D)]
    assert len(textures)==1,('Expected exactly one printed texture',[t.get_path_name() for t in textures])
    texture=textures[0]
    dimensions=[texture.blueprint_get_size_x(),texture.blueprint_get_size_y()]
    assert dimensions==[1536,2172],('Printed text resolution',dimensions)
    # A small non-power-of-two page cannot stream mip levels; preserve sharp print.
    for key,value in [('srgb',True),('compression_settings',u.TextureCompressionSettings.TC_BC7),
                      ('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS),('never_stream',True),
                      ('max_texture_size',4096),('filter',u.TextureFilter.TF_BILINEAR)]:texture.set_editor_property(key,value)
    if eal.does_asset_exist(PRINT_MATERIAL):
        readable=eal.load_asset(PRINT_MATERIAL)
        if mesh.get_material(0)!=readable:mesh.set_material(0,readable)
    materials=[mesh.get_material(i) for i in range(2)]
    assert all(materials),'Unassigned paper material'
    # Read actual material parameter bindings, not just importer settings.
    mel=u.MaterialEditingLibrary;bound=[]
    for mat in materials:
        if isinstance(mat,u.Material):
            bound.extend(t.get_path_name() for t in mel.get_used_textures(mat))
        elif isinstance(mat,u.MaterialInstance):
            for name in mel.get_texture_parameter_names(mat):
                value=mel.get_material_instance_texture_parameter_value(mat,name)
                if value:bound.append(value.get_path_name())
    assert texture.get_path_name() in bound,('Printed texture not bound to paper material',bound)
    for asset in assets:assert eal.save_loaded_asset(asset,False),asset.get_path_name()
    table=u.load_asset(TABLE);assert table,TABLE
    lib=u.DataTableFunctionLibrary;original=lib.export_data_table_to_json_string(table)
    rows=json.loads(original);wanted=merge_row(rows,mesh.get_path_name())
    sys.path.insert(0,'P:/FoA/Tools/Unreal/flow')
    from story_text import plain
    def normalize(values):
        return {r['Name']:{k:plain(v) if k in ('DisplayName','LookLine') else v for k,v in r.items()} for r in values}
    if normalize(rows)!=normalize(wanted):
        from datetime import datetime
        backup=Path('P:/FoA/Saved/Backups/cv_paper')/datetime.now().strftime('%Y%m%d_%H%M%S')
        backup.mkdir(parents=True,exist_ok=False);(backup/'DT_Items.json').write_text(original,encoding='utf-8')
        try:
            assert lib.fill_data_table_from_json_string(table,json.dumps(wanted))
            actual=json.loads(lib.export_data_table_to_json_string(table))
            assert normalize(actual)==normalize(wanted),'Item rows changed unexpectedly'
            assert eal.save_loaded_asset(table,False)
        except Exception:
            assert lib.fill_data_table_from_json_string(table,original),'Item table rollback failed'
            assert eal.save_loaded_asset(table,False),'Item table rollback save failed'
            raise
    eal.set_metadata_tag(mesh,'FoA.PaperSourceSHA256',signature)
    assert eal.save_loaded_asset(mesh,False)
    report=dict(mesh=mesh.get_path_name(),size_cm=size,triangles=mesh.get_num_triangles(0),
        texture=texture.get_path_name(),texture_size=dimensions,bound_textures=bound,
        materials=[m.get_path_name() for m in materials],row=ROW,other_rows_preserved=len(rows)-(ROW in {r['Name'] for r in rows}),
        source_sha256=signature,native_visual_verified=False)
    (SOURCE.parent/'native_setup.json').write_text(json.dumps(report,indent=2))
    print('CV PAPER SETUP',json.dumps(report))


if __name__=='__main__':main()
