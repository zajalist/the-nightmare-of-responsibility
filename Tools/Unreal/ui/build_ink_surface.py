"""One texture-free ink backplate for existing in-game UI, authored through native Hayba."""
import json
import sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h

P='/Game/FoA/UI/Materials/M_UI_InkSurface'
CODE='''
float2 q = saturate(UV);
float tooth = frac(sin(dot(floor(q*float2(820,190)),float2(12.9898,78.233)))*43758.5453);
float edge = min(min(q.x,1-q.x)*5.0,min(q.y,1-q.y));
float bleed = .011*sin(q.x*47.0+q.y*11.0)+.007*sin(q.x*109.0-q.y*29.0);
float coverage = smoothstep(.003,.075,edge+bleed);
float paper = .965+.035*tooth;
return float4(float3(.009,.010,.012)*paper,coverage*(.83+.035*tooth));
'''

def main():
    owner=h.agent_id() or 'main:presentation'
    assert not h.call('editor_get_state')['data']['pie_running'], 'User PIE active'
    lease=h.lease_acquire(owner,['asset:'+P],ttl_s=60,wait_s=3)
    def c(cmd,**params):
        r=h.call(cmd,params,owner=owner,lease=lease);assert r.get('ok'),r
        d=r.get('data',{});assert d.get('ok',True) and not d.get('has_errors') and not d.get('failed'),d
        return d
    try:
        assert not c('editor_get_state')['pie_running']
        if not Path('Content/FoA/UI/Materials/M_UI_InkSurface.uasset').exists():
            c('material_create',package_path='/Game/FoA/UI/Materials',name='M_UI_InkSurface')
        info=c('material_get_info',path=P)
        if info.get('expressions'):
            custom=next(x for x in info['expressions'] if x['class']=='MaterialExpressionCustom')
            c('material_set_node',material_path=P,node_id=custom['id'],properties={'Code':CODE})
        else:
            c('material_set_property',material_path=P,properties={'domain':'EMaterialDomain::MD_UI','blend_mode':'BLEND_Translucent'})
            def node(cls,x,y,**props):
                return c('material_add_node',material_path=P,expression_class=cls,node_pos=[x,y],properties=props)['node_id']
            uv=node('MaterialExpressionTextureCoordinate',-700,0)
            ink=node('MaterialExpressionCustom',-430,0,Description='Ink edge',OutputType='CMOT_Float4',Code=CODE,Inputs=[{'InputName':'UV'}])
            rgb=node('MaterialExpressionComponentMask',-110,-80,R=True,G=True,B=True,A=False)
            alpha=node('MaterialExpressionComponentMask',-110,160,R=False,G=False,B=False,A=True)
            c('material_connect_nodes',material_path=P,from_node=uv,to_node=ink,to_input='UV')
            for out in (rgb,alpha):c('material_connect_nodes',material_path=P,from_node=ink,to_node=out,to_input='Input')
            c('material_connect_nodes',material_path=P,from_node=rgb,to_property='emissive')
            c('material_connect_nodes',material_path=P,from_node=alpha,to_property='opacity')
            c('material_add_comment',material_path=P,text='Soft ink coverage',node_pos=[-760,-160],size=[940,500],color=[.15,.18,.20])
        c('material_validate',material_path=P)
        result=c('material_compile',material_path=P)
        assert not result.get('errors') and result.get('saved'),result
        Path('Saved/PresentationReview/ink_surface_compile.json').write_text(json.dumps(result,indent=1))
        print('Ink surface: four expressions, no texture samples',result)
    finally:h.release(owner,lease)

if __name__=='__main__':main()
