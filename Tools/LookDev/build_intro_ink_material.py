"""Reuse the existing unused story-panel master for ink rendering of actual game frames."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
P='/Game/FoA/UI/Materials/M_UI_Panel';MI='/Game/FoA/UI/Materials/MI_UI_PanelNear'
def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('has_errors') and not d.get('failed'),d
 return d
assert not c('editor_get_state')['pie_running']
owner=h.agent_id() or 'room-takeover';lease=h.lease_acquire(owner,['asset:'+P,'asset:'+MI],ttl_s=120,wait_s=30)
try:
 info=c('material_get_info',path=P)
 for box in info.get('comments',[]):c('material_delete_comment',material_path=P,comment_id=box['id'])
 for n in info.get('expressions',[]):c('material_delete_node',material_path=P,node_id=n['id'])
 c('material_set_property',material_path=P,properties={'domain':'EMaterialDomain::MD_UI','blend_mode':'BLEND_Translucent'})
 def node(cls,x,y,**props):return c('material_add_node',material_path=P,expression_class=cls,node_pos=[x,y],properties=props)['node_id']
 uv=node('MaterialExpressionTextureCoordinate',-1000,0)
 art=node('MaterialExpressionTextureObjectParameter',-1000,180,Texture='/Game/FoA/UI/Intro/Textures/T_Intro_Game01_Sleep',ParameterName='Texture')
 reveal=node('MaterialExpressionScalarParameter',-1000,380,ParameterName='Reveal',DefaultValue=1)
 ink=node('MaterialExpressionVectorParameter',-1000,580,ParameterName='Ink',DefaultValue={'R':.30,'G':.045,'B':.016,'A':.94})
 shader=node('MaterialExpressionCustom',-580,180,Description='Ink on paper',OutputType='CMOT_Float4',Code=Path('P:/FoA/Tools/LookDev/hlsl/intro_ink.hlsl').read_text(),Inputs=[{'InputName':n} for n in ('UV','Frame','Reveal','Ink')])
 for source,name in zip((uv,art,reveal,ink),('UV','Frame','Reveal','Ink')):c('material_connect_nodes',material_path=P,from_node=source,to_node=shader,to_input=name,from_output_index=0)
 rgb=node('MaterialExpressionComponentMask',-240,100,R=True,G=True,B=True,A=False);alpha=node('MaterialExpressionComponentMask',-240,300,R=False,G=False,B=False,A=True)
 for n in (rgb,alpha):c('material_connect_nodes',material_path=P,from_node=shader,to_node=n,to_input='Input')
 c('material_connect_nodes',material_path=P,from_node=rgb,to_property='emissive');c('material_connect_nodes',material_path=P,from_node=alpha,to_property='opacity')
 for title,xy,size in [('Actual frame and ink',[-1060,-70],[350,900]),('Print and reveal',[-640,40],[340,460]),('Color and coverage',[-290,20],[300,440])]:c('material_add_comment',material_path=P,text=title,node_pos=xy,size=size,color=[.18,.18,.18])
 c('material_validate',material_path=P);result=c('material_compile',material_path=P);assert not result.get('errors'),result
 if not (Path('P:/FoA/Content/FoA/UI/Materials/MI_UI_PanelNear.uasset')).exists():c('material_create_instance',parent_material_path=P,package_path=MI,name='MI_UI_PanelNear')
 c('material_set_param',instance_path=MI,param_name='Texture',value='/Game/FoA/UI/Intro/Textures/T_Intro_Game01_Sleep_Near')
 c('asset_save',asset_paths=[P,MI]);Path('P:/FoA/Saved/LookDev/intro_restored/ink_material_compile.json').write_text(json.dumps(result,indent=1));print(result)
finally:h.release(owner,lease)
