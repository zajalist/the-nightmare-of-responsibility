"""Stronger layered camera motion and live ink-shader parameters in the existing intro widget."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
W='/Game/FoA/UI/Intro/WBP_IntroStory';C=W+'.WBP_IntroStory_C'
M='/Game/FoA/UI/Materials/M_UI_Panel';NEAR='/Game/FoA/UI/Materials/MI_UI_PanelNear'
K='/Script/Engine.KismetMathLibrary:';KS='/Script/Engine.KismetSystemLibrary:';MID='/Script/Engine.MaterialInstanceDynamic:'
def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
 return d
def fresh(name):
 ns,_=inspect(W,name);e=find(ns,name);b=Batch(W,name)
 old=[n['node_id'] for n in ns if n['node_id']!=e]
 if old:b.ops.append(dict(op='remove',node_ids=old))
 return b,e
assert not c('editor_get_state')['pie_running']
owner=h.agent_id() or 'room-takeover';lease=h.lease_acquire(owner,['asset:'+W],ttl_s=180,wait_s=30)
try:
 for n in ('FarInk','NearInk'):c('blueprint_add_variable',path=W,variable_name=n,variable_type='object:/Script/Engine.MaterialInstanceDynamic',category='Intro',update_existing=True)
 for fn in ('EnsureInkMaterials','UpdateInkReveal'):
  if not h.call('blueprint_inspect_graph',{'path':W,'graph_name':fn}).get('ok'):c('blueprint_add_function',path=W,function_name=fn)
 b,e=fresh('EnsureInkMaterials');b.get('far','FarInk',0,250);b.get('near','NearInk',0,450)
 for n,var,y in [('far','FarInk',250),('near','NearInk',450)]:b.fn(n+'valid',KS+'IsValid',280,y);b.link(n,var,n+'valid','Object')
 b.fn('ready',K+'BooleanAND',560,250);b.link('farvalid','ReturnValue','ready','A');b.link('nearvalid','ReturnValue','ready','B');b.node('once','branch',850,0);b.link('ready','ReturnValue','once','Condition');b.chain(e,'once')
 prev=None
 for i,(image,var,mat) in enumerate([('Img_Panel','FarInk',M),('Img_Near','NearInk',NEAR)]):
  x=1100+i*950;b.get('image'+str(i),image,x,500)
  b.fn('brush'+str(i),'/Script/UMG.Image:SetBrushFromMaterial',x,0,Material=mat);b.link('image'+str(i),image,'brush'+str(i),'self')
  b.fn('dynamic'+str(i),'/Script/UMG.Image:GetDynamicMaterial',x+300,0);b.link('image'+str(i),image,'dynamic'+str(i),'self')
  b.set('save'+str(i),var,x+600,0);b.link('dynamic'+str(i),'ReturnValue','save'+str(i),var)
  if prev:b.chain(prev,'brush'+str(i))
  else:b.link('once','else','brush'+str(i),'execute')
  b.chain('brush'+str(i),'dynamic'+str(i),'save'+str(i));prev='save'+str(i)
 b.comment('One ink instance per depth',[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()
 b,e=fresh('UpdateInkReveal');b.get('age','PanelTime',0,250);b.fn('divide',K+'Divide_DoubleDouble',260,250,B=1.15);b.link('age','PanelTime','divide','A')
 b.fn('clamp',K+'FClamp',520,250,Min=0,Max=1);b.link('divide','ReturnValue','clamp','Value')
 b.fn('reduced','/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue',0,550,Collection='/Game/FoA/UI/Style/MPC_UI.MPC_UI',ParameterName='ReduceMotion')
 b.fn('static',K+'Greater_DoubleDouble',520,550,B=.5);b.link('reduced','ReturnValue','static','A')
 b.fn('reveal',K+'SelectFloat',780,250,A=1);b.link('clamp','ReturnValue','reveal','B');b.link('static','ReturnValue','reveal','bPickA')
 b.get('far','FarInk',780,550);b.fn('valid',KS+'IsValid',1050,550);b.link('far','FarInk','valid','Object');b.node('guard','branch',1050,0);b.link('valid','ReturnValue','guard','Condition');b.chain(e,'reduced','guard')
 b.fn('setfar',MID+'SetScalarParameterValue',1330,0,ParameterName='Reveal');b.link('far','FarInk','setfar','self');b.link('reveal','ReturnValue','setfar','Value')
 b.get('near','NearInk',1330,550);b.fn('setnear',MID+'SetScalarParameterValue',1620,0,ParameterName='Reveal');b.link('near','NearInk','setnear','self');b.link('reveal','ReturnValue','setnear','Value');b.chain('guard','setfar','setnear')
 b.comment('Ink develops over the paper',[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()
 ns,es=inspect(W,'NextPanel');by={n['node_id']:n for n in ns}
 brushes=[n for n in ns if n['title']=='SetBrushFromTexture']
 if brushes:
  assert len(brushes)==2
  def image_for(n):
   ed=next(e for e in es if e['to_node']==n['node_id'] and e['to_pin']=='self');return by[ed['from_node']]
  far=next(n for n in brushes if image_for(n)['title']=='Get Img_Panel');near=next(n for n in brushes if image_for(n)['title']=='Get Img_Near')
  before=next(e for e in es if e['to_node']==far['node_id'] and e['to_pin']=='execute');after=next(e for e in es if e['from_node']==near['node_id'] and e['from_pin']=='then')
  b=Batch(W,'NextPanel');b.fn('ensure',C+':EnsureInkMaterials',1500,-80)
  b.cut(before['from_node'],before['from_pin'],before['to_node'],before['to_pin']);b.cut(after['from_node'],after['from_pin'],after['to_node'],after['to_pin'])
  b.chain(before['from_node'],'ensure');prev='ensure';remove=[]
  for i,(old,var) in enumerate([(far,'FarInk'),(near,'NearInk')]):
   tex=next(e for e in es if e['to_node']==old['node_id'] and e['to_pin']=='Texture');x=1800+i*400
   b.get('ink'+str(i),var,x,-450);b.fn('texture'+str(i),MID+'SetTextureParameterValue',x,-80,ParameterName='Texture')
   b.link('ink'+str(i),var,'texture'+str(i),'self');b.link(tex['from_node'],tex['from_pin'],'texture'+str(i),'Value');b.chain(prev,'texture'+str(i));prev='texture'+str(i)
   remove.extend([old['node_id'],image_for(old)['node_id']])
  b.link(prev,'then',after['to_node'],after['to_pin']);b.ops.append(dict(op='remove',node_ids=remove));b.comment('Feed the real render layers',['ensure','ink0','texture0','ink1','texture1']);b.run()
 ns,es=inspect(W,'UpdateFrame')
 if not any(n['title']=='UpdateInkReveal' for n in ns):
  sub=find(ns,'Get Txt_Sub');setter=next(e['to_node'] for e in es if e['from_node']==sub and e['to_pin']=='self')
  b=Batch(W,'UpdateFrame');b.fn('ink',C+':UpdateInkReveal',4600,0);b.chain(setter,'ink');b.comment('Reveal the painted frame',['ink']);b.run()
 ns,es=inspect(W,'ApplyLayer');b=Batch(W,'ApplyLayer')
 def number(n,pin):
  v=next((p.get('default_value') for p in n.get('pins',[]) if p['name']==pin),None)
  try:return float(v)
  except:return None
 shift=next(n for n in ns if n['title'] in ['float * float','double * double'] and number(n,'B') in [42,260])
 zoom=next(n for n in ns if n['title'] in ['float * float','double * double'] and number(n,'B') in [.03,.06])
 over=next(n for n in ns if n['title'] in ['float + float','double + double'] and number(n,'B') in [1.045,1.18])
 b.pin(shift['node_id'],'B',260);b.pin(zoom['node_id'],'B',.06);b.pin(over['node_id'],'B',1.18)
 xy=next(n for n in ns if n['title']=='MakeVector2D' and any(e['to_node']==n['node_id'] and e['from_node']==shift['node_id'] for e in es))
 if not any(e['to_node']==xy['node_id'] and e['to_pin']=='Y' for e in es):
  depth=next(e for e in es if e['to_node']==shift['node_id'] and e['to_pin']=='A')
  b.fn('lift',K+'Multiply_DoubleDouble',430,750,B=-36);b.link(depth['from_node'],depth['from_pin'],'lift','A');b.link('lift','ReturnValue',xy['node_id'],'Y');b.comment('Vertical depth drift',['lift'])
 b.run()
 for name,material in [('Img_Panel',M),('Img_Near',NEAR)]:c('ui_set_widget_properties',widget_blueprint_path=W,widget_name=name,properties={'Brush':{'ResourceObject':material,'DrawAs':'Image'},'RenderTransform':{'Scale':{'X':1.18,'Y':1.18}}})
 paper=[pow(v/255,2.2) for v in (238,228,204)];charcoal=[pow(v/255,2.2) for v in (51,58,59)]
 for n,col in [('Img_Black',paper+[1]),('Img_Foot',paper+[.94])]:c('ui_set_widget_properties',widget_blueprint_path=W,widget_name=n,properties={'Brush':{'DrawAs':'Image','TintColor':{'SpecifiedColor':dict(zip('RGBA',col))}},'Visibility':'HitTestInvisible','RenderOpacity':1})
 for n in ('Txt_Sub','Txt_Skip'):c('ui_set_widget_properties',widget_blueprint_path=W,widget_name=n,properties={'ColorAndOpacity':{'SpecifiedColor':dict(zip('RGBA',charcoal+[1]))}})
 result=c('ui_compile_widget',widget_blueprint_path=W);c('ui_save_widget',widget_blueprint_path=W)
 proof={'compile':result,'foreground_sweep_px':260,'background_sweep_px':65,'overscan':1.18}
 for graph in ('EnsureInkMaterials','UpdateInkReveal','NextPanel','UpdateFrame','ApplyLayer'):
  ns,es=inspect(W,graph);proof[graph]={'nodes':ns,'edges':es}
 Path('P:/FoA/Saved/LookDev/intro_restored/ink_parallax_integration.json').write_text(json.dumps(proof,indent=1));print('Ink parallax integrated and saved',result)
finally:h.release(owner,lease)
