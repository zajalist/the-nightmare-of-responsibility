"""Dream-only faithful ellipse material. Native CLI requires an explicit parent writer grant.
Duplicates the existing dream material once, retaining its shared dynamics and black-sand behavior.
"""
import json
import os
from pathlib import Path
import sys
import time
sys.path[:0]=[str(Path(__file__).resolve().parent),'P:/FoA/Tools/Unreal']
import hayba_call as h
import build_splat_world_lean as base
import dream_ellipse

MAT='/Game/FoA/Level2/M_SplatWorld_Aniso'

def apply(call):
    before=call('material_get_info',path=MAT)
    byid={node['id']:node for node in before['expressions']}
    assert byid['MaterialExpressionCustom_0']['class']=='MaterialExpressionCustom'
    assert any(n['class']=='MaterialExpressionMaterialFunctionCall' for n in byid.values()),'Preserve dynamics clone'
    specs=[('cov0','TextureCoordinate',[-1500,-200],dict(CoordinateIndex=2)),
           ('cov1','TextureCoordinate',[-1500,0],dict(CoordinateIndex=3)),
           ('cov2','TextureCoordinate',[-1500,200],dict(CoordinateIndex=4)),
           ('camera','CameraPositionWS',[-1500,400],{}),
           ('rest','WorldPosition',[-1500,600],dict(WorldPositionShaderOffset='WPT_ExcludeAllShaderOffsets'))]
    original=base.call;base.call=call
    try:ids,_=base.nodes(MAT,specs)
    finally:base.call=original
    call('material_set_node',material_path=MAT,node_id='MaterialExpressionCustom_0',properties=dict(
        Description='Projected source ellipse',Code=dream_ellipse.BILLBOARD,
        Inputs=[dict(InputName=n) for n in ('Corner','RS','Scale','Cov0','Cov1','Cov2','WP','Cam')]))
    sources={'Corner':'MaterialExpressionTextureCoordinate_0','RS':'MaterialExpressionTextureCoordinate_1',
             'Scale':'MaterialExpressionScalarParameter_0','Cov0':ids['cov0'],'Cov1':ids['cov1'],
             'Cov2':ids['cov2'],'WP':ids['rest'],'Cam':ids['camera']}
    for pin,node in sources.items():
        call('material_connect_nodes',material_path=MAT,from_node=node,from_output_index=0,
             to_node='MaterialExpressionCustom_0',to_input=pin)
    call('material_set_node',material_path=MAT,node_id='MaterialExpressionCustom_1',properties=dict(
        Description='Source Gaussian opacity',Code=dream_ellipse.COVERAGE))
    call('material_set_node',material_path=MAT,node_id='MaterialExpressionScalarParameter_0',properties=dict(DefaultValue=1.0))
    call('material_set_node',material_path=MAT,node_id='MaterialExpressionScalarParameter_1',properties=dict(DefaultValue=4.5))
    if not any(c.get('text')=='Source covariance' for c in before.get('comments',[])):
        call('material_add_comment',material_path=MAT,text='Source covariance',node_pos=[-1580,-280],size=[440,1080],color=[.1,.2,.35])
    for c in call('material_get_info',path=MAT).get('comments',[]):
        call('material_set_comment',material_path=MAT,comment_id=c['id'],show_bubble=True,color_bubble=True)
    result=call('material_compile',material_path=MAT)
    call('asset_save',asset_paths=[MAT])
    return result

def main():
    owner='main-splat-aniso';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner)
    resources=['asset:'+MAT];token=h.lease_acquire(owner,resources,ttl_s=60,wait_s=3)
    os.environ['FOA_LEASE']=token;renewed=time.monotonic()
    def call(command,**params):
        nonlocal renewed
        if time.monotonic()-renewed>20:
            assert h.call('lease_renew',dict(token=token,ttl_s=60),owner=owner).get('ok');renewed=time.monotonic()
        result=h.call(command,params,owner=owner,timeout=45);assert result.get('ok'),result
        data=result.get('data',{});assert data.get('ok',True) and not data.get('has_errors') and not data.get('errors'),data
        return data
    try:
        assert not call('editor_get_state')['pie_running']
        native=str(Path(__file__).with_name('dream_aniso_native.py'))
        call('python_exec_file',path=native,resources=resources,env=dict(FOA_LEASE=token,FOA_SPLAT_ANISO_STEP='clone'))
        result=apply(call)
        Path('P:/FoA/Saved/Integration/splat_visual_20261112/aniso_compile.json').write_text(json.dumps(result,indent=1))
        call('python_exec_file',path=native,resources=resources,env=dict(FOA_LEASE=token,FOA_SPLAT_ANISO_STEP='capture'))
    finally:h.release(owner,token)

if __name__=='__main__':main()
