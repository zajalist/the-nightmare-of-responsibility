"""Two owned HUD eyelids provide headache blinks without camera fade/input ownership changes."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
HUD='/Game/FoA/UI/Game/WBP_HUD';HC=HUD+'.WBP_HUD_C'
D='/Game/FoA/Gameplay/BP_BeatDirector';DC=D+'.BP_BeatDirector_C'
FE='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
K='/Script/Engine.KismetMathLibrary:';KS='/Script/Engine.KismetSystemLibrary:';GS='/Script/Engine.GameplayStatics:'
def c(n,**p):
 r=h.call(n,p);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
 return d
def fresh(path,graph):
 ns,_=inspect(path,graph);entry=find(ns,graph);b=Batch(path,graph)
 old=[n['node_id'] for n in ns if n['node_id']!=entry]
 if old:b.ops.append(dict(op='remove',node_ids=old))
 return b,entry
def declare(path,graph,inputs=[]):
 if not h.call('blueprint_inspect_graph',{'path':path,'graph_name':graph}).get('ok'):c('blueprint_add_function',path=path,function_name=graph,inputs=inputs)
def check_math():
 def blink(t,reduce=0):return max(0,min(1,max(1-abs(t-.28)/.22,1-abs(t-.95)/.28)))*(1-reduce)
 assert blink(0)==0 and blink(1.3)==0 and blink(4)==0
 assert blink(.28)==1 and blink(.95)==1 and blink(.28,1)==0
check_math()
assert not c('editor_get_state')['pie_running'],'User or coordinator PIE active'
owner=h.agent_id() or 'room-takeover';lease=h.lease_acquire(owner,['asset:'+HUD,'asset:'+D],ttl_s=120,wait_s=30)
try:
 tree=c('ui_query',path=HUD)
 def names(n):return [n['name']]+[v for ch in n.get('children',[]) for v in names(ch)]
 have=names(tree['root'])
 for n,pivot in [('Brd_HeadacheTop',0),('Brd_HeadacheBottom',1)]:
  if n not in have:c('ui_add_element',widget_blueprint_path=HUD,name=n,child_class='Border',parent_widget_name='Overlay_0')
  c('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name=n,properties={
   'Visibility':'HitTestInvisible','BrushColor':'(R=0,G=0,B=0,A=1)',
   'RenderTransform':{'Scale':{'X':1,'Y':0}},'RenderTransformPivot':{'X':.5,'Y':pivot}},
   slot_props={'horizontal_alignment':'Fill','vertical_alignment':'Fill','padding':[0,0,0,0]})
  c('ui_set_variable',widget_blueprint_path=HUD,widget_name=n,is_variable=True)
 declare(HUD,'SetHeadacheBlink',[{'name':'Amount','type':'float'}])
 b,e=fresh(HUD,'SetHeadacheBlink');b.fn('clamp',K+'FClamp',0,250,Min=0,Max=1);b.link(e,'Amount','clamp','Value')
 b.fn('half',K+'Multiply_DoubleDouble',300,250,B=.5);b.link('clamp','ReturnValue','half','A')
 b.fn('scale',K+'MakeVector2D',600,250,X=1);b.link('half','ReturnValue','scale','Y');prev=e
 for i,n in enumerate(('Brd_HeadacheTop','Brd_HeadacheBottom')):
  b.get('lid'+str(i),n,900+i*350,250);b.fn('apply'+str(i),'/Script/UMG.Widget:SetRenderScale',900+i*350,0)
  b.link('lid'+str(i),n,'apply'+str(i),'self');b.link('scale','ReturnValue','apply'+str(i),'Scale');b.chain(prev,'apply'+str(i));prev='apply'+str(i)
 b.comment('Owned eyelids',[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()
 c('ui_compile_widget',widget_blueprint_path=HUD);c('ui_save_widget',widget_blueprint_path=HUD)
 declare(D,'ApplyHeadacheBlink',[{'name':'Amount','type':'float'}])
 b,e=fresh(D,'ApplyHeadacheBlink');b.fn('fe',GS+'GetActorOfClass',300,0,ActorClass=FE);b.chain(e,'fe')
 b.fn('valid',KS+'IsValid',300,300);b.link('fe','ReturnValue','valid','Object');b.node('guard','branch',600,0);b.link('valid','ReturnValue','guard','Condition');b.chain('fe','guard')
 b.get('hud','HUD',600,300,FE);b.link('fe','ReturnValue','hud','self');b.node('cast','cast',900,0,class_path=HC);b.link('hud','HUD','cast','Object');b.chain('guard','cast')
 b.fn('apply',HC+':SetHeadacheBlink',1250,0);b.link('cast','AsWBP HUD','apply','self');b.link(e,'Amount','apply','Amount');b.chain('cast','apply')
 b.comment('Use the existing HUD',[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()
 ns,es=inspect(D,'StepHeadache');by={n['node_id']:n for n in ns}
 if not any(n['title']=='ApplyHeadacheBlink' for n in ns):
  start=find(ns,'Get StoryStarted');elapsed=next(edge['to_node'] for edge in es if edge['from_node']==start and edge['to_pin']=='B')
  # The ReduceMotion read already exists; use its value directly to suppress vision motion.
  motion=next(n['node_id'] for n in ns if n['title']=='GetScalarParameterValue')
  tail=find(ns,'SetEchoStrength');b=Batch(D,'StepHeadache')
  for i,centre,width in [(0,.28,.22),(1,.95,.28)]:
   x=200+i*950
   b.fn('offset'+str(i),K+'Subtract_DoubleDouble',x,1800,B=centre);b.link(elapsed,'ReturnValue','offset'+str(i),'A')
   b.fn('abs'+str(i),K+'Abs',x+230,1800);b.link('offset'+str(i),'ReturnValue','abs'+str(i),'A')
   b.fn('width'+str(i),K+'Divide_DoubleDouble',x+460,1800,B=width);b.link('abs'+str(i),'ReturnValue','width'+str(i),'A')
   b.fn('blink'+str(i),K+'Subtract_DoubleDouble',x+690,1800,A=1);b.link('width'+str(i),'ReturnValue','blink'+str(i),'B')
  b.fn('either',K+'FMax',2200,1800);b.link('blink0','ReturnValue','either','A');b.link('blink1','ReturnValue','either','B')
  b.fn('clamp',K+'FClamp',2450,1800,Min=0,Max=1);b.link('either','ReturnValue','clamp','Value')
  b.fn('allowed',K+'Subtract_DoubleDouble',2200,2100,A=1);b.link(motion,'ReturnValue','allowed','B')
  b.fn('amount',K+'Multiply_DoubleDouble',2700,1800);b.link('clamp','ReturnValue','amount','A');b.link('allowed','ReturnValue','amount','B')
  b.fn('eyes',DC+':ApplyHeadacheBlink',3000,1500);b.link('amount','ReturnValue','eyes','Amount');b.chain(tail,'eyes')
  b.comment('Two brief eyelid closures',[o['ref'] for o in b.ops if o.get('op')=='add_node']);b.run()
 ns,es=inspect(D,'EndHeadache')
 if not any(n['title']=='ApplyHeadacheBlink' for n in ns):
  entry=find(ns,'EndHeadache');edge=next(e for e in es if e['from_node']==entry and e['from_pin']=='then');b=Batch(D,'EndHeadache')
  b.ops.append(dict(op='move',node_id=entry,x=-1550,y=0));b.fn('openeyes',DC+':ApplyHeadacheBlink',-1250,0,Amount=0)
  b.cut(entry,'then',edge['to_node'],edge['to_pin']);b.chain(entry,'openeyes');b.link('openeyes','then',edge['to_node'],edge['to_pin']);b.comment('Always reopen the eyes',['openeyes']);b.run()
 proof={'hud_compile':c('blueprint_compile',path=HUD),'director_compile':c('blueprint_compile',path=D)}
 c('asset_save',asset_paths=[HUD,D])
 for p,g in [(HUD,'SetHeadacheBlink'),(D,'ApplyHeadacheBlink'),(D,'StepHeadache'),(D,'EndHeadache')]:
  ns,es=inspect(p,g);proof[g]={'nodes':ns,'edges':es}
 Path('P:/FoA/Saved/LookDev/prompt_audit/headache_blink_integration.json').write_text(json.dumps(proof,indent=1))
 print('Owned headache blink integrated; clean compile/save; runtime proof pending')
finally:h.release(owner,lease)
