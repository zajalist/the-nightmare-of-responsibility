"""Narrow art-only update; preserve intro replay, timers, focus cleanup and layer motion."""
import json,sys,hashlib,os,argparse
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from held_tool_graphs import inspect
os.environ['HAYBA_AGENT_ID']='room-takeover'
P='/Game/FoA/UI/Materials/M_UI_Panel'
W='/Game/FoA/UI/Intro/WBP_IntroStory'
parser=argparse.ArgumentParser()
parser.add_argument('--shader',default='Tools/LookDev/hlsl/intro_ink.hlsl')
parser.add_argument('--variant',default='')
args=parser.parse_args()
OUT=Path('P:/FoA/Saved/LookDev/intro_restored/rice_ink')/args.variant
OUT.mkdir(parents=True,exist_ok=True)
def c(cmd,**params):
 r=h.call(cmd,params);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('failed') and not d.get('has_errors'),d
 return d
def rgb(hex):return [pow(int(hex[i:i+2],16)/255,2.2) for i in (0,2,4)]
def protected():
 return {graph:hashlib.sha256(json.dumps(inspect(W,graph),sort_keys=True).encode()).hexdigest() for graph in ('Finish','FocusSkip','EventGraph','NextPanel','ApplyLayer')}
assert not c('editor_get_state')['pie_running'],'User PIE active'
lease=h.lease_acquire('room-takeover',['asset:'+P,'asset:'+W],ttl_s=90,wait_s=20)
try:
 assert not c('editor_get_state')['pie_running']
 graphs=protected()
 info=c('material_get_info',path=P)
 (OUT/'material_before.json').write_text(json.dumps(info,indent=1))
 custom=[e for e in info['expressions'] if e['class']=='MaterialExpressionCustom']
 vector=[e for e in info['expressions'] if e['class']=='MaterialExpressionVectorParameter']
 assert len(custom)==len(vector)==1,(custom,vector)
 c('material_set_node',material_path=P,node_id=custom[0]['id'],properties={'Code':Path(args.shader).read_text(),'Description':'Pigment on rice paper'})
 c('material_set_node',material_path=P,node_id=vector[0]['id'],properties={'DefaultValue':{'R':.30,'G':.045,'B':.016,'A':.94}})
 c('material_validate',material_path=P)
 material=c('material_compile',material_path=P)
 assert not material.get('errors'),material
 paper=rgb('EEE4CC');text=rgb('333A3B')
 for name,alpha in [('Img_Black',1),('Img_Foot',.94)]:
  c('ui_set_widget_properties',widget_blueprint_path=W,widget_name=name,properties={'Brush':{'DrawAs':'Image','TintColor':{'SpecifiedColor':dict(zip('RGBA',paper+[alpha]))}}})
 for name in ('Txt_Sub','Txt_Skip'):
  c('ui_set_widget_properties',widget_blueprint_path=W,widget_name=name,properties={'ColorAndOpacity':{'SpecifiedColor':dict(zip('RGBA',text+[1]))}})
 compiled=c('ui_compile_widget',widget_blueprint_path=W)
 c('asset_save',asset_paths=[P,W])
 after=c('material_get_info',path=P)
 assert protected()==graphs,'Intro lifecycle or depth graph unexpectedly changed'
 (OUT/'applied.json').write_text(json.dumps({'material_compile':material,'widget_compile':compiled,'material':after,'protected_graph_hashes':graphs,'palette':['EEE4CC','333A3B','687D86','B59A69'],'samples':9,'runtime_verified':False},indent=1))
 print(json.dumps({'material_compile':material,'widget_compile':compiled,'expression_count':len(after['expressions'])}))
finally:h.release('room-takeover',lease)
