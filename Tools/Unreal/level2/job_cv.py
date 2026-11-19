"""Print earned jobs onto the existing A4 inspect mesh, for any completion order."""

import os
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from job_hunt_data import JOBS

ROOT='/Game/FoA/Level2/Journey/JobRecords'
SOURCE='/Game/FoA/Level2/Journey/Paper/SM_L2CVPaper/StaticMeshes/SM_L2CVPaper'
OUT=Path('P:/FoA/Saved/Integration/job_hunt/paper')


def generate(masks):
    from PIL import Image, ImageDraw, ImageFont
    from cv_paper import FONT
    from textwrap import wrap
    OUT.mkdir(parents=True,exist_ok=True)
    for mask in masks:
        image=Image.new('RGB',(1152,1628),(238,234,224));draw=ImageDraw.Draw(image)
        def write(x,y,text,size,weight='Medium',colour=(25,23,21)):
            font=ImageFont.truetype(str(FONT/f'DarkerGrotesque-{weight}.ttf'),size)
            assert draw.textbbox((x,y),text,font=font)[2]<=1050,text
            draw.text((x,y),text,font=font,fill=colour)
        write(100,92,'Curriculum vitae',120,'ExtraBold')
        write(100,312,'Work experience',76,'SemiBold')
        y=430
        for index,job in enumerate(JOBS):
            if not mask&(1<<index):continue
            write(100,y,job.role,71,'ExtraBold')
            write(100,y+73,job.employer,63,'SemiBold',(75,36,30))
            for offset,line in enumerate(wrap(job.evidence,width=35)):
                write(100,y+151+offset*55,line,60)
            y+=321
        image.save(OUT/f'T_JobRecord{mask}.png')


def import_assets(masks,step):
    import unreal as u
    eal=u.EditorAssetLibrary
    for mask in masks:
        if step=='textures':
            name=f'T_JobRecord{mask}';path=f'{ROOT}/{name}'
            if not eal.does_asset_exist(path):
                task=u.AssetImportTask()
                for key,value in (('filename',str(OUT/(name+'.png'))),('destination_path',ROOT),('automated',True)):
                    task.set_editor_property(key,value)
                u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            asset=u.load_asset(path);assert asset and asset.blueprint_get_size_x()==1152
            asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
            asset.set_editor_property('never_stream',True)
        else:
            path=f'{ROOT}/SM_JobRecord{mask}'
            asset=u.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset(SOURCE,path)
            material=u.load_asset(f'{ROOT}/MI_JobRecord{mask}');assert material and asset
            asset.set_material(0,material)
        assert eal.save_loaded_asset(asset,False)


def install(masks):
    from build_drive import call,h
    from cv_paper_setup import PRINT_MATERIAL
    from cv_revisions import materials
    # Keep the base print material's texture input compatible with old paper assets.
    nodes=call('material_get_info',path=PRINT_MATERIAL)['expressions']
    if not any(node['class']=='MaterialExpressionTextureSampleParameter2D' for node in nodes):materials()
    def worker(step):
        call('python_exec_file',path=str(Path(__file__).resolve()).replace('\\','/'),
             env={'FOA_JOB_CV_STEP':step,'FOA_JOB_CV_MASKS':','.join(map(str,masks))},resources=['asset:'+ROOT])
    worker('textures')
    for mask in masks:
        name=f'MI_JobRecord{mask}';path=f'{ROOT}/{name}'
        if not h.call('material_get_info',{'path':path}).get('ok'):
            call('material_create_instance',parent_material_path=PRINT_MATERIAL,package_path=ROOT,name=name)
        call('material_set_param',instance_path=path,param_name='CVPrint',value=f'{ROOT}/T_JobRecord{mask}')
        call('asset_save',asset_paths=[path])
    worker('meshes')


def apply_print(g,paper,masks=(1,)):
    from build_journey import INSPECT
    from build_job_hunt import pick
    flags=[g.math('SelectInt',A=1<<i,B=0,bPickA=g.getv(f'Edited{i}')) for i in range(len(JOBS))]
    mask=g.math('Add_IntInt',A=g.math('Add_IntInt',A=flags[0],B=flags[1]),B=flags[2])
    mesh=pick(g,'Object',[SOURCE]+[f'{ROOT}/SM_JobRecord{i}' for i in masks],mask)
    mesh=g.cast(mesh,'/Script/Engine.StaticMesh','Static Mesh')
    g.do('/Script/Engine.StaticMeshComponent:SetStaticMesh',self=g.getv('ItemMesh',paper,INSPECT),NewMesh=mesh)


def sharpen_print():
    from build_drive import call
    from cv_paper_setup import PRINT_MATERIAL
    # Draw the print after temporal accumulation while the city retains TSR.
    call('object_set_property',path=PRINT_MATERIAL,properties={'TranslucencyPass':'MTP_AfterMotionBlur',
                                                            'AllowTranslucentCustomDepthWrites':True})
    call('material_set_property',material_path=PRINT_MATERIAL,properties={'blend_mode':'Translucent'})
    result=call('material_validate',material_path=PRINT_MATERIAL);assert not result.get('has_errors'),result
    result=call('material_compile',material_path=PRINT_MATERIAL);assert not result.get('has_errors'),result
    call('asset_save',asset_paths=[PRINT_MATERIAL])


if __name__=='__main__':
    if os.environ.get('FOA_JOB_CV_STEP'):
        sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
        import_assets(tuple(map(int,os.environ['FOA_JOB_CV_MASKS'].split(','))),os.environ['FOA_JOB_CV_STEP'])
    else:
        generate(range(1,8) if sys.argv[1:]==['all'] else (1,))
