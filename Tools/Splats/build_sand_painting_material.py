"""A lit, animated canvas using existing artwork. Native Hayba asset-only build."""
import sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
P='/Game/FoA/Art/Materials/M_SandPainting'

def call(cmd,**params):
    r=h.call(cmd,params);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True) and not d.get('has_errors'),d
    return d

def main():
    assert not call('editor_get_state')['pie_running']
    lease=h.lease_acquire(h.agent_id(),['asset:'+P],ttl_s=120,wait_s=30)
    try:
        if not h.call('material_get_info',{'path':P}).get('ok'):
            call('material_create',package_path=P,name='M_SandPainting')
        call('material_set_property',material_path=P,properties={'blend_mode':'Masked','shading_model':'DefaultLit','two_sided':True,'opacity_mask_clip_value':.2})
        expr=call('material_get_info',path=P).get('expressions',[])
        for n in expr:
            if n['class']=='MaterialExpressionTextureObject':call('material_delete_node',material_path=P,node_id=n['id'])
        def node(cls,x,y,**props):
            old=next((n for n in expr if n['class']==cls and [n.get('x'),n.get('y')]==[x,y]),None)
            if old:
                if props:call('material_set_node',material_path=P,node_id=old['id'],properties=props)
                return old['id']
            return call('material_add_node',material_path=P,expression_class=cls,node_pos=[x,y],properties=props)['node_id']
        uv=node('MaterialExpressionTextureCoordinate',-1000,0)
        art=node('MaterialExpressionTextureObjectParameter',-1000,160,Texture='/Game/FoA/Art/Textures/T_Art_Whistlejacket',ParameterName='Art')
        time=node('MaterialExpressionTime',-1000,380)
        stage=node('MaterialExpressionScalarParameter',-1000,520,ParameterName='PaintingStage',DefaultValue=0,bUseCustomPrimitiveData=True,PrimitiveDataIndex=0)
        pulse=node('MaterialExpressionScalarParameter',-1000,680,ParameterName='PaintingPulse',DefaultValue=-100,bUseCustomPrimitiveData=True,PrimitiveDataIndex=1)
        reduce=node('MaterialExpressionCollectionParameter',-1000,840,Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream',ParameterName='ReduceMotion')
        shader=node('MaterialExpressionCustom',-550,200,Description='Sand becomes a picture',OutputType='CMOT_Float4',Code=Path('P:/FoA/Tools/Splats/hlsl/sand_painting.hlsl').read_text(),Inputs=[{'InputName':n} for n in ('UV','Art','Clock','Stage','Pulse','ReduceMotion')])
        for source,name in zip((uv,art,time,stage,pulse,reduce),('UV','Art','Clock','Stage','Pulse','ReduceMotion')):
            call('material_connect_nodes',material_path=P,from_node=source,to_node=shader,to_input=name,from_output_index=0)
        rgb=node('MaterialExpressionComponentMask',-250,100,R=True,G=True,B=True,A=False)
        alpha=node('MaterialExpressionComponentMask',-250,300,R=False,G=False,B=False,A=True)
        for n in (rgb,alpha):call('material_connect_nodes',material_path=P,from_node=shader,to_node=n,to_input='Input')
        rough=node('MaterialExpressionConstant',-250,500,R=.88);spec=node('MaterialExpressionConstant',-250,650,R=.12)
        for n,p in ((rgb,'base_color'),(alpha,'opacity_mask'),(rough,'roughness'),(spec,'specular')):
            call('material_connect_nodes',material_path=P,from_node=n,to_property=p)
        if not call('material_get_info',path=P).get('comments'):
            call('material_add_comment',material_path=P,text='The canvas remembers',node_pos=[-1060,-80],size=[1130,1100],color=[.22,.18,.13])
        result=call('material_compile',material_path=P)
        assert not result.get('errors'),result
        print('Sand painting compiled',result)
    finally:h.release(h.agent_id(),lease)

if __name__=='__main__':main()
