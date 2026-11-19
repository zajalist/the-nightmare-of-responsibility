"""Print the three earned C.V. revisions onto the existing 3D paper."""
from pathlib import Path

ROOT='/Game/FoA/Level2/Journey/CVRevisions'
OUT=Path('P:/FoA/Saved/Integration/l2_followup')
REVISIONS=(('Interior management','Five years of experience.'),
           ('Warehousing and office logistics','Three years of experience.'),
           ('Available immediately.','Reliable under pressure.'))


def generate():
    from PIL import ImageDraw, ImageFont
    from cv_paper import texture, FONT
    OUT.mkdir(parents=True,exist_ok=True)
    for stage in range(1,4):
        image=texture();draw=ImageDraw.Draw(image)
        draw.rectangle((146,680,1390,825),fill=(230,230,230))
        for index,lines in enumerate(REVISIONS[:stage]):
            for offset,line in enumerate(lines):
                font=ImageFont.truetype(str(FONT/('DarkerGrotesque-'+('SemiBold' if not offset else 'Medium')+'.ttf')),92)
                pos=(160,(680,1210,1720)[index]+offset*92)
                assert draw.textbbox(pos,line,font=font)[2]<1376,line
                draw.text(pos,line,font=font,fill=(27,27,27))
        image.save(OUT/f'T_CVRevision{stage}.png')


def apply_print(g,paper):
    from build_journey import INSPECT
    mesh='/Game/FoA/Level2/Journey/Paper/SM_L2CVPaper/StaticMeshes/SM_L2CVPaper'
    for index in range(3):
        variant=f'{ROOT}/SM_CVRevision{index+1}'
        mesh=g.math('SelectObject',A=variant,B=mesh,bSelectA=g.getv('Edited'+str(index)))
    mesh=g.cast(mesh,'/Script/Engine.StaticMesh','Static Mesh')
    g.do('/Script/Engine.StaticMeshComponent:SetStaticMesh',self=g.getv('ItemMesh',paper,INSPECT),NewMesh=mesh)


def import_textures():
    import unreal as u
    for stage in range(1,4):
        name=f'T_CVRevision{stage}';path=f'{ROOT}/{name}'
        if not u.EditorAssetLibrary.does_asset_exist(path):
            task=u.AssetImportTask()
            for k,v in [('filename',str(OUT/(name+'.png'))),('destination_path',ROOT),('automated',True)]:
                task.set_editor_property(k,v)
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        asset=u.load_asset(path);assert asset and asset.blueprint_get_size_x()==1536
        asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        asset.set_editor_property('never_stream',True)
        assert u.EditorAssetLibrary.save_loaded_asset(asset)


def materials():
    from finalize_l2_graphs import call, h
    from cv_paper_setup import PRINT_MATERIAL
    path=PRINT_MATERIAL
    nodes=call('material_get_info',path=path)['expressions']
    uv=next(n['id'] for n in nodes if n['class']=='MaterialExpressionCustom')
    existing=next((n['id'] for n in nodes if n['class']=='MaterialExpressionTextureSampleParameter2D'),None)
    if not existing:
        base='/Game/FoA/Level2/Journey/Paper/SM_L2CVPaper/Textures/T_L2CVPaper.T_L2CVPaper'
        existing=call('material_add_node',material_path=path,expression_class='MaterialExpressionTextureSampleParameter2D',
                      node_pos=[-150,0],properties={'ParameterName':'CVPrint','Texture':base})['node_id']
        call('material_connect_nodes',material_path=path,from_node=uv,to_node=existing,to_input='Coordinates')
        call('material_connect_nodes',material_path=path,from_node=existing,from_output_index=0,to_property='emissive_color')
    call('material_compile',material_path=path);call('asset_save',asset_paths=[path])
    for stage in range(1,4):
        name=f'MI_CVRevision{stage}';instance=f'{ROOT}/{name}'
        if not h.call('material_get_info',{'path':instance}).get('ok'):
            call('material_create_instance',parent_material_path=path,package_path=ROOT,name=name)
        call('material_set_param',instance_path=instance,param_name='CVPrint',value=f'{ROOT}/T_CVRevision{stage}')
        call('asset_save',asset_paths=[instance])


def bind_meshes():
    import unreal as u
    source='/Game/FoA/Level2/Journey/Paper/SM_L2CVPaper/StaticMeshes/SM_L2CVPaper'
    for stage in range(1,4):
        path=f'{ROOT}/SM_CVRevision{stage}'
        mesh=(u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path)
              else u.EditorAssetLibrary.duplicate_asset(source,path))
        material=u.load_asset(f'{ROOT}/MI_CVRevision{stage}')
        assert mesh and material
        mesh.set_material(0,material)
        assert u.EditorAssetLibrary.save_loaded_asset(mesh)


if __name__=='__main__':
    import os
    import sys
    if sys.argv[1:]==['generate']:generate()
    else:
        assert os.environ.get('FOA_LEASE')
        {'textures':import_textures,'meshes':bind_meshes}[os.environ['FOA_CV_REVISION_STEP']]()
