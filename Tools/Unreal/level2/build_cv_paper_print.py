"""Correct the imported front-face UV handedness with a readable paper material."""
import json
import os
from pathlib import Path

from cv_paper_setup import PRINT_MATERIAL, ROOT, TABLE
from finalize_l2_graphs import call, h
import editor_lock


def apply():
    owner='main-cv-paper-print'
    os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner)
    token=editor_lock.acquire(owner,wait_s=10,ttl=75,areas=[ROOT,TABLE])
    os.environ['FOA_LEASE']=token
    try:
        assert not call('editor_get_state')['pie_running']
        path=PRINT_MATERIAL
        texture=json.loads(Path('P:/FoA/Saved/Codex/l2_cv_paper/native_setup.json').read_text())['texture']
        if not h.call('material_get_info',{'path':path}).get('ok'):
            call('material_create',package_path=ROOT,name=path.rsplit('/',1)[1])
        call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/close_ui_editors.py',
             env={'FOA_ASSETS':path},resources=['asset:'+ROOT])

        def node(kind,x,**properties):
            existing=[n for n in call('material_get_info',path=path)['expressions'] if n['class']=='MaterialExpression'+kind]
            assert len(existing)<=1,existing
            if existing:return existing[0]['id']
            return call('material_add_node',material_path=path,expression_class='MaterialExpression'+kind,
                        node_pos=[x,0],properties=properties)['node_id']

        uv=node('TextureCoordinate',-700)
        flip=node('Custom',-450,Description='Readable front UV',OutputType='CMOT_Float2',
                  Inputs=[{'InputName':'UV'}],Code='return float2(1 - UV.x, UV.y);')
        sample=node('TextureSampleParameter2D',-160,ParameterName='CVPrint',Texture=texture,SamplerType='SAMPLERTYPE_Color')
        for src,dest,pin in ((uv,flip,'UV'),(flip,sample,'Coordinates')):
            call('material_connect_nodes',material_path=path,from_node=src,to_node=dest,to_input=pin)
        call('material_connect_nodes',material_path=path,from_node=sample,from_output_index=0,to_property='emissive_color')
        call('material_set_property',material_path=path,properties={'shading_model':'Unlit'})
        call('material_validate',material_path=path)
        call('material_compile',material_path=path)
        call('asset_save',asset_paths=[path])
        call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/cv_paper_setup.py',env={'FOA_LEASE':token},
             resources=['asset:'+ROOT,'asset:'+TABLE])
        print('Readable print material bound to paper',flush=True)
    finally:editor_lock.release(owner)


if __name__=='__main__':apply()
